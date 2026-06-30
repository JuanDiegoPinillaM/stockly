"""Marca para correos electrónicos.

Los clientes de correo no entienden variables CSS, así que aquí se resuelven los
valores reales (colores de la paleta, URL absoluta del logo, redes con etiqueta)
para inyectarlos en el contexto de las plantillas. Lo usan los recibos de venta
y los correos de pedido, de modo que TODO correo respeta la Personalización.
"""

from django.conf import settings

from .colors import palette
from .models import SiteConfig

# Etiqueta legible de cada red (espejo de utils/socials.js del frontend).
SOCIAL_LABELS = {
    'instagram': 'Instagram', 'facebook': 'Facebook', 'whatsapp': 'WhatsApp',
    'x': 'X', 'tiktok': 'TikTok', 'youtube': 'YouTube', 'linkedin': 'LinkedIn',
    'telegram': 'Telegram', 'twitch': 'Twitch', 'website': 'Sitio web',
}


def email_brand():
    """Diccionario de marca para el contexto de los correos: datos del negocio +
    colores de la paleta + logo absoluto + redes (con etiqueta)."""
    cfg = SiteConfig.load()
    tokens = palette(cfg.color_primary, cfg.color_accent)

    logo_url = ''
    if cfg.logo:
        base = getattr(settings, 'BACKEND_URL', '').rstrip('/')
        logo_url = f'{base}{cfg.logo.url}' if base else cfg.logo.url

    socials = [
        {
            'network': s['network'],
            'url': s['url'],
            'label': SOCIAL_LABELS.get(s['network'], s['network'].title()),
        }
        for s in (cfg.socials or [])
        if isinstance(s, dict) and s.get('url')
    ]

    return {
        **cfg.business_info(),  # name, nit, address, phone, email
        'logo_url': logo_url,
        'primary': tokens['color-primary'],
        'primary_dark': tokens['color-primary-dark'],
        'primary_soft': tokens['color-primary-soft'],
        'accent': tokens['color-accent'],
        'socials': socials,
    }
