from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from catalog.models import Category, Product, ProductVariant, Subcategory
from inventory.models import Warehouse
from sales.models import Sale, SaleItem, SalePayment, SaleStatus
from store.models import Order

User = get_user_model()


class AnalyticsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Stockly2026',
            role=User.Role.ADMIN, is_email_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer@test.com', password='Stockly2026',
            role=User.Role.BUYER, is_email_verified=True,
        )
        self.wh = Warehouse.objects.create(name='Centro')
        cat = Category.objects.create(name='Ropa')
        sub = Subcategory.objects.create(category=cat, name='Camisetas')
        prod = Product.objects.create(name='Camiseta', subcategory=sub)
        self.v = ProductVariant.objects.create(
            product=prod, sku='C-1', sale_price=Decimal('50000'),
            cost_price=Decimal('20000'), stock=10, min_stock=2,
        )
        sale = Sale.objects.create(
            number=1, warehouse=self.wh, status=SaleStatus.COMPLETED,
            subtotal=Decimal('42016'), tax_total=Decimal('7984'),
            total=Decimal('50000'), paid=Decimal('50000'), customer=self.buyer,
        )
        SaleItem.objects.create(
            sale=sale, variant=self.v, description='Camiseta', quantity=2,
            unit_price=Decimal('25000'), unit_cost=Decimal('10000'),
            line_total=Decimal('50000'), tax_rate=19,
        )
        SalePayment.objects.create(sale=sale, method='efectivo', amount=Decimal('50000'))
        Order.objects.create(
            number=1, user=self.buyer, warehouse=self.wh,
            payment_method=Order.Payment.CARD, status=Order.Status.PENDING,
            subtotal=Decimal('42016'), tax_total=Decimal('7984'), total=Decimal('50000'),
        )

    def _auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Stockly2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_overview_for_staff(self):
        self._auth(self.admin)
        resp = self.client.get('/api/v1/analytics/overview/?period=30d')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('kpis', resp.data)
        # Ingresos = venta (50.000) + pedido (50.000).
        self.assertEqual(resp.data['kpis']['revenue']['value'], 100000.0)
        self.assertEqual(resp.data['kpis']['transactions']['value'], 2)
        self.assertTrue(len(resp.data['timeseries']) > 0)
        self.assertTrue(len(resp.data['top_products']) >= 1)
        self.assertIn('inventory', resp.data)

    def test_periods_supported(self):
        self._auth(self.admin)
        for p in ('7d', '30d', '90d', '12m'):
            resp = self.client.get(f'/api/v1/analytics/overview/?period={p}')
            self.assertEqual(resp.status_code, 200, p)

    def test_overview_scoped_by_warehouse(self):
        # Filtrar por bodega usa el inventario por StockLevel (no debe romperse).
        self._auth(self.admin)
        resp = self.client.get(f'/api/v1/analytics/overview/?period=30d&warehouse={self.wh.id}')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('inventory', resp.data)
        self.assertEqual(resp.data['range']['warehouse'], self.wh.id)

    def test_buyer_forbidden(self):
        self._auth(self.buyer)
        resp = self.client.get('/api/v1/analytics/overview/')
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_unauthorized(self):
        self.assertEqual(self.client.get('/api/v1/analytics/overview/').status_code, 401)

    def test_export_sales_csv(self):
        self._auth(self.admin)
        resp = self.client.get('/api/v1/analytics/export/?dataset=sales&period=30d')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        self.assertIn('attachment', resp['Content-Disposition'])
        self.assertIn('Total', resp.content.decode('utf-8'))
