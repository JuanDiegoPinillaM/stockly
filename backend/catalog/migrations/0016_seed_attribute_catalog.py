from django.db import migrations


def seed_catalog(apps, schema_editor):
    """Crea el catálogo de atributos a partir de las librerías Color y Size, y
    enlaza los atributos de producto existentes (Color/Talla) con su definición.
    """
    Color = apps.get_model('catalog', 'Color')
    Size = apps.get_model('catalog', 'Size')
    AttributeDefinition = apps.get_model('catalog', 'AttributeDefinition')
    AttributeOption = apps.get_model('catalog', 'AttributeOption')
    ProductAttribute = apps.get_model('catalog', 'ProductAttribute')

    color_def = None
    colors = list(Color.objects.all().order_by('name'))
    if colors:
        color_def = AttributeDefinition.objects.create(
            name='Color', has_swatch=True, position=0
        )
        for i, c in enumerate(colors):
            AttributeOption.objects.create(
                definition=color_def,
                value=c.name,
                swatch_hex=(c.hex_code or '').upper(),
                position=i,
                is_active=c.is_active,
            )

    size_def = None
    sizes = list(Size.objects.all().order_by('position', 'name'))
    if sizes:
        size_def = AttributeDefinition.objects.create(
            name='Talla', has_swatch=False, position=1
        )
        for i, s in enumerate(sizes):
            AttributeOption.objects.create(
                definition=size_def,
                value=s.name,
                position=s.position or i,
                is_active=s.is_active,
            )

    # Enlaza los atributos de producto existentes por nombre con su definición.
    if color_def:
        ProductAttribute.objects.filter(name__iexact='Color', definition__isnull=True).update(
            definition=color_def
        )
    if size_def:
        ProductAttribute.objects.filter(name__iexact='Talla', definition__isnull=True).update(
            definition=size_def
        )


def unseed_catalog(apps, schema_editor):
    AttributeDefinition = apps.get_model('catalog', 'AttributeDefinition')
    AttributeDefinition.objects.filter(name__in=['Color', 'Talla']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0015_attributedefinition_productattribute_definition_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
