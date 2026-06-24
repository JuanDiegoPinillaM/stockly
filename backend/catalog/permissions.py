from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Lectura para cualquier usuario autenticado; escritura solo para admin.

    El rol vive en `user.role` (campo del modelo accounts.User), expuesto
    también como la propiedad `user.is_admin`.
    """

    message = 'Solo un administrador puede realizar esta acción.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(request.user, 'is_admin', False)
