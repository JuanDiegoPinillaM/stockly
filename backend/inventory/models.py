from django.conf import settings
from django.db import models

from catalog.models import ProductVariant, TimeStampedModel


class Warehouse(TimeStampedModel):
    """Bodega o almacén donde se guarda existencia (multi-ubicación)."""

    name = models.CharField('nombre', max_length=120, unique=True)
    code = models.CharField('código', max_length=20, blank=True, default='')
    address = models.CharField('dirección', max_length=200, blank=True, default='')
    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'bodega'
        verbose_name_plural = 'bodegas'
        ordering = ['name']

    def __str__(self):
        return self.name


class StockLevel(models.Model):
    """Existencia de una variante en una bodega concreta.

    Es el saldo por (variante × bodega). Solo lo mueven los StockMovement.
    """

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='stock_levels',
        verbose_name='variante',
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_levels',
        verbose_name='bodega',
    )
    quantity = models.PositiveIntegerField('existencias', default=0)

    class Meta:
        verbose_name = 'existencia por bodega'
        verbose_name_plural = 'existencias por bodega'
        ordering = ['warehouse__name']
        constraints = [
            models.UniqueConstraint(
                fields=['variant', 'warehouse'],
                name='unique_variant_per_warehouse',
            )
        ]

    def __str__(self):
        return f'{self.variant} @ {self.warehouse} = {self.quantity}'


class MovementType(models.TextChoices):
    """Tipo de movimiento de inventario."""

    ENTRY = 'entrada', 'Entrada'
    EXIT = 'salida', 'Salida'
    ADJUST_IN = 'ajuste_entrada', 'Ajuste (entrada)'
    ADJUST_OUT = 'ajuste_salida', 'Ajuste (salida)'
    TRANSFER = 'transferencia', 'Transferencia'


class MovementReason(models.TextChoices):
    """Motivo del movimiento (sobre todo para ajustes)."""

    PURCHASE = 'compra', 'Compra'
    SALE = 'venta', 'Venta'
    INITIAL = 'saldo_inicial', 'Saldo inicial'
    COUNT = 'conteo_fisico', 'Conteo físico'
    DAMAGE = 'merma_dano', 'Merma / daño'
    EXPIRY = 'vencimiento', 'Vencimiento'
    THEFT = 'robo_perdida', 'Robo / pérdida'
    TRANSFER = 'transferencia', 'Transferencia'
    CORRECTION = 'correccion', 'Corrección'
    OTHER = 'otro', 'Otro'


# Tipos que suman / restan existencia.
INBOUND_TYPES = {MovementType.ENTRY, MovementType.ADJUST_IN}
OUTBOUND_TYPES = {MovementType.EXIT, MovementType.ADJUST_OUT}


class StockMovement(models.Model):
    """Asiento inmutable del kardex: cada entrada/salida/ajuste/transferencia.

    No se edita ni se borra; las correcciones se hacen con nuevos movimientos.
    Cada asiento guarda el saldo resultante de su bodega (`balance_after`) para
    reconstruir el kardex sin recalcular.
    """

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='variante',
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='bodega',
    )
    # Solo en transferencias: bodega destino (este asiento es la salida origen).
    warehouse_to = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name='bodega destino',
        blank=True,
        null=True,
    )

    type = models.CharField('tipo', max_length=20, choices=MovementType.choices)
    reason = models.CharField(
        'motivo', max_length=20, choices=MovementReason.choices, blank=True, default=''
    )
    quantity = models.PositiveIntegerField('cantidad')

    # Costo unitario del asiento y su total. En entradas lo fija el usuario; en
    # salidas/ajustes/transferencias se toma el costo promedio vigente.
    unit_cost = models.DecimalField(
        'costo unitario', max_digits=12, decimal_places=2, default=0
    )
    total_cost = models.DecimalField(
        'costo total', max_digits=14, decimal_places=2, default=0
    )
    # Existencia de la variante en su bodega tras aplicar el movimiento.
    balance_after = models.PositiveIntegerField('saldo resultante', default=0)

    note = models.CharField('nota', max_length=255, blank=True, default='')
    reference = models.CharField('referencia', max_length=64, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='stock_movements',
        verbose_name='registrado por',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField('fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'movimiento de inventario'
        verbose_name_plural = 'movimientos de inventario'
        ordering = ['-created_at', '-id']

    @property
    def is_inbound(self):
        """True si el asiento SUMA existencia en su bodega.

        En una transferencia hay dos asientos: el de origen lleva `warehouse_to`
        (es la salida, resta) y el de destino no lo lleva (es la entrada, suma).
        """
        if self.type == MovementType.TRANSFER:
            return self.warehouse_to_id is None
        return self.type in INBOUND_TYPES

    @property
    def signed_quantity(self):
        """Cantidad con signo según la dirección (+ entra, − sale)."""
        return self.quantity if self.is_inbound else -self.quantity

    def __str__(self):
        return f'{self.get_type_display()} {self.quantity} · {self.variant}'


class TransferStatus(models.TextChoices):
    """Estado de una transferencia entre puntos (flujo con aprobación)."""

    PENDING = 'pendiente', 'Pendiente'
    ACCEPTED = 'aceptada', 'Aceptada'
    REJECTED = 'rechazada', 'Rechazada'
    CANCELLED = 'cancelada', 'Cancelada'


class Transfer(TimeStampedModel):
    """Solicitud de traslado de existencia entre dos bodegas/puntos.

    Al solicitarla, la existencia SALE de la bodega origen (queda en tránsito).
    El jefe del punto destino la acepta (entra al destino) o la rechaza (vuelve
    a origen); el solicitante puede cancelarla mientras esté pendiente.
    """

    number = models.PositiveIntegerField('número', unique=True)
    origin = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='transfers_out',
        verbose_name='bodega origen',
    )
    destination = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='transfers_in',
        verbose_name='bodega destino',
    )
    status = models.CharField(
        'estado', max_length=12, choices=TransferStatus.choices,
        default=TransferStatus.PENDING,
    )
    note = models.CharField('nota', max_length=255, blank=True, default='')

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='transfers_requested',
        verbose_name='solicitada por',
        blank=True,
        null=True,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='transfers_resolved',
        verbose_name='resuelta por',
        blank=True,
        null=True,
    )
    resolved_at = models.DateTimeField('fecha de resolución', blank=True, null=True)

    class Meta:
        verbose_name = 'transferencia'
        verbose_name_plural = 'transferencias'
        ordering = ['-created_at', '-id']

    @property
    def is_pending(self):
        return self.status == TransferStatus.PENDING

    def __str__(self):
        return f'Transferencia #{self.number} {self.origin} → {self.destination}'


class TransferItem(models.Model):
    """Línea de una transferencia: una variante y su cantidad (con costo fijado
    al momento de reservar, ya que el traslado no cambia el costo)."""

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='transferencia',
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name='transfer_items',
        verbose_name='variante',
    )
    quantity = models.PositiveIntegerField('cantidad')
    unit_cost = models.DecimalField(
        'costo unitario', max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = 'línea de transferencia'
        verbose_name_plural = 'líneas de transferencia'
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.variant} (transf. #{self.transfer_id})'
