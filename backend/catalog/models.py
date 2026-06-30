from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

from config.uploads import UploadToUUID

hex_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$',
    message='Usa un color HEX válido, p. ej. #1A2B3C.',
)


class Color(models.Model):
    """Color reutilizable del catálogo: un nombre y su valor HEX."""

    name = models.CharField('nombre', max_length=60, unique=True)
    hex_code = models.CharField('HEX', max_length=7, validators=[hex_validator])
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'color'
        verbose_name_plural = 'colores'
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Normaliza el HEX a mayúsculas para consistencia.
        if self.hex_code:
            self.hex_code = self.hex_code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.hex_code})'


class Size(models.Model):
    """Talla reutilizable (XS, S, M, L…). `position` define el orden."""

    name = models.CharField('nombre', max_length=20, unique=True)
    position = models.PositiveIntegerField('orden', default=0)
    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'talla'
        verbose_name_plural = 'tallas'
        ordering = ['position', 'name']

    def __str__(self):
        return self.name


class AttributeDefinition(models.Model):
    """Atributo reutilizable del catálogo (Color, Talla, Almacenamiento, RAM…).

    Define un "tipo de opción" que cualquier producto puede reusar para sus
    variantes. `has_swatch` indica que sus opciones llevan un color HEX (como
    Color). Las opciones viven en `AttributeOption`.
    """

    name = models.CharField('nombre', max_length=60, unique=True)
    has_swatch = models.BooleanField('usa color', default=False)
    position = models.PositiveIntegerField('orden', default=0)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'atributo del catálogo'
        verbose_name_plural = 'atributos del catálogo'
        ordering = ['position', 'name']

    def __str__(self):
        return self.name


class AttributeOption(models.Model):
    """Opción reutilizable de un atributo del catálogo (Rojo, M, 256GB…)."""

    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='atributo',
    )
    value = models.CharField('valor', max_length=80)
    swatch_hex = models.CharField('HEX', max_length=7, blank=True, default='')
    position = models.PositiveIntegerField('orden', default=0)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'opción de atributo'
        verbose_name_plural = 'opciones de atributo'
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['definition', 'value'], name='unique_option_per_definition'
            )
        ]

    def save(self, *args, **kwargs):
        if self.swatch_hex:
            self.swatch_hex = self.swatch_hex.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.definition.name}: {self.value}'


class Brand(models.Model):
    """Marca reutilizable del catálogo (Nike, Coca-Cola, genérica…)."""

    name = models.CharField('nombre', max_length=80, unique=True)
    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'marca'
        verbose_name_plural = 'marcas'
        ordering = ['name']

    def __str__(self):
        return self.name


class UnitOfMeasure(models.TextChoices):
    """Unidad en la que se vende/almacena el producto."""

    UNIT = 'unidad', 'Unidad'
    KG = 'kg', 'Kilogramo'
    G = 'g', 'Gramo'
    LB = 'lb', 'Libra'
    L = 'l', 'Litro'
    ML = 'ml', 'Mililitro'
    PACK = 'paquete', 'Paquete'
    BOX = 'caja', 'Caja'
    DOZEN = 'docena', 'Docena'


class TaxRate(models.IntegerChoices):
    """IVA aplicable en Colombia."""

    IVA_19 = 19, 'IVA 19%'
    IVA_5 = 5, 'IVA 5%'
    EXEMPT = 0, 'Excluido / 0%'


class TimeStampedModel(models.Model):
    """Base abstracta con marcas de tiempo reutilizable por el catálogo."""

    created_at = models.DateTimeField('creado', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    """Categoría de primer nivel (p. ej. 'Ropa', 'Alimentos')."""

    name = models.CharField('nombre', max_length=120, unique=True)
    slug = models.SlugField('slug', max_length=140, unique=True, blank=True)
    description = models.TextField('descripción', blank=True)
    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Subcategory(TimeStampedModel):
    """Subcategoría que cuelga de una categoría. Un producto se asigna aquí."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name='categoría',
    )
    name = models.CharField('nombre', max_length=120)
    slug = models.SlugField('slug', max_length=140, blank=True)
    description = models.TextField('descripción', blank=True)
    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'subcategoría'
        verbose_name_plural = 'subcategorías'
        ordering = ['category__name', 'name']
        # El nombre de la subcategoría es único dentro de su categoría.
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'],
                name='unique_subcategory_name_per_category',
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Subcategory, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.category.name} › {self.name}'


class Product(TimeStampedModel):
    """Producto del catálogo. La categoría se deriva de la subcategoría."""

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='subcategoría',
    )
    name = models.CharField('nombre', max_length=200)
    slug = models.SlugField('slug', max_length=220, blank=True)
    description = models.TextField('descripción', blank=True)

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name='products',
        verbose_name='marca',
        blank=True,
        null=True,
    )
    # Cómo se mide/vende el producto (unidad, kg, litro…).
    unit_of_measure = models.CharField(
        'unidad de medida',
        max_length=10,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.UNIT,
    )
    # IVA aplicable (para precio final y futura factura electrónica).
    tax_rate = models.PositiveSmallIntegerField(
        'IVA (%)', choices=TaxRate.choices, default=TaxRate.IVA_19
    )

    expiration_date = models.DateField('fecha de vencimiento', blank=True, null=True)

    is_active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['name']

    @property
    def category(self):
        """Categoría derivada de la subcategoría (sin almacenar duplicado)."""
        return self.subcategory.category

    @property
    def main_image(self):
        """Portada del producto: la primera imagen de su galería."""
        return self.images.first()

    def _active_variants(self):
        # Usa el caché de prefetch_related si está disponible.
        return [v for v in self.variants.all() if v.is_active]

    @property
    def total_stock(self):
        """Suma de existencias de las variantes activas."""
        return sum(v.stock for v in self._active_variants())

    @property
    def price_min(self):
        prices = [v.sale_price for v in self._active_variants()]
        return min(prices) if prices else None

    @property
    def price_max(self):
        prices = [v.sale_price for v in self._active_variants()]
        return max(prices) if prices else None

    @property
    def has_low_stock(self):
        """True si alguna variante activa está en/por debajo de su reorden."""
        return any(v.is_low_stock for v in self._active_variants())

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    """Atributo de variación de un producto (p. ej. 'Color', 'Talla',
    'Almacenamiento'). Cada producto define los suyos (sistema flexible: sirve
    para ropa, electrónica o cualquier cosa).

    Exactamente uno puede marcarse como `is_image_axis`: es el eje "visual"
    cuyas opciones tienen fotos propias (normalmente el color). Los demás ejes
    solo afectan SKU/precio/stock, no las fotos.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='attributes', verbose_name='producto'
    )
    # Atributo del catálogo del que proviene (Color, Talla…). Permite saber qué
    # opciones ofrecer y si usa color. Nulo si fue un atributo ad-hoc.
    definition = models.ForeignKey(
        AttributeDefinition,
        on_delete=models.SET_NULL,
        related_name='product_attributes',
        verbose_name='atributo del catálogo',
        blank=True,
        null=True,
    )
    name = models.CharField('nombre', max_length=60)
    position = models.PositiveIntegerField('orden', default=0)
    is_image_axis = models.BooleanField('eje de las fotos', default=False)

    class Meta:
        verbose_name = 'atributo de producto'
        verbose_name_plural = 'atributos de producto'
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'name'], name='unique_attribute_name_per_product'
            )
        ]

    @property
    def ordered_values(self):
        """Valores de este atributo en el orden GLOBAL del catálogo.

        Si el atributo proviene de una definición del catálogo (Color, Talla…),
        sus valores se ordenan según la posición de la opción equivalente en el
        catálogo (AttributeOption.position) — así el orden que se fija una vez en
        Atributos (S, M, L, XL) se respeta en la tienda, el POS y todo el sitio.
        Los valores sin opción equivalente van al final, por su propio orden.
        """
        values = list(self.values.all())
        if not self.definition_id:
            return values
        pos = {o.value.lower(): o.position for o in self.definition.options.all()}
        fallback = (max(pos.values()) + 1) if pos else 0
        return sorted(
            values,
            key=lambda v: (pos.get(v.value.lower(), fallback), v.position, v.id),
        )

    def __str__(self):
        return f'{self.product.name} · {self.name}'


class AttributeValue(models.Model):
    """Valor posible de un atributo (p. ej. 'Rojo', 'M', '256GB')."""

    attribute = models.ForeignKey(
        ProductAttribute, on_delete=models.CASCADE, related_name='values', verbose_name='atributo'
    )
    value = models.CharField('valor', max_length=80)
    # HEX opcional para mostrar un swatch (solo tiene sentido en el eje de color).
    swatch_hex = models.CharField('HEX', max_length=7, blank=True, default='')
    position = models.PositiveIntegerField('orden', default=0)

    class Meta:
        verbose_name = 'valor de atributo'
        verbose_name_plural = 'valores de atributo'
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['attribute', 'value'], name='unique_value_per_attribute'
            )
        ]

    def save(self, *args, **kwargs):
        if self.swatch_hex:
            self.swatch_hex = self.swatch_hex.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'


class ProductVariant(TimeStampedModel):
    """Combinación concreta y vendible de un producto (p. ej. Roja / Talla M).

    El inventario vive aquí: SKU, código de barras, precios y existencias son
    propios de cada variante. Todo producto tiene al menos una variante; un
    producto sin opciones reales es una sola variante con color/talla nulos.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='producto',
    )
    sku = models.CharField('SKU', max_length=64, unique=True)
    barcode = models.CharField(
        'código de barras', max_length=14, blank=True, default=''
    )

    cost_price = models.DecimalField(
        'precio de costo de referencia', max_digits=12, decimal_places=2, default=0
    )
    sale_price = models.DecimalField(
        'precio de venta', max_digits=12, decimal_places=2, default=0
    )
    # Costo promedio ponderado real, calculado por el módulo de inventario a
    # partir de las entradas. Es el costo usado para valorar el inventario.
    average_cost = models.DecimalField(
        'costo promedio', max_digits=12, decimal_places=2, default=0
    )

    # Existencias TOTALES (caché): suma de los StockLevel por bodega. Solo lo
    # actualizan los movimientos de inventario, nunca a mano.
    stock = models.PositiveIntegerField('existencias', default=0)
    # Umbral de reorden: por debajo de esto la variante está en bajo stock.
    min_stock = models.PositiveIntegerField('stock mínimo', default=0)

    # La combinación de la variante (color=Rojo, talla=M, …) se define con
    # `VariantValue` (un valor por atributo del producto). Una variante sin
    # atributos es el producto "simple" (una sola variante).

    is_active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'variante de producto'
        verbose_name_plural = 'variantes de producto'
        ordering = ['product', 'id']
        constraints = [
            # El código de barras es único cuando se especifica (los vacíos no chocan).
            models.UniqueConstraint(
                fields=['barcode'],
                condition=models.Q(barcode__gt=''),
                name='unique_barcode_when_set',
            ),
        ]

    @property
    def effective_cost(self):
        """Costo real para valorar y calcular margen: el promedio ponderado.

        Si la variante aún no tiene entradas (promedio en 0), cae al costo de
        referencia que se capturó al crearla.
        """
        return self.average_cost or self.cost_price

    @property
    def selected_values(self):
        """Valores de la variante ordenados por el orden de su atributo."""
        return sorted(
            (vv.value for vv in self.values.all()),
            key=lambda v: (v.attribute.position, v.position, v.id),
        )

    @property
    def options_label(self):
        """Etiqueta legible de la combinación (p. ej. 'Rojo / M')."""
        return ' / '.join(v.value for v in self.selected_values)

    @property
    def image_value(self):
        """El valor de la variante en el eje visual (el de las fotos), o None."""
        for vv in self.values.all():
            if vv.value.attribute.is_image_axis:
                return vv.value
        return None

    @property
    def gallery(self):
        """Galería de la variante: las fotos de su valor visual; si no hay, las
        fotos generales del producto (sin valor)."""
        iv = self.image_value
        if iv is not None:
            imgs = list(iv.images.all())
            if imgs:
                return imgs
        return list(self.product.images.all())

    @property
    def main_image(self):
        """Portada de la variante: la primera de su galería."""
        gallery = self.gallery
        return gallery[0] if gallery else None

    @property
    def profit_margin(self):
        """Ganancia por unidad (venta − costo real)."""
        return self.sale_price - self.effective_cost

    @property
    def stock_value(self):
        """Valor del inventario de esta variante: existencias × costo real."""
        return self.stock * self.effective_cost

    @property
    def is_low_stock(self):
        """True si las existencias están en/por debajo del umbral de reorden."""
        return self.stock <= self.min_stock

    def __str__(self):
        opts = self.options_label
        return f'{self.product.name}' + (f' — {opts}' if opts else '')


class VariantValue(models.Model):
    """Enlaza una variante con uno de los valores de un atributo del producto.

    Una variante tiene un `VariantValue` por cada atributo del producto; el
    conjunto define su combinación única.
    """

    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name='values', verbose_name='variante'
    )
    value = models.ForeignKey(
        AttributeValue, on_delete=models.PROTECT, related_name='variant_values', verbose_name='valor'
    )

    class Meta:
        verbose_name = 'valor de variante'
        verbose_name_plural = 'valores de variante'
        constraints = [
            models.UniqueConstraint(
                fields=['variant', 'value'], name='unique_value_per_variant'
            )
        ]

    def __str__(self):
        return f'{self.variant_id} → {self.value}'


class ProductImage(models.Model):
    """Imagen de la galería de un producto, opcionalmente asociada al valor del
    eje visual (p. ej. las fotos del 'Rojo'). Si `value` es nulo, son fotos
    generales que aplican a todo el producto.

    Las fotos viven a este nivel (producto + valor), NO por variante: así
    agregar otra talla del mismo color reutiliza las fotos sin recargarlas.
    """

    MAX_PER_GROUP = 8

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images', verbose_name='producto'
    )
    value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='valor (eje visual)',
        blank=True,
        null=True,
    )
    image = models.ImageField('imagen', upload_to=UploadToUUID('products'))
    alt_text = models.CharField('texto alternativo', max_length=160, blank=True)
    position = models.PositiveIntegerField('orden', default=0)

    class Meta:
        verbose_name = 'imagen de producto'
        verbose_name_plural = 'imágenes de producto'
        ordering = ['position', 'id']

    def __str__(self):
        return f'Imagen de {self.product.name}'


def _unique_slug(model, value, pk):
    """Genera un slug único para el modelo, ignorando la propia instancia."""
    base = slugify(value) or 'item'
    slug = base
    counter = 2
    queryset = model.objects.exclude(pk=pk) if pk else model.objects.all()
    while queryset.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug
