<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, CheckCircle2, ImageOff, MapPin, Store, CreditCard, XCircle, PartyPopper } from 'lucide-vue-next'
import { ordersApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const order = ref(null)
const loading = ref(true)
const error = ref('')
const cancelling = ref(false)

const isNew = computed(() => route.query.nuevo === '1')

// Pasos del flujo para la línea de tiempo (cancelado se muestra aparte).
const STEPS = [
  { key: 'pendiente', label: 'Pendiente' },
  { key: 'confirmado', label: 'Confirmado' },
  { key: 'enviado', label: 'Enviado' },
  { key: 'entregado', label: 'Entregado' }
]
const stepIndex = computed(() => STEPS.findIndex((s) => s.key === order.value?.status))
const isCancelled = computed(() => order.value?.status === 'cancelado')

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}
function dt(value) {
  return value ? new Date(value).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' }) : ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    order.value = await ordersApi.get(route.params.id)
  } catch (e) {
    error.value = e.response?.status === 404 ? 'Este pedido no existe.' : 'No se pudo cargar el pedido.'
  } finally {
    loading.value = false
  }
}

async function cancel() {
  if (!confirm('¿Seguro que quieres cancelar este pedido?')) return
  cancelling.value = true
  try {
    order.value = await ordersApi.cancel(order.value.id)
  } catch (e) {
    alert(e.response?.data?.detail || 'No se pudo cancelar el pedido.')
  } finally {
    cancelling.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container detail">
    <RouterLink :to="{ name: 'account-orders' }" class="back"><ArrowLeft :size="16" /> Mis compras</RouterLink>

    <LoadingState v-if="loading" label="Cargando pedido…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <template v-else-if="order">
      <div v-if="isNew" class="banner">
        <PartyPopper :size="20" />
        <div>
          <strong>¡Pedido confirmado!</strong>
          <p>Te enviamos un correo con los detalles. Puedes seguir su estado aquí.</p>
        </div>
      </div>

      <header class="detail__head">
        <div>
          <h1 class="detail__title">Pedido #{{ order.number }}</h1>
          <p class="detail__sub">Realizado el {{ dt(order.created_at) }}</p>
        </div>
        <button
          v-if="order.status === 'pendiente'"
          class="btn btn--danger btn--sm"
          :disabled="cancelling"
          @click="cancel"
        >
          {{ cancelling ? 'Cancelando…' : 'Cancelar pedido' }}
        </button>
      </header>

      <!-- Estado -->
      <section class="card">
        <div v-if="isCancelled" class="cancelled">
          <XCircle :size="22" />
          <div>
            <strong>Pedido cancelado</strong>
            <p v-if="order.cancel_reason">{{ order.cancel_reason }}</p>
          </div>
        </div>
        <ol v-else class="timeline">
          <li
            v-for="(step, i) in STEPS"
            :key="step.key"
            class="timeline__step"
            :class="{ 'timeline__step--done': i <= stepIndex, 'timeline__step--current': i === stepIndex }"
          >
            <span class="timeline__dot"><CheckCircle2 v-if="i <= stepIndex" :size="18" /></span>
            <span class="timeline__label">{{ step.label }}</span>
          </li>
        </ol>
      </section>

      <div class="detail__grid">
        <!-- Productos -->
        <section class="card">
          <h2 class="card__title">Productos</h2>
          <ul class="items">
            <li v-for="item in order.items" :key="item.id" class="item">
              <span class="item__img">
                <img v-if="item.image" :src="item.image" :alt="item.description" />
                <ImageOff v-else :size="22" />
              </span>
              <span class="item__info">
                <span class="item__name">{{ item.description }}</span>
                <span class="item__meta">{{ item.quantity }} × {{ money(item.unit_price) }}</span>
              </span>
              <span class="item__total">{{ money(item.line_total) }}</span>
            </li>
          </ul>
          <div class="totals">
            <div class="totals__row"><span>Subtotal</span><span>{{ money(order.subtotal) }}</span></div>
            <div class="totals__row"><span>IVA</span><span>{{ money(order.tax_total) }}</span></div>
            <div class="totals__row totals__row--total"><span>Total</span><strong>{{ money(order.total) }}</strong></div>
          </div>
        </section>

        <!-- Entrega y pago -->
        <aside class="side">
          <section class="card">
            <h2 class="card__title">
              <component :is="order.fulfillment === 'recoge' ? Store : MapPin" :size="17" />
              {{ order.fulfillment_display }}
            </h2>
            <template v-if="order.fulfillment === 'envio'">
              <p class="side__line side__line--strong">{{ order.ship_recipient }}</p>
              <p class="side__line">{{ order.ship_line1 }}</p>
              <p v-if="order.ship_city" class="side__line">
                {{ order.ship_city }}<span v-if="order.ship_department">, {{ order.ship_department }}</span><span v-if="order.ship_country">, {{ order.ship_country }}</span>
              </p>
              <p v-if="order.ship_phone" class="side__line">Tel: {{ order.ship_phone }}</p>
              <p v-if="order.ship_phone_alt" class="side__line side__line--muted">Tel. secundario: {{ order.ship_phone_alt }}</p>
              <p v-if="order.ship_notes" class="side__line side__line--muted">{{ order.ship_notes }}</p>
            </template>
            <p v-else class="side__line">Recoge en <strong>{{ order.warehouse_name }}</strong></p>
          </section>

          <section class="card">
            <h2 class="card__title"><CreditCard :size="17" /> Pago</h2>
            <p class="side__line">{{ order.payment_display }}</p>
            <span class="badge" :class="order.is_paid ? 'badge--on' : 'badge--pending'">
              {{ order.is_paid ? 'Pagado' : 'Pendiente de pago' }}
            </span>
          </section>

          <section v-if="order.note" class="card">
            <h2 class="card__title">Nota</h2>
            <p class="side__line side__line--muted">{{ order.note }}</p>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail {
  padding: 28px 0 60px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-bottom: 16px;
}
.back:hover {
  color: var(--color-primary);
}
.banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
  border-radius: var(--radius-md);
  padding: 14px 18px;
  margin-bottom: 18px;
}
.banner p {
  font-size: 0.88rem;
  margin-top: 2px;
}
.detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}
.detail__title {
  font-size: 1.6rem;
}
.detail__sub {
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-top: 2px;
}
.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
}
.card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  margin-bottom: 14px;
}
.timeline {
  display: flex;
  justify-content: space-between;
  position: relative;
}
.timeline::before {
  content: '';
  position: absolute;
  top: 13px;
  left: 5%;
  right: 5%;
  height: 2px;
  background: var(--color-line);
  z-index: 0;
}
.timeline__step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 1;
  flex: 1;
}
.timeline__dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--color-line);
  color: #fff;
}
.timeline__step--done .timeline__dot {
  background: var(--color-primary);
  border-color: var(--color-primary);
}
.timeline__label {
  font-size: 0.82rem;
  color: var(--color-muted);
}
.timeline__step--done .timeline__label {
  color: var(--color-ink);
}
.timeline__step--current .timeline__label {
  color: var(--color-primary);
  font-weight: 600;
}
.cancelled {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #b91c1c;
}
.cancelled p {
  font-size: 0.88rem;
  color: var(--color-muted);
  margin-top: 2px;
}
.detail__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
.items {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.item__img {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-alt);
  display: grid;
  place-items: center;
  color: #cbd5e1;
  flex-shrink: 0;
}
.item__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.item__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.item__name {
  font-weight: 500;
  color: var(--color-ink);
}
.item__meta {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.item__total {
  font-weight: 600;
  white-space: nowrap;
}
.totals {
  border-top: 1px solid var(--color-line);
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.totals__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.92rem;
  color: var(--color-body);
}
.totals__row--total {
  padding-top: 8px;
  border-top: 1px solid var(--color-surface-alt);
  font-size: 1.05rem;
}
.totals__row--total strong {
  color: var(--color-primary);
}
.side__line {
  font-size: 0.9rem;
  color: var(--color-body);
  margin-bottom: 4px;
}
.side__line--strong {
  font-weight: 600;
  color: var(--color-ink);
}
.side__line--muted {
  color: var(--color-muted);
}
.badge {
  display: inline-block;
  margin-top: 8px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}
.badge--on {
  background: #ecfdf5;
  color: #047857;
}
.badge--pending {
  background: #fffbeb;
  color: #b45309;
}

@media (max-width: 760px) {
  .detail__grid {
    grid-template-columns: 1fr;
  }
}
</style>
