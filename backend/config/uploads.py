"""Utilidades para nombrar archivos subidos de forma segura.

Nunca se guarda el nombre original del archivo del usuario: se genera un nombre
único (UUID) en el servidor, conservando solo la extensión. Así se evitan
colisiones entre archivos distintos con el mismo nombre, nombres con caracteres
peligrosos o rutas demasiado largas, y no se filtra el nombre original.
"""
import uuid
from pathlib import Path

from django.utils.deconstruct import deconstructible

# Extensiones de imagen permitidas para la extensión final del archivo.
ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}


@deconstructible
class UploadToUUID:
    """`upload_to` que guarda como `<carpeta>/<uuid>.<ext>`.

    Es deconstructible para que las migraciones puedan serializarlo.
    """

    def __init__(self, folder):
        self.folder = folder.strip('/')

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            ext = '.jpg'
        return f'{self.folder}/{uuid.uuid4().hex}{ext}'

    def __eq__(self, other):
        return isinstance(other, UploadToUUID) and self.folder == other.folder
