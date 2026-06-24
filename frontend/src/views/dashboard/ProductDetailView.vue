<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, Pencil, ImageOff, AlertTriangle } from 'lucide-vue-next'
import { productsApi } from '@/services/catalog'
import { useAuthStore } from '@/stores/auth'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)

const product = ref(null)
const activeImage = ref('')
const selectedVariantId = ref(null)
const loading = ref(true)
const error = ref('')

function money(value) {
  if (value == null) return '—'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(value)
}

const priceLabel = computed(() => {
  const p = product.value
  if (!p || p.price_min == null) return '—'
  if (p.price_min === p.price_max) return money(p.price_min)
  return `${money(p.price_min)} – ${money(p.price_max)}`
})

// Solo variantes activas, igual que en el catálogo.
const variants = computed(() => (product.value?.variants || []).filter((v) => v.is_active))
const attributes = computed(() => product.value?.attributes || [])

// Atributo que manda las fotos (el "eje visual", normalmente el color).
const imageAxisAttrId = computed(
  () => attributes.value.find((a) => a.is_image_axis)?.id ?? null
)

function visualValueId(v) {
  if (!v || imageAxisAttrId.value == null) return null
  const found = (v.values || []).find((x) => x.attribute === imageAxisAttrId.value)
  return found ? found.value : null
}

const selectedVariant = computed(
  () => variants.value.find((v) => v.id === selectedVariantId.value) || variants.value[0] || null
)

// Galería del producto filtrada por el valor visual de la variante elegida.
const galleryImages = computed(() => {
  const all = product.value?.images || []
  const vid = visualValueId(selectedVariant.value)
  if (vid != null) {
    const grouped = all.filter((im) => im.value === vid)
    if (grouped.length) return grouped
  }
  const general = all.filter((im) => im.value == null)
  return general.length ? general : all
})

function variantAttrs(v) {
  return v.options_label || '—'
}
function variantDot(v) {
  const found = (v.values || []).find((x) => x.attribute === imageAxisAttrId.value)
  return found?.swatch_hex || ''
}

function selectVariant(v) {
  selectedVariantId.value = v.id
}

// La imagen grande sigue a la galería de la variante seleccionada.
watch(galleryImages, (imgs) => {
  activeImage.value = imgs[0]?.image || product.value?.main_image || ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await productsApi.get(route.params.id)
    product.value = data
    const first = (data.variants || []).find((v) => v.is_active)
    selectedVariantId.value = first?.id ?? null
    activeImage.value = data.main_image || ''
  } catch {
    error.value = 'No se pudo cargar el producto.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'products' }" class="back">
      <ArrowLeft :size="16" /> Volver a productos
    </RouterLink>

    <LoadingState v-if="loading" label="Cargando producto…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="product">
      <header class="page__head">
        <div>
          <div class="title-row">
            <h1 class="page__title">{{ product.name }}</h1>
            <span class="badge" :class="product.is_active ? 'badge--on' : 'badge--off'">
              {{ product.is_active ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <p class="page__subtitle">{{ product.category_name }} › {{ product.subcategory_name }}</p>
        </div>
        <RouterLink
          v-if="isAdmin"
          :to="{ name: 'product-edit', params: { id: product.id } }"
          class="btn btn--primary"
        >
          <Pencil :size="16" /> Editar
        </RouterLink>
      </header>

      <div class="layout">
        <!-- Galería de la variante seleccionada -->
        <section class="card-box gallery-box">
          <p v-if="selectedVariant" class="gallery__label">
            Fotos de: <strong>{{ variantAttrs(selectedVariant) }}</strong>
          </p>
          <div class="gallery__main">
            <img v-if="activeImage" :src="activeImage" :alt="product.name" />
            <ImageOff v-else :size="40" />
          </div>
          <div v-if="galleryImages.length > 1" class="gallery__thumbs">
            <button
              v-for="img in galleryImages"
              :key="img.id"
              type="button"
              class="gallery__thumb"
              :class="{ active: activeImage === img.image }"
              @click="activeImage = img.image"
            >
              <img :src="img.image" :alt="img.alt_text" />
            </button>
          </div>
        </section>

        <!-- Datos -->
        <section class="info">
          <div class="card-box">
            <h2 class="card-box__title">Datos del producto</h2>
            <dl class="data">
              <div><dt>Marca</dt><dd>{{ product.brand_detail?.name || '—' }}</dd></div>
              <div><dt>Unidad de medida</dt><dd>{{ product.unit_of_measure_display }}</dd></div>
              <div><dt>IVA</dt><dd>{{ product.tax_rate_display }}</dd></div>
              <div><dt>Vencimiento</dt><dd>{{ product.expiration_date || 'No perecedero' }}</dd></div>
              <div><dt>Precio de venta</dt><dd>{{ priceLabel }}</dd></div>
              <div>
                <dt>Existencias totales</dt>
                <dd :class="{ low: product.has_low_stock }">{{ product.total_stock }}</dd>
              </div>
            </dl>
            <p v-if="product.description" class="desc">{{ product.description }}</p>
          </div>
        </section>
      </div>

      <!-- Variantes -->
      <section class="card-box">
        <h2 class="card-box__title">Variantes <span class="muted">({{ variants.length }})</span></h2>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th class="thumb-col">Foto</th>
                <th>SKU</th>
                <th>Atributos</th>
                <th>Código de barras</th>
                <th class="num">Costo</th>
                <th class="num">Venta</th>
                <th class="num">Stock</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="v in variants"
                :key="v.id"
                class="vrow"
                :class="{ 'vrow--active': v.id === selectedVariantId }"
                @click="selectVariant(v)"
              >
                <td>
                  <span class="vthumb">
                    <img v-if="v.main_image" :src="v.main_image" :alt="v.sku" />
                    <ImageOff v-else :size="15" />
                  </span>
                </td>
                <td><code class="sku">{{ v.sku }}</code></td>
                <td>
                  <span class="attrs">
                    <span
                      v-if="variantDot(v)"
                      class="dot"
                      :style="{ background: variantDot(v) }"
                    ></span>
                    {{ variantAttrs(v) }}
                  </span>
                </td>
                <td>{{ v.barcode || '—' }}</td>
                <td class="num">{{ money(v.effective_cost) }}</td>
                <td class="num">{{ money(v.sale_price) }}</td>
                <td class="num">
                  {{ v.stock }}
                  <span v-if="v.is_low_stock" class="badge-low" title="En o por debajo del mínimo">
                    <AlertTriangle :size="12" /> bajo
                  </span>
                </td>
              </tr>
              <tr v-if="!variants.length">
                <td colspan="7" class="muted empty">Sin variantes activas.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--color-muted);
  margin-bottom: 16px;
}
.back:hover {
  color: var(--color-primary);
}
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page__title {
  font-size: 1.6rem;
}
.page__subtitle {
  color: var(--color-muted);
  margin-top: 4px;
}

.layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 20px;
  align-items: start;
  margin-bottom: 20px;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card-box__title {
  font-size: 1.02rem;
  margin-bottom: 16px;
}

.gallery__label {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-bottom: 10px;
}
.gallery__main {
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: #94a3b8;
  overflow: hidden;
}
.gallery__main img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gallery__thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.gallery__thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  border: 2px solid transparent;
  overflow: hidden;
  cursor: pointer;
  background: var(--color-surface-alt);
}
.gallery__thumb.active {
  border-color: var(--color-primary);
}
.gallery__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.data {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 20px;
}
.data dt {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  margin-bottom: 3px;
}
.data dd {
  font-weight: 600;
  color: var(--color-ink);
}
.data dd.low {
  color: #dc2626;
}
.desc {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-surface-alt);
  color: var(--color-body);
  font-size: 0.92rem;
  white-space: pre-line;
}

.table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.table th {
  text-align: left;
  padding: 11px 14px;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
  white-space: nowrap;
}
.table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.table .num {
  text-align: right;
  white-space: nowrap;
}
.sku {
  font-size: 0.82rem;
  background: var(--color-surface-alt);
  padding: 2px 7px;
  border-radius: 6px;
  color: var(--color-body);
}
.thumb-col {
  width: 56px;
}
.vthumb {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: #94a3b8;
  overflow: hidden;
}
.vthumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.vthumb__count {
  position: absolute;
  bottom: 0;
  right: 0;
  font-size: 0.6rem;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.7);
  color: #fff;
  padding: 0 4px;
  border-top-left-radius: 4px;
}
.vrow {
  cursor: pointer;
}
.vrow:hover {
  background: var(--color-surface-alt);
}
.vrow--active {
  background: var(--color-primary-soft);
}
.attrs {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.dot {
  width: 13px;
  height: 13px;
  border-radius: 4px;
  border: 1px solid var(--color-line);
}
.badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}
.badge--on { background: #ecfdf5; color: #047857; }
.badge--off { background: #fef2f2; color: #b91c1c; }
.badge-low {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: var(--radius-full);
  padding: 1px 7px;
  margin-left: 6px;
}
.muted { color: var(--color-muted); }
.empty { text-align: center; padding: 24px; }
.alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .page__head {
    flex-direction: column;
  }
}
</style>
