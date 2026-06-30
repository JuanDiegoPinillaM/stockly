from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from siteconfig.branding import email_brand


def get_business():
    """Marca del emisor del recibo (datos + colores + logo + redes), tomada del
    módulo de Configuración para que el correo respete la Personalización."""
    return email_brand()


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
        'business': get_business(),
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
            'gross': _cop(sale.total + sale.discount),
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
    subject = f'Recibo de compra · {context["business"]["name"]} — Venta #{sale.number}'
    text = render_to_string('emails/sale_receipt.txt', context)
    html = render_to_string('emails/sale_receipt.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()
