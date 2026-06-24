from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import (
    AttributeDefinition,
    AttributeOption,
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductVariant,
    Subcategory,
    VariantValue,
)
from geo.models import Country
from inventory.models import MovementType, StockLevel, Warehouse
from inventory.services import record_movement
from sales.models import Sale, SaleItem, SaleStatus
from store.models import Order

User = get_user_model()


class StoreCatalogTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(name='Ropa')
        self.sub = Subcategory.objects.create(category=self.category, name='Camisetas')
        self.product = Product.objects.create(name='Camiseta', subcategory=self.sub)
        self.variant = ProductVariant.objects.create(
            product=self.product, sku='C-1', sale_price=Decimal('50000'),
            cost_price=Decimal('20000'), stock=5,
        )

    def test_public_can_list_products(self):
        resp = self.client.get('/api/v1/store/products/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 1)

    def test_product_does_not_leak_cost(self):
        resp = self.client.get('/api/v1/store/products/')
        row = resp.data['results'][0]
        # La tienda nunca expone costos ni stock exacto.
        self.assertNotIn('cost_price', row)
        self.assertIn('price_min', row)
        self.assertIn('available', row)

    def test_public_can_view_detail_with_variants(self):
        resp = self.client.get(f'/api/v1/store/products/{self.product.slug}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['variants']), 1)
        self.assertNotIn('cost_price', resp.data['variants'][0])
        # El stock se expone para poder topar la cantidad en la tienda.
        self.assertEqual(resp.data['variants'][0]['stock'], 5)

    def test_public_categories(self):
        resp = self.client.get('/api/v1/store/categories/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [c['name'] for c in resp.data]
        self.assertIn('Ropa', names)

    def test_variant_stock_endpoint(self):
        resp = self.client.get(f'/api/v1/store/variants/stock/?ids={self.variant.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data[str(self.variant.id)], 5)

    def test_product_colors_breakdown(self):
        # Un producto con eje de color expone una entrada por color.
        prod = Product.objects.create(name='Camiseta', subcategory=self.sub)
        color = ProductAttribute.objects.create(
            product=prod, name='Color', is_image_axis=True
        )
        rojo = AttributeValue.objects.create(attribute=color, value='Rojo', swatch_hex='#FF0000')
        azul = AttributeValue.objects.create(attribute=color, value='Azul', swatch_hex='#0000FF')
        vr = ProductVariant.objects.create(product=prod, sku='R', sale_price=Decimal('50000'), stock=2)
        VariantValue.objects.create(variant=vr, value=rojo)
        va = ProductVariant.objects.create(product=prod, sku='A', sale_price=Decimal('60000'), stock=0)
        VariantValue.objects.create(variant=va, value=azul)

        resp = self.client.get(f'/api/v1/store/products/{prod.slug}/')
        colors = {c['label']: c for c in resp.data['colors']}
        self.assertEqual(set(colors), {'Rojo', 'Azul'})
        self.assertTrue(colors['Rojo']['available'])
        self.assertFalse(colors['Azul']['available'])
        self.assertEqual(colors['Rojo']['price_min'], 50000.0)
        # Cada color expone los valores (talla, etc.) de sus variantes.
        self.assertIn('rojo', colors['Rojo']['values'])

    def test_product_without_axis_has_no_colors(self):
        resp = self.client.get(f'/api/v1/store/products/{self.product.slug}/')
        self.assertEqual(resp.data['colors'], [])

    def test_brands_scoped_by_category(self):
        # La camiseta (Ropa) es Zara; un producto de Tecnología es Apple.
        zara = Brand.objects.create(name='Zara')
        apple = Brand.objects.create(name='Apple')
        self.product.brand = zara
        self.product.save()
        tech = Category.objects.create(name='Tecnología')
        tsub = Subcategory.objects.create(category=tech, name='Celulares')
        phone = Product.objects.create(name='Tel', subcategory=tsub, brand=apple)
        ProductVariant.objects.create(product=phone, sku='T-1', sale_price=Decimal('3000000'), stock=2)

        ropa = self.category.id
        names = [b['name'] for b in self.client.get(f'/api/v1/store/brands/?category={ropa}').data]
        self.assertIn('Zara', names)
        self.assertNotIn('Apple', names)  # Apple es de Tecnología, no de Ropa
        names_tech = [b['name'] for b in self.client.get(f'/api/v1/store/brands/?category={tech.id}').data]
        self.assertEqual(names_tech, ['Apple'])

    def test_price_range_scoped_by_category(self):
        tech = Category.objects.create(name='Tecnología')
        tsub = Subcategory.objects.create(category=tech, name='Celulares')
        phone = Product.objects.create(name='Tel', subcategory=tsub)
        ProductVariant.objects.create(product=phone, sku='T-1', sale_price=Decimal('3000000'), stock=2)
        # Ropa: solo la camiseta de 50.000.
        rng = self.client.get(f'/api/v1/store/price-range/?category={self.category.id}').data
        self.assertEqual(rng['max'], 50000)


class StoreSortTests(APITestCase):
    """Ordenamiento del catálogo por precio y por unidades vendidas."""

    def setUp(self):
        cache.clear()
        cat = Category.objects.create(name='Ropa')
        sub = Subcategory.objects.create(category=cat, name='Camisetas')
        self.warehouse = Warehouse.objects.create(name='Centro')

        # A: barato y muy vendido. B: caro y poco vendido.
        self.prod_a = Product.objects.create(name='Producto A', subcategory=sub)
        self.var_a = ProductVariant.objects.create(
            product=self.prod_a, sku='A-1', sale_price=Decimal('10000'), stock=100
        )
        self.prod_b = Product.objects.create(name='Producto B', subcategory=sub)
        self.var_b = ProductVariant.objects.create(
            product=self.prod_b, sku='B-1', sale_price=Decimal('90000'), stock=100
        )

        # Venta completada: A vende 5, B vende 1.
        sale = Sale.objects.create(
            number=1, warehouse=self.warehouse, status=SaleStatus.COMPLETED, total=Decimal('0')
        )
        SaleItem.objects.create(
            sale=sale, variant=self.var_a, description='A', quantity=5,
            unit_price=Decimal('10000'), line_total=Decimal('50000'),
        )
        SaleItem.objects.create(
            sale=sale, variant=self.var_b, description='B', quantity=1,
            unit_price=Decimal('90000'), line_total=Decimal('90000'),
        )

    def _names(self, ordering):
        resp = self.client.get('/api/v1/store/products/', {'ordering': ordering})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return [p['name'] for p in resp.data['results']]

    def test_order_by_price_asc(self):
        self.assertEqual(self._names('price'), ['Producto A', 'Producto B'])

    def test_order_by_price_desc(self):
        self.assertEqual(self._names('-price'), ['Producto B', 'Producto A'])

    def test_order_by_most_sold(self):
        self.assertEqual(self._names('-sold'), ['Producto A', 'Producto B'])

    def test_order_by_least_sold(self):
        self.assertEqual(self._names('sold'), ['Producto B', 'Producto A'])


class StoreFilterTests(APITestCase):
    """Filtros del catálogo: marca, rango de precio y disponibilidad."""

    def setUp(self):
        cache.clear()
        cat = Category.objects.create(name='Tecnología')
        sub = Subcategory.objects.create(category=cat, name='Audio')
        self.nike = Brand.objects.create(name='Nike')
        self.sony = Brand.objects.create(name='Sony')

        self.cheap = Product.objects.create(name='Audífonos básicos', subcategory=sub, brand=self.nike)
        ProductVariant.objects.create(
            product=self.cheap, sku='CH-1', sale_price=Decimal('20000'), stock=10
        )
        self.pricey = Product.objects.create(name='Audífonos pro', subcategory=sub, brand=self.sony)
        ProductVariant.objects.create(
            product=self.pricey, sku='PR-1', sale_price=Decimal('200000'), stock=5
        )
        # Producto agotado (sin existencia).
        self.out = Product.objects.create(name='Parlante agotado', subcategory=sub, brand=self.sony)
        ProductVariant.objects.create(
            product=self.out, sku='OUT-1', sale_price=Decimal('80000'), stock=0
        )

    def _names(self, params):
        resp = self.client.get('/api/v1/store/products/', params)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return {p['name'] for p in resp.data['results']}

    def test_brands_endpoint_lists_used_brands(self):
        resp = self.client.get('/api/v1/store/brands/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual({b['name'] for b in resp.data}, {'Nike', 'Sony'})

    def test_filter_by_brand(self):
        self.assertEqual(self._names({'brand': self.nike.id}), {'Audífonos básicos'})

    def test_filter_price_min(self):
        self.assertEqual(self._names({'price_min': 100000}), {'Audífonos pro'})

    def test_filter_price_max(self):
        self.assertEqual(self._names({'price_max': 50000}), {'Audífonos básicos'})

    def test_filter_price_range(self):
        self.assertEqual(
            self._names({'price_min': 50000, 'price_max': 150000}), {'Parlante agotado'}
        )

    def test_filter_only_available(self):
        names = self._names({'available': '1'})
        self.assertIn('Audífonos básicos', names)
        self.assertIn('Audífonos pro', names)
        self.assertNotIn('Parlante agotado', names)


class AccountTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.buyer = User.objects.create_user(
            email='comprador@test.com', password='Stockly2026',
            first_name='Ana', role=User.Role.BUYER, is_email_verified=True,
        )
        self.other = User.objects.create_user(
            email='otro@test.com', password='Stockly2026',
            first_name='Beto', role=User.Role.BUYER, is_email_verified=True,
        )
        # Ubicación sembrada por la migración de geo (disponible en la BD de test).
        self.country = Country.objects.get(code='CO')
        self.department = self.country.departments.first()
        self.city = self.department.cities.first()

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def _address(self, **over):
        data = {
            'recipient': 'Ana', 'line1': 'Calle 1', 'phone': '3001234567',
            'country': self.country.id, 'department': self.department.id, 'city': self.city.id,
        }
        data.update(over)
        return data

    def test_addresses_are_owner_scoped(self):
        self._auth(self.buyer)
        resp = self.client.post('/api/v1/account/addresses/', self._address(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(self.client.get('/api/v1/account/addresses/').data['count'], 1)
        # Otro usuario no ve las direcciones del primero.
        self._auth(self.other)
        self.assertEqual(self.client.get('/api/v1/account/addresses/').data['count'], 0)

    def test_address_requires_location(self):
        self._auth(self.buyer)
        resp = self.client.post(
            '/api/v1/account/addresses/', {'recipient': 'Ana', 'line1': 'Calle 1'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_setting_default_unsets_previous(self):
        self._auth(self.buyer)
        a = self.client.post('/api/v1/account/addresses/', self._address(is_default=True), format='json').data
        b = self.client.post('/api/v1/account/addresses/', self._address(is_default=True), format='json').data
        ax = self.client.get(f'/api/v1/account/addresses/{a["id"]}/').data
        bx = self.client.get(f'/api/v1/account/addresses/{b["id"]}/').data
        self.assertFalse(ax['is_default'])
        self.assertTrue(bx['is_default'])

    def test_anonymous_cannot_access_account(self):
        resp = self.client.get('/api/v1/account/addresses/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class StoreAttributeFilterTests(APITestCase):
    """Filtros del catálogo por atributos de variación."""

    def setUp(self):
        cache.clear()
        cat = Category.objects.create(name='Tecnología')
        sub = Subcategory.objects.create(category=cat, name='Celulares')
        self.p1 = Product.objects.create(name='Tel A', subcategory=sub)
        self.p2 = Product.objects.create(name='Tel B', subcategory=sub)
        ProductVariant.objects.create(product=self.p1, sku='A1', sale_price=Decimal('100'), stock=3)
        ProductVariant.objects.create(product=self.p2, sku='B1', sale_price=Decimal('100'), stock=3)
        self.defn = AttributeDefinition.objects.create(name='Almacenamiento', has_swatch=False)
        self.o128 = AttributeOption.objects.create(definition=self.defn, value='128GB')
        self.o256 = AttributeOption.objects.create(definition=self.defn, value='256GB')
        a1 = ProductAttribute.objects.create(product=self.p1, definition=self.defn, name='Almacenamiento')
        AttributeValue.objects.create(attribute=a1, value='128GB')
        a2 = ProductAttribute.objects.create(product=self.p2, definition=self.defn, name='Almacenamiento')
        AttributeValue.objects.create(attribute=a2, value='256GB')

    def test_facets_list_used_options(self):
        resp = self.client.get('/api/v1/store/attribute-filters/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        group = next((g for g in resp.data if g['name'] == 'Almacenamiento'), None)
        self.assertIsNotNone(group)
        self.assertEqual({o['value'] for o in group['options']}, {'128GB', '256GB'})

    def test_filter_products_by_option(self):
        resp = self.client.get(f'/api/v1/store/products/?options={self.o128.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [r['name'] for r in resp.data['results']]
        self.assertIn('Tel A', names)
        self.assertNotIn('Tel B', names)

    def test_filter_multiple_options_same_attribute_is_or(self):
        resp = self.client.get(
            f'/api/v1/store/products/?options={self.o128.id},{self.o256.id}'
        )
        names = [r['name'] for r in resp.data['results']]
        self.assertIn('Tel A', names)
        self.assertIn('Tel B', names)


class WishlistTests(APITestCase):
    """Favoritos persistidos por cuenta."""

    def setUp(self):
        cache.clear()
        self.buyer = User.objects.create_user(
            email='w@test.com', password='Stockly2026',
            first_name='Ana', role=User.Role.BUYER, is_email_verified=True,
        )
        self.other = User.objects.create_user(
            email='w2@test.com', password='Stockly2026',
            first_name='Beto', role=User.Role.BUYER, is_email_verified=True,
        )
        cat = Category.objects.create(name='Ropa')
        sub = Subcategory.objects.create(category=cat, name='Camisetas')
        self.p1 = Product.objects.create(name='Camiseta', subcategory=sub)
        self.p2 = Product.objects.create(name='Pantalón', subcategory=sub)
        ProductVariant.objects.create(product=self.p1, sku='C1', sale_price=Decimal('50000'), stock=3)
        ProductVariant.objects.create(product=self.p2, sku='C2', sale_price=Decimal('80000'), stock=3)

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_anonymous_cannot_access(self):
        self.assertEqual(self.client.get('/api/v1/account/favorites/').status_code, 401)

    def test_add_list_and_dedupe(self):
        self._auth(self.buyer)
        r = self.client.post('/api/v1/account/favorites/', {'product': self.p1.id}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(r.data['name'], 'Camiseta')
        # Agregar el mismo no duplica.
        self.client.post('/api/v1/account/favorites/', {'product': self.p1.id}, format='json')
        self.assertEqual(len(self.client.get('/api/v1/account/favorites/').data), 1)

    def test_remove_and_clear(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/favorites/', {'product': self.p1.id}, format='json')
        self.client.post('/api/v1/account/favorites/', {'product': self.p2.id}, format='json')
        self.client.post('/api/v1/account/favorites/remove/', {'product': self.p1.id}, format='json')
        self.assertEqual(len(self.client.get('/api/v1/account/favorites/').data), 1)
        self.client.delete('/api/v1/account/favorites/clear/')
        self.assertEqual(len(self.client.get('/api/v1/account/favorites/').data), 0)

    def test_owner_scoped(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/favorites/', {'product': self.p1.id}, format='json')
        self._auth(self.other)
        self.assertEqual(len(self.client.get('/api/v1/account/favorites/').data), 0)

    def test_merge(self):
        self._auth(self.buyer)
        resp = self.client.post(
            '/api/v1/account/favorites/merge/',
            {'items': [{'product': self.p1.id}, {'product': self.p2.id}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(len(resp.data), 2)


class CartTests(APITestCase):
    """Carrito persistido por cuenta."""

    def setUp(self):
        cache.clear()
        self.buyer = User.objects.create_user(
            email='c@test.com', password='Stockly2026',
            first_name='Ana', role=User.Role.BUYER, is_email_verified=True,
        )
        self.other = User.objects.create_user(
            email='o@test.com', password='Stockly2026',
            first_name='Beto', role=User.Role.BUYER, is_email_verified=True,
        )
        cat = Category.objects.create(name='Ropa')
        sub = Subcategory.objects.create(category=cat, name='Camisetas')
        prod = Product.objects.create(name='Camiseta', subcategory=sub)
        self.v1 = ProductVariant.objects.create(
            product=prod, sku='V-1', sale_price=Decimal('50000'), stock=5
        )
        self.v2 = ProductVariant.objects.create(
            product=prod, sku='V-2', sale_price=Decimal('60000'), stock=3
        )

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_anonymous_cannot_access_cart(self):
        self.assertEqual(self.client.get('/api/v1/account/cart/').status_code, 401)

    def test_set_and_list(self):
        self._auth(self.buyer)
        resp = self.client.post(
            '/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 2}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['quantity'], 2)
        items = self.client.get('/api/v1/account/cart/').data
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Camiseta')

    def test_quantity_capped_at_stock(self):
        self._auth(self.buyer)
        resp = self.client.post(
            '/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 99}, format='json'
        )
        self.assertEqual(resp.data['quantity'], 5)  # stock = 5

    def test_set_is_absolute_upsert(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 2}, format='json')
        self.client.post('/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 4}, format='json')
        items = self.client.get('/api/v1/account/cart/').data
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['quantity'], 4)

    def test_cart_is_owner_scoped(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 1}, format='json')
        self._auth(self.other)
        self.assertEqual(len(self.client.get('/api/v1/account/cart/').data), 0)

    def test_remove_and_clear(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 1}, format='json')
        self.client.post('/api/v1/account/cart/', {'variant': self.v2.id, 'quantity': 1}, format='json')
        self.client.delete(f'/api/v1/account/cart/{self.v1.id}/')
        self.assertEqual(len(self.client.get('/api/v1/account/cart/').data), 1)
        self.client.delete('/api/v1/account/cart/clear/')
        self.assertEqual(len(self.client.get('/api/v1/account/cart/').data), 0)

    def test_merge_adds_quantities(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/cart/', {'variant': self.v1.id, 'quantity': 2}, format='json')
        resp = self.client.post(
            '/api/v1/account/cart/merge/',
            {'items': [{'variant': self.v1.id, 'quantity': 2}, {'variant': self.v2.id, 'quantity': 1}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        by_variant = {i['variant']: i['quantity'] for i in resp.data}
        self.assertEqual(by_variant[self.v1.id], 4)  # 2 + 2
        self.assertEqual(by_variant[self.v2.id], 1)


class OrderTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.buyer = User.objects.create_user(
            email='comprador@test.com', password='Stockly2026',
            first_name='Ana', role=User.Role.BUYER, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Stockly2026',
            first_name='Jefe', role=User.Role.ADMIN, is_email_verified=True,
        )
        self.warehouse = Warehouse.objects.create(name='Tienda Centro')
        self.category = Category.objects.create(name='Ropa')
        self.sub = Subcategory.objects.create(category=self.category, name='Camisetas')
        self.product = Product.objects.create(name='Camiseta', subcategory=self.sub, tax_rate=19)
        self.variant = ProductVariant.objects.create(
            product=self.product, sku='C-1', sale_price=Decimal('50000'),
            cost_price=Decimal('20000'),
        )
        # Carga 10 unidades en el punto vía un movimiento real (entrada de compra).
        record_movement(
            variant=self.variant, warehouse=self.warehouse,
            type=MovementType.ENTRY, quantity=10, unit_cost=Decimal('20000'),
        )

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def _order_payload(self, qty=2):
        return {
            'warehouse': self.warehouse.id,
            'fulfillment': 'recoge',
            'payment_method': 'efectivo',
            'items': [{'variant': self.variant.id, 'quantity': qty}],
        }

    def test_buyer_creates_order_and_stock_drops(self):
        self._auth(self.buyer)
        resp = self.client.post('/api/v1/account/orders/', self._order_payload(2), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['status'], 'pendiente')
        self.assertEqual(resp.data['total'], '100000.00')
        level = StockLevel.objects.get(variant=self.variant, warehouse=self.warehouse)
        self.assertEqual(level.quantity, 8)

    def test_delivery_requires_address(self):
        self._auth(self.buyer)
        payload = self._order_payload()
        payload['fulfillment'] = 'envio'
        resp = self.client.post('/api/v1/account/orders/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # El contrato de error uniforme envuelve los errores de campo en `errors`.
        self.assertIn('address', resp.data['errors'])

    def test_cannot_order_more_than_stock(self):
        self._auth(self.buyer)
        resp = self.client.post('/api/v1/account/orders/', self._order_payload(99), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # La existencia no se tocó (transacción revertida).
        level = StockLevel.objects.get(variant=self.variant, warehouse=self.warehouse)
        self.assertEqual(level.quantity, 10)

    def test_availability_check(self):
        self._auth(self.buyer)
        resp = self.client.post(
            '/api/v1/account/orders/availability/',
            {'warehouse': self.warehouse.id, 'items': [{'variant': self.variant.id, 'quantity': 99}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['results'][0]['available'])

    def test_buyer_only_sees_own_orders(self):
        self._auth(self.buyer)
        self.client.post('/api/v1/account/orders/', self._order_payload(1), format='json')
        self.assertEqual(self.client.get('/api/v1/account/orders/').data['count'], 1)
        # Un comprador no entra al back-office de pedidos.
        resp = self.client.get('/api/v1/orders/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_returns_stock(self):
        self._auth(self.buyer)
        order = self.client.post('/api/v1/account/orders/', self._order_payload(3), format='json').data
        resp = self.client.post(f'/api/v1/account/orders/{order["id"]}/cancel/', format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'cancelado')
        level = StockLevel.objects.get(variant=self.variant, warehouse=self.warehouse)
        self.assertEqual(level.quantity, 10)

    def test_staff_advances_order_status(self):
        self._auth(self.buyer)
        order = self.client.post('/api/v1/account/orders/', self._order_payload(1), format='json').data
        self._auth(self.admin)
        for expected in ['confirmado', 'enviado', 'entregado']:
            resp = self.client.post(f'/api/v1/orders/{order["id"]}/advance/', format='json')
            self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
            self.assertEqual(resp.data['status'], expected)
        # Al entregar, el efectivo contra entrega queda pagado.
        self.assertTrue(resp.data['is_paid'])
        # No avanza más allá de entregado.
        resp = self.client.post(f'/api/v1/orders/{order["id"]}/advance/', format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_buyer_cannot_cancel_after_confirmed(self):
        self._auth(self.buyer)
        order = self.client.post('/api/v1/account/orders/', self._order_payload(1), format='json').data
        self._auth(self.admin)
        self.client.post(f'/api/v1/orders/{order["id"]}/advance/', format='json')
        self._auth(self.buyer)
        resp = self.client.post(f'/api/v1/account/orders/{order["id"]}/cancel/', format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
