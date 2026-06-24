import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Las imágenes pasan del producto a la variante.

    La relación cambia de naturaleza (un ProductImage del producto no sabe a
    qué variante pertenece), así que no hay datos que migrar: se elimina la
    tabla antigua y se crea la nueva colgando de ProductVariant.
    """

    dependencies = [
        ('catalog', '0011_productvariant_average_cost_and_more'),
    ]

    operations = [
        migrations.DeleteModel(name='ProductImage'),
        migrations.CreateModel(
            name='VariantImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='variants/', verbose_name='imagen')),
                ('alt_text', models.CharField(blank=True, max_length=160, verbose_name='texto alternativo')),
                ('position', models.PositiveIntegerField(default=0, verbose_name='orden')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.productvariant', verbose_name='variante')),
            ],
            options={
                'verbose_name': 'imagen de variante',
                'verbose_name_plural': 'imágenes de variante',
                'ordering': ['position', 'id'],
            },
        ),
    ]
