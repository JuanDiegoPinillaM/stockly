import re

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import ProductVariant

from .models import (
    MovementType,
    StockLevel,
    StockMovement,
    Transfer,
    TransferItem,
    Warehouse,
)
from .schedule import summarize_schedule
from .services import record_movement, request_transfer


class WarehouseSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True, default=None)
    department_name = serializers.CharField(
        source='city.department.name', read_only=True, default=None
    )
    country_name = serializers.CharField(
        source='city.department.country.name', read_only=True, default=None
    )
    # IDs derivados (para precargar el cascadeo país→depto→ciudad en el formulario).
    department = serializers.IntegerField(source='city.department_id', read_only=True, default=None)
    country = serializers.IntegerField(
        source='city.department.country_id', read_only=True, default=None
    )
    # Horario agrupado para mostrar ("Lunes a viernes …"); el editor usa `schedule`.
    schedule_display = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            'id', 'name', 'code', 'address', 'is_active',
            'description', 'email', 'phone', 'hours', 'schedule', 'schedule_display', 'photo',
            'map_embed_url', 'show_in_store',
            'city', 'city_name', 'department', 'department_name',
            'country', 'country_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True},
            'city': {'required': False, 'allow_null': True},
        }

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_schedule_display(self, obj):
        return summarize_schedule(obj.schedule)

    # Dominios de mapa permitidos para el iframe (evita incrustar cualquier sitio).
    _MAP_HOSTS = ('google.com', 'google.', 'maps.google', 'openstreetmap.org')

    def validate_map_embed_url(self, value):
        value = (value or '').strip()
        if not value:
            return ''
        # Si pegaron el <iframe ... src="...">, extrae solo el src.
        match = re.search(r'src=["\']([^"\']+)["\']', value, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
        if not value.startswith('https://'):
            raise serializers.ValidationError('El mapa debe ser un enlace https de Google Maps.')
        if not any(h in value for h in self._MAP_HOSTS):
            raise serializers.ValidationError(
                'Usa el enlace para insertar de Google Maps (Compartir → Insertar un mapa).'
            )
        return value

    def validate_phone(self, value):
        # Opcional; si viene, debe tener exactamente 10 dígitos. Se normaliza al
        # formato agrupado "300 123 4567" para que quede igual venga del form o de la API.
        value = (value or '').strip()
        if not value:
            return ''
        digits = re.sub(r'\D', '', value)
        if len(digits) != 10:
            raise serializers.ValidationError('El teléfono debe tener 10 dígitos.')
        return f'{digits[:3]} {digits[3:6]} {digits[6:]}'


class WarehouseDetailSerializer(WarehouseSerializer):
    """Bodega + KPIs de inventario para la vista de detalle del panel."""

    stats = serializers.SerializerMethodField()

    class Meta(WarehouseSerializer.Meta):
        fields = WarehouseSerializer.Meta.fields + ['stats']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_stats(self, obj):
        from django.db.models import Count, Sum

        levels = obj.stock_levels.filter(quantity__gt=0)
        agg = levels.aggregate(units=Sum('quantity'), variants=Count('id'))
        products = levels.values('variant__product').distinct().count()
        return {
            'total_units': agg['units'] or 0,
            'variant_count': agg['variants'] or 0,
            'product_count': products,
        }


class StockLevelSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    variant_sku = serializers.CharField(source='variant.sku', read_only=True)

    class Meta:
        model = StockLevel
        fields = ['id', 'variant', 'variant_sku', 'warehouse', 'warehouse_name', 'quantity']
        read_only_fields = fields


class StockBreakdownSerializer(serializers.ModelSerializer):
    """Existencia de una variante en una bodega (desglose del reporte)."""

    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = StockLevel
        fields = ['warehouse', 'warehouse_name', 'quantity']
        read_only_fields = fields


class InventoryStockSerializer(serializers.ModelSerializer):
    """Fila del reporte de existencias: una variante valorizada y su desglose.

    `effective_cost` es el costo promedio ponderado real (o el de referencia si
    aún no hay entradas); `stock_value` = existencias × ese costo.
    """

    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_label = serializers.SerializerMethodField()
    average_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    effective_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    stock_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)
    warehouses = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'barcode', 'product', 'product_name', 'variant_label',
            'sale_price', 'average_cost', 'effective_cost',
            'stock', 'min_stock', 'is_low_stock', 'stock_value', 'warehouses',
        ]
        read_only_fields = fields

    def get_variant_label(self, obj):
        return obj.options_label

    def get_warehouses(self, obj):
        # Solo bodegas con existencia (usa el prefetch para no pegarle a la BD).
        levels = [lvl for lvl in obj.stock_levels.all() if lvl.quantity > 0]
        return StockBreakdownSerializer(levels, many=True).data


class StockMovementSerializer(serializers.ModelSerializer):
    """Lectura de un asiento del kardex."""

    variant_sku = serializers.CharField(source='variant.sku', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_to_name = serializers.CharField(
        source='warehouse_to.name', read_only=True, default=None
    )
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    signed_quantity = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.first_name', read_only=True, default=None
    )

    class Meta:
        model = StockMovement
        fields = [
            'id', 'variant', 'variant_sku', 'product_name',
            'warehouse', 'warehouse_name', 'warehouse_to', 'warehouse_to_name',
            'type', 'type_display', 'reason', 'reason_display',
            'quantity', 'signed_quantity', 'unit_cost', 'total_cost', 'balance_after',
            'note', 'reference', 'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = fields


# Tipos permitidos al registrar un movimiento a mano. Se excluyen la SALIDA (las
# ventas se registran por el POS) y la TRANSFERENCIA (va por el flujo de
# transferencias con aprobación entre puntos).
_MANUAL_EXCLUDED = {MovementType.EXIT, MovementType.TRANSFER}
MANUAL_MOVEMENT_TYPES = [
    choice for choice in MovementType.choices if choice[0] not in _MANUAL_EXCLUDED
]


class StockMovementCreateSerializer(serializers.Serializer):
    """Registra un movimiento; toda la lógica vive en services.record_movement."""

    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all()
    )
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all()
    )
    warehouse_to = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), required=False, allow_null=True
    )
    type = serializers.ChoiceField(choices=MANUAL_MOVEMENT_TYPES)
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    quantity = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    note = serializers.CharField(required=False, allow_blank=True, default='')
    reference = serializers.CharField(required=False, allow_blank=True, default='')

    def create(self, validated_data):
        request = self.context.get('request')
        return record_movement(
            variant=validated_data['variant'],
            warehouse=validated_data['warehouse'],
            warehouse_to=validated_data.get('warehouse_to'),
            type=validated_data['type'],
            quantity=validated_data['quantity'],
            unit_cost=validated_data.get('unit_cost'),
            reason=validated_data.get('reason', ''),
            note=validated_data.get('note', ''),
            reference=validated_data.get('reference', ''),
            user=request.user if request and request.user.is_authenticated else None,
        )

    def to_representation(self, instance):
        return StockMovementSerializer(instance, context=self.context).data


# ----------------------------- Transferencias -----------------------------
class TransferItemSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source='variant.sku', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = TransferItem
        fields = [
            'id', 'variant', 'variant_sku', 'product_name',
            'quantity', 'unit_cost', 'line_total',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_line_total(self, obj):
        return obj.unit_cost * obj.quantity


class TransferSerializer(serializers.ModelSerializer):
    """Lectura de una transferencia con sus líneas."""

    items = TransferItemSerializer(many=True, read_only=True)
    origin_name = serializers.CharField(source='origin.name', read_only=True)
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.CharField(
        source='requested_by.first_name', read_only=True, default=None
    )
    resolved_by_name = serializers.CharField(
        source='resolved_by.first_name', read_only=True, default=None
    )
    total_units = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            'id', 'number', 'status', 'status_display',
            'origin', 'origin_name', 'destination', 'destination_name',
            'note', 'items', 'total_units',
            'requested_by', 'requested_by_name', 'created_at',
            'resolved_by', 'resolved_by_name', 'resolved_at',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.INT)
    def get_total_units(self, obj):
        return sum(i.quantity for i in obj.items.all())


class _TransferItemInput(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class TransferCreateSerializer(serializers.Serializer):
    """Solicita una transferencia; la lógica vive en services.request_transfer."""

    origin = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    destination = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    note = serializers.CharField(required=False, allow_blank=True, default='')
    items = _TransferItemInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('La transferencia no tiene productos.')
        return value

    def validate(self, attrs):
        if attrs['origin'].pk == attrs['destination'].pk:
            raise serializers.ValidationError(
                {'destination': 'La bodega destino debe ser distinta a la origen.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        return request_transfer(
            origin=validated_data['origin'],
            destination=validated_data['destination'],
            lines=validated_data['items'],
            note=validated_data.get('note', ''),
            user=user,
        )

    def to_representation(self, instance):
        return TransferSerializer(instance, context=self.context).data
