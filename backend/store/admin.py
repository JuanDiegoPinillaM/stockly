from django.contrib import admin

from .models import Address, CartItem, Order, OrderItem, SavedPaymentMethod, WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'value', 'created_at']
    search_fields = ['user__email', 'product__name']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'user', 'city', 'is_default']
    search_fields = ['recipient', 'user__email', 'line1']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'variant', 'quantity', 'updated_at']
    search_fields = ['user__email', 'variant__sku']


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['label', 'kind', 'user', 'is_default']
    list_filter = ['kind']
    search_fields = ['label', 'user__email']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [
        'variant', 'description', 'sku', 'quantity',
        'unit_price', 'tax_rate', 'unit_cost', 'line_total',
    ]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['number', 'user', 'warehouse', 'status', 'total', 'is_paid', 'created_at']
    list_filter = ['status', 'fulfillment', 'is_paid', 'warehouse']
    search_fields = ['number', 'user__email', 'ship_recipient']
    inlines = [OrderItemInline]
    readonly_fields = ['number', 'created_at', 'updated_at']
