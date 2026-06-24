from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_order_confirmation_email(order):
    """Envía al comprador la confirmación de su pedido (texto + HTML)."""
    to_email = order.user.email
    if not to_email:
        return
    context = {
        'order': order,
        'items': list(order.items.all()),
        'business': 'Stockly',
    }
    subject = f'Confirmación de tu pedido — Pedido #{order.number}'
    text = render_to_string('emails/order_confirmation.txt', context)
    html = render_to_string('emails/order_confirmation.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()
