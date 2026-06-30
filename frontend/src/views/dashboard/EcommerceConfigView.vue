<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { Upload, Trash2, Plus, Palette, Layers, Type, Store, Phone, Share2, Check, Image as ImageIcon } from 'lucide-vue-next'
import { useConfigStore } from '@/stores/config'
import { geoApi } from '@/services/store'
import { palette, surfaces, textTokens } from '@/utils/palette'
import { FONTS, applyFonts } from '@/utils/fonts'
import { SOCIAL_NETWORKS } from '@/utils/socials'
import { BRAND_ICONS, brandIcon, ANNOUNCE_ICONS } from '@/utils/brandIcons'
import { formatNit } from '@/utils/validators'
import { toastSuccess, toastError } from '@/utils/notify'
import SearchSelect from '@/components/SearchSelect.vue'
import LoadingState from '@/components/LoadingState.vue'

const configStore = useConfigStore()

const loading = ref(true)
const saving = ref(false)
const fieldErrors = ref({})

const form = ref(blank())
const logoFile = ref(null)
const logoPreview = ref('')
const removeLogo = ref(false)
const faviconFile = ref(null)
const faviconPreview = ref('')
const removeFavicon = ref(false)

// Catálogos de ubicación (cascada país→depto→ciudad).
const countries = ref([])
const departments = ref([])
const cities = ref([])
let hydrating = false

function blank() {
  return {
    business_name: '', tagline: '', announce_text: '', announce_icon: 'Truck',
    announce_icon_color: '', announce_animation: 'static', announce_speed: 'normal', icon: '',
    color_primary: '#0e6e4e', color_accent: '#b8923a',
    color_navbar: '', color_footer: '', color_hero: '', color_page: '', color_announce: '',
    color_text: '', font_heading: 'fraunces', font_body: 'inter',
    contact_email: '', contact_phone: '', nit: '',
    contact_address: '', contact_country: null, contact_department: null, contact_city: null,
    socials: [], footer_note: ''
  }
}

function seed(c) {
  form.value = {
    business_name: c.business_name || '',
    tagline: c.tagline || '',
    announce_text: c.announce_text ?? '',
    announce_icon: c.announce_icon || 'Truck',
    announce_icon_color: c.announce_icon_color || '',
    announce_animation: c.announce_animation || 'static',
    announce_speed: c.announce_speed || 'normal',
    icon: c.icon || '',
    color_primary: c.color_primary || '#0e6e4e',
    color_accent: c.color_accent || '#b8923a',
    color_navbar: c.color_navbar || '',
    color_footer: c.color_footer || '',
    color_hero: c.color_hero || '',
    color_page: c.color_page || '',
    color_announce: c.color_announce || '',
    color_text: c.color_text || '',
    font_heading: c.font_heading || 'fraunces',
    font_body: c.font_body || 'inter',
    contact_email: c.contact_email || '',
    contact_phone: c.contact_phone || '',
    nit: c.nit || '',
    contact_address: c.contact_address || '',
    contact_country: c.contact_country || null,
    contact_department: c.contact_department || null,
    contact_city: c.contact_city || null,
    socials: (c.socials || []).map((s) => ({ network: s.network, url: s.url })),
    footer_note: c.footer_note || ''
  }
  logoPreview.value = c.logo || ''
  faviconPreview.value = c.favicon || ''
}

// Opciones para el SearchSelect de redes (con su icono).
const socialOptions = SOCIAL_NETWORKS

// Etiqueta legible de cada fuente (para la vista previa de tipografía).
const FONT_LABELS = Object.fromEntries(FONTS.map((f) => [f.key, f.label]))

// Opciones de comportamiento de la barra de anuncio.
const ANIM_OPTIONS = [
  { value: 'static', label: 'Estática' },
  { value: 'marquee', label: 'Texto deslizante' }
]
const SPEED_OPTIONS = [
  { value: 'slow', label: 'Lenta' },
  { value: 'normal', label: 'Normal' },
  { value: 'fast', label: 'Rápida' }
]

// Vista previa de marca en vivo (refleja el formulario, no el store).
const previewMark = computed(() => brandIcon(form.value.icon))

// ---- Imágenes ----
function onLogoChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  logoFile.value = file
  removeLogo.value = false
  logoPreview.value = URL.createObjectURL(file)
}
function clearLogo() {
  logoFile.value = null
  logoPreview.value = ''
  removeLogo.value = true
}
function onFaviconChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  faviconFile.value = file
  removeFavicon.value = false
  faviconPreview.value = URL.createObjectURL(file)
}
function clearFavicon() {
  faviconFile.value = null
  faviconPreview.value = ''
  removeFavicon.value = true
}

// ---- Icono de marca ----
function pickIcon(key) {
  form.value.icon = form.value.icon === key ? '' : key // re-clic = quitar
}

// ---- NIT ----
function onNitInput(e) {
  form.value.nit = formatNit(e.target.value)
}

// ---- Redes ----
function addSocial() {
  form.value.socials.push({ network: 'instagram', url: '' })
}
function removeSocial(i) {
  form.value.socials.splice(i, 1)
}

// ---- Geo (cascada) ----
async function onCountry(id) {
  form.value.contact_country = id
  if (hydrating) return
  form.value.contact_department = null
  form.value.contact_city = null
  departments.value = id ? await geoApi.departments(id) : []
  cities.value = []
}
async function onDepartment(id) {
  form.value.contact_department = id
  if (hydrating) return
  form.value.contact_city = null
  cities.value = id ? await geoApi.cities(id) : []
}

// ---- Superficies ----
// Cada superficie ofrece "Automático" + atajos a la paleta de marca + color libre.
const SURFACES = [
  { key: 'color_announce', label: 'Barra de anuncio', hint: 'Franja superior del sitio' },
  { key: 'color_navbar', label: 'Barra de navegación', hint: 'Cabecera del ecommerce' },
  { key: 'color_hero', label: 'Hero / cabeceras', hint: 'Encabezado de las páginas' },
  { key: 'color_footer', label: 'Pie de página', hint: 'Footer del ecommerce' },
  { key: 'color_page', label: 'Fondo de página', hint: 'Base del sitio y del panel' }
]
// Atajos de marca disponibles como muestras rápidas.
const swatches = computed(() => [
  { value: form.value.color_primary, label: 'Primario' },
  { value: form.value.color_accent, label: 'Acento' },
  { value: '#0e1a14', label: 'Tinta' },
  { value: '#faf7f0', label: 'Crema' },
  { value: '#ffffff', label: 'Blanco' }
])
function setSurface(key, value) {
  form.value[key] = value
}

// ---- Vista previa de colores en vivo ----
const previewTokens = computed(() => {
  const base = palette(form.value.color_primary, form.value.color_accent)
  if (!base) return null
  return {
    ...base,
    ...surfaces({
      navbar: form.value.color_navbar,
      footer: form.value.color_footer,
      hero: form.value.color_hero,
      page: form.value.color_page,
      announce: form.value.color_announce
    }),
    ...textTokens(form.value.color_text)
  }
})
watch(previewTokens, (tokens) => configStore.applyTheme(tokens))

// Vista previa de tipografía en vivo.
watch(
  () => [form.value.font_heading, form.value.font_body],
  ([h, b]) => applyFonts(h, b)
)

// Fondo + tinta resueltos de una superficie, para su mini-vista previa.
function surfaceToken(formKey) {
  const prefix = formKey.replace('_', '-') // color_navbar -> color-navbar
  const t = previewTokens.value || {}
  // El fondo de página en automático no emite token: muestra blanco de muestra.
  const bg = t[prefix] || (prefix === 'color-page' ? '#ffffff' : undefined)
  return { bg, ink: t[`${prefix}-ink`] || t['color-ink'] || '#14201a' }
}

function buildPayload() {
  const f = form.value
  const base = {
    business_name: f.business_name, tagline: f.tagline,
    announce_text: f.announce_text, announce_icon: f.announce_icon,
    announce_icon_color: f.announce_icon_color, announce_animation: f.announce_animation,
    announce_speed: f.announce_speed, icon: f.icon,
    color_primary: f.color_primary, color_accent: f.color_accent,
    color_navbar: f.color_navbar, color_footer: f.color_footer,
    color_hero: f.color_hero, color_page: f.color_page, color_announce: f.color_announce,
    color_text: f.color_text, font_heading: f.font_heading, font_body: f.font_body,
    contact_email: f.contact_email, contact_phone: f.contact_phone, nit: f.nit,
    contact_address: f.contact_address, contact_city: f.contact_city,
    socials: f.socials, footer_note: f.footer_note
  }
  if (logoFile.value || faviconFile.value) {
    const fd = new FormData()
    Object.entries(base).forEach(([k, v]) => {
      if (k === 'socials') fd.append(k, JSON.stringify(v))
      else if (v === null || v === undefined) return // FK nula: no se envía
      else fd.append(k, v)
    })
    if (logoFile.value) fd.append('logo', logoFile.value)
    if (faviconFile.value) fd.append('favicon', faviconFile.value)
    return fd
  }
  if (removeLogo.value) base.logo = null
  if (removeFavicon.value) base.favicon = null
  return base
}

async function save() {
  saving.value = true
  fieldErrors.value = {}
  try {
    await configStore.save(buildPayload())
    logoFile.value = null
    removeLogo.value = false
    faviconFile.value = null
    removeFavicon.value = false
    // Re-sincroniza el form con lo normalizado por el backend (NIT, etc.).
    seed(configStore.config)
    toastSuccess('Configuración guardada')
  } catch (e) {
    const data = e.response?.data
    if (data && typeof data === 'object') fieldErrors.value = data
    toastError(data?.detail || 'No se pudo guardar la configuración.')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!configStore.config) await configStore.load()
  if (configStore.config) seed(configStore.config)
  try {
    countries.value = await geoApi.countries()
    // Precarga el cascadeo si ya hay ubicación.
    if (form.value.contact_country) {
      hydrating = true
      departments.value = await geoApi.departments(form.value.contact_country)
      if (form.value.contact_department) cities.value = await geoApi.cities(form.value.contact_department)
      hydrating = false
    }
  } catch {
    /* sin geo, los selects quedan vacíos */
  }
  loading.value = false
})

onBeforeUnmount(() => {
  // Si se sale sin guardar, revierte la vista previa (colores y fuentes).
  const c = configStore.config
  if (c?.tokens) configStore.applyTheme(c.tokens)
  if (c) applyFonts(c.font_heading, c.font_body)
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Personalización</h1>
        <p class="page__subtitle">
          Identidad, marca y contacto de tu tienda. Los cambios de color se ven en vivo en todo el panel.
        </p>
      </div>
    </header>

    <LoadingState v-if="loading" label="Cargando configuración…" />

    <form v-else class="grid" @submit.prevent="save">
      <!-- Identidad -->
      <section class="card-box span-2">
        <h2 class="card-box__title"><Store :size="18" /> Identidad</h2>

        <div class="identity">
          <!-- Logo + favicon -->
          <div class="identity__media">
            <div class="upload">
              <span class="field__label">Logo</span>
              <div class="upload__row">
                <div class="upload__preview" :class="{ 'upload__preview--empty': !logoPreview }">
                  <img v-if="logoPreview" :src="logoPreview" alt="Logo" />
                  <ImageIcon v-else :size="22" />
                </div>
                <div class="upload__actions">
                  <label class="btn btn--ghost btn--sm">
                    <Upload :size="15" /> {{ logoPreview ? 'Cambiar' : 'Subir' }}
                    <input type="file" accept=".png,.jpg,.jpeg,.webp,.svg,.gif,image/*" hidden @change="onLogoChange" />
                  </label>
                  <button v-if="logoPreview" type="button" class="btn btn--ghost btn--sm" @click="clearLogo">
                    <Trash2 :size="15" /> Quitar
                  </button>
                </div>
              </div>
              <p class="field__hint">Reemplaza al nombre en navbar y footer. PNG o SVG con fondo transparente.</p>
            </div>

            <div class="upload">
              <span class="field__label">Favicon</span>
              <div class="upload__row">
                <div class="upload__preview upload__preview--ico" :class="{ 'upload__preview--empty': !faviconPreview }">
                  <img v-if="faviconPreview" :src="faviconPreview" alt="Favicon" />
                  <span v-else>—</span>
                </div>
                <div class="upload__actions">
                  <label class="btn btn--ghost btn--sm">
                    <Upload :size="15" /> {{ faviconPreview ? 'Cambiar' : 'Subir' }}
                    <input type="file" accept=".png,.svg,.ico,.jpg,.jpeg,.webp,image/*" hidden @change="onFaviconChange" />
                  </label>
                  <button v-if="faviconPreview" type="button" class="btn btn--ghost btn--sm" @click="clearFavicon">
                    <Trash2 :size="15" /> Quitar
                  </button>
                </div>
              </div>
              <p class="field__hint">Icono de la pestaña del navegador. Cuadrado (PNG/ICO/SVG).</p>
            </div>
          </div>

          <!-- Nombre + vista previa -->
          <div class="identity__fields">
            <label class="field">
              <span class="field__label">Nombre del negocio</span>
              <input v-model="form.business_name" class="field__input" maxlength="80" placeholder="Mi Tienda" />
              <span v-if="fieldErrors.business_name" class="field__error">{{ fieldErrors.business_name[0] }}</span>
            </label>
            <label class="field">
              <span class="field__label">Eslogan</span>
              <input v-model="form.tagline" class="field__input" maxlength="180" placeholder="Una frase corta de tu negocio" />
            </label>
            <div class="field">
              <span class="field__label">Barra de anuncio <span class="field__hint-inline">(franja superior; vacío = oculta)</span></span>
              <input v-model="form.announce_text" class="field__input" maxlength="160" placeholder="Envío a todo el país · Atención de lunes a sábado" />
              <template v-if="form.announce_text">
                <div class="announceicons">
                  <button
                    v-for="ic in ANNOUNCE_ICONS"
                    :key="ic.key"
                    type="button"
                    class="announceicons__item"
                    :class="{ 'announceicons__item--active': form.announce_icon === ic.key }"
                    :title="ic.key"
                    @click="form.announce_icon = ic.key"
                  >
                    <component :is="ic.icon" :size="16" />
                  </button>
                </div>

                <div class="announce-opts">
                  <div class="announce-opts__col">
                    <span class="field__label field__label--sm">Color del icono</span>
                    <div class="textcolor">
                      <button
                        type="button"
                        class="surface__auto"
                        :class="{ 'surface__auto--active': !form.announce_icon_color }"
                        @click="form.announce_icon_color = ''"
                      >
                        Auto
                      </button>
                      <input :value="form.announce_icon_color || '#b8923a'" type="color" class="color__swatch" @input="form.announce_icon_color = $event.target.value" />
                    </div>
                  </div>
                  <div class="announce-opts__col">
                    <span class="field__label field__label--sm">Comportamiento</span>
                    <SearchSelect v-model="form.announce_animation" :options="ANIM_OPTIONS" value-key="value" label-key="label" placeholder="Comportamiento" />
                  </div>
                  <div v-if="form.announce_animation === 'marquee'" class="announce-opts__col">
                    <span class="field__label field__label--sm">Velocidad</span>
                    <SearchSelect v-model="form.announce_speed" :options="SPEED_OPTIONS" value-key="value" label-key="label" placeholder="Velocidad" />
                  </div>
                </div>
              </template>
            </div>
            <div class="brand-preview">
              <span class="field__label">Vista previa de la marca</span>
              <div class="brand-preview__box">
                <span v-if="logoPreview" class="bp__logo"><img :src="logoPreview" :alt="form.business_name" /></span>
                <span v-else class="bp">
                  <span class="bp__mark" :class="{ 'bp__mark--img': !previewMark && faviconPreview }">
                    <component :is="previewMark" v-if="previewMark" :size="20" />
                    <img v-else-if="faviconPreview" :src="faviconPreview" alt="" class="bp__mark-img" />
                    <svg v-else viewBox="0 0 32 32" width="20" height="20">
                      <path d="M16 4 L27 9.7 V22.3 L16 28 L5 22.3 V9.7 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
                      <path d="M5 9.7 L16 15.4 L27 9.7 M16 15.4 V28" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
                    </svg>
                  </span>
                  <span class="bp__name">{{ form.business_name || 'Mi Tienda' }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Icono de marca: relevante mientras falte el logo o el favicon -->
        <div v-if="!logoPreview || !faviconPreview" class="iconpick">
          <span class="field__label">Icono de marca <span class="field__hint-inline">(se usa como favicon cuando no subes uno, y junto al nombre cuando no hay logo)</span></span>
          <div class="iconpick__grid">
            <button
              v-for="ic in BRAND_ICONS"
              :key="ic.key"
              type="button"
              class="iconpick__item"
              :class="{ 'iconpick__item--active': form.icon === ic.key }"
              :title="ic.key"
              @click="pickIcon(ic.key)"
            >
              <component :is="ic.icon" :size="20" />
            </button>
          </div>
        </div>
      </section>

      <!-- Marca (colores) -->
      <section class="card-box">
        <h2 class="card-box__title"><Palette :size="18" /> Colores de marca</h2>
        <p class="card-box__hint">Elige 2 colores; el resto de la paleta se deriva.</p>

        <div class="field-row">
          <div class="field">
            <span class="field__label">Primario</span>
            <div class="color">
              <input v-model="form.color_primary" type="color" class="color__swatch" />
              <input v-model="form.color_primary" class="field__input color__hex" maxlength="7" />
            </div>
            <span v-if="fieldErrors.color_primary" class="field__error">{{ fieldErrors.color_primary[0] }}</span>
          </div>
          <div class="field">
            <span class="field__label">Acento</span>
            <div class="color">
              <input v-model="form.color_accent" type="color" class="color__swatch" />
              <input v-model="form.color_accent" class="field__input color__hex" maxlength="7" />
            </div>
            <span v-if="fieldErrors.color_accent" class="field__error">{{ fieldErrors.color_accent[0] }}</span>
          </div>
        </div>

        <div class="preview">
          <span class="preview__label">Vista previa</span>
          <div class="preview__row">
            <button type="button" class="btn btn--primary btn--sm">Primario</button>
            <button type="button" class="btn btn--accent btn--sm">Acento</button>
            <span class="preview__chip">Etiqueta</span>
            <a class="preview__link" href="#" @click.prevent>Enlace</a>
          </div>
        </div>
      </section>

      <!-- Contacto -->
      <section class="card-box">
        <h2 class="card-box__title"><Phone :size="18" /> Contacto</h2>
        <p class="card-box__hint">Se muestra en el footer y en los recibos por correo.</p>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Correo</span>
            <input v-model="form.contact_email" type="email" class="field__input" placeholder="hola@mitienda.com" />
            <span v-if="fieldErrors.contact_email" class="field__error">{{ fieldErrors.contact_email[0] }}</span>
          </label>
          <label class="field">
            <span class="field__label">Teléfono</span>
            <input v-model="form.contact_phone" class="field__input" placeholder="+57 300 123 4567" />
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">NIT</span>
            <input :value="form.nit" class="field__input" inputmode="numeric" placeholder="900.123.456-7" @input="onNitInput" />
          </label>
          <label class="field">
            <span class="field__label">Dirección (calle)</span>
            <input v-model="form.contact_address" class="field__input" maxlength="200" placeholder="Cra 00 #00-00, Barrio" />
          </label>
        </div>

        <div class="field-row field-row--3">
          <div class="field">
            <span class="field__label">País</span>
            <SearchSelect :model-value="form.contact_country" :options="countries" value-key="id" label-key="name" placeholder="País" clearable clear-label="Sin país" @update:model-value="onCountry" />
          </div>
          <div class="field">
            <span class="field__label">Departamento</span>
            <SearchSelect :model-value="form.contact_department" :options="departments" value-key="id" label-key="name" placeholder="Departamento" :disabled="!form.contact_country" @update:model-value="onDepartment" />
          </div>
          <div class="field">
            <span class="field__label">Ciudad</span>
            <SearchSelect v-model="form.contact_city" :options="cities" value-key="id" label-key="name" placeholder="Ciudad" :disabled="!form.contact_department" />
          </div>
        </div>
      </section>

      <!-- Colores por superficie -->
      <section class="card-box span-2">
        <h2 class="card-box__title"><Layers :size="18" /> Colores por superficie</h2>
        <p class="card-box__hint">
          Opcional. Deja <strong>Automático</strong> para usar el tono por defecto. El color del texto se ajusta solo por contraste.
        </p>

        <div class="surfaces">
          <div v-for="s in SURFACES" :key="s.key" class="surface">
            <span
              class="surface__preview"
              :style="{ background: surfaceToken(s.key).bg, color: surfaceToken(s.key).ink }"
            >Aa</span>

            <div class="surface__info">
              <span class="surface__label">{{ s.label }}</span>
              <span class="surface__hint">{{ s.hint }}</span>
            </div>

            <div class="surface__controls">
              <button
                type="button"
                class="surface__auto"
                :class="{ 'surface__auto--active': !form[s.key] }"
                @click="setSurface(s.key, '')"
              >
                Automático
              </button>
              <span class="surface__sws">
                <button
                  v-for="sw in swatches"
                  :key="sw.label"
                  type="button"
                  class="surface__sw"
                  :class="{ 'surface__sw--active': (form[s.key] || '').toLowerCase() === sw.value.toLowerCase() }"
                  :style="{ background: sw.value }"
                  :title="sw.label"
                  @click="setSurface(s.key, sw.value)"
                ></button>
              </span>
              <span class="surface__free">
                <input
                  :value="form[s.key] || '#ffffff'"
                  type="color"
                  class="color__swatch"
                  @input="setSurface(s.key, $event.target.value)"
                />
                <input
                  :value="form[s.key]"
                  class="field__input color__hex"
                  maxlength="7"
                  placeholder="auto"
                  @input="setSurface(s.key, $event.target.value)"
                />
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Tipografía y color de texto -->
      <section class="card-box span-2">
        <h2 class="card-box__title"><Type :size="18" /> Tipografía y texto</h2>
        <p class="card-box__hint">Elige las fuentes del ecommerce y el color del texto. La vista previa usa las fuentes elegidas.</p>

        <div class="field-row field-row--3">
          <div class="field">
            <span class="field__label">Fuente de titulares</span>
            <SearchSelect v-model="form.font_heading" :options="FONTS" value-key="key" label-key="label" placeholder="Fuente" />
          </div>
          <div class="field">
            <span class="field__label">Fuente del cuerpo</span>
            <SearchSelect v-model="form.font_body" :options="FONTS" value-key="key" label-key="label" placeholder="Fuente" />
          </div>
          <div class="field">
            <span class="field__label">Color del texto</span>
            <div class="textcolor">
              <button
                type="button"
                class="surface__auto"
                :class="{ 'surface__auto--active': !form.color_text }"
                @click="form.color_text = ''"
              >
                Automático
              </button>
              <input :value="form.color_text || '#14201a'" type="color" class="color__swatch" @input="form.color_text = $event.target.value" />
              <input v-model="form.color_text" class="field__input color__hex" maxlength="7" placeholder="auto" />
            </div>
          </div>
        </div>

        <div class="type-preview">
          <span class="preview__label">Vista previa</span>
          <h3 class="type-preview__title">Titulares con {{ FONT_LABELS[form.font_heading] }}</h3>
          <p class="type-preview__body">
            El cuerpo de texto usa {{ FONT_LABELS[form.font_body] }}. Así se verán los párrafos, descripciones y textos del ecommerce con el color elegido.
          </p>
        </div>
      </section>

      <!-- Redes y pie -->
      <section class="card-box span-2">
        <h2 class="card-box__title"><Share2 :size="18" /> Redes sociales y pie</h2>
        <p class="card-box__hint">Agrega solo las redes que tengas. Aparecen en el footer con su icono.</p>

        <div class="socials">
          <div v-for="(s, i) in form.socials" :key="i" class="social-row">
            <div class="social-row__net">
              <SearchSelect v-model="s.network" :options="socialOptions" value-key="key" label-key="label" icon-key="icon" placeholder="Red" />
            </div>
            <input v-model="s.url" class="field__input social-row__url" placeholder="https://…" />
            <button type="button" class="icon-btn" title="Quitar" @click="removeSocial(i)">
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
        <span v-if="fieldErrors.socials" class="field__error">{{ fieldErrors.socials[0] }}</span>
        <button type="button" class="add-social" @click="addSocial">
          <Plus :size="15" /> Agregar red
        </button>

        <label class="field">
          <span class="field__label">Nota del pie de página</span>
          <input v-model="form.footer_note" class="field__input" maxlength="200" placeholder="Todos los derechos reservados." />
        </label>
      </section>

      <div class="form-actions">
        <button type="submit" class="btn btn--primary" :disabled="saving">
          <Check :size="18" /> {{ saving ? 'Guardando…' : 'Guardar cambios' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.page__head {
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
  max-width: 600px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: start;
}
.span-2 {
  grid-column: 1 / -1;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-box__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
}
.card-box__title svg {
  color: var(--color-primary);
}
.card-box__hint {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-top: -8px;
}

/* Campos */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
}
.field__hint-inline {
  font-weight: 400;
  color: var(--color-muted);
}
.field__input {
  width: 100%;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field__hint {
  font-size: 0.8rem;
  color: var(--color-muted);
}
.field__error {
  font-size: 0.8rem;
  color: #dc2626;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field-row--3 {
  grid-template-columns: 1fr 1fr 1fr;
}

/* Identidad */
.identity {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 22px;
}
.identity__media {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.identity__fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.upload {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.upload__row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.upload__preview {
  width: 130px;
  height: 64px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-line);
  background: var(--color-surface-alt);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-muted);
}
.upload__preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.upload__preview--ico {
  width: 64px;
}
.upload__preview--empty {
  color: var(--color-muted);
  font-size: 0.82rem;
}
.upload__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.brand-preview {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: auto;
}
.brand-preview__box {
  display: flex;
  align-items: center;
  min-height: 64px;
  padding: 12px 16px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}
.bp {
  display: inline-flex;
  align-items: center;
  gap: 11px;
}
.bp__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: var(--color-primary);
  color: #fff;
  flex-shrink: 0;
  overflow: hidden;
}
.bp__mark--img {
  background: #fff;
  box-shadow: inset 0 0 0 1px var(--color-line);
}
.bp__mark-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 3px;
}
.bp__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.32rem;
  letter-spacing: -0.02em;
  color: var(--color-ink);
}
.bp__logo img {
  height: 44px;
  width: auto;
  max-width: 200px;
  object-fit: contain;
}

/* Selector de icono */
.iconpick {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid var(--color-line);
  padding-top: 16px;
}
.iconpick__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(46px, 1fr));
  gap: 8px;
}
.iconpick__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 46px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-body);
  background: #fff;
  cursor: pointer;
  transition: all 0.14s ease;
}
.iconpick__item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.iconpick__item--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}

/* Color */
.color {
  display: flex;
  align-items: center;
  gap: 10px;
}
.color__swatch {
  width: 46px;
  height: 42px;
  padding: 0;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: none;
  cursor: pointer;
}
.color__hex {
  flex: 1;
  text-transform: lowercase;
}

/* Colores por superficie — lista de filas tipo "ajuste" */
.surfaces {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.surface {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}
.surface__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.surface__label {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--color-ink);
}
.surface__hint {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.surface__preview {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.05rem;
  flex-shrink: 0;
}
.surface__controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.surface__auto {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-line);
  background: var(--color-surface);
  color: var(--color-muted);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    color 0.15s ease,
    background 0.15s ease;
}
.surface__auto--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.surface__sws {
  display: inline-flex;
  gap: 5px;
}
.surface__sw {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid var(--color-line);
  cursor: pointer;
  padding: 0;
  transition: transform 0.12s ease;
}
.surface__sw:hover {
  transform: scale(1.12);
}
.surface__sw--active {
  box-shadow: 0 0 0 2px var(--color-surface), 0 0 0 4px var(--color-primary);
}
.surface__free {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.surface__free .color__swatch {
  width: 38px;
  height: 38px;
}
.surface__free .color__hex {
  width: 90px;
  flex: none;
}

@media (max-width: 760px) {
  .surfaces {
    grid-template-columns: 1fr;
  }
  .surface {
    flex-wrap: wrap;
  }
}

/* Selector de icono de la barra de anuncio */
.announceicons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.announceicons__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: var(--color-surface);
  color: var(--color-muted);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    color 0.15s ease,
    background 0.15s ease;
}
.announceicons__item:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.announceicons__item--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.announce-opts {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 12px;
}
.announce-opts__col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 150px;
  flex: 1;
}
.field__label--sm {
  font-size: 0.78rem;
}

/* Tipografía y color de texto */
.textcolor {
  display: flex;
  align-items: center;
  gap: 8px;
}
.textcolor .color__hex {
  flex: 1;
  min-width: 0;
}
.type-preview {
  margin-top: 4px;
  padding: 18px 20px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}
.type-preview__title {
  font-family: var(--font-display);
  color: var(--color-ink);
  font-size: 1.5rem;
  font-weight: 600;
  margin: 6px 0 8px;
}
.type-preview__body {
  font-family: var(--font-sans);
  color: var(--color-body);
  font-size: 0.96rem;
  line-height: 1.6;
  max-width: 640px;
}

/* Vista previa de colores */
.preview {
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
  padding: 14px;
  background: var(--color-surface-alt);
  margin-top: auto;
}
.preview__label {
  display: block;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted);
  margin-bottom: 10px;
}
.preview__row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.preview__chip {
  font-size: 0.74rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.preview__link {
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.9rem;
}
.preview__link:hover {
  text-decoration: underline;
}

/* Redes */
.socials {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.social-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.social-row__net {
  width: 200px;
  flex-shrink: 0;
}
.social-row__url {
  flex: 1;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  border: 1px solid var(--color-line);
  background: #fff;
  transition: all 0.16s ease;
}
.icon-btn:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}
.add-social {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  align-self: flex-start;
  padding: 9px 14px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-primary);
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.add-social:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.form-actions {
  grid-column: 1 / -1;
  position: sticky;
  bottom: 18px;
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}
/* Solo el botón flota y es interactivo; nada de barra blanca de fondo. */
.form-actions .btn {
  pointer-events: auto;
  box-shadow: var(--shadow-lg);
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .identity {
    grid-template-columns: 1fr;
  }
  .field-row--3 {
    grid-template-columns: 1fr;
  }
}
</style>
