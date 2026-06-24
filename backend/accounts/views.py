import logging

from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import filters, generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .emails import (
    send_invitation_email,
    send_password_reset_email,
    send_verification_email,
)
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserAdminSerializer,
    UserCreateSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

AUTH_TAG = ['Autenticación']

# Respuesta estándar { "message": "..." } reutilizada en varios endpoints.
MessageResponse = inline_serializer(
    name='MessageResponse',
    fields={'message': serializers.CharField()},
)


def _safe_send(send_func, user):
    """Envía un correo sin tumbar el request si el SMTP falla."""
    try:
        send_func(user)
        return True
    except Exception:
        logger.exception('Fallo al enviar correo a %s', user.email)
        return False


@extend_schema(
    tags=AUTH_TAG,
    summary='Registrar una cuenta nueva',
    responses={201: inline_serializer(
        name='RegisterResponse',
        fields={
            'user': UserSerializer(),
            'email_sent': serializers.BooleanField(),
            'message': serializers.CharField(),
        },
    )},
)
class RegisterView(generics.CreateAPIView):
    """Crea la cuenta con rol 'user' y envía el correo de verificación."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        email_sent = _safe_send(send_verification_email, user)
        message = (
            'Cuenta creada. Revisa tu correo para activarla.'
            if email_sent
            else 'Cuenta creada, pero no pudimos enviar el correo. Intenta reenviarlo.'
        )
        return Response(
            {'user': UserSerializer(user).data, 'email_sent': email_sent, 'message': message},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=AUTH_TAG, summary='Iniciar sesión (obtener tokens JWT)')
class LoginView(TokenObtainPairView):
    """Devuelve access, refresh y los datos del usuario."""

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class LogoutView(APIView):
    """Invalida el refresh token (blacklist)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=AUTH_TAG,
        summary='Cerrar sesión (invalidar refresh token)',
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': serializers.CharField()},
        ),
        responses={200: MessageResponse},
    )
    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass  # token ya inválido o expirado: nada que invalidar
        return Response({'message': 'Sesión cerrada.'})


@extend_schema_view(
    get=extend_schema(tags=AUTH_TAG, summary='Perfil del usuario autenticado'),
    patch=extend_schema(tags=AUTH_TAG, summary='Actualizar mi perfil (nombre, correo, foto)'),
)
class MeView(generics.RetrieveUpdateAPIView):
    """Lee y edita el perfil del usuario autenticado.

    Cambiar el correo marca la cuenta como no verificada y reenvía el enlace de
    confirmación al nuevo correo.
    """

    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        old_email = user.email
        partial = kwargs.pop('partial', True)
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data.get('email', old_email)
        email_changed = bool(new_email) and new_email.lower() != old_email.lower()
        instance = serializer.save()
        if email_changed:
            instance.is_email_verified = False
            instance.save(update_fields=['is_email_verified'])
            _safe_send(send_verification_email, instance)
        data = self.get_serializer(instance).data
        data['email_changed'] = email_changed
        return Response(data)


class ChangePasswordView(APIView):
    """El usuario autenticado cambia su contraseña (pide la actual)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=AUTH_TAG,
        summary='Cambiar mi contraseña',
        request=ChangePasswordSerializer,
        responses={200: MessageResponse},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Tu contraseña fue actualizada.'})


class VerifyEmailView(APIView):
    """Activa la cuenta con uid + token."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=AUTH_TAG,
        summary='Verificar correo y activar la cuenta',
        request=VerifyEmailSerializer,
        responses={200: MessageResponse},
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Tu cuenta fue verificada correctamente.'})


class ResendVerificationView(APIView):
    """Reenvía el correo de activación."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'resend_verification'

    @extend_schema(
        tags=AUTH_TAG,
        summary='Reenviar correo de verificación',
        request=ResendVerificationSerializer,
        responses={200: MessageResponse},
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user and not user.is_email_verified:
            _safe_send(send_verification_email, user)
        # Respuesta genérica para no revelar qué correos existen.
        return Response({'message': 'Si la cuenta existe y no está verificada, enviamos un correo.'})


class PasswordResetRequestView(APIView):
    """Envía el correo de restablecimiento de contraseña."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(
        tags=AUTH_TAG,
        summary='Solicitar restablecimiento de contraseña',
        request=PasswordResetRequestSerializer,
        responses={200: MessageResponse},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user:
            _safe_send(send_password_reset_email, user)
        # Respuesta genérica para evitar enumeración de correos.
        return Response({'message': 'Si el correo está registrado, enviamos un enlace.'})


USERS_TAG = ['Usuarios']


def _self_action_blocked(detail):
    return Response(
        {'detail': detail, 'code': 'self_action_forbidden', 'errors': None},
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema_view(
    list=extend_schema(tags=USERS_TAG, summary='Listar usuarios (admin)'),
    retrieve=extend_schema(tags=USERS_TAG, summary='Ver un usuario (admin)'),
    create=extend_schema(tags=USERS_TAG, summary='Crear usuario e invitar por correo (admin)'),
    update=extend_schema(tags=USERS_TAG, summary='Actualizar usuario (admin)'),
    partial_update=extend_schema(tags=USERS_TAG, summary='Editar usuario (admin)'),
    destroy=extend_schema(tags=USERS_TAG, summary='Desactivar usuario (admin)'),
)
class UserViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios para el panel admin.

    Crear envía una invitación por correo (el usuario fija su contraseña).
    Eliminar desactiva (is_active=False); reactivar = PATCH is_active=true.
    """

    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_email_verified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email', 'first_name']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserAdminSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        email_sent = _safe_send(send_invitation_email, user)
        data = UserAdminSerializer(user).data
        data['email_sent'] = email_sent
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Un admin no puede desactivarse ni quitarse el rol admin a sí mismo.
        if instance.pk == request.user.pk:
            if request.data.get('is_active') is False:
                return _self_action_blocked('No puedes desactivar tu propia cuenta.')
            if request.data.get('role') and request.data['role'] != instance.role:
                return _self_action_blocked('No puedes cambiar tu propio rol.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            return _self_action_blocked('No puedes eliminar tu propia cuenta.')
        if instance.is_active:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=USERS_TAG,
        summary='Reenviar invitación / enlace para fijar contraseña (admin)',
        request=None,
        responses={200: MessageResponse},
    )
    @action(detail=True, methods=['post'], url_path='resend-invitation')
    def resend_invitation(self, request, pk=None):
        user = self.get_object()
        _safe_send(send_invitation_email, user)
        return Response({'message': 'Invitación reenviada si el correo es válido.'})


class PasswordResetConfirmView(APIView):
    """Fija la nueva contraseña e invalida las sesiones existentes."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=AUTH_TAG,
        summary='Confirmar nueva contraseña',
        request=PasswordResetConfirmSerializer,
        responses={200: MessageResponse},
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Seguridad: invalida todas las sesiones (refresh tokens) existentes.
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        logger.info('Contraseña restablecida para %s; sesiones invalidadas.', user.email)
        return Response({'message': 'Tu contraseña fue actualizada. Ya puedes iniciar sesión.'})
