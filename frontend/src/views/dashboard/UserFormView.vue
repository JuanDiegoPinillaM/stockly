<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import { usersApi } from '@/services/users'
import { warehousesApi } from '@/services/inventory'
import { ID_TYPES } from '@/utils/identification'
import { toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const ROLE_OPTIONS = [
  { value: 'cajero', label: 'Cajero' },
  { value: 'jefe_punto', label: 'Jefe de punto' },
  { value: 'admin', label: 'Administrador' }
]

const userId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(userId.value))

const form = ref({
  first_name: '',
  last_name: '',
  id_type: 'CC',
  id_number: '',
  phone: '',
  email: '',
  role: 'cajero',
  warehouse: '',
  is_active: true
})
const warehouses = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})

// El admin vende en cualquier bodega; cajero/jefe de punto operan en la suya.
const needsWarehouse = computed(() => form.value.role !== 'admin')

const canSave = computed(() => {
  const name = form.value.first_name.trim()
  const email = form.value.email.trim()
  return Boolean(name) && Boolean(form.value.id_number.trim()) && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
})

async function loadUser() {
  loading.value = true
  error.value = ''
  try {
    const u = await usersApi.get(userId.value)
    form.value = {
      first_name: u.first_name,
      last_name: u.last_name || '',
      id_type: u.id_type || 'CC',
      id_number: u.id_number || '',
      phone: u.phone || '',
      email: u.email,
      role: u.role,
      warehouse: u.warehouse || '',
      is_active: u.is_active
    }
  } catch {
    error.value = 'No se pudo cargar el usuario.'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  error.value = ''
  fieldErrors.value = {}
  // El admin no opera por bodega: se guarda sin asignación.
  const warehouse = needsWarehouse.value ? form.value.warehouse || null : null
  try {
    if (isEdit.value) {
      await usersApi.update(userId.value, { ...form.value, warehouse })
      toastSuccess('Usuario actualizado')
    } else {
      const created = await usersApi.create({
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        id_type: form.value.id_type,
        id_number: form.value.id_number,
        phone: form.value.phone,
        email: form.value.email,
        role: form.value.role,
        warehouse
      })
      toastSuccess(
        created.email_sent
          ? 'Usuario creado. Se envió la invitación por correo.'
          : 'Usuario creado, pero no se pudo enviar la invitación.'
      )
    }
    router.push({ name: 'users' })
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || 'No se pudo guardar el usuario.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

async function loadWarehouses() {
  try {
    const data = await warehousesApi.list({ page_size: 200, is_active: true })
    warehouses.value = data.results
  } catch {
    /* el selector queda vacío; no bloquea el alta */
  }
}

onMounted(() => {
  loadWarehouses()
  if (isEdit.value) loadUser()
})
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'users' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a usuarios
    </RouterLink>

    <header class="page__head">
      <h1 class="page__title">{{ isEdit ? 'Editar usuario' : 'Nuevo usuario' }}</h1>
      <p v-if="!isEdit" class="page__subtitle">Al crearlo se le envía una invitación por correo.</p>
    </header>

    <LoadingState v-if="loading" label="Cargando usuario…" />
    <p v-else-if="error && !saving" class="form-alert">{{ error }}</p>

    <form v-if="!loading" class="form-grid" @submit.prevent="save">
      <section class="card-box">
        <h2 class="card-box__title">Datos del usuario</h2>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Nombre *</span>
            <input v-model="form.first_name" class="field__input" maxlength="150" />
            <span v-if="fieldErrors.first_name" class="field__error">{{ fieldErrors.first_name[0] }}</span>
          </label>
          <label class="field">
            <span class="field__label">Apellido</span>
            <input v-model="form.last_name" class="field__input" maxlength="150" placeholder="Opcional" />
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Tipo de identificación *</span>
            <SearchSelect v-model="form.id_type" :options="ID_TYPES" value-key="value" label-key="label" />
          </label>
          <label class="field">
            <span class="field__label">Número de identificación *</span>
            <input v-model="form.id_number" class="field__input" maxlength="40" />
            <span v-if="fieldErrors.id_number" class="field__error">{{ fieldErrors.id_number[0] }}</span>
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Correo *</span>
            <input v-model="form.email" class="field__input" type="email" />
            <span v-if="fieldErrors.email" class="field__error">{{ fieldErrors.email[0] }}</span>
          </label>
          <label class="field">
            <span class="field__label">Teléfono</span>
            <input v-model="form.phone" class="field__input" maxlength="40" placeholder="Opcional" />
          </label>
        </div>

        <label class="field">
          <span class="field__label">Rol</span>
          <SearchSelect v-model="form.role" :options="ROLE_OPTIONS" value-key="value" label-key="label" />
        </label>

        <label v-if="needsWarehouse" class="field">
          <span class="field__label">Bodega asignada</span>
          <SearchSelect
            v-model="form.warehouse"
            :options="warehouses"
            clearable
            clear-label="Sin asignar"
            placeholder="Elige una bodega"
          />
          <span class="field__hint">El punto de venta operará sobre esta bodega.</span>
          <span v-if="fieldErrors.warehouse" class="field__error">{{ fieldErrors.warehouse[0] }}</span>
        </label>
      </section>

      <div class="form-actions">
        <label v-if="isEdit" class="toggle">
          <input v-model="form.is_active" type="checkbox" />
          <span>Usuario activo</span>
        </label>
        <span v-else></span>
        <button type="submit" class="btn btn--primary" :disabled="saving || !canSave">
          {{ saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear e invitar' }}
        </button>
      </div>
    </form>
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
.page__head {
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
}
.page__subtitle {
  color: var(--color-muted);
  margin-top: 4px;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-box__title {
  font-size: 1rem;
  color: var(--color-ink);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
}
.field__input {
  width: 100%;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field__error {
  font-size: 0.8rem;
  color: #dc2626;
}
.field__hint {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.92rem;
  color: var(--color-ink);
}
.form-actions {
  position: sticky;
  bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}
.form-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  margin-bottom: 14px;
}
</style>
