<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Pencil, Trash2, MapPin, Star } from 'lucide-vue-next'
import AccountNav from '@/components/AccountNav.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { addressesApi, geoApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { confirmDelete, toastSuccess, toastError } from '@/utils/notify'

const addresses = ref([])
const loading = ref(true)
const error = ref('')
const editing = ref(null) // null = cerrado; {} = nuevo; {id,...} = editar
const saving = ref(false)

// Catálogos de ubicación (cascada).
const countries = ref([])
const departments = ref([])
const cities = ref([])

function blank() {
  return {
    label: '', recipient: '', line1: '', phone: '',
    country: '', department: '', city: '', notes: '', is_default: false
  }
}

const canSave = computed(() => {
  const e = editing.value
  return (
    e &&
    e.recipient?.trim() &&
    e.line1?.trim() &&
    e.phone?.trim() &&
    e.country &&
    e.department &&
    e.city
  )
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await addressesApi.list()
    addresses.value = data.results || data
  } catch {
    error.value = 'No se pudieron cargar tus direcciones.'
  } finally {
    loading.value = false
  }
}

async function openNew() {
  editing.value = blank()
  departments.value = []
  cities.value = []
  // Colombia es el único país por ahora: lo preselecciona y carga departamentos.
  if (countries.value.length === 1) {
    editing.value.country = countries.value[0].id
    departments.value = await geoApi.departments(editing.value.country)
  }
}

async function openEdit(a) {
  editing.value = {
    id: a.id,
    label: a.label || '',
    recipient: a.recipient || '',
    line1: a.line1 || '',
    phone: a.phone || '',
    country: a.country || '',
    department: a.department || '',
    city: a.city || '',
    notes: a.notes || '',
    is_default: a.is_default
  }
  departments.value = a.country ? await geoApi.departments(a.country) : []
  cities.value = a.department ? await geoApi.cities(a.department) : []
}

function cancel() {
  editing.value = null
}

async function onCountry(id) {
  editing.value.country = id
  editing.value.department = ''
  editing.value.city = ''
  departments.value = id ? await geoApi.departments(id) : []
  cities.value = []
}
async function onDepartment(id) {
  editing.value.department = id
  editing.value.city = ''
  cities.value = id ? await geoApi.cities(id) : []
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  try {
    if (editing.value.id) {
      await addressesApi.update(editing.value.id, editing.value)
    } else {
      await addressesApi.create(editing.value)
    }
    editing.value = null
    await load()
    toastSuccess('Dirección guardada')
  } catch (e) {
    const err = e.response?.data
    toastError(err?.errors?.city?.[0] || err?.errors?.department?.[0] || err?.detail || 'No se pudo guardar.')
  } finally {
    saving.value = false
  }
}

async function remove(a) {
  if (!(await confirmDelete('Se eliminará esta dirección.'))) return
  try {
    await addressesApi.remove(a.id)
    await load()
    toastSuccess('Dirección eliminada')
  } catch {
    toastError('No se pudo eliminar.')
  }
}

onMounted(async () => {
  try {
    countries.value = await geoApi.countries()
  } catch {
    /* el form igual abre; sin países no se puede guardar */
  }
  await load()
})
</script>

<template>
  <div class="container account">
    <h1 class="account__title">Mi cuenta</h1>
    <AccountNav />

    <div class="head">
      <h2 class="head__title">Direcciones</h2>
      <button v-if="!editing" class="btn btn--primary" @click="openNew"><Plus :size="17" /> Nueva dirección</button>
    </div>

    <!-- Formulario -->
    <section v-if="editing" class="card-box form">
      <div class="field-row">
        <label class="field"><span class="field__label">Etiqueta</span><input v-model="editing.label" class="field__input" placeholder="Casa, Oficina…" /></label>
        <label class="field"><span class="field__label">Destinatario *</span><input v-model="editing.recipient" class="field__input" /></label>
      </div>

      <label class="field"><span class="field__label">Dirección *</span><input v-model="editing.line1" class="field__input" placeholder="Calle 00 # 00-00" /></label>

      <div class="field-row">
        <label class="field">
          <span class="field__label">País *</span>
          <SearchSelect :model-value="editing.country" :options="countries" value-key="id" label-key="name" placeholder="Selecciona país" @update:model-value="onCountry" />
        </label>
        <label class="field">
          <span class="field__label">Departamento *</span>
          <SearchSelect :model-value="editing.department" :options="departments" value-key="id" label-key="name" placeholder="Selecciona departamento" :disabled="!editing.country" @update:model-value="onDepartment" />
        </label>
      </div>

      <div class="field-row">
        <label class="field">
          <span class="field__label">Ciudad *</span>
          <SearchSelect v-model="editing.city" :options="cities" value-key="id" label-key="name" placeholder="Selecciona ciudad" :disabled="!editing.department" />
        </label>
        <label class="field"><span class="field__label">Teléfono *</span><input v-model="editing.phone" class="field__input" placeholder="300 123 4567" /></label>
      </div>

      <label class="field"><span class="field__label">Indicaciones</span><input v-model="editing.notes" class="field__input" placeholder="Apto, torre, referencia…" /></label>

      <label class="check"><input v-model="editing.is_default" type="checkbox" /> Usar como predeterminada</label>
      <div class="form__actions">
        <button class="btn btn--ghost" @click="cancel">Cancelar</button>
        <button class="btn btn--primary" :disabled="saving || !canSave" @click="save">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
      </div>
    </section>

    <LoadingState v-if="loading" label="Cargando direcciones…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!addresses.length && !editing" class="empty">
      <MapPin :size="34" />
      <p>Aún no tienes direcciones guardadas.</p>
    </div>

    <div v-else class="list">
      <article v-for="a in addresses" :key="a.id" class="addr">
        <div class="addr__body">
          <div class="addr__top">
            <strong>{{ a.label || a.recipient }}</strong>
            <span v-if="a.is_default" class="addr__default"><Star :size="12" /> Predeterminada</span>
          </div>
          <p class="addr__line">{{ a.recipient }}</p>
          <p class="addr__line">{{ a.line1 }}</p>
          <p class="addr__line">
            {{ a.city_name }}<span v-if="a.department_name">, {{ a.department_name }}</span><span v-if="a.country_name">, {{ a.country_name }}</span>
          </p>
          <p v-if="a.phone" class="addr__muted">Tel: {{ a.phone }}</p>
          <p v-if="a.notes" class="addr__muted">{{ a.notes }}</p>
        </div>
        <div class="addr__actions">
          <button class="icon-btn" title="Editar" @click="openEdit(a)"><Pencil :size="15" /></button>
          <button class="icon-btn icon-btn--danger" title="Eliminar" @click="remove(a)"><Trash2 :size="15" /></button>
        </div>
      </article>
    </div>
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
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.head__title {
  font-size: 1.2rem;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.85rem;
  font-weight: 600;
}
.field__input {
  width: 100%;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
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
.check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  cursor: pointer;
}
.form__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.addr {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px;
}
.addr__top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.addr__default {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  padding: 2px 7px;
  border-radius: var(--radius-full);
}
.addr__line {
  color: var(--color-body);
  font-size: 0.92rem;
}
.addr__muted {
  color: var(--color-muted);
  font-size: 0.86rem;
}
.addr__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
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
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 24px;
  color: var(--color-muted);
}
</style>
