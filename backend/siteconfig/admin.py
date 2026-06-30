from django.contrib import admin

from .models import SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'color_primary', 'color_accent', 'updated_at']

    def has_add_permission(self, request):
        # Singleton: no se crean más instancias desde el admin.
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
