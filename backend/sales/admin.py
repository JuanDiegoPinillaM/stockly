from django.contrib import admin

from .models import Sale, SaleItem, SalePayment


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    can_delete = False
    readonly_fields = ['variant', 'description', 'sku', 'quantity', 'unit_price', 'tax_rate', 'unit_cost', 'line_total']


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['number', 'customer', 'warehouse', 'status', 'total', 'created_at']
    list_filter = ['status', 'warehouse', 'created_at']
    search_fields = ['number', 'customer__id_number', 'customer__first_name', 'customer__email']
    readonly_fields = ['number', 'subtotal', 'tax_total', 'total', 'paid', 'change', 'created_at']
    inlines = [SaleItemInline, SalePaymentInline]
