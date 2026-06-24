from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

# Datos del emisor que aparecen en el recibo. Edítalos con los de tu negocio
# (o muévelos a settings/variables de entorno si prefieres configurarlos ahí).
BUSINESS = {
    'name': getattr(settings, 'BUSINESS_NAME', 'Stockly'),
    'nit': getattr(settings, 'BUSINESS_NIT', '900.123.456-7'),
    'address': getattr(settings, 'BUSINESS_ADDRESS', 'Cra 00 #00-00, Medellín, Colombia'),
    'phone': getattr(settings, 'BUSINESS_PHONE', '+57 300 123 4567'),
    'email': getattr(settings, 'BUSINESS_EMAIL', 'hola@stockly.com'),
}


def _cop(value):
    """Formatea un monto como pesos colombianos: 23800 -> '$23.800'."""
    try:
        return '$' + f'{int(round(float(value))):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return '$0'


def _receipt_context(sale):
    """Arma el contexto del recibo con montos ya formateados (COP)."""
    customer = None
    if sale.customer_id:
        c = sale.customer
        doc = ''
        if c.id_number:
            doc = f'{c.get_id_type_display()} {c.id_number}'
        customer = {'name': c.full_name, 'document': doc, 'email': c.email or ''}

    items = [
        {
            'description': i.description,
            'sku': i.sku,
            'quantity': i.quantity,
            'tax_rate': i.tax_rate,
            'unit_price': _cop(i.unit_price),
            'line_total': _cop(i.line_total),
        }
        for i in sale.items.all()
    ]
    payments = [
        {'method': p.get_method_display(), 'amount': _cop(p.amount)}
        for p in sale.payments.all()
    ]
    return {
        'business': BUSINESS,
        'sale': {
            'number': sale.number,
            'date': timezone.localtime(sale.created_at).strftime('%d/%m/%Y · %I:%M %p'),
            'status': sale.get_status_display(),
            'is_void': sale.status == 'anulada',
            'warehouse': sale.warehouse.name if sale.warehouse_id else '',
            'cashier': sale.created_by.first_name if sale.created_by_id else '',
            'note': sale.note,
        },
        'customer': customer,
        'items': items,
        'payments': payments,
        'totals': {
            'subtotal': _cop(sale.subtotal),
            'tax': _cop(sale.tax_total),
            'discount': _cop(sale.discount),
            'has_discount': bool(sale.discount),
            'total': _cop(sale.total),
            'paid': _cop(sale.paid),
            'change': _cop(sale.change),
            'item_count': sum(i.quantity for i in sale.items.all()),
        },
    }


def send_receipt_email(sale, to_email):
    """Envía el recibo de una venta (texto + HTML) al correo indicado."""
    context = _receipt_context(sale)
    subject = f'Recibo de compra · {BUSINESS["name"]} — Venta #{sale.number}'
    text = render_to_string('emails/sale_receipt.txt', context)
    html = render_to_string('emails/sale_receipt.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()
