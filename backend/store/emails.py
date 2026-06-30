from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from siteconfig.branding import email_brand


def send_order_confirmation_email(order):
    """Envía al comprador la confirmación de su pedido (texto + HTML)."""
    to_email = order.user.email
    if not to_email:
        return
    # Datos completos del negocio (nombre, NIT, dirección, contacto), igual que el
    # recibo de venta, para un correo consistente.
    business = email_brand()
    context = {
        'order': order,
        'items': list(order.items.all()),
        'business': business,
    }
    subject = f'Confirmación de tu pedido · {business["name"]} — Pedido #{order.number}'
    text = render_to_string('emails/order_confirmation.txt', context)
    html = render_to_string('emails/order_confirmation.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()


# Mensaje (titular + texto) por cada estado al que avanza un pedido. PENDING no
# está: ese estado lo cubre el correo de confirmación al crear el pedido.
ORDER_STATUS_COPY = {
    'confirmado': ('Tu pedido fue confirmado',
                   'Recibimos tu pago y estamos preparando tu pedido.'),
    'enviado': ('Tu pedido va en camino',
                'Despachamos tu pedido. Pronto lo tendrás contigo.'),
    'entregado': ('Tu pedido fue entregado',
                  '¡Esperamos que lo disfrutes! Gracias por confiar en nosotros.'),
    'cancelado': ('Tu pedido fue cancelado',
                  'Tu pedido se canceló. Si tienes dudas, escríbenos y te ayudamos.'),
}


def send_order_status_email(order):
    """Avisa al comprador cuando su pedido cambia de estado (confirmado, enviado,
    entregado o cancelado). Sin correo del comprador o estado sin copy, no hace nada."""
    to_email = order.user.email
    if not to_email:
        return
    copy = ORDER_STATUS_COPY.get(order.status)
    if not copy:
        return
    headline, message = copy
    business = email_brand()
    context = {
        'order': order,
        'business': business,
        'headline': headline,
        'message': message,
        'cancel_reason': order.cancel_reason if order.status == 'cancelado' else '',
    }
    subject = f'{headline} · {business["name"]} — Pedido #{order.number}'
    text = render_to_string('emails/order_status.txt', context)
    html = render_to_string('emails/order_status.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()
