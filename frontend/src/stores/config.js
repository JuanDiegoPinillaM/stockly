import { defineStore } from 'pinia'
import { ref, h, render } from 'vue'
import { configApi } from '@/services/config'
import { brandIcon } from '@/utils/brandIcons'
import { applyFonts } from '@/utils/fonts'

// Genera un favicon (data URI SVG) a partir de un icono lucide: recuadro
// redondeado con el color primario y el icono en blanco, igual que la marca.
function iconFavicon(iconComp, color) {
  const box = document.createElement('div')
  render(h(iconComp, { size: 24 }), box)
  const inner = box.querySelector('svg')?.innerHTML || ''
  render(null, box)
  if (!inner) return ''
  // El icono lucide vive en una caja de 24×24. Lo escalo a 18 (scale .75) y lo
  // centro en los 32: margen (32-18)/2 = 7 → translate(7 7).
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">` +
    `<rect width="32" height="32" rx="7" fill="${color}"/>` +
    `<g transform="translate(7 7) scale(0.75)" fill="none" stroke="#fff" ` +
    `stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">${inner}</g></svg>`
  return 'data:image/svg+xml,' + encodeURIComponent(svg)
}

/**
 * Configuración del ecommerce cargada en runtime. Aplica la paleta de marca
 * inyectando las variables CSS en :root, de modo que TODO el diseño (que usa
 * esas variables) cambie al instante. También expone identidad y contacto para
 * el logo, el footer, etc.
 */
export const useConfigStore = defineStore('config', () => {
  const config = ref(null)
  const loaded = ref(false)
  // Etiqueta de la página actual (la actualiza el router en cada navegación);
  // el título de la pestaña se compone como "Nombre del negocio — Etiqueta".
  const routeLabel = ref('')

  // Compone y aplica el título de la pestaña con el nombre actual + la página.
  function applyTitle() {
    const name = config.value?.business_name || 'Stockly'
    document.title = routeLabel.value ? `${name} — ${routeLabel.value}` : name
  }

  // La llama el router en afterEach con la etiqueta de la ruta.
  function setRouteTitle(label) {
    routeLabel.value = label || ''
    applyTitle()
  }

  // Inyecta los tokens de color como variables CSS en el documento.
  function applyTheme(tokens) {
    if (!tokens) return
    const root = document.documentElement
    for (const [key, value] of Object.entries(tokens)) {
      root.style.setProperty(`--${key}`, value)
    }
  }

  // Cambia el icono de la pestaña del navegador (favicon). Sin url vuelve al
  // favicon de fábrica del index.html.
  function applyFavicon(url) {
    let link = document.querySelector("link[rel~='icon']")
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    // Quita el type fijo del index.html para que el navegador infiera el formato
    // del archivo subido (PNG/ICO/SVG) o del data URI generado.
    link.removeAttribute('type')
    link.href = url || '/favicon.svg'
    // Recuerda el favicon resuelto para pintarlo de inmediato en el próximo
    // arranque (evita el parpadeo del favicon anterior mientras carga la config).
    try {
      localStorage.setItem('faviconCache', url || '')
    } catch {
      /* almacenamiento no disponible: no pasa nada */
    }
  }

  // Resuelve qué favicon poner en la pestaña, por precedencia:
  // 1) favicon subido  2) el icono de marca elegido (generado en color primario)
  // 3) el de fábrica. El icono se usa SOLO si no hay favicon cargado.
  function resolveFavicon(data) {
    if (data?.favicon) return data.favicon
    const comp = brandIcon(data?.icon)
    if (comp) return iconFavicon(comp, data?.color_primary || '#0e6e4e')
    return ''
  }

  function set(data) {
    config.value = data
    applyTheme(data?.tokens)
    applyFonts(data?.font_heading, data?.font_body)
    applyFavicon(resolveFavicon(data))
    // Recompone el título completo (nombre nuevo + la página en que estamos),
    // así al guardar no se pierde el "— Personalización".
    applyTitle()
  }

  // Al arrancar, pinta de inmediato el favicon recordado (si lo hay) para que la
  // pestaña no muestre el icono anterior mientras llega la config del servidor.
  try {
    const cached = localStorage.getItem('faviconCache')
    if (cached) applyFavicon(cached)
  } catch {
    /* almacenamiento no disponible */
  }

  async function load() {
    try {
      set(await configApi.get())
    } catch {
      /* sin config el sitio usa los valores de fábrica de main.css */
    } finally {
      loaded.value = true
    }
  }

  async function save(payload) {
    set(await configApi.update(payload))
    return config.value
  }

  return { config, loaded, load, save, applyTheme, setRouteTitle }
})
