from django.db import migrations


def user_to_comprador(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='user').update(role='comprador')


def comprador_to_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='comprador').update(role='user')


class Migration(migrations.Migration):
    """Migra el rol antiguo 'user' al nuevo 'comprador'."""

    dependencies = [
        ('accounts', '0006_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(user_to_comprador, comprador_to_user),
    ]
