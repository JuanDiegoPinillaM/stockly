<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  Wallet,
  Coins,
  ShoppingBag,
  Receipt,
  Package,
  Users,
  Download,
  RefreshCw,
  Store,
  Boxes,
  TriangleAlert,
  PackageX
} from 'lucide-vue-next'
import { analyticsApi } from '@/services/analytics'
import { warehousesApi } from '@/services/inventory'
import { useAuthStore } from '@/stores/auth'
import { toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import KpiCard from '@/components/charts/KpiCard.vue'
import ChartArea from '@/components/charts/ChartArea.vue'
import ChartBars from '@/components/charts/ChartBars.vue'
import ChartDonut from '@/components/charts/ChartDonut.vue'
import SearchSelect from '@/components/SearchSelect.vue'

const auth = useAuthStore()

const period = ref('30d')
const warehouse = ref('')
const warehouses = ref([])
const data = ref(null)
const loading = ref(true)
const refreshing = ref(false)
const exporting = ref(false)

const periods = [
  { key: '7d', label: '7 días' },
  { key: '30d', label: '30 días' },
  { key: '90d', label: '90 días' },
  { key: '12m', label: '12 meses' }
]

const REV = '#0f766e'
const PROFIT = '#d4a437'

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

async function fetchData() {
  const first = data.value === null
  if (first) loading.value = true
  else refreshing.value = true
  try {
    const params = { period: period.value }
    if (auth.isAdmin && warehouse.value) params.warehouse = warehouse.value
    data.value = await analyticsApi.overview(params)
  } catch {
    toastError('No se pudo cargar la analítica.')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function exportReport(dataset) {
  exporting.value = true
  try {
    const params = { period: period.value, dataset }
    if (auth.isAdmin && warehouse.value) params.warehouse = warehouse.value
    await analyticsApi.download(params)
  } catch {
    toastError('No se pudo generar el reporte.')
  } finally {
    exporting.value = false
  }
}

// --- Datos derivados para las gráficas ---
const ts = computed(() => data.value?.timeseries || [])
const labels = computed(() => ts.value.map((t) => t.label))
const revenueSpark = computed(() => ts.value.map((t) => t.revenue))
const profitSpark = computed(() => ts.value.map((t) => t.profit))
const ordersSpark = computed(() => ts.value.map((t) => t.orders))

const areaSeries = computed(() => [
  { name: 'Ingresos', color: REV, values: revenueSpark.value },
  { name: 'Ganancia', color: PROFIT, values: profitSpark.value }
])

const channelItems = computed(() => (data.value?.channels || []).map((c) => ({ name: c.name, value: c.amount })))
const paymentItems = computed(() => (data.value?.payment_methods || []).map((p) => ({ name: p.name, value: p.amount })))
const topProducts = computed(() =>
  (data.value?.top_products || []).map((p) => ({ label: p.name, value: p.revenue, meta: `${p.units} uds vendidas` }))
)
const topCategories = computed(() => (data.value?.top_categories || []).map((c) => ({ label: c.name, value: c.revenue })))
const byWarehouse = computed(() => (data.value?.by_warehouse || []).map((w) => ({ label: w.name, value: w.revenue })))
const pipeline = computed(() => data.value?.order_pipeline || [])
const inventory = computed(() => data.value?.inventory || {})

const k = computed(() => data.value?.kpis || {})

const pipelineColors = {
  pendiente: '#f59e0b',
  confirmado: '#6366f1',
  enviado: '#0ea5a3',
  entregado: '#047857',
  cancelado: '#dc2626'
}

watch([period, warehouse], fetchData)

onMounted(async () => {
  if (auth.isAdmin) {
    try {
      const w = await warehousesApi.list({ page_size: 200, is_active: true })
      warehouses.value = w.results
    } catch {
      /* sin selector de bodega si falla */
    }
  }
  fetchData()
})
</script>

<template>
  <div class="page">
    <header class="dash-head">
      <div>
        <h1 class="page__title">Hola, {{ auth.firstName }}</h1>
        <p class="page__subtitle">
          Panorama de tu negocio
          <RefreshCw v-if="refreshing" :size="14" class="spin" />
        </p>
      </div>

      <div class="dash-controls">
        <SearchSelect
          v-if="auth.isAdmin && warehouses.length"
          v-model="warehouse"
          :options="warehouses"
          clearable
          clear-label="Todas las bodegas"
          placeholder="Todas las bodegas"
          class="wh-select"
        />
        <div class="period">
          <button
            v-for="p in periods"
            :key="p.key"
            class="period__btn"
            :class="{ 'period__btn--active': period === p.key }"
            @click="period = p.key"
          >
            {{ p.label }}
          </button>
        </div>
        <details class="export">
          <summary class="btn btn--ghost btn--sm">
            <Download :size="16" /> Exportar
          </summary>
          <div class="export__menu">
            <button :disabled="exporting" @click="exportReport('sales')">Ventas (POS)</button>
            <button :disabled="exporting" @click="exportReport('orders')">Pedidos en línea</button>
            <button :disabled="exporting" @click="exportReport('products')">Productos vendidos</button>
            <button :disabled="exporting" @click="exportReport('inventory')">Inventario bajo</button>
          </div>
        </details>
      </div>
    </header>

    <LoadingState v-if="loading" label="Cargando analítica…" />

    <template v-else-if="data">
      <!-- KPIs -->
      <section class="kpis">
        <KpiCard label="Ingresos" :value="k.revenue.value" :change="k.revenue.change" format="money" :accent="REV" :spark="revenueSpark" :icon="Wallet" />
        <KpiCard label="Ganancia" :value="k.profit.value" :change="k.profit.change" format="money" :accent="PROFIT" :spark="profitSpark" :icon="Coins" />
        <KpiCard label="Transacciones" :value="k.transactions.value" :change="k.transactions.change" format="number" accent="#6366f1" :spark="ordersSpark" :icon="ShoppingBag" />
        <KpiCard label="Ticket promedio" :value="k.avg_ticket.value" :change="k.avg_ticket.change" format="money" accent="#0ea5a3" :icon="Receipt" />
        <KpiCard label="Unidades" :value="k.units.value" :change="k.units.change" format="number" accent="#f97316" :icon="Package" />
        <KpiCard label="Clientes" :value="k.customers.value" :change="k.customers.change" format="number" accent="#64748b" :icon="Users" />
      </section>

      <!-- Serie principal + canales -->
      <section class="grid grid--main">
        <div class="card">
          <div class="card__head">
            <h2 class="card__title">Ingresos y ganancia</h2>
            <div class="legend-inline">
              <span class="legend-inline__item"><i :style="{ background: REV }"></i> Ingresos</span>
              <span class="legend-inline__item"><i :style="{ background: PROFIT }"></i> Ganancia</span>
            </div>
          </div>
          <ChartArea :labels="labels" :series="areaSeries" format="money" :height="300" />
        </div>
        <div class="card">
          <h2 class="card__title">Ventas por canal</h2>
          <ChartDonut :items="channelItems" format="money" :palette="[REV, PROFIT]" />
        </div>
      </section>

      <!-- Top productos / categorías / pagos -->
      <section class="grid grid--3">
        <div class="card">
          <h2 class="card__title">Productos más vendidos</h2>
          <ChartBars :items="topProducts" format="money" rank :color="REV" />
        </div>
        <div class="card">
          <h2 class="card__title">Ventas por categoría</h2>
          <ChartBars :items="topCategories" format="money" color="#6366f1" />
        </div>
        <div class="card">
          <h2 class="card__title">Métodos de pago</h2>
          <ChartDonut :items="paymentItems" format="money" />
        </div>
      </section>

      <!-- Pedidos por estado + inventario -->
      <section class="grid grid--2">
        <div class="card">
          <h2 class="card__title">Pedidos en línea por estado</h2>
          <div class="pipeline">
            <div v-for="p in pipeline" :key="p.status" class="pstat">
              <span class="pstat__dot" :style="{ background: pipelineColors[p.status] }"></span>
              <span class="pstat__count">{{ p.count }}</span>
              <span class="pstat__label">{{ p.label }}</span>
            </div>
          </div>
          <div v-if="byWarehouse.length > 1" class="wh-block">
            <h3 class="card__subtitle">Ingresos por bodega</h3>
            <ChartBars :items="byWarehouse" format="money" :color="REV" />
          </div>
        </div>

        <div class="card">
          <h2 class="card__title">Inventario</h2>
          <div class="inv-stats">
            <div class="inv-stat">
              <span class="inv-stat__icon" style="color:#0f766e;background:#ecfdf5"><Boxes :size="18" /></span>
              <div>
                <p class="inv-stat__value">{{ money(inventory.stock_value) }}</p>
                <p class="inv-stat__label">Valor del inventario</p>
              </div>
            </div>
            <div class="inv-stat">
              <span class="inv-stat__icon" style="color:#6366f1;background:#eef2ff"><Package :size="18" /></span>
              <div>
                <p class="inv-stat__value">{{ new Intl.NumberFormat('es-CO').format(inventory.units || 0) }}</p>
                <p class="inv-stat__label">Unidades en stock</p>
              </div>
            </div>
            <div class="inv-stat">
              <span class="inv-stat__icon" style="color:#b45309;background:#fffbeb"><TriangleAlert :size="18" /></span>
              <div>
                <p class="inv-stat__value">{{ inventory.low_stock || 0 }}</p>
                <p class="inv-stat__label">Bajo stock</p>
              </div>
            </div>
            <div class="inv-stat">
              <span class="inv-stat__icon" style="color:#dc2626;background:#fef2f2"><PackageX :size="18" /></span>
              <div>
                <p class="inv-stat__value">{{ inventory.out_of_stock || 0 }}</p>
                <p class="inv-stat__label">Agotados</p>
              </div>
            </div>
          </div>

          <div v-if="inventory.low_list && inventory.low_list.length" class="low-list">
            <h3 class="card__subtitle">Reabastecer pronto</h3>
            <div v-for="r in inventory.low_list" :key="r.sku" class="low-row">
              <span class="low-row__name">{{ r.name }}</span>
              <span class="low-row__sku">{{ r.sku }}</span>
              <span class="low-row__stock" :class="{ 'low-row__stock--out': r.stock === 0 }">
                {{ r.stock }} / {{ r.min_stock }}
              </span>
            </div>
          </div>
          <p v-else class="muted-hint">Todo el inventario está por encima de su mínimo. <Store :size="14" /></p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dash-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.spin {
  animation: spin 0.9s linear infinite;
  color: var(--color-primary);
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.dash-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.wh-select {
  min-width: 200px;
}
.period {
  display: inline-flex;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  padding: 3px;
}
.period__btn {
  padding: 7px 14px;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--color-muted);
  border-radius: var(--radius-full);
  transition: all 0.15s ease;
}
.period__btn--active {
  background: var(--color-primary);
  color: #fff;
}

.export {
  position: relative;
}
.export summary {
  list-style: none;
  cursor: pointer;
}
.export summary::-webkit-details-marker {
  display: none;
}
.export__menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  padding: 6px;
  z-index: 20;
  min-width: 190px;
}
.export__menu button {
  display: block;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  font-size: 0.88rem;
  color: var(--color-ink);
  border-radius: var(--radius-sm);
}
.export__menu button:hover {
  background: var(--color-surface-alt);
  color: var(--color-primary);
}

.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.grid {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
}
.grid--main {
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
}
.grid--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.grid--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.card__title {
  font-size: 1rem;
  color: var(--color-ink);
  margin-bottom: 14px;
}
.card__head .card__title {
  margin-bottom: 0;
}
.card__subtitle {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 18px 0 12px;
}
.legend-inline {
  display: flex;
  gap: 14px;
}
.legend-inline__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--color-muted);
}
.legend-inline__item i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

/* Pipeline de pedidos */
.pipeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 10px;
}
.pstat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}
.pstat__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.pstat__count {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-ink);
}
.pstat__label {
  font-size: 0.78rem;
  color: var(--color-muted);
}

/* Inventario */
.inv-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.inv-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.inv-stat__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.inv-stat__value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-ink);
}
.inv-stat__label {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.low-list {
  margin-top: 6px;
}
.low-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--color-surface-alt);
  font-size: 0.88rem;
}
.low-row__name {
  flex: 1;
  color: var(--color-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.low-row__sku {
  color: var(--color-muted);
  font-size: 0.8rem;
}
.low-row__stock {
  font-weight: 700;
  color: #b45309;
}
.low-row__stock--out {
  color: #dc2626;
}
.muted-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.86rem;
  color: var(--color-muted);
  margin-top: 12px;
}

@media (max-width: 1024px) {
  .grid--main,
  .grid--3,
  .grid--2 {
    grid-template-columns: 1fr;
  }
}
</style>
