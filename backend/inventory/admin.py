from django.contrib import admin

from .models import StockLevel, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ['variant', 'warehouse', 'quantity']
    list_filter = ['warehouse']
    search_fields = ['variant__sku', 'variant__product__name']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'type', 'variant', 'warehouse', 'quantity',
        'unit_cost', 'balance_after',
    ]
    list_filter = ['type', 'reason', 'warehouse']
    search_fields = ['variant__sku', 'variant__product__name', 'reference']
    # Libro inmutable: no se edita ni se borra desde el admin.
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
