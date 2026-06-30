/**
 * Catálogo curado de tipografías para personalizar el ecommerce.
 * `google` es el parámetro `family=…` del API css2 de Google Fonts.
 * `stack` es la pila CSS que se inyecta en --font-sans / --font-display.
 * Inter y Fraunces ya vienen en index.html (no se recargan).
 */
export const FONTS = [
  { key: 'inter', label: 'Inter', kind: 'Sans', stack: "'Inter', system-ui, sans-serif", google: 'Inter:wght@400;500;600;700' },
  { key: 'fraunces', label: 'Fraunces', kind: 'Serif', stack: "'Fraunces', Georgia, serif", google: 'Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700' },
  { key: 'poppins', label: 'Poppins', kind: 'Sans', stack: "'Poppins', system-ui, sans-serif", google: 'Poppins:wght@400;500;600;700' },
  { key: 'montserrat', label: 'Montserrat', kind: 'Sans', stack: "'Montserrat', system-ui, sans-serif", google: 'Montserrat:wght@400;500;600;700' },
  { key: 'dmsans', label: 'DM Sans', kind: 'Sans', stack: "'DM Sans', system-ui, sans-serif", google: 'DM+Sans:wght@400;500;600;700' },
  { key: 'worksans', label: 'Work Sans', kind: 'Sans', stack: "'Work Sans', system-ui, sans-serif", google: 'Work+Sans:wght@400;500;600;700' },
  { key: 'nunito', label: 'Nunito', kind: 'Sans', stack: "'Nunito', system-ui, sans-serif", google: 'Nunito:wght@400;500;600;700' },
  { key: 'spacegrotesk', label: 'Space Grotesk', kind: 'Sans', stack: "'Space Grotesk', system-ui, sans-serif", google: 'Space+Grotesk:wght@400;500;600;700' },
  { key: 'playfair', label: 'Playfair Display', kind: 'Serif', stack: "'Playfair Display', Georgia, serif", google: 'Playfair+Display:wght@400;500;600;700' },
  { key: 'lora', label: 'Lora', kind: 'Serif', stack: "'Lora', Georgia, serif", google: 'Lora:wght@400;500;600;700' },
  { key: 'cormorant', label: 'Cormorant', kind: 'Serif', stack: "'Cormorant', Georgia, serif", google: 'Cormorant:wght@400;500;600;700' },
  { key: 'librebaskerville', label: 'Libre Baskerville', kind: 'Serif', stack: "'Libre Baskerville', Georgia, serif", google: 'Libre+Baskerville:wght@400;700' }
]

export const FONT_MAP = Object.fromEntries(FONTS.map((f) => [f.key, f]))

// Ya cargadas en index.html: no hace falta volver a pedirlas a Google.
const PRELOADED = new Set(['inter', 'fraunces'])

export function fontStack(key, fallback = "'Inter', system-ui, sans-serif") {
  return FONT_MAP[key]?.stack || fallback
}

/**
 * Aplica las fuentes elegidas: inyecta las variables CSS y carga de Google solo
 * las familias no precargadas. Idempotente (reusa un único <link>).
 */
export function applyFonts(headingKey, bodyKey) {
  const heading = FONT_MAP[headingKey] || FONT_MAP.fraunces
  const body = FONT_MAP[bodyKey] || FONT_MAP.inter

  const root = document.documentElement
  root.style.setProperty('--font-display', heading.stack)
  root.style.setProperty('--font-sans', body.stack)

  const families = [...new Set([heading, body].filter((f) => !PRELOADED.has(f.key)).map((f) => f.google))]
  let link = document.getElementById('dynamic-fonts')
  if (!families.length) {
    if (link) link.remove()
    return
  }
  if (!link) {
    link = document.createElement('link')
    link.id = 'dynamic-fonts'
    link.rel = 'stylesheet'
    document.head.appendChild(link)
  }
  link.href = 'https://fonts.googleapis.com/css2?' + families.map((f) => 'family=' + f).join('&') + '&display=swap'
}
