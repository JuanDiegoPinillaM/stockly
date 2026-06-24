<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { warehousesApi } from '@/services/inventory'
import { toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const warehouseId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(warehouseId.value))

const form = ref({ name: '', code: '', address: '', is_active: true })
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})

const canSave = computed(() => Boolean(form.value.name.trim()))

async function loadWarehouse() {
  loading.value = true
  error.value = ''
  try {
    const w = await warehousesApi.get(warehouseId.value)
    form.value = {
      name: w.name,
      code: w.code || '',
      address: w.address || '',
      is_active: w.is_active
    }
  } catch {
    error.value = 'No se pudo cargar la bodega.'
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
      await warehousesApi.update(warehouseId.value, { ...form.value })
      toastSuccess('Bodega actualizada')
    } else {
      await warehousesApi.create({ ...form.value })
      toastSuccess('Bodega creada')
    }
    router.push({ name: 'warehouses' })
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || 'No se pudo guardar la bodega.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (isEdit.value) loadWarehouse()
})
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'warehouses' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a bodegas
    </RouterLink>

    <header class="page__head">
      <h1 class="page__title">{{ isEdit ? 'Editar bodega' : 'Nueva bodega' }}</h1>
    </header>

    <LoadingState v-if="loading" label="Cargando bodega…" />
    <p v-else-if="error && !saving" class="form-alert">{{ error }}</p>

    <form v-if="!loading" class="form-grid" @submit.prevent="save">
      <section class="card-box">
        <h2 class="card-box__title">Datos de la bodega</h2>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Nombre *</span>
            <input v-model="form.name" class="field__input" required maxlength="120" />
            <span v-if="fieldErrors.name" class="field__error">{{ fieldErrors.name[0] }}</span>
          </label>
          <label class="field">
            <span class="field__label">Código</span>
            <input v-model="form.code" class="field__input" maxlength="20" placeholder="Opcional" />
          </label>
        </div>

        <label class="field">
          <span class="field__label">Dirección</span>
          <input v-model="form.address" class="field__input" maxlength="200" placeholder="Opcional" />
        </label>
      </section>

      <div class="form-actions">
        <label class="toggle">
          <input v-model="form.is_active" type="checkbox" />
          <span>Bodega activa</span>
        </label>
        <button type="submit" class="btn btn--primary" :disabled="saving || !canSave">
          {{ saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear bodega' }}
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
