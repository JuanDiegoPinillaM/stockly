from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from config.uploads import UploadToUUID


class CustomUserManager(BaseUserManager):
    """Manager de usuario que usa el correo como identificador (sin username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        # El correo es opcional: un cliente de mostrador (creado en el POS) puede
        # no tener cuenta ni correo. Si no hay correo, se guarda como NULL.
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio para un superusuario.')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_email_verified', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Un superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Un superusuario debe tener is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        WAREHOUSE_MANAGER = 'jefe_punto', 'Jefe de punto'
        CASHIER = 'cajero', 'Cajero'
        BUYER = 'comprador', 'Comprador'

    class IdType(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        CE = 'CE', 'Cédula de extranjería'
        NIT = 'NIT', 'NIT'
        PP = 'PP', 'Pasaporte'
        TI = 'TI', 'Tarjeta de identidad'

    # Roles del back-office (acceso al dashboard). El comprador NO entra al
    # dashboard: usa la tienda y su área de cuenta.
    STAFF_ROLES = (Role.ADMIN, Role.WAREHOUSE_MANAGER, Role.CASHIER)

    # Se elimina username: el login y la identidad son por correo. El correo es
    # OPCIONAL: un cliente de mostrador puede no tener cuenta (ver POS).
    username = None
    email = models.EmailField('correo electrónico', unique=True, null=True, blank=True)

    # Identificación (obligatoria al crear/editar desde la app; en blanco solo en
    # registros antiguos). El número es único cuando está definido y sirve como
    # llave de búsqueda del cliente en el POS.
    id_type = models.CharField(
        'tipo de identificación', max_length=8, choices=IdType.choices, blank=True, default=''
    )
    id_number = models.CharField('número de identificación', max_length=40, blank=True, default='')
    phone = models.CharField('teléfono', max_length=40, blank=True, default='')
    # El nombre es obligatorio: es lo que se muestra en toda la app.
    first_name = models.CharField('nombre', max_length=150)
    last_name = models.CharField('apellido', max_length=150, blank=True)
    role = models.CharField(
        'rol',
        max_length=20,
        choices=Role.choices,
        default=Role.BUYER,
    )
    avatar = models.ImageField(
        'foto de perfil', upload_to=UploadToUUID('avatars'), blank=True, null=True
    )
    # Bodega/punto asignado al personal (cajero o jefe de punto). El POS opera
    # SOLO sobre esta bodega; el admin no la necesita (vende en cualquiera).
    warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.SET_NULL,
        related_name='staff',
        verbose_name='bodega asignada',
        blank=True,
        null=True,
    )
    is_email_verified = models.BooleanField('correo verificado', default=False)
    # Cliente genérico de mostrador ("Consumidor final"): para ventas en las que
    # el comprador no quiere registrarse ni dar sus datos. Cumple la regla de que
    # toda venta tenga cliente. Hay exactamente uno y no se puede borrar.
    is_walk_in = models.BooleanField('consumidor final (mostrador)', default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        constraints = [
            # El número de identificación es único cuando está definido (los
            # vacíos no chocan, para registros antiguos sin él).
            models.UniqueConstraint(
                fields=['id_number'],
                condition=models.Q(id_number__gt=''),
                name='unique_id_number_when_set',
            ),
        ]

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff_member(self):
        """Puede entrar al back-office (admin, jefe de punto o cajero)."""
        return self.role in self.STAFF_ROLES

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def __str__(self):
        return f'{self.email} ({self.get_role_display()})'
