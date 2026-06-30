<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, Ban, Mail, ChevronRight } from 'lucide-vue-next'
import { salesApi } from '@/services/sales'
import { useAuthStore } from '@/stores/auth'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()
const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)

const sale = ref(null)
const loading = ref(true)
const error = ref('')
const emailInput = ref('')
const sending = ref(false)
const voiding = ref(false)

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}
function dt(value) {
  return new Date(value).toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    sale.value = await salesApi.get(route.params.id)
    emailInput.value = sale.value.receipt_email || sale.value.customer_email || ''
  } catch {
    error.value = 'No se pudo cargar la venta.'
  } finally {
    loading.value = false
  }
}

async function voidSale() {
  const ok = await confirmAction({
    title: 'Anular venta',
    text: 'Se devolverá la existencia al inventario. Esta acción no se puede deshacer.',
    confirmText: 'Anular',
    icon: 'warning'
  })
  if (!ok) return
  voiding.value = true
  try {
    sale.value = await salesApi.void(sale.value.id)
    toastSuccess('Venta anulada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo anular.')
  } finally {
    voiding.value = false
  }
}

async function resendReceipt() {
  sending.value = true
  try {
    const res = await salesApi.sendReceipt(sale.value.id, emailInput.value || undefined)
    toastSuccess(res.detail || 'Recibo enviado')
  } catch (e) {
    toastError(e.response?.data?.detail || e.response?.data?.email?.[0] || 'No se pudo enviar.')
  } finally {
    sending.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'sales' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a ventas
    </RouterLink>

    <LoadingState v-if="loading" label="Cargando venta…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="sale">
      <header class="page__head">
        <div>
          <div class="title-row">
            <h1 class="page__title">Venta {{ sale.code }}</h1>
            <span class="badge" :class="sale.status === 'completada' ? 'badge--on' : 'badge--off'">{{ sale.status_display }}</span>
          </div>
          <p class="page__subtitle">{{ dt(sale.created_at) }} · {{ sale.warehouse_name }}<span v-if="sale.created_by_name"> · {{ sale.created_by_name }}</span></p>
        </div>
        <button
          v-if="isAdmin && sale.status === 'completada'"
          class="btn btn--ghost"
          :disabled="voiding"
          @click="voidSale"
        >
          <Ban :size="16" /> Anular venta
        </button>
      </header>

      <div class="layout">
        <section class="card-box">
          <h2 class="card-box__title">Productos</h2>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>Producto</th><th class="num">Precio</th><th class="num">Cant.</th><th class="num">Subtotal</th></tr>
              </thead>
              <tbody>
                <tr v-for="i in sale.items" :key="i.id">
                  <td><span class="i-name">{{ i.description }}</span><code class="i-sku">{{ i.sku }}</code></td>
                  <td class="num">{{ money(i.unit_price) }}</td>
                  <td class="num">{{ i.quantity }}</td>
                  <td class="num strong">{{ money(i.line_total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <aside class="side">
          <div class="card-box">
            <h2 class="card-box__title">Cliente</h2>
            <RouterLink
              v-if="sale.customer"
              :to="{ name: 'customer-detail', params: { id: sale.customer } }"
              class="cust"
            >
              <span class="cust__avatar">{{ (sale.customer_name || '?').charAt(0).toUpperCase() }}</span>
              <span class="cust__info">
                <span class="cust__name">{{ sale.customer_name }}</span>
                <span v-if="sale.customer_document" class="cust__doc">{{ sale.customer_document }}</span>
              </span>
              <ChevronRight :size="18" class="cust__chev" />
            </RouterLink>
            <p v-else class="cust__none">Venta de mostrador (sin cliente)</p>
          </div>

          <div class="card-box">
            <h2 class="card-box__title">Resumen</h2>
            <div class="totals">
              <div v-if="Number(sale.discount)" class="totals__row"><span>Bruto</span><span>{{ money(Number(sale.total) + Number(sale.discount)) }}</span></div>
              <div v-if="Number(sale.discount)" class="totals__row"><span>Descuento</span><span>-{{ money(sale.discount) }}</span></div>
              <div class="totals__row"><span>Subtotal (sin IVA)</span><span>{{ money(sale.subtotal) }}</span></div>
              <div class="totals__row"><span>IVA</span><span>{{ money(sale.tax_total) }}</span></div>
              <div class="totals__row totals__row--total"><span>Total</span><span>{{ money(sale.total) }}</span></div>
            </div>
          </div>

          <div class="card-box">
            <h2 class="card-box__title">Pagos</h2>
            <div class="totals">
              <div v-for="p in sale.payments" :key="p.id" class="totals__row"><span>{{ p.method_display }}</span><span>{{ money(p.amount) }}</span></div>
              <div class="totals__row"><span>Pagado</span><span>{{ money(sale.paid) }}</span></div>
              <div v-if="Number(sale.change)" class="totals__row totals__row--change"><span>Cambio</span><span>{{ money(sale.change) }}</span></div>
            </div>
          </div>

          <div class="card-box">
            <h2 class="card-box__title">Recibo</h2>
            <label class="field">
              <span class="field__label">Enviar recibo a</span>
              <input v-model="emailInput" type="email" class="field__input" placeholder="correo@ejemplo.com" />
            </label>
            <button class="btn btn--ghost btn--block" :disabled="sending" @click="resendReceipt">
              <Mail :size="16" /> {{ sending ? 'Enviando…' : 'Enviar recibo' }}
            </button>
          </div>
        </aside>
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
  color: var(--color-muted);
  margin-bottom: 14px;
}
.back-link:hover {
  color: var(--color-primary);
}
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page__title {
  font-size: 1.6rem;
}
.page__subtitle {
  color: var(--color-muted);
  margin-top: 4px;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
  align-items: start;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card-box__title {
  font-size: 1.02rem;
  margin-bottom: 14px;
}
.cust {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px;
  margin: -4px;
  border-radius: var(--radius-sm);
  transition: background 0.15s ease;
}
.cust:hover {
  background: var(--color-surface-alt);
}
.cust__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 700;
  flex-shrink: 0;
}
.cust__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.cust__name {
  font-weight: 600;
  color: var(--color-ink);
}
.cust__doc {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.cust__chev {
  color: #cbd5cf;
}
.cust__none {
  color: var(--color-muted);
  font-size: 0.9rem;
}
.table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
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
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-surface-alt);
}
.table .num {
  text-align: right;
  white-space: nowrap;
}
.i-name {
  display: block;
  font-weight: 600;
  color: var(--color-ink);
}
.i-sku {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.strong {
  font-weight: 700;
}
.totals {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.totals__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--color-body);
}
.totals__row--total {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-ink);
  padding-top: 8px;
  border-top: 1px solid var(--color-line);
}
.totals__row--change {
  font-weight: 600;
  color: var(--color-success);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.field__label {
  font-size: 0.82rem;
  font-weight: 600;
}
.field__input {
  width: 100%;
  padding: 10px 12px;
  font-family: inherit;
  font-size: 0.92rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
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
@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
