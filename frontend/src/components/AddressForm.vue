<script setup>
import { ref, computed, onMounted } from 'vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { geoApi } from '@/services/store'
import { phone as validatePhone, formatPhone, onlyDigits } from '@/utils/validators'

const props = defineProps({
  // Valores iniciales (al editar); null/undefined = dirección nueva.
  initial: { type: Object, default: null },
  saving: { type: Boolean, default: false },
  submitLabel: { type: String, default: 'Guardar' }
})
const emit = defineEmits(['submit', 'cancel'])

const countries = ref([])
const departments = ref([])
const cities = ref([])

function seed() {
  const a = props.initial || {}
  return {
    id: a.id ?? null,
    label: a.label || '',
    recipient: a.recipient || '',
    line1: a.line1 || '',
    // Formatea solo si ya cumple 10 dígitos; conserva valores heredados.
    phone: onlyDigits(a.phone).length === 10 ? formatPhone(a.phone) : (a.phone || ''),
    country: a.country || '',
    department: a.department || '',
    city: a.city || '',
    notes: a.notes || '',
    is_default: a.is_default ?? false
  }
}

const form = ref(seed())
const errors = ref({ recipient: '', line1: '', phone: '', city: '' })

const canSave = computed(() => {
  const f = form.value
  return Boolean(
    f.recipient?.trim() && f.line1?.trim() && f.phone?.trim() &&
    f.country && f.department && f.city
  )
})

function onPhoneInput(e) {
  form.value.phone = formatPhone(e.target.value)
  if (errors.value.phone) errors.value.phone = ''
}

async function onCountry(id) {
  form.value.country = id
  form.value.department = ''
  form.value.city = ''
  departments.value = id ? await geoApi.departments(id) : []
  cities.value = []
}
async function onDepartment(id) {
  form.value.department = id
  form.value.city = ''
  cities.value = id ? await geoApi.cities(id) : []
  if (errors.value.city) errors.value.city = ''
}

function validate() {
  errors.value.recipient = form.value.recipient.trim() ? '' : 'Ingresa el destinatario.'
  errors.value.line1 = form.value.line1.trim() ? '' : 'Ingresa la dirección.'
  errors.value.phone = validatePhone(form.value.phone)
  errors.value.city = form.value.city ? '' : 'Selecciona la ciudad.'
  return !errors.value.recipient && !errors.value.line1 && !errors.value.phone && !errors.value.city
}

function submit() {
  if (!validate()) return
  emit('submit', { ...form.value })
}

onMounted(async () => {
  try {
    countries.value = await geoApi.countries()
  } catch {
    /* sin países no se puede guardar, pero el form igual se muestra */
  }
  if (form.value.country) {
    departments.value = await geoApi.departments(form.value.country)
    if (form.value.department) cities.value = await geoApi.cities(form.value.department)
  } else if (countries.value.length === 1) {
    // Colombia es el único país por ahora: lo preselecciona y carga departamentos.
    form.value.country = countries.value[0].id
    departments.value = await geoApi.departments(form.value.country)
  }
})
</script>

<template>
  <form class="addr-form" novalidate @submit.prevent="submit">
    <div class="field-row">
      <label class="field">
        <span class="field__label">Etiqueta</span>
        <input v-model="form.label" class="field__input" placeholder="Casa, Oficina…" />
      </label>
      <label class="field">
        <span class="field__label">Destinatario *</span>
        <input v-model="form.recipient" class="field__input" @input="errors.recipient = ''" />
        <span v-if="errors.recipient" class="field__error">{{ errors.recipient }}</span>
      </label>
    </div>

    <label class="field">
      <span class="field__label">Dirección *</span>
      <input v-model="form.line1" class="field__input" placeholder="Calle 00 # 00-00" @input="errors.line1 = ''" />
      <span v-if="errors.line1" class="field__error">{{ errors.line1 }}</span>
    </label>

    <div class="field-row">
      <label class="field">
        <span class="field__label">País *</span>
        <SearchSelect :model-value="form.country" :options="countries" value-key="id" label-key="name" placeholder="Selecciona país" @update:model-value="onCountry" />
      </label>
      <label class="field">
        <span class="field__label">Departamento *</span>
        <SearchSelect :model-value="form.department" :options="departments" value-key="id" label-key="name" placeholder="Selecciona departamento" :disabled="!form.country" @update:model-value="onDepartment" />
      </label>
    </div>

    <div class="field-row">
      <label class="field">
        <span class="field__label">Ciudad *</span>
        <SearchSelect v-model="form.city" :options="cities" value-key="id" label-key="name" placeholder="Selecciona ciudad" :disabled="!form.department" />
        <span v-if="errors.city" class="field__error">{{ errors.city }}</span>
      </label>
      <label class="field">
        <span class="field__label">Teléfono *</span>
        <input
          :value="form.phone"
          class="field__input"
          type="tel"
          inputmode="numeric"
          maxlength="12"
          placeholder="300 123 4567"
          @input="onPhoneInput"
        />
        <span v-if="errors.phone" class="field__error">{{ errors.phone }}</span>
      </label>
    </div>

    <label class="field">
      <span class="field__label">Indicaciones</span>
      <input v-model="form.notes" class="field__input" placeholder="Apto, torre, referencia…" />
    </label>

    <label class="check"><input v-model="form.is_default" type="checkbox" /> Usar como predeterminada</label>

    <div class="addr-form__actions">
      <button type="button" class="btn btn--ghost" @click="emit('cancel')">Cancelar</button>
      <button type="submit" class="btn btn--primary" :disabled="saving || !canSave">
        {{ saving ? 'Guardando…' : submitLabel }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.addr-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
.field__error {
  font-size: 0.8rem;
  color: #dc2626;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 560px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  cursor: pointer;
}
.addr-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
