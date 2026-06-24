<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ShoppingBag, ChevronRight } from 'lucide-vue-next'
import { ordersApi } from '@/services/store'
import AccountNav from '@/components/AccountNav.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()
const orders = ref([])
const loading = ref(true)
const error = ref('')

const STATUS_CLASS = {
  pendiente: 'badge--pending',
  confirmado: 'badge--info',
  enviado: 'badge--info',
  entregado: 'badge--on',
  cancelado: 'badge--off',
  completada: 'badge--on',
  anulada: 'badge--off'
}

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}
function dt(value) {
  return new Date(value).toLocaleDateString('es-CO', { dateStyle: 'medium' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    // Historial unificado: pedidos en línea + compras en tienda (POS).
    orders.value = await ordersApi.purchases()
  } catch {
    error.value = 'No se pudieron cargar tus compras.'
  } finally {
    loading.value = false
  }
}

function open(o) {
  const name = o.kind === 'order' ? 'account-order-detail' : 'account-sale-detail'
  router.push({ name, params: { id: o.id } })
}

onMounted(load)
</script>

<template>
  <div class="container account">
    <h1 class="account__title">Mi cuenta</h1>
    <AccountNav />

    <LoadingState v-if="loading" label="Cargando tus compras…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!orders.length" class="empty">
      <span class="empty__icon"><ShoppingBag :size="34" /></span>
      <h2 class="empty__title">Aún no tienes compras</h2>
      <p class="empty__text">Cuando hagas tu primer pedido, aquí verás su historial y estado.</p>
      <RouterLink :to="{ name: 'home' }" class="btn btn--primary">Ir a la tienda</RouterLink>
    </div>

    <ul v-else class="orders">
      <li
        v-for="o in orders"
        :key="o.kind + '-' + o.id"
        class="order"
        @click="open(o)"
      >
        <div class="order__main">
          <div class="order__head">
            <span class="order__number">
              {{ o.kind === 'order' ? 'Pedido' : 'Compra' }} #{{ o.number }}
            </span>
            <span class="chip" :class="o.kind === 'order' ? 'chip--online' : 'chip--store'">
              {{ o.kind === 'order' ? 'En línea' : 'En tienda' }}
            </span>
            <span class="badge" :class="STATUS_CLASS[o.status]">{{ o.status_display }}</span>
          </div>
          <span class="order__meta">{{ dt(o.date) }} · {{ o.total_items }} producto(s)</span>
        </div>
        <div class="order__right">
          <span class="order__total">{{ money(o.total) }}</span>
          <ChevronRight :size="18" class="order__chev" />
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.account {
  padding: 28px 0 60px;
}
.account__title {
  font-size: 1.6rem;
  margin-bottom: 20px;
}
.orders {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.order {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.order:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--color-primary);
}
.order--static {
  cursor: default;
}
.order--static:hover {
  box-shadow: none;
  border-color: var(--color-line);
}
.chip {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.chip--online {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.chip--store {
  background: var(--color-accent-soft);
  color: var(--color-accent-dark);
}
.order__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.order__number {
  font-weight: 700;
  color: var(--color-ink);
}
.order__meta {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.order__right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.order__total {
  font-weight: 700;
  color: var(--color-ink);
}
.order__chev {
  color: #cbd5e1;
}
.badge {
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
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 60px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 8px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  max-width: 420px;
  margin-bottom: 12px;
}
</style>
