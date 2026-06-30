"""Geocodificación (OpenStreetMap / Nominatim) y distancia entre coordenadas.

- `geocode(texto)` convierte una dirección en coordenadas (lat, lon). Es
  best-effort: ante cualquier fallo (red, sin resultados, desactivado) devuelve
  None y quien llama sigue sin coordenadas (el ruteo cae al método por ciudad).
- `haversine_km(a, b)` da la distancia en kilómetros entre dos puntos, para
  elegir la bodega más cercana al comprador. Sin librerías externas.

Se respeta la política de uso de Nominatim: llamada desde el servidor, con un
User-Agent que identifica a Stockly y una sola petición por dirección guardada.
"""
import json
import re
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from math import asin, cos, radians, sin, sqrt

from django.conf import settings

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
_USER_AGENT = 'Stockly/1.0 (tienda en línea; ruteo de pedidos al punto más cercano)'


def geocode(query, *, country_code='co', timeout=5):
    """Devuelve (lat, lon) como Decimal para una dirección en texto, o None."""
    query = (query or '').strip()
    if not query or not getattr(settings, 'GEOCODING_ENABLED', False):
        return None
    params = {'q': query, 'format': 'json', 'limit': 1}
    if country_code:
        params['countrycodes'] = country_code
    url = f'{NOMINATIM_URL}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if not data:
            return None
        return Decimal(str(data[0]['lat'])), Decimal(str(data[0]['lon']))
    except (OSError, ValueError, KeyError, InvalidOperation):
        return None


def coords_from_map_url(url):
    """Extrae (lat, lon) de un enlace de Google Maps, o None.

    Soporta el src del iframe (`...!2d{lon}!3d{lat}...`) y la URL con
    `@{lat},{lon},...`. Así, al pegar el mapa, ya tenemos las coordenadas sin
    geocodificar.
    """
    if not url:
        return None
    m = re.search(r'!2d(-?\d+(?:\.\d+)?)!3d(-?\d+(?:\.\d+)?)', url)
    if m:  # en el embed va primero la longitud (2d) y luego la latitud (3d)
        return Decimal(m.group(2)), Decimal(m.group(1))
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        return Decimal(m.group(1)), Decimal(m.group(2))
    return None


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos (lat/lon en grados). None si falta alguno."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        lat1, lon1, lat2, lon2 = (radians(float(v)) for v in (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return None
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371.0  # radio medio de la Tierra en km
