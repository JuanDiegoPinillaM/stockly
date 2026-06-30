from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models

# Valida un color hexadecimal (#rgb o #rrggbb).
hex_color = RegexValidator(
    r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$',
    'Usa un color hexadecimal, p. ej. #0e6e4e.',
)
# Igual, pero admite vacío (para los colores de superficie opcionales = automático).
hex_color_optional = RegexValidator(
    r'^(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))?$',
    'Usa un color hexadecimal, p. ej. #0e6e4e.',
)

# El logo se guarda como FileField (no ImageField) para permitir SVG, que Pillow
# no reconoce como imagen. Se restringe por extensión.
logo_formats = FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp', 'svg', 'gif'])
favicon_formats = FileExtensionValidator(['png', 'svg', 'ico', 'jpg', 'jpeg', 'webp'])

# Redes sociales soportadas (cada una tiene su icono en el frontend).
SOCIAL_NETWORKS = [
    'instagram', 'facebook', 'whatsapp', 'x', 'tiktok',
    'youtube', 'linkedin', 'telegram', 'twitch', 'website',
]


class SiteConfig(models.Model):
    """Configuración global del ecommerce (singleton: siempre pk=1).

    Centraliza la identidad (nombre, logo), la marca (colores), el contacto y las
    redes que antes estaban dispersos y hardcodeados en el front y en los correos.
    """

    # Identidad
    business_name = models.CharField('nombre del negocio', max_length=80, default='Stockly')
    tagline = models.CharField('eslogan', max_length=180, blank=True, default='')
    # Texto de la franja superior del ecommerce. Vacío = no se muestra la barra.
    announce_text = models.CharField(
        'texto de la barra de anuncio', max_length=160, blank=True,
        default='Envío a todo el país · Atención cercana de lunes a sábado',
    )
    # Icono lucide de la barra de anuncio (clave del catálogo del frontend).
    announce_icon = models.CharField('icono de la barra de anuncio', max_length=40, blank=True, default='Truck')
    # Color del icono de la barra (vacío = usa el color de acento).
    announce_icon_color = models.CharField(
        'color del icono de la barra', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )

    class Announce(models.TextChoices):
        STATIC = 'static', 'Estática'
        MARQUEE = 'marquee', 'Texto deslizante'

    class Speed(models.TextChoices):
        SLOW = 'slow', 'Lenta'
        NORMAL = 'normal', 'Normal'
        FAST = 'fast', 'Rápida'

    # Comportamiento de la barra de anuncio.
    announce_animation = models.CharField(
        'comportamiento de la barra', max_length=12,
        choices=Announce.choices, default=Announce.STATIC,
    )
    announce_speed = models.CharField(
        'velocidad del deslizamiento', max_length=8,
        choices=Speed.choices, default=Speed.NORMAL,
    )
    logo = models.FileField(
        'logo', upload_to='branding/', blank=True, null=True, validators=[logo_formats]
    )
    favicon = models.FileField(
        'icono de pestaña (favicon)', upload_to='branding/', blank=True, null=True,
        validators=[favicon_formats],
    )
    # Icono de marca (nombre de un icono lucide) que se usa cuando no hay logo ni
    # favicon. Vacío = la marca por defecto del front.
    icon = models.CharField('icono de marca', max_length=40, blank=True, default='')

    # Marca (solo 2 colores; el resto de la paleta se deriva)
    color_primary = models.CharField(
        'color primario', max_length=7, default='#0e6e4e', validators=[hex_color]
    )
    color_accent = models.CharField(
        'color de acento', max_length=7, default='#b8923a', validators=[hex_color]
    )

    # Colores de superficie (overrides opcionales). Vacío = automático: se usa el
    # tono por defecto. El color de texto se calcula por contraste en colors.py.
    color_navbar = models.CharField(
        'fondo de la barra de navegación', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )
    color_footer = models.CharField(
        'fondo del pie de página', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )
    color_hero = models.CharField(
        'fondo del hero de inicio', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )
    color_page = models.CharField(
        'fondo general de la página', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )
    color_announce = models.CharField(
        'fondo de la barra de anuncio', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )
    # Color del texto principal del ecommerce (titulares y cuerpo se derivan).
    # Vacío = el color de tinta por defecto.
    color_text = models.CharField(
        'color del texto', max_length=7, blank=True, default='',
        validators=[hex_color_optional],
    )

    # Tipografía (claves de un catálogo curado en el frontend: utils/fonts.js).
    font_heading = models.CharField('fuente de titulares', max_length=40, default='fraunces')
    font_body = models.CharField('fuente del cuerpo', max_length=40, default='inter')

    # Contacto (también se usa en los recibos)
    contact_email = models.EmailField('correo de contacto', blank=True, default='')
    contact_phone = models.CharField('teléfono de contacto', max_length=40, blank=True, default='')
    contact_address = models.CharField('dirección (calle)', max_length=200, blank=True, default='')
    contact_city = models.ForeignKey(
        'geo.City', verbose_name='ciudad', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    nit = models.CharField('NIT', max_length=40, blank=True, default='')

    # Redes (lista flexible: [{'network': 'instagram', 'url': 'https://…'}, …])
    socials = models.JSONField('redes sociales', blank=True, default=list)
    footer_note = models.CharField('nota del pie', max_length=200, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuración del sitio'
        verbose_name_plural = 'configuración del sitio'

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        self.pk = 1  # fuerza el singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Devuelve la única instancia, creándola con los valores de fábrica."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def full_address(self):
        """Compone la dirección: 'Calle 00 #00-00, Ciudad, Departamento, País'."""
        parts = [self.contact_address]
        city = self.contact_city
        if city:
            parts.append(city.name)
            parts.append(city.department.name)
            parts.append(city.department.country.name)
        return ', '.join(p for p in parts if p)

    def business_info(self):
        """Datos del emisor para los recibos/correos (con respaldos por defecto)."""
        return {
            'name': self.business_name or 'Stockly',
            'nit': self.nit or '',
            'address': self.full_address(),
            'phone': self.contact_phone or '',
            'email': self.contact_email or '',
        }
