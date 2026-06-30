<script setup>
import { ref, onMounted } from 'vue'
import {
  Tag,
  Layers,
  Plus,
  Pencil,
  Power,
  PowerOff,
  Check,
  X,
  ChevronRight,
  GripVertical
} from 'lucide-vue-next'
import { brandsApi, attributeDefinitionsApi, attributeOptionsApi } from '@/services/catalog'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const brands = ref([])
const definitions = ref([])
const loading = ref(true)
const error = ref('')

// Formularios de alta
const newBrand = ref({ name: '' })
const newDef = ref({ name: '', has_swatch: false })
const brandError = ref('')
const defError = ref('')
const newOpt = ref({}) // defId -> { value, hex }

// Edición inline
const editingBrand = ref(null)
const editBrandData = ref({})
const editingDef = ref(null)
const editDefData = ref({})
const editingOpt = ref(null)
const editOptData = ref({})

// Atributos colapsables
const expanded = ref({})
function toggleExpand(id) {
  expanded.value[id] = !expanded.value[id]
}
function optDraft(defId) {
  if (!newOpt.value[defId]) newOpt.value[defId] = { value: '', hex: '#4F46E5' }
  return newOpt.value[defId]
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [b, d] = await Promise.all([
      brandsApi.list({ page_size: 200 }),
      attributeDefinitionsApi.list({ page_size: 200 })
    ])
    brands.value = b.results
    definitions.value = d.results
  } catch {
    error.value = 'No se pudieron cargar los atributos.'
  } finally {
    loading.value = false
  }
}

// ------------------------------ Marcas ------------------------------
async function addBrand() {
  brandError.value = ''
  try {
    await brandsApi.create({ ...newBrand.value })
    newBrand.value = { name: '' }
    await load()
    toastSuccess('Marca creada')
  } catch (e) {
    brandError.value = e.response?.data?.detail || 'No se pudo crear la marca.'
  }
}

function startEditBrand(brand) {
  editingBrand.value = brand.id
  editBrandData.value = { name: brand.name, is_active: brand.is_active }
}

async function saveBrand(id) {
  try {
    await brandsApi.update(id, editBrandData.value)
    editingBrand.value = null
    await load()
    toastSuccess('Marca actualizada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo guardar.')
  }
}

async function toggleBrand(brand) {
  const activate = !brand.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar marca' : 'Desactivar marca',
    text: activate
      ? `"${brand.name}" volverá a estar disponible.`
      : `"${brand.name}" dejará de aparecer al crear productos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await brandsApi.update(brand.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Marca activada' : 'Marca desactivada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

// --------------------- Atributos del catálogo ---------------------
async function addDefinition() {
  defError.value = ''
  const name = newDef.value.name.trim()
  if (!name) return
  try {
    const def = await attributeDefinitionsApi.create({
      name,
      has_swatch: newDef.value.has_swatch,
      position: definitions.value.length
    })
    newDef.value = { name: '', has_swatch: false }
    await load()
    expanded.value[def.id] = true
    toastSuccess('Atributo creado')
  } catch (e) {
    defError.value =
      e.response?.data?.errors?.name?.[0] ||
      e.response?.data?.detail ||
      'No se pudo crear el atributo.'
  }
}

function startEditDef(def) {
  editingDef.value = def.id
  editDefData.value = { name: def.name, has_swatch: def.has_swatch }
}

async function saveDef(id) {
  try {
    await attributeDefinitionsApi.update(id, editDefData.value)
    editingDef.value = null
    await load()
    toastSuccess('Atributo actualizado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo guardar.')
  }
}

async function toggleDef(def) {
  const activate = !def.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar atributo' : 'Desactivar atributo',
    text: activate
      ? `"${def.name}" volverá a estar disponible al crear productos.`
      : `"${def.name}" dejará de aparecer al crear productos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await attributeDefinitionsApi.update(def.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Atributo activado' : 'Atributo desactivado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

// ------------------------- Opciones -------------------------
async function addOption(def) {
  const draft = optDraft(def.id)
  const value = draft.value.trim()
  if (!value) return
  try {
    await attributeOptionsApi.create({
      definition: def.id,
      value,
      swatch_hex: def.has_swatch ? draft.hex : '',
      position: def.options.length
    })
    newOpt.value[def.id] = { value: '', hex: '#4F46E5' }
    await load()
    toastSuccess('Opción agregada')
  } catch (e) {
    toastError(
      e.response?.data?.errors?.value?.[0] ||
        e.response?.data?.detail ||
        'No se pudo agregar la opción.'
    )
  }
}

function startEditOpt(opt) {
  editingOpt.value = opt.id
  editOptData.value = { value: opt.value, swatch_hex: opt.swatch_hex || '#4F46E5' }
}

async function saveOpt(def, id) {
  try {
    const payload = { value: editOptData.value.value }
    if (def.has_swatch) payload.swatch_hex = editOptData.value.swatch_hex
    await attributeOptionsApi.update(id, payload)
    editingOpt.value = null
    await load()
    toastSuccess('Opción actualizada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo guardar.')
  }
}

async function toggleOpt(opt) {
  const activate = !opt.is_active
  try {
    await attributeOptionsApi.update(opt.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Opción activada' : 'Opción desactivada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

// --- Reordenar opciones (S, M, L, XL…) arrastrando ---
// El orden (`position`) es GLOBAL: se respeta en la tienda, el POS y todos los
// productos que usen este atributo.
const dragDef = ref(null)
const dragOptIndex = ref(null)
function onOptDragStart(def, i) {
  dragDef.value = def.id
  dragOptIndex.value = i
}
function onOptDragEnd() {
  dragDef.value = null
  dragOptIndex.value = null
}
async function onOptDrop(def, i) {
  if (dragDef.value !== def.id || dragOptIndex.value === null || dragOptIndex.value === i) {
    onOptDragEnd()
    return
  }
  const arr = [...def.options]
  const [moved] = arr.splice(dragOptIndex.value, 1)
  arr.splice(i, 0, moved)
  def.options = arr
  onOptDragEnd()
  arr.forEach((o, idx) => (o.position = idx))
  try {
    await Promise.all(arr.map((o, idx) => attributeOptionsApi.update(o.id, { position: idx })))
    toastSuccess('Orden actualizado')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo guardar el orden.')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <h1 class="page__title">Atributos</h1>
      <p class="page__subtitle">
        Define las marcas y los atributos de variación (Color, Talla, Almacenamiento…)
        que podrás reutilizar en tus productos.
      </p>
    </header>

    <LoadingState v-if="loading" label="Cargando atributos…" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else class="grid">
      <!-- Marcas -->
      <section class="card-box">
        <h2 class="card-box__title"><Tag :size="18" /> Marcas</h2>

        <form class="add-row" @submit.prevent="addBrand">
          <input v-model="newBrand.name" class="field__input" placeholder="Nombre de la marca" required maxlength="80" />
          <button type="submit" class="btn btn--primary btn--icon" :disabled="!newBrand.name.trim()"><Plus :size="18" /></button>
        </form>
        <p v-if="brandError" class="attr-alert attr-alert--sm">{{ brandError }}</p>

        <ul class="attr-list">
          <li v-for="brand in brands" :key="brand.id" class="attr-item">
            <template v-if="editingBrand === brand.id">
              <input v-model="editBrandData.name" class="field__input field__input--inline" />
              <div class="attr-item__actions">
                <button class="icon-btn icon-btn--ok" @click="saveBrand(brand.id)"><Check :size="16" /></button>
                <button class="icon-btn" @click="editingBrand = null"><X :size="16" /></button>
              </div>
            </template>
            <template v-else>
              <span class="attr-item__name">
                {{ brand.name }}
                <span v-if="!brand.is_active" class="attr-badge">Inactiva</span>
              </span>
              <span
                v-if="brand.products_count"
                class="attr-item__count"
                :title="`${brand.products_count} producto(s) usan esta marca`"
              >
                {{ brand.products_count }} prod.
              </span>
              <div class="attr-item__actions">
                <button class="icon-btn" title="Editar" @click="startEditBrand(brand)"><Pencil :size="15" /></button>
                <button
                  v-if="brand.is_active"
                  class="icon-btn icon-btn--danger"
                  title="Desactivar"
                  @click="toggleBrand(brand)"
                >
                  <PowerOff :size="15" />
                </button>
                <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggleBrand(brand)">
                  <Power :size="15" />
                </button>
              </div>
            </template>
          </li>
        </ul>
      </section>

      <!-- Atributos del catálogo -->
      <section class="card-box card-box--wide">
        <h2 class="card-box__title"><Layers :size="18" /> Atributos de variación</h2>
        <p class="attr-hint">
          Cada atributo agrupa sus opciones. Marca <strong>usa color</strong> si sus
          opciones llevan un color (como Color); el resto son texto (Talla, Almacenamiento…).
        </p>

        <form class="add-row" @submit.prevent="addDefinition">
          <input
            v-model="newDef.name"
            class="field__input"
            placeholder="Nuevo atributo (Color, Talla, Almacenamiento…)"
            maxlength="60"
          />
          <label class="toggle toggle--inline" title="Sus opciones llevan un color">
            <input v-model="newDef.has_swatch" type="checkbox" /> <span>usa color</span>
          </label>
          <button type="submit" class="btn btn--primary btn--icon" :disabled="!newDef.name.trim()"><Plus :size="18" /></button>
        </form>
        <p v-if="defError" class="attr-alert attr-alert--sm">{{ defError }}</p>

        <div class="def-list">
          <div v-for="def in definitions" :key="def.id" class="def" :class="{ 'def--off': !def.is_active }">
            <div class="def__head">
              <template v-if="editingDef === def.id">
                <input v-model="editDefData.name" class="field__input field__input--inline" />
                <label class="toggle toggle--inline">
                  <input v-model="editDefData.has_swatch" type="checkbox" /> <span>usa color</span>
                </label>
                <div class="attr-item__actions">
                  <button class="icon-btn icon-btn--ok" @click="saveDef(def.id)"><Check :size="16" /></button>
                  <button class="icon-btn" @click="editingDef = null"><X :size="16" /></button>
                </div>
              </template>
              <template v-else>
                <button class="def__expand" :class="{ 'def__expand--open': expanded[def.id] }" @click="toggleExpand(def.id)">
                  <ChevronRight :size="16" />
                </button>
                <button class="def__name" @click="toggleExpand(def.id)">{{ def.name }}</button>
                <span v-if="def.has_swatch" class="def__tag">usa color</span>
                <span v-if="!def.is_active" class="attr-badge">Inactivo</span>
                <span
                  class="attr-item__count"
                  :title="`${def.products_count} producto(s) usan este atributo`"
                >{{ def.options.length }} opc. · {{ def.products_count }} prod.</span>
                <div class="attr-item__actions">
                  <button class="icon-btn" title="Editar" @click="startEditDef(def)"><Pencil :size="15" /></button>
                  <button
                    v-if="def.is_active"
                    class="icon-btn icon-btn--danger"
                    title="Desactivar"
                    @click="toggleDef(def)"
                  >
                    <PowerOff :size="15" />
                  </button>
                  <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggleDef(def)">
                    <Power :size="15" />
                  </button>
                </div>
              </template>
            </div>

            <div v-if="expanded[def.id]" class="def__body">
              <p v-if="def.options.length > 1" class="opt-reorder-hint">
                Arrastra las opciones para ordenarlas; ese orden se respeta en la tienda y el POS.
              </p>
              <ul class="opt-list">
                <li
                  v-for="(opt, oi) in def.options"
                  :key="opt.id"
                  class="opt-item"
                  :class="{ 'opt-item--drag': dragDef === def.id && dragOptIndex === oi }"
                  :draggable="editingOpt !== opt.id"
                  @dragstart="onOptDragStart(def, oi)"
                  @dragover.prevent
                  @drop.prevent="onOptDrop(def, oi)"
                  @dragend="onOptDragEnd"
                >
                  <template v-if="editingOpt === opt.id">
                    <input v-if="def.has_swatch" v-model="editOptData.swatch_hex" type="color" class="color-input color-input--sm" />
                    <input v-model="editOptData.value" class="field__input field__input--inline" />
                    <div class="attr-item__actions">
                      <button class="icon-btn icon-btn--ok" @click="saveOpt(def, opt.id)"><Check :size="15" /></button>
                      <button class="icon-btn" @click="editingOpt = null"><X :size="15" /></button>
                    </div>
                  </template>
                  <template v-else>
                    <GripVertical :size="15" class="opt-item__grip" />
                    <span v-if="def.has_swatch" class="swatch swatch--sm" :style="{ background: opt.swatch_hex }"></span>
                    <span class="opt-item__name">
                      {{ opt.value }}
                      <span v-if="!opt.is_active" class="attr-badge">Inactiva</span>
                    </span>
                    <div class="attr-item__actions">
                      <button class="icon-btn" title="Editar" @click="startEditOpt(opt)"><Pencil :size="14" /></button>
                      <button
                        v-if="opt.is_active"
                        class="icon-btn icon-btn--danger"
                        title="Desactivar"
                        @click="toggleOpt(opt)"
                      >
                        <PowerOff :size="14" />
                      </button>
                      <button v-else class="icon-btn icon-btn--ok" title="Activar" @click="toggleOpt(opt)">
                        <Power :size="14" />
                      </button>
                    </div>
                  </template>
                </li>
                <li v-if="!def.options.length" class="opt-empty">Aún no hay opciones.</li>
              </ul>

              <form class="add-row add-row--opt" @submit.prevent="addOption(def)">
                <input
                  v-if="def.has_swatch"
                  v-model="optDraft(def.id).hex"
                  type="color"
                  class="color-input"
                  title="Elegir color"
                />
                <input
                  v-model="optDraft(def.id).value"
                  class="field__input"
                  :placeholder="def.has_swatch ? 'Nuevo color (Rojo…)' : 'Nueva opción (256GB, M…)'"
                  maxlength="80"
                />
                <button type="submit" class="btn btn--primary btn--icon" :disabled="!optDraft(def.id).value.trim()"><Plus :size="18" /></button>
              </form>
            </div>
          </div>
          <p v-if="!definitions.length" class="attr-muted">Aún no hay atributos. Crea el primero arriba.</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page__head {
  margin-bottom: 24px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}

.grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 2fr);
  gap: 20px;
  align-items: start;
}

.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card-box__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  margin-bottom: 16px;
}

.add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.field__input {
  flex: 1;
  width: 100%;
  min-width: 140px;
  padding: 10px 12px;
  font-family: inherit;
  font-size: 0.92rem;
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
.field__input--inline {
  flex: 1;
}
.color-input {
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  padding: 2px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  cursor: pointer;
}
.color-input--sm {
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
}
.btn--icon {
  padding: 10px;
  flex: 0 0 auto;
}

/* Toggle reutilizado del resto de la app */
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.86rem;
  font-weight: 500;
  color: var(--color-ink);
  white-space: nowrap;
}
.toggle input {
  appearance: none;
  -webkit-appearance: none;
  position: relative;
  flex-shrink: 0;
  width: 36px;
  height: 20px;
  border-radius: var(--radius-full);
  background: var(--color-line);
  cursor: pointer;
  transition: background 0.18s ease;
}
.toggle input:checked {
  background: var(--color-primary);
}
.toggle input::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s ease;
}
.toggle input:checked::after {
  transform: translateX(16px);
}

.attr-list {
  display: flex;
  flex-direction: column;
  margin-top: 12px;
}
.attr-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-surface-alt);
}
.swatch {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid var(--color-line);
}
.swatch--sm {
  flex: 0 0 20px;
  width: 20px;
  height: 20px;
}
.attr-item__name {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--color-ink);
}
.attr-item__count {
  font-size: 0.78rem;
  color: var(--color-muted);
  text-align: right;
}
.attr-badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: #fef2f2;
  color: #b91c1c;
}
.attr-item__actions {
  display: flex;
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

/* Catálogo de atributos */
.attr-hint {
  font-size: 0.84rem;
  color: var(--color-muted);
  margin-bottom: 14px;
}
.def-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}
.def {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.def--off {
  opacity: 0.65;
}
.def__head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-surface-alt);
}
.def__expand {
  display: inline-flex;
  color: var(--color-muted);
  transition: transform 0.18s ease;
}
.def__expand--open {
  transform: rotate(90deg);
}
.def__name {
  flex: 1;
  text-align: left;
  font-weight: 600;
  color: var(--color-ink);
}
.def__tag {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.def__body {
  padding: 8px 12px 14px;
}
.opt-list {
  display: flex;
  flex-direction: column;
}
.opt-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-surface-alt);
}
.opt-item[draggable='true'] {
  cursor: grab;
}
.opt-item[draggable='true']:active {
  cursor: grabbing;
}
.opt-item--drag {
  opacity: 0.4;
}
.opt-item__grip {
  color: var(--color-muted);
  flex-shrink: 0;
}
.opt-reorder-hint {
  font-size: 0.78rem;
  color: var(--color-muted);
  margin-bottom: 6px;
}
.opt-item__name {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--color-ink);
}
.opt-empty {
  padding: 8px 0;
  font-size: 0.84rem;
  color: var(--color-muted);
}
.add-row--opt {
  margin-top: 12px;
}

.attr-muted {
  color: var(--color-muted);
}
.attr-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}
.attr-alert--sm {
  padding: 6px 10px;
  font-size: 0.82rem;
  margin-top: 4px;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
