<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Trash2, CreditCard, Star } from 'lucide-vue-next'
import AccountNav from '@/components/AccountNav.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { paymentMethodsApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { confirmDelete, toastSuccess, toastError } from '@/utils/notify'

const KIND_OPTIONS = [
  { value: 'tarjeta', label: 'Tarjeta' },
  { value: 'nequi', label: 'Nequi' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'efectivo', label: 'Efectivo contra entrega' },
  { value: 'otro', label: 'Otro' }
]

const methods = ref([])
const loading = ref(true)
const error = ref('')
const editing = ref(null)
const saving = ref(false)

const canSave = computed(() => editing.value && editing.value.kind && editing.value.label?.trim())

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await paymentMethodsApi.list()
    methods.value = data.results || data
  } catch {
    error.value = 'No se pudieron cargar tus métodos de pago.'
  } finally {
    loading.value = false
  }
}

function openNew() {
  editing.value = { kind: 'tarjeta', label: '', is_default: false }
}
function cancel() {
  editing.value = null
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  try {
    await paymentMethodsApi.create(editing.value)
    editing.value = null
    await load()
    toastSuccess('Método de pago guardado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo guardar.')
  } finally {
    saving.value = false
  }
}

async function remove(m) {
  if (!(await confirmDelete('Se eliminará este método de pago.'))) return
  try {
    await paymentMethodsApi.remove(m.id)
    await load()
    toastSuccess('Método eliminado')
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
      <h2 class="head__title">Métodos de pago</h2>
      <button v-if="!editing" class="btn btn--primary" @click="openNew"><Plus :size="17" /> Agregar método</button>
    </div>

    <p class="note">Guarda tus formas de pago preferidas. No almacenamos números de tarjeta.</p>

    <section v-if="editing" class="card-box form">
      <div class="field-row">
        <label class="field">
          <span class="field__label">Tipo *</span>
          <SearchSelect v-model="editing.kind" :options="KIND_OPTIONS" value-key="value" label-key="label" />
        </label>
        <label class="field">
          <span class="field__label">Alias *</span>
          <input v-model="editing.label" class="field__input" placeholder="Ej. Visa terminada en 1234" maxlength="80" />
        </label>
      </div>
      <label class="check"><input v-model="editing.is_default" type="checkbox" /> Usar como predeterminado</label>
      <div class="form__actions">
        <button class="btn btn--ghost" @click="cancel">Cancelar</button>
        <button class="btn btn--primary" :disabled="saving || !canSave" @click="save">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
      </div>
    </section>

    <LoadingState v-if="loading" label="Cargando métodos…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!methods.length && !editing" class="empty">
      <CreditCard :size="34" />
      <p>Aún no tienes métodos de pago guardados.</p>
    </div>

    <div v-else class="list">
      <article v-for="m in methods" :key="m.id" class="pm">
        <div class="pm__body">
          <span class="pm__icon"><CreditCard :size="18" /></span>
          <div>
            <div class="pm__top">
              <strong>{{ m.label }}</strong>
              <span v-if="m.is_default" class="pm__default"><Star :size="12" /> Predeterminado</span>
            </div>
            <span class="pm__kind">{{ m.kind_display }}</span>
          </div>
        </div>
        <button class="icon-btn icon-btn--danger" title="Eliminar" @click="remove(m)"><Trash2 :size="15" /></button>
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
  margin-bottom: 8px;
}
.head__title {
  font-size: 1.2rem;
}
.note {
  color: var(--color-muted);
  font-size: 0.88rem;
  margin-bottom: 16px;
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
.pm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px;
}
.pm__body {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pm__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.pm__top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pm__default {
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
.pm__kind {
  font-size: 0.84rem;
  color: var(--color-muted);
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
