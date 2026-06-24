<script setup>
import { ref, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Plus, Search, Receipt } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import { salesApi } from '@/services/sales'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()

const STATUS_OPTIONS = [
  { value: 'completada', label: 'Completada' },
  { value: 'anulada', label: 'Anulada' }
]

const sales = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')
const search = ref('')
const statusFilter = ref('')
let timer = null

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}
function dt(value) {
  return new Date(value).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page_size: 100, ordering: '-created_at' }
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const data = await salesApi.list(params)
    sales.value = data.results
    count.value = data.count
  } catch {
    error.value = 'No se pudieron cargar las ventas.'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}
watch(statusFilter, load)

function openSale(s) {
  router.push({ name: 'sale-detail', params: { id: s.id } })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Ventas</h1>
        <p class="page__subtitle">{{ count }} venta(s) registradas.</p>
      </div>
      <RouterLink :to="{ name: 'pos' }" class="btn btn--primary">
        <Plus :size="18" /> Nueva venta
      </RouterLink>
    </header>

    <div class="toolbar">
      <div class="toolbar__search">
        <Search :size="18" class="toolbar__search-icon" />
        <input v-model="search" class="toolbar__input" type="search" placeholder="Buscar por número o cliente…" @input="onSearch" />
      </div>
      <div class="toolbar__filter">
        <SearchSelect v-model="statusFilter" :options="STATUS_OPTIONS" value-key="value" label-key="label" clearable clear-label="Todos los estados" placeholder="Todos los estados" />
      </div>
    </div>

    <LoadingState v-if="loading" label="Cargando ventas…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!sales.length" class="empty">
      <span class="empty__icon"><Receipt :size="30" /></span>
      <h2 class="empty__title">Aún no hay ventas</h2>
      <p class="empty__text">Registra tu primera venta desde el punto de venta.</p>
      <RouterLink :to="{ name: 'pos' }" class="btn btn--primary"><Plus :size="18" /> Nueva venta</RouterLink>
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Fecha</th>
            <th>Cliente</th>
            <th class="num">Ítems</th>
            <th class="num">Total</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sales" :key="s.id" class="row--clickable" :class="{ 'row--void': s.status === 'anulada' }" @click="openSale(s)">
            <td class="strong">#{{ s.number }}</td>
            <td class="nowrap">{{ dt(s.created_at) }}</td>
            <td>{{ s.customer_name || 'Mostrador' }}</td>
            <td class="num">{{ s.total_items }}</td>
            <td class="num strong">{{ money(s.total) }}</td>
            <td>
              <span class="badge" :class="s.status === 'completada' ? 'badge--on' : 'badge--off'">{{ s.status_display }}</span>
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
  margin-bottom: 18px;
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
.toolbar__input {
  width: 100%;
  padding: 11px 14px 11px 40px;
  font-family: inherit;
  font-size: 0.93rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.toolbar__filter {
  width: 220px;
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
  padding: 12px 16px;
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
}
.table td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.table .num {
  text-align: right;
  white-space: nowrap;
}
.nowrap {
  white-space: nowrap;
}
.strong {
  font-weight: 700;
  color: var(--color-ink);
}
.row--clickable {
  cursor: pointer;
}
.row--clickable:hover {
  background: var(--color-surface-alt);
}
.row--void {
  opacity: 0.55;
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
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
  gap: 6px;
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
  margin-bottom: 10px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  margin-bottom: 14px;
}
</style>
