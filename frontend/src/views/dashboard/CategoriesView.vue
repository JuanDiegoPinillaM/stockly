<script setup>
import { ref, onMounted, computed } from 'vue'
import { FolderTree, Plus, Pencil, Power, PowerOff, ChevronDown } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { categoriesApi, subcategoriesApi } from '@/services/catalog'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import { useAuthStore } from '@/stores/auth'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)
const router = useRouter()

const categories = ref([])
const loading = ref(true)
const error = ref('')
const expanded = ref(new Set())

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await categoriesApi.list({ page_size: 100 })
    categories.value = data.results
  } catch {
    error.value = 'No se pudieron cargar las categorías.'
  } finally {
    loading.value = false
  }
}

function toggle(id) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

// --------------------------- Navegación ---------------------------
function newCategory() {
  router.push({ name: 'category-new' })
}
function editCategory(cat) {
  router.push({ name: 'category-edit', params: { id: cat.id } })
}
function newSubcategory(cat) {
  router.push({ name: 'subcategory-new', query: { category: cat.id } })
}
function editSubcategory(sub) {
  router.push({ name: 'subcategory-edit', params: { id: sub.id } })
}

async function toggleCategory(cat) {
  const activate = !cat.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar categoría' : 'Desactivar categoría',
    text: activate
      ? `"${cat.name}" volverá a estar disponible.`
      : `"${cat.name}" dejará de mostrarse al crear productos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await categoriesApi.update(cat.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Categoría activada' : 'Categoría desactivada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

async function toggleSubcategory(sub) {
  const activate = !sub.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar subcategoría' : 'Desactivar subcategoría',
    text: activate
      ? `"${sub.name}" volverá a estar disponible.`
      : `"${sub.name}" dejará de mostrarse al crear productos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await subcategoriesApi.update(sub.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Subcategoría activada' : 'Subcategoría desactivada')
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
        <h1 class="page__title">Categorías</h1>
        <p class="page__subtitle">Organiza tu catálogo en categorías y subcategorías.</p>
      </div>
      <button v-if="isAdmin" class="btn btn--primary" @click="newCategory">
        <Plus :size="18" /> Nueva categoría
      </button>
    </header>

    <LoadingState v-if="loading" label="Cargando categorías…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!categories.length" class="empty">
      <span class="empty__icon"><FolderTree :size="32" /></span>
      <h2 class="empty__title">Aún no hay categorías</h2>
      <p class="empty__text">
        {{ isAdmin ? 'Crea tu primera categoría para empezar a organizar productos.' : 'Un administrador aún no ha creado categorías.' }}
      </p>
    </div>

    <ul v-else class="cat-list">
      <li v-for="cat in categories" :key="cat.id" class="cat-card">
        <div class="cat-card__head" @click="toggle(cat.id)">
          <button class="cat-card__toggle" :class="{ open: expanded.has(cat.id) }">
            <ChevronDown :size="18" />
          </button>
          <div class="cat-card__info">
            <h3 class="cat-card__name">
              {{ cat.name }}
              <span v-if="!cat.is_active" class="cat-badge cat-badge--off">Inactiva</span>
            </h3>
            <p class="cat-card__meta">{{ cat.subcategories_count }} subcategoría(s)</p>
          </div>
          <div v-if="isAdmin" class="cat-card__actions" @click.stop>
            <button class="icon-btn" title="Editar" @click="editCategory(cat)">
              <Pencil :size="16" />
            </button>
            <button
              v-if="cat.is_active"
              class="icon-btn icon-btn--danger"
              title="Desactivar"
              @click="toggleCategory(cat)"
            >
              <PowerOff :size="16" />
            </button>
            <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggleCategory(cat)">
              <Power :size="16" />
            </button>
          </div>
        </div>

        <div v-if="expanded.has(cat.id)" class="cat-card__body">
          <ul v-if="cat.subcategories.length" class="sub-list">
            <li v-for="sub in cat.subcategories" :key="sub.id" class="sub-item">
              <div>
                <span class="sub-item__name">{{ sub.name }}</span>
                <span v-if="!sub.is_active" class="cat-badge cat-badge--off">Inactiva</span>
                <span class="sub-item__count">{{ sub.products_count }} producto(s)</span>
              </div>
              <div v-if="isAdmin" class="cat-card__actions">
                <button class="icon-btn" title="Editar" @click="editSubcategory(sub)">
                  <Pencil :size="15" />
                </button>
                <button
                  v-if="sub.is_active"
                  class="icon-btn icon-btn--danger"
                  title="Desactivar"
                  @click="toggleSubcategory(sub)"
                >
                  <PowerOff :size="15" />
                </button>
                <button
                  v-else
                  class="icon-btn icon-btn--ok"
                  title="Activar"
                  @click="toggleSubcategory(sub)"
                >
                  <Power :size="15" />
                </button>
              </div>
            </li>
          </ul>
          <p v-else class="cat-muted cat-muted--sm">Sin subcategorías todavía.</p>

          <button
            v-if="isAdmin"
            class="btn btn--ghost btn--sm"
            @click="newSubcategory(cat)"
          >
            <Plus :size="16" /> Agregar subcategoría
          </button>
        </div>
      </li>
    </ul>

  </div>
</template>

<style scoped>
.page__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cat-card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.cat-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  cursor: pointer;
}
.cat-card__head:hover {
  background: var(--color-surface-alt);
}
.cat-card__toggle {
  color: var(--color-muted);
  transition: transform 0.18s ease;
}
.cat-card__toggle.open {
  transform: rotate(180deg);
}
.cat-card__info {
  flex: 1;
  min-width: 0;
}
.cat-card__name {
  font-size: 1.02rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.cat-card__meta {
  font-size: 0.82rem;
  color: var(--color-muted);
}
.cat-card__actions {
  display: flex;
  gap: 6px;
}
.cat-card__body {
  padding: 4px 18px 18px 44px;
  border-top: 1px solid var(--color-line);
}
.sub-list {
  display: flex;
  flex-direction: column;
  margin: 8px 0 12px;
}
.sub-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-surface-alt);
}
.sub-item__name {
  font-weight: 500;
  color: var(--color-ink);
}
.sub-item__count {
  margin-left: 10px;
  font-size: 0.8rem;
  color: var(--color-muted);
}

.cat-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.cat-badge--off {
  background: #fef2f2;
  color: #b91c1c;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
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
.icon-btn--ok:hover {
  background: #ecfdf5;
}

.btn--sm {
  padding: 7px 14px;
  font-size: 0.85rem;
}

.cat-muted {
  color: var(--color-muted);
}
.cat-muted--sm {
  font-size: 0.88rem;
  margin-bottom: 12px;
}
.cat-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 18px;
}
.empty__title {
  font-size: 1.2rem;
  margin-bottom: 6px;
}
.empty__text {
  color: var(--color-muted);
  max-width: 420px;
}

/* Modal */
.modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.45);
}
.modal__box {
  width: 100%;
  max-width: 460px;
  background: #fff;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-line);
}
.modal__title {
  font-size: 1.1rem;
}
.modal__form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
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
  font-size: 0.95rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field--check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
}
</style>
