from django.conf import settings
from django.db import models

from catalog.models import TimeStampedModel


class Address(TimeStampedModel):
    """Dirección de envío/facturación de un comprador."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='usuario',
    )
    label = models.CharField('etiqueta', max_length=60, blank=True, default='')
    recipient = models.CharField('destinatario', max_length=160)
    phone = models.CharField('teléfono', max_length=40, blank=True, default='')
    line1 = models.CharField('dirección', max_length=200)
    # Ubicación relacional (país → departamento → ciudad).
    country = models.ForeignKey(
        'geo.Country', on_delete=models.PROTECT, related_name='addresses',
        verbose_name='país', blank=True, null=True,
    )
    department = models.ForeignKey(
        'geo.Department', on_delete=models.PROTECT, related_name='addresses',
        verbose_name='departamento', blank=True, null=True,
    )
    city = models.ForeignKey(
        'geo.City', on_delete=models.PROTECT, related_name='addresses',
        verbose_name='ciudad', blank=True, null=True,
    )
    notes = models.CharField('indicaciones', max_length=255, blank=True, default='')
    is_default = models.BooleanField('predeterminada', default=False)
    # Coordenadas (geocodificadas de la dirección) para rutear al punto más
    # cercano. Pueden ser nulas si la geocodificación no las resolvió.
    latitude = models.DecimalField(
        'latitud', max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        'longitud', max_digits=9, decimal_places=6, blank=True, null=True
    )

    class Meta:
        verbose_name = 'dirección'
        verbose_name_plural = 'direcciones'
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f'{self.label or self.recipient} — {self.line1}'


class SavedPaymentMethod(TimeStampedModel):
    """Método de pago guardado por el comprador (solo referencia, sin datos
    sensibles: no se almacenan números de tarjeta)."""

    class Kind(models.TextChoices):
        CARD = 'tarjeta', 'Tarjeta'
        NEQUI = 'nequi', 'Nequi'
        TRANSFER = 'transferencia', 'Transferencia'
        CASH = 'efectivo', 'Efectivo contra entrega'
        OTHER = 'otro', 'Otro'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name='usuario',
    )
    kind = models.CharField('tipo', max_length=20, choices=Kind.choices)
    label = models.CharField('alias', max_length=80)
    is_default = models.BooleanField('predeterminado', default=False)

    class Meta:
        verbose_name = 'método de pago'
        verbose_name_plural = 'métodos de pago'
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f'{self.get_kind_display()} · {self.label}'


class CartItem(TimeStampedModel):
    """Línea del carrito de un comprador, persistida en el servidor.

    Así el carrito sigue a la cuenta (no al navegador): si inicias sesión en otro
    dispositivo ves tu mismo carrito. Un visitante sin sesión usa el carrito local
    del navegador; al iniciar sesión se fusiona aquí.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='usuario',
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='variante',
    )
    quantity = models.PositiveIntegerField('cantidad', default=1)

    class Meta:
        verbose_name = 'ítem de carrito'
        verbose_name_plural = 'ítems de carrito'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'variant'], name='unique_cart_variant_per_user'
            )
        ]

    def __str__(self):
        return f'{self.quantity} × {self.variant} ({self.user})'


class WishlistItem(TimeStampedModel):
    """Favorito de un comprador, persistido por cuenta (como el carrito).

    Guarda el producto y, si aplica, el valor del eje de fotos (color) elegido,
    para reflejar la misma tarjeta del catálogo. Un visitante sin sesión usa los
    favoritos locales del navegador; al iniciar sesión se fusionan aquí.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='usuario',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='producto',
    )
    # Color (valor del eje de fotos) marcado, o nulo si el producto no tiene eje.
    value = models.ForeignKey(
        'catalog.AttributeValue',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='color',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'favorito'
        verbose_name_plural = 'favoritos'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product', 'value'], name='unique_wishlist_item'
            )
        ]

    def __str__(self):
        return f'{self.user} ♥ {self.product}'


class Order(TimeStampedModel):
    """Pedido en línea de un comprador (compra desde la tienda pública).

    A diferencia de la venta del POS (inmediata e inmutable), el pedido tiene un
    ciclo de vida: nace PENDIENTE, el personal lo confirma, lo despacha y lo
    entrega (o se cancela). Al crearse descuenta inventario del punto que eligió
    el comprador (movimientos de salida = venta), igual que una venta; al
    cancelarse devuelve la existencia con ajustes de entrada. Nada se borra:
    el pedido queda como registro con todo su historial.
    """

    class Status(models.TextChoices):
        PENDING = 'pendiente', 'Pendiente'
        CONFIRMED = 'confirmado', 'Confirmado'
        SHIPPED = 'enviado', 'Enviado'
        DELIVERED = 'entregado', 'Entregado'
        CANCELLED = 'cancelado', 'Cancelado'

    class Fulfillment(models.TextChoices):
        DELIVERY = 'envio', 'Envío a domicilio'
        PICKUP = 'recoge', 'Recoge en el punto'

    class Payment(models.TextChoices):
        CARD = 'tarjeta', 'Tarjeta'
        NEQUI = 'nequi', 'Nequi'
        TRANSFER = 'transferencia', 'Transferencia'
        CASH = 'efectivo', 'Efectivo contra entrega'

    number = models.PositiveIntegerField('número', unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='comprador',
    )
    # Punto (bodega) que surte el pedido; lo elige el comprador en el checkout.
    warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='punto',
    )
    status = models.CharField(
        'estado', max_length=12, choices=Status.choices, default=Status.PENDING
    )
    fulfillment = models.CharField(
        'entrega', max_length=10, choices=Fulfillment.choices, default=Fulfillment.DELIVERY
    )
    payment_method = models.CharField('forma de pago', max_length=20, choices=Payment.choices)
    # Pago simulado: las formas distintas de "contra entrega" se marcan pagadas al
    # crear el pedido; el efectivo contra entrega se paga al entregar.
    is_paid = models.BooleanField('pagado', default=False)

    # Totales (los precios de venta incluyen IVA; se desglosa para el detalle).
    subtotal = models.DecimalField('subtotal sin IVA', max_digits=14, decimal_places=2, default=0)
    tax_total = models.DecimalField('IVA', max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField('total', max_digits=14, decimal_places=2, default=0)

    # Datos de envío: copia (snapshot) de la dirección al momento de la compra,
    # así editar/eliminar la dirección no altera el pedido. Vacíos si recoge.
    ship_recipient = models.CharField('destinatario', max_length=160, blank=True, default='')
    ship_phone = models.CharField('teléfono', max_length=40, blank=True, default='')
    # Teléfono secundario: el de la cuenta del comprador (respaldo de contacto).
    ship_phone_alt = models.CharField('teléfono secundario', max_length=40, blank=True, default='')
    ship_line1 = models.CharField('dirección', max_length=200, blank=True, default='')
    ship_city = models.CharField('ciudad', max_length=120, blank=True, default='')
    ship_department = models.CharField('departamento', max_length=120, blank=True, default='')
    ship_country = models.CharField('país', max_length=120, blank=True, default='')
    ship_notes = models.CharField('indicaciones', max_length=255, blank=True, default='')

    note = models.CharField('nota del comprador', max_length=255, blank=True, default='')
    cancel_reason = models.CharField('motivo de cancelación', max_length=255, blank=True, default='')

    # Marcas de tiempo del flujo.
    confirmed_at = models.DateTimeField('confirmado el', blank=True, null=True)
    shipped_at = models.DateTimeField('enviado el', blank=True, null=True)
    delivered_at = models.DateTimeField('entregado el', blank=True, null=True)
    cancelled_at = models.DateTimeField('cancelado el', blank=True, null=True)

    # Último miembro del personal que avanzó/resolvió el pedido.
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='handled_orders',
        verbose_name='gestionado por',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'
        ordering = ['-created_at', '-id']

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def is_open(self):
        """True si el pedido aún puede avanzar o cancelarse."""
        return self.status not in (self.Status.DELIVERED, self.Status.CANCELLED)

    @property
    def code(self):
        """Identificador legible e inequívoco del pedido (P-0001).

        El prefijo evita la ambigüedad con las ventas (V-0001): un pedido es el
        documento comercial; al entregarse genera su venta (ver sales.Sale).
        """
        return f'P-{self.number:04d}'

    def __str__(self):
        return f'Pedido {self.code}'


class OrderItem(models.Model):
    """Línea de un pedido. Guarda copia (snapshot) de precio/nombre/costo."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items', verbose_name='pedido'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,
        related_name='order_items',
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
        verbose_name = 'línea de pedido'
        verbose_name_plural = 'líneas de pedido'
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.description}'


class OrderAllocation(models.Model):
    """Reparto del pedido entre bodegas (fulfillment dividido).

    Indica de qué bodega salen cuántas unidades de cada variante. Es lo que
    mueve el inventario: un pedido puede surtirse desde varias sedes, así no se
    pierde una venta porque ninguna tienda sola lo tenga todo. La suma de las
    asignaciones de una variante es igual a la cantidad pedida de esa variante.
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='allocations', verbose_name='pedido'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,
        related_name='order_allocations',
        verbose_name='variante',
    )
    warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.PROTECT,
        related_name='order_allocations',
        verbose_name='bodega',
    )
    quantity = models.PositiveIntegerField('cantidad')
    unit_cost = models.DecimalField('costo unitario', max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'asignación de pedido'
        verbose_name_plural = 'asignaciones de pedido'
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.variant} @ {self.warehouse}'
