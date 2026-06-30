from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_walk_in(apps, schema_editor):
    """Crea el cliente genérico de mostrador ("Consumidor final").

    Se usa en el POS para ventas sin datos del comprador. NIT 222.222.222.222 es
    el código de "consumidor final" de la DIAN en Colombia. Contraseña inutilizable
    (no es una cuenta con la que se inicie sesión).
    """
    User = apps.get_model('accounts', 'User')
    if User.objects.filter(is_walk_in=True).exists():
        return
    User.objects.update_or_create(
        id_number='222222222222',
        defaults={
            'is_walk_in': True,
            'role': 'comprador',
            'id_type': 'NIT',
            'first_name': 'Consumidor final',
            'last_name': '',
            'email': None,
            'is_active': True,
            'is_email_verified': False,
            'password': make_password(None),
        },
    )


def remove_walk_in(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(is_walk_in=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_user_is_walk_in'),
    ]

    operations = [
        migrations.RunPython(create_walk_in, remove_walk_in),
    ]
