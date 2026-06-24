from django.db import migrations


def seed_initial_stock(apps, schema_editor):
    """Activa el inventario sobre los datos existentes.

    Crea la bodega "Principal", lleva el stock actual de cada variante a su
    nivel en esa bodega y registra un movimiento de saldo inicial para que el
    kardex cuadre. El costo promedio inicial = costo de referencia.
    """
    Warehouse = apps.get_model('inventory', 'Warehouse')
    StockLevel = apps.get_model('inventory', 'StockLevel')
    StockMovement = apps.get_model('inventory', 'StockMovement')
    ProductVariant = apps.get_model('catalog', 'ProductVariant')

    if not ProductVariant.objects.exists():
        return

    warehouse, _ = Warehouse.objects.get_or_create(
        name='Principal', defaults={'code': 'PRIN'}
    )
    for variant in ProductVariant.objects.all():
        if not variant.average_cost:
            variant.average_cost = variant.cost_price
            variant.save(update_fields=['average_cost'])
        if variant.stock and variant.stock > 0:
            StockLevel.objects.get_or_create(
                variant=variant,
                warehouse=warehouse,
                defaults={'quantity': variant.stock},
            )
            StockMovement.objects.create(
                variant=variant,
                warehouse=warehouse,
                type='entrada',
                reason='saldo_inicial',
                quantity=variant.stock,
                unit_cost=variant.cost_price,
                total_cost=variant.cost_price * variant.stock,
                balance_after=variant.stock,
                note='Saldo inicial al activar el inventario',
            )


def unseed(apps, schema_editor):
    apps.get_model('inventory', 'StockMovement').objects.all().delete()
    apps.get_model('inventory', 'StockLevel').objects.all().delete()
    apps.get_model('inventory', 'Warehouse').objects.filter(name='Principal').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial'),
        ('catalog', '0011_productvariant_average_cost_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_initial_stock, unseed),
    ]
