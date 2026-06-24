<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, PackageSearch, SlidersHorizontal, X, ChevronDown, Check } from 'lucide-vue-next'
import { storeApi } from '@/services/store'
import ProductCard from '@/components/store/ProductCard.vue'
import PriceRange from '@/components/store/PriceRange.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const router = useRouter()

const categories = ref([])
const brands = ref([])
const products = ref([])
const loading = ref(true)
const error = ref('')

const activeCategory = ref(route.query.category ? Number(route.query.category) : '')
const activeSubcategory = ref(route.query.subcategory ? Number(route.query.subcategory) : '')
const activeBrand = ref(route.query.brand ? Number(route.query.brand) : '')
const search = ref(route.query.search || '')
const priceMin = ref(route.query.price_min || '')
const priceMax = ref(route.query.price_max || '')
const priceBounds = ref({ min: 0, max: 0 })
const onlyAvailable = ref(route.query.available === '1')
const ordering = ref('name')
const mobileFilters = ref(false)
let timer = null

// Filtros por atributos de variación (Color, Talla, Almacenamiento, RAM…).
const attrFilters = ref([]) // [{ id, name, is_color, options:[{id,value,swatch_hex}] }]
const optionLabels = ref({}) // id de opción -> etiqueta (para los chips)
const selectedOptions = ref(
  (route.query.options ? String(route.query.options).split(',') : [])
    .map(Number)
    .filter(Boolean)
)
function isOption(id) {
  return selectedOptions.value.includes(id)
}
function toggleOption(id) {
  const i = selectedOptions.value.indexOf(id)
  if (i >= 0) selectedOptions.value.splice(i, 1)
  else selectedOptions.value.push(id)
}

const SORTS = [
  { value: 'name', label: 'Nombre (A–Z)' },
  { value: '-created_at', label: 'Más recientes' },
  { value: 'price', label: 'Precio: menor a mayor' },
  { value: '-price', label: 'Precio: mayor a menor' },
  { value: '-sold', label: 'Destacados: más vendidos' },
  { value: 'sold', label: 'Destacados: menos vendidos' }
]

// Desplegable de orden personalizado (el <select> nativo no se puede estilizar).
const sortOpen = ref(false)
const sortRef = ref(null)
const currentSortLabel = computed(
  () => SORTS.find((s) => s.value === ordering.value)?.label || ''
)
function selectSort(value) {
  ordering.value = value
  sortOpen.value = false
}
function onDocClick(e) {
  if (sortRef.value && !sortRef.value.contains(e.target)) sortOpen.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

const activeCategoryObj = computed(() =>
  categories.value.find((c) => c.id === activeCategory.value) || null
)
const activeSubcategoryObj = computed(() =>
  activeCategoryObj.value?.subcategories.find((s) => s.id === activeSubcategory.value) || null
)
const activeBrandObj = computed(() =>
  brands.value.find((b) => b.id === activeBrand.value) || null
)
const hasFilters = computed(
  () =>
    activeCategory.value ||
    activeSubcategory.value ||
    activeBrand.value ||
    search.value.trim() ||
    priceMin.value ||
    priceMax.value ||
    onlyAvailable.value ||
    selectedOptions.value.length
)

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

// Grupo de color (eje de fotos) y colores seleccionados en el filtro.
const colorGroup = computed(() => attrFilters.value.find((g) => g.is_color) || null)
const selectedColorLabels = computed(() => {
  const g = colorGroup.value
  if (!g) return null
  const sel = g.options
    .filter((o) => selectedOptions.value.includes(o.id))
    .map((o) => o.value.toLowerCase())
  return sel.length ? new Set(sel) : null
})

// Grupos de atributos NO-color con opciones seleccionadas (talla, almacenamiento…),
// como listas de textos de valor por grupo (OR dentro del grupo, AND entre grupos).
const nonColorSelectedGroups = computed(() => {
  const groups = []
  for (const g of attrFilters.value) {
    if (g.is_color) continue
    const sel = g.options
      .filter((o) => selectedOptions.value.includes(o.id))
      .map((o) => o.value.toLowerCase())
    if (sel.length) groups.push(sel)
  }
  return groups
})
// Un color pasa si sus variantes cubren cada grupo de atributos seleccionado.
function colorMatchesAttrs(c) {
  if (!nonColorSelectedGroups.value.length) return true
  const cv = new Set((c.values || []).map((x) => x.toLowerCase()))
  return nonColorSelectedGroups.value.every((sel) => sel.some((v) => cv.has(v)))
}

// Expande cada producto en una tarjeta por color (eje de fotos). Si filtras por
// color, solo aparecen los colores elegidos. Productos sin color → una tarjeta.
const cards = computed(() => {
  const out = []
  for (const p of products.value) {
    const colors = p.colors || []
    if (!colors.length) {
      out.push({
        key: `p${p.id}`,
        product_id: p.id,
        slug: p.slug,
        name: p.name,
        category: p.category,
        main_image: p.main_image,
        hover_image: p.hover_image,
        is_new: p.is_new,
        available: p.available,
        price_min: p.price_min,
        price_max: p.price_max
      })
      continue
    }
    const wanted = selectedColorLabels.value
    let list = wanted ? colors.filter((c) => wanted.has(c.label.toLowerCase())) : colors
    // Oculta colores cuyas variantes no cubren la talla/atributo filtrado.
    list = list.filter(colorMatchesAttrs)
    for (const c of list) {
      out.push({
        key: `p${p.id}-v${c.value_id}`,
        product_id: p.id,
        slug: p.slug,
        name: p.name,
        category: p.category,
        main_image: c.image,
        hover_image: c.image2,
        is_new: p.is_new,
        available: c.available,
        price_min: c.price_min,
        price_max: c.price_max,
        color_label: c.label,
        color_id: c.value_id,
        swatch_hex: c.swatch_hex
      })
    }
  }
  return out
})

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    const params = { ordering: ordering.value }
    if (activeCategory.value) params.category = activeCategory.value
    if (activeSubcategory.value) params.subcategory = activeSubcategory.value
    if (activeBrand.value) params.brand = activeBrand.value
    if (search.value.trim()) params.search = search.value.trim()
    if (priceMin.value) params.price_min = priceMin.value
    if (priceMax.value) params.price_max = priceMax.value
    if (onlyAvailable.value) params.available = '1'
    if (selectedOptions.value.length) params.options = selectedOptions.value.join(',')
    const data = await storeApi.products(params)
    products.value = data.results || data
  } catch {
    error.value = 'No se pudieron cargar los productos.'
  } finally {
    loading.value = false
  }
}

function syncQuery() {
  const query = {}
  if (activeCategory.value) query.category = activeCategory.value
  if (activeSubcategory.value) query.subcategory = activeSubcategory.value
  if (activeBrand.value) query.brand = activeBrand.value
  if (search.value.trim()) query.search = search.value.trim()
  if (priceMin.value) query.price_min = priceMin.value
  if (priceMax.value) query.price_max = priceMax.value
  if (onlyAvailable.value) query.available = '1'
  if (selectedOptions.value.length) query.options = selectedOptions.value.join(',')
  router.replace({ query })
}

function scopeParams() {
  const p = {}
  if (activeCategory.value) p.category = activeCategory.value
  if (activeSubcategory.value) p.subcategory = activeSubcategory.value
  return p
}

// Recarga TODOS los filtros laterales acotados a la categoría/subcategoría
// elegida, para que sean coherentes (marca, precio y atributos del rubro).
async function loadScopedFilters() {
  const params = scopeParams()
  try {
    const [brs, range, facets] = await Promise.all([
      storeApi.brands(params),
      storeApi.priceRange(params),
      storeApi.attributeFilters(params)
    ])
    brands.value = brs
    priceBounds.value = range
    attrFilters.value = facets
    // Acumula etiquetas para poder mostrar los chips aunque cambie la categoría.
    facets.forEach((g) => g.options.forEach((o) => (optionLabels.value[o.id] = o.value)))
  } catch {
    /* el catálogo igual funciona */
  }
}

// Al cambiar de categoría, los filtros del rubro anterior dejan de aplicar.
function resetScopedSelections() {
  selectedOptions.value = []
  activeBrand.value = ''
  priceMin.value = ''
  priceMax.value = ''
}
function pickCategory(id) {
  activeCategory.value = activeCategory.value === id ? '' : id
  activeSubcategory.value = ''
  resetScopedSelections()
}
function pickSubcategory(id) {
  activeSubcategory.value = activeSubcategory.value === id ? '' : id
  resetScopedSelections()
}
function clearCategory() {
  activeCategory.value = ''
  activeSubcategory.value = ''
  resetScopedSelections()
}
function clearPrice() {
  priceMin.value = ''
  priceMax.value = ''
}
function pickBrand(id) {
  activeBrand.value = activeBrand.value === id ? '' : id
}
function clearFilters() {
  activeCategory.value = ''
  activeSubcategory.value = ''
  activeBrand.value = ''
  search.value = ''
  priceMin.value = ''
  priceMax.value = ''
  onlyAvailable.value = false
  selectedOptions.value = []
}

watch([activeCategory, activeSubcategory, activeBrand, onlyAvailable, ordering], () => {
  syncQuery()
  loadProducts()
})
// Al cambiar de categoría, recarga los filtros laterales acotados a ella.
watch([activeCategory, activeSubcategory], loadScopedFilters)
watch(selectedOptions, () => {
  syncQuery()
  loadProducts()
}, { deep: true })
watch([search, priceMin, priceMax], () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    syncQuery()
    loadProducts()
  }, 400)
})

onMounted(async () => {
  try {
    categories.value = await storeApi.categories()
  } catch {
    /* el catálogo igual carga */
  }
  await Promise.all([loadScopedFilters(), loadProducts()])
})
</script>

<template>
  <div class="catalog-page">
    <!-- Cabecera -->
    <div class="catalog-hero">
      <div class="container">
        <span class="eyebrow">Catálogo</span>
        <h1 class="catalog-hero__title">Nuestros productos</h1>
        <p class="catalog-hero__sub">Explora la colección y encuentra justo lo que buscas.</p>
      </div>
    </div>

    <div class="container catalog">
      <div class="catalog__bar">
        <button class="filters-toggle" @click="mobileFilters = !mobileFilters">
          <SlidersHorizontal :size="16" /> Filtros
        </button>
        <p class="catalog__count">
          <strong>{{ cards.length }}</strong> resultado(s)
        </p>
        <div class="sort">
          <span class="sort__caption">Ordenar</span>
          <div ref="sortRef" class="sort__control">
            <button
              type="button"
              class="sort__btn"
              :class="{ 'sort__btn--open': sortOpen }"
              :aria-expanded="sortOpen"
              @click="sortOpen = !sortOpen"
            >
              {{ currentSortLabel }} <ChevronDown :size="15" />
            </button>
            <transition name="pop">
              <ul v-if="sortOpen" class="sort__menu" role="listbox">
                <li v-for="s in SORTS" :key="s.value">
                  <button
                    type="button"
                    class="sort__opt"
                    :class="{ 'sort__opt--active': s.value === ordering }"
                    role="option"
                    :aria-selected="s.value === ordering"
                    @click="selectSort(s.value)"
                  >
                    {{ s.label }} <Check v-if="s.value === ordering" :size="15" />
                  </button>
                </li>
              </ul>
            </transition>
          </div>
        </div>
      </div>

      <div class="catalog__layout">
        <!-- Filtros -->
        <aside class="filters" :class="{ 'filters--open': mobileFilters }">
          <label class="search">
            <Search :size="17" class="search__icon" />
            <input v-model="search" type="search" placeholder="Buscar productos…" />
          </label>

          <!-- Categorías -->
          <div class="filters__group">
            <div class="filters__label">Categorías</div>
            <button class="cat-link" :class="{ active: !activeCategory }" @click="clearCategory">
              Todas las categorías
            </button>
            <div v-for="c in categories" :key="c.id" class="cat-block">
              <button
                class="cat-link"
                :class="{ active: activeCategory === c.id, 'cat-link--parent': c.subcategories.length }"
                @click="pickCategory(c.id)"
              >
                {{ c.name }}
                <ChevronDown
                  v-if="c.subcategories.length"
                  :size="15"
                  class="cat-link__chevron"
                  :class="{ 'cat-link__chevron--open': activeCategory === c.id }"
                />
              </button>
              <transition name="expand">
                <div v-if="activeCategory === c.id && c.subcategories.length" class="subs">
                  <button
                    v-for="s in c.subcategories"
                    :key="s.id"
                    class="sub-link"
                    :class="{ active: activeSubcategory === s.id }"
                    @click="pickSubcategory(s.id)"
                  >
                    {{ s.name }}
                  </button>
                </div>
              </transition>
            </div>
          </div>

          <!-- Precio -->
          <div class="filters__group">
            <div class="filters__label">Precio</div>
            <PriceRange
              v-if="priceBounds.max > priceBounds.min"
              v-model:lo="priceMin"
              v-model:hi="priceMax"
              :min="priceBounds.min"
              :max="priceBounds.max"
            />
            <div class="price">
              <div class="price__field">
                <span>$</span>
                <input v-model="priceMin" type="number" min="0" inputmode="numeric" placeholder="Mín" />
              </div>
              <span class="price__sep">–</span>
              <div class="price__field">
                <span>$</span>
                <input v-model="priceMax" type="number" min="0" inputmode="numeric" placeholder="Máx" />
              </div>
            </div>
          </div>

          <!-- Disponibilidad -->
          <div class="filters__group">
            <div class="filters__label">Disponibilidad</div>
            <label class="check">
              <input v-model="onlyAvailable" type="checkbox" />
              <span class="check__box"><Check :size="13" /></span>
              <span>Solo productos disponibles</span>
            </label>
          </div>

          <!-- Marcas -->
          <div v-if="brands.length" class="filters__group">
            <div class="filters__label">Marca</div>
            <button class="cat-link" :class="{ active: !activeBrand }" @click="activeBrand = ''">
              Todas las marcas
            </button>
            <button
              v-for="b in brands"
              :key="b.id"
              class="cat-link"
              :class="{ active: activeBrand === b.id }"
              @click="pickBrand(b.id)"
            >
              {{ b.name }}
            </button>
          </div>

          <!-- Atributos de variación (Color, Talla, Almacenamiento, RAM…) -->
          <div v-for="g in attrFilters" :key="g.id" class="filters__group">
            <div class="filters__label">{{ g.name }}</div>
            <div class="opt-chips">
              <button
                v-for="o in g.options"
                :key="o.id"
                class="opt-chip"
                :class="{ 'opt-chip--active': isOption(o.id) }"
                @click="toggleOption(o.id)"
              >
                <span v-if="g.is_color" class="opt-chip__dot" :style="{ background: o.swatch_hex || '#cbd5cf' }"></span>
                {{ o.value }}
              </button>
            </div>
          </div>
        </aside>

        <!-- Resultados -->
        <div class="results">
          <!-- Chips de filtros activos -->
          <div v-if="hasFilters" class="chips">
            <span v-if="activeCategoryObj" class="chip" @click="clearCategory">
              {{ activeCategoryObj.name }} <X :size="13" />
            </span>
            <span v-if="activeSubcategoryObj" class="chip" @click="pickSubcategory(activeSubcategory)">
              {{ activeSubcategoryObj.name }} <X :size="13" />
            </span>
            <span v-if="activeBrandObj" class="chip" @click="activeBrand = ''">
              {{ activeBrandObj.name }} <X :size="13" />
            </span>
            <span v-if="priceMin || priceMax" class="chip" @click="clearPrice">
              {{ priceMin ? money(priceMin) : '$0' }} – {{ priceMax ? money(priceMax) : '∞' }} <X :size="13" />
            </span>
            <span v-if="onlyAvailable" class="chip" @click="onlyAvailable = false">
              Disponibles <X :size="13" />
            </span>
            <span v-if="search.trim()" class="chip" @click="search = ''">
              “{{ search }}” <X :size="13" />
            </span>
            <span v-for="id in selectedOptions" :key="`o${id}`" class="chip" @click="toggleOption(id)">
              {{ optionLabels[id] }} <X :size="13" />
            </span>
            <button class="chips__clear" @click="clearFilters">Limpiar todo</button>
          </div>

          <LoadingState v-if="loading" label="Cargando productos…" />
          <ErrorState v-else-if="error" :message="error" @retry="loadProducts" />

          <div v-else-if="!cards.length" class="empty">
            <span class="empty__icon"><PackageSearch :size="34" /></span>
            <h2 class="empty__title">Sin resultados</h2>
            <p class="empty__text">No encontramos productos con esos filtros.</p>
            <button class="btn btn--ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-else class="grid">
            <ProductCard v-for="c in cards" :key="c.key" :product="c" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.catalog-page {
  padding-bottom: 72px;
}
.catalog-hero {
  background:
    radial-gradient(700px 300px at 85% -40%, rgba(14, 110, 78, 0.08), transparent 60%),
    var(--color-surface-alt);
  border-bottom: 1px solid var(--color-line);
  padding: 48px 0 44px;
  margin-bottom: 28px;
}
.catalog-hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  letter-spacing: -0.015em;
}
.catalog-hero__sub {
  color: var(--color-muted);
  margin-top: 6px;
}

.catalog__bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--color-line);
}
.catalog__count {
  font-size: 0.92rem;
  color: var(--color-muted);
}
.catalog__count strong {
  color: var(--color-ink);
}
.filters-toggle {
  display: none;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  background: #fff;
  font-weight: 500;
}
.sort {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  font-size: 0.86rem;
  color: var(--color-muted);
}
.sort__caption {
  white-space: nowrap;
}
.sort__control {
  position: relative;
}
.sort__btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  background: #fff;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.sort__btn:hover {
  border-color: var(--color-primary);
}
.sort__btn--open {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.sort__btn svg {
  color: var(--color-muted);
  transition: transform 0.2s ease;
}
.sort__btn--open svg {
  transform: rotate(180deg);
}
.sort__menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 210px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 6px;
  z-index: 30;
}
.sort__opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--color-body);
  cursor: pointer;
  transition:
    background 0.14s ease,
    color 0.14s ease;
}
.sort__opt:hover {
  background: var(--color-surface-alt);
  color: var(--color-ink);
}
.sort__opt--active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.sort__opt svg {
  color: var(--color-primary);
}
.pop-enter-active,
.pop-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.catalog__layout {
  display: grid;
  grid-template-columns: 248px 1fr;
  gap: 40px;
  align-items: start;
}
.filters {
  position: sticky;
  top: 130px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.search {
  position: relative;
}
.search__icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-muted);
}
.search input {
  width: 100%;
  padding: 12px 14px 12px 40px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  font-family: inherit;
  font-size: 0.92rem;
  background: #fff;
}
.search input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.filters__label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 10px;
}
.cat-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.93rem;
  color: var(--color-body);
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.cat-link:hover {
  background: var(--color-surface-alt);
  color: var(--color-ink);
}
.cat-link.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.cat-link__chevron {
  flex-shrink: 0;
  color: var(--color-muted);
  transition: transform 0.2s ease;
}
.cat-link__chevron--open {
  transform: rotate(180deg);
  color: var(--color-primary);
}

/* Rango de precio */
.filters__group :deep(.rng) {
  margin: 4px 0 16px;
}
.price {
  display: flex;
  align-items: center;
  gap: 8px;
}
.price__field {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--color-muted);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.price__field:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.price__field input {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  padding: 9px 0;
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--color-ink);
  background: transparent;
}
/* Oculta las flechas del input number para un look más limpio */
.price__field input::-webkit-outer-spin-button,
.price__field input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.price__field input[type='number'] {
  -moz-appearance: textfield;
  appearance: textfield;
}
.price__sep {
  color: var(--color-muted);
}

/* Checkbox de disponibilidad */
.check {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.92rem;
  color: var(--color-body);
  cursor: pointer;
}
.check input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.check__box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-line);
  border-radius: 6px;
  background: #fff;
  color: #fff;
  flex-shrink: 0;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.check__box svg {
  opacity: 0;
  transition: opacity 0.12s ease;
}
.check input:checked + .check__box {
  background: var(--color-primary);
  border-color: var(--color-primary);
}
.check input:checked + .check__box svg {
  opacity: 1;
}
.check input:focus-visible + .check__box {
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

/* Chips de opciones de atributo (Color, Talla, Almacenamiento…) */
.opt-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.opt-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  background: #fff;
  font-size: 0.86rem;
  color: var(--color-body);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}
.opt-chip:hover {
  border-color: var(--color-primary);
}
.opt-chip--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.opt-chip__dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}

/* Transición de despliegue de subcategorías */
.expand-enter-active,
.expand-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.subs {
  margin: 4px 0 8px 14px;
  padding-left: 10px;
  border-left: 1.5px solid var(--color-line);
  display: flex;
  flex-direction: column;
}
.sub-link {
  text-align: left;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  color: var(--color-muted);
}
.sub-link:hover {
  color: var(--color-ink);
}
.sub-link.active {
  color: var(--color-primary);
  font-weight: 600;
}

.chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 22px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-size: 0.84rem;
  font-weight: 500;
  cursor: pointer;
}
.chip:hover {
  background: #d6e7df;
}
.chips__clear {
  font-size: 0.84rem;
  color: var(--color-muted);
  text-decoration: underline;
  margin-left: 4px;
}
.chips__clear:hover {
  color: var(--color-ink);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 22px;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 72px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 8px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  margin-bottom: 12px;
}

@media (max-width: 820px) {
  .catalog__layout {
    grid-template-columns: 1fr;
  }
  .filters {
    position: static;
    display: none;
    background: #fff;
    border: 1px solid var(--color-line);
    border-radius: var(--radius-md);
    padding: 18px;
  }
  .filters--open {
    display: flex;
  }
  .filters-toggle {
    display: inline-flex;
  }
}
</style>
