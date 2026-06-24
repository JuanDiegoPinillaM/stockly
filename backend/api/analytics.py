"""Analítica del ecommerce para el panel del dashboard.

Un único endpoint `overview` arma toda la foto del negocio (KPIs, series de
tiempo, canales, top de productos/categorías, estados de pedidos, métodos de
pago e inventario) en una sola respuesta, para un panel reactivo y rápido.
`export` genera reportes CSV descargables.

Fuentes: ventas del POS (sales.Sale) + pedidos en línea (store.Order). Los
ingresos cuentan ventas COMPLETADAS y pedidos NO cancelados. La ganancia usa el
costo por línea (subtotal sin IVA − costo). El inventario es una foto actual.
"""

import csv
from datetime import timedelta

from django.db.models import (
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    When,
)
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import ProductVariant
from inventory.models import StockLevel
from sales.models import Sale, SaleItem, SalePayment, SaleStatus
from store.models import Order, OrderItem

ANALYTICS_TAG = ['Analítica']

# Periodos soportados: (días hacia atrás, agrupar por mes).
PERIODS = {
    '7d': (7, False),
    '30d': (30, False),
    '90d': (90, False),
    '12m': (365, True),
}

_DEC = DecimalField(max_digits=18, decimal_places=2)


def _cost_expr():
    """Costo de una línea = costo unitario × cantidad."""
    return ExpressionWrapper(F('unit_cost') * F('quantity'), output_field=_DEC)


def _f(value):
    """Decimal/None → float para gráficas."""
    return float(value or 0)


def _require_staff(request):
    user = request.user
    if not getattr(user, 'is_staff_member', False):
        raise PermissionDenied('Solo el personal puede ver la analítica.')
    return user


def _resolve_scope(request):
    """Devuelve el id de bodega a usar (None = todas). El no-admin queda fijo a
    su bodega asignada; el admin puede filtrar con ?warehouse=."""
    user = request.user
    if not getattr(user, 'is_admin', False):
        return user.warehouse_id
    raw = request.query_params.get('warehouse')
    return int(raw) if raw and str(raw).isdigit() else None


def _resolve_period(request):
    key = request.query_params.get('period', '30d')
    days, monthly = PERIODS.get(key, PERIODS['30d'])
    today = timezone.localdate()
    if monthly:
        # 12 cubos mensuales: primer día del mes, 11 meses atrás.
        start = (today.replace(day=1) - timedelta(days=330)).replace(day=1)
    else:
        start = today - timedelta(days=days - 1)
    span = (today - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = start - timedelta(days=span)
    return {
        'key': key,
        'monthly': monthly,
        'start': start,
        'end': today,
        'prev_start': prev_start,
        'prev_end': prev_end,
    }


def _sales_qs(start, end, warehouse_id):
    qs = Sale.objects.filter(
        status=SaleStatus.COMPLETED, created_at__date__gte=start, created_at__date__lte=end
    )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    return qs


def _orders_qs(start, end, warehouse_id):
    qs = Order.objects.exclude(status=Order.Status.CANCELLED).filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    return qs


def _totals(start, end, warehouse_id):
    """Agregados base del periodo: ingresos, neto (sin IVA), costo, # transacciones, unidades."""
    sales = _sales_qs(start, end, warehouse_id)
    orders = _orders_qs(start, end, warehouse_id)

    s_agg = sales.aggregate(rev=Sum('total'), net=Sum('subtotal'), n=Count('id'))
    o_agg = orders.aggregate(rev=Sum('total'), net=Sum('subtotal'), n=Count('id'))

    s_items = SaleItem.objects.filter(sale__in=sales).aggregate(
        cost=Sum(_cost_expr()), units=Sum('quantity')
    )
    o_items = OrderItem.objects.filter(order__in=orders).aggregate(
        cost=Sum(_cost_expr()), units=Sum('quantity')
    )

    revenue = (s_agg['rev'] or 0) + (o_agg['rev'] or 0)
    net = (s_agg['net'] or 0) + (o_agg['net'] or 0)
    cost = (s_items['cost'] or 0) + (o_items['cost'] or 0)
    txns = (s_agg['n'] or 0) + (o_agg['n'] or 0)
    units = (s_items['units'] or 0) + (o_items['units'] or 0)

    # Clientes únicos (compradores identificados) en el periodo.
    s_cust = set(sales.exclude(customer__isnull=True).values_list('customer_id', flat=True))
    o_cust = set(orders.values_list('user_id', flat=True))
    customers = len(s_cust | o_cust)

    return {
        'revenue': revenue,
        'profit': net - cost,
        'transactions': txns,
        'units': units,
        'avg_ticket': (revenue / txns) if txns else 0,
        'customers': customers,
    }


def _kpi(cur, prev):
    change = None
    if prev:
        change = round((float(cur) - float(prev)) / float(prev) * 100, 1)
    elif cur:
        change = 100.0
    return {'value': _f(cur), 'prev': _f(prev), 'change': change}


def _timeseries(period, warehouse_id):
    """Serie de ingresos, ganancia y transacciones por día (o mes)."""
    start, end, monthly = period['start'], period['end'], period['monthly']
    trunc = TruncMonth if monthly else TruncDate
    sales = _sales_qs(start, end, warehouse_id)
    orders = _orders_qs(start, end, warehouse_id)

    def group(qs, field):
        return {
            r['b']: r for r in qs.annotate(b=trunc(field)).values('b').annotate(
                rev=Sum('total'), net=Sum('subtotal'), n=Count('id')
            )
        }

    def group_cost(item_qs, field):
        return {
            r['b']: r['c']
            for r in item_qs.annotate(b=trunc(field)).values('b').annotate(c=Sum(_cost_expr()))
        }

    s_by = group(sales, 'created_at')
    o_by = group(orders, 'created_at')
    s_cost = group_cost(SaleItem.objects.filter(sale__in=sales), 'sale__created_at')
    o_cost = group_cost(OrderItem.objects.filter(order__in=orders), 'order__created_at')

    # Cubos del periodo (rellena huecos con cero).
    buckets = []
    if monthly:
        d = start.replace(day=1)
        while d <= end:
            buckets.append(d)
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        d = start
        while d <= end:
            buckets.append(d)
            d += timedelta(days=1)

    out = []
    for b in buckets:
        sb, ob = s_by.get(b, {}), o_by.get(b, {})
        rev = (sb.get('rev') or 0) + (ob.get('rev') or 0)
        net = (sb.get('net') or 0) + (ob.get('net') or 0)
        cost = (s_cost.get(b) or 0) + (o_cost.get(b) or 0)
        txns = (sb.get('n') or 0) + (ob.get('n') or 0)
        out.append({
            'date': b.isoformat(),
            'label': b.strftime('%b') if monthly else b.strftime('%d/%m'),
            'revenue': _f(rev),
            'profit': _f(net - cost),
            'orders': txns,
        })
    return out


def _top_products(period, warehouse_id, limit=8):
    start, end = period['start'], period['end']
    rows = {}
    s_items = (
        SaleItem.objects.filter(sale__in=_sales_qs(start, end, warehouse_id))
        .values(name=F('variant__product__name'))
        .annotate(units=Sum('quantity'), revenue=Sum('line_total'))
    )
    o_items = (
        OrderItem.objects.filter(order__in=_orders_qs(start, end, warehouse_id))
        .values(name=F('variant__product__name'))
        .annotate(units=Sum('quantity'), revenue=Sum('line_total'))
    )
    for r in list(s_items) + list(o_items):
        acc = rows.setdefault(r['name'], {'name': r['name'], 'units': 0, 'revenue': 0})
        acc['units'] += r['units'] or 0
        acc['revenue'] += r['revenue'] or 0
    ranked = sorted(rows.values(), key=lambda x: x['revenue'], reverse=True)[:limit]
    return [{'name': r['name'], 'units': r['units'], 'revenue': _f(r['revenue'])} for r in ranked]


def _top_categories(period, warehouse_id, limit=6):
    start, end = period['start'], period['end']
    rows = {}
    field = 'variant__product__subcategory__category__name'
    s_items = (
        SaleItem.objects.filter(sale__in=_sales_qs(start, end, warehouse_id))
        .values(name=F(field)).annotate(revenue=Sum('line_total'))
    )
    o_items = (
        OrderItem.objects.filter(order__in=_orders_qs(start, end, warehouse_id))
        .values(name=F(field)).annotate(revenue=Sum('line_total'))
    )
    for r in list(s_items) + list(o_items):
        name = r['name'] or 'Sin categoría'
        rows[name] = rows.get(name, 0) + (r['revenue'] or 0)
    ranked = sorted(rows.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{'name': n, 'revenue': _f(v)} for n, v in ranked]


def _payment_methods(period, warehouse_id):
    start, end = period['start'], period['end']
    rows = {}
    pos = (
        SalePayment.objects.filter(sale__in=_sales_qs(start, end, warehouse_id))
        .values('method').annotate(amount=Sum('amount'))
    )
    for r in pos:
        label = dict(SalePayment._meta.get_field('method').choices).get(r['method'], r['method'])
        rows[label] = rows.get(label, 0) + (r['amount'] or 0)
    online = (
        _orders_qs(start, end, warehouse_id)
        .values('payment_method').annotate(amount=Sum('total'))
    )
    for r in online:
        label = dict(Order.Payment.choices).get(r['payment_method'], r['payment_method'])
        rows[label] = rows.get(label, 0) + (r['amount'] or 0)
    return [{'name': n, 'amount': _f(v)} for n, v in sorted(rows.items(), key=lambda x: x[1], reverse=True)]


def _by_warehouse(period, warehouse_id):
    start, end = period['start'], period['end']
    rows = {}
    s = _sales_qs(start, end, warehouse_id).values(name=F('warehouse__name')).annotate(rev=Sum('total'))
    o = _orders_qs(start, end, warehouse_id).values(name=F('warehouse__name')).annotate(rev=Sum('total'))
    for r in list(s) + list(o):
        rows[r['name']] = rows.get(r['name'], 0) + (r['rev'] or 0)
    return [{'name': n, 'revenue': _f(v)} for n, v in sorted(rows.items(), key=lambda x: x[1], reverse=True)]


def _order_pipeline(period, warehouse_id):
    """Pedidos en línea por estado en el periodo (embudo operativo)."""
    start, end = period['start'], period['end']
    qs = Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    counts = {r['status']: r['n'] for r in qs.values('status').annotate(n=Count('id'))}
    labels = dict(Order.Status.choices)
    return [{'status': s, 'label': labels[s], 'count': counts.get(s, 0)} for s in labels]


def _inventory(warehouse_id):
    """Foto actual del inventario: valor, unidades, bajo stock y agotados."""
    if warehouse_id:
        # En StockLevel, el costo está en la variante (variant__…).
        unit_cost = Case(
            When(variant__average_cost__gt=0, then=F('variant__average_cost')),
            default=F('variant__cost_price'),
            output_field=_DEC,
        )
        levels = StockLevel.objects.filter(
            warehouse_id=warehouse_id, variant__is_active=True, variant__product__is_active=True
        )
        value_expr = ExpressionWrapper(F('quantity') * unit_cost, output_field=_DEC)
        agg = levels.aggregate(value=Sum(value_expr), units=Sum('quantity'))
        low = levels.filter(quantity__lte=F('variant__min_stock'), quantity__gt=0).count()
        out = levels.filter(quantity=0).count()
        low_rows = (
            levels.filter(quantity__lte=F('variant__min_stock'))
            .select_related('variant__product')
            .order_by('quantity')[:8]
        )
        low_list = [
            {
                'name': lvl.variant.product.name,
                'sku': lvl.variant.sku,
                'stock': lvl.quantity,
                'min_stock': lvl.variant.min_stock,
            }
            for lvl in low_rows
        ]
    else:
        unit_cost = Case(
            When(average_cost__gt=0, then=F('average_cost')),
            default=F('cost_price'),
            output_field=_DEC,
        )
        variants = ProductVariant.objects.filter(is_active=True, product__is_active=True)
        value_expr = ExpressionWrapper(F('stock') * unit_cost, output_field=_DEC)
        agg = variants.aggregate(value=Sum(value_expr), units=Sum('stock'))
        low = variants.filter(stock__lte=F('min_stock'), stock__gt=0).count()
        out = variants.filter(stock=0).count()
        low_rows = (
            variants.filter(stock__lte=F('min_stock'))
            .select_related('product')
            .order_by('stock')[:8]
        )
        low_list = [
            {
                'name': v.product.name,
                'sku': v.sku,
                'stock': v.stock,
                'min_stock': v.min_stock,
            }
            for v in low_rows
        ]
    return {
        'stock_value': _f(agg['value']),
        'units': agg['units'] or 0,
        'low_stock': low,
        'out_of_stock': out,
        'low_list': low_list,
    }


@extend_schema(tags=ANALYTICS_TAG, summary='Panorama de analítica del negocio')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    _require_staff(request)
    warehouse_id = _resolve_scope(request)
    period = _resolve_period(request)

    cur = _totals(period['start'], period['end'], warehouse_id)
    prev = _totals(period['prev_start'], period['prev_end'], warehouse_id)

    return Response({
        'range': {
            'period': period['key'],
            'start': period['start'].isoformat(),
            'end': period['end'].isoformat(),
            'warehouse': warehouse_id,
        },
        'kpis': {
            'revenue': _kpi(cur['revenue'], prev['revenue']),
            'profit': _kpi(cur['profit'], prev['profit']),
            'transactions': _kpi(cur['transactions'], prev['transactions']),
            'avg_ticket': _kpi(cur['avg_ticket'], prev['avg_ticket']),
            'units': _kpi(cur['units'], prev['units']),
            'customers': _kpi(cur['customers'], prev['customers']),
        },
        'timeseries': _timeseries(period, warehouse_id),
        'channels': [
            {'name': 'Punto de venta', 'amount': _f(_sales_qs(period['start'], period['end'], warehouse_id).aggregate(s=Sum('total'))['s'])},
            {'name': 'Tienda en línea', 'amount': _f(_orders_qs(period['start'], period['end'], warehouse_id).aggregate(s=Sum('total'))['s'])},
        ],
        'by_warehouse': _by_warehouse(period, warehouse_id),
        'top_products': _top_products(period, warehouse_id),
        'top_categories': _top_categories(period, warehouse_id),
        'payment_methods': _payment_methods(period, warehouse_id),
        'order_pipeline': _order_pipeline(period, warehouse_id),
        'inventory': _inventory(warehouse_id),
    })


@extend_schema(tags=ANALYTICS_TAG, summary='Exportar reporte CSV')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export(request):
    """Reporte CSV del periodo. ?dataset=sales|orders|products|inventory."""
    _require_staff(request)
    warehouse_id = _resolve_scope(request)
    period = _resolve_period(request)
    dataset = request.query_params.get('dataset', 'sales')
    start, end = period['start'], period['end']

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="stockly-{dataset}-{end}.csv"'
    response.write('﻿')  # BOM para que Excel respete los acentos
    writer = csv.writer(response)

    if dataset == 'sales':
        writer.writerow(['Número', 'Fecha', 'Bodega', 'Cliente', 'Estado', 'Subtotal', 'IVA', 'Total', 'Ítems'])
        qs = _sales_qs(start, end, warehouse_id).select_related('warehouse', 'customer').prefetch_related('items')
        for s in qs.order_by('created_at'):
            writer.writerow([
                s.number, s.created_at.strftime('%Y-%m-%d %H:%M'), s.warehouse.name,
                (s.customer.full_name if s.customer_id else 'Mostrador'),
                s.get_status_display(), s.subtotal, s.tax_total, s.total, s.total_items,
            ])
    elif dataset == 'orders':
        writer.writerow(['Número', 'Fecha', 'Punto', 'Comprador', 'Estado', 'Entrega', 'Pago', 'Total', 'Ítems'])
        qs = _orders_qs(start, end, warehouse_id).select_related('warehouse', 'user').prefetch_related('items')
        for o in qs.order_by('created_at'):
            writer.writerow([
                o.number, o.created_at.strftime('%Y-%m-%d %H:%M'), o.warehouse.name,
                o.user.full_name, o.get_status_display(), o.get_fulfillment_display(),
                o.get_payment_method_display(), o.total, o.total_items,
            ])
    elif dataset == 'products':
        writer.writerow(['Producto', 'Unidades', 'Ingresos'])
        for r in _top_products(period, warehouse_id, limit=1000):
            writer.writerow([r['name'], r['units'], r['revenue']])
    elif dataset == 'inventory':
        writer.writerow(['Producto', 'SKU', 'Existencias', 'Stock mínimo'])
        inv = _inventory(warehouse_id)
        for r in inv['low_list']:
            writer.writerow([r['name'], r['sku'], r['stock'], r['min_stock']])
    else:
        writer.writerow(['Dataset no reconocido'])

    return response
