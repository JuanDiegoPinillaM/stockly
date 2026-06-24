from django.contrib import admin

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
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


class AttributeOptionInline(admin.TabularInline):
    model = AttributeOption
    extra = 1


@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'has_swatch', 'position', 'is_active']
    list_filter = ['is_active', 'has_swatch']
    search_fields = ['name']
    ordering = ['position', 'name']
    inlines = [AttributeOptionInline]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'hex_code']


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['position']


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 0
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubcategoryInline]


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'definition', 'is_image_axis', 'position']
    list_filter = ['is_image_axis']
    search_fields = ['name', 'product__name']
    inlines = [AttributeValueInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'subcategory', 'is_active']
    list_filter = ['is_active', 'brand', 'subcategory__category', 'subcategory']
    search_fields = ['name', 'variants__sku']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['sku', 'product', 'options_label', 'sale_price', 'stock', 'is_active']
    list_filter = ['is_active']
    search_fields = ['sku', 'barcode', 'product__name']
