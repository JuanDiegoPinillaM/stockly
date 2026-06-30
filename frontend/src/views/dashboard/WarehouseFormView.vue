<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ArrowLeft, Upload, Trash2 } from 'lucide-vue-next'
import { warehousesApi } from '@/services/inventory'
import { geoApi } from '@/services/store'
import { toastSuccess, toastError } from '@/utils/notify'
import { email as validateEmail, phone as validatePhone, formatPhone, onlyDigits } from '@/utils/validators'
import LoadingState from '@/components/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const warehouseId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(warehouseId.value))

// Días del horario (los 7 + festivos).
const DAYS = [
  { key: 'mon', label: 'Lunes' },
  { key: 'tue', label: 'Martes' },
  { key: 'wed', label: 'Miércoles' },
  { key: 'thu', label: 'Jueves' },
  { key: 'fri', label: 'Viernes' },
  { key: 'sat', label: 'Sábado' },
  { key: 'sun', label: 'Domingo' },
  { key: 'holidays', label: 'Festivos' }
]
const WEEK_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

function defaultSchedule() {
  const s = {}
  for (const { key } of DAYS) {
    // Por defecto: entre semana abierto 8–18, fines/festivos cerrados.
    const open = ['sat', 'sun', 'holidays'].includes(key) ? false : true
    s[key] = { closed: !open, open: '08:00', close: '18:00' }
  }
  return s
}

// Fusiona el horario guardado (puede venir parcial o vacío) con los defaults
// para garantizar que las 8 entradas existan en el formulario.
function mergeSchedule(saved) {
  const base = defaultSchedule()
  if (saved && typeof saved === 'object') {
    for (const { key } of DAYS) {
      const entry = saved[key]
      if (entry && typeof entry === 'object') {
        base[key] = {
          closed: Boolean(entry.closed),
          open: entry.open || '08:00',
          close: entry.close || '18:00'
        }
      }
    }
  }
  return base
}

const form = ref({
  name: '',
  code: '',
  address: '',
  is_active: true,
  description: '',
  email: '',
  phone: '',
  hours: '',
  schedule: defaultSchedule(),
  map_embed_url: '',
  show_in_store: true,
  // Ubicación (para el ruteo por cercanía); solo `city` se persiste.
  country: null,
  department: null,
  city: null
})

// Copia el horario de un día a todos los días entre semana (L–V).
function applyToWeekdays(key) {
  const src = form.value.schedule[key]
  for (const k of ['mon', 'tue', 'wed', 'thu', 'fri']) {
    form.value.schedule[k] = { ...src }
  }
}
// Copia el horario de un día a TODA la semana (no a festivos).
function applyToAllWeek(key) {
  const src = form.value.schedule[key]
  for (const k of WEEK_KEYS) {
    form.value.schedule[k] = { ...src }
  }
}
const countries = ref([])
const departments = ref([])
const cities = ref([])
const photoFile = ref(null) // archivo nuevo seleccionado (File) o null
const photoPreview = ref('') // url para previsualizar (objeto local o la guardada)
const removePhoto = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const fieldErrors = ref({})
// Errores de validación en el cliente (teléfono/correo).
const clientErrors = ref({ phone: '', email: '' })

// Autoformatea el teléfono mientras se escribe: solo dígitos, agrupados 3-3-4,
// tope de 10 dígitos ("300 123 4567").
function onPhoneInput(e) {
  form.value.phone = formatPhone(e.target.value)
  if (clientErrors.value.phone) clientErrors.value.phone = ''
}

// Valida teléfono y correo (ambos opcionales; si vienen, deben ser válidos).
function validate() {
  clientErrors.value.phone = form.value.phone.trim() ? validatePhone(form.value.phone) : ''
  clientErrors.value.email = form.value.email.trim() ? validateEmail(form.value.email) : ''
  return !clientErrors.value.phone && !clientErrors.value.email
}
// Evita que los watch borren la selección durante la precarga al editar.
let hydrating = false

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
      is_active: w.is_active,
      description: w.description || '',
      email: w.email || '',
      // Formatea solo si ya cumple los 10 dígitos; conserva valores heredados raros.
      phone: onlyDigits(w.phone).length === 10 ? formatPhone(w.phone) : (w.phone || ''),
      hours: w.hours || '',
      schedule: mergeSchedule(w.schedule),
      map_embed_url: w.map_embed_url || '',
      show_in_store: w.show_in_store,
      country: w.country || null,
      department: w.department || null,
      city: w.city || null
    }
    photoPreview.value = w.photo || ''
    // Precarga el cascadeo si la bodega ya tiene ubicación.
    if (w.country) {
      hydrating = true
      departments.value = await geoApi.departments(w.country)
      if (w.department) cities.value = await geoApi.cities(w.department)
      hydrating = false
    }
  } catch {
    error.value = 'No se pudo cargar la bodega.'
  } finally {
    loading.value = false
  }
}

watch(() => form.value.country, async (country) => {
  if (hydrating) return
  form.value.department = null
  form.value.city = null
  departments.value = country ? await geoApi.departments(country) : []
  cities.value = []
})

watch(() => form.value.department, async (department) => {
  if (hydrating) return
  form.value.city = null
  cities.value = department ? await geoApi.cities(department) : []
})

function onPhotoChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  photoFile.value = file
  removePhoto.value = false
  photoPreview.value = URL.createObjectURL(file)
}

function clearPhoto() {
  photoFile.value = null
  photoPreview.value = ''
  removePhoto.value = true
}

// Si el usuario pega el <iframe ...> completo de Google Maps, extrae el src.
function normalizeMapUrl() {
  const raw = form.value.map_embed_url.trim()
  const match = raw.match(/src=["']([^"']+)["']/i)
  if (match) form.value.map_embed_url = match[1]
}

function buildPayload() {
  normalizeMapUrl()
  // Solo campos persistibles (country/department son auxiliares del cascadeo).
  const f = form.value
  const base = {
    name: f.name,
    code: f.code,
    address: f.address,
    is_active: f.is_active,
    description: f.description,
    email: f.email,
    phone: f.phone,
    hours: f.hours,
    schedule: f.schedule,
    map_embed_url: f.map_embed_url,
    show_in_store: f.show_in_store,
    city: f.city
  }
  // Foto nueva → multipart (el archivo va como tal).
  if (photoFile.value) {
    const fd = new FormData()
    Object.entries(base).forEach(([k, v]) => {
      if (v === null || v === undefined) return // FK/valores nulos: no se envían
      if (k === 'schedule') { fd.append(k, JSON.stringify(v)); return } // objeto → JSON
      fd.append(k, typeof v === 'boolean' ? (v ? 'true' : 'false') : v)
    })
    fd.append('photo', photoFile.value)
    return fd
  }
  // Quitar la foto → JSON con photo:null (ImageField allow_null la limpia).
  if (removePhoto.value) return { ...base, photo: null }
  // Sin cambios de foto → JSON simple (no se toca la foto existente).
  return base
}

async function save() {
  if (!canSave.value) return
  if (!validate()) {
    toastError('Revisa el teléfono y el correo.')
    return
  }
  saving.value = true
  error.value = ''
  fieldErrors.value = {}
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await warehousesApi.update(warehouseId.value, payload)
      toastSuccess('Bodega actualizada')
    } else {
      await warehousesApi.create(payload)
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

onMounted(async () => {
  countries.value = await geoApi.countries()
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
          <input v-model="form.address" class="field__input" maxlength="200" placeholder="Ej. Cra 00 #00-00, Barrio, Ciudad" />
        </label>

        <div class="field-row field-row--3">
          <label class="field">
            <span class="field__label">País</span>
            <select v-model="form.country" class="field__input">
              <option :value="null">—</option>
              <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">Departamento</span>
            <select v-model="form.department" class="field__input" :disabled="!form.country">
              <option :value="null">—</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">Ciudad</span>
            <select v-model="form.city" class="field__input" :disabled="!form.department">
              <option :value="null">—</option>
              <option v-for="ci in cities" :key="ci.id" :value="ci.id">{{ ci.name }}</option>
            </select>
          </label>
        </div>
        <p class="field__hint">
          La ciudad se usa para elegir <strong>esta tienda como la más cercana</strong> al comprador
          al despachar envíos a domicilio.
        </p>
      </section>

      <section class="card-box">
        <div class="card-box__head">
          <h2 class="card-box__title">Vitrina pública (tienda)</h2>
          <p class="card-box__hint">
            Estos datos se muestran a los compradores en la página de <strong>Tiendas</strong>.
          </p>
        </div>

        <label class="toggle toggle--block">
          <input v-model="form.show_in_store" type="checkbox" />
          <span>Mostrar esta tienda en el ecommerce (y permitir recoger aquí)</span>
        </label>

        <!-- Foto -->
        <div class="field">
          <span class="field__label">Foto de la tienda</span>
          <div class="photo">
            <div class="photo__preview" :class="{ 'photo__preview--empty': !photoPreview }">
              <img v-if="photoPreview" :src="photoPreview" alt="Foto de la tienda" />
              <span v-else>Sin foto</span>
            </div>
            <div class="photo__actions">
              <label class="btn btn--ghost btn--sm">
                <Upload :size="15" /> {{ photoPreview ? 'Cambiar' : 'Subir foto' }}
                <input type="file" accept="image/*" hidden @change="onPhotoChange" />
              </label>
              <button v-if="photoPreview" type="button" class="btn btn--ghost btn--sm" @click="clearPhoto">
                <Trash2 :size="15" /> Quitar
              </button>
            </div>
          </div>
        </div>

        <label class="field">
          <span class="field__label">Descripción</span>
          <textarea
            v-model="form.description"
            class="field__input field__textarea"
            rows="3"
            maxlength="1000"
            placeholder="Cuenta qué encontrará el cliente en esta tienda, referencias para llegar, etc."
          ></textarea>
        </label>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Teléfono</span>
            <input
              :value="form.phone"
              class="field__input"
              type="tel"
              inputmode="numeric"
              maxlength="12"
              placeholder="Ej. 300 123 4567"
              @input="onPhoneInput"
            />
            <span v-if="clientErrors.phone" class="field__error">{{ clientErrors.phone }}</span>
          </label>
          <label class="field">
            <span class="field__label">Correo</span>
            <input
              v-model="form.email"
              type="email"
              class="field__input"
              placeholder="tienda@negocio.com"
              @input="clientErrors.email = ''"
            />
            <span v-if="clientErrors.email" class="field__error">{{ clientErrors.email }}</span>
            <span v-else-if="fieldErrors.email" class="field__error">{{ fieldErrors.email[0] }}</span>
          </label>
        </div>

        <div class="field">
          <span class="field__label">Horario de atención</span>
          <p class="field__hint">
            Define el horario de cada día. En la página de Tiendas los días con el mismo
            horario se agrupan automáticamente (p. ej. «Lunes a viernes 7:00 a.m. – 9:00 p.m.»).
          </p>
          <div class="schedule">
            <div v-for="day in DAYS" :key="day.key" class="schedule__row" :class="{ 'schedule__row--closed': form.schedule[day.key].closed }">
              <span class="schedule__day">{{ day.label }}</span>
              <label class="toggle schedule__toggle">
                <input v-model="form.schedule[day.key].closed" type="checkbox" :true-value="false" :false-value="true" />
                <span class="schedule__state">{{ form.schedule[day.key].closed ? 'Cerrado' : 'Abierto' }}</span>
              </label>
              <div v-if="!form.schedule[day.key].closed" class="schedule__times">
                <input v-model="form.schedule[day.key].open" type="time" class="schedule__time" />
                <span class="schedule__sep">a</span>
                <input v-model="form.schedule[day.key].close" type="time" class="schedule__time" />
              </div>
              <span v-else class="schedule__closed-text">Sin atención</span>
              <div class="schedule__copy">
                <button v-if="['mon','tue','wed','thu','fri'].includes(day.key)" type="button" class="schedule__copy-btn" title="Aplicar este horario de lunes a viernes" @click="applyToWeekdays(day.key)">L–V</button>
                <button type="button" class="schedule__copy-btn" title="Aplicar este horario a toda la semana" @click="applyToAllWeek(day.key)">Toda la semana</button>
              </div>
            </div>
          </div>
        </div>

        <label class="field">
          <span class="field__label">Nota de horario <span class="field__optional">(opcional)</span></span>
          <input v-model="form.hours" class="field__input" maxlength="200" placeholder="Ej. Cerramos en festivos especiales. Domicilios hasta las 8 p.m." />
          <span class="field__hint">Aclaración corta que se muestra debajo del horario.</span>
        </label>

        <label class="field">
          <span class="field__label">Mapa (Google Maps)</span>
          <input
            v-model="form.map_embed_url"
            class="field__input"
            placeholder="Pega aquí el iframe o el enlace de Google Maps"
            @blur="normalizeMapUrl"
          />
          <span class="field__hint">
            En Google Maps: <strong>Compartir → Insertar un mapa</strong> y pega el código (o solo el enlace <code>src</code>).
          </span>
          <span v-if="fieldErrors.map_embed_url" class="field__error">{{ fieldErrors.map_embed_url[0] }}</span>
        </label>

        <div v-if="form.map_embed_url" class="map-preview">
          <iframe
            :src="form.map_embed_url"
            title="Vista previa del mapa"
            loading="lazy"
            referrerpolicy="no-referrer-when-downgrade"
          ></iframe>
        </div>
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
.card-box__head {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.card-box__title {
  font-size: 1rem;
  color: var(--color-ink);
}
.card-box__hint {
  font-size: 0.84rem;
  color: var(--color-muted);
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
.field__textarea {
  resize: vertical;
  min-height: 70px;
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
.field-row--3 {
  grid-template-columns: 1fr 1fr 1fr;
}
@media (max-width: 640px) {
  .field-row,
  .field-row--3 {
    grid-template-columns: 1fr;
  }
}
.field__error {
  font-size: 0.8rem;
  color: #dc2626;
}
.field__hint {
  font-size: 0.8rem;
  color: var(--color-muted);
}
.field__hint code {
  background: var(--color-surface-alt, #f1efe9);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.78rem;
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-ink);
}
.toggle input {
  appearance: none;
  -webkit-appearance: none;
  position: relative;
  flex-shrink: 0;
  width: 38px;
  height: 22px;
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
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s ease;
}
.toggle input:checked::after {
  transform: translateX(16px);
}
.toggle--block {
  align-items: flex-start;
}

/* Foto */
.photo {
  display: flex;
  align-items: center;
  gap: 16px;
}
.photo__preview {
  width: 130px;
  height: 90px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-line);
  flex-shrink: 0;
}
.photo__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.photo__preview--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt, #f5f3ee);
  color: var(--color-muted);
  font-size: 0.82rem;
}
.photo__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__optional {
  font-weight: 400;
  color: var(--color-muted);
}

/* Editor de horario por día */
.schedule {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.schedule__row {
  display: grid;
  grid-template-columns: 120px 116px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-line);
}
.schedule__row:last-child {
  border-bottom: 0;
}
.schedule__row--closed {
  background: var(--color-surface-alt, #faf7f0);
}
.schedule__day {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-ink);
}
.schedule__toggle {
  font-size: 0.85rem;
  font-weight: 500;
}
.schedule__state {
  color: var(--color-body);
}
.schedule__times {
  display: flex;
  align-items: center;
  gap: 8px;
}
.schedule__time {
  padding: 7px 9px;
  font-family: inherit;
  font-size: 0.88rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.schedule__time:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.schedule__sep {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.schedule__closed-text {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-style: italic;
}
.schedule__copy {
  display: flex;
  gap: 6px;
  justify-self: end;
}
.schedule__copy-btn {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 0;
  border-radius: var(--radius-full);
  padding: 5px 11px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.schedule__copy-btn:hover {
  background: #d8e8df;
}
@media (max-width: 640px) {
  .schedule__row {
    grid-template-columns: 1fr 1fr;
    row-gap: 8px;
  }
  .schedule__copy {
    grid-column: 1 / -1;
    justify-self: start;
  }
}

/* Mapa */
.map-preview {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.map-preview iframe {
  width: 100%;
  height: 220px;
  border: 0;
  display: block;
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
