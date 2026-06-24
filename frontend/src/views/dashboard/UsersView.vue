<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Plus, Pencil, Power, PowerOff, Mail, Search } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { usersApi } from '@/services/users'
import { useAuthStore } from '@/stores/auth'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'

const auth = useAuthStore()
const myId = computed(() => auth.user?.id)
const router = useRouter()

const ROLE_OPTIONS = [
  { value: 'cajero', label: 'Cajero' },
  { value: 'jefe_punto', label: 'Jefe de punto' },
  { value: 'admin', label: 'Administrador' },
  { value: 'comprador', label: 'Comprador' }
]

const users = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')

// Filtros
const search = ref('')
const roleFilter = ref('')
const showInactive = ref(false)
let searchTimer = null

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page_size: 100 }
    if (search.value) params.search = search.value
    if (roleFilter.value) params.role = roleFilter.value
    if (!showInactive.value) params.is_active = true
    const data = await usersApi.list(params)
    users.value = data.results
    count.value = data.count
  } catch {
    error.value = 'No se pudieron cargar los usuarios.'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}
watch([roleFilter, showInactive], load)

function openEdit(u) {
  router.push({ name: 'user-edit', params: { id: u.id } })
}

async function toggle(u) {
  const activate = !u.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar usuario' : 'Desactivar usuario',
    text: activate
      ? `"${u.first_name}" volverá a tener acceso.`
      : `"${u.first_name}" no podrá iniciar sesión, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await usersApi.update(u.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Usuario activado' : 'Usuario desactivado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

async function resend(u) {
  try {
    await usersApi.resendInvitation(u.id)
    toastSuccess('Invitación reenviada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo reenviar.')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <div>
        <h1 class="page__title">Usuarios</h1>
        <p class="page__subtitle">{{ count }} usuario(s). Crear envía una invitación por correo.</p>
      </div>
      <RouterLink :to="{ name: 'user-new' }" class="btn btn--primary">
        <Plus :size="18" /> Nuevo usuario
      </RouterLink>
    </header>

    <div class="toolbar">
      <div class="toolbar__search">
        <Search :size="18" class="toolbar__search-icon" />
        <input v-model="search" class="toolbar__input" type="search" placeholder="Buscar por nombre o correo…" @input="onSearch" />
      </div>
      <div class="toolbar__filter">
        <SearchSelect
          v-model="roleFilter"
          :options="ROLE_OPTIONS"
          value-key="value"
          label-key="label"
          clearable
          clear-label="Todos los roles"
          placeholder="Todos los roles"
        />
      </div>
      <label class="toolbar__check">
        <input v-model="showInactive" type="checkbox" />
        <span>Mostrar inactivos</span>
      </label>
    </div>

    <LoadingState v-if="loading" label="Cargando usuarios…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Usuario</th>
            <th>Correo</th>
            <th>Rol</th>
            <th>Bodega</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in users"
            :key="u.id"
            class="row--clickable"
            :class="{ 'row--inactive': !u.is_active }"
            @click="openEdit(u)"
          >
            <td>
              <span class="u-avatar">
                <img v-if="u.avatar" :src="u.avatar" alt="" />
                <template v-else>{{ (u.first_name || u.email).charAt(0).toUpperCase() }}</template>
              </span>
              <span class="u-name">
                {{ u.full_name }}
                <span v-if="u.id === myId" class="u-you">tú</span>
              </span>
            </td>
            <td>
              <span class="u-email">{{ u.email }}</span>
              <span v-if="!u.is_email_verified" class="u-unverified">sin verificar</span>
            </td>
            <td>
              <span class="badge" :class="u.role === 'admin' ? 'badge--admin' : 'badge--user'">
                {{ u.role_display }}
              </span>
            </td>
            <td>
              <span v-if="u.warehouse_name" class="u-wh">{{ u.warehouse_name }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <span class="badge" :class="u.is_active ? 'badge--on' : 'badge--off'">
                {{ u.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td class="actions" @click.stop>
              <button
                v-if="!u.is_email_verified"
                class="icon-btn"
                title="Reenviar invitación"
                @click="resend(u)"
              >
                <Mail :size="15" />
              </button>
              <button class="icon-btn" title="Editar" @click="openEdit(u)"><Pencil :size="15" /></button>
              <button
                v-if="u.is_active"
                class="icon-btn icon-btn--danger"
                title="Desactivar"
                :disabled="u.id === myId"
                @click="toggle(u)"
              >
                <PowerOff :size="15" />
              </button>
              <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggle(u)">
                <Power :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="6" class="muted empty">No hay usuarios para mostrar.</td>
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
.toolbar__filter {
  width: 220px;
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
.row--clickable {
  cursor: pointer;
}
.row--clickable:hover {
  background: var(--color-surface-alt);
}
.row--inactive {
  opacity: 0.55;
}
.u-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.82rem;
  margin-right: 9px;
  overflow: hidden;
  flex-shrink: 0;
  vertical-align: middle;
}
.u-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.u-name {
  font-weight: 600;
  color: var(--color-ink);
}
.u-you {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  padding: 1px 6px;
  border-radius: var(--radius-full);
  margin-left: 6px;
}
.u-email {
  color: var(--color-body);
}
.u-wh {
  color: var(--color-body);
  font-size: 0.88rem;
}
.u-unverified {
  display: block;
  font-size: 0.72rem;
  color: #b45309;
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
.badge--admin {
  background: #eef2ff;
  color: #4338ca;
}
.badge--user {
  background: var(--color-surface-alt);
  color: var(--color-body);
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
.icon-btn:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.icon-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.icon-btn--danger:hover:not(:disabled) {
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
  text-align: center;
  padding: 26px;
}
</style>
