from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product, ProductVariant, Subcategory
from inventory.models import StockMovement, Warehouse
from inventory.services import record_movement

User = get_user_model()


class SalesTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = self._user('admin@test.com', User.Role.ADMIN)
        self.cashier = self._user('cajero@test.com', User.Role.CASHIER)
        self.category = Category.objects.create(name='Tecnología')
        self.subcategory = Subcategory.objects.create(category=self.category, name='Celulares')
        self.product = Product.objects.create(
            name='iPhone', subcategory=self.subcategory, tax_rate=19
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku='IPH-1', sale_price=Decimal('11900')
        )
        self.warehouse = Warehouse.objects.create(name='Principal')
        # Cliente obligatorio en toda venta: un comprador para los payloads base.
        self.buyer = User(
            email='cliente@test.com', first_name='Cliente', role=User.Role.BUYER,
            is_email_verified=True, id_number='100',
        )
        self.buyer.set_password('Stockly2026')
        self.buyer.save()
        # El cajero opera sobre su bodega asignada (regla del POS por bodega).
        self.cashier.warehouse = self.warehouse
        self.cashier.save(update_fields=['warehouse'])
        # Stock inicial: 10 unidades a $5.000.
        record_movement(
            variant=self.variant, warehouse=self.warehouse,
            type='entrada', quantity=10, unit_cost=Decimal('5000'),
        )

    def _user(self, email, role):
        u = User(email=email, first_name='Test', role=role, is_email_verified=True)
        u.set_password('Stockly2026')
        u.save()
        return u

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def _sale_payload(self, **over):
        data = {
            'warehouse': self.warehouse.id,
            'customer': self.buyer.id,
            'items': [{'variant': self.variant.id, 'quantity': 2}],
            'payments': [{'method': 'efectivo', 'amount': '25000'}],
        }
        data.update(over)
        return data


class SaleTests(SalesTestBase):
    def test_cashier_can_register_sale(self):
        self._auth(self.cashier)
        resp = self.client.post('/api/v1/sales/', self._sale_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # 2 × 11900 = 23800 ; subtotal sin IVA = 20000 ; IVA = 3800.
        self.assertEqual(Decimal(resp.data['total']), Decimal('23800.00'))
        self.assertEqual(Decimal(resp.data['subtotal']), Decimal('20000.00'))
        self.assertEqual(Decimal(resp.data['tax_total']), Decimal('3800.00'))
        self.assertEqual(Decimal(resp.data['change']), Decimal('1200.00'))

    def test_buyer_resends_own_receipt(self):
        from django.core import mail
        self._auth(self.cashier)
        sale = self.client.post('/api/v1/sales/', self._sale_payload(), format='json').data
        self._auth(self.buyer)
        mail.outbox = []
        resp = self.client.post(
            f'/api/v1/account/purchases/sale/{sale["id"]}/send-receipt/', format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(mail.outbox, 'No se reenvió el recibo')
        self.assertIn('cliente@test.com', mail.outbox[0].to)

    def test_buyer_cannot_resend_others_receipt(self):
        self._auth(self.cashier)
        sale = self.client.post('/api/v1/sales/', self._sale_payload(), format='json').data
        other = self._user('otro@test.com', User.Role.BUYER)
        self._auth(other)
        resp = self.client.post(
            f'/api/v1/account/purchases/sale/{sale["id"]}/send-receipt/', format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_sale_reduces_stock_via_kardex(self):
        self._auth(self.cashier)
        self.client.post('/api/v1/sales/', self._sale_payload(), format='json')
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 8)
        self.assertTrue(
            StockMovement.objects.filter(type='salida', reason='venta', quantity=2).exists()
        )

    def test_discount_reduces_total(self):
        self._auth(self.cashier)
        payload = self._sale_payload(discount='3800')
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(resp.data['total']), Decimal('20000.00'))

    def test_discount_recomputes_taxable_base_and_iva(self):
        # El descuento reduce la base gravable y el IVA se recalcula sobre el
        # neto: subtotal + IVA debe seguir siendo igual al total.
        self._auth(self.cashier)
        # 2 × 11900 = 23800 (IVA 19% incluido); descuento de 3800 → total 20000.
        resp = self.client.post('/api/v1/sales/', self._sale_payload(discount='3800'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        subtotal = Decimal(resp.data['subtotal'])
        tax = Decimal(resp.data['tax_total'])
        total = Decimal(resp.data['total'])
        self.assertEqual(total, Decimal('20000.00'))
        # El desglose cuadra: base + IVA = total (antes el IVA quedaba inflado).
        self.assertEqual(subtotal + tax, total)
        # IVA = total − total/1.19 ≈ 3193.28 (sobre el neto, no sobre el bruto).
        expected_tax = (total - (total / Decimal('1.19'))).quantize(Decimal('0.01'))
        self.assertEqual(tax, expected_tax)

    def test_cannot_sell_more_than_stock(self):
        self._auth(self.cashier)
        payload = self._sale_payload(
            items=[{'variant': self.variant.id, 'quantity': 99}],
            payments=[{'method': 'efectivo', 'amount': '9999999'}],
        )
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)  # no cambió

    def test_payment_must_cover_total(self):
        self._auth(self.cashier)
        payload = self._sale_payload(payments=[{'method': 'efectivo', 'amount': '1000'}])
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_split_payment(self):
        self._auth(self.cashier)
        payload = self._sale_payload(
            payments=[
                {'method': 'efectivo', 'amount': '10000'},
                {'method': 'tarjeta', 'amount': '13800'},
            ]
        )
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data['payments']), 2)

    def test_void_returns_stock_and_is_admin_only(self):
        self._auth(self.cashier)
        sale = self.client.post('/api/v1/sales/', self._sale_payload(), format='json').data
        # El cajero no puede anular.
        denied = self.client.post(f'/api/v1/sales/{sale["id"]}/void/')
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        # El admin sí; la existencia vuelve a 10.
        self._auth(self.admin)
        ok = self.client.post(f'/api/v1/sales/{sale["id"]}/void/')
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_sale_requires_customer(self):
        # El cliente es obligatorio: una venta sin cliente debe rechazarse.
        self._auth(self.cashier)
        payload = self._sale_payload()
        payload.pop('customer')
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer', resp.data.get('errors', {}))
        # No descontó inventario.
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_anonymous_cannot_sell(self):
        resp = self.client.post('/api/v1/sales/', self._sale_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cashier_without_warehouse_cannot_sell(self):
        self.cashier.warehouse = None
        self.cashier.save(update_fields=['warehouse'])
        self._auth(self.cashier)
        resp = self.client.post('/api/v1/sales/', self._sale_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cashier_sale_uses_assigned_warehouse_ignoring_body(self):
        # El cajero intenta vender en OTRA bodega; debe forzarse a la suya.
        other = Warehouse.objects.create(name='Sucursal')
        self._auth(self.cashier)
        payload = self._sale_payload(warehouse=other.id)
        resp = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['warehouse'], self.warehouse.id)
        # La salida descontó de la bodega asignada, no de la enviada.
        self.assertTrue(
            StockMovement.objects.filter(
                type='salida', reason='venta', warehouse=self.warehouse
            ).exists()
        )

    def test_admin_chooses_warehouse_freely(self):
        other = Warehouse.objects.create(name='Sucursal')
        record_movement(
            variant=self.variant, warehouse=other,
            type='entrada', quantity=5, unit_cost=Decimal('5000'),
        )
        self._auth(self.admin)
        resp = self.client.post(
            '/api/v1/sales/', self._sale_payload(warehouse=other.id), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['warehouse'], other.id)

    def test_cashier_only_sees_own_warehouse_sales(self):
        # Venta del cajero en su bodega.
        self._auth(self.cashier)
        self.client.post('/api/v1/sales/', self._sale_payload(), format='json')
        # Venta del admin en otra bodega.
        other = Warehouse.objects.create(name='Sucursal')
        record_movement(
            variant=self.variant, warehouse=other,
            type='entrada', quantity=5, unit_cost=Decimal('5000'),
        )
        self._auth(self.admin)
        self.client.post(
            '/api/v1/sales/', self._sale_payload(warehouse=other.id), format='json'
        )
        # El admin ve ambas; el cajero solo la de su bodega.
        self.assertEqual(self.client.get('/api/v1/sales/').data['count'], 2)
        self._auth(self.cashier)
        sales = self.client.get('/api/v1/sales/').data
        self.assertEqual(sales['count'], 1)
        self.assertEqual(sales['results'][0]['warehouse'], self.warehouse.id)


class CustomerTests(SalesTestBase):
    def test_create_and_list_customer(self):
        self._auth(self.cashier)
        resp = self.client.post(
            '/api/v1/customers/',
            {'id_type': 'CC', 'id_number': '123456', 'first_name': 'Juan',
             'last_name': 'Pérez', 'email': 'juan@test.com'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        # El cliente es un usuario comprador buscable por identificación.
        listed = self.client.get('/api/v1/customers/?search=123456').data
        self.assertEqual(listed['count'], 1)
        self.assertEqual(listed['results'][0]['full_name'], 'Juan Pérez')

    def test_customer_requires_identification(self):
        self._auth(self.cashier)
        resp = self.client.post(
            '/api/v1/customers/', {'first_name': 'Sin documento'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_be_created_without_email(self):
        # Cliente de mostrador: solo identificación y nombre.
        self._auth(self.cashier)
        resp = self.client.post(
            '/api/v1/customers/',
            {'id_type': 'CC', 'id_number': '777', 'first_name': 'Mostrador'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_pos_sale_appears_in_customer_purchases(self):
        buyer = User(
            email='comprador1@test.com', first_name='Ana', role=User.Role.BUYER,
            is_email_verified=True, id_number='555',
        )
        buyer.set_password('Stockly2026')
        buyer.save()
        self._auth(self.cashier)
        self.client.post('/api/v1/sales/', self._sale_payload(customer=buyer.id), format='json')
        # El comprador ve esa venta en su historial unificado de compras.
        self._auth(buyer)
        resp = self.client.get('/api/v1/account/purchases/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sales = [i for i in resp.data if i['kind'] == 'sale']
        self.assertTrue(sales)

        # Y puede abrir el detalle de esa compra en tienda.
        sale_id = sales[0]['id']
        detail = self.client.get(f'/api/v1/account/purchases/sale/{sale_id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['customer'], buyer.id)

        # Otro comprador NO puede ver una compra ajena.
        other = User(
            email='otro_comprador@test.com', first_name='Otro', role=User.Role.BUYER,
            is_email_verified=True, id_number='556',
        )
        other.set_password('Stockly2026')
        other.save()
        self._auth(other)
        denied = self.client.get(f'/api/v1/account/purchases/sale/{sale_id}/')
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
