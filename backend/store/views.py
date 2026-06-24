from collections import defaultdict
from math import ceil, floor

from django.db.models import DecimalField, IntegerField, Max, Min, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import (
    AttributeDefinition,
    AttributeOption,
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductVariant,
)
from inventory.models import Warehouse
from django.shortcuts import get_object_or_404

from sales.models import Sale, SaleItem, SaleStatus
from sales.serializers import SaleSerializer

from .emails import send_order_confirmation_email
from .models import Address, CartItem, Order, OrderItem, SavedPaymentMethod, WishlistItem
from .serializers import (
    AddressSerializer,
    AvailabilityCheckSerializer,
    CartItemSerializer,
    CartItemWriteSerializer,
    CartMergeSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    SavedPaymentMethodSerializer,
    StoreBrandSerializer,
    StoreCategorySerializer,
    StorePointSerializer,
    StoreProductDetailSerializer,
    StoreProductSerializer,
    WishlistItemSerializer,
    WishlistMergeSerializer,
    WishlistWriteSerializer,
)
from .services import check_availability, advance_order, cancel_order

STORE_TAG = ['Tienda']


class IsStaffMember(BasePermission):
    """Permite el acceso solo al personal del back-office (no compradores)."""

    message = 'No tienes permiso para gestionar pedidos.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_staff_member', False)
        )


def _price_expression():
    """Precio del producto para ordenar: el más bajo entre sus variantes activas.

    Subconsulta independiente para no interferir con otros JOIN/filtros (p. ej.
    la búsqueda por variante) ni multiplicar filas.
    """
    cheapest = (
        ProductVariant.objects.filter(product_id=OuterRef('pk'), is_active=True)
        .order_by('sale_price')
        .values('sale_price')[:1]
    )
    return Subquery(cheapest, output_field=DecimalField(max_digits=12, decimal_places=2))


def _sold_expression():
    """Unidades vendidas por producto: ventas del POS completadas + pedidos en
    línea no cancelados. Subconsultas agregadas (sin multiplicar filas)."""
    sale_units = (
        SaleItem.objects.filter(
            variant__product_id=OuterRef('pk'), sale__status=SaleStatus.COMPLETED
        )
        .order_by()
        .values('variant__product_id')
        .annotate(total=Sum('quantity'))
        .values('total')
    )
    order_units = (
        OrderItem.objects.filter(variant__product_id=OuterRef('pk'))
        .exclude(order__status=Order.Status.CANCELLED)
        .order_by()
        .values('variant__product_id')
        .annotate(total=Sum('quantity'))
        .values('total')
    )
    return Coalesce(Subquery(sale_units, output_field=IntegerField()), 0) + Coalesce(
        Subquery(order_units, output_field=IntegerField()), 0
    )


def _product_queryset():
    return (
        Product.objects.filter(is_active=True)
        .select_related('subcategory__category', 'brand')
        .prefetch_related(
            'images',
            'attributes__values__images',
            'variants__values__value__attribute',
        )
        .annotate(price=_price_expression(), sold=_sold_expression())
    )


@extend_schema(tags=STORE_TAG, summary='Puntos / tiendas (público)')
class StorePointListView(generics.ListAPIView):
    """Puntos activos donde el comprador puede pedir o recoger."""

    queryset = Warehouse.objects.filter(is_active=True).order_by('name')
    serializer_class = StorePointSerializer
    permission_classes = [AllowAny]
    pagination_class = None


@extend_schema(tags=STORE_TAG, summary='Categorías de la tienda (público)')
class StoreCategoryListView(generics.ListAPIView):
    queryset = (
        Category.objects.filter(is_active=True)
        .prefetch_related('subcategories')
        .order_by('name')
    )
    serializer_class = StoreCategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None


@extend_schema(tags=STORE_TAG, summary='Existencias de variantes (público)')
class StoreVariantStockView(APIView):
    """Stock actual de un conjunto de variantes (para topar cantidades en el
    carrito). Recibe `?ids=1,2,3` y responde {id: stock}."""

    permission_classes = [AllowAny]

    def get(self, request):
        raw = request.query_params.get('ids', '')
        ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
        rows = ProductVariant.objects.filter(id__in=ids, is_active=True).values_list('id', 'stock')
        return Response({str(vid): stock for vid, stock in rows})


@extend_schema(tags=STORE_TAG, summary='Rango de precios del catálogo (público)')
class StorePriceRangeView(APIView):
    """Precio mínimo y máximo del catálogo, para el slider de rango."""

    permission_classes = [AllowAny]

    def get(self, request):
        qs = ProductVariant.objects.filter(is_active=True, product__is_active=True)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(product__subcategory__category_id=category)
        subcategory = request.query_params.get('subcategory')
        if subcategory:
            qs = qs.filter(product__subcategory_id=subcategory)
        agg = qs.aggregate(lo=Min('sale_price'), hi=Max('sale_price'))
        lo = agg['lo'] or 0
        hi = agg['hi'] or 0
        return Response({'min': floor(lo), 'max': ceil(hi)})


@extend_schema(tags=STORE_TAG, summary='Marcas con productos (público)')
class StoreBrandListView(generics.ListAPIView):
    """Marcas con al menos un producto activo. Se acota a la categoría/subcategoría
    elegida (?category= / ?subcategory=) para que el filtro sea coherente."""

    serializer_class = StoreBrandSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Brand.objects.filter(is_active=True, products__is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(products__subcategory__category_id=category)
        subcategory = self.request.query_params.get('subcategory')
        if subcategory:
            qs = qs.filter(products__subcategory_id=subcategory)
        return qs.distinct().order_by('name')


@extend_schema(tags=STORE_TAG, summary='Filtros por atributos de variación (público)')
class StoreAttributeFiltersView(APIView):
    """Atributos (Color, Talla, Almacenamiento, RAM…) con las opciones que de
    verdad usan los productos activos, para armar los filtros del catálogo.
    Se puede acotar a una categoría/subcategoría con ?category= / ?subcategory=.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        used_qs = AttributeValue.objects.filter(
            attribute__product__is_active=True,
            attribute__definition__isnull=False,
        )
        category = request.query_params.get('category')
        if category:
            used_qs = used_qs.filter(attribute__product__subcategory__category_id=category)
        subcategory = request.query_params.get('subcategory')
        if subcategory:
            used_qs = used_qs.filter(attribute__product__subcategory_id=subcategory)
        used = set(used_qs.values_list('attribute__definition_id', 'value'))

        out = []
        defs = (
            AttributeDefinition.objects.filter(is_active=True)
            .prefetch_related('options')
            .order_by('position', 'name')
        )
        for d in defs:
            opts = [o for o in d.options.all() if o.is_active and (d.id, o.value) in used]
            if not opts:
                continue
            opts.sort(key=lambda o: (o.position, o.id))
            out.append({
                'id': d.id,
                'name': d.name,
                'is_color': d.has_swatch,
                'options': [
                    {'id': o.id, 'value': o.value, 'swatch_hex': o.swatch_hex} for o in opts
                ],
            })
        return Response(out)


@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Productos de la tienda (público)'),
    retrieve=extend_schema(tags=STORE_TAG, summary='Detalle de producto (público)'),
)
class StoreProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo público. Solo expone datos seguros (sin costos ni stock exacto)."""

    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'created_at', 'price', 'sold']
    ordering = ['name']

    def get_serializer_class(self):
        return StoreProductDetailSerializer if self.action == 'retrieve' else StoreProductSerializer

    def get_queryset(self):
        qs = _product_queryset()
        params = self.request.query_params
        category = params.get('category')
        if category:
            qs = qs.filter(subcategory__category_id=category)
        subcategory = params.get('subcategory')
        if subcategory:
            qs = qs.filter(subcategory_id=subcategory)
        brand = params.get('brand')
        if brand:
            qs = qs.filter(brand_id=brand)
        # Filtro por atributos de variación (?options=<ids de opción del catálogo>).
        # Mismo atributo → OR entre sus valores; atributos distintos → AND.
        options = params.get('options')
        if options:
            ids = [int(x) for x in options.split(',') if x.strip().isdigit()]
            if ids:
                groups = defaultdict(list)
                for opt in AttributeOption.objects.filter(id__in=ids).values('definition_id', 'value'):
                    groups[opt['definition_id']].append(opt['value'])
                for def_id, values in groups.items():
                    qs = qs.filter(
                        attributes__definition_id=def_id,
                        attributes__values__value__in=values,
                    )
                qs = qs.distinct()
        # Rango de precio sobre el precio anotado (más bajo entre variantes activas).
        price_min = params.get('price_min')
        if price_min:
            qs = qs.filter(price__gte=price_min)
        price_max = params.get('price_max')
        if price_max:
            qs = qs.filter(price__lte=price_max)
        # Solo productos con existencia en alguna variante activa.
        if params.get('available') in ('1', 'true', 'True'):
            qs = qs.filter(variants__is_active=True, variants__stock__gt=0).distinct()
        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(variants__sku__icontains=search)
            ).distinct()
        return qs


# ----------------------------- Cuenta -----------------------------

class _OwnerScopedViewSet(viewsets.ModelViewSet):
    """ViewSet cuyo contenido pertenece al usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user)
        self._sync_default(obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._sync_default(obj)

    def _sync_default(self, obj):
        # Si se marcó como predeterminado, quita el predeterminado de los demás.
        if obj.is_default:
            type(obj).objects.filter(user=self.request.user).exclude(pk=obj.pk).update(
                is_default=False
            )


@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Mis direcciones'),
    create=extend_schema(tags=STORE_TAG, summary='Agregar dirección'),
    update=extend_schema(tags=STORE_TAG, summary='Actualizar dirección'),
    partial_update=extend_schema(tags=STORE_TAG, summary='Editar dirección'),
    destroy=extend_schema(tags=STORE_TAG, summary='Eliminar dirección'),
)
class AddressViewSet(_OwnerScopedViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer


@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Mis métodos de pago'),
    create=extend_schema(tags=STORE_TAG, summary='Agregar método de pago'),
    update=extend_schema(tags=STORE_TAG, summary='Actualizar método de pago'),
    partial_update=extend_schema(tags=STORE_TAG, summary='Editar método de pago'),
    destroy=extend_schema(tags=STORE_TAG, summary='Eliminar método de pago'),
)
class PaymentMethodViewSet(_OwnerScopedViewSet):
    queryset = SavedPaymentMethod.objects.all()
    serializer_class = SavedPaymentMethodSerializer


# ----------------------------- Carrito -----------------------------

@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Mi carrito'),
    create=extend_schema(tags=STORE_TAG, summary='Fijar cantidad de una variante'),
    partial_update=extend_schema(tags=STORE_TAG, summary='Cambiar cantidad'),
    destroy=extend_schema(tags=STORE_TAG, summary='Quitar del carrito'),
)
class CartItemViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Carrito persistido por cuenta. Las operaciones se hacen por variante:
    POST fija una cantidad absoluta, PATCH la cambia, DELETE la quita; además
    `merge` (fusiona el carrito local al iniciar sesión) y `clear` (vacía)."""

    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer
    pagination_class = None
    lookup_field = 'variant'
    lookup_value_regex = r'\d+'

    def get_queryset(self):
        return (
            CartItem.objects.filter(user=self.request.user)
            .select_related('variant__product')
            .prefetch_related(
                'variant__values__value__attribute', 'variant__product__images'
            )
        )

    def _cap(self, variant, qty):
        """Nunca por encima del stock; nunca negativo."""
        return max(0, min(int(qty), variant.stock))

    def _item_data(self, item):
        return CartItemSerializer(item, context=self.get_serializer_context()).data

    def create(self, request, *args, **kwargs):
        ser = CartItemWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        variant = ser.validated_data['variant']
        qty = self._cap(variant, ser.validated_data['quantity'])
        if qty <= 0:
            CartItem.objects.filter(user=request.user, variant=variant).delete()
            return Response(status=204)
        item, _ = CartItem.objects.update_or_create(
            user=request.user, variant=variant, defaults={'quantity': qty}
        )
        return Response(self._item_data(item), status=200)

    def partial_update(self, request, variant=None):
        item = get_object_or_404(CartItem, user=request.user, variant_id=variant)
        qty = self._cap(item.variant, request.data.get('quantity', item.quantity))
        if qty <= 0:
            item.delete()
            return Response(status=204)
        item.quantity = qty
        item.save(update_fields=['quantity', 'updated_at'])
        return Response(self._item_data(item))

    def destroy(self, request, variant=None):
        CartItem.objects.filter(user=request.user, variant_id=variant).delete()
        return Response(status=204)

    @extend_schema(tags=STORE_TAG, summary='Fusionar carrito local (al iniciar sesión)')
    @action(detail=False, methods=['post'])
    def merge(self, request):
        ser = CartMergeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        for row in ser.validated_data['items']:
            variant = row['variant']
            existing = CartItem.objects.filter(user=request.user, variant=variant).first()
            base = existing.quantity if existing else 0
            qty = self._cap(variant, base + row['quantity'])
            if qty <= 0:
                continue
            CartItem.objects.update_or_create(
                user=request.user, variant=variant, defaults={'quantity': qty}
            )
        data = CartItemSerializer(
            self.get_queryset(), many=True, context=self.get_serializer_context()
        ).data
        return Response(data)

    @extend_schema(tags=STORE_TAG, summary='Vaciar el carrito')
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        CartItem.objects.filter(user=request.user).delete()
        return Response(status=204)


# ----------------------------- Favoritos -----------------------------

@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Mis favoritos'),
    create=extend_schema(tags=STORE_TAG, summary='Agregar a favoritos'),
)
class WishlistViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Favoritos persistidos por cuenta. POST agrega (producto + color opcional);
    `remove` quita; `merge` fusiona los locales al iniciar sesión; `clear` vacía."""

    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            WishlistItem.objects.filter(user=self.request.user)
            .select_related('product__subcategory__category', 'value')
            .prefetch_related(
                'product__images', 'product__variants__values'
            )
        )

    def create(self, request, *args, **kwargs):
        ser = WishlistWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item, _ = WishlistItem.objects.get_or_create(
            user=request.user,
            product=ser.validated_data['product'],
            value=ser.validated_data.get('value'),
        )
        return Response(WishlistItemSerializer(item, context=self.get_serializer_context()).data)

    @extend_schema(tags=STORE_TAG, summary='Quitar de favoritos')
    @action(detail=False, methods=['post'])
    def remove(self, request):
        ser = WishlistWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        WishlistItem.objects.filter(
            user=request.user,
            product=ser.validated_data['product'],
            value=ser.validated_data.get('value'),
        ).delete()
        return Response(status=204)

    @extend_schema(tags=STORE_TAG, summary='Fusionar favoritos locales (al iniciar sesión)')
    @action(detail=False, methods=['post'])
    def merge(self, request):
        ser = WishlistMergeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        for row in ser.validated_data['items']:
            WishlistItem.objects.get_or_create(
                user=request.user, product=row['product'], value=row.get('value')
            )
        data = WishlistItemSerializer(
            self.get_queryset(), many=True, context=self.get_serializer_context()
        ).data
        return Response(data)

    @extend_schema(tags=STORE_TAG, summary='Vaciar favoritos')
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        WishlistItem.objects.filter(user=request.user).delete()
        return Response(status=204)


# ----------------------------- Pedidos -----------------------------

_ORDER_QS = Order.objects.select_related('warehouse', 'user').prefetch_related(
    'items__variant__values__value__attribute',
    'items__variant__product__images',
)


@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Mis pedidos'),
    retrieve=extend_schema(tags=STORE_TAG, summary='Ver un pedido'),
    create=extend_schema(tags=STORE_TAG, summary='Crear pedido (compra en línea)'),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Pedidos del comprador: crea y consulta los suyos."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _ORDER_QS.filter(user=self.request.user)

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == 'create' else OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # Correo de confirmación (best-effort: no falla el pedido si el envío falla).
        try:
            send_order_confirmation_email(order)
        except Exception:
            pass
        data = OrderSerializer(order, context=self.get_serializer_context()).data
        return Response(data, status=201)

    @extend_schema(tags=STORE_TAG, summary='Consultar disponibilidad en un punto')
    @action(detail=False, methods=['post'])
    def availability(self, request):
        serializer = AvailabilityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = check_availability(
            serializer.validated_data['warehouse'],
            serializer.validated_data['items'],
        )
        return Response({'results': result})

    @extend_schema(tags=STORE_TAG, summary='Cancelar mi pedido')
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        # El comprador solo puede cancelar mientras el pedido está pendiente.
        if order.status != Order.Status.PENDING:
            raise PermissionDenied(
                'Solo puedes cancelar un pedido mientras está pendiente. '
                'Contáctanos si necesitas ayuda.'
            )
        order = cancel_order(order, user=request.user, reason='Cancelado por el comprador')
        data = OrderSerializer(order, context=self.get_serializer_context()).data
        return Response(data)


@extend_schema(tags=STORE_TAG, summary='Mis compras (pedidos en línea + ventas en tienda)')
class AccountPurchasesView(APIView):
    """Historial unificado del comprador: sus pedidos en línea y las ventas del
    POS donde figura como cliente (clientes y usuarios son la misma entidad)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        items = []
        for o in Order.objects.filter(user=user).prefetch_related('items'):
            items.append({
                'kind': 'order',
                'id': o.id,
                'number': o.number,
                'date': o.created_at,
                'total': o.total,
                'total_items': o.total_items,
                'status': o.status,
                'status_display': o.get_status_display(),
            })
        for s in Sale.objects.filter(customer=user).prefetch_related('items'):
            items.append({
                'kind': 'sale',
                'id': s.id,
                'number': s.number,
                'date': s.created_at,
                'total': s.total,
                'total_items': s.total_items,
                'status': s.status,
                'status_display': s.get_status_display(),
            })
        items.sort(key=lambda x: x['date'], reverse=True)
        return Response(items)


@extend_schema(tags=STORE_TAG, summary='Ver una de mis compras en tienda (POS)')
class AccountSaleDetailView(APIView):
    """Detalle de una venta del POS para el comprador dueño de ella."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk, customer=request.user)
        return Response(SaleSerializer(sale, context={'request': request}).data)


@extend_schema_view(
    list=extend_schema(tags=STORE_TAG, summary='Pedidos (back-office)'),
    retrieve=extend_schema(tags=STORE_TAG, summary='Ver un pedido (back-office)'),
)
class StaffOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Gestión de pedidos por el personal: avanzar estado y cancelar.

    El admin ve todos los pedidos; el cajero/jefe de punto solo los de su bodega
    asignada (sin bodega → no ve ninguno), igual que en Ventas.
    """

    serializer_class = OrderSerializer
    permission_classes = [IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'warehouse', 'fulfillment']
    search_fields = ['number', 'ship_recipient', 'user__email', 'user__first_name']
    ordering_fields = ['created_at', 'number', 'total']

    def get_queryset(self):
        user = self.request.user
        if not getattr(user, 'is_admin', False):
            return _ORDER_QS.filter(warehouse_id=user.warehouse_id)
        return _ORDER_QS.all()

    @extend_schema(tags=STORE_TAG, summary='Avanzar el estado del pedido')
    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        order = self.get_object()
        order = advance_order(order, user=request.user)
        data = OrderSerializer(order, context=self.get_serializer_context()).data
        return Response(data)

    @extend_schema(tags=STORE_TAG, summary='Cancelar el pedido (back-office)')
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get('reason', '')
        order = cancel_order(order, user=request.user, reason=reason)
        data = OrderSerializer(order, context=self.get_serializer_context()).data
        return Response(data)
