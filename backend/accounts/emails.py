from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def _send_button_email(subject, to_email, context):
    """Renderiza las plantillas (texto + HTML) y envía el correo."""
    text = render_to_string('emails/button_email.txt', context)
    html = render_to_string('emails/button_email.html', context)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, 'text/html')
    msg.send()


def _token_link(user, token, path):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f'{settings.FRONTEND_URL}/{path}?uid={uid}&token={token}'


def send_verification_email(user):
    link = _token_link(user, email_verification_token.make_token(user), 'verify-email')
    _send_button_email(
        'Confirma tu cuenta de Stockly',
        user.email,
        {
            'title': 'Confirma tu correo',
            'intro': (
                f'Hola {user.first_name or user.email}, gracias por registrarte en '
                'Stockly. Confirma tu correo para activar tu cuenta.'
            ),
            'button_label': 'Activar mi cuenta',
            'link': link,
            'footer': 'Si no creaste esta cuenta, puedes ignorar este mensaje.',
        },
    )


def send_password_reset_email(user):
    link = _token_link(user, default_token_generator.make_token(user), 'reset-password')
    _send_button_email(
        'Restablece tu contraseña de Stockly',
        user.email,
        {
            'title': 'Restablece tu contraseña',
            'intro': (
                f'Hola {user.first_name or user.email}, recibimos una solicitud para '
                'restablecer tu contraseña. El enlace expira en unas horas.'
            ),
            'button_label': 'Crear nueva contraseña',
            'link': link,
            'footer': 'Si no solicitaste esto, ignora este correo; tu contraseña no cambiará.',
        },
    )


def send_invitation_email(user):
    """Invita a un usuario creado por el admin a fijar su contraseña."""
    link = _token_link(user, default_token_generator.make_token(user), 'reset-password')
    _send_button_email(
        'Te invitaron a Stockly',
        user.email,
        {
            'title': 'Activa tu cuenta',
            'intro': (
                f'Hola {user.first_name or user.email}, se creó una cuenta para ti en '
                'Stockly. Crea tu contraseña para empezar a usarla.'
            ),
            'button_label': 'Crear mi contraseña',
            'link': link,
            'footer': 'Si no esperabas esta invitación, puedes ignorar este mensaje.',
        },
    )
