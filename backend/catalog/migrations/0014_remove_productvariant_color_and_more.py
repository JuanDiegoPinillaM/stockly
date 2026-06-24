# Refactor de variantes: de color/talla fijos a atributos N flexibles, con
# fotos por valor del eje visual. Crea los modelos nuevos, migra los datos
# existentes (color/talla -> atributos; VariantImage -> ProductImage) y al final
# elimina los campos/modelo viejos.

import config.uploads
import django.db.models.deletion
from django.db import migrations, models


def migrate_to_attributes(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    VariantImage = apps.get_model('catalog', 'VariantImage')
    ProductAttribute = apps.get_model('catalog', 'ProductAttribute')
    AttributeValue = apps.get_model('catalog', 'AttributeValue')
    VariantValue = apps.get_model('catalog', 'VariantValue')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    Color = apps.get_model('catalog', 'Color')
    Size = apps.get_model('catalog', 'Size')

    for product in Product.objects.all():
        variants = list(product.variants.all())
        if not variants:
            continue

        has_color = any(v.color_id for v in variants)
        has_size = any(v.size_id for v in variants)

        color_attr = None
        size_attr = None
        if has_color:
            color_attr = ProductAttribute.objects.create(
                product=product, name='Color', position=0, is_image_axis=True
            )
        if has_size:
            size_attr = ProductAttribute.objects.create(
                product=product, name='Talla', position=1, is_image_axis=False
            )

        color_values = {}  # Color.id -> AttributeValue
        size_values = {}   # Size.id -> AttributeValue

        def color_value(cid):
            if cid not in color_values:
                c = Color.objects.get(pk=cid)
                color_values[cid] = AttributeValue.objects.create(
                    attribute=color_attr, value=c.name,
                    swatch_hex=(c.hex_code or ''), position=len(color_values),
                )
            return color_values[cid]

        def size_value(sid):
            if sid not in size_values:
                s = Size.objects.get(pk=sid)
                size_values[sid] = AttributeValue.objects.create(
                    attribute=size_attr, value=s.name, position=len(size_values),
                )
            return size_values[sid]

        for v in variants:
            if v.color_id:
                VariantValue.objects.create(variant=v, value=color_value(v.color_id))
            if v.size_id:
                VariantValue.objects.create(variant=v, value=size_value(v.size_id))

        # Mueve las fotos: las de cada variante pasan al producto, asociadas al
        # valor de su color (eje visual). Se reutiliza el archivo (mismo path) y
        # se deduplica por (color, archivo) para no repetir fotos entre tallas.
        seen = set()
        for v in variants:
            cval = color_values.get(v.color_id) if v.color_id else None
            for img in VariantImage.objects.filter(variant=v).order_by('position', 'id'):
                key = (cval.id if cval else None, img.image)
                if key in seen:
                    continue
                seen.add(key)
                pos = ProductImage.objects.filter(product=product, value=cval).count()
                ProductImage.objects.create(
                    product=product, value=cval, image=img.image,
                    alt_text=img.alt_text, position=pos,
                )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0013_alter_variantimage_image'),
    ]

    operations = [
        # 1) Crear los modelos nuevos.
        migrations.CreateModel(
            name='ProductAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, verbose_name='nombre')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='orden')),
                ('is_image_axis', models.BooleanField(default=False, verbose_name='eje de las fotos')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attributes', to='catalog.product', verbose_name='producto')),
            ],
            options={
                'verbose_name': 'atributo de producto',
                'verbose_name_plural': 'atributos de producto',
                'ordering': ['position', 'id'],
            },
        ),
        migrations.CreateModel(
            name='AttributeValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=80, verbose_name='valor')),
                ('swatch_hex', models.CharField(blank=True, default='', max_length=7, verbose_name='HEX')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='orden')),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='catalog.productattribute', verbose_name='atributo')),
            ],
            options={
                'verbose_name': 'valor de atributo',
                'verbose_name_plural': 'valores de atributo',
                'ordering': ['position', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=config.uploads.UploadToUUID('products'), verbose_name='imagen')),
                ('alt_text', models.CharField(blank=True, max_length=160, verbose_name='texto alternativo')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='orden')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.product', verbose_name='producto')),
                ('value', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.attributevalue', verbose_name='valor (eje visual)')),
            ],
            options={
                'verbose_name': 'imagen de producto',
                'verbose_name_plural': 'imágenes de producto',
                'ordering': ['position', 'id'],
            },
        ),
        migrations.CreateModel(
            name='VariantValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='variant_values', to='catalog.attributevalue', verbose_name='valor')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='catalog.productvariant', verbose_name='variante')),
            ],
            options={
                'verbose_name': 'valor de variante',
                'verbose_name_plural': 'valores de variante',
            },
        ),
        migrations.AddConstraint(
            model_name='productattribute',
            constraint=models.UniqueConstraint(fields=('product', 'name'), name='unique_attribute_name_per_product'),
        ),
        migrations.AddConstraint(
            model_name='attributevalue',
            constraint=models.UniqueConstraint(fields=('attribute', 'value'), name='unique_value_per_attribute'),
        ),
        migrations.AddConstraint(
            model_name='variantvalue',
            constraint=models.UniqueConstraint(fields=('variant', 'value'), name='unique_value_per_variant'),
        ),
        # 2) Migrar los datos existentes a la nueva estructura.
        migrations.RunPython(migrate_to_attributes, noop),
        # 3) Eliminar lo viejo.
        migrations.RemoveField(model_name='productvariant', name='color'),
        migrations.RemoveField(model_name='productvariant', name='size'),
        migrations.DeleteModel(name='VariantImage'),
    ]
