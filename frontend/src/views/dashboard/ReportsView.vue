<script setup>
import { ref, onMounted } from 'vue'
import { Download, Receipt, Package, ShoppingBag, Boxes } from 'lucide-vue-next'
import { analyticsApi } from '@/services/analytics'
import { warehousesApi } from '@/services/inventory'
import { useAuthStore } from '@/stores/auth'
import { toastError } from '@/utils/notify'

const auth = useAuthStore()

function isoDaysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const from = ref(isoDaysAgo(29))
const to = ref(isoDaysAgo(0))
const warehouse = ref('')
const warehouses = ref([])
const downloading = ref('')

// `ranged` = el reporte depende del rango de fechas; el inventario es una foto actual.
const reports = [
  { dataset: 'sales', label: 'Ventas', desc: 'Ventas del punto de venta completadas en el rango.', icon: Receipt, ranged: true },
  { dataset: 'orders', label: 'Pedidos en línea', desc: 'Pedidos del rango (excluye cancelados).', icon: ShoppingBag, ranged: true },
  { dataset: 'products', label: 'Productos más vendidos', desc: 'Ranking por ingresos y unidades en el rango.', icon: Package, ranged: true },
  { dataset: 'inventory', label: 'Inventario valorizado', desc: 'Foto actual: existencias, costo unitario y valor de todo el inventario.', icon: Boxes, ranged: false }
]

async function download(report) {
  if (report.ranged && from.value > to.value) {
    toastError('La fecha inicial no puede ser mayor que la final.')
    return
  }
  downloading.value = report.dataset
  try {
    const params = { dataset: report.dataset }
    if (report.ranged) {
      params.from = from.value
      params.to = to.value
    }
    if (auth.isAdmin && warehouse.value) params.warehouse = warehouse.value
    await analyticsApi.download(params)
  } catch {
    toastError('No se pudo generar el reporte. Intenta de nuevo.')
  } finally {
    downloading.value = ''
  }
}

onMounted(async () => {
  if (!auth.isAdmin) return
  try {
    const w = await warehousesApi.list({ page_size: 200, is_active: true })
    warehouses.value = w.results
  } catch {
    /* sin selector de bodega si falla */
  }
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Reportes</h1>
        <p class="page__subtitle">
          Descarga reportes en CSV (se abren en Excel o Google Sheets). Elige el rango y la bodega.
        </p>
      </div>
    </header>

    <!-- Filtros -->
    <section class="filters">
      <label class="filter">
        <span class="filter__label">Desde</span>
        <input v-model="from" type="date" class="filter__input" :max="to" />
      </label>
      <label class="filter">
        <span class="filter__label">Hasta</span>
        <input v-model="to" type="date" class="filter__input" :min="from" />
      </label>
      <label v-if="auth.isAdmin && warehouses.length" class="filter">
        <span class="filter__label">Bodega</span>
        <select v-model="warehouse" class="filter__input">
          <option value="">Todas</option>
          <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
      </label>
    </section>

    <!-- Reportes -->
    <section class="reports">
      <article v-for="r in reports" :key="r.dataset" class="report">
        <span class="report__icon"><component :is="r.icon" :size="22" /></span>
        <div class="report__body">
          <h2 class="report__title">{{ r.label }}</h2>
          <p class="report__desc">{{ r.desc }}</p>
          <p v-if="!r.ranged" class="report__note">Foto actual del inventario (no depende del rango).</p>
        </div>
        <button
          class="btn btn--primary report__btn"
          :disabled="downloading === r.dataset"
          @click="download(r)"
        >
          <Download :size="16" /> {{ downloading === r.dataset ? 'Generando…' : 'Descargar CSV' }}
        </button>
      </article>
    </section>
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
  max-width: 620px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  margin-bottom: 18px;
}
.filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 160px;
}
.filter__label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-muted);
}
.filter__input {
  padding: 9px 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.92rem;
  color: var(--color-ink);
  background: var(--color-surface);
}
.filter__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.reports {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.report {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
}
.report__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex-shrink: 0;
}
.report__body {
  flex: 1;
  min-width: 0;
}
.report__title {
  font-size: 1.02rem;
  margin-bottom: 3px;
}
.report__desc {
  font-size: 0.86rem;
  color: var(--color-muted);
  line-height: 1.45;
}
.report__note {
  font-size: 0.78rem;
  color: var(--color-accent-dark);
  margin-top: 4px;
}
.report__btn {
  flex-shrink: 0;
  gap: 8px;
}

@media (max-width: 820px) {
  .reports {
    grid-template-columns: 1fr;
  }
  .report {
    flex-wrap: wrap;
  }
  .report__btn {
    width: 100%;
  }
}
</style>
