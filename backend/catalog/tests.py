import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import (
    AttributeValue,
    Brand,
    Category,
    Color,
    Product,
    ProductAttribute,
    ProductImage,
    ProductVariant,
    Size,
    Subcategory,
    VariantValue,
)

User = get_user_model()


def make_image(name='test.png'):
    """Genera una imagen PNG válida en memoria para las pruebas de subida."""
    buffer = BytesIO()
    Image.new('RGB', (10, 10), 'red').save(buffer, 'PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


class CatalogTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = self._user('admin@test.com', 'admin', User.Role.ADMIN)
        self.user = self._user('user@test.com', 'user', User.Role.CASHIER)
        self.category = Category.objects.create(name='Ropa')
        self.subcategory = Subcategory.objects.create(
            category=self.category, name='Camisetas'
        )

    def _user(self, email, username, role):
        u = User(email=email, first_name=username, role=role, is_email_verified=True)
        u.set_password('Stockly2026')
        u.save()
        return u

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        token = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class CategoryTests(CatalogTestBase):
    def test_anonymous_cannot_list(self):
        self.client.credentials()
        resp = self.client.get('/api/v1/categories/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_but_not_create(self):
        self._auth(self.user)
        self.assertEqual(self.client.get('/api/v1/categories/').status_code, 200)
        resp = self.client.post('/api/v1/categories/', {'name': 'Hogar'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_category_and_slug_autogenerates(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/categories/', {'name': 'Alimentos Frescos'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['slug'], 'alimentos-frescos')

    def test_category_includes_nested_subcategories(self):
        self._auth(self.user)
        resp = self.client.get(f'/api/v1/categories/{self.category.id}/')
        names = [s['name'] for s in resp.data['subcategories']]
        self.assertIn('Camisetas', names)


class SubcategoryTests(CatalogTestBase):
    def test_admin_creates_subcategory(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/subcategories/',
            {'category': self.category.id, 'name': 'Pantalones'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_duplicate_name_in_same_category_rejected(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/subcategories/',
            {'category': self.category.id, 'name': 'Camisetas'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_category(self):
        self._auth(self.user)
        other = Category.objects.create(name='Tecnología')
        Subcategory.objects.create(category=other, name='Celulares')
        resp = self.client.get(f'/api/v1/subcategories/?category={other.id}')
        self.assertEqual(len(resp.data['results']), 1)
        self.assertEqual(resp.data['results'][0]['name'], 'Celulares')


class ProductTests(CatalogTestBase):
    def _payload(self, **overrides):
        # El producto ya no lleva sku/precios/stock (viven en la variante).
        data = {
            'name': 'Camiseta básica',
            'subcategory': self.subcategory.id,
        }
        data.update(overrides)
        return data

    def test_admin_creates_product_and_category_is_derived(self):
        self._auth(self.admin)
        resp = self.client.post('/api/v1/products/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # La categoría se deriva de la subcategoría, no se envía.
        self.assertEqual(resp.data['category'], self.category.id)
        self.assertEqual(resp.data['category_name'], 'Ropa')
        self.assertEqual(resp.data['subcategory_name'], 'Camisetas')

    def test_user_cannot_create_product(self):
        self._auth(self.user)
        resp = self.client.post('/api/v1/products/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_products_by_category(self):
        self._auth(self.user)
        Product.objects.create(name='P1', subcategory=self.subcategory)
        resp = self.client.get(
            f'/api/v1/products/?subcategory__category={self.category.id}'
        )
        self.assertEqual(len(resp.data['results']), 1)

    def test_admin_can_update_product(self):
        self._auth(self.admin)
        created = self.client.post('/api/v1/products/', self._payload(), format='json')
        pid = created.data['id']
        patch = self.client.patch(
            f'/api/v1/products/{pid}/', {'description': 'Nueva desc'}, format='json'
        )
        self.assertEqual(patch.data['description'], 'Nueva desc')

    def test_product_aggregates_stock_and_price_from_variants(self):
        self._auth(self.admin)
        product = Product.objects.create(name='Agregado', subcategory=self.subcategory)
        ProductVariant.objects.create(
            product=product, sku='AGG-1', cost_price=1, sale_price=1000, stock=3
        )
        ProductVariant.objects.create(
            product=product, sku='AGG-2', cost_price=1, sale_price=4000, stock=7
        )
        resp = self.client.get(f'/api/v1/products/{product.id}/')
        self.assertEqual(resp.data['total_stock'], 10)
        self.assertEqual(resp.data['price_min'], '1000.00')
        self.assertEqual(resp.data['price_max'], '4000.00')
        self.assertEqual(len(resp.data['variants']), 2)

    def test_delete_only_deactivates_product(self):
        # En esta BD nada se borra: DELETE marca is_active=False y conserva el registro.
        self._auth(self.admin)
        created = self.client.post('/api/v1/products/', self._payload(), format='json')
        pid = created.data['id']
        resp = self.client.delete(f'/api/v1/products/{pid}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        product = Product.objects.get(pk=pid)  # sigue existiendo
        self.assertFalse(product.is_active)

    def test_can_reactivate_product_via_patch(self):
        self._auth(self.admin)
        created = self.client.post('/api/v1/products/', self._payload(), format='json')
        pid = created.data['id']
        self.client.delete(f'/api/v1/products/{pid}/')
        resp = self.client.patch(
            f'/api/v1/products/{pid}/', {'is_active': True}, format='json'
        )
        self.assertTrue(resp.data['is_active'])

    def test_inactive_products_hidden_with_filter(self):
        self._auth(self.admin)
        created = self.client.post('/api/v1/products/', self._payload(), format='json')
        self.client.delete(f"/api/v1/products/{created.data['id']}/")
        active = self.client.get('/api/v1/products/?is_active=true')
        self.assertEqual(active.data['count'], 0)


class ProductVariantTests(CatalogTestBase):
    def setUp(self):
        super().setUp()
        self.product = Product.objects.create(
            name='Camiseta', subcategory=self.subcategory
        )

    def _payload(self, **overrides):
        data = {
            'product': self.product.id,
            'sku': 'CAM-001',
            'cost_price': '10000.00',
            'sale_price': '25000.00',
            'stock': 50,
        }
        data.update(overrides)
        return data

    def test_admin_creates_variant_and_profit_margin(self):
        self._auth(self.admin)
        resp = self.client.post('/api/v1/variants/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['profit_margin'], '15000.00')

    def test_user_cannot_create_variant(self):
        self._auth(self.user)
        resp = self.client.post('/api/v1/variants/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_sku_rejected(self):
        self._auth(self.admin)
        self.client.post('/api/v1/variants/', self._payload(), format='json')
        resp = self.client.post(
            '/api/v1/variants/', self._payload(sku='CAM-001'), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_price_rejected(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/variants/', self._payload(sku='NEG', sale_price='-5'), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_barcode_rejected(self):
        self._auth(self.admin)
        self.client.post(
            '/api/v1/variants/', self._payload(sku='B1', barcode='7700000000017'),
            format='json',
        )
        resp = self.client.post(
            '/api/v1/variants/', self._payload(sku='B2', barcode='7700000000017'),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blank_barcodes_do_not_collide(self):
        self._auth(self.admin)
        self.client.post('/api/v1/variants/', self._payload(sku='V1'), format='json')
        resp = self.client.post('/api/v1/variants/', self._payload(sku='V2'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_variant_with_attribute_values(self):
        self._auth(self.admin)
        color = ProductAttribute.objects.create(
            product=self.product, name='Color', is_image_axis=True
        )
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo', swatch_hex='#FF0000')
        talla = ProductAttribute.objects.create(product=self.product, name='Talla', position=1)
        m = AttributeValue.objects.create(attribute=talla, value='M')
        resp = self.client.post(
            '/api/v1/variants/',
            self._payload(sku='RED-M', value_ids=[rojo.id, m.id]),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['options_label'], 'Rojo / M')
        self.assertEqual({v['value_label'] for v in resp.data['values']}, {'Rojo', 'M'})

    def test_variant_rejects_value_from_other_product(self):
        self._auth(self.admin)
        other = Product.objects.create(name='Otro', subcategory=self.subcategory)
        attr = ProductAttribute.objects.create(product=other, name='Color')
        val = AttributeValue.objects.create(attribute=attr, value='Azul')
        resp = self.client.post(
            '/api/v1/variants/',
            self._payload(sku='BAD', value_ids=[val.id]),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_combination_rejected(self):
        # No se permite otra variante con la MISMA combinación (aunque cambie el SKU).
        self._auth(self.admin)
        color = ProductAttribute.objects.create(
            product=self.product, name='Color', is_image_axis=True
        )
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        ok = self.client.post(
            '/api/v1/variants/', self._payload(sku='R1', value_ids=[rojo.id]), format='json'
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED, ok.data)
        dup = self.client.post(
            '/api/v1/variants/', self._payload(sku='R2', value_ids=[rojo.id]), format='json'
        )
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)

    def test_variant_requires_value_per_attribute(self):
        # Si el producto tiene 2 atributos, la variante debe traer 2 valores.
        self._auth(self.admin)
        color = ProductAttribute.objects.create(product=self.product, name='Color')
        ProductAttribute.objects.create(product=self.product, name='Talla', position=1)
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        resp = self.client.post(
            '/api/v1/variants/', self._payload(sku='INC', value_ids=[rojo.id]), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edit_variant_combination(self):
        # Se puede cambiar la combinación (value_ids) de una variante existente.
        self._auth(self.admin)
        color = ProductAttribute.objects.create(product=self.product, name='Color')
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        azul = AttributeValue.objects.create(attribute=color, value='Azul')
        created = self.client.post(
            '/api/v1/variants/', self._payload(sku='C1', value_ids=[rojo.id]), format='json'
        )
        vid = created.data['id']
        resp = self.client.patch(
            f'/api/v1/variants/{vid}/', {'value_ids': [azul.id]}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['options_label'], 'Azul')

    def test_reactivate_variant(self):
        # Una variante desactivada (soft-delete) se puede reactivar.
        self._auth(self.admin)
        a = self.client.post('/api/v1/variants/', self._payload(sku='A1'), format='json')
        # Necesita otra activa para poder desactivar la primera.
        self.client.post('/api/v1/variants/', self._payload(sku='A2'), format='json')
        vid = a.data['id']
        self.client.delete(f'/api/v1/variants/{vid}/')
        resp = self.client.patch(
            f'/api/v1/variants/{vid}/', {'is_active': True}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data['is_active'])

    def test_reactivate_conflicting_combination_rejected(self):
        # Reactivar choca si ya hay otra variante activa con la misma combinación.
        self._auth(self.admin)
        color = ProductAttribute.objects.create(product=self.product, name='Color')
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        azul = AttributeValue.objects.create(attribute=color, value='Azul')
        first = self.client.post(
            '/api/v1/variants/', self._payload(sku='R1', value_ids=[rojo.id]), format='json'
        )
        vid = first.data['id']
        # Variante de relleno (otra combinación) para poder desactivar la primera.
        self.client.post(
            '/api/v1/variants/', self._payload(sku='AZ', value_ids=[azul.id]), format='json'
        )
        self.client.delete(f'/api/v1/variants/{vid}/')
        # Otra variante activa toma la misma combinación (Rojo).
        self.client.post(
            '/api/v1/variants/', self._payload(sku='R2', value_ids=[rojo.id]), format='json'
        )
        resp = self.client.patch(
            f'/api/v1/variants/{vid}/', {'is_active': True}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)

    def test_remove_attribute_detaches_variants(self):
        # Quitar un eje desliga las variantes (sin chocar si quedan distintas).
        self._auth(self.admin)
        color = ProductAttribute.objects.create(
            product=self.product, name='Color', is_image_axis=True
        )
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        azul = AttributeValue.objects.create(attribute=color, value='Azul')
        talla = ProductAttribute.objects.create(product=self.product, name='Talla', position=1)
        m = AttributeValue.objects.create(attribute=talla, value='M')
        v1 = ProductVariant.objects.create(product=self.product, sku='R-M')
        VariantValue.objects.create(variant=v1, value=rojo)
        VariantValue.objects.create(variant=v1, value=m)
        v2 = ProductVariant.objects.create(product=self.product, sku='A-M')
        VariantValue.objects.create(variant=v2, value=azul)
        VariantValue.objects.create(variant=v2, value=m)

        resp = self.client.delete(f'/api/v1/product-attributes/{talla.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, getattr(resp, 'data', None))
        self.assertFalse(ProductAttribute.objects.filter(id=talla.id).exists())
        self.assertEqual(v1.options_label, 'Rojo')
        self.assertEqual(v2.options_label, 'Azul')

    def test_remove_attribute_blocked_when_duplicate(self):
        # Si al quitar el eje dos variantes activas colapsan en la misma combinación → 400.
        self._auth(self.admin)
        color = ProductAttribute.objects.create(product=self.product, name='Color')
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo')
        talla = ProductAttribute.objects.create(product=self.product, name='Talla', position=1)
        m = AttributeValue.objects.create(attribute=talla, value='M')
        l = AttributeValue.objects.create(attribute=talla, value='L')
        v1 = ProductVariant.objects.create(product=self.product, sku='R-M')
        VariantValue.objects.create(variant=v1, value=rojo)
        VariantValue.objects.create(variant=v1, value=m)
        v2 = ProductVariant.objects.create(product=self.product, sku='R-L')
        VariantValue.objects.create(variant=v2, value=rojo)
        VariantValue.objects.create(variant=v2, value=l)

        resp = self.client.delete(f'/api/v1/product-attributes/{talla.id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ProductAttribute.objects.filter(id=talla.id).exists())

    def test_low_stock_flag(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/variants/',
            self._payload(sku='LOW', stock=2, min_stock=5),
            format='json',
        )
        self.assertTrue(resp.data['is_low_stock'])

    def test_filter_variants_by_product(self):
        self._auth(self.admin)
        ProductVariant.objects.create(product=self.product, sku='F1', sale_price=1)
        other = Product.objects.create(name='Otro', subcategory=self.subcategory)
        ProductVariant.objects.create(product=other, sku='F2', sale_price=1)
        resp = self.client.get(f'/api/v1/variants/?product={self.product.id}')
        self.assertEqual(resp.data['count'], 1)

    def test_cannot_deactivate_last_active_variant(self):
        self._auth(self.admin)
        v = ProductVariant.objects.create(product=self.product, sku='ONLY', sale_price=1)
        resp = self.client.delete(f'/api/v1/variants/{v.id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['code'], 'min_variants')

    def test_can_deactivate_when_another_active_remains(self):
        self._auth(self.admin)
        v1 = ProductVariant.objects.create(product=self.product, sku='K1', sale_price=1)
        ProductVariant.objects.create(product=self.product, sku='K2', sale_price=1)
        resp = self.client.delete(f'/api/v1/variants/{v1.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductVariant.objects.get(pk=v1.id).is_active)


class ColorSizeTests(CatalogTestBase):
    def test_sizes_and_colors_were_seeded(self):
        # La migración de datos siembra tallas y colores base.
        self.assertTrue(Size.objects.filter(name='M').exists())
        self.assertTrue(Color.objects.filter(name='Negro').exists())

    def test_admin_creates_color_and_hex_is_uppercased(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/colors/', {'name': 'Turquesa', 'hex_code': '#40e0d0'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['hex_code'], '#40E0D0')

    def test_invalid_hex_rejected(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/colors/', {'name': 'Malo', 'hex_code': 'azul'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_create_size(self):
        self._auth(self.user)
        resp = self.client.post('/api/v1/sizes/', {'name': '4XL'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class BrandTests(CatalogTestBase):
    def test_admin_creates_brand(self):
        self._auth(self.admin)
        resp = self.client.post('/api/v1/brands/', {'name': 'Nike'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['name'], 'Nike')

    def test_user_cannot_create_brand(self):
        self._auth(self.user)
        resp = self.client.post('/api/v1/brands/', {'name': 'Adidas'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_brand_rejected(self):
        self._auth(self.admin)
        self.client.post('/api/v1/brands/', {'name': 'Puma'}, format='json')
        resp = self.client.post('/api/v1/brands/', {'name': 'Puma'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_only_deactivates_brand(self):
        self._auth(self.admin)
        created = self.client.post('/api/v1/brands/', {'name': 'Bimbo'}, format='json')
        resp = self.client.delete(f"/api/v1/brands/{created.data['id']}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Brand.objects.get(pk=created.data['id']).is_active)

    def test_product_defaults_to_unit_and_iva_19(self):
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/products/',
            {'name': 'Genérico', 'subcategory': self.subcategory.id},
            format='json',
        )
        self.assertEqual(resp.data['unit_of_measure'], 'unidad')
        self.assertEqual(resp.data['tax_rate'], 19)
        self.assertEqual(resp.data['unit_of_measure_display'], 'Unidad')

    def test_product_with_brand_uom_and_tax(self):
        self._auth(self.admin)
        brand = Brand.objects.create(name='Coca-Cola')
        resp = self.client.post(
            '/api/v1/products/',
            {
                'name': 'Gaseosa 1.5L',
                'subcategory': self.subcategory.id,
                'brand': brand.id,
                'unit_of_measure': 'l',
                'tax_rate': 5,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['brand'], brand.id)
        self.assertEqual(resp.data['brand_detail']['name'], 'Coca-Cola')
        self.assertEqual(resp.data['unit_of_measure_display'], 'Litro')
        self.assertEqual(resp.data['tax_rate_display'], 'IVA 5%')

    def test_filter_products_by_brand(self):
        self._auth(self.admin)
        brand = Brand.objects.create(name='Marca X')
        Product.objects.create(name='Con marca', subcategory=self.subcategory, brand=brand)
        Product.objects.create(name='Sin marca', subcategory=self.subcategory)
        resp = self.client.get(f'/api/v1/products/?brand={brand.id}')
        self.assertEqual(resp.data['count'], 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductImageTests(CatalogTestBase):
    """Galería del producto por valor del eje visual (reemplaza VariantImage)."""

    def setUp(self):
        super().setUp()
        self._auth(self.admin)
        self.product = Product.objects.create(name='Camiseta', subcategory=self.subcategory)
        self.color = ProductAttribute.objects.create(
            product=self.product, name='Color', is_image_axis=True
        )
        self.rojo = AttributeValue.objects.create(
            attribute=self.color, value='Rojo', swatch_hex='#FF0000'
        )

    def _upload(self, name='a.png', value=None):
        data = {'product': self.product.id, 'image': make_image(name)}
        if value is not None:
            data['value'] = value
        return self.client.post('/api/v1/product-images/', data, format='multipart')

    def _images(self, value=None):
        params = {'product': self.product.id}
        if value is not None:
            params['value'] = value
        return self.client.get('/api/v1/product-images/', params).data

    def test_product_cover_is_first_image(self):
        self._upload('cover.png')
        detail = self.client.get(f'/api/v1/products/{self.product.id}/')
        self.assertIsNotNone(detail.data['main_image'])

    def test_uploaded_file_gets_unique_name_not_original(self):
        url = self._upload('mi archivo personal.png').data['image']
        self.assertNotIn('mi archivo personal', url)
        self.assertNotIn('mi%20archivo', url)
        self.assertIn('/products/', url)
        self.assertTrue(url.endswith('.png'))

    def test_same_filename_twice_does_not_collide(self):
        a = self._upload('foto.png').data['image']
        b = self._upload('foto.png').data['image']
        self.assertNotEqual(a, b)

    def test_uploaded_images_get_increasing_position(self):
        a = self._upload('a.png', value=self.rojo.id).data
        b = self._upload('b.png', value=self.rojo.id).data
        self.assertEqual(a['position'], 0)
        self.assertEqual(b['position'], 1)

    def test_delete_image(self):
        a = self._upload('only.png').data
        resp = self.client.delete(f'/api/v1/product-images/{a["id"]}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self._images(), [])

    def test_reorder_changes_gallery_order(self):
        a = self._upload('a.png', value=self.rojo.id).data
        b = self._upload('b.png', value=self.rojo.id).data
        c = self._upload('c.png', value=self.rojo.id).data
        resp = self.client.post(
            '/api/v1/product-images/reorder/',
            {'order': [c['id'], a['id'], b['id']]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [i['id'] for i in self._images(value=self.rojo.id)]
        self.assertEqual(ids, [c['id'], a['id'], b['id']])

    def test_cannot_exceed_max_per_group(self):
        for n in range(ProductImage.MAX_PER_GROUP):
            self.assertEqual(
                self._upload(f'{n}.png', value=self.rojo.id).status_code,
                status.HTTP_201_CREATED,
            )
        resp = self._upload('extra.png', value=self.rojo.id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_variant_inherits_color_gallery(self):
        # La variante 'Rojo' hereda las fotos del valor Rojo (sin subirlas).
        self._upload('rojo.png', value=self.rojo.id)
        variant = ProductVariant.objects.create(
            product=self.product, sku='CAM-ROJO', sale_price=2500
        )
        from catalog.models import VariantValue
        VariantValue.objects.create(variant=variant, value=self.rojo)
        detail = self.client.get(f'/api/v1/variants/{variant.id}/')
        self.assertIsNotNone(detail.data['main_image'])

    def test_user_cannot_upload_image(self):
        self._auth(self.user)
        resp = self._upload('x.png')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
