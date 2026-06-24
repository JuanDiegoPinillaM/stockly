from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token de un solo uso para verificar el correo.

    Incluye `is_email_verified` en el hash: una vez verificada la cuenta,
    el token deja de ser válido automáticamente.
    """

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{timestamp}{user.is_email_verified}'


email_verification_token = EmailVerificationTokenGenerator()
