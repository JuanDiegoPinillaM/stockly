<script setup>
import { ref, onMounted, watch } from 'vue'
import { Boxes, Coins, Layers, AlertTriangle, Search } from 'lucide-vue-next'
import { stockApi } from '@/services/inventory'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const PAGE_SIZE = 50

const rows = ref([])
const summary = ref({ total_value: 0, total_units: 0, variants_count: 0, low_stock_count: 0 })
const count = ref(0)
const page = ref(1)
const loading = ref(true)
const error = ref('')

// Filtros
const search = ref('')
const onlyInStock = ref(false)
const onlyLowStock = ref(false)
const ordering = ref('product__name')

const ORDER_OPTIONS = [
  { value: 'product__name', label: 'Nombre (A→Z)' },
  { value: '-stock', label: 'Más existencias' },
  { value: 'stock', label: 'Menos existencias' },
  { value: '-sale_price', label: 'Mayor precio' }
]

function money(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(value || 0)
}

function num(value) {
  return new Intl.NumberFormat('es-CO').format(value || 0)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page: page.value, page_size: PAGE_SIZE, ordering: ordering.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (onlyInStock.value) params.in_stock = 1
    if (onlyLowStock.value) params.low_stock = 1
    const data = await stockApi.list(params)
    rows.value = data.results
    count.value = data.count ?? data.results.length
    if (data.summary) summary.value = data.summary
  } catch {
    error.value = 'No se pudo cargar el inventario.'
  } finally {
    loading.value = false
  }
}

// Al cambiar filtros se vuelve a la primera página.
let debounce
watch(search, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => {
    page.value = 1
    load()
  }, 350)
})
watch([onlyInStock, onlyLowStock, ordering], () => {
  page.value = 1
  load()
})
watch(page, load)

const totalPages = () => Math.max(1, Math.ceil(count.value / PAGE_SIZE))

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <h1 class="page__title">Inventario</h1>
      <p class="page__subtitle">Tus existencias actuales valorizadas al costo promedio, con el desglose por bodega.</p>
    </header>

    <ErrorState v-if="error" :message="error" @retry="load" />

    <template v-else>
    <!-- Resumen -->
    <div class="cards">
      <div class="stat">
        <div class="stat__icon stat__icon--value"><Coins :size="20" /></div>
        <div>
          <p class="stat__label">Valor del inventario</p>
          <p class="stat__value">{{ money(summary.total_value) }}</p>
        </div>
      </div>
      <div class="stat">
        <div class="stat__icon stat__icon--units"><Boxes :size="20" /></div>
        <div>
          <p class="stat__label">Unidades totales</p>
          <p class="stat__value">{{ num(summary.total_units) }}</p>
        </div>
      </div>
      <div class="stat">
        <div class="stat__icon stat__icon--variants"><Layers :size="20" /></div>
        <div>
          <p class="stat__label">Variantes</p>
          <p class="stat__value">{{ num(summary.variants_count) }}</p>
        </div>
      </div>
      <div class="stat">
        <div class="stat__icon stat__icon--low"><AlertTriangle :size="20" /></div>
        <div>
          <p class="stat__label">En bajo stock</p>
          <p class="stat__value">{{ num(summary.low_stock_count) }}</p>
        </div>
      </div>
    </div>

    <!-- Filtros -->
    <div class="toolbar">
      <label class="search">
        <Search :size="17" class="search__icon" />
        <input v-model="search" class="search__input" type="search" placeholder="Buscar por producto, SKU o código…" />
      </label>
      <select v-model="ordering" class="select">
        <option v-for="o in ORDER_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <label class="check">
        <input v-model="onlyInStock" type="checkbox" /> Con existencia
      </label>
      <label class="check">
        <input v-model="onlyLowStock" type="checkbox" /> Bajo stock
      </label>
    </div>

    <section class="card-box">
      <LoadingState v-if="loading" label="Cargando inventario…" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Producto</th>
              <th>SKU</th>
              <th>Bodegas</th>
              <th class="num">Existencias</th>
              <th class="num">Costo prom.</th>
              <th class="num">P. venta</th>
              <th class="num">Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id" :class="{ 'row--low': r.is_low_stock }">
              <td>
                <span class="vname">{{ r.product_name }}</span>
                <span v-if="r.variant_label" class="muted vopts">{{ r.variant_label }}</span>
              </td>
              <td><code class="sku">{{ r.sku }}</code></td>
              <td>
                <span v-if="!r.warehouses.length" class="muted">—</span>
                <span v-for="w in r.warehouses" :key="w.warehouse" class="chip">
                  {{ w.warehouse_name }}: <strong>{{ num(w.quantity) }}</strong>
                </span>
              </td>
              <td class="num">
                {{ num(r.stock) }}
                <span v-if="r.is_low_stock" class="badge-low" title="En o por debajo del mínimo">bajo</span>
                <span v-if="r.min_stock" class="muted min">mín {{ num(r.min_stock) }}</span>
              </td>
              <td class="num">{{ money(r.effective_cost) }}</td>
              <td class="num">{{ money(r.sale_price) }}</td>
              <td class="num strong">{{ money(r.stock_value) }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="7" class="muted empty">No hay existencias para mostrar.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!loading && count > PAGE_SIZE" class="pager">
        <button class="btn btn--ghost" :disabled="page <= 1" @click="page--">Anterior</button>
        <span class="muted">Página {{ page }} de {{ totalPages() }}</span>
        <button class="btn btn--ghost" :disabled="page >= totalPages()" @click="page++">Siguiente</button>
      </div>
    </section>
    </template>
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
}

/* Tarjetas de resumen */
.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}
.stat {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px 18px;
}
.stat__icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.stat__icon--value { background: #eef2ff; color: #4338ca; }
.stat__icon--units { background: #ecfeff; color: #0e7490; }
.stat__icon--variants { background: #f0fdf4; color: #15803d; }
.stat__icon--low { background: #fef2f2; color: #b91c1c; }
.stat__label {
  font-size: 0.78rem;
  color: var(--color-muted);
  margin-bottom: 2px;
}
.stat__value {
  font-size: 1.25rem;
  font-weight: 700;
}

/* Filtros */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}
.search {
  position: relative;
  flex: 1;
  min-width: 240px;
}
.search__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-muted);
}
.search__input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  font-family: inherit;
  font-size: 0.93rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
}
.search__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.select {
  padding: 10px 12px;
  font-family: inherit;
  font-size: 0.9rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
}
.check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--color-ink);
  cursor: pointer;
}

.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 8px 0;
}
.table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.74rem;
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
.table .num {
  text-align: right;
  white-space: nowrap;
}
.row--low {
  background: #fffbeb;
}
.vname {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
}
.vopts {
  font-size: 0.8rem;
}
.sku {
  font-size: 0.8rem;
  color: var(--color-muted);
}
.chip {
  display: inline-block;
  font-size: 0.78rem;
  background: var(--color-surface-alt);
  border-radius: var(--radius-full);
  padding: 2px 10px;
  margin: 2px 4px 2px 0;
  color: var(--color-ink);
}
.strong {
  font-weight: 700;
}
.badge-low {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: var(--radius-full);
  padding: 1px 7px;
  margin-left: 6px;
}
.min {
  display: block;
  font-size: 0.72rem;
}
.muted { color: var(--color-muted); }
.pad { padding: 22px 16px; }
.empty { text-align: center; padding: 28px; }
.alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  margin-bottom: 14px;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 14px;
}

@media (max-width: 900px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
