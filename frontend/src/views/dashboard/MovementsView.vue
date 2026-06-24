<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ArrowLeftRight } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import LoadingState from '@/components/LoadingState.vue'
import { warehousesApi, movementsApi } from '@/services/inventory'
import { variantsApi } from '@/services/catalog'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'

// La SALIDA por venta va por el POS y las TRANSFERENCIAS por su propio flujo con
// aprobación; aquí solo se registran entradas y ajustes.
const TYPE_OPTIONS = [
  { value: 'entrada', label: 'Entrada' },
  { value: 'ajuste_entrada', label: 'Ajuste (entrada)' },
  { value: 'ajuste_salida', label: 'Ajuste (salida)' }
]
// Los tipos que pueden aparecer en el kardex (incluye transferencias históricas).
const KARDEX_TYPE_OPTIONS = [...TYPE_OPTIONS, { value: 'transferencia', label: 'Transferencia' }]
const REASON_OPTIONS = [
  { value: 'compra', label: 'Compra' },
  { value: 'conteo_fisico', label: 'Conteo físico' },
  { value: 'merma_dano', label: 'Merma / daño' },
  { value: 'vencimiento', label: 'Vencimiento' },
  { value: 'robo_perdida', label: 'Robo / pérdida' },
  { value: 'correccion', label: 'Corrección' },
  { value: 'otro', label: 'Otro' }
]

const warehouses = ref([])
const variantsRaw = ref([])
const movements = ref([])
const count = ref(0)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const form = ref({
  product: '',
  variant: '',
  type: 'entrada',
  warehouse: '',
  quantity: 1,
  unit_cost: '',
  reason: '',
  note: ''
})

// Filtros del kardex (también en dos pasos: producto → variante)
const filterProduct = ref('')
const filterVariant = ref('')
const filterWarehouse = ref('')
const filterType = ref('')

const isEntry = computed(() => form.value.type === 'entrada')

// Habilita "Registrar" solo con los obligatorios completos.
const canSubmit = computed(() => {
  if (!form.value.product || !form.value.variant) return false
  if (!form.value.warehouse) return false
  if (!form.value.quantity || form.value.quantity <= 0) return false
  return true
})

function money(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Etiqueta de la variante SIN el nombre del producto (ya se eligió antes):
// destaca SKU + color/talla + stock, que es lo que distingue una variante.
function variantOptionLabel(v) {
  const opts = v.options_label || v.variant_label || ''
  return `${v.sku}${opts ? ` · ${opts}` : ''} · stock ${v.stock}`
}

// Productos únicos derivados de las variantes activas (para el 1.er paso).
const products = computed(() => {
  const map = new Map()
  for (const v of variantsRaw.value) {
    if (!map.has(v.product)) map.set(v.product, { id: v.product, label: v.product_name })
  }
  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label))
})

function variantsOf(productId) {
  return variantsRaw.value
    .filter((v) => v.product === productId)
    .map((v) => ({ id: v.id, label: variantOptionLabel(v) }))
}

const formVariantOptions = computed(() =>
  form.value.product ? variantsOf(form.value.product) : []
)
const filterVariantOptions = computed(() =>
  filterProduct.value ? variantsOf(filterProduct.value) : []
)

// Al cambiar de producto se limpia la variante elegida.
watch(() => form.value.product, () => { form.value.variant = '' })
watch(filterProduct, () => { filterVariant.value = '' })

async function loadRefs() {
  const [wh, vs] = await Promise.all([
    warehousesApi.list({ page_size: 200, is_active: true }),
    variantsApi.list({ page_size: 1000, is_active: true })
  ])
  warehouses.value = wh.results
  variantsRaw.value = vs.results
  // Bodega por defecto = la primera.
  if (warehouses.value.length && !form.value.warehouse) {
    form.value.warehouse = warehouses.value[0].id
  }
}

async function loadMovements() {
  const params = { page_size: 50 }
  // Una variante concreta manda; si solo hay producto, filtra por todo el producto.
  if (filterVariant.value) params.variant = filterVariant.value
  else if (filterProduct.value) params.variant__product = filterProduct.value
  if (filterWarehouse.value) params.warehouse = filterWarehouse.value
  if (filterType.value) params.type = filterType.value
  const data = await movementsApi.list(params)
  movements.value = data.results
  count.value = data.count
}

watch([filterProduct, filterVariant, filterWarehouse, filterType], loadMovements)

async function submit() {
  if (!form.value.product) return toastError('Selecciona un producto.')
  if (!form.value.variant) return toastError('Selecciona una variante.')
  if (!form.value.warehouse) return toastError('Selecciona una bodega.')
  if (!form.value.quantity || form.value.quantity <= 0) {
    return toastError('La cantidad debe ser mayor a cero.')
  }
  const ok = await confirmAction({
    title: 'Registrar movimiento',
    text: '¿Confirmas registrar este movimiento de inventario?',
    confirmText: 'Registrar'
  })
  if (!ok) return

  saving.value = true
  error.value = ''
  try {
    const payload = {
      variant: form.value.variant,
      warehouse: form.value.warehouse,
      type: form.value.type,
      quantity: form.value.quantity,
      reason: form.value.reason || '',
      note: form.value.note || ''
    }
    if (isEntry.value) payload.unit_cost = form.value.unit_cost || 0
    await movementsApi.create(payload)
    toastSuccess('Movimiento registrado')
    form.value.quantity = 1
    form.value.unit_cost = ''
    form.value.note = ''
    await loadMovements()
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudo registrar el movimiento.'
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadRefs()
    await loadMovements()
  } catch {
    error.value = 'No se pudo cargar el inventario.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <h1 class="page__title">Movimientos de inventario</h1>
      <p class="page__subtitle">Registra entradas, salidas, ajustes y transferencias. El kardex es inmutable.</p>
    </header>

    <p v-if="error && !loading" class="alert">{{ error }}</p>
    <LoadingState v-if="loading" label="Cargando inventario…" />

    <div v-else class="layout">
      <!-- Registrar movimiento -->
      <section class="card-box form-card">
        <h2 class="card-box__title"><ArrowLeftRight :size="18" /> Registrar movimiento</h2>

        <label class="field">
          <span class="field__label">Producto *</span>
          <SearchSelect
            v-model="form.product"
            :options="products"
            value-key="id"
            label-key="label"
            placeholder="Busca el producto"
          />
        </label>

        <label class="field">
          <span class="field__label">Variante *</span>
          <SearchSelect
            v-model="form.variant"
            :options="formVariantOptions"
            value-key="id"
            label-key="label"
            :disabled="!form.product"
            :placeholder="form.product ? 'Selecciona la variante' : 'Primero elige el producto'"
          />
        </label>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Tipo *</span>
            <SearchSelect v-model="form.type" :options="TYPE_OPTIONS" value-key="value" label-key="label" />
          </label>
          <label class="field">
            <span class="field__label">Bodega *</span>
            <SearchSelect v-model="form.warehouse" :options="warehouses" placeholder="Selecciona…" />
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Cantidad *</span>
            <input v-model.number="form.quantity" type="number" min="1" class="field__input" />
          </label>
          <label v-if="isEntry" class="field">
            <span class="field__label">Costo unitario</span>
            <MoneyInput v-model="form.unit_cost" />
          </label>
        </div>

        <label class="field">
          <span class="field__label">Motivo</span>
          <SearchSelect
            v-model="form.reason"
            :options="REASON_OPTIONS"
            value-key="value"
            label-key="label"
            placeholder="Sin motivo"
            clearable
            clear-label="Sin motivo"
          />
        </label>

        <label class="field">
          <span class="field__label">Nota</span>
          <input v-model="form.note" class="field__input" maxlength="255" placeholder="Opcional" />
        </label>

        <button class="btn btn--primary btn--block" :disabled="saving || !canSubmit" @click="submit">
          {{ saving ? 'Registrando…' : 'Registrar movimiento' }}
        </button>
      </section>

      <!-- Kardex -->
      <section class="card-box kardex-card">
        <div class="kardex-head">
          <h2 class="card-box__title">Kardex <span class="muted">({{ count }})</span></h2>
        </div>

        <div class="filters">
          <SearchSelect
            v-model="filterProduct"
            :options="products"
            value-key="id"
            label-key="label"
            clearable
            clear-label="Todos los productos"
            placeholder="Todos los productos"
          />
          <SearchSelect
            v-model="filterVariant"
            :options="filterVariantOptions"
            value-key="id"
            label-key="label"
            clearable
            clear-label="Todas las variantes"
            placeholder="Todas las variantes"
            :disabled="!filterProduct"
          />
          <SearchSelect
            v-model="filterWarehouse"
            :options="warehouses"
            clearable
            clear-label="Todas las bodegas"
            placeholder="Todas las bodegas"
          />
          <SearchSelect
            v-model="filterType"
            :options="KARDEX_TYPE_OPTIONS"
            value-key="value"
            label-key="label"
            clearable
            clear-label="Todos los tipos"
            placeholder="Todos los tipos"
          />
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Variante</th>
                <th>Bodega</th>
                <th class="num">Cant.</th>
                <th class="num">Costo u.</th>
                <th class="num">Saldo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in movements" :key="m.id">
                <td class="nowrap">{{ new Date(m.created_at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
                <td>
                  <span class="mtype" :class="m.signed_quantity >= 0 ? 'mtype--in' : 'mtype--out'">
                    {{ m.type_display }}
                  </span>
                  <span v-if="m.warehouse_to_name" class="muted"> → {{ m.warehouse_to_name }}</span>
                </td>
                <td>
                  <span class="vname">{{ m.product_name }}</span>
                  <code class="sku">{{ m.variant_sku }}</code>
                </td>
                <td>{{ m.warehouse_name }}</td>
                <td class="num" :class="m.signed_quantity >= 0 ? 'pos' : 'neg'">
                  {{ m.signed_quantity > 0 ? '+' : '' }}{{ m.signed_quantity }}
                </td>
                <td class="num">{{ money(m.unit_cost) }}</td>
                <td class="num">{{ m.balance_after }}</td>
              </tr>
              <tr v-if="!movements.length">
                <td colspan="7" class="muted empty">Sin movimientos.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
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

.layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: start;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card-box__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.02rem;
  margin-bottom: 16px;
}
.form-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.form-card .card-box__title {
  margin-bottom: 2px;
}

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
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
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
  padding: 10px 12px;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
  white-space: nowrap;
}
.table td {
  padding: 10px 12px;
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
.mtype {
  font-size: 0.74rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.mtype--in {
  background: #ecfdf5;
  color: #047857;
}
.mtype--out {
  background: #fef2f2;
  color: #b91c1c;
}
.vname {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
}
.sku {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.pos {
  color: #047857;
  font-weight: 600;
}
.neg {
  color: #b91c1c;
  font-weight: 600;
}
.muted {
  color: var(--color-muted);
}
.empty {
  text-align: center;
  padding: 26px;
}
.alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
