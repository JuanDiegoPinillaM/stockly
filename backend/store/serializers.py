import re
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import (
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductVariant,
    Subcategory,
)
from inventory.models import Warehouse
from inventory.schedule import summarize_schedule

from .models import Address, CartItem, Order, OrderAllocation, OrderItem, SavedPaymentMethod
from .services import (
    allocate_delivery,
    allocate_pickup_split,
    create_order,
    pickup_warehouses,
    single_warehouse_allocation,
)


def _abs_url(serializer, file_field):
    if not file_field:
        return None
    url = file_field.url
    request = serializer.context.get('request')
    return request.build_absolute_uri(url) if request else url


class StoreBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']


class StoreSubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'slug']


class StoreCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'subcategories']

    @extend_schema_field(StoreSubcategorySerializer(many=True))
    def get_subcategories(self, obj):
        active = [s for s in obj.subcategories.all() if s.is_active]
        return StoreSubcategorySerializer(active, many=True).data


class StoreVariantSerializer(serializers.ModelSerializer):
    """Variante para la tienda: datos públicos + sus valores de atributo.

    `value_ids` indica qué valores tiene (para que la tienda case la selección
    de atributos con la variante). Las fotos se heredan del valor visual.
    """

    available = serializers.SerializerMethodField()
    value_ids = serializers.SerializerMethodField()
    options_label = serializers.CharField(read_only=True)
    main_image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sale_price', 'available', 'stock',
            'value_ids', 'options_label', 'main_image', 'images',
        ]

    def get_available(self, obj):
        return obj.stock > 0

    @extend_schema_field({'type': 'array', 'items': {'type': 'integer'}})
    def get_value_ids(self, obj):
        return [vv.value_id for vv in obj.values.all()]

    @extend_schema_field(OpenApiTypes.URI)
    def get_main_image(self, obj):
        img = obj.main_image
        return _abs_url(self, img.image if img else None)

    @extend_schema_field({'type': 'array', 'items': {'type': 'string', 'format': 'uri'}})
    def get_images(self, obj):
        """Galería de la variante (heredada del valor del eje visual)."""
        return [_abs_url(self, im.image) for im in obj.gallery]


class StoreProductSerializer(serializers.ModelSerializer):
    """Producto para el listado de la tienda (datos públicos)."""

    category = serializers.CharField(source='subcategory.category.name', read_only=True)
    category_id = serializers.IntegerField(source='subcategory.category_id', read_only=True)
    brand = serializers.CharField(source='brand.name', read_only=True, default=None)
    main_image = serializers.SerializerMethodField()
    price_min = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    price_max = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    available = serializers.SerializerMethodField()
    # Segunda foto (para el efecto de cambio de imagen al pasar el cursor).
    hover_image = serializers.SerializerMethodField()
    # Producto reciente (badge "Nuevo").
    is_new = serializers.SerializerMethodField()
    # Una entrada por valor del eje de fotos (color), con su foto/precio propios,
    # para que la tienda muestre una tarjeta por color.
    colors = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_id',
            'brand', 'main_image', 'hover_image', 'is_new',
            'price_min', 'price_max', 'available', 'colors',
        ]

    def get_available(self, obj):
        return obj.total_stock > 0

    @extend_schema_field(OpenApiTypes.URI)
    def get_main_image(self, obj):
        img = obj.main_image
        return _abs_url(self, img.image if img else None)

    @extend_schema_field(OpenApiTypes.URI)
    def get_hover_image(self, obj):
        imgs = list(obj.images.all())
        return _abs_url(self, imgs[1].image) if len(imgs) > 1 else None

    def get_is_new(self, obj):
        return bool(obj.created_at and obj.created_at >= timezone.now() - timedelta(days=30))

    @extend_schema_field({'type': 'array', 'items': {'type': 'object'}})
    def get_colors(self, obj):
        """Desglose por color (eje de fotos). Vacío si el producto no tiene
        eje visual: en ese caso la tienda muestra una sola tarjeta del producto."""
        axis = next((a for a in obj.attributes.all() if a.is_image_axis), None)
        if not axis:
            return []
        # Imágenes (por orden) agrupadas por valor del eje.
        imgs_by_val = {}
        for im in obj.images.all():
            imgs_by_val.setdefault(im.value_id, []).append(im)
        out = []
        for val in axis.ordered_values:
            variants = [
                v for v in obj.variants.all()
                if v.is_active and any(vv.value_id == val.id for vv in v.values.all())
            ]
            if not variants:
                continue
            prices = [v.sale_price for v in variants]
            imgs = imgs_by_val.get(val.id) or ([obj.main_image] if obj.main_image else [])
            img = imgs[0] if imgs else None
            img2 = imgs[1] if len(imgs) > 1 else None
            # Valores (talla, almacenamiento…) presentes en las variantes de este
            # color, para poder filtrar las tarjetas por otros atributos.
            value_texts = sorted(
                {vv.value.value.lower() for v in variants for vv in v.values.all()}
            )
            out.append({
                'value_id': val.id,
                'label': val.value,
                'swatch_hex': val.swatch_hex,
                'image': _abs_url(self, img.image if img else None),
                'image2': _abs_url(self, img2.image if img2 else None),
                'price_min': float(min(prices)),
                'price_max': float(max(prices)),
                'available': any(v.stock > 0 for v in variants),
                'values': value_texts,
            })
        return out


class StoreProductDetailSerializer(StoreProductSerializer):
    variants = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    class Meta(StoreProductSerializer.Meta):
        fields = StoreProductSerializer.Meta.fields + ['attributes', 'variants']

    @extend_schema_field({'type': 'array', 'items': {'type': 'object'}})
    def get_attributes(self, obj):
        """Atributos del producto con sus valores, para armar los selectores."""
        out = []
        for a in obj.attributes.all():
            out.append({
                'id': a.id,
                'name': a.name,
                'is_image_axis': a.is_image_axis,
                'values': [
                    {'id': v.id, 'value': v.value, 'swatch_hex': v.swatch_hex}
                    for v in a.ordered_values
                ],
            })
        return out

    @extend_schema_field(StoreVariantSerializer(many=True))
    def get_variants(self, obj):
        active = [v for v in obj.variants.all() if v.is_active]
        return StoreVariantSerializer(active, many=True, context=self.context).data


# ----------------------------- Carrito -----------------------------

class CartItemSerializer(serializers.ModelSerializer):
    """Línea del carrito con los datos que necesita la tienda para mostrarla."""

    product_slug = serializers.CharField(source='variant.product.slug', read_only=True)
    name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.options_label', read_only=True)
    price = serializers.DecimalField(
        source='variant.sale_price', max_digits=12, decimal_places=2, read_only=True
    )
    stock = serializers.IntegerField(source='variant.stock', read_only=True)
    available = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'variant', 'quantity',
            'product_slug', 'name', 'variant_label', 'price',
            'stock', 'available', 'image',
        ]
        read_only_fields = fields

    def get_available(self, obj):
        return obj.variant.stock > 0

    @extend_schema_field(OpenApiTypes.URI)
    def get_image(self, obj):
        img = obj.variant.main_image
        return _abs_url(self, img.image if img else None)


class CartItemWriteSerializer(serializers.Serializer):
    """Entrada para fijar/agregar una línea del carrito."""

    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class CartMergeSerializer(serializers.Serializer):
    """Fusiona el carrito local del visitante al iniciar sesión."""

    items = CartItemWriteSerializer(many=True)


# ----------------------------- Favoritos -----------------------------

def _wishlist_card(serializer, product, value):
    """Datos de tarjeta para un favorito (producto + color opcional)."""
    imgs = list(product.images.all())
    is_new = bool(
        product.created_at and product.created_at >= timezone.now() - timedelta(days=30)
    )
    if value is None:
        variants = [v for v in product.variants.all() if v.is_active]
        first = imgs[0] if imgs else None
    else:
        variants = [
            v for v in product.variants.all()
            if v.is_active and any(vv.value_id == value.id for vv in v.values.all())
        ]
        vimgs = [im for im in imgs if im.value_id == value.id]
        first = vimgs[0] if vimgs else (imgs[0] if imgs else None)
    prices = [v.sale_price for v in variants]
    return {
        'product_id': product.id,
        'slug': product.slug,
        'name': product.name,
        'category': product.subcategory.category.name if product.subcategory_id else '',
        'is_new': is_new,
        'hover_image': _abs_url(serializer, imgs[1].image) if len(imgs) > 1 else None,
        'color_id': value.id if value else None,
        'color_label': value.value if value else None,
        'swatch_hex': value.swatch_hex if value else None,
        'main_image': _abs_url(serializer, first.image if first else None),
        'price_min': float(min(prices)) if prices else None,
        'price_max': float(max(prices)) if prices else None,
        'available': any(v.stock > 0 for v in variants),
    }


class WishlistItemSerializer(serializers.Serializer):
    """Favorito como tarjeta lista para la tienda."""

    def to_representation(self, obj):
        return _wishlist_card(self, obj.product, obj.value)


class WishlistWriteSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    value = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.all(), required=False, allow_null=True
    )


class WishlistMergeSerializer(serializers.Serializer):
    items = WishlistWriteSerializer(many=True)


# ----------------------------- Cuenta -----------------------------

class AddressSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True, default=None)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    city_name = serializers.CharField(source='city.name', read_only=True, default=None)

    class Meta:
        model = Address
        fields = [
            'id', 'label', 'recipient', 'phone', 'line1',
            'country', 'department', 'city',
            'country_name', 'department_name', 'city_name',
            'notes', 'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'country_name', 'department_name', 'city_name',
        ]
        extra_kwargs = {
            'recipient': {'required': True, 'allow_blank': False},
            'line1': {'required': True, 'allow_blank': False},
            'phone': {'required': True, 'allow_blank': False},
            'country': {'required': True},
            'department': {'required': True},
            'city': {'required': True},
        }

    def validate_phone(self, value):
        # Exactamente 10 dígitos; se normaliza al formato agrupado "300 123 4567".
        digits = re.sub(r'\D', '', value or '')
        if len(digits) != 10:
            raise serializers.ValidationError('El teléfono debe tener 10 dígitos.')
        return f'{digits[:3]} {digits[3:6]} {digits[6:]}'

    def validate(self, attrs):
        country = attrs.get('country') or getattr(self.instance, 'country', None)
        department = attrs.get('department') or getattr(self.instance, 'department', None)
        city = attrs.get('city') or getattr(self.instance, 'city', None)
        if country and department and department.country_id != country.id:
            raise serializers.ValidationError(
                {'department': 'El departamento no pertenece al país seleccionado.'}
            )
        if department and city and city.department_id != department.id:
            raise serializers.ValidationError(
                {'city': 'La ciudad no pertenece al departamento seleccionado.'}
            )
        return attrs


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = SavedPaymentMethod
        fields = ['id', 'kind', 'kind_display', 'label', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'kind_display', 'created_at', 'updated_at']


# ----------------------------- Pedidos -----------------------------

class StorePointSerializer(serializers.ModelSerializer):
    """Punto/tienda donde el comprador puede pedir o recoger (bodega activa),
    con sus datos de vitrina pública (ubicación, contacto, foto, horario y mapa)."""

    photo = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True, default=None)
    department_name = serializers.CharField(
        source='city.department.name', read_only=True, default=None
    )
    country_name = serializers.CharField(
        source='city.department.country.name', read_only=True, default=None
    )
    schedule_display = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            'id', 'name', 'address', 'description', 'email', 'phone',
            'city_name', 'department_name', 'country_name',
            'hours', 'schedule_display', 'photo', 'map_embed_url',
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_photo(self, obj):
        if not obj.photo:
            return None
        request = self.context.get('request')
        url = obj.photo.url
        return request.build_absolute_uri(url) if request else url

    @extend_schema_field({'type': 'array', 'items': {'type': 'object'}})
    def get_schedule_display(self, obj):
        return summarize_schedule(obj.schedule)


class OrderItemSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'variant', 'description', 'sku', 'quantity',
            'unit_price', 'tax_rate', 'unit_cost', 'line_total', 'image',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.URI)
    def get_image(self, obj):
        img = obj.variant.main_image if obj.variant_id else None
        return _abs_url(self, img.image if img else None)


class OrderAllocationSerializer(serializers.ModelSerializer):
    """Reparto de una variante del pedido en una bodega (fulfillment dividido)."""

    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    description = serializers.CharField(source='variant.product.name', read_only=True)
    options = serializers.CharField(source='variant.options_label', read_only=True)

    class Meta:
        model = OrderAllocation
        fields = ['id', 'variant', 'description', 'options', 'warehouse', 'warehouse_name', 'quantity']
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Lectura de un pedido con sus líneas."""

    items = OrderItemSerializer(many=True, read_only=True)
    allocations = OrderAllocationSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    fulfillment_display = serializers.CharField(source='get_fulfillment_display', read_only=True)
    payment_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    customer = serializers.IntegerField(source='user_id', read_only=True)
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_email = serializers.EmailField(source='user.email', read_only=True)
    customer_document = serializers.CharField(source='user.id_number', read_only=True, default=None)
    total_items = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    code = serializers.CharField(read_only=True)
    # Venta generada al entregar el pedido (un pedido culmina en una venta).
    sale_id = serializers.IntegerField(source='sale.id', read_only=True, default=None)
    sale_code = serializers.CharField(source='sale.code', read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            'id', 'number', 'code', 'status', 'status_display',
            'fulfillment', 'fulfillment_display',
            'payment_method', 'payment_display', 'is_paid',
            'warehouse', 'warehouse_name',
            'customer', 'customer_name', 'customer_email', 'customer_document',
            'subtotal', 'tax_total', 'total', 'total_items',
            'ship_recipient', 'ship_phone', 'ship_phone_alt', 'ship_line1',
            'ship_city', 'ship_department', 'ship_country', 'ship_notes',
            'note', 'cancel_reason', 'is_open', 'sale_id', 'sale_code',
            'items', 'allocations',
            'created_at', 'confirmed_at', 'shipped_at', 'delivered_at', 'cancelled_at',
        ]
        read_only_fields = fields


class _OrderItemInput(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class AvailabilityCheckSerializer(serializers.Serializer):
    """Consulta de disponibilidad del carrito en un punto."""

    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(is_active=True)
    )
    items = _OrderItemInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('El carrito está vacío.')
        return value


class FulfillmentOptionsSerializer(serializers.Serializer):
    """Entrada para consultar las opciones de entrega de un carrito (solo ítems)."""

    items = _OrderItemInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('El carrito está vacío.')
        return value


class OrderCreateSerializer(serializers.Serializer):
    """Crea un pedido en línea; la lógica vive en services.create_order.

    El comprador ya NO elige la bodega: en envío a domicilio el sistema la decide
    por cercanía y existencia (smart order routing); para recoger, el comprador
    elige `warehouse` solo entre las tiendas que tienen el pedido completo.
    """

    # Solo se envía cuando es "recoger en una tienda" concreta. En envío a
    # domicilio se ignora (lo decide el ruteo); en recoger dividido tampoco.
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False, allow_null=True,
    )
    # Recoger repartido en varias tiendas (cuando ninguna sola tiene todo).
    pickup_split = serializers.BooleanField(required=False, default=False)
    fulfillment = serializers.ChoiceField(choices=Order.Fulfillment.choices)
    payment_method = serializers.ChoiceField(choices=Order.Payment.choices)
    # Dirección propia del comprador; obligatoria solo para envío a domicilio.
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), required=False, allow_null=True
    )
    items = _OrderItemInput(many=True)
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('El pedido no tiene productos.')
        return value

    def validate_address(self, value):
        # La dirección debe pertenecer al comprador autenticado.
        request = self.context.get('request')
        if value is not None and request and value.user_id != request.user.id:
            raise serializers.ValidationError('La dirección no es válida.')
        return value

    def validate(self, attrs):
        items = attrs['items']
        if attrs['fulfillment'] == Order.Fulfillment.DELIVERY:
            # Envío: el comprador no elige tienda. El sistema reparte el pedido
            # entre las sedes más cercanas (varias si hace falta).
            address = attrs.get('address')
            if not address:
                raise serializers.ValidationError({'address': 'Indica una dirección de envío.'})
            allocations = allocate_delivery(items, address)
            if allocations is None:
                raise serializers.ValidationError(
                    'No tenemos existencia suficiente para enviarte este pedido en este momento.'
                )
        elif attrs.get('pickup_split'):
            # Recoger repartido entre varias tiendas públicas.
            allocations = allocate_pickup_split(items)
            if allocations is None:
                raise serializers.ValidationError(
                    'No hay existencia suficiente en las tiendas para recoger este pedido.'
                )
        else:
            # Recoger en UNA tienda elegida por el comprador (con el pedido completo).
            warehouse = attrs.get('warehouse')
            if warehouse is None:
                raise serializers.ValidationError(
                    {'warehouse': 'Elige la tienda donde vas a recoger.'}
                )
            allocations = single_warehouse_allocation(items, warehouse)
            if allocations is None:
                raise serializers.ValidationError(
                    {'warehouse': 'Esa tienda no tiene tu pedido completo disponible.'}
                )
        attrs['allocations'] = allocations
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        address = validated_data.get('address')
        shipping = None
        if address is not None and validated_data['fulfillment'] == Order.Fulfillment.DELIVERY:
            shipping = {
                'recipient': address.recipient,
                'phone': address.phone,
                # Teléfono secundario: el de la cuenta del comprador.
                'phone_alt': request.user.phone or '',
                'line1': address.line1,
                'city': address.city.name if address.city_id else '',
                'department': address.department.name if address.department_id else '',
                'country': address.country.name if address.country_id else '',
                'notes': address.notes,
            }
        return create_order(
            user=request.user,
            allocations=validated_data['allocations'],
            fulfillment=validated_data['fulfillment'],
            payment_method=validated_data['payment_method'],
            items=validated_data['items'],
            shipping=shipping,
            note=validated_data.get('note', ''),
        )

    def to_representation(self, instance):
        return OrderSerializer(instance, context=self.context).data
