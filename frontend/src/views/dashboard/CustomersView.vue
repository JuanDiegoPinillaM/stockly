<script setup>
import { ref, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Users, Plus, Pencil, Power, PowerOff, Search } from 'lucide-vue-next'
import { customersApi } from '@/services/sales'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()

const customers = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')
const search = ref('')
const showInactive = ref(false)
let timer = null

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page_size: 200 }
    if (search.value) params.search = search.value
    if (!showInactive.value) params.is_active = true
    const data = await customersApi.list(params)
    customers.value = data.results
    count.value = data.count
  } catch {
    error.value = 'No se pudieron cargar los clientes.'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}
watch(showInactive, load)

function openDetail(c) {
  router.push({ name: 'customer-detail', params: { id: c.id } })
}
function openEdit(c) {
  router.push({ name: 'customer-edit', params: { id: c.id } })
}

async function toggle(c) {
  const activate = !c.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar cliente' : 'Desactivar cliente',
    text: activate ? `"${c.full_name}" volverá a estar disponible.` : `"${c.full_name}" se ocultará, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await customersApi.update(c.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Cliente activado' : 'Cliente desactivado')
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
        <h1 class="page__title">Clientes</h1>
        <p class="page__subtitle">{{ count }} cliente(s).</p>
      </div>
      <RouterLink :to="{ name: 'customer-new' }" class="btn btn--primary">
        <Plus :size="18" /> Nuevo cliente
      </RouterLink>
    </header>

    <div class="toolbar">
      <div class="toolbar__search">
        <Search :size="18" class="toolbar__search-icon" />
        <input v-model="search" class="toolbar__input" type="search" placeholder="Buscar por identificación, nombre o correo…" @input="onSearch" />
      </div>
      <label class="toolbar__check">
        <input v-model="showInactive" type="checkbox" />
        <span>Mostrar inactivos</span>
      </label>
    </div>

    <LoadingState v-if="loading" label="Cargando clientes…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!customers.length" class="empty">
      <span class="empty__icon"><Users :size="30" /></span>
      <h2 class="empty__title">No hay clientes</h2>
      <p class="empty__text">Crea tu primer cliente para asociarlo a las ventas.</p>
      <RouterLink :to="{ name: 'customer-new' }" class="btn btn--primary"><Plus :size="18" /> Nuevo cliente</RouterLink>
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Identificación</th>
            <th>Contacto</th>
            <th class="num">Compras</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in customers" :key="c.id" class="row--clickable" :class="{ 'row--inactive': !c.is_active }" @click="openDetail(c)">
            <td><span class="c-name">{{ c.full_name }}</span></td>
            <td>
              <span v-if="c.id_number">{{ c.id_type }} {{ c.id_number }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <span v-if="c.email" class="c-contact">{{ c.email }}</span>
              <span v-if="c.phone" class="c-contact muted">{{ c.phone }}</span>
              <span v-if="!c.email && !c.phone" class="muted">—</span>
            </td>
            <td class="num">{{ c.sales_count }}</td>
            <td>
              <span class="badge" :class="c.is_active ? 'badge--on' : 'badge--off'">{{ c.is_active ? 'Activo' : 'Inactivo' }}</span>
            </td>
            <td class="actions" @click.stop>
              <button class="icon-btn" title="Editar" @click="openEdit(c)"><Pencil :size="15" /></button>
              <button v-if="c.is_active" class="icon-btn icon-btn--danger" title="Desactivar" @click="toggle(c)"><PowerOff :size="15" /></button>
              <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggle(c)"><Power :size="15" /></button>
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
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.toolbar__search {
  position: relative;
  flex: 1;
  min-width: 220px;
}
.toolbar__search-icon {
  position: absolute;
  left: 13px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}
.toolbar__input {
  width: 100%;
  padding: 11px 14px 11px 40px;
  font-family: inherit;
  font-size: 0.93rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.toolbar__check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.88rem;
  color: var(--color-body);
  cursor: pointer;
  white-space: nowrap;
}
.table-wrap {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
.table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-line);
}
.table td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--color-surface-alt);
  vertical-align: middle;
}
.table .num {
  text-align: right;
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
.c-name {
  font-weight: 600;
  color: var(--color-ink);
}
.c-contact {
  display: block;
  font-size: 0.86rem;
}
.muted {
  color: var(--color-muted);
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
