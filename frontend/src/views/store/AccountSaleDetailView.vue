<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, Store, CreditCard, Receipt } from 'lucide-vue-next'
import { ordersApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const sale = ref(null)
const loading = ref(true)
const error = ref('')

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
    sale.value = await ordersApi.sale(route.params.id)
  } catch (e) {
    error.value = e.response?.status === 404 ? 'Esta compra no existe.' : 'No se pudo cargar la compra.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container detail">
    <RouterLink :to="{ name: 'account-orders' }" class="back"><ArrowLeft :size="16" /> Mis compras</RouterLink>

    <LoadingState v-if="loading" label="Cargando compra…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <template v-else-if="sale">
      <header class="detail__head">
        <div>
          <h1 class="detail__title">Compra #{{ sale.number }}</h1>
          <p class="detail__sub">{{ dt(sale.created_at) }} · Compra en tienda</p>
        </div>
        <span class="badge" :class="sale.status === 'completada' ? 'badge--on' : 'badge--off'">
          {{ sale.status_display }}
        </span>
      </header>

      <div class="detail__grid">
        <!-- Productos -->
        <section class="card">
          <h2 class="card__title">Productos</h2>
          <ul class="items">
            <li v-for="item in sale.items" :key="item.id" class="item">
              <span class="item__info">
                <span class="item__name">{{ item.description }}</span>
                <span class="item__meta">{{ item.sku }} · {{ item.quantity }} × {{ money(item.unit_price) }}</span>
              </span>
              <span class="item__total">{{ money(item.line_total) }}</span>
            </li>
          </ul>
          <div class="totals">
            <div class="totals__row"><span>Subtotal</span><span>{{ money(sale.subtotal) }}</span></div>
            <div class="totals__row"><span>IVA</span><span>{{ money(sale.tax_total) }}</span></div>
            <div v-if="Number(sale.discount)" class="totals__row"><span>Descuento</span><span>-{{ money(sale.discount) }}</span></div>
            <div class="totals__row totals__row--total"><span>Total</span><strong>{{ money(sale.total) }}</strong></div>
          </div>
        </section>

        <aside class="side">
          <section class="card">
            <h2 class="card__title"><Store :size="17" /> Punto de venta</h2>
            <p class="side__line">{{ sale.warehouse_name }}</p>
          </section>

          <section class="card">
            <h2 class="card__title"><CreditCard :size="17" /> Pago</h2>
            <div v-for="p in sale.payments" :key="p.id" class="side__row">
              <span>{{ p.method_display }}</span>
              <span>{{ money(p.amount) }}</span>
            </div>
            <div class="side__row side__row--muted">
              <span>Pagado</span><span>{{ money(sale.paid) }}</span>
            </div>
            <div v-if="Number(sale.change)" class="side__row side__row--muted">
              <span>Cambio</span><span>{{ money(sale.change) }}</span>
            </div>
          </section>

          <section v-if="sale.receipt_email" class="card">
            <h2 class="card__title"><Receipt :size="17" /> Recibo</h2>
            <p class="side__line side__line--muted">Enviado a {{ sale.receipt_email }}</p>
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
.detail__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
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
.items {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.item__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
}
.side__line--muted {
  color: var(--color-muted);
}
.side__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--color-body);
  margin-bottom: 6px;
}
.side__row--muted {
  color: var(--color-muted);
}
.badge {
  font-size: 0.74rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.badge--on {
  background: #ecfdf5;
  color: #047857;
}
.badge--off {
  background: #fef2f2;
  color: #b91c1c;
}

@media (max-width: 760px) {
  .detail__grid {
    grid-template-columns: 1fr;
  }
}
</style>
