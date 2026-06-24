import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tokens import email_verification_token
from inventory.models import Warehouse

User = get_user_model()


def make_image(name='avatar.png'):
    buffer = BytesIO()
    Image.new('RGB', (10, 10), 'blue').save(buffer, 'PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


class AuthFlowTests(APITestCase):
    def setUp(self):
        # Resetea los contadores de throttling entre pruebas.
        cache.clear()

    def _create_user(self, verified=True, password='Stockly2026', **kwargs):
        kwargs.pop('username', None)  # username ya no existe en el modelo
        data = {'email': 'user1@test.com', 'first_name': 'Usuario'}
        data.update(kwargs)
        user = User(**data)
        user.set_password(password)
        user.is_email_verified = verified
        user.save()
        return user

    # ----------------------------- Registro -----------------------------
    def test_register_creates_unverified_user_and_sends_email(self):
        resp = self.client.post(
            reverse('register'),
            {
                'email': 'nuevo@test.com',
                'first_name': 'Nuevo',
                'id_type': 'CC',
                'id_number': '100100',
                'password': 'Stockly2026',
                'password2': 'Stockly2026',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(email='nuevo@test.com')
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.role, User.Role.BUYER)
        self.assertEqual(len(mail.outbox), 1)

    def test_register_rejects_duplicate_email(self):
        self._create_user(email='dup@test.com', username='dup')
        resp = self.client.post(
            reverse('register'),
            {
                'email': 'dup@test.com',
                'first_name': 'Otro',
                'id_type': 'CC',
                'id_number': '100101',
                'password': 'Stockly2026',
                'password2': 'Stockly2026',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_password_mismatch(self):
        resp = self.client.post(
            reverse('register'),
            {
                'email': 'x@test.com',
                'first_name': 'Equis',
                'id_type': 'CC',
                'id_number': '100102',
                'password': 'Stockly2026',
                'password2': 'OtraClave2026',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------------- Login -----------------------------
    def test_login_blocked_when_email_not_verified(self):
        self._create_user(verified=False, email='nv@test.com', username='nv')
        resp = self.client.post(
            reverse('login'),
            {'email': 'nv@test.com', 'password': 'Stockly2026'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp.data['code'], 'email_not_verified')

    def test_login_succeeds_when_verified(self):
        self._create_user(verified=True, email='v@test.com', username='v')
        resp = self.client.post(
            reverse('login'),
            {'email': 'v@test.com', 'password': 'Stockly2026'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertEqual(resp.data['user']['email'], 'v@test.com')

    def test_login_wrong_password(self):
        self._create_user(email='w@test.com', username='w')
        resp = self.client.post(
            reverse('login'),
            {'email': 'w@test.com', 'password': 'incorrecta'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ----------------------------- Verificación -----------------------------
    def test_verify_email_activates_account(self):
        user = self._create_user(verified=False, email='vf@test.com', username='vf')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        resp = self.client.post(
            reverse('verify_email'), {'uid': uid, 'token': token}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_verify_email_rejects_bad_token(self):
        user = self._create_user(verified=False, email='bad@test.com', username='bad')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        resp = self.client.post(
            reverse('verify_email'), {'uid': uid, 'token': 'token-falso'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    # ----------------------------- Logout / blacklist -----------------------------
    def test_logout_blacklists_refresh_token(self):
        self._create_user(email='lo@test.com', username='lo')
        login = self.client.post(
            reverse('login'),
            {'email': 'lo@test.com', 'password': 'Stockly2026'},
            format='json',
        )
        refresh = login.data['refresh']
        self.client.post(reverse('logout'), {'refresh': refresh}, format='json')
        # El refresh ya no debe servir para renovar.
        resp = self.client.post(reverse('token_refresh'), {'refresh': refresh}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ----------------------------- Reset de contraseña -----------------------------
    def test_password_reset_request_is_generic(self):
        resp = self.client.post(
            reverse('password_reset'), {'email': 'noexiste@test.com'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_password_reset_confirm_changes_password_and_revokes_sessions(self):
        user = self._create_user(email='rs@test.com', username='rs')
        login = self.client.post(
            reverse('login'),
            {'email': 'rs@test.com', 'password': 'Stockly2026'},
            format='json',
        )
        old_refresh = login.data['refresh']

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        resp = self.client.post(
            reverse('password_reset_confirm'),
            {
                'uid': uid,
                'token': token,
                'password': 'NuevaClave2026',
                'password2': 'NuevaClave2026',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # La nueva contraseña funciona.
        relogin = self.client.post(
            reverse('login'),
            {'email': 'rs@test.com', 'password': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(relogin.status_code, status.HTTP_200_OK)

        # Las sesiones anteriores quedaron revocadas.
        refresh_resp = self.client.post(
            reverse('token_refresh'), {'refresh': old_refresh}, format='json'
        )
        self.assertEqual(refresh_resp.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email='me@test.com', password='Stockly2026',
            first_name='Juan', last_name='Pérez', is_email_verified=True,
        )
        self._auth(self.user)

    def _auth(self, user):
        resp = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_me_returns_profile(self):
        resp = self.client.get(reverse('me'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['email'], 'me@test.com')
        self.assertEqual(resp.data['first_name'], 'Juan')

    def test_update_names(self):
        resp = self.client.patch(
            reverse('me'), {'first_name': 'Juana', 'last_name': 'Gómez'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Juana')
        self.assertFalse(resp.data['email_changed'])

    def test_changing_email_reverifies_and_sends_link(self):
        resp = self.client.patch(
            reverse('me'), {'email': 'nuevo@test.com'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['email_changed'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'nuevo@test.com')
        self.assertFalse(self.user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_must_be_unique(self):
        User.objects.create_user(
            email='taken@test.com', password='Stockly2026', first_name='X',
        )
        resp = self.client.patch(
            reverse('me'), {'email': 'taken@test.com'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_avatar(self):
        resp = self.client.patch(
            reverse('me'), {'avatar': make_image()}, format='multipart'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp.data['avatar'])

    def test_remove_avatar(self):
        self.client.patch(reverse('me'), {'avatar': make_image()}, format='multipart')
        resp = self.client.patch(reverse('me'), {'avatar': None}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data['avatar'])
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.avatar))

    def test_change_password_requires_current(self):
        resp = self.client.post(
            reverse('change_password'),
            {'current_password': 'incorrecta', 'password': 'NuevaClave2026', 'password2': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_works(self):
        resp = self.client.post(
            reverse('change_password'),
            {'current_password': 'Stockly2026', 'password': 'NuevaClave2026', 'password2': 'NuevaClave2026'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave2026'))

    def test_profile_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get(reverse('me')).status_code, 401)


class SuperuserTests(APITestCase):
    def test_superuser_is_admin_and_verified(self):
        admin = User.objects.create_superuser(
            email='root@test.com', password='Stockly2026', first_name='Root'
        )
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_email_verified)


class UserManagementTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Stockly2026',
            first_name='Ana', role=User.Role.ADMIN, is_email_verified=True,
        )
        self.other = User.objects.create_user(
            email='bob@test.com', password='Stockly2026',
            first_name='Bob', role=User.Role.CASHIER, is_email_verified=True,
        )

    def _auth(self, user):
        resp = self.client.post(
            reverse('login'),
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_non_admin_cannot_list_users(self):
        self._auth(self.other)
        self.assertEqual(self.client.get('/api/v1/users/').status_code, 403)

    def test_admin_lists_users(self):
        self._auth(self.admin)
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 2)

    def test_admin_creates_user_and_sends_invitation(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/users/',
            {'email': 'nuevo@test.com', 'first_name': 'Nuevo', 'role': 'cajero',
             'id_type': 'CC', 'id_number': '900900'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(email='nuevo@test.com')
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)

    def test_create_requires_first_name(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/users/', {'email': 'x@test.com', 'role': 'cajero'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_only_deactivates_user(self):
        self._auth(self.admin)
        resp = self.client.delete(f'/api/v1/users/{self.other.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_active)

    def test_admin_cannot_deactivate_self(self):
        self._auth(self.admin)
        resp = self.client.delete(f'/api/v1/users/{self.admin.id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['code'], 'self_action_forbidden')

    def test_admin_can_change_role(self):
        self._auth(self.admin)
        resp = self.client.patch(
            f'/api/v1/users/{self.other.id}/', {'role': 'admin'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.other.refresh_from_db()
        self.assertEqual(self.other.role, User.Role.ADMIN)

    def test_admin_assigns_warehouse_to_cashier(self):
        warehouse = Warehouse.objects.create(name='Principal')
        self._auth(self.admin)
        resp = self.client.patch(
            f'/api/v1/users/{self.other.id}/',
            {'warehouse': warehouse.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['warehouse'], warehouse.id)
        self.assertEqual(resp.data['warehouse_name'], 'Principal')
        self.other.refresh_from_db()
        self.assertEqual(self.other.warehouse_id, warehouse.id)

    def test_me_exposes_assigned_warehouse(self):
        warehouse = Warehouse.objects.create(name='Principal')
        self.other.warehouse = warehouse
        self.other.save(update_fields=['warehouse'])
        self._auth(self.other)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['warehouse'], warehouse.id)
        self.assertEqual(resp.data['warehouse_name'], 'Principal')
