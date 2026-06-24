from rest_framework.routers import DefaultRouter

from .views import (
    AttributeDefinitionViewSet,
    AttributeOptionViewSet,
    AttributeValueViewSet,
    BrandViewSet,
    CategoryViewSet,
    ColorViewSet,
    ProductAttributeViewSet,
    ProductImageViewSet,
    ProductVariantViewSet,
    ProductViewSet,
    SizeViewSet,
    SubcategoryViewSet,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('subcategories', SubcategoryViewSet, basename='subcategory')
router.register('brands', BrandViewSet, basename='brand')
router.register('colors', ColorViewSet, basename='color')
router.register('sizes', SizeViewSet, basename='size')
router.register('attribute-definitions', AttributeDefinitionViewSet, basename='attribute-definition')
router.register('attribute-options', AttributeOptionViewSet, basename='attribute-option')
router.register('products', ProductViewSet, basename='product')
router.register('variants', ProductVariantViewSet, basename='variant')
router.register('product-attributes', ProductAttributeViewSet, basename='product-attribute')
router.register('attribute-values', AttributeValueViewSet, basename='attribute-value')
router.register('product-images', ProductImageViewSet, basename='product-image')

urlpatterns = router.urls
