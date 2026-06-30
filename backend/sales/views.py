from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth import get_user_model

from catalog.views import SoftDeleteModelViewSet

from .emails import send_receipt_email
from .models import Sale
from .serializers import (
    CustomerDetailSerializer,
    CustomerSerializer,
    SaleCreateSerializer,
    SaleSerializer,
)
from .services import void_sale

User = get_user_model()

SALES_TAG = ['Ventas']


@extend_schema_view(
    list=extend_schema(tags=SALES_TAG, summary='Listar clientes'),
    retrieve=extend_schema(tags=SALES_TAG, summary='Ver un cliente'),
    create=extend_schema(tags=SALES_TAG, summary='Crear cliente'),
    update=extend_schema(tags=SALES_TAG, summary='Actualizar cliente'),
    partial_update=extend_schema(tags=SALES_TAG, summary='Editar cliente'),
    destroy=extend_schema(tags=SALES_TAG, summary='Desactivar cliente'),
)
class CustomerViewSet(SoftDeleteModelViewSet):
    """CRUD de clientes = usuarios con rol comprador (soft-delete).

    La búsqueda es por número de identificación, nombre, correo o teléfono.
    """

    queryset = User.objects.filter(role=User.Role.BUYER)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['id_number', 'first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['first_name', 'date_joined']

    def get_serializer_class(self):
        # En el detalle se incluye el historial de compras y las direcciones.
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer

    def perform_destroy(self, instance):
        # El "Consumidor final" es un cliente del sistema: no se desactiva.
        if getattr(instance, 'is_walk_in', False):
            raise ValidationError('El cliente "Consumidor final" no se puede desactivar.')
        super().perform_destroy(instance)


@extend_schema_view(
    list=extend_schema(tags=SALES_TAG, summary='Historial de ventas'),
    retrieve=extend_schema(tags=SALES_TAG, summary='Ver una venta'),
    create=extend_schema(tags=SALES_TAG, summary='Registrar una venta (POS)'),
)
class SaleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Ventas del POS. Inmutables salvo la anulación (admin)."""

    queryset = Sale.objects.select_related(
        'customer', 'warehouse', 'created_by'
    ).prefetch_related('items', 'payments').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer', 'warehouse']
    search_fields = ['number', 'customer__id_number', 'customer__first_name', 'note']
    ordering_fields = ['created_at', 'number', 'total']

    def get_queryset(self):
        # El admin ve todas las ventas; el cajero/jefe de punto solo las de su
        # bodega asignada (sin bodega → no ve ninguna).
        qs = super().get_queryset()
        user = self.request.user
        if not getattr(user, 'is_admin', False):
            return qs.filter(warehouse_id=user.warehouse_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()
        # Recibo por correo (best-effort: no falla la venta si el envío falla).
        to_email = sale.receipt_email or (sale.customer.email if sale.customer else '')
        if to_email:
            try:
                send_receipt_email(sale, to_email)
            except Exception:
                pass
        data = SaleSerializer(sale, context=self.get_serializer_context()).data
        return Response(data, status=201)

    @extend_schema(tags=SALES_TAG, summary='Anular una venta (admin)')
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied('Solo un administrador puede anular ventas.')
        sale = self.get_object()
        void_sale(sale, user=request.user)
        data = SaleSerializer(sale, context=self.get_serializer_context()).data
        return Response(data)

    @extend_schema(tags=SALES_TAG, summary='Reenviar el recibo por correo')
    @action(detail=True, methods=['post'], url_path='send-receipt')
    def send_receipt(self, request, pk=None):
        sale = self.get_object()
        to_email = (
            request.data.get('email')
            or sale.receipt_email
            or (sale.customer.email if sale.customer else '')
        )
        if not to_email:
            raise ValidationError({'email': 'Indica un correo para enviar el recibo.'})
        try:
            send_receipt_email(sale, to_email)
        except Exception:
            raise ValidationError('No se pudo enviar el correo. Intenta más tarde.')
        return Response({'detail': f'Recibo enviado a {to_email}.'})
