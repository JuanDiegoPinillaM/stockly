<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import { customersApi } from '@/services/sales'
import { ID_TYPES } from '@/utils/identification'
import { toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const customerId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(customerId.value))

const form = ref({
  id_type: 'CC',
  id_number: '',
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  is_active: true
})
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})

const canSave = computed(
  () => Boolean(form.value.first_name.trim()) && Boolean(form.value.id_number.trim())
)

async function loadCustomer() {
  loading.value = true
  error.value = ''
  try {
    const c = await customersApi.get(customerId.value)
    form.value = {
      id_type: c.id_type || 'CC',
      id_number: c.id_number || '',
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      email: c.email || '',
      phone: c.phone || '',
      is_active: c.is_active
    }
  } catch {
    error.value = 'No se pudo cargar el cliente.'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  error.value = ''
  fieldErrors.value = {}
  try {
    if (isEdit.value) {
      await customersApi.update(customerId.value, { ...form.value })
      toastSuccess('Cliente actualizado')
    } else {
      await customersApi.create({ ...form.value })
      toastSuccess('Cliente creado')
    }
    router.push({ name: 'customers' })
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || 'No se pudo guardar el cliente.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (isEdit.value) loadCustomer()
})
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'customers' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a clientes
    </RouterLink>

    <header class="page__head">
      <h1 class="page__title">{{ isEdit ? 'Editar cliente' : 'Nuevo cliente' }}</h1>
    </header>

    <LoadingState v-if="loading" label="Cargando cliente…" />
    <p v-else-if="error && !saving" class="form-alert">{{ error }}</p>

    <form v-if="!loading" class="form-grid" @submit.prevent="save">
      <section class="card-box">
        <h2 class="card-box__title">Datos del cliente</h2>

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
            <span class="field__label">Correo</span>
            <input v-model="form.email" type="email" class="field__input" placeholder="Opcional" />
            <span v-if="fieldErrors.email" class="field__error">{{ fieldErrors.email[0] }}</span>
          </label>
          <label class="field">
            <span class="field__label">Teléfono</span>
            <input v-model="form.phone" class="field__input" maxlength="40" placeholder="Opcional" />
          </label>
        </div>
      </section>

      <div class="form-actions">
        <label class="toggle">
          <input v-model="form.is_active" type="checkbox" />
          <span>Cliente activo</span>
        </label>
        <button type="submit" class="btn btn--primary" :disabled="saving || !canSave">
          {{ saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear cliente' }}
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
.form-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
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
  padding: 14px 20px;
  background: #fff;
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
