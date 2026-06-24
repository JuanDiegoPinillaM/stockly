from django.db.models import (
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    When,
)
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics, mixins, viewsets
from rest_framework.response import Response

from catalog.models import ProductVariant
from catalog.permissions import IsAdminOrReadOnly
from catalog.serializers import ProductVariantSerializer
from catalog.views import SoftDeleteModelViewSet

from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import StockLevel, StockMovement, Transfer, Warehouse
from .serializers import (
    InventoryStockSerializer,
    StockLevelSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
    TransferCreateSerializer,
    TransferSerializer,
    WarehouseSerializer,
)
from .services import accept_transfer, cancel_transfer, reject_transfer

TRUTHY = {'1', 'true', 'True', 'yes'}

INVENTORY_TAG = ['Inventario']


@extend_schema_view(
    list=extend_schema(tags=INVENTORY_TAG, summary='Listar bodegas'),
    retrieve=extend_schema(tags=INVENTORY_TAG, summary='Ver una bodega'),
    create=extend_schema(tags=INVENTORY_TAG, summary='Crear bodega (admin)'),
    update=extend_schema(tags=INVENTORY_TAG, summary='Actualizar bodega (admin)'),
    partial_update=extend_schema(tags=INVENTORY_TAG, summary='Editar bodega (admin)'),
    destroy=extend_schema(tags=INVENTORY_TAG, summary='Desactivar bodega (admin)'),
)
class WarehouseViewSet(SoftDeleteModelViewSet):
    """CRUD de bodegas/almacenes (soft-delete)."""

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name']


@extend_schema_view(
    list=extend_schema(tags=INVENTORY_TAG, summary='Kardex / historial de movimientos'),
    retrieve=extend_schema(tags=INVENTORY_TAG, summary='Ver un movimiento'),
    create=extend_schema(tags=INVENTORY_TAG, summary='Registrar movimiento (admin)'),
)
class StockMovementViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Libro de movimientos (kardex). Inmutable: solo se listan y se crean.

    Filtra el kardex con ?variant=&warehouse=&type= y ?ordering=created_at.
    """

    queryset = StockMovement.objects.select_related(
        'variant', 'variant__product', 'warehouse', 'warehouse_to', 'created_by'
    ).all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['variant', 'variant__product', 'warehouse', 'type', 'reason']
    search_fields = ['variant__sku', 'variant__product__name', 'reference', 'note']
    ordering_fields = ['created_at', 'id']

    def get_serializer_class(self):
        if self.action == 'create':
            return StockMovementCreateSerializer
        return StockMovementSerializer


@extend_schema_view(
    list=extend_schema(tags=INVENTORY_TAG, summary='Existencias por bodega'),
    retrieve=extend_schema(tags=INVENTORY_TAG, summary='Ver existencia por bodega'),
)
class StockLevelViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Existencia de cada variante por bodega (solo lectura)."""

    queryset = StockLevel.objects.select_related('variant', 'warehouse').all()
    serializer_class = StockLevelSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['variant', 'warehouse']
    ordering_fields = ['quantity']


@extend_schema(tags=INVENTORY_TAG, summary='Existencias valorizadas (reporte de inventario)')
class StockValuationView(generics.ListAPIView):
    """Reporte de existencias: cada variante activa con su valor y desglose por
    bodega, más un resumen global (unidades, valor total, bajo stock).

    Filtros: ?search=, ?low_stock=1, ?in_stock=1 y ?ordering=stock|sale_price|…
    El valor usa el costo promedio real (o el de referencia si aún no hay
    entradas), igual que `ProductVariant.effective_cost`.
    """

    serializer_class = InventoryStockSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['sku', 'barcode', 'product__name']
    ordering_fields = ['stock', 'sale_price', 'average_cost', 'product__name', 'sku']
    ordering = ['product__name', 'sku']

    def get_queryset(self):
        qs = (
            ProductVariant.objects.filter(is_active=True, product__is_active=True)
            .select_related('product')
            .prefetch_related('stock_levels__warehouse', 'values__value__attribute')
        )
        params = self.request.query_params
        if params.get('low_stock') in TRUTHY:
            qs = qs.filter(min_stock__gt=0, stock__lte=F('min_stock'))
        if params.get('in_stock') in TRUTHY:
            qs = qs.filter(stock__gt=0)
        return qs

    def _summary(self, queryset):
        # Costo efectivo en SQL: promedio si > 0, si no el de referencia.
        effective_cost = Case(
            When(average_cost__gt=0, then=F('average_cost')),
            default=F('cost_price'),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
        value = ExpressionWrapper(
            F('stock') * effective_cost,
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        agg = queryset.aggregate(
            total_units=Sum('stock'),
            total_value=Sum(value),
            variants_count=Count('id'),
            low_stock_count=Count(
                'id', filter=Q(min_stock__gt=0, stock__lte=F('min_stock'))
            ),
        )
        return {
            'total_units': agg['total_units'] or 0,
            'total_value': agg['total_value'] or 0,
            'variants_count': agg['variants_count'] or 0,
            'low_stock_count': agg['low_stock_count'] or 0,
        }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        summary = self._summary(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            response = self.get_paginated_response(data)
            response.data['summary'] = summary
            return response
        data = self.get_serializer(queryset, many=True).data
        return Response({'results': data, 'summary': summary})


def _is_manager(user):
    """Admin o jefe de punto: los únicos que operan transferencias."""
    return getattr(user, 'is_admin', False) or getattr(user, 'role', None) == 'jefe_punto'


@extend_schema_view(
    list=extend_schema(tags=INVENTORY_TAG, summary='Listar transferencias'),
    retrieve=extend_schema(tags=INVENTORY_TAG, summary='Ver una transferencia'),
    create=extend_schema(tags=INVENTORY_TAG, summary='Solicitar una transferencia'),
)
class TransferViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Transferencias entre puntos con aprobación.

    Solicita el jefe de punto (desde su bodega) o el admin; acepta/rechaza el
    jefe del punto destino o el admin; el solicitante puede cancelar mientras
    esté pendiente. Inmutable salvo el cambio de estado.
    """

    queryset = Transfer.objects.select_related(
        'origin', 'destination', 'requested_by', 'resolved_by'
    ).prefetch_related('items__variant__product').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'origin', 'destination']
    search_fields = ['number', 'note']
    ordering_fields = ['created_at', 'number']

    def get_serializer_class(self):
        if self.action == 'create':
            return TransferCreateSerializer
        return TransferSerializer

    def get_queryset(self):
        # El admin ve todas; el resto solo las de su bodega (origen o destino).
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return qs
        wid = user.warehouse_id
        return qs.filter(Q(origin_id=wid) | Q(destination_id=wid))

    def create(self, request, *args, **kwargs):
        user = request.user
        if not _is_manager(user):
            raise PermissionDenied('Solo el jefe de punto o el admin pueden transferir.')
        data = request.data.copy()
        # El jefe de punto solo puede transferir DESDE su bodega asignada.
        if not user.is_admin:
            if user.warehouse_id is None:
                raise ValidationError(
                    {'origin': 'No tienes una bodega asignada para transferir.'}
                )
            data['origin'] = user.warehouse_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        out = TransferSerializer(transfer, context=self.get_serializer_context()).data
        return Response(out, status=201)

    def _get_pending(self):
        transfer = self.get_object()
        if not transfer.is_pending:
            raise ValidationError('La transferencia ya fue resuelta.')
        return transfer

    @extend_schema(tags=INVENTORY_TAG, summary='Aceptar (jefe destino o admin)')
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        transfer = self._get_pending()
        if not (request.user.is_admin or request.user.warehouse_id == transfer.destination_id):
            raise PermissionDenied('Solo el jefe del punto destino puede aceptarla.')
        transfer = accept_transfer(transfer, user=request.user)
        return Response(TransferSerializer(transfer, context=self.get_serializer_context()).data)

    @extend_schema(tags=INVENTORY_TAG, summary='Rechazar (jefe destino o admin)')
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        transfer = self._get_pending()
        if not (request.user.is_admin or request.user.warehouse_id == transfer.destination_id):
            raise PermissionDenied('Solo el jefe del punto destino puede rechazarla.')
        transfer = reject_transfer(transfer, user=request.user)
        return Response(TransferSerializer(transfer, context=self.get_serializer_context()).data)

    @extend_schema(tags=INVENTORY_TAG, summary='Cancelar (solicitante o admin)')
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        transfer = self._get_pending()
        if not (request.user.is_admin or request.user.warehouse_id == transfer.origin_id):
            raise PermissionDenied('Solo el punto origen puede cancelarla.')
        transfer = cancel_transfer(transfer, user=request.user)
        return Response(TransferSerializer(transfer, context=self.get_serializer_context()).data)


@extend_schema(tags=INVENTORY_TAG, summary='Variantes en bajo stock (≤ mínimo)')
class LowStockView(generics.ListAPIView):
    """Variantes activas cuya existencia total está en o por debajo del mínimo."""

    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        return (
            ProductVariant.objects.select_related('product')
            .prefetch_related('values__value__attribute')
            .filter(is_active=True, min_stock__gt=0, stock__lte=F('min_stock'))
            .order_by('product__name', 'sku')
        )
