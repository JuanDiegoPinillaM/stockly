<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft, Pencil, Mail, Phone, IdCard, MapPin, ShoppingBag } from 'lucide-vue-next'
import { customersApi } from '@/services/sales'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const router = useRouter()

const customer = ref(null)
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
    customer.value = await customersApi.get(route.params.id)
  } catch (e) {
    error.value = e.response?.status === 404 ? 'Este cliente no existe.' : 'No se pudo cargar el cliente.'
  } finally {
    loading.value = false
  }
}

function openPurchase(p) {
  if (p.kind === 'order') router.push({ name: 'order-detail', params: { id: p.id } })
  else router.push({ name: 'sale-detail', params: { id: p.id } })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'customers' }" class="back-link"><ArrowLeft :size="17" /> Volver a clientes</RouterLink>

    <LoadingState v-if="loading" label="Cargando cliente…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <template v-else-if="customer">
      <header class="head">
        <div class="head__left">
          <span class="avatar">
            <img v-if="customer.avatar" :src="customer.avatar" alt="" />
            <template v-else>{{ (customer.full_name || '?').charAt(0).toUpperCase() }}</template>
          </span>
          <div>
            <h1 class="head__title">
              {{ customer.full_name }}
              <span class="badge" :class="customer.is_active ? 'badge--on' : 'badge--off'">
                {{ customer.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </h1>
            <p class="head__sub">Cliente desde {{ dt(customer.date_joined) }} · {{ customer.sales_count }} compra(s)</p>
          </div>
        </div>
        <RouterLink :to="{ name: 'customer-edit', params: { id: customer.id } }" class="btn btn--ghost btn--sm">
          <Pencil :size="15" /> Editar
        </RouterLink>
      </header>

      <div class="grid">
        <!-- Información -->
        <section class="card">
          <h2 class="card__title">Información</h2>
          <ul class="info">
            <li><IdCard :size="16" /> <span>{{ customer.id_type_display || customer.id_type }} {{ customer.id_number || '—' }}</span></li>
            <li><Mail :size="16" /> <span>{{ customer.email || 'Sin correo' }}</span></li>
            <li><Phone :size="16" /> <span>{{ customer.phone || 'Sin teléfono' }}</span></li>
          </ul>

          <h3 class="card__subtitle"><MapPin :size="15" /> Direcciones</h3>
          <div v-if="!customer.addresses.length" class="muted">Sin direcciones guardadas.</div>
          <ul v-else class="addresses">
            <li v-for="a in customer.addresses" :key="a.id" class="address">
              <span class="address__recipient">
                {{ a.recipient }}
                <span v-if="a.is_default" class="tag">Predeterminada</span>
              </span>
              <span class="address__line">{{ a.line1 }}</span>
              <span class="address__line">
                {{ a.city }}<span v-if="a.department">, {{ a.department }}</span><span v-if="a.country">, {{ a.country }}</span>
              </span>
              <span v-if="a.phone" class="address__phone">Tel: {{ a.phone }}</span>
            </li>
          </ul>
        </section>

        <!-- Historial de compras -->
        <section class="card">
          <h2 class="card__title">Historial de compras</h2>
          <div v-if="!customer.purchases.length" class="empty">
            <span class="empty__icon"><ShoppingBag :size="26" /></span>
            <p>Este cliente aún no tiene compras.</p>
          </div>
          <table v-else class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Canal</th>
                <th>Fecha</th>
                <th class="num">Total</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in customer.purchases" :key="p.kind + '-' + p.id" class="row--clickable" @click="openPurchase(p)">
                <td class="strong">#{{ p.number }}</td>
                <td>
                  <span class="chip" :class="p.kind === 'order' ? 'chip--online' : 'chip--store'">
                    {{ p.kind === 'order' ? 'En línea' : 'En tienda' }}
                  </span>
                </td>
                <td class="nowrap">{{ dt(p.date) }}</td>
                <td class="num strong">{{ money(p.total) }}</td>
                <td><span class="badge" :class="STATUS_CLASS[p.status]">{{ p.status_display }}</span></td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-muted);
  margin-bottom: 14px;
}
.back-link:hover {
  color: var(--color-primary);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.head__left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 1.5rem;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.head__title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.5rem;
}
.head__sub {
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-top: 2px;
}
.grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card__title {
  font-size: 1.05rem;
  margin-bottom: 16px;
}
.card__subtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  margin: 20px 0 12px;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.info li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.93rem;
  color: var(--color-body);
}
.info svg {
  color: var(--color-muted);
  flex-shrink: 0;
}
.addresses {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.address {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}
.address__recipient {
  font-weight: 600;
  color: var(--color-ink);
  display: flex;
  align-items: center;
  gap: 8px;
}
.address__line,
.address__phone {
  color: var(--color-muted);
}
.tag {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  padding: 2px 7px;
  border-radius: var(--radius-full);
}
.muted {
  color: var(--color-muted);
  font-size: 0.9rem;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
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
}
.table td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--color-surface-alt);
}
.table .num {
  text-align: right;
  white-space: nowrap;
}
.nowrap {
  white-space: nowrap;
}
.strong {
  font-weight: 700;
  color: var(--color-ink);
}
.row--clickable {
  cursor: pointer;
}
.row--clickable:hover {
  background: var(--color-surface-alt);
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
.badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
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
  gap: 8px;
  padding: 40px 20px;
  color: var(--color-muted);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
