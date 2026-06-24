<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  ArrowLeft,
  ImageOff,
  ShoppingCart,
  Check,
  Minus,
  Plus,
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  Truck,
  ShieldCheck,
  RotateCcw,
  Heart
} from 'lucide-vue-next'
import { storeApi } from '@/services/store'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const wishlist = useWishlistStore()

const product = ref(null)
const loading = ref(true)
const error = ref('')

// Selección de atributos: { [attributeId]: valueId }.
const selection = ref({})
const quantity = ref(1)
const justAdded = ref(false)
const activeImg = ref(0)
const lightboxOpen = ref(false)
const zoomStyle = ref({ transform: 'scale(1)' })

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

const variants = computed(() => product.value?.variants || [])
const attributes = computed(() => product.value?.attributes || [])

// Orden de selección en cascada: el eje de fotos (color) manda primero; los
// demás (talla, almacenamiento…) se filtran según los anteriores. Así elegir un
// color solo deja ver/elegir sus valores disponibles, sin "bailar" entre colores.
const orderedAttributes = computed(() =>
  [...attributes.value].sort((a, b) => (b.is_image_axis === true) - (a.is_image_axis === true))
)

// value_id -> attribute_id
const valueAttr = computed(() => {
  const m = {}
  attributes.value.forEach((a) => a.values.forEach((v) => (m[v.id] = a.id)))
  return m
})

function variantMatches(v, sel) {
  const ids = v.value_ids || []
  const selVals = Object.values(sel)
  return selVals.length === attributes.value.length && selVals.every((vid) => ids.includes(vid))
}

function selectionFromVariant(v) {
  const sel = {}
  ;(v.value_ids || []).forEach((vid) => {
    const aid = valueAttr.value[vid]
    if (aid) sel[aid] = vid
  })
  return sel
}

// La variante seleccionada (o la única, si el producto no tiene atributos).
const selected = computed(() => {
  if (!attributes.value.length) return variants.value[0] || null
  return variants.value.find((v) => variantMatches(v, selection.value)) || null
})

// Un valor está deshabilitado si, respetando la selección de los atributos
// ANTERIORES en la cascada, ninguna variante disponible lo incluye. El primer
// atributo (color) solo se deshabilita si está agotado globalmente; las tallas
// se filtran por el color elegido, etc.
function valueDisabled(attrId, valueId) {
  const order = orderedAttributes.value
  const idx = order.findIndex((a) => a.id === attrId)
  return !variants.value.some((v) => {
    if (!v.available) return false
    const ids = v.value_ids || []
    if (!ids.includes(valueId)) return false
    // Debe respetar la selección de los atributos anteriores en la cascada.
    return order.every((a, i) => i >= idx || ids.includes(selection.value[a.id]))
  })
}
function valueSelected(attrId, valueId) {
  return selection.value[attrId] === valueId
}
function valueLabelFor(attr) {
  const v = attr.values.find((x) => x.id === selection.value[attr.id])
  return v ? v.value : ''
}

function selectValue(attrId, valueId) {
  if (valueDisabled(attrId, valueId)) return
  const order = orderedAttributes.value
  const idx = order.findIndex((a) => a.id === attrId)
  // Valores fijos: los atributos anteriores + el que acabo de tocar.
  const fixed = { [attrId]: valueId }
  order.forEach((a, i) => {
    if (i < idx) fixed[a.id] = selection.value[a.id]
  })
  // Candidatas: variantes disponibles que respetan los valores fijos.
  const candidates = variants.value.filter(
    (v) => v.available && Object.values(fixed).every((vid) => (v.value_ids || []).includes(vid))
  )
  if (!candidates.length) {
    selection.value = { ...selection.value, [attrId]: valueId }
    return
  }
  // Preferir la variante que conserve más de mi selección actual (atributos
  // posteriores), para no cambiar de talla sin necesidad al cambiar de color.
  let best = candidates[0]
  let bestScore = -1
  for (const v of candidates) {
    const ids = v.value_ids || []
    let score = 0
    order.forEach((a, i) => {
      if (i > idx && ids.includes(selection.value[a.id])) score++
    })
    if (score > bestScore) {
      bestScore = score
      best = v
    }
  }
  selection.value = selectionFromVariant(best)
}

const gallery = computed(() => {
  const imgs = selected.value?.images?.length ? selected.value.images : []
  if (imgs.length) return imgs
  const m = selected.value?.main_image || product.value?.main_image
  return m ? [m] : []
})
const cover = computed(() => gallery.value[activeImg.value] || gallery.value[0] || '')

function optsLabel(v) {
  return v.options_label || 'Estándar'
}
const inCart = computed(() => (selected.value ? cart.has(selected.value.id) : false))

// --- Favoritos (por producto + color del eje visual) ---
const imageAxisAttr = computed(() => orderedAttributes.value.find((a) => a.is_image_axis) || null)
const favColorId = computed(() =>
  imageAxisAttr.value ? selection.value[imageAxisAttr.value.id] ?? null : null
)
const isFav = computed(() => (product.value ? wishlist.has(product.value.id, favColorId.value) : false))
function toggleFav() {
  if (!product.value) return
  const colorVal = imageAxisAttr.value
    ? imageAxisAttr.value.values.find((v) => v.id === favColorId.value)
    : null
  wishlist.toggle({
    product_id: product.value.id,
    color_id: favColorId.value,
    slug: product.value.slug,
    name: product.value.name,
    category: product.value.category,
    main_image: cover.value || product.value.main_image,
    hover_image: gallery.value[1] || null,
    is_new: product.value.is_new,
    available: selected.value?.available ?? product.value.available,
    price_min: selected.value?.sale_price ?? product.value.price_min,
    price_max: selected.value?.sale_price ?? product.value.price_max,
    color_label: colorVal?.value ?? null,
    swatch_hex: colorVal?.swatch_hex ?? null
  })
}

// Tope de existencias y cuánto se puede aún agregar (descontando lo que ya está
// en el carrito de esta misma variante).
const maxStock = computed(() => selected.value?.stock ?? 0)
const inCartQty = computed(() => (selected.value ? cart.quantityOf(selected.value.id) : 0))
const maxAddable = computed(() => Math.max(0, maxStock.value - inCartQty.value))

function incQty() {
  if (quantity.value < maxAddable.value) quantity.value++
}
function onQtyInput(e) {
  const v = Math.floor(Number(e.target.value))
  const max = Math.max(1, maxAddable.value)
  quantity.value = Number.isFinite(v) ? Math.min(Math.max(1, v), max) : 1
  e.target.value = quantity.value
}

function addToCart() {
  const v = selected.value
  if (!v || !v.available || maxAddable.value <= 0) return
  cart.add(
    {
      variantId: v.id,
      productSlug: product.value.slug,
      name: product.value.name,
      variantLabel: optsLabel(v),
      price: Number(v.sale_price),
      image: v.main_image || gallery.value[0] || '',
      stock: v.stock
    },
    quantity.value
  )
  justAdded.value = true
  setTimeout(() => (justAdded.value = false), 2000)
}
function buyNow() {
  if (maxAddable.value <= 0) return
  addToCart()
  router.push('/carrito')
}

// --- Zoom al pasar el cursor sobre la imagen principal ---
function onZoomMove(e) {
  const r = e.currentTarget.getBoundingClientRect()
  const x = ((e.clientX - r.left) / r.width) * 100
  const y = ((e.clientY - r.top) / r.height) * 100
  zoomStyle.value = { transformOrigin: `${x}% ${y}%`, transform: 'scale(2)' }
}
function onZoomLeave() {
  zoomStyle.value = { transform: 'scale(1)' }
}

// --- Lightbox (ver en grande) ---
function openLightbox() {
  if (cover.value) lightboxOpen.value = true
}
function closeLightbox() {
  lightboxOpen.value = false
}
function lbPrev() {
  if (!gallery.value.length) return
  activeImg.value = (activeImg.value - 1 + gallery.value.length) % gallery.value.length
}
function lbNext() {
  if (!gallery.value.length) return
  activeImg.value = (activeImg.value + 1) % gallery.value.length
}
function onKey(e) {
  if (!lightboxOpen.value) return
  if (e.key === 'Escape') closeLightbox()
  else if (e.key === 'ArrowLeft') lbPrev()
  else if (e.key === 'ArrowRight') lbNext()
}

// Al cambiar de variante, reinicia imagen y cantidad.
watch(selected, () => {
  activeImg.value = 0
})
watch(selection, () => {
  quantity.value = 1
}, { deep: true })
// Nunca dejar la cantidad por encima de lo que se puede agregar.
watch(maxAddable, (m) => {
  if (quantity.value > m) quantity.value = Math.max(1, m)
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    product.value = await storeApi.product(route.params.slug)
    // Si vienes de una tarjeta de color, preselecciona ese color.
    const colorId = route.query.color ? Number(route.query.color) : null
    let initial = null
    if (colorId) {
      initial =
        variants.value.find((v) => v.available && (v.value_ids || []).includes(colorId)) ||
        variants.value.find((v) => (v.value_ids || []).includes(colorId))
    }
    if (!initial) initial = variants.value.find((v) => v.available) || variants.value[0]
    selection.value = initial ? selectionFromVariant(initial) : {}
    activeImg.value = 0
  } catch (e) {
    error.value =
      e.response?.status === 404
        ? 'Este producto no existe o ya no está disponible.'
        : 'No se pudo cargar el producto.'
  } finally {
    loading.value = false
  }
}

watch(() => route.params.slug, load)
onMounted(() => {
  window.addEventListener('keydown', onKey)
  load()
})
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="container detail">
    <RouterLink :to="{ name: 'catalog' }" class="back"><ArrowLeft :size="16" /> Volver al catálogo</RouterLink>

    <LoadingState v-if="loading" label="Cargando producto…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <div v-else-if="product" class="detail__grid">
      <!-- Galería -->
      <div class="gallery">
        <div
          class="gallery__main"
          :class="{ 'gallery__main--zoomable': cover }"
          @mousemove="onZoomMove"
          @mouseleave="onZoomLeave"
          @click="openLightbox"
        >
          <img v-if="cover" :src="cover" :alt="product.name" :style="zoomStyle" />
          <ImageOff v-else :size="48" />
          <span v-if="cover" class="gallery__hint"><ZoomIn :size="16" /> Pasa el cursor para ampliar</span>
        </div>
        <div v-if="gallery.length > 1" class="gallery__thumbs">
          <button
            v-for="(img, i) in gallery"
            :key="i"
            class="thumb"
            :class="{ active: i === activeImg }"
            @click="activeImg = i"
          >
            <img :src="img" :alt="`${product.name} ${i + 1}`" />
          </button>
        </div>
      </div>

      <!-- Info -->
      <div class="info">
        <div class="info__top">
          <div class="info__heading">
            <span class="info__cat">{{ product.category }}</span>
            <h1 class="info__name">{{ product.name }}</h1>
          </div>
          <button
            type="button"
            class="fav-icon"
            :class="{ 'fav-icon--on': isFav }"
            :aria-label="isFav ? 'Quitar de favoritos' : 'Agregar a favoritos'"
            :aria-pressed="isFav"
            :title="isFav ? 'En favoritos' : 'Agregar a favoritos'"
            @click="toggleFav"
          >
            <Heart :size="20" :fill="isFav ? 'currentColor' : 'none'" />
          </button>
        </div>
        <p v-if="product.brand" class="info__brand">{{ product.brand }}</p>
        <p class="info__price">{{ money(selected?.sale_price ?? product.price_min) }}</p>

        <p v-if="selected && selected.available" class="info__stock"><Check :size="15" /> Disponible</p>
        <p v-else class="info__out">Agotado</p>

        <!-- Atributos (color, talla, almacenamiento, …) -->
        <div v-for="attr in orderedAttributes" :key="attr.id" class="opt-group">
          <div class="opt-group__head">
            <span class="opt-group__label">{{ attr.name }}</span>
            <span class="opt-group__value">{{ valueLabelFor(attr) }}</span>
          </div>

          <!-- Eje visual (color): círculos con tooltip -->
          <div v-if="attr.is_image_axis" class="swatches">
            <button
              v-for="val in attr.values"
              :key="val.id"
              class="swatch"
              :class="{ 'swatch--active': valueSelected(attr.id, val.id), 'swatch--off': valueDisabled(attr.id, val.id) }"
              :disabled="valueDisabled(attr.id, val.id)"
              :title="valueDisabled(attr.id, val.id) ? `${val.value} — agotado` : val.value"
              :aria-label="val.value"
              @click="selectValue(attr.id, val.id)"
            >
              <span class="swatch__dot" :style="{ background: val.swatch_hex || '#cbd5cf' }"></span>
            </button>
          </div>

          <!-- Demás atributos (talla, almacenamiento…): chips de texto -->
          <div v-else class="sizes">
            <button
              v-for="val in attr.values"
              :key="val.id"
              class="size"
              :class="{ 'size--active': valueSelected(attr.id, val.id), 'size--off': valueDisabled(attr.id, val.id) }"
              :disabled="valueDisabled(attr.id, val.id)"
              :title="valueDisabled(attr.id, val.id) ? `${val.value} — no disponible` : val.value"
              @click="selectValue(attr.id, val.id)"
            >
              {{ val.value }}
            </button>
          </div>
        </div>

        <p v-if="product.description" class="info__desc">{{ product.description }}</p>

        <!-- Compra -->
        <template v-if="selected && selected.available">
          <p class="stock-note" :class="{ 'stock-note--low': maxStock <= 5 }">
            <template v-if="maxStock <= 5">¡Solo quedan {{ maxStock }} unidades!</template>
            <template v-else>{{ maxStock }} unidades disponibles</template>
            <span v-if="inCartQty">· ya tienes {{ inCartQty }} en el carrito</span>
          </p>
          <div class="buy">
            <div class="qty" role="group" aria-label="Cantidad">
              <button class="qty__btn" :disabled="quantity <= 1" aria-label="Quitar uno" @click="quantity--">
                <Minus :size="16" />
              </button>
              <input
                class="qty__input"
                type="number"
                min="1"
                :max="maxAddable"
                :value="quantity"
                aria-label="Cantidad"
                @change="onQtyInput"
              />
              <button
                class="qty__btn"
                :disabled="quantity >= maxAddable"
                aria-label="Agregar uno"
                @click="incQty"
              >
                <Plus :size="16" />
              </button>
            </div>
            <div class="buy__actions">
              <button class="btn btn--ghost" :disabled="maxAddable <= 0" @click="addToCart">
                <Check v-if="justAdded" :size="18" />
                <ShoppingCart v-else :size="18" />
                {{ justAdded ? 'Agregado' : inCart ? 'Agregar más' : 'Agregar al carrito' }}
              </button>
              <button class="btn btn--primary" :disabled="maxAddable <= 0" @click="buyNow">
                Comprar ahora
              </button>
            </div>
          </div>
          <p v-if="maxAddable <= 0" class="stock-note stock-note--max">
            Ya tienes todas las unidades disponibles en el carrito.
          </p>
        </template>
        <div v-else class="buy buy--out">
          Esta combinación no está disponible. Prueba con otro color o talla.
        </div>

        <!-- Garantías -->
        <ul class="perks">
          <li><Truck :size="17" /> Envío a todo el país</li>
          <li><ShieldCheck :size="17" /> Pago seguro</li>
          <li><RotateCcw :size="17" /> Cambios fáciles</li>
        </ul>
      </div>
    </div>

    <!-- Lightbox -->
    <transition name="fade">
      <div v-if="lightboxOpen" class="lightbox" @click.self="closeLightbox">
        <button class="lightbox__close" aria-label="Cerrar" @click="closeLightbox"><X :size="22" /></button>
        <button
          v-if="gallery.length > 1"
          class="lightbox__nav lightbox__nav--prev"
          aria-label="Anterior"
          @click="lbPrev"
        >
          <ChevronLeft :size="26" />
        </button>
        <img class="lightbox__img" :src="cover" :alt="product?.name" />
        <button
          v-if="gallery.length > 1"
          class="lightbox__nav lightbox__nav--next"
          aria-label="Siguiente"
          @click="lbNext"
        >
          <ChevronRight :size="26" />
        </button>
        <div v-if="gallery.length > 1" class="lightbox__thumbs">
          <button
            v-for="(img, i) in gallery"
            :key="i"
            :class="{ active: i === activeImg }"
            @click="activeImg = i"
          >
            <img :src="img" :alt="`${product?.name} ${i + 1}`" />
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.detail {
  padding: 28px 0 64px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-bottom: 18px;
}
.back:hover {
  color: var(--color-primary);
}
.detail__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 48px;
  align-items: start;
}

/* ---------------- Galería ---------------- */
.gallery {
  position: sticky;
  top: 130px;
}
.gallery__main {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-surface-alt);
  display: grid;
  place-items: center;
  color: #c7cfc8;
  border: 1px solid var(--color-line);
}
.gallery__main--zoomable {
  cursor: zoom-in;
}
.gallery__main img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.12s ease-out;
}
.gallery__hint {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.76rem;
  font-weight: 500;
  color: var(--color-ink);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  padding: 6px 10px;
  border-radius: var(--radius-full);
  pointer-events: none;
  opacity: 1;
  transition: opacity 0.2s ease;
}
.gallery__main:hover .gallery__hint {
  opacity: 0;
}
.gallery__thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}
.thumb {
  width: 70px;
  height: 70px;
  border-radius: var(--radius-sm);
  border: 2px solid transparent;
  overflow: hidden;
  cursor: pointer;
  background: var(--color-surface-alt);
  transition: border-color 0.15s ease;
}
.thumb:hover {
  border-color: var(--color-line);
}
.thumb.active {
  border-color: var(--color-primary);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ---------------- Info ---------------- */
.info__cat {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  color: var(--color-accent-dark);
}
.info__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 2rem;
  letter-spacing: -0.015em;
  margin: 8px 0 2px;
}
.info__brand {
  color: var(--color-muted);
  font-size: 0.92rem;
  margin-bottom: 12px;
}
.info__price {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--color-ink);
}
.info__stock {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.9rem;
  margin-top: 10px;
}
.info__out {
  color: #dc2626;
  font-weight: 600;
  font-size: 0.9rem;
  margin-top: 10px;
}

.info__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.info__heading {
  min-width: 0;
}
.fav-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  color: var(--color-muted);
  background: #fff;
  border: 1px solid var(--color-line);
  cursor: pointer;
  transition:
    color 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease,
    transform 0.16s ease;
}
.fav-icon:hover {
  color: #e11d48;
  border-color: #f7b9c4;
  transform: scale(1.06);
}
.fav-icon--on {
  color: #e11d48;
  border-color: #f7b9c4;
  background: #fff1f3;
}

/* Selectores */
.opt-group {
  margin-top: 26px;
}
.opt-group__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}
.opt-group__label {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-ink);
}
.opt-group__value {
  font-size: 0.9rem;
  color: var(--color-muted);
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.swatch {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--color-line);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    transform 0.15s ease;
}
.swatch:hover:not(:disabled) {
  transform: scale(1.06);
}
.swatch__dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.swatch--active {
  border-color: var(--color-primary);
}
.swatch--off {
  cursor: not-allowed;
  opacity: 0.45;
}
.swatch--off::after {
  content: '';
  position: absolute;
  inset: 0;
  margin: auto;
  width: 130%;
  height: 1.5px;
  background: #9aa39c;
  transform: rotate(-45deg);
}

.sizes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.size {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 48px;
  padding: 10px 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-ink);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}
.size:hover:not(:disabled) {
  border-color: var(--color-primary);
}
.size--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}
.size--off {
  cursor: not-allowed;
  color: var(--color-muted);
  background: var(--color-surface-alt);
  text-decoration: line-through;
  opacity: 0.7;
}
.size__dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}
.size--active .size__dot {
  border-color: rgba(255, 255, 255, 0.6);
}

.info__desc {
  margin-top: 26px;
  color: var(--color-body);
  white-space: pre-line;
  line-height: 1.75;
}

/* Compra */
.stock-note {
  margin-top: 24px;
  font-size: 0.86rem;
  color: var(--color-muted);
}
.stock-note--low {
  color: var(--color-accent-dark);
  font-weight: 600;
}
.stock-note--max {
  margin-top: 10px;
  color: var(--color-accent-dark);
}
.buy {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.buy--out {
  padding: 14px 16px;
  background: var(--color-surface-alt);
  color: var(--color-muted);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
}
.qty {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.qty__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 42px;
  color: var(--color-ink);
  transition: background 0.15s ease;
}
.qty__btn:hover:not(:disabled) {
  background: var(--color-surface-alt);
}
.qty__btn:disabled {
  color: #cbd5cf;
  cursor: not-allowed;
}
.qty__input {
  width: 52px;
  text-align: center;
  font-family: inherit;
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-ink);
  border: none;
  border-left: 1px solid var(--color-line);
  border-right: 1px solid var(--color-line);
  background: transparent;
  padding: 11px 0;
  -moz-appearance: textfield;
  appearance: textfield;
}
.qty__input:focus {
  outline: none;
  background: var(--color-surface-alt);
}
.qty__input::-webkit-outer-spin-button,
.qty__input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.buy__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1;
}

.perks {
  display: flex;
  flex-wrap: wrap;
  gap: 18px 22px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--color-line);
}
.perks li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.88rem;
  color: var(--color-body);
}
.perks svg {
  color: var(--color-primary);
}

/* ---------------- Lightbox ---------------- */
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(14, 26, 20, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.lightbox__img {
  max-width: min(90vw, 900px);
  max-height: 82vh;
  object-fit: contain;
  border-radius: var(--radius-sm);
}
.lightbox__close {
  position: absolute;
  top: 22px;
  right: 24px;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  transition: background 0.15s ease;
}
.lightbox__close:hover {
  background: rgba(255, 255, 255, 0.24);
}
.lightbox__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  transition: background 0.15s ease;
}
.lightbox__nav:hover {
  background: rgba(255, 255, 255, 0.24);
}
.lightbox__nav--prev {
  left: 24px;
}
.lightbox__nav--next {
  right: 24px;
}
.lightbox__thumbs {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  max-width: 90vw;
  overflow-x: auto;
  padding: 6px;
}
.lightbox__thumbs button {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 2px solid transparent;
  opacity: 0.6;
  cursor: pointer;
  flex-shrink: 0;
  transition:
    opacity 0.15s ease,
    border-color 0.15s ease;
}
.lightbox__thumbs button:hover {
  opacity: 1;
}
.lightbox__thumbs button.active {
  opacity: 1;
  border-color: #fff;
}
.lightbox__thumbs img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (max-width: 880px) {
  .detail__grid {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .gallery {
    position: static;
  }
}
</style>
