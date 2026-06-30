"""Lógica de pedidos en línea (tienda).

Un pedido se crea de forma atómica: valida los productos, calcula totales (los
precios incluyen IVA, que se desglosa) y descuenta inventario del punto elegido
por el comprador creando los movimientos de salida (venta) en el kardex, así
toda compra en línea queda trazada en el inventario igual que una venta del POS.

El pedido avanza por estados (pendiente → confirmado → enviado → entregado). La
cancelación devuelve la existencia con movimientos de ajuste de entrada. Nada se
borra: cada paso queda como registro.
"""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from geo.geocoding import geocode, haversine_km
from inventory.models import MovementReason, MovementType, StockLevel, Warehouse
from inventory.services import record_movement, resolve_warehouse_coords

from .emails import send_order_status_email
from .models import Order, OrderAllocation, OrderItem

CENTS = Decimal('0.01')

# Cómo se mapea la forma de pago del pedido a la forma de pago de la venta.
# (La venta del POS no tiene "nequi"; se registra como transferencia.)
_ORDER_TO_SALE_PAYMENT = {
    Order.Payment.CARD: 'tarjeta',
    Order.Payment.NEQUI: 'transferencia',
    Order.Payment.TRANSFER: 'transferencia',
    Order.Payment.CASH: 'efectivo',
}


class OrderError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'No se pudo procesar el pedido.'
    default_code = 'invalid_order'


def _money(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def _next_number():
    last = Order.objects.aggregate(m=models.Max('number'))['m'] or 0
    return last + 1


def _stock_map(warehouses, variant_ids):
    """{bodega_id: {variante_id: existencia}} para las bodegas/variantes dadas
    (una sola consulta a StockLevel)."""
    by_wh = defaultdict(dict)
    rows = StockLevel.objects.filter(
        warehouse__in=warehouses, variant_id__in=variant_ids
    ).values_list('warehouse_id', 'variant_id', 'quantity')
    for wh_id, variant_id, qty in rows:
        by_wh[wh_id][variant_id] = qty
    return by_wh


def _warehouses_with_full_stock(warehouses, items):
    """De las bodegas dadas, las que tienen existencia para TODAS las líneas.
    Devuelve [(warehouse, unidades_totales)] (para desempatar por "más stock")."""
    needed = {e['variant'].id: int(e['quantity']) for e in items}
    warehouses = list(warehouses)
    stock = _stock_map(warehouses, list(needed))
    out = []
    for wh in warehouses:
        wh_stock = stock.get(wh.id, {})
        if all(wh_stock.get(vid, 0) >= q for vid, q in needed.items()):
            out.append((wh, sum(wh_stock.get(vid, 0) for vid in needed)))
    return out


def _can_fulfill(items, warehouses):
    """True si la existencia SUMADA de las bodegas alcanza para todo el pedido."""
    warehouses = list(warehouses)
    needed = {e['variant'].id: int(e['quantity']) for e in items}
    stock = _stock_map(warehouses, list(needed))
    for vid, qty in needed.items():
        total = sum(stock.get(wh.id, {}).get(vid, 0) for wh in warehouses)
        if total < qty:
            return False
    return True


def _allocate(items, warehouses_ordered):
    """Reparte el pedido entre las bodegas (en el orden dado), tomando de cada una
    lo que tenga hasta cubrir cada variante (fulfillment dividido).

    Devuelve [{variant, warehouse, quantity, unit_cost}] o None si ni sumando
    todas las bodegas alcanza para alguna variante.
    """
    warehouses_ordered = list(warehouses_ordered)
    needed = {e['variant']: int(e['quantity']) for e in items}
    stock = _stock_map(warehouses_ordered, [v.id for v in needed])
    allocations = []
    for variant, qty_needed in needed.items():
        remaining = qty_needed
        unit_cost = _money(variant.average_cost or variant.cost_price)
        for wh in warehouses_ordered:
            if remaining <= 0:
                break
            take = min(stock.get(wh.id, {}).get(variant.id, 0), remaining)
            if take > 0:
                allocations.append({
                    'variant': variant, 'warehouse': wh,
                    'quantity': take, 'unit_cost': unit_cost,
                })
                remaining -= take
        if remaining > 0:
            return None
    return allocations


def _proximity_rank(warehouse, address):
    """Cercanía por ubicación relacional cuando no hay coordenadas (menor = más
    cerca): 0 misma ciudad · 1 mismo departamento · 2 mismo país · 3 otro."""
    city = warehouse.city
    if not city or address is None:
        return 3
    if address.city_id and city.id == address.city_id:
        return 0
    if address.department_id and city.department_id == address.department_id:
        return 1
    if address.country_id and city.department.country_id == address.country_id:
        return 2
    return 3


def _order_by_proximity(warehouses, address):
    """Ordena las bodegas de más a menos cercana a la dirección. Usa la distancia
    real (haversine) cuando hay coordenadas en ambos lados; si no, cae a la
    cercanía por ciudad/departamento/país."""
    def key(wh):
        dist = None
        if address is not None:
            dist = haversine_km(address.latitude, address.longitude, wh.latitude, wh.longitude)
        if dist is not None:
            return (0, dist, wh.id)  # con coordenadas: por distancia real
        return (1, _proximity_rank(wh, address), wh.id)  # sin coords: por ciudad
    return sorted(warehouses, key=key)


def ensure_address_coords(address):
    """Geocoordenadas de la dirección, consultándolas UNA vez si faltan y
    guardándolas (respaldo perezoso para direcciones viejas sin coordenadas).
    Si ya las tiene, no llama a OpenStreetMap."""
    if address is None or (address.latitude is not None and address.longitude is not None):
        return
    parts = [
        address.line1,
        address.city.name if address.city_id else '',
        address.department.name if address.department_id else '',
        address.country.name if address.country_id else '',
    ]
    coords = geocode(', '.join(p for p in parts if p))
    if coords:
        address.latitude, address.longitude = coords
        address.save(update_fields=['latitude', 'longitude', 'updated_at'])


def allocate_delivery(items, address):
    """Reparte un envío a domicilio: bodegas activas ordenadas por cercanía al
    comprador, surtiendo desde varias sedes si hace falta. None si no alcanza.

    Asegura (perezosamente) las coordenadas de la dirección y de las bodegas:
    si faltan, las consulta una vez y las guarda; si ya están, las reutiliza.
    """
    ensure_address_coords(address)
    warehouses = list(
        Warehouse.objects.filter(is_active=True).select_related('city__department')
    )
    for wh in warehouses:
        resolve_warehouse_coords(wh)
    return _allocate(items, _order_by_proximity(warehouses, address))


def single_warehouse_allocation(items, warehouse):
    """Reparto de todo el pedido desde UNA sola bodega (recoger en una tienda).
    None si esa bodega no tiene el pedido completo."""
    return _allocate(items, [warehouse])


def pickup_warehouses(items):
    """Tiendas públicas activas con el pedido COMPLETO (para recoger en una sola
    sede). Ordenadas por mayor existencia."""
    warehouses = Warehouse.objects.filter(is_active=True, show_in_store=True)
    candidates = _warehouses_with_full_stock(warehouses, items)
    candidates.sort(key=lambda c: (-c[1], c[0].name))
    return [wh for wh, _total in candidates]


def allocate_pickup_split(items):
    """Reparte el pedido para recoger entre varias tiendas públicas, priorizando
    las de mayor existencia (para usar la menor cantidad de sedes). None si ni
    sumando todas alcanza."""
    warehouses = list(Warehouse.objects.filter(is_active=True, show_in_store=True))
    variant_ids = [e['variant'].id for e in items]
    stock = _stock_map(warehouses, variant_ids)
    warehouses.sort(key=lambda wh: -sum(stock.get(wh.id, {}).values()))
    return _allocate(items, warehouses)


def delivery_available(items):
    """True si, sumando todas las bodegas activas, se puede enviar a domicilio."""
    return _can_fulfill(items, Warehouse.objects.filter(is_active=True))


def pickup_split_available(items):
    """True si, combinando tiendas públicas, se puede recoger todo el pedido."""
    return _can_fulfill(items, Warehouse.objects.filter(is_active=True, show_in_store=True))


def allocations_by_warehouse(allocations):
    """Agrupa una lista de asignaciones por bodega: [{'warehouse', 'items': [...]}]."""
    grouped = defaultdict(list)
    for a in allocations:
        grouped[a['warehouse']].append(a)
    return [{'warehouse': wh, 'items': rows} for wh, rows in grouped.items()]


def check_availability(warehouse, items):
    """Indica, por línea, si el punto tiene existencia para la cantidad pedida.

    No revela la existencia exacta (dato no público): solo si la cantidad
    solicitada se puede cumplir. `items`: [{variant, quantity}].
    """
    levels = {
        sl.variant_id: sl.quantity
        for sl in StockLevel.objects.filter(
            warehouse=warehouse,
            variant__in=[e['variant'] for e in items],
        )
    }
    result = []
    for entry in items:
        variant = entry['variant']
        quantity = int(entry['quantity'])
        result.append(
            {
                'variant': variant.id,
                'quantity': quantity,
                'available': levels.get(variant.id, 0) >= quantity,
            }
        )
    return result


@transaction.atomic
def create_order(
    *,
    user,
    allocations,
    fulfillment,
    payment_method,
    items,
    shipping=None,
    note='',
):
    """Crea un pedido PENDIENTE y descuenta inventario según el reparto entre sedes.

    `items`: [{variant, quantity}] (líneas del comprador). `allocations`:
    [{variant, warehouse, quantity, unit_cost}] (de qué bodega sale cada unidad;
    puede haber varias sedes). La bodega "principal" del pedido es la que aporta
    más unidades. `shipping`: datos de envío (solo a domicilio). El pago es
    simulado: las formas distintas del efectivo contra entrega se marcan pagadas.
    """
    if not items:
        raise OrderError('El pedido no tiene productos.')
    if not allocations:
        raise OrderError('No hay existencia para surtir el pedido.')

    shipping = shipping or {}

    # Bodega principal del pedido: la que aporta más unidades (para la venta del
    # punto 2 y la analítica; el reparto real vive en OrderAllocation).
    units_by_wh = defaultdict(int)
    for a in allocations:
        units_by_wh[a['warehouse']] += a['quantity']
    warehouse = max(units_by_wh.items(), key=lambda kv: (kv[1], -kv[0].id))[0]

    # ---- Construye las líneas y los totales (precio incluye IVA) ----
    subtotal = Decimal('0')
    tax_total = Decimal('0')
    total = Decimal('0')
    line_rows = []
    seen = set()
    for entry in items:
        variant = entry['variant']
        if variant.id in seen:
            raise OrderError('Hay un producto repetido en el pedido.')
        seen.add(variant.id)
        quantity = int(entry['quantity'])
        if quantity <= 0:
            raise OrderError('Cada producto debe tener cantidad mayor a cero.')

        unit_price = _money(variant.sale_price)
        rate = int(variant.product.tax_rate or 0)
        line_total = _money(unit_price * quantity)
        divisor = Decimal(1) + Decimal(rate) / Decimal(100)
        line_subtotal = _money(line_total / divisor) if divisor else line_total
        line_tax = _money(line_total - line_subtotal)

        subtotal += line_subtotal
        tax_total += line_tax
        total += line_total

        opts = variant.options_label
        description = variant.product.name + (f' — {opts}' if opts else '')
        line_rows.append(
            {
                'variant': variant,
                'description': description,
                'sku': variant.sku,
                'quantity': quantity,
                'unit_price': unit_price,
                'tax_rate': rate,
                'unit_cost': _money(variant.average_cost or variant.cost_price),
                'line_total': line_total,
            }
        )

    is_paid = payment_method != Order.Payment.CASH

    order = Order.objects.create(
        number=_next_number(),
        user=user,
        warehouse=warehouse,
        status=Order.Status.PENDING,
        fulfillment=fulfillment,
        payment_method=payment_method,
        is_paid=is_paid,
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        ship_recipient=shipping.get('recipient', ''),
        ship_phone=shipping.get('phone', ''),
        ship_phone_alt=shipping.get('phone_alt', ''),
        ship_line1=shipping.get('line1', ''),
        ship_city=shipping.get('city', ''),
        ship_department=shipping.get('department', ''),
        ship_country=shipping.get('country', ''),
        ship_notes=shipping.get('notes', ''),
        note=note,
    )
    OrderItem.objects.bulk_create(
        [OrderItem(order=order, **row) for row in line_rows]
    )
    OrderAllocation.objects.bulk_create([
        OrderAllocation(
            order=order, variant=a['variant'], warehouse=a['warehouse'],
            quantity=a['quantity'], unit_cost=a['unit_cost'],
        )
        for a in allocations
    ])

    # ---- Descuenta inventario de cada sede según el reparto (salida = venta) ----
    # record_movement no deja la existencia en negativo: si falta stock lanza
    # InsufficientStock y la transacción completa se revierte.
    for a in allocations:
        record_movement(
            variant=a['variant'],
            warehouse=a['warehouse'],
            type=MovementType.EXIT,
            quantity=a['quantity'],
            reason=MovementReason.SALE,
            reference=f'Pedido {order.code}',
            user=user,
        )

    return order


def build_sale_from_order(order, *, user=None):
    """Genera la venta (registro de ingreso) de un pedido entregado.

    Un pedido culmina en una venta: ésta es el documento fiscal del libro de
    ventas único (canal=online), con copia de las líneas y el pago. NO mueve
    inventario —el pedido ya lo descontó al crearse—; solo registra el ingreso.

    Idempotente: si el pedido ya tiene su venta, la devuelve sin duplicar.
    Debe llamarse dentro de una transacción.
    """
    # Import diferido para evitar dependencia circular a nivel de módulo.
    from sales.models import Sale, SaleItem, SalePayment, SaleChannel, SaleStatus

    existing = Sale.objects.filter(order=order).first()
    if existing:
        return existing

    next_number = (Sale.objects.aggregate(m=models.Max('number'))['m'] or 0) + 1
    sale = Sale.objects.create(
        number=next_number,
        channel=SaleChannel.ONLINE,
        order=order,
        customer=order.user,
        warehouse=order.warehouse,
        status=SaleStatus.COMPLETED,
        subtotal=order.subtotal,
        tax_total=order.tax_total,
        discount=Decimal('0'),
        total=order.total,
        paid=order.total,
        change=Decimal('0'),
        note=f'Pedido {order.code}',
        receipt_email=order.user.email or '',
        created_by=user,
    )
    # La venta refleja el evento económico del pedido: misma fecha de creación
    # (cuando salió el inventario), para que el libro y la analítica no se
    # desplacen a la fecha de entrega. created_at es auto_now_add → se fija con
    # update() que lo evita.
    Sale.objects.filter(pk=sale.pk).update(created_at=order.created_at)

    SaleItem.objects.bulk_create([
        SaleItem(
            sale=sale,
            variant=item.variant,
            description=item.description,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            unit_cost=item.unit_cost,
            line_total=item.line_total,
        )
        for item in order.items.select_related('variant').all()
    ])
    SalePayment.objects.create(
        sale=sale,
        method=_ORDER_TO_SALE_PAYMENT.get(order.payment_method, 'otro'),
        amount=order.total,
    )
    return sale


# Transiciones lineales del flujo: cada estado avanza al siguiente.
_NEXT_STATUS = {
    Order.Status.PENDING: Order.Status.CONFIRMED,
    Order.Status.CONFIRMED: Order.Status.SHIPPED,
    Order.Status.SHIPPED: Order.Status.DELIVERED,
}
_STATUS_TIMESTAMP = {
    Order.Status.CONFIRMED: 'confirmed_at',
    Order.Status.SHIPPED: 'shipped_at',
    Order.Status.DELIVERED: 'delivered_at',
}


@transaction.atomic
def advance_order(order, *, user=None):
    """Avanza el pedido al siguiente estado del flujo (lo hace el personal).

    Al entregar marca el pago como recibido (cubre el efectivo contra entrega).
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    nxt = _NEXT_STATUS.get(order.status)
    if nxt is None:
        raise OrderError('El pedido ya está en su estado final o cancelado.')

    fields = ['status', 'handled_by', 'updated_at']
    order.status = nxt
    order.handled_by = user
    setattr(order, _STATUS_TIMESTAMP[nxt], timezone.now())
    fields.append(_STATUS_TIMESTAMP[nxt])
    if nxt == Order.Status.DELIVERED and not order.is_paid:
        order.is_paid = True
        fields.append('is_paid')
    order.save(update_fields=fields)

    # Al entregar, el pedido culmina en una venta (registro de ingreso en el
    # libro de ventas único). No mueve inventario: el pedido ya lo descontó.
    if nxt == Order.Status.DELIVERED:
        build_sale_from_order(order, user=user)

    # Avisa al comprador del nuevo estado, tras confirmar la transacción (un fallo
    # de correo no debe revertir el cambio de estado).
    transaction.on_commit(lambda: send_order_status_email(order))
    return order


@transaction.atomic
def cancel_order(order, *, user=None, reason=''):
    """Cancela un pedido abierto y devuelve la existencia al punto.

    Las devoluciones se registran como ajustes de entrada en el kardex (nada se
    borra). No se pueden cancelar pedidos entregados ni ya cancelados.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.is_open:
        raise OrderError('Este pedido ya no se puede cancelar.')

    # Devuelve la existencia a CADA sede según el reparto con el que se surtió.
    for a in order.allocations.select_related('variant', 'warehouse'):
        record_movement(
            variant=a.variant,
            warehouse=a.warehouse,
            type=MovementType.ADJUST_IN,
            quantity=a.quantity,
            reason=MovementReason.CORRECTION,
            reference=f'Cancelación pedido {order.code}',
            user=user,
        )

    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.cancel_reason = reason
    order.handled_by = user
    order.save(
        update_fields=['status', 'cancelled_at', 'cancel_reason', 'handled_by', 'updated_at']
    )
    transaction.on_commit(lambda: send_order_status_email(order))
    return order
