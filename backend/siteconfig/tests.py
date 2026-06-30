import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .colors import (
    INK_DARK, INK_LIGHT, hex_to_rgb, ink_on, palette, surfaces, text_tokens,
)
from .models import SiteConfig

User = get_user_model()


class ColorPaletteTests(SimpleTestCase):
    def test_hex_to_rgb_parses_both_forms(self):
        self.assertEqual(hex_to_rgb('#0e6e4e'), (14, 110, 78))
        self.assertEqual(hex_to_rgb('0e6e4e'), (14, 110, 78))
        self.assertEqual(hex_to_rgb('#abc'), (170, 187, 204))

    def test_palette_derives_full_set_of_tokens(self):
        tokens = palette('#0e6e4e', '#b8923a')
        # Devuelve las claves que el front inyecta como variables CSS.
        for key in (
            'color-primary', 'color-primary-rgb', 'color-primary-dark',
            'color-primary-light', 'color-primary-soft',
            'color-accent', 'color-accent-rgb', 'color-accent-dark', 'color-accent-soft',
        ):
            self.assertIn(key, tokens)
        self.assertEqual(tokens['color-primary'], '#0e6e4e')
        self.assertEqual(tokens['color-primary-rgb'], '14, 110, 78')
        # El tono "dark" es más oscuro y el "soft" más claro que el primario.
        self.assertLess(tokens['color-primary-dark'], tokens['color-primary'])
        self.assertGreater(tokens['color-primary-soft'], tokens['color-primary'])


class SurfaceTokenTests(SimpleTestCase):
    def test_ink_contrasts_with_background(self):
        # Fondo claro -> texto oscuro; fondo oscuro -> texto claro.
        self.assertEqual(ink_on('#ffffff'), INK_DARK)
        self.assertEqual(ink_on('#faf7f0'), INK_DARK)
        self.assertEqual(ink_on('#0e1a14'), INK_LIGHT)
        self.assertEqual(ink_on('#0e6e4e'), INK_LIGHT)

    def test_surfaces_default_to_current_look(self):
        t = surfaces()  # sin overrides
        self.assertEqual(t['color-navbar'], '#faf7f0')
        self.assertEqual(t['color-footer'], '#0e1a14')
        self.assertEqual(t['color-hero'], '#faf7f0')
        self.assertEqual(t['color-announce'], '#14201a')
        # Navbar crema -> texto oscuro; footer/anuncio oscuros -> texto claro.
        self.assertEqual(t['color-navbar-ink'], INK_DARK)
        self.assertEqual(t['color-footer-ink'], INK_LIGHT)
        self.assertEqual(t['color-announce-ink'], INK_LIGHT)

    def test_text_tokens_override_ink_and_body(self):
        self.assertEqual(text_tokens(''), {})  # sin color = sin cambios
        t = text_tokens('#222222')
        self.assertEqual(t['color-ink'], '#222222')
        self.assertEqual(t['color-ink-rgb'], '34, 34, 34')
        # El cuerpo se deriva más suave que la tinta.
        self.assertNotEqual(t['color-body'], t['color-ink'])

    def test_page_only_emitted_when_customized(self):
        # En automático NO se emite color-page (cada área conserva su fondo).
        self.assertNotIn('color-page', surfaces())
        # Personalizado sí, con su tinta de contraste.
        t = surfaces(page='#101010')
        self.assertEqual(t['color-page'], '#101010')
        self.assertEqual(t['color-page-ink'], INK_LIGHT)

    def test_surface_override_sets_contrasting_ink(self):
        t = surfaces(navbar='#0e6e4e')  # navbar oscuro elegido
        self.assertEqual(t['color-navbar'], '#0e6e4e')
        self.assertEqual(t['color-navbar-ink'], INK_LIGHT)
        # Expone el triple rgb para fondos translúcidos.
        self.assertEqual(t['color-navbar-rgb'], '14, 110, 78')


class SiteConfigApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Stockly2026',
            first_name='Admin', role=User.Role.ADMIN, is_email_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer@test.com', password='Stockly2026',
            first_name='Buyer', role=User.Role.BUYER, is_email_verified=True,
        )

    def test_singleton_always_pk_1(self):
        a = SiteConfig.load()
        b = SiteConfig.load()
        self.assertEqual(a.pk, 1)
        self.assertEqual(SiteConfig.objects.count(), 1)
        self.assertEqual(a.pk, b.pk)

    def test_get_is_public_and_returns_tokens(self):
        resp = self.client.get('/api/v1/config/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', resp.data)
        self.assertEqual(resp.data['business_name'], 'Stockly')
        self.assertIn('color-primary-soft', resp.data['tokens'])

    def test_non_admin_cannot_update(self):
        self.client.force_authenticate(self.buyer)
        resp = self.client.patch('/api/v1/config/', {'business_name': 'Hack'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_updates_brand_and_tokens_reflect(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/',
            {'business_name': 'Mi Tienda', 'color_primary': '#123456'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['business_name'], 'Mi Tienda')
        self.assertEqual(resp.data['tokens']['color-primary'], '#123456')
        self.assertEqual(resp.data['tokens']['color-primary-rgb'], '18, 52, 86')
        # Persiste como singleton.
        self.assertEqual(SiteConfig.load().business_name, 'Mi Tienda')

    def test_surface_override_reflects_in_tokens(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/', {'color_footer': '#ffffff'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['tokens']['color-footer'], '#ffffff')
        # Footer claro -> texto del footer oscuro (contraste automático).
        self.assertEqual(resp.data['tokens']['color-footer-ink'], '#14201a')

    def test_empty_surface_color_is_accepted_as_auto(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/', {'color_navbar': ''}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Vacío = automático -> usa el defecto crema.
        self.assertEqual(resp.data['tokens']['color-navbar'], '#faf7f0')

    def test_persists_fonts_announce_and_text_color(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/',
            {
                'announce_text': 'Hola mundo', 'font_heading': 'playfair',
                'font_body': 'poppins', 'color_text': '#333333',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['announce_text'], 'Hola mundo')
        self.assertEqual(resp.data['font_heading'], 'playfair')
        self.assertEqual(resp.data['font_body'], 'poppins')
        # El color de texto se refleja en los tokens (sobrescribe la tinta).
        self.assertEqual(resp.data['tokens']['color-ink'], '#333333')

    def test_invalid_hex_is_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/', {'color_primary': 'notacolor'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_sets_flexible_socials(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/',
            {'socials': [
                {'network': 'tiktok', 'url': 'https://tiktok.com/@x'},
                {'network': '', 'url': ''},  # fila vacía: se descarta
            ]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['socials'], [{'network': 'tiktok', 'url': 'https://tiktok.com/@x'}])

    def test_unsupported_social_network_is_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/',
            {'socials': [{'network': 'myspace', 'url': 'https://x.com'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_social_without_url_is_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(
            '/api/v1/config/',
            {'socials': [{'network': 'instagram', 'url': ''}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_logo_accepts_svg(self):
        self.client.force_authenticate(self.admin)
        svg = SimpleUploadedFile(
            'logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            content_type='image/svg+xml',
        )
        resp = self.client.patch('/api/v1/config/', {'logo': svg}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['logo'].endswith('.svg'))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_logo_rejects_unsupported_extension(self):
        self.client.force_authenticate(self.admin)
        bad = SimpleUploadedFile('logo.txt', b'hola', content_type='text/plain')
        resp = self.client.patch('/api/v1/config/', {'logo': bad}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nit_is_normalized_with_dots_and_dv(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.patch('/api/v1/config/', {'nit': '9001234567'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['nit'], '900.123.456-7')

    def test_receipt_business_reads_from_config(self):
        # El recibo de venta toma el emisor de la Configuración.
        from sales.emails import get_business
        c = SiteConfig.load()
        c.business_name = 'Mi Tienda Test'
        c.nit = '900.000.000-1'
        c.contact_email = 'hola@mitienda.test'
        c.contact_phone = '300 111 2233'
        c.contact_address = 'Calle 1, Medellín'
        c.save()
        b = get_business()
        self.assertEqual(b['name'], 'Mi Tienda Test')
        self.assertEqual(b['nit'], '900.000.000-1')
        self.assertEqual(b['email'], 'hola@mitienda.test')
        self.assertEqual(b['phone'], '300 111 2233')
        self.assertEqual(b['address'], 'Calle 1, Medellín')
