<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { ArrowLeft, MapPin, Store, Truck, CreditCard, AlertTriangle, Check } from 'lucide-vue-next'
import { storeApi, ordersApi, addressesApi } from '@/services/store'
import { useCartStore } from '@/stores/cart'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()
const cart = useCartStore()

const loading = ref(true)
const loadError = ref('')
const points = ref([])
const addresses = ref([])

// Selección del comprador.
const pointId = ref(null)
const fulfillment = ref('envio') // 'envio' | 'recoge'
const addressId = ref(null)
const payment = ref('tarjeta')
const note = ref('')

// Disponibilidad en el punto elegido.
const availability = ref(null) // { [variantId]: bool }
const checking = ref(false)

const placing = ref(false)
const placeError = ref('')

const PAYMENTS = [
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'nequi', label: 'Nequi' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'efectivo', label: 'Efectivo contra entrega' }
]

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

const selectedPoint = computed(() => points.value.find((p) => p.id === pointId.value) || null)

const unavailableItems = computed(() => {
  if (!availability.value) return []
  return cart.items.filter((i) => availability.value[i.variantId] === false)
})

const canPlace = computed(() => {
  if (cart.isEmpty || !pointId.value) return false
  if (fulfillment.value === 'envio' && !addressId.value) return false
  if (unavailableItems.value.length) return false
  return true
})

async function checkAvailability() {
  if (!pointId.value || cart.isEmpty) {
    availability.value = null
    return
  }
  checking.value = true
  try {
    const data = await ordersApi.checkAvailability({
      warehouse: pointId.value,
      items: cart.toItemsPayload()
    })
    const map = {}
    data.results.forEach((r) => (map[r.variant] = r.available))
    availability.value = map
  } catch {
    availability.value = null
  } finally {
    checking.value = false
  }
}

watch(pointId, checkAvailability)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [pts, addrs] = await Promise.all([storeApi.points(), addressesApi.list()])
    points.value = pts
    addresses.value = addrs.results || addrs
    if (points.value.length === 1) pointId.value = points.value[0].id
    const def = addresses.value.find((a) => a.is_default) || addresses.value[0]
    if (def) addressId.value = def.id
  } catch {
    loadError.value = 'No se pudo cargar la información del checkout.'
  } finally {
    loading.value = false
  }
}

async function placeOrder() {
  if (!canPlace.value || placing.value) return
  placing.value = true
  placeError.value = ''
  try {
    const order = await ordersApi.create({
      warehouse: pointId.value,
      fulfillment: fulfillment.value,
      payment_method: payment.value,
      address: fulfillment.value === 'envio' ? addressId.value : null,
      items: cart.toItemsPayload(),
      note: note.value
    })
    cart.clear()
    router.push({ name: 'account-order-detail', params: { id: order.id }, query: { nuevo: '1' } })
  } catch (e) {
    placeError.value = e.response?.data?.detail || 'No se pudo crear el pedido. Revisa los datos e intenta de nuevo.'
  } finally {
    placing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container checkout">
    <RouterLink :to="{ name: 'cart' }" class="back"><ArrowLeft :size="16" /> Volver al carrito</RouterLink>
    <h1 class="checkout__title">Finalizar compra</h1>

    <LoadingState v-if="loading" label="Cargando…" />
    <ErrorState v-else-if="loadError" :message="loadError" @retry="load" />

    <div v-else-if="cart.isEmpty" class="empty">
      <p>Tu carrito está vacío.</p>
      <RouterLink :to="{ name: 'catalog' }" class="btn btn--primary">Ver productos</RouterLink>
    </div>

    <div v-else class="checkout__grid">
      <div class="form">
        <!-- 1. Punto -->
        <section class="card">
          <h2 class="card__title"><Store :size="18" /> Punto</h2>
          <p class="card__hint">Elige la tienda que prepara tu pedido.</p>
          <div v-if="!points.length" class="warn">No hay puntos disponibles por ahora.</div>
          <div v-else class="options">
            <label v-for="p in points" :key="p.id" class="option" :class="{ 'option--active': pointId === p.id }">
              <input v-model="pointId" type="radio" :value="p.id" />
              <span class="option__body">
                <span class="option__name">{{ p.name }}</span>
                <span v-if="p.address" class="option__sub">{{ p.address }}</span>
              </span>
            </label>
          </div>
        </section>

        <!-- 2. Entrega -->
        <section class="card">
          <h2 class="card__title"><Truck :size="18" /> Entrega</h2>
          <div class="seg">
            <button class="seg__btn" :class="{ 'seg__btn--active': fulfillment === 'envio' }" @click="fulfillment = 'envio'">
              Envío a domicilio
            </button>
            <button class="seg__btn" :class="{ 'seg__btn--active': fulfillment === 'recoge' }" @click="fulfillment = 'recoge'">
              Recoger en el punto
            </button>
          </div>

          <template v-if="fulfillment === 'envio'">
            <div v-if="!addresses.length" class="warn">
              No tienes direcciones guardadas.
              <RouterLink :to="{ name: 'account-addresses' }" class="warn__link">Agregar una dirección</RouterLink>
            </div>
            <div v-else class="options">
              <label v-for="a in addresses" :key="a.id" class="option" :class="{ 'option--active': addressId === a.id }">
                <input v-model="addressId" type="radio" :value="a.id" />
                <span class="option__body">
                  <span class="option__name"><MapPin :size="14" /> {{ a.recipient }}</span>
                  <span class="option__sub">{{ a.line1 }}{{ a.city_name ? ', ' + a.city_name : '' }}{{ a.department_name ? ', ' + a.department_name : '' }}</span>
                </span>
              </label>
            </div>
          </template>
          <p v-else class="card__hint">
            Recoges en {{ selectedPoint?.name || 'el punto seleccionado' }}{{ selectedPoint?.address ? ' — ' + selectedPoint.address : '' }}.
          </p>
        </section>

        <!-- 3. Pago -->
        <section class="card">
          <h2 class="card__title"><CreditCard :size="18" /> Pago</h2>
          <p class="card__hint">El cobro es simulado; no se registran datos de tarjeta.</p>
          <div class="options">
            <label v-for="m in PAYMENTS" :key="m.value" class="option" :class="{ 'option--active': payment === m.value }">
              <input v-model="payment" type="radio" :value="m.value" />
              <span class="option__name">{{ m.label }}</span>
            </label>
          </div>
        </section>

        <!-- 4. Nota -->
        <section class="card">
          <h2 class="card__title">Nota (opcional)</h2>
          <textarea v-model="note" class="textarea" rows="2" placeholder="Indicaciones para tu pedido…"></textarea>
        </section>
      </div>

      <!-- Resumen -->
      <aside class="summary">
        <h2 class="summary__title">Tu pedido</h2>
        <ul class="summary__items">
          <li v-for="item in cart.items" :key="item.variantId" class="summary__item" :class="{ 'summary__item--out': availability && availability[item.variantId] === false }">
            <span class="summary__qty">{{ item.quantity }}×</span>
            <span class="summary__name">
              {{ item.name }}
              <small>{{ item.variantLabel }}</small>
            </span>
            <span class="summary__price">{{ money(item.price * item.quantity) }}</span>
          </li>
        </ul>

        <div v-if="checking" class="summary__checking">Verificando disponibilidad…</div>
        <div v-else-if="unavailableItems.length" class="warn warn--block">
          <AlertTriangle :size="16" />
          <span>Algunos productos no están disponibles en este punto. Quítalos del carrito o elige otro punto.</span>
        </div>

        <div class="summary__total">
          <span>Total</span>
          <strong>{{ money(cart.subtotal) }}</strong>
        </div>

        <p v-if="placeError" class="summary__error">{{ placeError }}</p>

        <button class="btn btn--primary btn--block" :disabled="!canPlace || placing" @click="placeOrder">
          <Check :size="18" /> {{ placing ? 'Creando pedido…' : 'Confirmar pedido' }}
        </button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.checkout {
  padding: 28px 0 60px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-bottom: 14px;
}
.back:hover {
  color: var(--color-primary);
}
.checkout__title {
  font-size: 1.7rem;
  margin-bottom: 22px;
}
.checkout__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 28px;
  align-items: start;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 20px;
}
.card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  margin-bottom: 6px;
}
.card__hint {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-bottom: 14px;
}
.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.option:hover {
  border-color: var(--color-primary);
}
.option--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.option input {
  accent-color: var(--color-primary);
}
.option__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.option__name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--color-ink);
}
.option__sub {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.seg {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.seg__btn {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--color-body);
  transition: all 0.15s ease;
}
.seg__btn--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.textarea {
  width: 100%;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-family: inherit;
  font-size: 0.92rem;
  resize: vertical;
}
.warn {
  font-size: 0.88rem;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.warn--block {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 14px;
}
.warn__link {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: underline;
}
.summary {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 20px;
  position: sticky;
  top: 90px;
}
.summary__title {
  font-size: 1.1rem;
  margin-bottom: 14px;
}
.summary__items {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}
.summary__item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  font-size: 0.9rem;
}
.summary__item--out {
  opacity: 0.5;
  text-decoration: line-through;
}
.summary__qty {
  color: var(--color-muted);
  font-weight: 600;
}
.summary__name small {
  display: block;
  color: var(--color-muted);
  font-size: 0.78rem;
}
.summary__price {
  white-space: nowrap;
  font-weight: 600;
}
.summary__checking {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-bottom: 12px;
}
.summary__total {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-top: 14px;
  border-top: 1px solid var(--color-line);
  margin-bottom: 16px;
}
.summary__total strong {
  font-size: 1.3rem;
  color: var(--color-primary);
}
.summary__error {
  color: #dc2626;
  font-size: 0.85rem;
  margin-bottom: 12px;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 60px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
}

@media (max-width: 820px) {
  .checkout__grid {
    grid-template-columns: 1fr;
  }
  .summary {
    position: static;
  }
}
</style>
