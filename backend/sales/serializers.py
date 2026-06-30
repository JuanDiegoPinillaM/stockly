from django.contrib.auth import get_user_model
from rest_framework import serializers

from catalog.models import ProductVariant
from inventory.models import Warehouse

from .models import (
    PaymentMethod,
    Sale,
    SaleItem,
    SalePayment,
)
from .services import create_sale

User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    """Cliente = usuario (rol comprador). Lo gestiona el módulo Clientes y el POS.

    La identificación es obligatoria; el correo y la contraseña son opcionales
    (un cliente de mostrador puede no tener cuenta).
    """

    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    sales_count = serializers.IntegerField(source='purchases.count', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'id_type', 'id_type_display', 'id_number',
            'first_name', 'last_name', 'full_name', 'email', 'phone', 'avatar',
            'is_active', 'is_walk_in', 'sales_count', 'date_joined',
        ]
        read_only_fields = [
            'id', 'id_type_display', 'full_name', 'avatar', 'is_walk_in',
            'sales_count', 'date_joined',
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            'id_type': {'required': True, 'allow_blank': False},
            'id_number': {'required': True, 'allow_blank': False},
            'email': {'required': False, 'allow_blank': True},
        }

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        url = obj.avatar.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('El nombre es obligatorio.')
        return value

    def validate_id_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('El número de identificación es obligatorio.')
        qs = User.objects.filter(id_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe alguien con este número de identificación.')
        return value

    def validate_email(self, value):
        if not value:
            return None
        value = value.lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    def create(self, validated_data):
        # Cliente nuevo = usuario comprador sin contraseña utilizable.
        user = User(role=User.Role.BUYER, is_active=True, **validated_data)
        user.set_unusable_password()
        user.save()
        return user


def _purchase_rows(user):
    """Historial unificado de compras de un usuario: pedidos en línea + ventas.

    Las ventas generadas a partir de un pedido (canal online) se omiten aquí: ya
    están representadas por su pedido, que muestra el código de su venta. Solo se
    listan las ventas del POS (sin pedido asociado) para no duplicar.
    """
    rows = []
    for o in user.orders.all():
        rows.append({
            'kind': 'order', 'id': o.id, 'number': o.number, 'code': o.code,
            'date': o.created_at,
            'total': o.total, 'total_items': o.total_items,
            'status': o.status, 'status_display': o.get_status_display(),
        })
    for s in user.purchases.filter(order__isnull=True):
        rows.append({
            'kind': 'sale', 'id': s.id, 'number': s.number, 'code': s.code,
            'date': s.created_at,
            'total': s.total, 'total_items': s.total_items,
            'status': s.status, 'status_display': s.get_status_display(),
        })
    rows.sort(key=lambda x: x['date'], reverse=True)
    return rows


class CustomerDetailSerializer(CustomerSerializer):
    """Cliente con su historial de compras y direcciones (vista de detalle)."""

    addresses = serializers.SerializerMethodField()
    purchases = serializers.SerializerMethodField()

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ['addresses', 'purchases']

    def get_addresses(self, obj):
        return [
            {
                'id': a.id, 'label': a.label, 'recipient': a.recipient,
                'phone': a.phone, 'line1': a.line1,
                'city': a.city.name if a.city_id else '',
                'department': a.department.name if a.department_id else '',
                'country': a.country.name if a.country_id else '',
                'notes': a.notes, 'is_default': a.is_default,
            }
            for a in obj.addresses.select_related('city', 'department', 'country')
        ]

    def get_purchases(self, obj):
        return _purchase_rows(obj)


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = [
            'id', 'variant', 'description', 'sku', 'quantity',
            'unit_price', 'tax_rate', 'unit_cost', 'line_total',
        ]
        read_only_fields = fields


class SalePaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = SalePayment
        fields = ['id', 'method', 'method_display', 'amount']
        read_only_fields = ['id', 'method_display']


class SaleSerializer(serializers.ModelSerializer):
    """Lectura de una venta con sus líneas y pagos."""

    items = SaleItemSerializer(many=True, read_only=True)
    payments = SalePaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True, default=None)
    customer_document = serializers.CharField(source='customer.id_number', read_only=True, default=None)
    customer_email = serializers.EmailField(source='customer.email', read_only=True, default=None)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    code = serializers.CharField(read_only=True)
    order_code = serializers.CharField(source='order.code', read_only=True, default=None)
    created_by_name = serializers.CharField(
        source='created_by.first_name', read_only=True, default=None
    )
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'number', 'code', 'channel', 'channel_display',
            'order', 'order_code',
            'status', 'status_display',
            'customer', 'customer_name', 'customer_document', 'customer_email',
            'warehouse', 'warehouse_name',
            'subtotal', 'tax_total', 'discount', 'total', 'paid', 'change',
            'note', 'receipt_email', 'total_items',
            'items', 'payments',
            'created_by', 'created_by_name', 'created_at', 'voided_at',
        ]
        read_only_fields = fields


class _SaleItemInput(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class _SalePaymentInput(serializers.Serializer):
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)


class SaleCreateSerializer(serializers.Serializer):
    """Registra una venta; la lógica vive en services.create_sale."""

    # El admin elige bodega libremente; al cajero/jefe de punto se le fuerza a su
    # bodega asignada (se resuelve en validate), así que no es obligatoria en el body.
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), required=False, allow_null=True
    )
    # El cliente es obligatorio: ninguna venta queda sin asociar. Se elige uno
    # existente o se crea al vuelo desde el POS (módulo Clientes).
    customer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.BUYER),
        required=True,
        allow_null=False,
        error_messages={
            'required': 'Selecciona o crea un cliente para la venta.',
            'null': 'Selecciona o crea un cliente para la venta.',
        },
    )
    discount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0, min_value=0
    )
    note = serializers.CharField(required=False, allow_blank=True, default='')
    receipt_email = serializers.EmailField(required=False, allow_blank=True, default='')
    items = _SaleItemInput(many=True)
    payments = _SalePaymentInput(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('La venta no tiene productos.')
        return value

    def validate_payments(self, value):
        if not value:
            raise serializers.ValidationError('Indica al menos una forma de pago.')
        return value

    def validate(self, attrs):
        """Resuelve la bodega de la venta según el rol de quien vende.

        - Admin: vende en la bodega que indique (debe enviarla).
        - Cajero / jefe de punto: SIEMPRE en su bodega asignada (se ignora la del
          body); si no tiene una, no puede vender.
        """
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        if user is not None and not user.is_admin:
            if user.warehouse_id is None:
                raise serializers.ValidationError(
                    {
                        'warehouse': 'No tienes una bodega asignada. Pide a un '
                        'administrador que te asigne una para poder vender.'
                    },
                    code='no_warehouse_assigned',
                )
            attrs['warehouse'] = user.warehouse
        elif not attrs.get('warehouse'):
            raise serializers.ValidationError(
                {'warehouse': 'Indica la bodega de la venta.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        return create_sale(
            warehouse=validated_data['warehouse'],
            customer=validated_data.get('customer'),
            discount=validated_data.get('discount') or 0,
            note=validated_data.get('note', ''),
            receipt_email=validated_data.get('receipt_email', ''),
            items=validated_data['items'],
            payments=validated_data['payments'],
            user=user,
        )

    def to_representation(self, instance):
        return SaleSerializer(instance, context=self.context).data
