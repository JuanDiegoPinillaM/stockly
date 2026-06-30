import re

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .colors import palette, surfaces, text_tokens
from .models import SOCIAL_NETWORKS, SiteConfig


class SiteConfigSerializer(serializers.ModelSerializer):
    # Paleta completa derivada de los 2 colores de marca (la consume el front
    # para inyectar las variables CSS). Solo lectura: se calcula, no se guarda.
    tokens = serializers.SerializerMethodField()
    # Ubicación: nombres legibles + IDs derivados para precargar el cascadeo.
    contact_city_name = serializers.CharField(
        source='contact_city.name', read_only=True, default=None
    )
    contact_department_name = serializers.CharField(
        source='contact_city.department.name', read_only=True, default=None
    )
    contact_country_name = serializers.CharField(
        source='contact_city.department.country.name', read_only=True, default=None
    )
    contact_department = serializers.IntegerField(
        source='contact_city.department_id', read_only=True, default=None
    )
    contact_country = serializers.IntegerField(
        source='contact_city.department.country_id', read_only=True, default=None
    )
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = SiteConfig
        fields = [
            'business_name', 'tagline', 'announce_text', 'announce_icon',
            'announce_icon_color', 'announce_animation', 'announce_speed',
            'logo', 'favicon', 'icon',
            'color_primary', 'color_accent',
            'color_navbar', 'color_footer', 'color_hero', 'color_page', 'color_announce',
            'color_text', 'font_heading', 'font_body',
            'tokens',
            'contact_email', 'contact_phone', 'contact_address',
            'contact_city', 'contact_city_name', 'contact_department',
            'contact_department_name', 'contact_country', 'contact_country_name',
            'full_address', 'nit',
            'socials', 'footer_note',
            'updated_at',
        ]
        read_only_fields = ['tokens', 'full_address', 'updated_at']
        extra_kwargs = {
            'logo': {'required': False, 'allow_null': True},
            'favicon': {'required': False, 'allow_null': True},
            'contact_city': {'required': False, 'allow_null': True},
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_tokens(self, obj):
        # Paleta de marca + tokens de cada superficie (con su texto por contraste).
        return {
            **palette(obj.color_primary, obj.color_accent),
            **surfaces(
                obj.color_navbar, obj.color_footer, obj.color_hero,
                obj.color_page, obj.color_announce,
            ),
            **text_tokens(obj.color_text),
        }

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_address(self, obj):
        return obj.full_address()

    def validate_nit(self, value):
        # Normaliza el NIT al formato "900.123.456-7" (último dígito = verificación).
        digits = re.sub(r'\D', '', value or '')
        if not digits:
            return ''
        if len(digits) < 2:
            return digits
        body, dv = digits[:-1], digits[-1]
        grouped = f'{int(body):,}'.replace(',', '.')
        return f'{grouped}-{dv}'

    def validate_socials(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Las redes deben ser una lista.')
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Cada red debe ser un objeto {network, url}.')
            network = (item.get('network') or '').strip().lower()
            url = (item.get('url') or '').strip()
            if not network and not url:
                continue  # fila vacía: se ignora
            if network not in SOCIAL_NETWORKS:
                raise serializers.ValidationError(f'Red no soportada: {network or "(vacía)"}.')
            if not url:
                raise serializers.ValidationError('Cada red necesita un enlace.')
            cleaned.append({'network': network, 'url': url})
        return cleaned
