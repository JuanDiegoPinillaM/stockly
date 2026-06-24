"""Lógica de ventas (POS).

Una venta se registra de forma atómica: valida pagos, calcula totales (los
precios incluyen IVA, que se desglosa), descuenta inventario creando los
movimientos de salida en el kardex y guarda los pagos. La anulación devuelve
la existencia con movimientos de ajuste de entrada.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from inventory.models import MovementReason, MovementType
from inventory.services import record_movement

from .models import Sale, SaleItem, SalePayment, SaleStatus

CENTS = Decimal('0.01')


class SaleError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'No se pudo registrar la venta.'
    default_code = 'invalid_sale'


def _money(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def _next_number():
    last = Sale.objects.aggregate(m=models.Max('number'))['m'] or 0
    return last + 1


@transaction.atomic
def create_sale(
    *,
    warehouse,
    items,
    payments,
    customer=None,
    discount=Decimal('0'),
    note='',
    receipt_email='',
    user=None,
):
    """Crea una venta completada. `items`: [{variant, quantity}]. `payments`:
    [{method, amount}]. El descuento es un monto sobre el total (IVA incluido).
    """
    if not items:
        raise SaleError('La venta no tiene productos.')

    discount = _money(discount or 0)
    if discount < 0:
        raise SaleError('El descuento no puede ser negativo.')

    # ---- Construye las líneas y los totales (precio incluye IVA) ----
    gross = Decimal('0')
    subtotal = Decimal('0')
    tax_total = Decimal('0')
    line_rows = []
    for entry in items:
        variant = entry['variant']
        quantity = int(entry['quantity'])
        if quantity <= 0:
            raise SaleError('Cada producto debe tener cantidad mayor a cero.')

        unit_price = _money(variant.sale_price)
        rate = int(variant.product.tax_rate or 0)
        line_total = _money(unit_price * quantity)
        divisor = Decimal(1) + Decimal(rate) / Decimal(100)
        line_subtotal = _money(line_total / divisor) if divisor else line_total
        line_tax = _money(line_total - line_subtotal)

        gross += line_total
        subtotal += line_subtotal
        tax_total += line_tax

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

    if discount > gross:
        raise SaleError('El descuento no puede ser mayor al total.')
    total = _money(gross - discount)

    # ---- Valida los pagos ----
    if not payments:
        raise SaleError('Indica al menos una forma de pago.')
    paid = Decimal('0')
    for p in payments:
        amount = _money(p['amount'])
        if amount <= 0:
            raise SaleError('Cada pago debe ser mayor a cero.')
        paid += amount
    if paid < total:
        raise SaleError('El pago es menor al total de la venta.')
    change = _money(paid - total)

    # ---- Crea la venta ----
    sale = Sale.objects.create(
        number=_next_number(),
        customer=customer,
        warehouse=warehouse,
        status=SaleStatus.COMPLETED,
        subtotal=subtotal,
        tax_total=tax_total,
        discount=discount,
        total=total,
        paid=paid,
        change=change,
        note=note,
        receipt_email=receipt_email,
        created_by=user,
    )
    SaleItem.objects.bulk_create(
        [SaleItem(sale=sale, **row) for row in line_rows]
    )
    SalePayment.objects.bulk_create(
        [
            SalePayment(sale=sale, method=p['method'], amount=_money(p['amount']))
            for p in payments
        ]
    )

    # ---- Descuenta inventario (movimientos de salida = venta) ----
    for row in line_rows:
        record_movement(
            variant=row['variant'],
            warehouse=warehouse,
            type=MovementType.EXIT,
            quantity=row['quantity'],
            reason=MovementReason.SALE,
            reference=f'Venta #{sale.number}',
            user=user,
        )

    return sale


@transaction.atomic
def void_sale(sale, *, user=None):
    """Anula una venta y devuelve la existencia con ajustes de entrada."""
    if sale.status == SaleStatus.VOID:
        raise SaleError('La venta ya está anulada.')

    for item in sale.items.select_related('variant').all():
        record_movement(
            variant=item.variant,
            warehouse=sale.warehouse,
            type=MovementType.ADJUST_IN,
            quantity=item.quantity,
            reason=MovementReason.CORRECTION,
            reference=f'Anulación venta #{sale.number}',
            user=user,
        )

    sale.status = SaleStatus.VOID
    sale.voided_at = timezone.now()
    sale.voided_by = user
    sale.save(update_fields=['status', 'voided_at', 'voided_by'])
    return sale
