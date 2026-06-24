from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_customers_to_users(apps, schema_editor):
    """Convierte cada Customer en un usuario (rol comprador) y reapunta sus
    ventas. Reusa el usuario existente si coincide el correo o la identificación.
    """
    Customer = apps.get_model('sales', 'Customer')
    Sale = apps.get_model('sales', 'Sale')
    User = apps.get_model('accounts', 'User')

    for c in Customer.objects.all():
        email = (c.email or '').strip().lower() or None
        document = (c.document or '').strip()

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        if user is None and document:
            user = User.objects.filter(id_number=document).first()
        if user is None:
            user = User.objects.create(
                email=email,
                first_name=(c.name or 'Cliente')[:150],
                last_name='',
                role='comprador',
                is_active=c.is_active,
                is_email_verified=False,
                id_number=document,
                phone=(c.phone or '')[:40],
                password='!',  # contraseña inutilizable (cliente sin login)
            )
        Sale.objects.filter(customer_id=c.id).update(buyer_id=user.id)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0001_initial'),
        ('accounts', '0009_alter_user_options_user_id_number_user_id_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Nuevo FK temporal al usuario.
        migrations.AddField(
            model_name='sale',
            name='buyer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='purchases',
                to=settings.AUTH_USER_MODEL,
                verbose_name='cliente',
            ),
        ),
        # 2. Migra los datos (Customer -> User) y reapunta las ventas.
        migrations.RunPython(migrate_customers_to_users, noop),
        # 3. Quita el FK viejo a Customer y deja 'buyer' como 'customer'.
        migrations.RemoveField(model_name='sale', name='customer'),
        migrations.RenameField(model_name='sale', old_name='buyer', new_name='customer'),
        # 4. Elimina el modelo Customer (ya no se usa).
        migrations.DeleteModel(name='Customer'),
    ]
