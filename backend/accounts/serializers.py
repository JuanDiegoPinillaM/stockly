from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .tokens import email_verification_token

User = get_user_model()


def validate_unique_id_number(value, instance=None):
    """El número de identificación es obligatorio y único por persona."""
    value = (value or '').strip()
    if not value:
        raise serializers.ValidationError('El número de identificación es obligatorio.')
    qs = User.objects.filter(id_number=value)
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError('Ya existe alguien con este número de identificación.')
    return value


# Campos de identificación compartidos por los serializers de cuenta.
ID_EXTRA_KWARGS = {
    'id_type': {'required': True, 'allow_blank': False},
    'id_number': {'required': True, 'allow_blank': False},
    'phone': {'required': False, 'allow_blank': True},
}


class EmailNotVerified(AuthenticationFailed):
    default_detail = 'Debes confirmar tu correo antes de iniciar sesión.'
    default_code = 'email_not_verified'


class UserSerializer(serializers.ModelSerializer):
    """Representación pública del usuario que consume el frontend."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)
    avatar = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(
        source='warehouse.name', read_only=True, default=None
    )

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        url = obj.avatar.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'avatar',
            'id_type', 'id_type_display', 'id_number', 'phone',
            'role', 'role_display', 'is_email_verified',
            'warehouse', 'warehouse_name',
        ]
        read_only_fields = [
            'id', 'avatar', 'id_type_display', 'role', 'role_display',
            'is_email_verified', 'warehouse', 'warehouse_name',
        ]


class ProfileSerializer(serializers.ModelSerializer):
    """El usuario edita su propio perfil: nombre, apellido, correo y foto."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
    warehouse_name = serializers.CharField(
        source='warehouse.name', read_only=True, default=None
    )
    # Señala al frontend si el cambio de correo disparó re-verificación.
    email_changed = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'avatar',
            'id_type', 'id_type_display', 'id_number', 'phone',
            'role', 'role_display', 'is_email_verified', 'email_changed',
            'warehouse', 'warehouse_name',
        ]
        read_only_fields = [
            'id', 'id_type_display', 'role', 'role_display', 'is_email_verified',
            'warehouse', 'warehouse_name',
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            **ID_EXTRA_KWARGS,
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if instance.avatar and request:
            data['avatar'] = request.build_absolute_uri(instance.avatar.url)
        return data

    def validate_email(self, value):
        value = value.lower()
        qs = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    def validate_id_number(self, value):
        return validate_unique_id_number(value, instance=self.instance)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual no es correcta.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'Las contraseñas no coinciden.'})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password'])
        user.save(update_fields=['password'])
        return user


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'id_type', 'id_number', 'phone', 'password', 'password2',
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            **ID_EXTRA_KWARGS,
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value.lower()

    def validate_id_number(self, value):
        return validate_unique_id_number(value)

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password2': 'Las contraseñas no coinciden.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        # El registro público crea COMPRADORES (clientes de la tienda) sin verificar.
        user = User(role=User.Role.BUYER, is_email_verified=False, **validated_data)
        user.set_password(password)
        user.save()
        return user


class UserAdminSerializer(serializers.ModelSerializer):
    """Lectura/edición de un usuario desde el módulo de Usuarios (admin)."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(
        source='warehouse.name', read_only=True, default=None
    )

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        url = obj.avatar.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'avatar',
            'id_type', 'id_type_display', 'id_number', 'phone',
            'role', 'role_display', 'is_active', 'is_email_verified',
            'warehouse', 'warehouse_name', 'date_joined', 'last_login',
        ]
        read_only_fields = [
            'id', 'role_display', 'id_type_display', 'full_name', 'avatar',
            'warehouse_name', 'is_email_verified', 'date_joined', 'last_login',
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            'warehouse': {'required': False, 'allow_null': True},
            **ID_EXTRA_KWARGS,
        }

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value.lower()

    def validate_id_number(self, value):
        return validate_unique_id_number(value, instance=self.instance)


class UserCreateSerializer(serializers.ModelSerializer):
    """Alta de usuario por el admin. No fija contraseña: se invita por correo."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'id_type', 'id_number', 'phone', 'role', 'warehouse',
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            'warehouse': {'required': False, 'allow_null': True},
            **ID_EXTRA_KWARGS,
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value.lower()

    def validate_id_number(self, value):
        return validate_unique_id_number(value)

    def create(self, validated_data):
        # Cuenta activa pero sin verificar; la contraseña la fija el usuario
        # al aceptar la invitación (enlace por correo).
        user = User(is_active=True, is_email_verified=False, **validated_data)
        user.set_unusable_password()
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Añade el rol al token, bloquea cuentas sin verificar y devuelve el usuario."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_email_verified:
            raise EmailNotVerified()
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


# ------------------------- Verificación de correo -------------------------

def _user_from_uid(uid):
    """Decodifica el uid en base64 y devuelve el usuario, o None si es inválido."""
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = _user_from_uid(attrs['uid'])
        if user is None:
            raise serializers.ValidationError('El enlace no es válido.')
        if user.is_email_verified:
            self.context['already'] = True
            self.user = user
            return attrs
        if not email_verification_token.check_token(user, attrs['token']):
            raise serializers.ValidationError('El enlace expiró o ya fue usado.')
        self.user = user
        return attrs

    def save(self):
        if not self.context.get('already'):
            self.user.is_email_verified = True
            self.user.save(update_fields=['is_email_verified'])
        return self.user


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(validators=[validate_password])
    password2 = serializers.CharField()

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'Las contraseñas no coinciden.'})
        user = _user_from_uid(attrs['uid'])
        if user is None or not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError('El enlace no es válido o expiró.')
        self.user = user
        return attrs

    def save(self):
        self.user.set_password(self.validated_data['password'])
        # Acceder por el enlace prueba la titularidad del correo: queda verificado
        # (sirve también para aceptar invitaciones de usuarios nuevos).
        self.user.is_email_verified = True
        self.user.save(update_fields=['password', 'is_email_verified'])
        return self.user
