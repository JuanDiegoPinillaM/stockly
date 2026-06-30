<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search,
  Plus,
  Minus,
  Trash2,
  ShoppingCart,
  X,
  Store,
  UserPlus,
  Package,
  LayoutGrid,
  Maximize2,
  Minimize2,
  Delete,
  ArrowLeft,
  Check,
  Tag
} from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import LoadingState from '@/components/LoadingState.vue'
import { productsApi, categoriesApi } from '@/services/catalog'
import { warehousesApi, stockLevelsApi } from '@/services/inventory'
import { customersApi, salesApi } from '@/services/sales'
import { ID_TYPES } from '@/utils/identification'
import { useAuthStore } from '@/stores/auth'
import { toastSuccess, toastError } from '@/utils/notify'

const router = useRouter()
const auth = useAuthStore()

// El admin elige la bodega; el cajero/jefe de punto vende SIEMPRE en la suya.
const isAdmin = computed(() => auth.isAdmin)
const assignedWarehouseId = computed(() => auth.user?.warehouse ?? null)
const assignedWarehouseName = computed(() => auth.user?.warehouse_name || '')
const noWarehouse = computed(() => !isAdmin.value && !assignedWarehouseId.value)

const PAYMENT_OPTIONS = [
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'otro', label: 'Otro' }
]
// Montos rápidos en efectivo (billetes comunes en COP).
const QUICK_CASH = [5000, 10000, 20000, 50000, 100000]
// Paleta estable para el "icono" de cada categoría (color + inicial).
const CAT_COLORS = [
  '#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16'
]

const loading = ref(true)
const saving = ref(false)
const products = ref([])
const categories = ref([])
const customers = ref([])
const warehouses = ref([])
// Existencia de cada variante en la bodega activa: { [variantId]: cantidad }.
const stockMap = ref({})

const warehouse = ref('')
const customer = ref('')
const receiptEmail = ref('')
const query = ref('')
const activeCategory = ref('all')
const cart = ref([])
const discountInput = ref('')
const discountType = ref('amount') // 'amount' | 'percent'

function money(v) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(v || 0)
}

// ------------------------- Existencias por bodega -------------------------
function variantStock(v) {
  return stockMap.value[v.id] || 0
}
async function loadStock(whId) {
  stockMap.value = {}
  if (!whId) return
  const data = await stockLevelsApi.list({ warehouse: whId, page_size: 5000 })
  const map = {}
  for (const lvl of data.results) map[lvl.variant] = lvl.quantity
  stockMap.value = map
}

// --------------------------- Catálogo / grid ---------------------------
// Patrón estándar de POS para catálogos con muchas variantes (NN/g, Odoo POS,
// Loyverse): UNA TARJETA POR PRODUCTO con el stock total de la bodega y unos
// swatches que insinúan los colores (los agotados se atenúan). La elección de
// la variante concreta ocurre en el configurador (al tocar), donde se ve el
// stock por combinación. Así escala a cualquier nº de atributos/categorías.

// Eje visual (color) del producto, si lo tiene.
function imageAxis(p) {
  return (p.attributes || []).find((a) => a.is_image_axis) || null
}
// Variantes activas del producto que incluyen cierto valor (color).
function variantsForValue(p, valueId) {
  return (p.variants || []).filter(
    (v) => v.is_active && (v.values || []).some((x) => x.value === valueId)
  )
}
// Foto asociada a un valor del eje visual (o la portada del producto).
function imageForValue(p, valueId) {
  const img = (p.images || []).find((i) => i.value === valueId)
  return img?.image || p.main_image || null
}
// Arma la tarjeta de un producto: foto, precio, stock total y swatches de color.
function makeProductCard(p) {
  const actives = (p.variants || []).filter((v) => v.is_active)
  // El precio ("Desde") refleja solo lo DISPONIBLE en la bodega; si todo está
  // agotado, cae al rango de las activas (la tarjeta igual se marca Agotado).
  const sellable = actives.filter((v) => variantStock(v) > 0)
  const priced = sellable.length ? sellable : actives
  const prices = priced.map((v) => Number(v.sale_price))
  const axis = imageAxis(p)
  const swatches = axis
    ? axis.values
        .map((val) => {
          const vs = variantsForValue(p, val.id)
          if (!vs.length) return null
          return {
            id: val.id,
            label: val.value,
            hex: val.swatch_hex || '#cccccc',
            available: vs.some((v) => variantStock(v) > 0),
            image: imageForValue(p, val.id)
          }
        })
        .filter(Boolean)
    : []
  return {
    product: p,
    name: p.name,
    image: p.main_image,
    stock: actives.reduce((s, v) => s + variantStock(v), 0),
    priceMin: prices.length ? Math.min(...prices) : 0,
    priceMax: prices.length ? Math.max(...prices) : 0,
    swatches
  }
}

// Categorías que realmente tienen productos, con su conteo (para el panel izq.).
const categoryTabs = computed(() => {
  const counts = {}
  for (const p of products.value) {
    if (p.category != null) counts[p.category] = (counts[p.category] || 0) + 1
  }
  const tabs = categories.value
    .filter((c) => counts[c.id])
    .map((c) => ({ id: c.id, name: c.name, count: counts[c.id] }))
  return tabs
})

function catColor(id) {
  return CAT_COLORS[Math.abs(Number(id) || 0) % CAT_COLORS.length]
}

const cards = computed(() => {
  const q = query.value.trim().toLowerCase()
  let list = products.value.filter(
    (p) => activeCategory.value === 'all' || p.category === activeCategory.value
  )
  if (q) {
    list = list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.variants || []).some(
          (v) =>
            (v.sku && v.sku.toLowerCase().includes(q)) ||
            (v.barcode && v.barcode.toLowerCase().includes(q)) ||
            (v.options_label && v.options_label.toLowerCase().includes(q))
        )
    )
  }
  return list.map(makeProductCard)
})

// Previsualización de color en la tarjeta: productId -> valueId del color tocado.
// Al tocar un punto de color se cambia la foto de la tarjeta a la de ese color.
const cardPreview = ref({})
function cardImage(c) {
  const vid = cardPreview.value[c.product.id]
  if (vid) {
    const s = c.swatches.find((x) => x.id === vid)
    if (s?.image) return s.image
  }
  return c.image
}
function previewColor(c, s) {
  // Volver a tocar el mismo color quita la previsualización.
  const next = { ...cardPreview.value }
  if (next[c.product.id] === s.id) delete next[c.product.id]
  else next[c.product.id] = s.id
  cardPreview.value = next
}

// --------------------------- Carrito ---------------------------
function addVariant(v, product, qty = 1) {
  const available = variantStock(v)
  if (available <= 0) {
    toastError('Sin existencia en esta bodega.')
    return
  }
  const existing = cart.value.find((c) => c.id === v.id)
  if (existing) {
    existing.quantity = Math.min(existing.quantity + qty, available)
    if (existing.quantity === available && qty > available) {
      toastError('No hay más existencia de ese producto.')
    }
  } else {
    cart.value.push({
      id: v.id,
      name: product.name,
      options: v.options_label || '',
      sku: v.sku,
      image: v.main_image || product.main_image || null,
      unit_price: Number(v.sale_price),
      tax_rate: v.tax_rate || product.tax_rate || 0,
      stock: available,
      quantity: Math.min(qty, available)
    })
  }
}

function onCardClick(card) {
  const p = card.product
  if (card.stock <= 0) {
    toastError('Producto agotado en esta bodega.')
    return
  }
  // Producto simple (sin atributos) → una sola variante, al carrito directo.
  if (!(p.attributes || []).length) {
    const variant = (p.variants || []).find((v) => v.is_active && variantStock(v) > 0)
    if (!variant) {
      toastError('Agotado en esta bodega.')
      return
    }
    addVariant(variant, p)
    flashCard(p.id)
    return
  }
  // Con atributos → configurador para elegir la variante y ver su stock.
  openPicker(p)
}

// Pequeño feedback visual al agregar desde una tarjeta.
const flashedCard = ref(null)
let flashTimer = null
function flashCard(key) {
  flashedCard.value = key
  clearTimeout(flashTimer)
  flashTimer = setTimeout(() => (flashedCard.value = null), 450)
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
function clearCart() {
  cart.value = []
}

// --------------------------- Selección de variante ---------------------------
const pickerProduct = ref(null)
const pickerSelection = ref({})
const pickerQty = ref(1)

const pickerAttributes = computed(() => pickerProduct.value?.attributes || [])
const pickerVariants = computed(() =>
  (pickerProduct.value?.variants || [])
    .filter((v) => v.is_active)
    .map((v) => ({ ...v, value_ids: (v.values || []).map((x) => x.value) }))
)
// El eje visual (color) manda primero en la cascada.
const pickerOrdered = computed(() =>
  [...pickerAttributes.value].sort(
    (a, b) => (b.is_image_axis === true) - (a.is_image_axis === true)
  )
)
// Último atributo de la cascada: el que define la variante. El stock por opción
// solo se muestra ahí (si no, el mismo número aparecería en cada atributo).
const lastPickerAttrId = computed(() => {
  const o = pickerOrdered.value
  return o.length ? o[o.length - 1].id : null
})

function openPicker(p) {
  pickerProduct.value = p
  pickerSelection.value = {}
  pickerQty.value = 1
  // Preselecciona los atributos que solo tienen un valor posible.
  for (const a of p.attributes || []) {
    if (a.values.length === 1) pickerSelection.value[a.id] = a.values[0].id
  }
}
function closePicker() {
  pickerProduct.value = null
}

function variantMatches(v, sel) {
  const ids = v.value_ids || []
  const selVals = Object.values(sel)
  return (
    selVals.length === pickerAttributes.value.length &&
    selVals.every((vid) => ids.includes(vid))
  )
}
const pickerSelected = computed(() => {
  if (!pickerAttributes.value.length) return pickerVariants.value[0] || null
  return pickerVariants.value.find((v) => variantMatches(v, pickerSelection.value)) || null
})
const pickerSelectedStock = computed(() =>
  pickerSelected.value ? variantStock(pickerSelected.value) : 0
)
// Foto del configurador: la del color elegido en el eje visual; si no, la portada.
const pickerImage = computed(() => {
  const p = pickerProduct.value
  if (!p) return null
  const axis = imageAxis(p)
  const selColorId = axis ? pickerSelection.value[axis.id] : null
  return selColorId ? imageForValue(p, selColorId) : p.main_image || null
})

// Un valor se deshabilita si, respetando los atributos anteriores en la cascada,
// ninguna variante con stock en la bodega lo incluye.
function valueDisabled(attrId, valueId) {
  const order = pickerOrdered.value
  const idx = order.findIndex((a) => a.id === attrId)
  return !pickerVariants.value.some((v) => {
    if (variantStock(v) <= 0) return false
    const ids = v.value_ids || []
    if (!ids.includes(valueId)) return false
    return order.every((a, i) => i >= idx || ids.includes(pickerSelection.value[a.id]))
  })
}
function valueSelected(attrId, valueId) {
  return pickerSelection.value[attrId] === valueId
}
// Stock exacto de la variante que resultaría de elegir este valor, SOLO cuando
// los demás atributos ya están elegidos (si no, null y no se muestra número).
// Así en un producto de un eje (p. ej. almacenamiento) cada opción ya trae su
// stock; en dos ejes, las tallas muestran su stock una vez elegido el color.
function optionStock(attrId, valueId) {
  const others = pickerAttributes.value.filter((a) => a.id !== attrId)
  if (!others.every((a) => pickerSelection.value[a.id])) return null
  const sel = { ...pickerSelection.value, [attrId]: valueId }
  const variant = pickerVariants.value.find((v) => variantMatches(v, sel))
  return variant ? variantStock(variant) : 0
}
function selectValue(attrId, valueId) {
  if (valueDisabled(attrId, valueId)) return
  const order = pickerOrdered.value
  const idx = order.findIndex((a) => a.id === attrId)
  const fixed = { [attrId]: valueId }
  order.forEach((a, i) => {
    if (i < idx) fixed[a.id] = pickerSelection.value[a.id]
  })
  // Candidatas que respetan lo ya fijado; reconstruye la selección posterior.
  const candidates = pickerVariants.value.filter(
    (v) =>
      variantStock(v) > 0 &&
      Object.values(fixed).every((vid) => (v.value_ids || []).includes(vid))
  )
  const next = { ...fixed }
  order.forEach((a, i) => {
    if (i <= idx) return
    const prev = pickerSelection.value[a.id]
    const stillOk = prev && candidates.some((v) => (v.value_ids || []).includes(prev))
    if (stillOk) next[a.id] = prev
  })
  pickerSelection.value = next
}
function pickerQtyChange(delta) {
  const next = pickerQty.value + delta
  if (next < 1) return
  if (next > pickerSelectedStock.value) return
  pickerQty.value = next
}
function confirmPicker() {
  if (!pickerSelected.value || pickerSelectedStock.value <= 0) return
  addVariant(pickerSelected.value, pickerProduct.value, pickerQty.value)
  closePicker()
}

// --------------------------- Totales ---------------------------
const gross = computed(() => cart.value.reduce((s, c) => s + c.unit_price * c.quantity, 0))
// IVA contenido en el bruto (antes del descuento).
const grossTax = computed(() =>
  cart.value.reduce((s, c) => {
    const line = c.unit_price * c.quantity
    return s + (line - line / (1 + c.tax_rate / 100))
  }, 0)
)
const discountAmount = computed(() => {
  const n = Number(discountInput.value) || 0
  const amt = discountType.value === 'percent' ? (gross.value * n) / 100 : n
  return Math.min(Math.max(amt, 0), gross.value)
})
const total = computed(() => gross.value - discountAmount.value)
// El descuento reduce la base gravable: el IVA se recalcula a prorrata sobre el
// neto. Así el desglose cuadra siempre (subtotal + IVA = total = bruto − dcto).
const taxTotal = computed(() =>
  gross.value > 0 ? grossTax.value * (total.value / gross.value) : 0
)
const subtotal = computed(() => total.value - taxTotal.value)
const totalItems = computed(() => cart.value.reduce((s, c) => s + c.quantity, 0))

// --------------------------- Cliente ---------------------------
const customerOptions = computed(() =>
  customers.value.map((c) => ({
    id: c.id,
    label: `${c.id_number || 'Sin ID'} · ${c.full_name}`
  }))
)
const selectedCustomer = computed(
  () => customers.value.find((c) => c.id === customer.value) || null
)
// Cliente genérico de mostrador ("Consumidor final") para ventas sin datos.
const walkInCustomer = computed(() => customers.value.find((c) => c.is_walk_in) || null)
function useWalkIn() {
  if (!walkInCustomer.value) return
  customer.value = walkInCustomer.value.id
  receiptEmail.value = ''
}
function onCustomerChange(id) {
  const c = customers.value.find((x) => x.id === id)
  receiptEmail.value = c?.email || ''
}

// Crear cliente rápido (modal).
const newCustomerOpen = ref(false)
const creatingCustomer = ref(false)
const newCustomerErrors = ref({})
const newCustomer = ref({ id_type: 'CC', id_number: '', first_name: '', last_name: '', email: '', phone: '' })
const canCreateCustomer = computed(
  () => newCustomer.value.id_number.trim() && newCustomer.value.first_name.trim()
)
function openNewCustomer() {
  newCustomer.value = { id_type: 'CC', id_number: '', first_name: '', last_name: '', email: '', phone: '' }
  newCustomerErrors.value = {}
  newCustomerOpen.value = true
}
async function saveNewCustomer() {
  if (!canCreateCustomer.value || creatingCustomer.value) return
  creatingCustomer.value = true
  newCustomerErrors.value = {}
  try {
    const created = await customersApi.create({ ...newCustomer.value })
    customers.value.unshift(created)
    customer.value = created.id
    onCustomerChange(created.id)
    newCustomerOpen.value = false
    toastSuccess(`Cliente ${created.full_name} creado`)
  } catch (e) {
    const data = e.response?.data
    newCustomerErrors.value = data?.errors || {}
    if (!data?.errors) toastError(data?.detail || 'No se pudo crear el cliente.')
  } finally {
    creatingCustomer.value = false
  }
}

// --------------------------- Cobro (pantalla con teclado) ---------------------------
const payOpen = ref(false)
const payments = ref([{ method: 'efectivo', amount: 0 }])
const activePay = ref(0)

const paid = computed(() => payments.value.reduce((s, p) => s + (Number(p.amount) || 0), 0))
const remaining = computed(() => Math.max(0, total.value - paid.value))
// El cambio SOLO sale del efectivo: no se devuelve dinero de una tarjeta o
// transferencia (son montos exactos). Es el sobrante de efectivo una vez que
// los pagos no-efectivo cubrieron su parte.
const change = computed(() => {
  const cash = payments.value
    .filter((p) => p.method === 'efectivo')
    .reduce((s, p) => s + (Number(p.amount) || 0), 0)
  const nonCash = paid.value - cash
  return Math.max(0, cash - Math.max(0, total.value - nonCash))
})
const activeIsCash = computed(() => payments.value[activePay.value]?.method === 'efectivo')
const canCharge = computed(() => cart.value.length && customer.value && total.value > 0)
const canConfirmPay = computed(() => paid.value >= total.value && total.value > 0)

// Tope de un pago: el efectivo puede exceder (genera cambio); los demás métodos
// se topan al saldo pendiente (no se cobra de más a una tarjeta/transferencia).
function clampPay(p, value) {
  if (p.method === 'efectivo') return Math.max(0, value)
  const others = paid.value - (Number(p.amount) || 0)
  const due = Math.max(0, total.value - others)
  return Math.min(Math.max(0, value), due)
}

function openPay() {
  if (!canCharge.value) {
    if (!customer.value) toastError('Selecciona o crea un cliente para la venta.')
    return
  }
  // Arranca con un pago en efectivo por el total exacto (lo más común).
  payments.value = [{ method: 'efectivo', amount: total.value }]
  activePay.value = 0
  payOpen.value = true
}
function setActivePay(i) {
  activePay.value = i
}
function setPayMethod(method) {
  const p = payments.value[activePay.value]
  p.method = method
  // Al pasar a tarjeta/transferencia/otro, recorta un posible exceso (sin cambio).
  p.amount = clampPay(p, Number(p.amount) || 0)
}
function keypad(digit) {
  const p = payments.value[activePay.value]
  const cur = Math.round(Number(p.amount) || 0)
  let next = cur
  if (digit === 'back') next = Math.floor(cur / 10)
  else if (digit === '00') next = cur * 100
  else if (digit === 'clear') next = 0
  else next = cur * 10 + digit
  p.amount = clampPay(p, next)
}
function quickCash(amount) {
  const p = payments.value[activePay.value]
  p.amount = clampPay(p, amount)
}
function exactRemaining() {
  const p = payments.value[activePay.value]
  const others = paid.value - (Number(p.amount) || 0)
  p.amount = Math.max(0, total.value - others)
}
function addPaymentRow() {
  payments.value.push({ method: 'tarjeta', amount: remaining.value })
  activePay.value = payments.value.length - 1
}
function removePaymentRow(i) {
  payments.value.splice(i, 1)
  activePay.value = Math.min(activePay.value, payments.value.length - 1)
}

async function checkout() {
  if (!canConfirmPay.value || saving.value) return
  saving.value = true
  try {
    const sale = await salesApi.create({
      warehouse: warehouse.value,
      customer: customer.value,
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

// --------------------------- Pantalla completa ---------------------------
const immersive = ref(false)
async function toggleImmersive() {
  immersive.value = !immersive.value
  await nextTick()
  try {
    if (immersive.value && !document.fullscreenElement) {
      await document.documentElement.requestFullscreen?.()
    } else if (!immersive.value && document.fullscreenElement) {
      await document.exitFullscreen?.()
    }
  } catch {
    /* el navegador puede bloquear fullscreen; el modo CSS sigue activo */
  }
}
function onFsChange() {
  // Si el usuario sale del fullscreen nativo (Esc), salimos del modo inmersivo.
  if (!document.fullscreenElement) immersive.value = false
}

// --------------------------- Ciclo de vida ---------------------------
watch(warehouse, (id) => {
  cart.value = []
  loadStock(id)
})

onMounted(async () => {
  document.addEventListener('fullscreenchange', onFsChange)
  try {
    const [ps, cs, cats] = await Promise.all([
      productsApi.list({ page_size: 500, is_active: true }),
      customersApi.list({ page_size: 500, is_active: true }),
      categoriesApi.list({ page_size: 100, is_active: true })
    ])
    products.value = ps.results
    customers.value = cs.results
    categories.value = cats.results

    if (isAdmin.value) {
      const wh = await warehousesApi.list({ page_size: 200, is_active: true })
      warehouses.value = wh.results
      if (warehouses.value.length) warehouse.value = warehouses.value[0].id
    } else if (assignedWarehouseId.value) {
      warehouse.value = assignedWarehouseId.value
    }
  } catch {
    toastError('No se pudo cargar el punto de venta.')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFsChange)
  clearTimeout(flashTimer)
  if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {})
})
</script>

<template>
  <div class="pos-wrap" :class="{ 'pos-wrap--immersive': immersive }">
    <!-- Barra superior -->
    <header class="pos-top">
      <div class="pos-top__title">
        <ShoppingCart :size="20" />
        <h1>Punto de venta</h1>
      </div>
      <div class="pos-top__right">
        <div class="pos-wh">
          <span class="pos-wh__label">Bodega</span>
          <SearchSelect
            v-if="isAdmin"
            v-model="warehouse"
            :options="warehouses"
            placeholder="Bodega"
          />
          <span v-else class="pos-wh__fixed">
            <Store :size="15" /> {{ assignedWarehouseName || 'Sin asignar' }}
          </span>
        </div>
        <button class="pos-fs" :title="immersive ? 'Salir de pantalla completa' : 'Pantalla completa'" @click="toggleImmersive">
          <component :is="immersive ? Minimize2 : Maximize2" :size="18" />
        </button>
      </div>
    </header>

    <LoadingState v-if="loading" label="Cargando punto de venta…" />

    <div v-else-if="noWarehouse" class="pos-blocked">
      <Store :size="34" />
      <p>No tienes una bodega asignada.</p>
      <span>Pídele a un administrador que te asigne una para poder vender.</span>
    </div>

    <div v-else class="pos">
      <!-- Columna 1: categorías -->
      <nav class="pos-cats">
        <button
          class="pos-cat"
          :class="{ 'pos-cat--active': activeCategory === 'all' }"
          @click="activeCategory = 'all'"
        >
          <span class="pos-cat__icon pos-cat__icon--all"><LayoutGrid :size="18" /></span>
          <span class="pos-cat__name">Todos</span>
          <span class="pos-cat__count">{{ products.length }}</span>
        </button>
        <button
          v-for="c in categoryTabs"
          :key="c.id"
          class="pos-cat"
          :class="{ 'pos-cat--active': activeCategory === c.id }"
          @click="activeCategory = c.id"
        >
          <span class="pos-cat__icon" :style="{ background: catColor(c.id) }">
            {{ c.name.charAt(0).toUpperCase() }}
          </span>
          <span class="pos-cat__name">{{ c.name }}</span>
          <span class="pos-cat__count">{{ c.count }}</span>
        </button>
      </nav>

      <!-- Columna 2: búsqueda + grid -->
      <section class="pos-grid-col">
        <div class="pos-search">
          <Search :size="18" class="pos-search__icon" />
          <input
            v-model="query"
            class="pos-search__input"
            type="search"
            placeholder="Buscar producto por nombre, SKU o código…"
          />
        </div>

        <div v-if="!cards.length" class="pos-empty">
          <Package :size="40" />
          <p>{{ query ? 'Ningún producto coincide con la búsqueda.' : 'No hay productos en esta categoría.' }}</p>
        </div>

        <div v-else class="pos-grid">
          <button
            v-for="c in cards"
            :key="c.product.id"
            class="tile"
            :class="{ 'tile--out': c.stock <= 0, 'tile--flash': flashedCard === c.product.id }"
            @click="onCardClick(c)"
          >
            <span class="tile__media">
              <img v-if="cardImage(c)" :src="cardImage(c)" :alt="c.name" loading="lazy" />
              <Package v-else :size="30" class="tile__ph" />
              <span v-if="c.stock <= 0" class="tile__badge tile__badge--out">Agotado</span>
              <span v-else class="tile__badge tile__badge--stock">{{ c.stock }}</span>
            </span>
            <span class="tile__name">{{ c.name }}</span>
            <span class="tile__swatches">
              <button
                v-for="s in c.swatches.slice(0, 6)"
                :key="s.id"
                type="button"
                class="dot"
                :class="{ 'dot--out': !s.available, 'dot--active': cardPreview[c.product.id] === s.id }"
                :style="{ background: s.hex }"
                :title="s.available ? `Ver ${s.label}` : `${s.label} (agotado)`"
                @click.stop="previewColor(c, s)"
              />
              <span v-if="c.swatches.length > 6" class="dot-more">+{{ c.swatches.length - 6 }}</span>
            </span>
            <span class="tile__price">
              <small v-if="c.priceMin !== c.priceMax" class="tile__from">Desde</small>
              {{ money(c.priceMin) }}
            </span>
          </button>
        </div>
      </section>

      <!-- Columna 3: ticket -->
      <aside class="pos-ticket">
        <div class="ticket-customer">
          <div class="ticket-customer__head">
            <span class="field__label">Cliente *</span>
            <div class="ticket-customer__actions">
              <button v-if="walkInCustomer" type="button" class="link-btn" @click="useWalkIn">
                <Store :size="14" /> Consumidor final
              </button>
              <button type="button" class="link-btn" @click="openNewCustomer">
                <UserPlus :size="14" /> Nuevo
              </button>
            </div>
          </div>
          <SearchSelect
            v-model="customer"
            :options="customerOptions"
            value-key="id"
            label-key="label"
            placeholder="Buscar por identificación…"
            @update:model-value="onCustomerChange"
          />
        </div>

        <div class="ticket-body">
          <div v-if="!cart.length" class="ticket-empty">
            <ShoppingCart :size="32" />
            <p>Toca un producto para empezar la venta.</p>
          </div>
          <ul v-else class="ticket-lines">
            <li v-for="item in cart" :key="item.id" class="line">
              <span class="line__media">
                <img v-if="item.image" :src="item.image" :alt="item.name" />
                <Package v-else :size="18" />
              </span>
              <span class="line__info">
                <span class="line__name">{{ item.name }}</span>
                <span class="line__meta">
                  <template v-if="item.options">{{ item.options }} · </template>{{ money(item.unit_price) }} c/u
                </span>
                <span class="qty">
                  <button class="qty__btn" @click="changeQty(item, -1)"><Minus :size="15" /></button>
                  <span class="qty__val">{{ item.quantity }}</span>
                  <button class="qty__btn" @click="changeQty(item, 1)"><Plus :size="15" /></button>
                </span>
              </span>
              <span class="line__end">
                <button class="line__del" title="Quitar" @click="removeItem(item)"><Trash2 :size="16" /></button>
                <span class="line__total">{{ money(item.unit_price * item.quantity) }}</span>
              </span>
            </li>
          </ul>
        </div>

        <div class="ticket-foot">
          <div class="disc">
            <span class="field__label">Descuento</span>
            <div class="disc__row">
              <MoneyInput v-if="discountType === 'amount'" v-model="discountInput" />
              <input v-else v-model="discountInput" type="number" min="0" class="field__input" placeholder="0" />
              <div class="disc__toggle">
                <button type="button" :class="{ active: discountType === 'amount' }" @click="discountType = 'amount'">$</button>
                <button type="button" :class="{ active: discountType === 'percent' }" @click="discountType = 'percent'">%</button>
              </div>
            </div>
          </div>

          <div class="totals">
            <div v-if="discountAmount" class="totals__row"><span>Bruto</span><span>{{ money(gross) }}</span></div>
            <div v-if="discountAmount" class="totals__row totals__row--disc"><span>Descuento</span><span>-{{ money(discountAmount) }}</span></div>
            <div class="totals__row"><span>Subtotal (sin IVA)</span><span>{{ money(subtotal) }}</span></div>
            <div class="totals__row"><span>IVA</span><span>{{ money(taxTotal) }}</span></div>
            <div class="totals__row totals__row--total"><span>Total</span><span>{{ money(total) }}</span></div>
          </div>

          <div class="ticket-actions">
            <button v-if="cart.length" class="btn-clear" title="Vaciar" @click="clearCart"><Trash2 :size="16" /></button>
            <button class="btn-charge" :disabled="!canCharge" @click="openPay">
              <span>Cobrar</span>
              <strong>{{ money(total) }}</strong>
            </button>
          </div>
        </div>
      </aside>
    </div>

    <!-- Overlay: selección de variante -->
    <div v-if="pickerProduct" class="modal" @click.self="closePicker">
      <div class="modal__box modal__box--picker">
        <div class="modal__head">
          <h2 class="modal__title">{{ pickerProduct.name }}</h2>
          <button type="button" class="icon-btn" @click="closePicker"><X :size="18" /></button>
        </div>
        <div class="picker">
          <div class="picker-media">
            <img v-if="pickerImage" :src="pickerImage" :alt="pickerProduct.name" />
            <Package v-else :size="34" />
          </div>
          <div v-for="attr in pickerAttributes" :key="attr.id" class="picker-attr">
            <span class="picker-attr__label">{{ attr.name }}</span>
            <div class="picker-opts">
              <button
                v-for="val in attr.values"
                :key="val.id"
                class="opt"
                :class="{
                  'opt--swatch': attr.is_image_axis || val.swatch_hex,
                  'opt--active': valueSelected(attr.id, val.id),
                  'opt--disabled': valueDisabled(attr.id, val.id)
                }"
                :disabled="valueDisabled(attr.id, val.id)"
                @click="selectValue(attr.id, val.id)"
              >
                <span
                  v-if="val.swatch_hex"
                  class="opt__swatch"
                  :style="{ background: val.swatch_hex }"
                />
                {{ val.value }}
                <span
                  v-if="attr.id === lastPickerAttrId && !valueDisabled(attr.id, val.id) && optionStock(attr.id, val.id) !== null"
                  class="opt__stock"
                >· {{ optionStock(attr.id, val.id) }}</span>
                <Check v-if="valueSelected(attr.id, val.id)" :size="14" class="opt__check" />
              </button>
            </div>
          </div>

          <div class="picker-foot">
            <div class="picker-foot__info">
              <span v-if="pickerSelected" class="picker-price">{{ money(pickerSelected.sale_price) }}</span>
              <span v-else class="picker-hint">Elige las opciones</span>
              <span v-if="pickerSelected" class="picker-stock" :class="{ 'picker-stock--out': pickerSelectedStock <= 0 }">
                {{ pickerSelectedStock > 0 ? `Quedan ${pickerSelectedStock} unidad(es)` : 'Agotada' }}
              </span>
            </div>
            <div class="picker-foot__actions">
              <span class="qty">
                <button class="qty__btn" :disabled="pickerQty <= 1" @click="pickerQtyChange(-1)"><Minus :size="16" /></button>
                <span class="qty__val">{{ pickerQty }}</span>
                <button class="qty__btn" :disabled="pickerQty >= pickerSelectedStock" @click="pickerQtyChange(1)"><Plus :size="16" /></button>
              </span>
              <button class="btn btn--primary" :disabled="!pickerSelected || pickerSelectedStock <= 0" @click="confirmPicker">
                <Plus :size="16" /> Agregar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlay: cobro con teclado -->
    <div v-if="payOpen" class="pay">
      <div class="pay__panel">
        <header class="pay__head">
          <button class="icon-btn" @click="payOpen = false"><ArrowLeft :size="18" /> Volver</button>
          <h2>Cobro</h2>
          <span class="pay__items">{{ totalItems }} artículo(s)</span>
        </header>

        <div class="pay__body">
          <!-- Izquierda: resumen + métodos + pagos -->
          <div class="pay__left">
            <div class="pay-summary">
              <div class="pay-summary__row"><span>Total a cobrar</span><strong>{{ money(total) }}</strong></div>
              <div class="pay-summary__row pay-summary__row--paid"><span>Pagado</span><span>{{ money(paid) }}</span></div>
              <div v-if="remaining > 0" class="pay-summary__row pay-summary__row--due"><span>Falta</span><span>{{ money(remaining) }}</span></div>
              <div v-else class="pay-summary__row pay-summary__row--change"><span>Cambio</span><span>{{ money(change) }}</span></div>
            </div>

            <span class="field__label">Forma de pago</span>
            <div class="pay-methods">
              <button
                v-for="m in PAYMENT_OPTIONS"
                :key="m.value"
                class="pay-method"
                :class="{ 'pay-method--active': payments[activePay].method === m.value }"
                @click="setPayMethod(m.value)"
              >
                {{ m.label }}
              </button>
            </div>

            <div class="pay-list">
              <div
                v-for="(p, i) in payments"
                :key="i"
                class="pay-item"
                :class="{ 'pay-item--active': activePay === i }"
                @click="setActivePay(i)"
              >
                <Tag :size="14" />
                <span class="pay-item__method">{{ PAYMENT_OPTIONS.find((o) => o.value === p.method)?.label }}</span>
                <span class="pay-item__amount">{{ money(p.amount) }}</span>
                <button v-if="payments.length > 1" class="pay-item__del" @click.stop="removePaymentRow(i)"><X :size="14" /></button>
              </div>
              <button class="pay-add" @click="addPaymentRow"><Plus :size="15" /> Pago dividido</button>
            </div>

            <label class="field">
              <span class="field__label">Correo para el recibo (opcional)</span>
              <input v-model="receiptEmail" type="email" class="field__input" placeholder="correo@ejemplo.com" />
              <span v-if="selectedCustomer && selectedCustomer.email" class="field__hint">Tomado del cliente; puedes cambiarlo.</span>
              <span v-else-if="selectedCustomer" class="field__hint">Este cliente no tiene correo. Escribe uno si quieres enviar el recibo.</span>
            </label>
          </div>

          <!-- Derecha: teclado numérico -->
          <div class="pay__right">
            <div class="keypad-display">
              <span class="keypad-display__label">
                {{ PAYMENT_OPTIONS.find((o) => o.value === payments[activePay].method)?.label }}
                <span v-if="!activeIsCash" class="keypad-display__exact">· exacto, sin cambio</span>
              </span>
              <span class="keypad-display__amount">{{ money(payments[activePay].amount) }}</span>
            </div>
            <div class="quick-cash">
              <button
                class="quick-cash__btn quick-cash__btn--exact"
                :class="{ 'quick-cash__btn--full': !activeIsCash }"
                @click="exactRemaining"
              >
                Exacto
              </button>
              <template v-if="activeIsCash">
                <button v-for="amt in QUICK_CASH" :key="amt" class="quick-cash__btn" @click="quickCash(amt)">{{ money(amt) }}</button>
              </template>
            </div>
            <div class="keypad">
              <button v-for="n in [1,2,3,4,5,6,7,8,9]" :key="n" class="keypad__key" @click="keypad(n)">{{ n }}</button>
              <button class="keypad__key keypad__key--alt" @click="keypad('00')">00</button>
              <button class="keypad__key" @click="keypad(0)">0</button>
              <button class="keypad__key keypad__key--alt" @click="keypad('back')"><Delete :size="20" /></button>
            </div>
            <button class="btn-charge btn-charge--lg" :disabled="!canConfirmPay || saving" @click="checkout">
              <Check :size="20" />
              {{ saving ? 'Cobrando…' : `Cobrar ${money(total)}` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: crear cliente rápido -->
    <div v-if="newCustomerOpen" class="modal" @click.self="newCustomerOpen = false">
      <div class="modal__box">
        <div class="modal__head">
          <h2 class="modal__title">Nuevo cliente</h2>
          <button type="button" class="icon-btn" @click="newCustomerOpen = false"><X :size="16" /></button>
        </div>
        <form class="modal__form" @submit.prevent="saveNewCustomer">
          <div class="modal__row">
            <label class="field">
              <span class="field__label">Tipo de identificación *</span>
              <SearchSelect v-model="newCustomer.id_type" :options="ID_TYPES" value-key="value" label-key="label" />
            </label>
            <label class="field">
              <span class="field__label">Número *</span>
              <input v-model="newCustomer.id_number" class="field__input" maxlength="40" />
              <span v-if="newCustomerErrors.id_number" class="field__error">{{ newCustomerErrors.id_number[0] }}</span>
            </label>
          </div>
          <div class="modal__row">
            <label class="field">
              <span class="field__label">Nombre *</span>
              <input v-model="newCustomer.first_name" class="field__input" maxlength="150" />
              <span v-if="newCustomerErrors.first_name" class="field__error">{{ newCustomerErrors.first_name[0] }}</span>
            </label>
            <label class="field">
              <span class="field__label">Apellido</span>
              <input v-model="newCustomer.last_name" class="field__input" maxlength="150" placeholder="Opcional" />
            </label>
          </div>
          <div class="modal__row">
            <label class="field">
              <span class="field__label">Correo</span>
              <input v-model="newCustomer.email" type="email" class="field__input" placeholder="Opcional" />
              <span v-if="newCustomerErrors.email" class="field__error">{{ newCustomerErrors.email[0] }}</span>
            </label>
            <label class="field">
              <span class="field__label">Teléfono</span>
              <input v-model="newCustomer.phone" class="field__input" maxlength="40" placeholder="Opcional" />
            </label>
          </div>
          <div class="modal__actions">
            <button type="button" class="btn btn--ghost" @click="newCustomerOpen = false">Cancelar</button>
            <button type="submit" class="btn btn--primary" :disabled="!canCreateCustomer || creatingCustomer">
              {{ creatingCustomer ? 'Creando…' : 'Crear y seleccionar' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===================== Contenedor / modo inmersivo ===================== */
.pos-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pos-wrap--immersive {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: var(--color-surface-alt);
  padding: 16px;
  gap: 12px;
  overflow: hidden;
}

/* ===================== Barra superior ===================== */
.pos-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.pos-top__title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-ink);
}
.pos-top__title h1 {
  font-size: 1.5rem;
}
.pos-top__right {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
.pos-wh {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;
}
.pos-wh__label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}
.pos-wh__fixed {
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
.pos-fs {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  transition: all 0.16s ease;
}
.pos-fs:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
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

/* ===================== Layout 3 columnas ===================== */
.pos {
  display: grid;
  grid-template-columns: 200px 1fr 360px;
  gap: 14px;
  align-items: start;
  min-height: 0;
}
.pos-wrap--immersive .pos {
  flex: 1;
  height: calc(100vh - 92px);
}

/* ----- Columna 1: categorías ----- */
.pos-cats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 10px;
  max-height: calc(100vh - 130px);
  overflow-y: auto;
}
.pos-cat {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  background: none;
  text-align: left;
  transition: background 0.14s ease;
}
.pos-cat:hover {
  background: var(--color-surface-alt);
}
.pos-cat--active {
  background: var(--color-primary-soft);
}
.pos-cat--active .pos-cat__name {
  color: var(--color-primary);
  font-weight: 700;
}
.pos-cat__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
}
.pos-cat__icon--all {
  background: var(--color-ink);
}
.pos-cat__name {
  flex: 1;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pos-cat__count {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--color-muted);
  background: var(--color-surface-alt);
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

/* ----- Columna 2: búsqueda + grid ----- */
.pos-grid-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.pos-search {
  position: relative;
}
.pos-search__icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-muted);
}
.pos-search__input {
  width: 100%;
  padding: 13px 14px 13px 42px;
  font-family: inherit;
  font-size: 1rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: #fff;
}
.pos-search__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.pos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  align-content: start;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 2px;
}
.pos-wrap--immersive .pos-grid {
  max-height: calc(100vh - 170px);
}
.tile {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  transition: transform 0.12s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}
.tile:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.tile:active {
  transform: translateY(0);
}
.tile--out {
  opacity: 0.55;
}
.tile--flash {
  border-color: var(--color-success);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-success) 30%, transparent);
}
.tile__media {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  flex-shrink: 0;
  background: var(--color-surface-alt);
  color: var(--color-muted);
}
.tile__media img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.tile__ph {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
.tile__badge {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
}
.tile__badge--stock {
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-ink);
  box-shadow: var(--shadow-sm);
}
.tile__badge--out {
  background: #fef2f2;
  color: #b91c1c;
}
.tile__name {
  padding: 8px 10px 2px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.6em;
}
.tile__swatches {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  min-height: 1.1em;
}
.dot {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.18);
  flex-shrink: 0;
  cursor: pointer;
  padding: 0;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.dot:hover {
  transform: scale(1.15);
}
.dot--active {
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--color-primary);
}
/* Color agotado: atenuado y con una barra diagonal. */
.dot--out {
  opacity: 0.45;
  position: relative;
}
.dot--out::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top right,
    transparent calc(50% - 1px),
    #94a3b8 calc(50% - 1px),
    #94a3b8 calc(50% + 1px),
    transparent calc(50% + 1px)
  );
  border-radius: 50%;
}
.dot-more {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-muted);
}
.tile__price {
  margin-top: auto;
  padding: 4px 10px 10px;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--color-primary);
  white-space: nowrap;
}
.tile__from {
  display: block;
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-muted);
}

.pos-empty {
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

/* ----- Columna 3: ticket ----- */
.pos-ticket {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  max-height: calc(100vh - 130px);
  overflow: hidden;
}
.ticket-customer {
  padding: 14px;
  border-bottom: 1px solid var(--color-line);
}
.ticket-customer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.ticket-customer__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ticket-body {
  flex: 1;
  overflow-y: auto;
  min-height: 120px;
}
.ticket-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 48px 20px;
  color: var(--color-muted);
  text-align: center;
}
.ticket-lines {
  display: flex;
  flex-direction: column;
}
.line {
  display: grid;
  grid-template-columns: 44px 1fr auto;
  gap: 10px;
  align-items: start;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-surface-alt);
}
.line__media {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt);
  color: var(--color-muted);
}
.line__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.line__info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.line__name {
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--color-ink);
  line-height: 1.2;
}
.line__meta {
  font-size: 0.74rem;
  color: var(--color-muted);
}
.line__end {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  height: 100%;
}
.line__total {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-ink);
  white-space: nowrap;
}
.line__del {
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
  transition: all 0.14s ease;
}
.line__del:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}

.qty {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.qty__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  color: var(--color-ink);
}
.qty__btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.qty__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.qty__val {
  min-width: 26px;
  text-align: center;
  font-weight: 700;
}

.ticket-foot {
  border-top: 1px solid var(--color-line);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--color-surface-alt);
}
.disc {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.disc__row {
  display: flex;
  gap: 8px;
}
.disc__row > :first-child {
  flex: 1;
}
.disc__toggle {
  display: inline-flex;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #fff;
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
  gap: 5px;
}
.totals__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--color-body);
}
.totals__row--disc {
  color: #b45309;
}
.totals__row--total {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--color-ink);
  padding-top: 8px;
  border-top: 1px solid var(--color-line);
}
.ticket-actions {
  display: flex;
  gap: 10px;
}
.btn-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  color: var(--color-muted);
  cursor: pointer;
}
.btn-clear:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}
.btn-charge {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px 18px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 1.05rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.16s ease, transform 0.1s ease;
}
.btn-charge:hover:not(:disabled) {
  background: var(--color-primary-strong, var(--color-primary));
  filter: brightness(0.96);
}
.btn-charge:active:not(:disabled) {
  transform: scale(0.99);
}
.btn-charge:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

/* ===================== Modales genéricos ===================== */
.modal {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
}
.modal__box {
  width: 100%;
  max-width: 520px;
  background: #fff;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}
.modal__box--picker {
  max-width: 460px;
}
.modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-line);
}
.modal__title {
  font-size: 1.1rem;
}
.modal__form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.modal__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
}
.icon-btn:hover {
  color: var(--color-ink);
  border-color: var(--color-primary);
}

/* ----- Picker de variante ----- */
.picker {
  padding: 18px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.picker-media {
  align-self: center;
  width: 160px;
  height: 160px;
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt);
  color: var(--color-muted);
}
.picker-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.picker-attr {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.picker-attr__label {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-ink);
}
.picker-opts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink);
  transition: all 0.14s ease;
}
.opt:hover:not(.opt--disabled) {
  border-color: var(--color-primary);
}
.opt--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 700;
}
.opt--disabled {
  opacity: 0.4;
  cursor: not-allowed;
  text-decoration: line-through;
}
.opt__swatch {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.15);
}
.opt__check {
  color: var(--color-primary);
}
.opt__stock {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-muted);
}
.opt--active .opt__stock {
  color: var(--color-primary);
}
.picker-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--color-line);
}
.picker-foot__info {
  display: flex;
  flex-direction: column;
}
.picker-price {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--color-ink);
}
.picker-hint {
  color: var(--color-muted);
}
.picker-stock {
  font-size: 0.78rem;
  color: var(--color-success);
}
.picker-stock--out {
  color: #dc2626;
}
.picker-foot__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ===================== Pantalla de cobro ===================== */
.pay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.55);
}
.pay__panel {
  width: 100%;
  max-width: 880px;
  max-height: 96vh;
  background: var(--color-surface-alt);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.pay__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: #fff;
  border-bottom: 1px solid var(--color-line);
}
.pay__head h2 {
  font-size: 1.15rem;
}
.pay__items {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.pay__body {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
  padding: 18px;
  overflow-y: auto;
}
.pay__left {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.pay-summary {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pay-summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.92rem;
  color: var(--color-body);
}
.pay-summary__row strong {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-ink);
}
.pay-summary__row--paid {
  color: var(--color-muted);
}
.pay-summary__row--due {
  color: #b45309;
  font-weight: 700;
}
.pay-summary__row--change {
  color: var(--color-success);
  font-weight: 800;
  font-size: 1.05rem;
}
.pay-methods {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.pay-method {
  padding: 12px 8px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.86rem;
  color: var(--color-ink);
  transition: all 0.14s ease;
}
.pay-method:hover {
  border-color: var(--color-primary);
}
.pay-method--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.pay-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pay-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  color: var(--color-muted);
}
.pay-item--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.pay-item__method {
  font-weight: 600;
  color: var(--color-ink);
}
.pay-item__amount {
  margin-left: auto;
  font-weight: 700;
  color: var(--color-ink);
}
.pay-item__del {
  color: var(--color-muted);
  cursor: pointer;
}
.pay-item__del:hover {
  color: #dc2626;
}
.pay-add {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  background: none;
  padding: 4px 0;
}

.pay__right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.keypad-display {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.keypad-display__label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}
.keypad-display__exact {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
  color: var(--color-muted);
}
.keypad-display__amount {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-ink);
}
.quick-cash {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.quick-cash__btn {
  padding: 10px 4px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-ink);
}
.quick-cash__btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.quick-cash__btn--exact {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: transparent;
}
.quick-cash__btn--full {
  grid-column: 1 / -1;
}
.keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.keypad__key {
  padding: 16px 0;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  cursor: pointer;
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s ease;
}
.keypad__key:hover {
  background: var(--color-surface-alt);
}
.keypad__key:active {
  background: var(--color-primary-soft);
}
.keypad__key--alt {
  color: var(--color-muted);
  font-size: 1.05rem;
}
.btn-charge--lg {
  padding: 18px;
  font-size: 1.15rem;
}

/* ===================== Campos compartidos ===================== */
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
.field__hint {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.field__error {
  font-size: 0.78rem;
  color: #dc2626;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  background: none;
}
.link-btn:hover {
  text-decoration: underline;
}

/* ===================== Responsive ===================== */
@media (max-width: 1100px) {
  .pos {
    grid-template-columns: 170px 1fr 320px;
  }
}
@media (max-width: 900px) {
  .pos {
    grid-template-columns: 1fr;
  }
  .pos-cats {
    flex-direction: row;
    flex-wrap: wrap;
    max-height: none;
  }
  .pos-cat {
    flex: 0 0 auto;
  }
  .pos-cat__count {
    display: none;
  }
  .pos-grid,
  .pos-ticket {
    max-height: none;
  }
  .pay__body {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .modal__row {
    grid-template-columns: 1fr;
  }
}
</style>
