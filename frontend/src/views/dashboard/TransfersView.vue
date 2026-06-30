<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Send, Plus, Trash2, Check, X, Store } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import LoadingState from '@/components/LoadingState.vue'
import { warehousesApi, transfersApi, stockLevelsApi } from '@/services/inventory'
import { variantsApi } from '@/services/catalog'
import { useAuthStore } from '@/stores/auth'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'

const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)
const myWarehouseId = computed(() => auth.user?.warehouse ?? null)

const STATUS_OPTIONS = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'aceptada', label: 'Aceptada' },
  { value: 'rechazada', label: 'Rechazada' },
  { value: 'cancelada', label: 'Cancelada' }
]

const warehouses = ref([])
const variantsRaw = ref([])
// Existencias de la bodega ORIGEN seleccionada: { [variantId]: cantidad }.
// Solo se puede transferir lo que el origen tiene (el backend también lo valida).
const originStockMap = ref({})
const transfers = ref([])
const count = ref(0)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const statusFilter = ref('')

// --------------------------- Formulario ---------------------------
const form = ref({ origin: '', destination: '', note: '' })
// Línea en construcción + líneas ya agregadas a la solicitud.
const line = ref({ product: '', variant: '', quantity: 1 })
const lines = ref([])

// Jefe de punto sin bodega asignada: no puede transferir.
const noWarehouse = computed(() => !isAdmin.value && !myWarehouseId.value)

// Existencia de la variante en la bodega origen elegida (no el total global).
function originStock(variantId) {
  return originStockMap.value[variantId] || 0
}

function variantOptionLabel(v) {
  const opts = v.options_label || v.variant_label || ''
  return `${v.sku}${opts ? ` · ${opts}` : ''} · stock ${originStock(v.id)}`
}

// Solo productos con alguna variante en existencia en la bodega origen.
const products = computed(() => {
  const map = new Map()
  for (const v of variantsRaw.value) {
    if (originStock(v.id) <= 0) continue
    if (!map.has(v.product)) map.set(v.product, { id: v.product, label: v.product_name })
  }
  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label))
})

// Solo variantes del producto elegido con existencia en la bodega origen.
const lineVariantOptions = computed(() =>
  line.value.product
    ? variantsRaw.value
        .filter((v) => v.product === line.value.product && originStock(v.id) > 0)
        .map((v) => ({ id: v.id, label: variantOptionLabel(v) }))
    : []
)

// Bodega destino: cualquiera distinta de la origen.
const destinationOptions = computed(() =>
  warehouses.value.filter((w) => w.id !== form.value.origin)
)

watch(() => line.value.product, () => { line.value.variant = '' })
// Al cambiar la bodega origen: carga sus existencias y reinicia las líneas (lo
// agregado pertenecía al origen anterior). También limpia el destino si quedó igual.
watch(() => form.value.origin, (id) => {
  if (form.value.destination === form.value.origin) form.value.destination = ''
  line.value = { product: '', variant: '', quantity: 1 }
  lines.value = []
  loadOriginStock(id)
})

async function loadOriginStock(originId) {
  originStockMap.value = {}
  if (!originId) return
  const data = await stockLevelsApi.list({ warehouse: originId, page_size: 5000 })
  const map = {}
  for (const lvl of data.results) map[lvl.variant] = lvl.quantity
  originStockMap.value = map
}

function variantInfo(id) {
  return variantsRaw.value.find((v) => v.id === id)
}

function addLine() {
  if (!line.value.variant) return toastError('Elige la variante a transferir.')
  if (!line.value.quantity || line.value.quantity <= 0) {
    return toastError('La cantidad debe ser mayor a cero.')
  }
  if (lines.value.some((l) => l.variant === line.value.variant)) {
    return toastError('Esa variante ya está en la transferencia.')
  }
  const available = originStock(line.value.variant)
  if (line.value.quantity > available) {
    return toastError(`Solo hay ${available} unidad(es) en la bodega origen.`)
  }
  const v = variantInfo(line.value.variant)
  lines.value.push({
    variant: line.value.variant,
    quantity: line.value.quantity,
    label: v ? v.product_name : '',
    sku: v ? v.sku : ''
  })
  line.value = { product: '', variant: '', quantity: 1 }
}

function removeLine(i) {
  lines.value.splice(i, 1)
}

const canSubmit = computed(
  () =>
    !noWarehouse.value &&
    form.value.origin &&
    form.value.destination &&
    form.value.origin !== form.value.destination &&
    lines.value.length > 0
)

async function submit() {
  if (!canSubmit.value) return
  const ok = await confirmAction({
    title: 'Solicitar transferencia',
    text: 'La existencia saldrá de la bodega origen y quedará en tránsito hasta que el destino la acepte.',
    confirmText: 'Solicitar'
  })
  if (!ok) return
  saving.value = true
  error.value = ''
  try {
    await transfersApi.create({
      origin: form.value.origin,
      destination: form.value.destination,
      note: form.value.note || '',
      items: lines.value.map((l) => ({ variant: l.variant, quantity: l.quantity }))
    })
    toastSuccess('Transferencia solicitada')
    form.value = { origin: isAdmin.value ? '' : myWarehouseId.value, destination: '', note: '' }
    lines.value = []
    await Promise.all([loadTransfers(), loadVariants(), loadOriginStock(form.value.origin)])
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudo solicitar la transferencia.'
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

// --------------------------- Lista / acciones ---------------------------
function canApprove(t) {
  return t.status === 'pendiente' && (isAdmin.value || myWarehouseId.value === t.destination)
}
function canCancel(t) {
  return t.status === 'pendiente' && (isAdmin.value || myWarehouseId.value === t.origin)
}

async function act(t, kind) {
  const labels = {
    accept: { title: 'Aceptar transferencia', text: 'La existencia entrará a la bodega destino.', confirmText: 'Aceptar', icon: 'question' },
    reject: { title: 'Rechazar transferencia', text: 'La existencia volverá a la bodega origen.', confirmText: 'Rechazar', icon: 'warning' },
    cancel: { title: 'Cancelar transferencia', text: 'La existencia volverá a la bodega origen.', confirmText: 'Cancelar transferencia', icon: 'warning' }
  }[kind]
  const ok = await confirmAction(labels)
  if (!ok) return
  try {
    await transfersApi[kind](t.id)
    toastSuccess('Transferencia actualizada')
    await loadTransfers()
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar la transferencia.')
  }
}

function warehouseName(id) {
  return warehouses.value.find((w) => w.id === id)?.name || '—'
}

function formatDate(d) {
  return new Date(d).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

async function loadVariants() {
  const vs = await variantsApi.list({ page_size: 1000, is_active: true })
  variantsRaw.value = vs.results
}

async function loadTransfers() {
  const params = { page_size: 50 }
  if (statusFilter.value) params.status = statusFilter.value
  const data = await transfersApi.list(params)
  transfers.value = data.results
  count.value = data.count
}

watch(statusFilter, loadTransfers)

onMounted(async () => {
  try {
    const [wh] = await Promise.all([
      warehousesApi.list({ page_size: 200, is_active: true }),
      loadVariants(),
      loadTransfers()
    ])
    warehouses.value = wh.results
    // El jefe de punto transfiere desde su bodega (origen fijo).
    if (!isAdmin.value && myWarehouseId.value) form.value.origin = myWarehouseId.value
  } catch {
    error.value = 'No se pudieron cargar las transferencias.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <h1 class="page__title">Transferencias entre puntos</h1>
      <p class="page__subtitle">
        Solicita un traslado; la existencia sale de origen y entra al destino cuando su jefe la acepta.
      </p>
    </header>

    <p v-if="error && !loading" class="alert">{{ error }}</p>
    <LoadingState v-if="loading" label="Cargando transferencias…" />

    <div v-else class="layout">
      <!-- Solicitar transferencia -->
      <section class="card-box form-card">
        <h2 class="card-box__title"><Send :size="18" /> Nueva transferencia</h2>

        <div v-if="noWarehouse" class="blocked">
          <Store :size="28" />
          <p>No tienes una bodega asignada.</p>
          <span>Pide a un administrador que te asigne una para poder transferir.</span>
        </div>

        <template v-else>
          <div class="field-row">
            <label class="field">
              <span class="field__label">Bodega origen *</span>
              <SearchSelect
                v-if="isAdmin"
                v-model="form.origin"
                :options="warehouses"
                placeholder="Selecciona…"
              />
              <span v-else class="fixed-wh"><Store :size="14" /> {{ warehouseName(myWarehouseId) }}</span>
            </label>
            <label class="field">
              <span class="field__label">Bodega destino *</span>
              <SearchSelect
                v-model="form.destination"
                :options="destinationOptions"
                :disabled="!form.origin"
                placeholder="Selecciona…"
              />
            </label>
          </div>

          <!-- Constructor de líneas -->
          <div class="line-builder">
            <span class="field__label">Productos a transferir *</span>
            <SearchSelect
              v-model="line.product"
              :options="products"
              value-key="id"
              label-key="label"
              :disabled="!form.origin"
              :placeholder="form.origin ? 'Busca el producto' : 'Primero elige la bodega origen'"
            />
            <SearchSelect
              v-model="line.variant"
              :options="lineVariantOptions"
              value-key="id"
              label-key="label"
              :disabled="!line.product"
              :placeholder="line.product ? 'Selecciona la variante' : 'Primero elige el producto'"
            />
            <div class="line-add">
              <input v-model.number="line.quantity" type="number" min="1" class="field__input" placeholder="Cant." />
              <button type="button" class="btn btn--ghost btn--sm" :disabled="!line.variant" @click="addLine">
                <Plus :size="15" /> Agregar
              </button>
            </div>
          </div>

          <ul v-if="lines.length" class="lines">
            <li v-for="(l, i) in lines" :key="l.variant" class="lines__row">
              <span class="lines__name">{{ l.label }} <code>{{ l.sku }}</code></span>
              <span class="lines__qty">× {{ l.quantity }}</span>
              <button type="button" class="icon-btn icon-btn--danger" @click="removeLine(i)"><Trash2 :size="14" /></button>
            </li>
          </ul>
          <p v-else class="lines-empty">Aún no agregas productos.</p>

          <label class="field">
            <span class="field__label">Nota</span>
            <input v-model="form.note" class="field__input" maxlength="255" placeholder="Opcional" />
          </label>

          <button class="btn btn--primary btn--block" :disabled="saving || !canSubmit" @click="submit">
            {{ saving ? 'Solicitando…' : 'Solicitar transferencia' }}
          </button>
        </template>
      </section>

      <!-- Lista -->
      <section class="card-box list-card">
        <div class="list-head">
          <h2 class="card-box__title">Transferencias <span class="muted">({{ count }})</span></h2>
          <div class="list-filter">
            <SearchSelect
              v-model="statusFilter"
              :options="STATUS_OPTIONS"
              value-key="value"
              label-key="label"
              clearable
              clear-label="Todos los estados"
              placeholder="Todos los estados"
            />
          </div>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Ruta</th>
                <th>Productos</th>
                <th>Estado</th>
                <th>Solicitud</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in transfers" :key="t.id">
                <td class="nowrap">#{{ t.number }}</td>
                <td class="nowrap">
                  {{ t.origin_name }} <span class="muted">→</span> {{ t.destination_name }}
                </td>
                <td>
                  <ul class="items">
                    <li v-for="it in t.items" :key="it.id">
                      <span class="items__name">{{ it.product_name }}</span>
                      <code class="sku">{{ it.variant_sku }}</code>
                      <span class="items__qty">× {{ it.quantity }}</span>
                    </li>
                  </ul>
                </td>
                <td>
                  <span class="badge" :class="`badge--${t.status}`">{{ t.status_display }}</span>
                </td>
                <td class="nowrap">
                  <span class="who">{{ t.requested_by_name || '—' }}</span>
                  <span class="when">{{ formatDate(t.created_at) }}</span>
                </td>
                <td class="actions" @click.stop>
                  <template v-if="canApprove(t)">
                    <button class="icon-btn icon-btn--ok" title="Aceptar" @click="act(t, 'accept')"><Check :size="15" /></button>
                    <button class="icon-btn icon-btn--danger" title="Rechazar" @click="act(t, 'reject')"><X :size="15" /></button>
                  </template>
                  <button
                    v-if="canCancel(t)"
                    class="icon-btn"
                    title="Cancelar"
                    @click="act(t, 'cancel')"
                  >
                    <Trash2 :size="14" />
                  </button>
                </td>
              </tr>
              <tr v-if="!transfers.length">
                <td colspan="6" class="muted empty">No hay transferencias.</td>
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
  grid-template-columns: 360px 1fr;
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
.fixed-wh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  font-weight: 600;
  color: var(--color-ink);
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}

.line-builder {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
}
.line-add {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lines__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--color-surface-alt);
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
}
.lines__name {
  flex: 1;
  font-weight: 600;
  color: var(--color-ink);
}
.lines__name code {
  font-weight: 400;
  color: var(--color-muted);
}
.lines__qty {
  font-weight: 700;
}
.lines-empty {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.blocked {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 30px 12px;
  text-align: center;
  color: var(--color-muted);
}
.blocked p {
  font-weight: 600;
  color: var(--color-ink);
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.list-filter {
  width: 220px;
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
  vertical-align: top;
}
.nowrap {
  white-space: nowrap;
}
.items {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.items__name {
  font-weight: 600;
  color: var(--color-ink);
}
.items__qty {
  font-weight: 700;
}
.sku {
  font-size: 0.78rem;
  color: var(--color-muted);
  margin: 0 6px;
}
.who {
  display: block;
  color: var(--color-ink);
}
.when {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.badge--pendiente {
  background: #fef3c7;
  color: #b45309;
}
.badge--aceptada {
  background: #ecfdf5;
  color: #047857;
}
.badge--rechazada {
  background: #fef2f2;
  color: #b91c1c;
}
.badge--cancelada {
  background: var(--color-surface-alt);
  color: var(--color-body);
}
.actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  transition: all 0.16s ease;
}
.icon-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.icon-btn--ok {
  color: var(--color-success);
  border-color: #a7f3d0;
}
.icon-btn--ok:hover {
  background: #ecfdf5;
}
.icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
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
  margin-bottom: 14px;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
