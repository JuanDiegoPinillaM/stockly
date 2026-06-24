from django.db import migrations


def create_default_variants(apps, schema_editor):
    """Crea una variante por cada producto existente heredando sus campos.

    Mueve el inventario (sku, precios, stock, color, talla) al nivel de
    variante. Se ejecuta antes de eliminar esos campos de Product.
    """
    Product = apps.get_model('catalog', 'Product')
    ProductVariant = apps.get_model('catalog', 'ProductVariant')
    for product in Product.objects.all():
        ProductVariant.objects.create(
            product=product,
            sku=product.sku,
            cost_price=product.cost_price,
            sale_price=product.sale_price,
            stock=product.stock,
            color_id=product.color_id,
            size_id=product.size_id,
            is_active=product.is_active,
        )


def delete_variants(apps, schema_editor):
    ProductVariant = apps.get_model('catalog', 'ProductVariant')
    ProductVariant.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0008_productvariant'),
    ]

    operations = [
        migrations.RunPython(create_default_variants, delete_variants),
    ]
