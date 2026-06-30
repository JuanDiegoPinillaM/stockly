"""Respaldo: genera la venta de los pedidos ya entregados.

Con el modelo "un pedido culmina en una venta", cada pedido entregado debe tener
su venta (canal online) en el libro de ventas. Los pedidos entregados ANTES de
este cambio aún no la tienen; esta migración la crea para ellos, con la misma
fecha del pedido (el evento económico real) y sin tocar inventario (el pedido ya
lo descontó al crearse).
"""
from decimal import Decimal

from django.db import migrations

# Forma de pago del pedido → forma de pago de la venta (sin "nequi" en la venta).
_PAYMENT_MAP = {
    'tarjeta': 'tarjeta',
    'nequi': 'transferencia',
    'transferencia': 'transferencia',
    'efectivo': 'efectivo',
}


def backfill(apps, schema_editor):
    Order = apps.get_model('store', 'Order')
    Sale = apps.get_model('sales', 'Sale')
    SaleItem = apps.get_model('sales', 'SaleItem')
    SalePayment = apps.get_model('sales', 'SalePayment')

    delivered = (
        Order.objects.filter(status='entregado', sale__isnull=True)
        .order_by('created_at', 'id')
    )
    last = Sale.objects.order_by('-number').values_list('number', flat=True).first() or 0

    for order in delivered:
        last += 1
        sale = Sale.objects.create(
            number=last,
            channel='online',
            order=order,
            customer_id=order.user_id,
            warehouse_id=order.warehouse_id,
            status='completada',
            subtotal=order.subtotal,
            tax_total=order.tax_total,
            discount=Decimal('0'),
            total=order.total,
            paid=order.total,
            change=Decimal('0'),
            note=f'Pedido P-{order.number:04d}',
            receipt_email=(order.user.email or '') if order.user_id else '',
            created_by_id=order.handled_by_id,
        )
        # created_at es auto_now_add: se fija con update() para conservar la
        # fecha del pedido (evento económico) y no la de la migración.
        Sale.objects.filter(pk=sale.pk).update(created_at=order.created_at)

        SaleItem.objects.bulk_create([
            SaleItem(
                sale=sale,
                variant_id=item.variant_id,
                description=item.description,
                sku=item.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                unit_cost=item.unit_cost,
                line_total=item.line_total,
            )
            for item in order.items.all()
        ])
        SalePayment.objects.create(
            sale=sale,
            method=_PAYMENT_MAP.get(order.payment_method, 'otro'),
            amount=order.total,
        )


def unbackfill(apps, schema_editor):
    Sale = apps.get_model('sales', 'Sale')
    # Borra solo las ventas generadas a partir de un pedido.
    Sale.objects.filter(channel='online', order__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0003_sale_channel_sale_order'),
        ('store', '0002_order_orderitem'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
