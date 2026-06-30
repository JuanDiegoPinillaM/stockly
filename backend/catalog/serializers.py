from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    AttributeDefinition,
    AttributeOption,
    AttributeValue,
    Brand,
    Category,
    Color,
    Product,
    ProductAttribute,
    ProductImage,
    ProductVariant,
    Size,
    Subcategory,
    VariantValue,
)


class AttributeOptionSerializer(serializers.ModelSerializer):
    """Opción reutilizable de un atributo del catálogo (Rojo, M, 256GB…)."""

    class Meta:
        model = AttributeOption
        fields = ['id', 'definition', 'value', 'swatch_hex', 'position', 'is_active']
        read_only_fields = ['id']
        # `definition` solo es obligatorio al crear suelto (no anidado).
        extra_kwargs = {'definition': {'required': False}}


class AttributeDefinitionSerializer(serializers.ModelSerializer):
    """Atributo del catálogo (Color, Talla, Almacenamiento…) con sus opciones."""

    options = AttributeOptionSerializer(many=True, read_only=True)
    products_count = serializers.IntegerField(
        source='product_attributes.count', read_only=True
    )

    class Meta:
        model = AttributeDefinition
        fields = [
            'id', 'name', 'has_swatch', 'position', 'is_active',
            'options', 'products_count',
        ]
        read_only_fields = ['id']


class ColorSerializer(serializers.ModelSerializer):
    """Color de la librería reutilizable (sugerencias para el eje de color)."""

    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code', 'is_active']
        read_only_fields = ['id']


class SizeSerializer(serializers.ModelSerializer):
    """Talla de la librería reutilizable (sugerencias para tallas)."""

    class Meta:
        model = Size
        fields = ['id', 'name', 'position', 'is_active']
        read_only_fields = ['id']


class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Brand
        fields = ['id', 'name', 'is_active', 'products_count']
        read_only_fields = ['id']


class SubcategorySerializer(serializers.ModelSerializer):
    """Subcategoría con el nombre de su categoría para listados cómodos."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Subcategory
        fields = [
            'id', 'category', 'category_name', 'name', 'slug',
            'description', 'is_active', 'products_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    """Categoría con sus subcategorías anidadas (solo lectura)."""

    subcategories = SubcategorySerializer(many=True, read_only=True)
    subcategories_count = serializers.IntegerField(
        source='subcategories.count', read_only=True
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'is_active',
            'subcategories', 'subcategories_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'alt_text', 'position', 'value']
        read_only_fields = ['id', 'position']


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'attribute', 'value', 'swatch_hex', 'position']
        read_only_fields = ['id']
        # `attribute` solo es obligatorio al crear suelto (no anidado).
        extra_kwargs = {'attribute': {'required': False}}


class ProductAttributeSerializer(serializers.ModelSerializer):
    # Valores en el orden GLOBAL del catálogo (ver ProductAttribute.ordered_values).
    values = AttributeValueSerializer(source='ordered_values', many=True, read_only=True)
    # ¿Sus opciones usan color? (heredado del atributo del catálogo).
    has_swatch = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_swatch(self, obj):
        return bool(obj.definition and obj.definition.has_swatch)

    class Meta:
        model = ProductAttribute
        fields = [
            'id', 'product', 'definition', 'has_swatch',
            'name', 'position', 'is_image_axis', 'values',
        ]
        read_only_fields = ['id']
        extra_kwargs = {'definition': {'required': False}}


class ImageReorderSerializer(serializers.Serializer):
    """Recibe el nuevo orden de la galería como lista de IDs de imagen."""

    order = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='IDs de las imágenes en el orden deseado.',
    )


class ProductVariantSerializer(serializers.ModelSerializer):
    """Variante vendible: dueña del SKU, código de barras, precios y stock.

    Su combinación se define con `value_ids` (los valores de atributo elegidos,
    uno por atributo del producto). Las fotos se heredan del valor del eje
    visual (no se suben por variante).
    """

    product_name = serializers.CharField(source='product.name', read_only=True)
    tax_rate = serializers.IntegerField(source='product.tax_rate', read_only=True)
    profit_margin = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    effective_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    stock_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)
    options_label = serializers.CharField(read_only=True)
    values = serializers.SerializerMethodField()
    value_ids = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.all(), many=True, write_only=True, required=False
    )
    main_image = serializers.SerializerMethodField()

    @extend_schema_field(
        {'type': 'array', 'items': {'type': 'object'}}
    )
    def get_values(self, obj):
        out = []
        for vv in obj.values.all():
            v = vv.value
            out.append({
                'attribute': v.attribute_id,
                'attribute_name': v.attribute.name,
                'value': v.id,
                'value_label': v.value,
                'swatch_hex': v.swatch_hex,
            })
        return out

    @extend_schema_field(OpenApiTypes.URI)
    def get_main_image(self, obj):
        """URL (absoluta si hay request) de la imagen principal, o None."""
        img = obj.main_image
        if not img:
            return None
        url = img.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'tax_rate', 'sku', 'barcode',
            'cost_price', 'sale_price', 'profit_margin',
            'average_cost', 'effective_cost', 'stock_value',
            'stock', 'min_stock', 'is_low_stock',
            'options_label', 'values', 'value_ids',
            'main_image',
            'is_active', 'created_at', 'updated_at',
        ]
        # stock y average_cost los maneja SOLO el módulo de inventario.
        read_only_fields = ['id', 'stock', 'average_cost', 'created_at', 'updated_at']

    def validate_sku(self, value):
        return value.strip()

    def validate_barcode(self, value):
        value = (value or '').strip()
        if value:
            qs = ProductVariant.objects.filter(barcode=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('Ese código de barras ya existe.')
        return value

    def validate(self, attrs):
        for field in ('cost_price', 'sale_price'):
            value = attrs.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError(
                    {field: 'El precio no puede ser negativo.'}
                )
        # Los valores deben pertenecer al producto y ser uno por atributo.
        value_objs = attrs.get('value_ids')
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        if value_objs is not None and product is not None:
            seen = set()
            for v in value_objs:
                if v.attribute.product_id != product.id:
                    raise serializers.ValidationError(
                        {'value_ids': 'Un valor no pertenece a este producto.'}
                    )
                if v.attribute_id in seen:
                    raise serializers.ValidationError(
                        {'value_ids': 'Hay dos valores del mismo atributo en la variante.'}
                    )
                seen.add(v.attribute_id)
            # Debe haber un valor por cada atributo del producto (combinación completa).
            attr_count = product.attributes.count()
            if len(value_objs) != attr_count:
                raise serializers.ValidationError(
                    {'value_ids': 'Elige un valor para cada atributo del producto.'}
                )
            # No se permiten variantes con la MISMA combinación (entre las activas).
            new_set = frozenset(v.id for v in value_objs)
            for other in product.variants.filter(is_active=True):
                if self.instance and other.id == self.instance.id:
                    continue
                existing = frozenset(other.values.values_list('value_id', flat=True))
                if existing == new_set:
                    raise serializers.ValidationError(
                        {'value_ids': 'Ya existe una variante con esta combinación.'}
                    )
        # Reactivar: la combinación no debe chocar con otra variante ya activa.
        reactivating = (
            value_objs is None
            and attrs.get('is_active') is True
            and self.instance is not None
            and not self.instance.is_active
        )
        if reactivating and product is not None:
            mine = frozenset(self.instance.values.values_list('value_id', flat=True))
            # Solo aplica a variantes con combinación (productos sin atributos no chocan).
            for other in product.variants.filter(is_active=True).exclude(pk=self.instance.pk) if mine else []:
                if frozenset(other.values.values_list('value_id', flat=True)) == mine:
                    raise serializers.ValidationError(
                        {'is_active': 'Ya hay una variante activa con esta combinación. '
                                      'Edita una de las dos antes de reactivar.'}
                    )
        return attrs

    def _set_values(self, variant, value_objs):
        variant.values.all().delete()
        VariantValue.objects.bulk_create(
            [VariantValue(variant=variant, value=v) for v in value_objs]
        )

    def create(self, validated_data):
        value_objs = validated_data.pop('value_ids', [])
        variant = super().create(validated_data)
        self._set_values(variant, value_objs)
        return variant

    def update(self, instance, validated_data):
        value_objs = validated_data.pop('value_ids', None)
        variant = super().update(instance, validated_data)
        if value_objs is not None:
            self._set_values(variant, value_objs)
        return variant


class ProductSerializer(serializers.ModelSerializer):
    """Producto: lo compartido por sus variantes (nombre, marca, imágenes…)."""

    category = serializers.IntegerField(source='subcategory.category_id', read_only=True)
    category_name = serializers.CharField(
        source='subcategory.category.name', read_only=True
    )
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    main_image = serializers.SerializerMethodField()
    # brand se escribe por id y se lee anidado en brand_detail.
    brand_detail = BrandSerializer(source='brand', read_only=True)
    unit_of_measure_display = serializers.CharField(
        source='get_unit_of_measure_display', read_only=True
    )
    tax_rate_display = serializers.CharField(
        source='get_tax_rate_display', read_only=True
    )
    # Variantes, atributos e imágenes anidados (lectura; se gestionan aparte).
    variants = ProductVariantSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    price_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    price_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    has_low_stock = serializers.BooleanField(read_only=True)

    @extend_schema_field(OpenApiTypes.URI)
    def get_main_image(self, obj):
        """URL (absoluta si hay request) de la imagen principal, o None."""
        img = obj.main_image
        if not img:
            return None
        url = img.image.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description',
            'subcategory', 'subcategory_name', 'category', 'category_name',
            'brand', 'brand_detail',
            'unit_of_measure', 'unit_of_measure_display',
            'tax_rate', 'tax_rate_display',
            'main_image',
            'variants', 'attributes', 'images',
            'total_stock', 'price_min', 'price_max', 'has_low_stock',
            'expiration_date', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
