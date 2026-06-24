<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Package, Plus, Pencil, Power, PowerOff, Search, ImageOff } from 'lucide-vue-next'
import { productsApi, categoriesApi, brandsApi } from '@/services/catalog'
import SearchSelect from '@/components/SearchSelect.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const isAdmin = computed(() => auth.isAdmin)

function openDetail(product) {
  router.push({ name: 'product-detail', params: { id: product.id } })
}

const products = ref([])
const categories = ref([])
const brands = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')

// Filtros
const search = ref('')
const categoryFilter = ref('')
const brandFilter = ref('')
const showInactive = ref(false)
let searchTimer = null

function money(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(value)
}

// Precio del producto: rango min–max de sus variantes (o único si coinciden).
function priceLabel(p) {
  if (p.price_min == null) return '—'
  if (p.price_min === p.price_max) return money(p.price_min)
  return `${money(p.price_min)} – ${money(p.price_max)}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page_size: 50 }
    if (search.value) params.search = search.value
    if (categoryFilter.value) params.subcategory__category = categoryFilter.value
    if (brandFilter.value) params.brand = brandFilter.value
    // Por defecto solo se muestran los productos activos.
    if (!showInactive.value) params.is_active = true
    const data = await productsApi.list(params)
    products.value = data.results
    count.value = data.count
  } catch {
    error.value = 'No se pudieron cargar los productos.'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

// Recarga al cambiar filtros (categoría/marca) o el toggle de inactivos.
watch([categoryFilter, brandFilter, showInactive], load)

async function toggleActive(product) {
  const activate = !product.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar producto' : 'Desactivar producto',
    text: activate
      ? `"${product.name}" volverá a estar visible.`
      : `"${product.name}" dejará de mostrarse, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await productsApi.update(product.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Producto activado' : 'Producto desactivado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

onMounted(async () => {
  try {
    const [cats, brs] = await Promise.all([
      categoriesApi.list({ page_size: 100 }),
      brandsApi.list({ page_size: 200 })
    ])
    categories.value = cats.results
    brands.value = brs.results
  } catch {
    /* no bloquea la carga de productos */
  }
  await load()
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Productos</h1>
        <p class="page__subtitle">{{ count }} producto(s) en el catálogo.</p>
      </div>
      <RouterLink v-if="isAdmin" :to="{ name: 'product-new' }" class="btn btn--primary">
        <Plus :size="18" /> Nuevo producto
      </RouterLink>
    </header>

    <div class="toolbar">
      <div class="toolbar__search">
        <Search :size="18" class="toolbar__search-icon" />
        <input
          v-model="search"
          class="toolbar__input"
          type="search"
          placeholder="Buscar por nombre o SKU…"
          @input="onSearch"
        />
      </div>
      <div class="toolbar__filter">
        <SearchSelect
          v-model="categoryFilter"
          :options="categories"
          clearable
          clear-label="Todas las categorías"
          placeholder="Todas las categorías"
        />
      </div>
      <div class="toolbar__filter">
        <SearchSelect
          v-model="brandFilter"
          :options="brands"
          clearable
          clear-label="Todas las marcas"
          placeholder="Todas las marcas"
        />
      </div>
      <label v-if="isAdmin" class="toolbar__check">
        <input v-model="showInactive" type="checkbox" />
        <span>Mostrar inactivos</span>
      </label>
    </div>

    <LoadingState v-if="loading" label="Cargando productos…" />

    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!products.length" class="empty">
      <span class="empty__icon"><Package :size="32" /></span>
      <h2 class="empty__title">No hay productos</h2>
      <p class="empty__text">
        {{ isAdmin ? 'Crea tu primer producto para verlo aquí.' : 'Aún no hay productos en el catálogo.' }}
      </p>
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th></th>
            <th>Producto</th>
            <th>Categoría</th>
            <th class="num">Venta</th>
            <th class="num">Stock</th>
            <th>Estado</th>
            <th v-if="isAdmin"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in products"
            :key="p.id"
            class="row--clickable"
            :class="{ 'row--inactive': !p.is_active }"
            @click="openDetail(p)"
          >
            <td>
              <span class="thumb">
                <img v-if="p.main_image" :src="p.main_image" :alt="p.name" />
                <ImageOff v-else :size="18" />
              </span>
            </td>
            <td>
              <span class="prod-name">{{ p.name }}</span>
              <span v-if="p.brand_detail" class="prod-brand">{{ p.brand_detail.name }}</span>
              <span v-if="p.variants.length > 1" class="prod-attrs">
                {{ p.variants.length }} variantes
              </span>
            </td>
            <td>
              <span class="prod-cat">{{ p.category_name }}</span>
              <span class="prod-subcat">{{ p.subcategory_name }}</span>
            </td>
            <td class="num">{{ priceLabel(p) }}</td>
            <td class="num">
              <span class="stock" :class="{ 'stock--low': p.has_low_stock }">{{ p.total_stock }}</span>
            </td>
            <td>
              <span class="badge" :class="p.is_active ? 'badge--on' : 'badge--off'">
                {{ p.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td v-if="isAdmin" @click.stop>
              <div class="row-actions">
                <RouterLink
                  :to="{ name: 'product-edit', params: { id: p.id } }"
                  class="icon-btn"
                  title="Editar"
                >
                  <Pencil :size="16" />
                </RouterLink>
                <button
                  v-if="p.is_active"
                  class="icon-btn icon-btn--danger"
                  title="Desactivar"
                  @click="toggleActive(p)"
                >
                  <PowerOff :size="16" />
                </button>
                <button
                  v-else
                  class="icon-btn icon-btn--ok"
                  title="Activar"
                  @click="toggleActive(p)"
                >
                  <Power :size="16" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.toolbar__search {
  position: relative;
  flex: 1;
  min-width: 220px;
}
.toolbar__search-icon {
  position: absolute;
  left: 13px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}
.toolbar__input,
.toolbar__select {
  width: 100%;
  padding: 11px 14px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.toolbar__input {
  padding-left: 40px;
}
.toolbar__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.toolbar__filter {
  width: 240px;
  flex-shrink: 0;
}
.toolbar__check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.88rem;
  color: var(--color-body);
  cursor: pointer;
  white-space: nowrap;
}

.row--inactive {
  opacity: 0.55;
}
.row--inactive:hover {
  opacity: 0.8;
}

.table-wrap {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
.table th {
  text-align: left;
  padding: 13px 16px;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
  white-space: nowrap;
}
.table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.table tbody tr:hover {
  background: var(--color-surface-alt);
}
.table .num {
  text-align: right;
  white-space: nowrap;
}

.thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: #94a3b8;
  overflow: hidden;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.prod-name {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
  transition: color 0.16s ease;
}
.row--clickable {
  cursor: pointer;
}
.row--clickable:hover .prod-name {
  color: var(--color-primary);
}
.prod-brand {
  display: block;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--color-primary);
}
.prod-attrs {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 0.8rem;
  color: var(--color-muted);
}
.prod-color {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.prod-color__dot {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  border: 1px solid var(--color-line);
}
.sku {
  font-size: 0.85rem;
  background: var(--color-surface-alt);
  padding: 2px 7px;
  border-radius: 6px;
  color: var(--color-body);
}
.prod-cat {
  display: block;
  font-weight: 500;
}
.prod-subcat {
  display: block;
  font-size: 0.8rem;
  color: var(--color-muted);
}
.stock {
  font-weight: 600;
}
.stock--low {
  color: #dc2626;
}

.badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}
.badge--on {
  background: #ecfdf5;
  color: #047857;
}
.badge--off {
  background: #fef2f2;
  color: #b91c1c;
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  border: 1px solid var(--color-line);
  background: #fff;
  transition: all 0.16s ease;
}
.icon-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}
.icon-btn--ok {
  color: var(--color-success);
  border-color: #a7f3d0;
}
.icon-btn--ok:hover {
  background: #ecfdf5;
}

.prod-muted {
  color: var(--color-muted);
}
.prod-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 18px;
}
.empty__title {
  font-size: 1.2rem;
  margin-bottom: 6px;
}
.empty__text {
  color: var(--color-muted);
  max-width: 420px;
}
</style>
