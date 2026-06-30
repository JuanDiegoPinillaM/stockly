from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product, ProductVariant, Subcategory

from .models import StockLevel, StockMovement, Warehouse
from .schedule import summarize_schedule
from .services import InsufficientStock, InventoryError, record_movement

User = get_user_model()


class InventoryTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = self._user('admin@test.com', 'admin', User.Role.ADMIN)
        self.user = self._user('user@test.com', 'user', User.Role.CASHIER)
        self.category = Category.objects.create(name='Ropa')
        self.subcategory = Subcategory.objects.create(
            category=self.category, name='Camisetas'
        )
        self.product = Product.objects.create(name='Camiseta', subcategory=self.subcategory)
        self.variant = ProductVariant.objects.create(
            product=self.product, sku='CAM-1', cost_price=1000, sale_price=2500
        )
        self.wh = Warehouse.objects.create(name='Principal', code='PRIN')

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
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def _move(self, **data):
        return self.client.post('/api/v1/movements/', data, format='json')


class WarehouseTests(InventoryTestBase):
    def test_admin_creates_warehouse(self):
        self._auth(self.admin)
        resp = self.client.post('/api/v1/warehouses/', {'name': 'Sucursal Norte'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_create_warehouse(self):
        self._auth(self.user)
        resp = self.client.post('/api/v1/warehouses/', {'name': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_only_deactivates_warehouse(self):
        self._auth(self.admin)
        resp = self.client.delete(f'/api/v1/warehouses/{self.wh.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Warehouse.objects.get(pk=self.wh.id).is_active)

    def test_detail_includes_inventory_stats(self):
        self._auth(self.admin)
        self._move(
            variant=self.variant.id, warehouse=self.wh.id,
            type='entrada', quantity=7, unit_cost='1000.00',
        )
        resp = self.client.get(f'/api/v1/warehouses/{self.wh.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['stats']['total_units'], 7)
        self.assertEqual(resp.data['stats']['variant_count'], 1)
        self.assertEqual(resp.data['stats']['product_count'], 1)
        # El detalle también resume el horario por día.
        self.assertIn('schedule_display', resp.data)

    def test_phone_must_have_ten_digits(self):
        self._auth(self.admin)
        bad = self.client.post(
            '/api/v1/warehouses/', {'name': 'Tel corto', 'phone': '123'}, format='json'
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        ok = self.client.post(
            '/api/v1/warehouses/', {'name': 'Tel ok', 'phone': '3001234567'}, format='json'
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)
        # Se normaliza al formato agrupado "300 123 4567".
        self.assertEqual(ok.data['phone'], '300 123 4567')


class MovementTests(InventoryTestBase):
    def setUp(self):
        super().setUp()
        self._auth(self.admin)

    def test_entry_increases_stock_and_sets_average_cost(self):
        resp = self._move(
            variant=self.variant.id, warehouse=self.wh.id,
            type='entrada', quantity=10, unit_cost='1000.00',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['balance_after'], 10)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)
        self.assertEqual(self.variant.average_cost, 1000)

    def test_weighted_average_recalculates_on_second_entry(self):
        self._move(variant=self.variant.id, warehouse=self.wh.id,
                   type='entrada', quantity=10, unit_cost='1000.00')
        self._move(variant=self.variant.id, warehouse=self.wh.id,
                   type='entrada', quantity=10, unit_cost='2000.00')
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 20)
        self.assertEqual(self.variant.average_cost, 1500)

    def test_exit_uses_average_cost_and_reduces_stock(self):
        # La salida (venta) se aplica por el servicio; el módulo POS la usa.
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=10, unit_cost=1000)
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=10, unit_cost=2000)
        mv = record_movement(variant=self.variant, warehouse=self.wh,
                             type='salida', quantity=5)
        self.assertEqual(mv.unit_cost, 1500)  # costo promedio
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 15)
        self.assertEqual(self.variant.average_cost, 1500)  # la salida no lo cambia

    def test_api_rejects_manual_exit(self):
        # La salida ya no se permite a mano: las ventas pasan por el POS.
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=5, unit_cost=1000)
        resp = self._move(variant=self.variant.id, warehouse=self.wh.id,
                          type='salida', quantity=2)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_adjust_out_reduces_without_changing_average(self):
        self._move(variant=self.variant.id, warehouse=self.wh.id,
                   type='entrada', quantity=10, unit_cost='1000.00')
        resp = self._move(variant=self.variant.id, warehouse=self.wh.id,
                          type='ajuste_salida', quantity=2, reason='merma_dano')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 8)
        self.assertEqual(self.variant.average_cost, 1000)

    def test_transfer_service_moves_between_warehouses(self):
        # La transferencia inmediata ya no se expone por el endpoint (va por el
        # flujo con aprobación); el servicio `_transfer` sigue siendo válido.
        other = Warehouse.objects.create(name='Sucursal')
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=10, unit_cost=1000)
        record_movement(variant=self.variant, warehouse=self.wh, warehouse_to=other,
                        type='transferencia', quantity=4)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)  # total no cambia
        self.assertEqual(StockLevel.objects.get(variant=self.variant, warehouse=self.wh).quantity, 6)
        self.assertEqual(StockLevel.objects.get(variant=self.variant, warehouse=other).quantity, 4)
        # Genera dos asientos (salida origen + entrada destino).
        self.assertEqual(StockMovement.objects.filter(type='transferencia').count(), 2)
        origin_move = StockMovement.objects.get(type='transferencia', warehouse=self.wh)
        dest_move = StockMovement.objects.get(type='transferencia', warehouse=other)
        self.assertEqual(origin_move.signed_quantity, -4)
        self.assertEqual(dest_move.signed_quantity, 4)
        self.assertFalse(origin_move.is_inbound)
        self.assertTrue(dest_move.is_inbound)

    def test_transfer_service_requires_destination(self):
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=5, unit_cost=1000)
        with self.assertRaises(InventoryError):
            record_movement(variant=self.variant, warehouse=self.wh,
                            type='transferencia', quantity=2)

    def test_manual_transfer_via_endpoint_is_rejected(self):
        # El formulario de movimientos ya no acepta transferencias.
        other = Warehouse.objects.create(name='Sucursal')
        record_movement(variant=self.variant, warehouse=self.wh,
                        type='entrada', quantity=5, unit_cost=1000)
        resp = self._move(variant=self.variant.id, warehouse=self.wh.id,
                          warehouse_to=other.id, type='transferencia', quantity=2)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_movements_are_append_only(self):
        mv = self._move(variant=self.variant.id, warehouse=self.wh.id,
                        type='entrada', quantity=5, unit_cost='1000.00').data
        put = self.client.put(f'/api/v1/movements/{mv["id"]}/', {}, format='json')
        delete = self.client.delete(f'/api/v1/movements/{mv["id"]}/')
        self.assertEqual(put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_user_cannot_create_movement(self):
        self._auth(self.user)
        resp = self._move(variant=self.variant.id, warehouse=self.wh.id,
                          type='entrada', quantity=5, unit_cost='1000.00')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_kardex_filtered_by_variant(self):
        self._move(variant=self.variant.id, warehouse=self.wh.id,
                   type='entrada', quantity=5, unit_cost='1000.00')
        resp = self.client.get(f'/api/v1/movements/?variant={self.variant.id}')
        self.assertEqual(resp.data['count'], 1)


class LowStockTests(InventoryTestBase):
    def test_low_stock_lists_variants_at_or_below_min(self):
        self._auth(self.admin)
        low = ProductVariant.objects.create(
            product=self.product, sku='LOW-1', sale_price=1000, min_stock=5
        )
        record_movement(variant=low, warehouse=self.wh, type='entrada',
                        quantity=2, unit_cost=1000)
        # Una con stock holgado no debe aparecer.
        ok = ProductVariant.objects.create(
            product=self.product, sku='OK-1', sale_price=1000, min_stock=1
        )
        record_movement(variant=ok, warehouse=self.wh, type='entrada',
                        quantity=50, unit_cost=1000)
        resp = self.client.get('/api/v1/low-stock/')
        skus = [v['sku'] for v in resp.data['results']]
        self.assertIn('LOW-1', skus)
        self.assertNotIn('OK-1', skus)

    def test_service_raises_on_oversell(self):
        record_movement(variant=self.variant, warehouse=self.wh, type='entrada',
                        quantity=1, unit_cost=1000)
        with self.assertRaises(InsufficientStock):
            record_movement(variant=self.variant, warehouse=self.wh,
                            type='salida', quantity=5)


class TransferTests(InventoryTestBase):
    """Flujo de transferencias entre puntos con aprobación."""

    def setUp(self):
        super().setUp()
        self.origin = self.wh  # 'Principal'
        self.dest = Warehouse.objects.create(name='Sucursal', code='SUC')
        self.jefe_origin = self._user('jorigen@test.com', 'JefeO', User.Role.WAREHOUSE_MANAGER)
        self.jefe_origin.warehouse = self.origin
        self.jefe_origin.save(update_fields=['warehouse'])
        self.jefe_dest = self._user('jdest@test.com', 'JefeD', User.Role.WAREHOUSE_MANAGER)
        self.jefe_dest.warehouse = self.dest
        self.jefe_dest.save(update_fields=['warehouse'])
        # 10 unidades en la bodega origen.
        record_movement(variant=self.variant, warehouse=self.origin,
                        type='entrada', quantity=10, unit_cost=1000)

    def _payload(self, quantity=4, **over):
        data = {
            'origin': self.origin.id,
            'destination': self.dest.id,
            'items': [{'variant': self.variant.id, 'quantity': quantity}],
        }
        data.update(over)
        return data

    def _level(self, warehouse):
        lvl = StockLevel.objects.filter(variant=self.variant, warehouse=warehouse).first()
        return lvl.quantity if lvl else 0

    def _request(self, user, **over):
        self._auth(user)
        return self.client.post('/api/v1/transfers/', self._payload(**over), format='json')

    def test_request_reserves_stock_from_origin(self):
        resp = self._request(self.jefe_origin)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'pendiente')
        # La existencia salió de origen (en tránsito): origen 6, destino 0.
        self.assertEqual(self._level(self.origin), 6)
        self.assertEqual(self._level(self.dest), 0)

    def test_accept_moves_stock_to_destination(self):
        tid = self._request(self.jefe_origin).data['id']
        self._auth(self.jefe_dest)
        resp = self.client.post(f'/api/v1/transfers/{tid}/accept/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'aceptada')
        self.assertEqual(self._level(self.origin), 6)
        self.assertEqual(self._level(self.dest), 4)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)  # total intacto tras aceptar

    def test_reject_returns_stock_to_origin(self):
        tid = self._request(self.jefe_origin).data['id']
        self._auth(self.jefe_dest)
        resp = self.client.post(f'/api/v1/transfers/{tid}/reject/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'rechazada')
        self.assertEqual(self._level(self.origin), 10)
        self.assertEqual(self._level(self.dest), 0)

    def test_cancel_by_origin_returns_stock(self):
        tid = self._request(self.jefe_origin).data['id']
        self._auth(self.jefe_origin)
        resp = self.client.post(f'/api/v1/transfers/{tid}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'cancelada')
        self.assertEqual(self._level(self.origin), 10)

    def test_origin_jefe_cannot_accept(self):
        tid = self._request(self.jefe_origin).data['id']
        self._auth(self.jefe_origin)
        resp = self.client.post(f'/api/v1/transfers/{tid}/accept/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cashier_cannot_request(self):
        resp = self._request(self.user)  # self.user es cajero
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_jefe_origin_is_forced_to_own_warehouse(self):
        # Aunque envíe otra bodega origen, se fuerza a la suya.
        self._auth(self.jefe_origin)
        resp = self.client.post(
            '/api/v1/transfers/', self._payload(origin=self.dest.id), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['origin'], self.origin.id)

    def test_request_insufficient_stock_fails(self):
        resp = self._request(self.jefe_origin, quantity=99)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._level(self.origin), 10)  # no se reservó nada

    def test_cannot_accept_twice(self):
        tid = self._request(self.jefe_origin).data['id']
        self._auth(self.jefe_dest)
        self.client.post(f'/api/v1/transfers/{tid}/accept/')
        resp = self.client.post(f'/api/v1/transfers/{tid}/accept/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_transfer_movement_is_rejected(self):
        # La transferencia ya no se permite en el formulario de movimientos.
        self._auth(self.admin)
        resp = self._move(variant=self.variant.id, warehouse=self.origin.id,
                          warehouse_to=self.dest.id, type='transferencia', quantity=1)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ScheduleSummaryTests(SimpleTestCase):
    """Resumen del horario: agrupa días consecutivos con el mismo horario."""

    def test_groups_weekdays_and_weekend_with_holidays(self):
        sched = {d: {'open': '07:00', 'close': '21:00'} for d in ['mon', 'tue', 'wed', 'thu', 'fri']}
        sched['sat'] = sched['sun'] = sched['holidays'] = {'open': '07:00', 'close': '20:00'}
        out = summarize_schedule(sched)
        self.assertEqual(out[0]['days'], 'Lunes a viernes')
        self.assertEqual(out[0]['hours'], '7:00 a.m. – 9:00 p.m.')
        self.assertEqual(out[1]['days'], 'Fines de semana y festivos')

    def test_closed_day_shown_as_closed(self):
        sched = {d: {'open': '08:00', 'close': '18:00'} for d in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']}
        sched['sun'] = {'closed': True}
        out = summarize_schedule(sched)
        self.assertEqual(out[-1]['days'], 'Domingo')
        self.assertEqual(out[-1]['hours'], 'Cerrado')

    def test_empty_schedule(self):
        self.assertEqual(summarize_schedule({}), [])
