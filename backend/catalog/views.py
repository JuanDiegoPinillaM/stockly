from django.db import models, transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

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
from .permissions import IsAdminOrReadOnly
from .serializers import (
    AttributeDefinitionSerializer,
    AttributeOptionSerializer,
    AttributeValueSerializer,
    BrandSerializer,
    CategorySerializer,
    ColorSerializer,
    ImageReorderSerializer,
    ProductAttributeSerializer,
    ProductImageSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    SizeSerializer,
    SubcategorySerializer,
)

CATALOG_TAG = ['Catálogo']


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet donde DELETE no borra: marca is_active=False.

    En esta base de datos nada se elimina físicamente; los registros se
    desactivan para conservar el histórico e integridad referencial.
    """

    def perform_destroy(self, instance):
        if getattr(instance, 'is_active', True):
            instance.is_active = False
            instance.save(update_fields=['is_active'])


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar colores'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver un color'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear color (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar color (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar color (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar color (admin)'),
)
class ColorViewSet(SoftDeleteModelViewSet):
    """CRUD de colores (nombre + HEX)."""

    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'hex_code']
    ordering_fields = ['name']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar tallas'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una talla'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear talla (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar talla (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar talla (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar talla (admin)'),
)
class SizeViewSet(SoftDeleteModelViewSet):
    """CRUD de tallas (nombre + orden)."""

    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['position', 'name']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar atributos del catálogo'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver un atributo del catálogo'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear atributo del catálogo (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar atributo (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar atributo (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar atributo (admin)'),
)
class AttributeDefinitionViewSet(SoftDeleteModelViewSet):
    """CRUD de atributos reutilizables del catálogo (Color, Talla, Almacenamiento…)."""

    queryset = AttributeDefinition.objects.prefetch_related('options').all()
    serializer_class = AttributeDefinitionSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'has_swatch']
    search_fields = ['name']
    ordering_fields = ['position', 'name']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar opciones de un atributo'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una opción'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear opción (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar opción (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar opción (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar opción (admin)'),
)
class AttributeOptionViewSet(SoftDeleteModelViewSet):
    """CRUD de opciones reutilizables (?definition=<id>)."""

    queryset = AttributeOption.objects.select_related('definition').all()
    serializer_class = AttributeOptionSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['definition', 'is_active']
    search_fields = ['value']
    ordering_fields = ['position', 'value']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar marcas'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una marca'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear marca (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar marca (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar marca (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar marca (admin)'),
)
class BrandViewSet(SoftDeleteModelViewSet):
    """CRUD de marcas (solo nombre)."""

    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['name']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar categorías'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una categoría'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear categoría (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar categoría (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar categoría (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar categoría (admin)'),
)
class CategoryViewSet(SoftDeleteModelViewSet):
    """CRUD de categorías. Incluye sus subcategorías anidadas al leer."""

    queryset = Category.objects.prefetch_related('subcategories').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar subcategorías'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una subcategoría'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear subcategoría (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar subcategoría (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar subcategoría (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar subcategoría (admin)'),
)
class SubcategoryViewSet(SoftDeleteModelViewSet):
    """CRUD de subcategorías. Se puede filtrar por ?category=<id>."""

    queryset = Subcategory.objects.select_related('category').all()
    serializer_class = SubcategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar productos'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver un producto'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear producto (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar producto (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar producto (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar producto (admin)'),
)
class ProductViewSet(SoftDeleteModelViewSet):
    """CRUD de productos. Acepta JSON o multipart (para la imagen principal).

    Filtros: ?subcategory=<id>, ?subcategory__category=<id>, ?is_active=true.
    """

    queryset = (
        Product.objects.select_related(
            'subcategory', 'subcategory__category', 'brand'
        )
        .prefetch_related(
            'attributes__values',
            'attributes__definition__options',
            'images',
            'variants__values__value__attribute',
        )
        .all()
    )
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'subcategory', 'subcategory__category', 'is_active',
        'brand', 'unit_of_measure', 'tax_rate',
    ]
    search_fields = ['name', 'description', 'variants__sku', 'variants__barcode']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        # distinct() evita duplicados al filtrar/buscar por variantes (join 1:N).
        return super().get_queryset().distinct()


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar variantes'),
    retrieve=extend_schema(tags=CATALOG_TAG, summary='Ver una variante'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear variante (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar variante (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar variante (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Desactivar variante (admin)'),
)
class ProductVariantViewSet(SoftDeleteModelViewSet):
    """CRUD de variantes: SKU, código de barras, precios y stock por combinación.

    Se filtran por ?product=<id>. El DELETE desactiva (soft-delete), pero no
    se permite dejar un producto sin ninguna variante activa. Las fotos NO se
    gestionan aquí: viven en el producto por valor del eje visual.
    """

    queryset = (
        ProductVariant.objects.select_related('product')
        .prefetch_related('values__value__attribute', 'product__images')
        .all()
    )
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'is_active']
    search_fields = ['sku', 'barcode', 'product__name']
    ordering_fields = ['sku', 'sale_price', 'stock', 'created_at']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        others = instance.product.variants.filter(is_active=True).exclude(pk=instance.pk)
        if instance.is_active and not others.exists():
            return Response(
                {
                    'detail': 'El producto debe conservar al menos una variante activa.',
                    'code': 'min_variants',
                    'errors': None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar atributos de un producto'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear atributo (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar atributo (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar atributo (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Eliminar atributo (admin)'),
)
class ProductAttributeViewSet(viewsets.ModelViewSet):
    """Atributos de variación de un producto (?product=<id>)."""

    queryset = ProductAttribute.objects.prefetch_related('values').all()
    serializer_class = ProductAttributeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'is_image_axis']
    ordering_fields = ['position', 'name']

    def destroy(self, request, *args, **kwargs):
        """Quitar un atributo: lo desliga de las variantes (borra sus enlaces y
        valores) en vez de bloquear por el PROTECT. Se rechaza solo si, al quitar
        el eje, dos variantes activas quedarían con la MISMA combinación. Las
        fotos del eje pasan a "generales" para no perderlas.
        """
        attr = self.get_object()
        product = attr.product
        value_ids = list(attr.values.values_list('id', flat=True))

        # ¿Colapsarían dos variantes activas en la misma combinación?
        seen = {}
        for v in product.variants.filter(is_active=True).prefetch_related('values'):
            reduced = frozenset(
                vv.value_id for vv in v.values.all() if vv.value_id not in value_ids
            )
            if reduced in seen:
                return Response(
                    {
                        'detail': (
                            f'No se puede quitar "{attr.name}": las variantes '
                            f'"{seen[reduced]}" y "{v.options_label or "Estándar"}" '
                            'quedarían con la misma combinación. Desactiva una de las dos '
                            'antes de quitar el atributo.'
                        ),
                        'code': 'duplicate_after_remove',
                        'errors': None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen[reduced] = v.options_label or 'Estándar'

        with transaction.atomic():
            # Conservar las fotos del eje visual: pasarlas a "generales".
            ProductImage.objects.filter(value_id__in=value_ids).update(value=None)
            # Quitar los enlaces variante→valor (libera el PROTECT) y el atributo.
            VariantValue.objects.filter(value_id__in=value_ids).delete()
            attr.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar valores de un atributo'),
    create=extend_schema(tags=CATALOG_TAG, summary='Crear valor (admin)'),
    update=extend_schema(tags=CATALOG_TAG, summary='Actualizar valor (admin)'),
    partial_update=extend_schema(tags=CATALOG_TAG, summary='Editar valor (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Eliminar valor (admin)'),
)
class AttributeValueViewSet(viewsets.ModelViewSet):
    """Valores de un atributo (?attribute=<id>)."""

    queryset = AttributeValue.objects.all()
    serializer_class = AttributeValueSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['attribute']
    ordering_fields = ['position', 'value']


@extend_schema_view(
    list=extend_schema(tags=CATALOG_TAG, summary='Listar imágenes de un producto'),
    create=extend_schema(tags=CATALOG_TAG, summary='Subir imagen de producto (admin)'),
    destroy=extend_schema(tags=CATALOG_TAG, summary='Eliminar imagen (admin)'),
)
class ProductImageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Galería de un producto. Cada imagen puede asociarse al valor del eje
    visual (p. ej. las fotos del 'Rojo'); sin valor son generales. Filtra por
    ?product=<id> y ?value=<id>.
    """

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'value']

    def perform_create(self, serializer):
        # Posición al final del grupo (producto + valor); tope por grupo.
        product = serializer.validated_data['product']
        value = serializer.validated_data.get('value')
        group = ProductImage.objects.filter(product=product, value=value)
        if group.count() >= ProductImage.MAX_PER_GROUP:
            raise DRFValidationError(
                f'Una galería admite hasta {ProductImage.MAX_PER_GROUP} imágenes.'
            )
        last = group.aggregate(m=models.Max('position'))['m']
        serializer.save(position=0 if last is None else last + 1)

    @extend_schema(
        tags=CATALOG_TAG,
        summary='Reordenar imágenes (admin)',
        request=ImageReorderSerializer,
        responses={200: ProductImageSerializer(many=True)},
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        serializer = ImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['order']
        with transaction.atomic():
            for position, image_id in enumerate(ids):
                ProductImage.objects.filter(pk=image_id).update(position=position)
        images = ProductImage.objects.filter(pk__in=ids)
        data = ProductImageSerializer(
            images, many=True, context=self.get_serializer_context()
        ).data
        return Response(data)
