"""Lógica de pedidos en línea (tienda).

Un pedido se crea de forma atómica: valida los productos, calcula totales (los
precios incluyen IVA, que se desglosa) y descuenta inventario del punto elegido
por el comprador creando los movimientos de salida (venta) en el kardex, así
toda compra en línea queda trazada en el inventario igual que una venta del POS.

El pedido avanza por estados (pendiente → confirmado → enviado → entregado). La
cancelación devuelve la existencia con movimientos de ajuste de entrada. Nada se
borra: cada paso queda como registro.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from inventory.models import MovementReason, MovementType, StockLevel
from inventory.services import record_movement

from .models import Order, OrderItem

CENTS = Decimal('0.01')


class OrderError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'No se pudo procesar el pedido.'
    default_code = 'invalid_order'


def _money(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def _next_number():
    last = Order.objects.aggregate(m=models.Max('number'))['m'] or 0
    return last + 1


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
    warehouse,
    fulfillment,
    payment_method,
    items,
    shipping=None,
    note='',
):
    """Crea un pedido PENDIENTE y descuenta inventario del punto elegido.

    `items`: [{variant, quantity}]. `shipping`: dict con datos de envío (solo
    cuando es envío a domicilio). El pago es simulado: las formas distintas del
    efectivo contra entrega se marcan como pagadas de inmediato.
    """
    if not items:
        raise OrderError('El pedido no tiene productos.')

    shipping = shipping or {}

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

    # ---- Descuenta inventario del punto (salida = venta) ----
    # record_movement no deja la existencia en negativo: si falta stock lanza
    # InsufficientStock y la transacción completa se revierte.
    for row in line_rows:
        record_movement(
            variant=row['variant'],
            warehouse=warehouse,
            type=MovementType.EXIT,
            quantity=row['quantity'],
            reason=MovementReason.SALE,
            reference=f'Pedido #{order.number}',
            user=user,
        )

    return order


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

    for item in order.items.select_related('variant'):
        record_movement(
            variant=item.variant,
            warehouse=order.warehouse,
            type=MovementType.ADJUST_IN,
            quantity=item.quantity,
            reason=MovementReason.CORRECTION,
            reference=f'Cancelación pedido #{order.number}',
            user=user,
        )

    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.cancel_reason = reason
    order.handled_by = user
    order.save(
        update_fields=['status', 'cancelled_at', 'cancel_reason', 'handled_by', 'updated_at']
    )
    return order
