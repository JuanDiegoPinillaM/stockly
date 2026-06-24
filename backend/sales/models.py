from django.conf import settings
from django.db import models

from catalog.models import ProductVariant, TimeStampedModel
from inventory.models import Warehouse


class PaymentMethod(models.TextChoices):
    CASH = 'efectivo', 'Efectivo'
    CARD = 'tarjeta', 'Tarjeta'
    TRANSFER = 'transferencia', 'Transferencia'
    OTHER = 'otro', 'Otro'


class SaleStatus(models.TextChoices):
    COMPLETED = 'completada', 'Completada'
    VOID = 'anulada', 'Anulada'


class Sale(models.Model):
    """Una venta del POS. Inmutable salvo por la anulación.

    Al completarse descuenta inventario creando movimientos de salida (venta)
    en el kardex, así toda venta queda trazada en el inventario.
    """

    number = models.PositiveIntegerField('número', unique=True, editable=False)
    # El cliente es un usuario (clientes y usuarios son la misma entidad). Puede
    # ser nulo (venta de mostrador sin identificar).
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='purchases',
        verbose_name='cliente',
        blank=True,
        null=True,
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='bodega',
    )
    status = models.CharField(
        'estado', max_length=12, choices=SaleStatus.choices, default=SaleStatus.COMPLETED
    )

    # Totales (los precios de venta incluyen IVA; se desglosa para el recibo).
    subtotal = models.DecimalField('subtotal sin IVA', max_digits=14, decimal_places=2, default=0)
    tax_total = models.DecimalField('IVA', max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField('descuento', max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField('total', max_digits=14, decimal_places=2, default=0)
    paid = models.DecimalField('pagado', max_digits=14, decimal_places=2, default=0)
    change = models.DecimalField('cambio', max_digits=14, decimal_places=2, default=0)

    note = models.CharField('nota', max_length=255, blank=True, default='')
    receipt_email = models.EmailField('correo del recibo', blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sales',
        verbose_name='vendedor',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField('fecha', auto_now_add=True)
    voided_at = models.DateTimeField('anulada el', blank=True, null=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='voided_sales',
        verbose_name='anulada por',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'venta'
        verbose_name_plural = 'ventas'
        ordering = ['-created_at', '-id']

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f'Venta #{self.number}'


class SaleItem(models.Model):
    """Línea de una venta. Guarda copia (snapshot) de precio/nombre/costo."""

    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name='items', verbose_name='venta'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name='variante',
    )
    description = models.CharField('descripción', max_length=255)
    sku = models.CharField('SKU', max_length=64, blank=True, default='')
    quantity = models.PositiveIntegerField('cantidad')
    unit_price = models.DecimalField('precio unitario', max_digits=12, decimal_places=2)
    tax_rate = models.PositiveSmallIntegerField('IVA (%)', default=0)
    unit_cost = models.DecimalField('costo unitario', max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField('total línea', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'línea de venta'
        verbose_name_plural = 'líneas de venta'
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.description}'


class SalePayment(models.Model):
    """Pago de una venta. Una venta puede tener varios (pago dividido)."""

    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name='payments', verbose_name='venta'
    )
    method = models.CharField('forma de pago', max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField('monto', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'pago'
        verbose_name_plural = 'pagos'
        ordering = ['id']

    def __str__(self):
        return f'{self.get_method_display()}: {self.amount}'
