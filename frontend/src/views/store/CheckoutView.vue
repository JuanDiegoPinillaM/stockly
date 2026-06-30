<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { ArrowLeft, MapPin, Store, Truck, CreditCard, AlertTriangle, Check, Plus } from 'lucide-vue-next'
import { ordersApi, addressesApi } from '@/services/store'
import { useCartStore } from '@/stores/cart'
import { toastError } from '@/utils/notify'
import AddressForm from '@/components/AddressForm.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()
const cart = useCartStore()

const loading = ref(true)
const loadError = ref('')
const addresses = ref([])

// Opciones de entrega del carrito (las decide el backend).
const deliveryAvailable = ref(false)
const pickupPoints = ref([]) // tiendas que tienen el pedido COMPLETO
const pickupSplit = ref(null) // reparto entre varias tiendas (si ninguna sola)

// Selección del comprador.
const fulfillment = ref('envio') // 'envio' | 'recoge'
const addressId = ref(null)
const pickupPointId = ref(null) // tienda elegida para recoger (una sola)
const usePickupSplit = ref(false) // recoger repartido en varias tiendas
const payment = ref('tarjeta')
const note = ref('')

const placing = ref(false)
const placeError = ref('')

// Crear dirección sin salir del checkout.
const addingAddress = ref(false)
const savingAddress = ref(false)

async function saveAddress(payload) {
  savingAddress.value = true
  try {
    const created = await addressesApi.create(payload)
    const addrs = await addressesApi.list()
    addresses.value = addrs.results || addrs
    addressId.value = created.id // selecciona la recién creada
    addingAddress.value = false
  } catch (e) {
    const err = e.response?.data
    toastError(err?.errors?.city?.[0] || err?.detail || 'No se pudo guardar la dirección.')
  } finally {
    savingAddress.value = false
  }
}

const PAYMENTS = [
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'nequi', label: 'Nequi' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'efectivo', label: 'Efectivo contra entrega' }
]

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

const selectedPickup = computed(() => pickupPoints.value.find((p) => p.id === pickupPointId.value) || null)

const canPlace = computed(() => {
  if (cart.isEmpty) return false
  if (fulfillment.value === 'envio') return deliveryAvailable.value && Boolean(addressId.value)
  // Recoger: en una tienda elegida o repartido en varias.
  return Boolean(pickupPointId.value) || usePickupSplit.value
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [opts, addrs] = await Promise.all([
      ordersApi.fulfillmentOptions({ items: cart.toItemsPayload() }),
      addressesApi.list()
    ])
    deliveryAvailable.value = opts.delivery_available
    pickupPoints.value = opts.pickup_points || []
    pickupSplit.value = opts.pickup_split || null
    addresses.value = addrs.results || addrs
    if (pickupPoints.value.length === 1) pickupPointId.value = pickupPoints.value[0].id
    // Si no hay tienda única pero sí reparto, esa es la única vía para recoger.
    if (!pickupPoints.value.length && pickupSplit.value) usePickupSplit.value = true
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
    const isDelivery = fulfillment.value === 'envio'
    const isSplit = !isDelivery && usePickupSplit.value
    const order = await ordersApi.create({
      fulfillment: fulfillment.value,
      payment_method: payment.value,
      // Envío: el sistema decide. Recoger: una tienda elegida o reparto en varias.
      warehouse: isDelivery || isSplit ? null : pickupPointId.value,
      pickup_split: isSplit,
      address: isDelivery ? addressId.value : null,
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
        <!-- 1. Entrega -->
        <section class="card">
          <h2 class="card__title"><Truck :size="18" /> Entrega</h2>
          <div class="seg">
            <button class="seg__btn" :class="{ 'seg__btn--active': fulfillment === 'envio' }" @click="fulfillment = 'envio'">
              Envío a domicilio
            </button>
            <button class="seg__btn" :class="{ 'seg__btn--active': fulfillment === 'recoge' }" @click="fulfillment = 'recoge'">
              Recoger en tienda
            </button>
          </div>

          <!-- Envío: el comprador no elige tienda; el sistema la decide -->
          <template v-if="fulfillment === 'envio'">
            <div v-if="!deliveryAvailable" class="warn warn--block">
              <AlertTriangle :size="16" />
              <span>No tenemos tu pedido completo en una sola tienda para enviarlo a domicilio. Prueba a recoger en tienda o ajusta las cantidades.</span>
            </div>
            <template v-else>
              <p class="card__hint">
                Lo despachamos automáticamente desde la tienda más cercana a ti que tenga tu pedido.
              </p>

              <!-- Formulario inline de nueva dirección -->
              <div v-if="addingAddress" class="addr-new">
                <h3 class="addr-new__title">Nueva dirección</h3>
                <AddressForm
                  :saving="savingAddress"
                  submit-label="Guardar dirección"
                  @submit="saveAddress"
                  @cancel="addingAddress = false"
                />
              </div>

              <template v-else>
                <div v-if="!addresses.length" class="empty-addr">
                  <MapPin :size="22" />
                  <p>No tienes direcciones guardadas.</p>
                  <button class="btn btn--primary btn--sm" @click="addingAddress = true">
                    <Plus :size="16" /> Agregar dirección
                  </button>
                </div>
                <div v-else class="options">
                  <label v-for="a in addresses" :key="a.id" class="option" :class="{ 'option--active': addressId === a.id }">
                    <input v-model="addressId" type="radio" :value="a.id" />
                    <span class="option__body">
                      <span class="option__name"><MapPin :size="14" /> {{ a.recipient }}</span>
                      <span class="option__sub">{{ a.line1 }}{{ a.city_name ? ', ' + a.city_name : '' }}{{ a.department_name ? ', ' + a.department_name : '' }}</span>
                    </span>
                  </label>
                  <button class="add-addr" @click="addingAddress = true">
                    <Plus :size="15" /> Agregar otra dirección
                  </button>
                </div>
              </template>
            </template>
          </template>

          <!-- Recoger -->
          <template v-else>
            <!-- Una sola tienda tiene todo: el comprador elige -->
            <div v-if="pickupPoints.length" class="options">
              <p class="card__hint">Elige la tienda donde vas a recoger:</p>
              <label v-for="p in pickupPoints" :key="p.id" class="option" :class="{ 'option--active': pickupPointId === p.id }">
                <input v-model="pickupPointId" type="radio" :value="p.id" />
                <span class="option__body">
                  <span class="option__name"><Store :size="14" /> {{ p.name }}</span>
                  <span v-if="p.address" class="option__sub">{{ p.address }}</span>
                  <span v-if="p.hours" class="option__sub">{{ p.hours }}</span>
                </span>
              </label>
            </div>
            <!-- Ninguna sola, pero combinando varias sí: recoger repartido -->
            <div v-else-if="pickupSplit" class="split">
              <p class="card__hint">
                Tu pedido se prepara en varias tiendas. Podrás recogerlo así:
              </p>
              <div v-for="g in pickupSplit" :key="g.point.id" class="split__store">
                <div class="split__head"><Store :size="15" /> <strong>{{ g.point.name }}</strong></div>
                <p v-if="g.point.address" class="split__addr">{{ g.point.address }}</p>
                <ul class="split__items">
                  <li v-for="it in g.items" :key="it.variant">
                    {{ it.quantity }}× {{ it.name }} <small v-if="it.options">{{ it.options }}</small>
                  </li>
                </ul>
              </div>
            </div>
            <!-- Ni repartido alcanza -->
            <div v-else class="warn warn--block">
              <AlertTriangle :size="16" />
              <span>No hay unidades de tu pedido para recoger en tienda en este momento.</span>
            </div>
          </template>
        </section>

        <!-- 2. Pago -->
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

        <!-- 3. Nota -->
        <section class="card">
          <h2 class="card__title">Nota (opcional)</h2>
          <textarea v-model="note" class="textarea" rows="2" placeholder="Indicaciones para tu pedido…"></textarea>
        </section>
      </div>

      <!-- Resumen -->
      <aside class="summary">
        <h2 class="summary__title">Tu pedido</h2>
        <ul class="summary__items">
          <li v-for="item in cart.items" :key="item.variantId" class="summary__item">
            <span class="summary__qty">{{ item.quantity }}×</span>
            <span class="summary__name">
              {{ item.name }}
              <small>{{ item.variantLabel }}</small>
            </span>
            <span class="summary__price">{{ money(item.price * item.quantity) }}</span>
          </li>
        </ul>

        <p v-if="fulfillment === 'recoge' && selectedPickup" class="summary__pickup">
          Recoges en <strong>{{ selectedPickup.name }}</strong>.
        </p>
        <p v-else-if="fulfillment === 'recoge' && usePickupSplit && pickupSplit" class="summary__pickup">
          Recoges en <strong>{{ pickupSplit.length }} tiendas</strong> (ver el detalle arriba).
        </p>

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
.addr-new {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px;
  background: var(--color-surface-alt, #faf7f0);
}
.addr-new__title {
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 12px;
}
.empty-addr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
  color: var(--color-muted);
  text-align: center;
}
.add-addr {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 2px;
  padding: 11px;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.add-addr:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.split {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.split__store {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}
.split__head {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-ink);
}
.split__head svg {
  color: var(--color-primary);
}
.split__addr {
  font-size: 0.82rem;
  color: var(--color-muted);
  margin: 2px 0 8px 22px;
}
.split__items {
  margin: 0 0 0 22px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.88rem;
  color: var(--color-body);
}
.split__items small {
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
.summary__pickup {
  font-size: 0.85rem;
  color: var(--color-body);
  background: var(--color-primary-soft);
  padding: 9px 12px;
  border-radius: var(--radius-sm);
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
