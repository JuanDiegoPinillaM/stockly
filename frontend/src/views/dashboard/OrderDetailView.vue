<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, ImageOff, MapPin, Store, CreditCard, User, ArrowRight, XCircle } from 'lucide-vue-next'
import { staffOrdersApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const order = ref(null)
const loading = ref(true)
const error = ref('')
const working = ref(false)

const STATUS_CLASS = {
  pendiente: 'badge--pending',
  confirmado: 'badge--info',
  enviado: 'badge--info',
  entregado: 'badge--on',
  cancelado: 'badge--off'
}
// Etiqueta del botón para avanzar según el estado actual.
const ADVANCE_LABEL = {
  pendiente: 'Confirmar pedido',
  confirmado: 'Marcar como enviado',
  enviado: 'Marcar como entregado'
}
const advanceLabel = computed(() => ADVANCE_LABEL[order.value?.status] || '')

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
    order.value = await staffOrdersApi.get(route.params.id)
  } catch (e) {
    error.value = e.response?.status === 404 ? 'Este pedido no existe.' : 'No se pudo cargar el pedido.'
  } finally {
    loading.value = false
  }
}

async function advance() {
  working.value = true
  try {
    order.value = await staffOrdersApi.advance(order.value.id)
  } catch (e) {
    alert(e.response?.data?.detail || 'No se pudo avanzar el pedido.')
  } finally {
    working.value = false
  }
}

async function cancel() {
  const reason = prompt('Motivo de la cancelación (opcional):', '')
  if (reason === null) return
  working.value = true
  try {
    order.value = await staffOrdersApi.cancel(order.value.id, reason)
  } catch (e) {
    alert(e.response?.data?.detail || 'No se pudo cancelar el pedido.')
  } finally {
    working.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'orders' }" class="back"><ArrowLeft :size="16" /> Pedidos</RouterLink>

    <LoadingState v-if="loading" label="Cargando pedido…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <template v-else-if="order">
      <header class="head">
        <div class="head__left">
          <h1 class="head__title">Pedido #{{ order.number }}</h1>
          <span class="badge" :class="STATUS_CLASS[order.status]">{{ order.status_display }}</span>
        </div>
        <div v-if="order.is_open" class="head__actions">
          <button class="btn btn--danger btn--sm" :disabled="working" @click="cancel">
            <XCircle :size="16" /> Cancelar
          </button>
          <button v-if="advanceLabel" class="btn btn--primary btn--sm" :disabled="working" @click="advance">
            {{ advanceLabel }} <ArrowRight :size="16" />
          </button>
        </div>
      </header>
      <p class="head__date">Realizado el {{ dt(order.created_at) }}</p>

      <div class="grid">
        <!-- Productos -->
        <section class="card">
          <h2 class="card__title">Productos</h2>
          <ul class="items">
            <li v-for="item in order.items" :key="item.id" class="item">
              <span class="item__img">
                <img v-if="item.image" :src="item.image" :alt="item.description" />
                <ImageOff v-else :size="20" />
              </span>
              <span class="item__info">
                <span class="item__name">{{ item.description }}</span>
                <span class="item__meta">{{ item.sku }} · {{ item.quantity }} × {{ money(item.unit_price) }}</span>
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

        <aside class="side">
          <section class="card">
            <h2 class="card__title"><User :size="16" /> Cliente</h2>
            <RouterLink
              v-if="order.customer"
              :to="{ name: 'customer-detail', params: { id: order.customer } }"
              class="cust-link"
            >
              <span>
                <span class="side__line side__line--strong">{{ order.customer_name }}</span>
                <span class="side__line side__line--muted">{{ order.customer_email }}</span>
                <span v-if="order.customer_document" class="side__line side__line--muted">{{ order.customer_document }}</span>
              </span>
              <ArrowRight :size="16" />
            </RouterLink>
            <template v-else>
              <p class="side__line side__line--strong">{{ order.customer_name }}</p>
              <p class="side__line side__line--muted">{{ order.customer_email }}</p>
            </template>
          </section>

          <section class="card">
            <h2 class="card__title">
              <component :is="order.fulfillment === 'recoge' ? Store : MapPin" :size="16" />
              {{ order.fulfillment_display }}
            </h2>
            <p class="side__line">Punto: <strong>{{ order.warehouse_name }}</strong></p>
            <template v-if="order.fulfillment === 'envio'">
              <p class="side__line side__line--strong" style="margin-top: 8px">{{ order.ship_recipient }}</p>
              <p class="side__line">{{ order.ship_line1 }}</p>
              <p v-if="order.ship_city" class="side__line">
                {{ order.ship_city }}<span v-if="order.ship_department">, {{ order.ship_department }}</span><span v-if="order.ship_country">, {{ order.ship_country }}</span>
              </p>
              <p v-if="order.ship_phone" class="side__line">Tel: {{ order.ship_phone }}</p>
              <p v-if="order.ship_phone_alt" class="side__line side__line--muted">Tel. secundario: {{ order.ship_phone_alt }}</p>
              <p v-if="order.ship_notes" class="side__line side__line--muted">{{ order.ship_notes }}</p>
            </template>
          </section>

          <section class="card">
            <h2 class="card__title"><CreditCard :size="16" /> Pago</h2>
            <p class="side__line">{{ order.payment_display }}</p>
            <span class="badge" :class="order.is_paid ? 'badge--on' : 'badge--pending'">
              {{ order.is_paid ? 'Pagado' : 'Pendiente de pago' }}
            </span>
          </section>

          <section v-if="order.note" class="card">
            <h2 class="card__title">Nota del cliente</h2>
            <p class="side__line side__line--muted">{{ order.note }}</p>
          </section>

          <section v-if="order.status === 'cancelado' && order.cancel_reason" class="card">
            <h2 class="card__title">Motivo de cancelación</h2>
            <p class="side__line side__line--muted">{{ order.cancel_reason }}</p>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
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
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.head__left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.head__title {
  font-size: 1.5rem;
}
.head__actions {
  display: flex;
  gap: 10px;
}
.head__date {
  color: var(--color-muted);
  font-size: 0.9rem;
  margin: 4px 0 22px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}
.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 16px;
}
.card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.02rem;
  margin-bottom: 14px;
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
  width: 48px;
  height: 48px;
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
  font-size: 0.84rem;
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
.cust-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: inherit;
}
.cust-link > span {
  display: flex;
  flex-direction: column;
}
.cust-link .side__line {
  display: block;
}
.cust-link svg {
  color: var(--color-primary);
  flex-shrink: 0;
}
.cust-link:hover .side__line--strong {
  color: var(--color-primary);
}
.badge {
  display: inline-block;
  margin-top: 6px;
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
.badge--info {
  background: #eff6ff;
  color: #1d4ed8;
}
.badge--pending {
  background: #fffbeb;
  color: #b45309;
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
