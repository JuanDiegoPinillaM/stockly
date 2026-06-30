<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Warehouse, Building2, Plus, Pencil, Power, PowerOff, MapPin } from 'lucide-vue-next'
import { warehousesApi } from '@/services/inventory'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()

const warehouses = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await warehousesApi.list({ page_size: 200 })
    warehouses.value = data.results
  } catch {
    error.value = 'No se pudieron cargar las bodegas.'
  } finally {
    loading.value = false
  }
}

function openDetail(w) {
  router.push({ name: 'warehouse-detail', params: { id: w.id } })
}

function openEdit(w) {
  router.push({ name: 'warehouse-edit', params: { id: w.id } })
}

function localityOf(w) {
  return [w.city_name, w.department_name].filter(Boolean).join(', ')
}

async function toggle(w) {
  const activate = !w.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar bodega' : 'Desactivar bodega',
    text: activate
      ? `"${w.name}" volverá a estar disponible.`
      : `"${w.name}" dejará de aparecer en los movimientos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await warehousesApi.update(w.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Bodega activada' : 'Bodega desactivada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Bodegas</h1>
        <p class="page__subtitle">Almacenes o ubicaciones donde se guarda la existencia.</p>
      </div>
      <RouterLink :to="{ name: 'warehouse-new' }" class="btn btn--primary">
        <Plus :size="18" /> Nueva bodega
      </RouterLink>
    </header>

    <LoadingState v-if="loading" label="Cargando bodegas…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!warehouses.length" class="empty">
      <span class="empty__icon"><Warehouse :size="30" /></span>
      <h2 class="empty__title">Aún no hay bodegas</h2>
      <p class="empty__text">Crea tu primera bodega para registrar existencia.</p>
      <RouterLink :to="{ name: 'warehouse-new' }" class="btn btn--primary">
        <Plus :size="18" /> Nueva bodega
      </RouterLink>
    </div>

    <div v-else class="card-box">
      <table class="table">
        <thead>
          <tr>
            <th>Bodega</th>
            <th>Código</th>
            <th>Ubicación</th>
            <th>Teléfono</th>
            <th>Estado</th>
            <th>En tienda</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="w in warehouses"
            :key="w.id"
            class="row--clickable"
            :class="{ 'row--inactive': !w.is_active }"
            @click="openDetail(w)"
          >
            <td>
              <div class="wh-cell">
                <span class="wh-thumb" :class="{ 'wh-thumb--empty': !w.photo }">
                  <img v-if="w.photo" :src="w.photo" :alt="w.name" loading="lazy" />
                  <Building2 v-else :size="18" />
                </span>
                <div class="wh-text">
                  <span class="wh-name">{{ w.name }}</span>
                  <span v-if="w.address" class="wh-addr"><MapPin :size="12" /> {{ w.address }}</span>
                </div>
              </div>
            </td>
            <td><code v-if="w.code" class="code">{{ w.code }}</code><span v-else class="muted">—</span></td>
            <td>{{ localityOf(w) || '—' }}</td>
            <td>{{ w.phone || '—' }}</td>
            <td>
              <span class="badge" :class="w.is_active ? 'badge--on' : 'badge--off'">
                {{ w.is_active ? 'Activa' : 'Inactiva' }}
              </span>
            </td>
            <td>
              <span v-if="w.show_in_store" class="badge badge--store">Visible</span>
              <span v-else class="muted">—</span>
            </td>
            <td class="actions" @click.stop>
              <button class="icon-btn" title="Editar" @click="openEdit(w)"><Pencil :size="15" /></button>
              <button
                v-if="w.is_active"
                class="icon-btn icon-btn--danger"
                title="Desactivar"
                @click="toggle(w)"
              >
                <PowerOff :size="15" />
              </button>
              <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggle(w)">
                <Power :size="15" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
.table th {
  text-align: left;
  padding: 11px 12px;
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
}
.table td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.row--clickable {
  cursor: pointer;
}
.row--clickable:hover {
  background: var(--color-surface-alt);
}
.row--inactive {
  opacity: 0.55;
}
.wh-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.wh-thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
}
.wh-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.wh-thumb--empty {
  color: var(--color-muted);
}
.wh-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.wh-name {
  font-weight: 600;
  color: var(--color-ink);
}
.wh-addr {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--color-muted);
}
.wh-addr svg {
  flex-shrink: 0;
}
.code {
  font-size: 0.82rem;
  background: var(--color-surface-alt);
  padding: 2px 7px;
  border-radius: 6px;
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
.badge--store {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
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
  transition: all 0.16s ease;
}
.icon-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}
.icon-btn--ok {
  color: var(--color-success);
  border-color: #a7f3d0;
}
.muted {
  color: var(--color-muted);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
  gap: 6px;
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
  margin-bottom: 10px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  margin-bottom: 14px;
}
</style>
