/**
 * Derivación de paleta en el cliente, espejo de backend/siteconfig/colors.py.
 * Se usa SOLO para la vista previa en vivo del módulo de Configuración; la
 * verdad la calcula el backend y la devuelve en `tokens` al guardar.
 */

const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)))

export function hexToRgb(value) {
  let h = String(value || '').trim().replace(/^#/, '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
}

export function rgbToHex(rgb) {
  return '#' + rgb.map((c) => clamp(c).toString(16).padStart(2, '0')).join('')
}

const mix = (rgb, other, w) => rgb.map((c, i) => c * (1 - w) + other[i] * w)
const darken = (hex, w) => rgbToHex(mix(hexToRgb(hex), [0, 0, 0], w))
const lighten = (hex, w) => rgbToHex(mix(hexToRgb(hex), [255, 255, 255], w))

// --- Superficies (espejo de colors.py: surface/surfaces) ---
const INK_DARK = '#14201a'
const INK_LIGHT = '#f6f3ec'

const SURFACE_DEFAULTS = {
  'color-navbar': '#faf7f0',
  'color-footer': '#0e1a14',
  'color-hero': '#faf7f0',
  'color-page': '#ffffff',
  'color-announce': '#14201a'
}

function relativeLuminance(rgb) {
  const ch = (c) => {
    c /= 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const [r, g, b] = rgb.map(ch)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function inkOn(bgHex) {
  const rgb = hexToRgb(bgHex)
  if (!rgb) return INK_DARK
  return relativeLuminance(rgb) > 0.45 ? INK_DARK : INK_LIGHT
}

const rgba = (hex, a) => `rgba(${hexToRgb(hex).join(', ')}, ${a})`

function surface(prefix, bgHex) {
  const rgb = hexToRgb(bgHex)
  if (!rgb) return {}
  const bg = rgbToHex(rgb)
  const ink = inkOn(bg)
  const inkRgb = hexToRgb(ink)
  return {
    [prefix]: bg,
    [`${prefix}-rgb`]: rgb.join(', '),
    [`${prefix}-ink`]: ink,
    [`${prefix}-text`]: rgbToHex(mix(inkRgb, rgb, 0.22)),
    [`${prefix}-muted`]: rgbToHex(mix(inkRgb, rgb, 0.45)),
    [`${prefix}-line`]: rgba(ink, 0.12),
    [`${prefix}-field`]: rgba(ink, 0.06)
  }
}

/** Si hay color de texto, sobrescribe tinta/cuerpo/tenue (espejo de colors.py). */
export function textTokens(colorText) {
  const rgb = hexToRgb(colorText)
  if (!rgb) return {}
  const ink = rgbToHex(rgb)
  return {
    'color-ink': ink,
    'color-ink-rgb': rgb.join(', '),
    'color-body': rgbToHex(mix(rgb, [255, 255, 255], 0.26)),
    'color-muted': rgbToHex(mix(rgb, [255, 255, 255], 0.48))
  }
}

/** Tokens de las superficies (vacío = automático). */
export function surfaces({ navbar, footer, hero, page, announce } = {}) {
  const out = {
    ...surface('color-navbar', navbar || SURFACE_DEFAULTS['color-navbar']),
    ...surface('color-footer', footer || SURFACE_DEFAULTS['color-footer']),
    ...surface('color-hero', hero || SURFACE_DEFAULTS['color-hero']),
    ...surface('color-announce', announce || SURFACE_DEFAULTS['color-announce'])
  }
  // El fondo general solo se emite si se personaliza (ver colors.py).
  if (page) {
    const pageBg = rgbToHex(hexToRgb(page))
    out['color-page'] = pageBg
    out['color-page-ink'] = inkOn(pageBg)
  }
  return out
}

/** Devuelve el mapa de tokens CSS (mismas claves que main.css) o null si los
 * colores son inválidos. */
export function palette(primary, accent) {
  const p = hexToRgb(primary)
  const a = hexToRgb(accent)
  if (!p || !a) return null
  return {
    'color-primary': rgbToHex(p),
    'color-primary-rgb': p.join(', '),
    'color-primary-dark': darken(primary, 0.18),
    'color-primary-light': lighten(primary, 0.14),
    'color-primary-soft': lighten(primary, 0.9),
    'color-accent': rgbToHex(a),
    'color-accent-rgb': a.join(', '),
    'color-accent-dark': darken(accent, 0.18),
    'color-accent-soft': lighten(accent, 0.88)
  }
}
