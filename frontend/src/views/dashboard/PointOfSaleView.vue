<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus, Minus, Trash2, ShoppingCart, X, Store } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import LoadingState from '@/components/LoadingState.vue'
import { variantsApi } from '@/services/catalog'
import { warehousesApi, stockLevelsApi } from '@/services/inventory'
import { customersApi, salesApi } from '@/services/sales'
import { useAuthStore } from '@/stores/auth'
import { toastSuccess, toastError, confirmAction } from '@/utils/notify'

const router = useRouter()
const auth = useAuthStore()

// El admin elige la bodega; el cajero/jefe de punto vende SIEMPRE en la suya.
const isAdmin = computed(() => auth.isAdmin)
const assignedWarehouseId = computed(() => auth.user?.warehouse ?? null)
const assignedWarehouseName = computed(() => auth.user?.warehouse_name || '')
// Staff no-admin sin bodega asignada: no puede vender.
const noWarehouse = computed(() => !isAdmin.value && !assignedWarehouseId.value)

const PAYMENT_OPTIONS = [
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'otro', label: 'Otro' }
]

const loading = ref(true)
const saving = ref(false)
const warehouses = ref([])
const variants = ref([])
const customers = ref([])
// Existencia de cada variante en la bodega activa: { [variantId]: cantidad }.
const stockMap = ref({})

const warehouse = ref('')
const customer = ref('')
const receiptEmail = ref('')
const query = ref('')
const cart = ref([])
const discountInput = ref('')
const discountType = ref('amount') // 'amount' | 'percent'
const payments = ref([{ method: 'efectivo', amount: '' }])

function money(v) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(v || 0)
}

// Existencia de la variante en la bodega activa (no el total entre bodegas).
function stockFor(v) {
  return stockMap.value[v.id] || 0
}

// Carga las existencias de la bodega activa y arma el mapa variante→cantidad.
async function loadStock(whId) {
  stockMap.value = {}
  if (!whId) return
  const data = await stockLevelsApi.list({ warehouse: whId, page_size: 5000 })
  const map = {}
  for (const lvl of data.results) map[lvl.variant] = lvl.quantity
  stockMap.value = map
}

// --------------------------- Búsqueda ---------------------------
const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  return variants.value
    .filter((v) =>
      [v.product_name, v.sku, v.barcode].filter(Boolean).join(' ').toLowerCase().includes(q)
    )
    .slice(0, 8)
})

function variantLabel(v) {
  const opts = v.options_label || ''
  return v.product_name + (opts ? ` — ${opts}` : '')
}

// --------------------------- Carrito ---------------------------
function addToCart(v) {
  const available = stockFor(v)
  if (available <= 0) {
    toastError('Sin existencia en esta bodega.')
    return
  }
  const existing = cart.value.find((c) => c.id === v.id)
  if (existing) {
    if (existing.quantity < available) existing.quantity++
    else toastError('No hay más existencia de ese producto.')
  } else {
    cart.value.push({
      id: v.id,
      label: variantLabel(v),
      sku: v.sku,
      unit_price: Number(v.sale_price),
      tax_rate: v.tax_rate || 0,
      stock: available,
      quantity: 1
    })
  }
  query.value = ''
}

function changeQty(item, delta) {
  const next = item.quantity + delta
  if (next < 1) return
  if (next > item.stock) {
    toastError('Cantidad supera la existencia.')
    return
  }
  item.quantity = next
}

function removeItem(item) {
  cart.value = cart.value.filter((c) => c !== item)
}

// --------------------------- Totales ---------------------------
const gross = computed(() => cart.value.reduce((s, c) => s + c.unit_price * c.quantity, 0))
const taxTotal = computed(() =>
  cart.value.reduce((s, c) => {
    const line = c.unit_price * c.quantity
    return s + (line - line / (1 + c.tax_rate / 100))
  }, 0)
)
const subtotal = computed(() => gross.value - taxTotal.value)
const discountAmount = computed(() => {
  const n = Number(discountInput.value) || 0
  const amt = discountType.value === 'percent' ? (gross.value * n) / 100 : n
  return Math.min(Math.max(amt, 0), gross.value)
})
const total = computed(() => gross.value - discountAmount.value)
const paid = computed(() => payments.value.reduce((s, p) => s + (Number(p.amount) || 0), 0))
const change = computed(() => Math.max(0, paid.value - total.value))

// --------------------------- Pagos ---------------------------
function addPayment() {
  payments.value.push({ method: 'tarjeta', amount: '' })
}
function removePayment(i) {
  payments.value.splice(i, 1)
}
// Rellena el primer pago con el total pendiente (atajo).
function fillFirstPayment() {
  if (payments.value.length) payments.value[0].amount = total.value
}

// Opciones del selector de cliente: la búsqueda es por número de identificación
// (también encuentra por nombre). Etiqueta: "1234567 · Juan Pérez".
const customerOptions = computed(() =>
  customers.value.map((c) => ({
    id: c.id,
    label: `${c.id_number || 'Sin ID'} · ${c.full_name}`
  }))
)

function onCustomerChange(id) {
  const c = customers.value.find((x) => x.id === id)
  if (c?.email && !receiptEmail.value) receiptEmail.value = c.email
}

const canCheckout = computed(
  () => cart.value.length && warehouse.value && paid.value >= total.value && total.value > 0
)

async function checkout() {
  if (!canCheckout.value) return
  const ok = await confirmAction({
    title: 'Cobrar venta',
    text: `Total a cobrar: ${money(total.value)}. ¿Confirmas la venta?`,
    confirmText: 'Cobrar'
  })
  if (!ok) return
  saving.value = true
  try {
    const sale = await salesApi.create({
      warehouse: warehouse.value,
      customer: customer.value || null,
      discount: discountAmount.value,
      receipt_email: receiptEmail.value || '',
      items: cart.value.map((c) => ({ variant: c.id, quantity: c.quantity })),
      payments: payments.value
        .filter((p) => Number(p.amount) > 0)
        .map((p) => ({ method: p.method, amount: Number(p.amount) }))
    })
    toastSuccess(`Venta #${sale.number} registrada`)
    router.push({ name: 'sale-detail', params: { id: sale.id } })
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo registrar la venta.')
  } finally {
    saving.value = false
  }
}

// Al cambiar de bodega (solo el admin puede): recarga existencias y vacía el
// carrito (las cantidades disponibles cambian de una bodega a otra).
watch(warehouse, (id) => {
  cart.value = []
  loadStock(id)
})

onMounted(async () => {
  try {
    const [vs, cs] = await Promise.all([
      variantsApi.list({ page_size: 1000, is_active: true }),
      customersApi.list({ page_size: 500, is_active: true })
    ])
    variants.value = vs.results
    customers.value = cs.results

    if (isAdmin.value) {
      const wh = await warehousesApi.list({ page_size: 200, is_active: true })
      warehouses.value = wh.results
      if (warehouses.value.length) warehouse.value = warehouses.value[0].id
    } else if (assignedWarehouseId.value) {
      // Cajero / jefe de punto: fijo a su bodega asignada.
      warehouse.value = assignedWarehouseId.value
    }
    // Asignar `warehouse` dispara el watch, que carga las existencias.
  } catch {
    toastError('No se pudo cargar el POS.')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Punto de venta</h1>
        <p class="page__subtitle">Busca productos, arma la venta y cobra.</p>
      </div>
      <div class="head-wh">
        <span class="head-wh__label">Bodega</span>
        <SearchSelect
          v-if="isAdmin"
          v-model="warehouse"
          :options="warehouses"
          placeholder="Bodega"
        />
        <span v-else class="head-wh__fixed">
          <Store :size="15" /> {{ assignedWarehouseName || 'Sin asignar' }}
        </span>
      </div>
    </header>

    <LoadingState v-if="loading" label="Cargando punto de venta…" />

    <div v-else-if="noWarehouse" class="pos-blocked">
      <Store :size="34" />
      <p>No tienes una bodega asignada.</p>
      <span>Pídele a un administrador que te asigne una para poder vender.</span>
    </div>

    <div v-else class="pos">
      <!-- Productos + carrito -->
      <section class="pos__main">
        <div class="search">
          <Search :size="18" class="search__icon" />
          <input
            v-model="query"
            class="search__input"
            type="search"
            placeholder="Buscar producto por nombre, SKU o código…"
          />
          <ul v-if="results.length" class="search__results">
            <li v-for="v in results" :key="v.id">
              <button type="button" class="result" :disabled="stockFor(v) <= 0" @click="addToCart(v)">
                <span class="result__name">{{ variantLabel(v) }}</span>
                <span class="result__meta">
                  <code class="result__sku">{{ v.sku }}</code>
                  <span :class="{ 'result__stock--out': stockFor(v) <= 0 }">stock {{ stockFor(v) }}</span>
                  <strong>{{ money(v.sale_price) }}</strong>
                </span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="!cart.length" class="cart-empty">
          <ShoppingCart :size="34" />
          <p>El carrito está vacío. Busca productos para agregarlos.</p>
        </div>

        <table v-else class="cart">
          <thead>
            <tr>
              <th>Producto</th>
              <th class="num">Precio</th>
              <th class="center">Cantidad</th>
              <th class="num">Subtotal</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in cart" :key="item.id">
              <td>
                <span class="cart__name">{{ item.label }}</span>
                <code class="cart__sku">{{ item.sku }}</code>
              </td>
              <td class="num">{{ money(item.unit_price) }}</td>
              <td class="center">
                <div class="qty">
                  <button type="button" class="qty__btn" @click="changeQty(item, -1)"><Minus :size="14" /></button>
                  <span class="qty__val">{{ item.quantity }}</span>
                  <button type="button" class="qty__btn" @click="changeQty(item, 1)"><Plus :size="14" /></button>
                </div>
              </td>
              <td class="num strong">{{ money(item.unit_price * item.quantity) }}</td>
              <td>
                <button type="button" class="icon-btn icon-btn--danger" @click="removeItem(item)">
                  <Trash2 :size="15" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Resumen / cobro -->
      <aside class="pos__side">
        <div class="card-box">
          <label class="field">
            <span class="field__label">Cliente (opcional)</span>
            <SearchSelect
              v-model="customer"
              :options="customerOptions"
              value-key="id"
              label-key="label"
              clearable
              clear-label="Sin cliente"
              placeholder="Buscar por identificación…"
              @update:model-value="onCustomerChange"
            />
          </label>
          <label class="field">
            <span class="field__label">Correo para el recibo (opcional)</span>
            <input v-model="receiptEmail" type="email" class="field__input" placeholder="correo@ejemplo.com" />
          </label>
        </div>

        <div class="card-box">
          <div class="field">
            <span class="field__label">Descuento</span>
            <div class="disc">
              <MoneyInput v-if="discountType === 'amount'" v-model="discountInput" />
              <input v-else v-model="discountInput" type="number" min="0" class="field__input" placeholder="0" />
              <div class="disc__toggle">
                <button type="button" :class="{ active: discountType === 'amount' }" @click="discountType = 'amount'">$</button>
                <button type="button" :class="{ active: discountType === 'percent' }" @click="discountType = 'percent'">%</button>
              </div>
            </div>
          </div>

          <div class="totals">
            <div class="totals__row"><span>Subtotal</span><span>{{ money(subtotal) }}</span></div>
            <div class="totals__row"><span>IVA</span><span>{{ money(taxTotal) }}</span></div>
            <div v-if="discountAmount" class="totals__row"><span>Descuento</span><span>-{{ money(discountAmount) }}</span></div>
            <div class="totals__row totals__row--total"><span>Total</span><span>{{ money(total) }}</span></div>
          </div>
        </div>

        <div class="card-box">
          <div class="pay-head">
            <span class="field__label">Pagos</span>
            <button type="button" class="link-btn" @click="fillFirstPayment">Exacto</button>
          </div>
          <div v-for="(p, i) in payments" :key="i" class="pay-row">
            <SearchSelect v-model="p.method" :options="PAYMENT_OPTIONS" value-key="value" label-key="label" />
            <MoneyInput v-model="p.amount" />
            <button v-if="payments.length > 1" type="button" class="icon-btn" @click="removePayment(i)"><X :size="14" /></button>
          </div>
          <button type="button" class="btn btn--ghost btn--sm pay-add" @click="addPayment">
            <Plus :size="15" /> Otra forma de pago
          </button>

          <div class="totals">
            <div class="totals__row"><span>Pagado</span><span>{{ money(paid) }}</span></div>
            <div class="totals__row totals__row--change"><span>Cambio</span><span>{{ money(change) }}</span></div>
          </div>
        </div>

        <button class="btn btn--primary btn--block btn--lg" :disabled="!canCheckout || saving" @click="checkout">
          {{ saving ? 'Cobrando…' : `Cobrar ${money(total)}` }}
        </button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}
.head-wh {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 220px;
}
.head-wh__label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}
.head-wh__fixed {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 12px;
  font-weight: 600;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}

.pos-blocked {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 70px 24px;
  text-align: center;
  color: var(--color-muted);
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
}
.pos-blocked p {
  font-weight: 600;
  color: var(--color-ink);
}

.pos {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 20px;
  align-items: start;
}
.pos__main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pos__side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 16px;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Búsqueda */
.search {
  position: relative;
}
.search__icon {
  position: absolute;
  left: 14px;
  top: 16px;
  color: var(--color-muted);
}
.search__input {
  width: 100%;
  padding: 14px 14px 14px 42px;
  font-family: inherit;
  font-size: 1rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: #fff;
}
.search__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.search__results {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.result {
  width: 100%;
  text-align: left;
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-surface-alt);
  cursor: pointer;
}
.result:hover:not(:disabled) {
  background: var(--color-surface-alt);
}
.result:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.result__name {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
}
.result__meta {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 0.82rem;
  color: var(--color-muted);
  margin-top: 2px;
}
.result__sku {
  background: var(--color-surface-alt);
  padding: 1px 6px;
  border-radius: 5px;
}
.result__stock--out {
  color: #dc2626;
}

/* Carrito */
.cart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 60px 24px;
  color: var(--color-muted);
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
}
.cart {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow: hidden;
  font-size: 0.9rem;
}
.cart th {
  text-align: left;
  padding: 11px 14px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
}
.cart td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.cart .num {
  text-align: right;
  white-space: nowrap;
}
.cart .center {
  text-align: center;
}
.cart__name {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
}
.cart__sku {
  font-size: 0.76rem;
  color: var(--color-muted);
}
.strong {
  font-weight: 700;
}
.qty {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.qty__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
}
.qty__btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.qty__val {
  min-width: 24px;
  text-align: center;
  font-weight: 600;
}

/* Campos */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-ink);
}
.field__input {
  width: 100%;
  padding: 10px 12px;
  font-family: inherit;
  font-size: 0.92rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.disc {
  display: flex;
  gap: 8px;
}
.disc > :first-child {
  flex: 1;
}
.disc__toggle {
  display: inline-flex;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.disc__toggle button {
  width: 36px;
  cursor: pointer;
  background: #fff;
  font-weight: 700;
  color: var(--color-muted);
}
.disc__toggle button.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.totals {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.totals__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--color-body);
}
.totals__row--total {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-ink);
  padding-top: 8px;
  border-top: 1px solid var(--color-line);
}
.totals__row--change {
  font-weight: 600;
  color: var(--color-success);
}

.pay-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.link-btn {
  font-size: 0.8rem;
  color: var(--color-primary);
  cursor: pointer;
  background: none;
}
.pay-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  align-items: center;
}
.pay-add {
  align-self: flex-start;
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
}
.icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}

@media (max-width: 960px) {
  .pos {
    grid-template-columns: 1fr;
  }
  .pos__side {
    position: static;
  }
}
</style>
