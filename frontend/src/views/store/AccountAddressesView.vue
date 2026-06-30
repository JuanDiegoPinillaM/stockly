<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Pencil, Trash2, MapPin, Star } from 'lucide-vue-next'
import AccountNav from '@/components/AccountNav.vue'
import AddressForm from '@/components/AddressForm.vue'
import { addressesApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { confirmDelete, toastSuccess, toastError } from '@/utils/notify'

const addresses = ref([])
const loading = ref(true)
const error = ref('')
const editing = ref(null) // null = cerrado; {} = nueva; {id,...} = editar
const saving = ref(false)

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

function openNew() {
  editing.value = {}
}
function openEdit(a) {
  editing.value = a
}
function cancel() {
  editing.value = null
}

async function save(payload) {
  saving.value = true
  try {
    if (payload.id) {
      await addressesApi.update(payload.id, payload)
    } else {
      await addressesApi.create(payload)
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

onMounted(load)
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
      <AddressForm
        :key="editing.id || 'new'"
        :initial="editing"
        :saving="saving"
        @submit="save"
        @cancel="cancel"
      />
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
