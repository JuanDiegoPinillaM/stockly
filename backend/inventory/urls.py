from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    LowStockView,
    StockLevelViewSet,
    StockMovementViewSet,
    StockValuationView,
    TransferViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('movements', StockMovementViewSet, basename='movement')
router.register('stock-levels', StockLevelViewSet, basename='stock-level')
router.register('transfers', TransferViewSet, basename='transfer')

urlpatterns = [
    path('stock/', StockValuationView.as_view(), name='stock-valuation'),
    path('low-stock/', LowStockView.as_view(), name='low-stock'),
    *router.urls,
]
