<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import SearchSelect from '@/components/SearchSelect.vue'
import { categoriesApi, subcategoriesApi } from '@/services/catalog'
import { toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const subcategoryId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(subcategoryId.value))

const categories = ref([])
const form = ref({ category: '', name: '', description: '', is_active: true })
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})

const canSave = computed(() => Boolean(form.value.category) && Boolean(form.value.name.trim()))

async function init() {
  loading.value = true
  error.value = ''
  try {
    const cats = await categoriesApi.list({ page_size: 100, is_active: true })
    categories.value = cats.results
    if (isEdit.value) {
      const s = await subcategoriesApi.get(subcategoryId.value)
      form.value = {
        category: s.category,
        name: s.name,
        description: s.description || '',
        is_active: s.is_active
      }
    } else if (route.query.category) {
      // Prellena la categoría desde la que se abrió el alta.
      form.value.category = Number(route.query.category)
    }
  } catch {
    error.value = 'No se pudo cargar la información.'
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
      await subcategoriesApi.update(subcategoryId.value, { ...form.value })
      toastSuccess('Subcategoría actualizada')
    } else {
      await subcategoriesApi.create({ ...form.value })
      toastSuccess('Subcategoría creada')
    }
    router.push({ name: 'categories' })
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || 'No se pudo guardar la subcategoría.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    saving.value = false
  }
}

onMounted(init)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'categories' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a categorías
    </RouterLink>

    <header class="page__head">
      <h1 class="page__title">{{ isEdit ? 'Editar subcategoría' : 'Nueva subcategoría' }}</h1>
    </header>

    <LoadingState v-if="loading" label="Cargando…" />
    <p v-else-if="error && !saving" class="form-alert">{{ error }}</p>

    <form v-if="!loading" class="form-grid" @submit.prevent="save">
      <section class="card-box">
        <h2 class="card-box__title">Datos de la subcategoría</h2>

        <label class="field">
          <span class="field__label">Categoría *</span>
          <SearchSelect v-model="form.category" :options="categories" placeholder="Selecciona la categoría" />
          <span v-if="fieldErrors.category" class="field__error">{{ fieldErrors.category[0] }}</span>
        </label>

        <label class="field">
          <span class="field__label">Nombre *</span>
          <input v-model="form.name" class="field__input" required maxlength="120" />
          <span v-if="fieldErrors.name" class="field__error">{{ fieldErrors.name[0] }}</span>
        </label>

        <label class="field">
          <span class="field__label">Descripción</span>
          <textarea v-model="form.description" class="field__input" rows="3" placeholder="Opcional"></textarea>
        </label>
      </section>

      <div class="form-actions">
        <label class="toggle">
          <input v-model="form.is_active" type="checkbox" />
          <span>Subcategoría activa</span>
        </label>
        <button type="submit" class="btn btn--primary" :disabled="saving || !canSave">
          {{ saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear subcategoría' }}
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
