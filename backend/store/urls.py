from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountPurchasesView,
    AccountSaleDetailView,
    AccountSaleReceiptView,
    AddressViewSet,
    CartItemViewSet,
    OrderViewSet,
    PaymentMethodViewSet,
    StaffOrderViewSet,
    StoreAttributeFiltersView,
    StoreBrandListView,
    StoreCategoryListView,
    WishlistViewSet,
    StorePointListView,
    StorePriceRangeView,
    StoreProductViewSet,
    StoreVariantStockView,
)

router = DefaultRouter()
router.register('store/products', StoreProductViewSet, basename='store-product')
router.register('account/addresses', AddressViewSet, basename='address')
router.register('account/payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register('account/cart', CartItemViewSet, basename='cart')
router.register('account/favorites', WishlistViewSet, basename='favorite')
router.register('account/orders', OrderViewSet, basename='order')
router.register('orders', StaffOrderViewSet, basename='staff-order')

urlpatterns = [
    path('store/categories/', StoreCategoryListView.as_view(), name='store-categories'),
    path('store/brands/', StoreBrandListView.as_view(), name='store-brands'),
    path('store/attribute-filters/', StoreAttributeFiltersView.as_view(), name='store-attribute-filters'),
    path('store/price-range/', StorePriceRangeView.as_view(), name='store-price-range'),
    path('store/variants/stock/', StoreVariantStockView.as_view(), name='store-variant-stock'),
    path('store/points/', StorePointListView.as_view(), name='store-points'),
    path('account/purchases/', AccountPurchasesView.as_view(), name='account-purchases'),
    path('account/purchases/sale/<int:pk>/', AccountSaleDetailView.as_view(), name='account-sale-detail'),
    path('account/purchases/sale/<int:pk>/send-receipt/', AccountSaleReceiptView.as_view(), name='account-sale-receipt'),
    *router.urls,
]
