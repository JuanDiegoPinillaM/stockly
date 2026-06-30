from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from geo.geocoding import coords_from_map_url, geocode, haversine_km


class GeocodingUtilsTests(SimpleTestCase):
    def test_coords_from_google_embed_url(self):
        # En el embed (pb) va primero la longitud (!2d) y luego la latitud (!3d).
        url = 'https://www.google.com/maps/embed?pb=!1m18!2d-76.5320!3d3.4516!2m3'
        coords = coords_from_map_url(url)
        self.assertEqual(coords, (Decimal('3.4516'), Decimal('-76.5320')))

    def test_coords_from_at_url(self):
        url = 'https://www.google.com/maps/@3.4516,-76.5320,15z'
        self.assertEqual(coords_from_map_url(url), (Decimal('3.4516'), Decimal('-76.5320')))

    def test_coords_from_url_none_when_absent(self):
        self.assertIsNone(coords_from_map_url('https://example.com/no-coords'))
        self.assertIsNone(coords_from_map_url(''))

    def test_haversine_known_distance(self):
        # Bogotá (4.61,-74.08) a Cali (3.45,-76.53): ~300 km.
        d = haversine_km(4.61, -74.08, 3.45, -76.53)
        self.assertTrue(280 < d < 320, d)

    def test_haversine_none_when_missing_coord(self):
        self.assertIsNone(haversine_km(1, 2, None, 4))

    @override_settings(GEOCODING_ENABLED=False)
    def test_geocode_disabled_returns_none_without_network(self):
        self.assertIsNone(geocode('Calle 5, Cali, Colombia'))
