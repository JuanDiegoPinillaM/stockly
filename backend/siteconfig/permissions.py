from rest_framework import permissions


class IsAdminOrPublicRead(permissions.BasePermission):
    """Lectura para CUALQUIERA (la tienda es pública, incluso sin sesión);
    escritura solo para administradores."""

    message = 'Solo un administrador puede cambiar la configuración.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_admin', False)
        )
