"""Derivación de paleta a partir de 2 colores de marca.

El módulo de Configuración guarda solo el color primario y el de acento; aquí se
calculan todos los tonos derivados (dark/light/soft + triples RGB) que el frontend
inyecta como variables CSS. Así el administrador elige 2 colores y obtiene una
paleta coherente, sin poder romper el sistema con tonos incoherentes.
"""


def _clamp(value):
    return max(0, min(255, int(round(value))))


def hex_to_rgb(value):
    """'#0e6e4e' -> (14, 110, 78). Tolera may/min y el '#' opcional."""
    h = (value or '').strip().lstrip('#')
    if len(h) == 3:  # forma corta #abc
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f'Color hex inválido: {value!r}')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(_clamp(c) for c in rgb))


def _mix(rgb, other, weight):
    """Mezcla `rgb` con `other` (0 = todo rgb, 1 = todo other)."""
    return tuple(c * (1 - weight) + o * weight for c, o in zip(rgb, other))


def darken(hex_value, weight):
    """Oscurece mezclando con negro."""
    return rgb_to_hex(_mix(hex_to_rgb(hex_value), (0, 0, 0), weight))


def lighten(hex_value, weight):
    """Aclara mezclando con blanco."""
    return rgb_to_hex(_mix(hex_to_rgb(hex_value), (255, 255, 255), weight))


def palette(primary, accent):
    """Devuelve el mapa de tokens CSS (sin el prefijo '--') derivados de los 2
    colores de marca. Las claves coinciden con las variables de main.css."""
    p = hex_to_rgb(primary)
    a = hex_to_rgb(accent)
    return {
        'color-primary': rgb_to_hex(p),
        'color-primary-rgb': '{}, {}, {}'.format(*p),
        'color-primary-dark': darken(primary, 0.18),
        'color-primary-light': lighten(primary, 0.14),
        'color-primary-soft': lighten(primary, 0.90),
        'color-accent': rgb_to_hex(a),
        'color-accent-rgb': '{}, {}, {}'.format(*a),
        'color-accent-dark': darken(accent, 0.18),
        'color-accent-soft': lighten(accent, 0.88),
    }


# --- Superficies personalizables (navbar, footer, hero, fondo) ---------------
# Texto oscuro / claro que se coloca encima según el contraste del fondo.
INK_DARK = '#14201a'
INK_LIGHT = '#f6f3ec'

# Fondo por defecto de cada superficie cuando el administrador no define override
# (reproducen el aspecto actual del ecommerce).
SURFACE_DEFAULTS = {
    'color-navbar': '#faf7f0',    # crema
    'color-footer': '#0e1a14',    # tinta oscura
    'color-hero': '#faf7f0',      # crema
    'color-page': '#ffffff',      # blanco
    'color-announce': '#14201a',  # tinta (barra de anuncio)
}


def relative_luminance(rgb):
    """Luminancia relativa sRGB (WCAG), 0 (negro) … 1 (blanco)."""
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on(bg_hex):
    """Devuelve el color de texto legible (oscuro o claro) sobre `bg_hex`."""
    return INK_DARK if relative_luminance(hex_to_rgb(bg_hex)) > 0.45 else INK_LIGHT


def _rgba(hex_value, alpha):
    r, g, b = hex_to_rgb(hex_value)
    return f'rgba({r}, {g}, {b}, {alpha})'


def surface(prefix, bg_hex):
    """Tokens derivados de una superficie con su propio fondo: fondo + triple rgb
    + texto fuerte/normal/tenue + línea + campo, con contraste correcto sea el
    fondo claro u oscuro (el texto se mezcla hacia el fondo para los tonos tenues).
    """
    bg = rgb_to_hex(hex_to_rgb(bg_hex))
    rgb = hex_to_rgb(bg)
    ink = ink_on(bg)
    ink_rgb = hex_to_rgb(ink)
    return {
        prefix: bg,
        f'{prefix}-rgb': '{}, {}, {}'.format(*rgb),
        f'{prefix}-ink': ink,
        f'{prefix}-text': rgb_to_hex(_mix(ink_rgb, rgb, 0.22)),
        f'{prefix}-muted': rgb_to_hex(_mix(ink_rgb, rgb, 0.45)),
        f'{prefix}-line': _rgba(ink, 0.12),
        f'{prefix}-field': _rgba(ink, 0.06),
    }


def text_tokens(color_text):
    """Si el admin define un color de texto, sobrescribe la tinta principal y
    deriva el cuerpo (un poco más suave) y su triple rgb. Vacío = sin cambios."""
    if not color_text:
        return {}
    ink = rgb_to_hex(hex_to_rgb(color_text))
    ink_rgb = hex_to_rgb(ink)
    return {
        'color-ink': ink,
        'color-ink-rgb': '{}, {}, {}'.format(*ink_rgb),
        'color-body': rgb_to_hex(_mix(ink_rgb, (255, 255, 255), 0.26)),
        'color-muted': rgb_to_hex(_mix(ink_rgb, (255, 255, 255), 0.48)),
    }


def surfaces(navbar='', footer='', hero='', page='', announce=''):
    """Mapa de tokens para las superficies. Un valor vacío usa el defecto."""
    out = {}
    out.update(surface('color-navbar', navbar or SURFACE_DEFAULTS['color-navbar']))
    out.update(surface('color-footer', footer or SURFACE_DEFAULTS['color-footer']))
    out.update(surface('color-hero', hero or SURFACE_DEFAULTS['color-hero']))
    out.update(surface('color-announce', announce or SURFACE_DEFAULTS['color-announce']))
    # El fondo general SOLO se emite si el admin lo personaliza; así, en automático,
    # cada área conserva su propio fondo por defecto (ecommerce claro, dashboard
    # crema) y el card-on-bg mantiene su contraste.
    if page:
        page_bg = rgb_to_hex(hex_to_rgb(page))
        out['color-page'] = page_bg
        out['color-page-ink'] = ink_on(page_bg)
    return out
