<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import {
  ArrowLeft, Pencil, Power, PowerOff, Building2, MapPin, Phone, Mail, Hash,
  Globe, Clock, Boxes, Layers, Package, Store, Navigation, ExternalLink
} from 'lucide-vue-next'
import { warehousesApi } from '@/services/inventory'
import { confirmAction, toastSuccess, toastError } from '@/utils/notify'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const route = useRoute()

const warehouse = ref(null)
const loading = ref(true)
const error = ref('')

const locality = computed(() => {
  const w = warehouse.value
  if (!w) return ''
  return [w.city_name, w.department_name, w.country_name].filter(Boolean).join(', ')
})

const directionsLink = computed(() => {
  const w = warehouse.value
  if (!w) return ''
  const query = [w.address, locality.value].filter(Boolean).join(', ')
  if (query) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
  return w.map_embed_url || ''
})

function num(v) {
  return new Intl.NumberFormat('es-CO').format(v || 0)
}
function dt(value) {
  return value ? new Date(value).toLocaleDateString('es-CO', { dateStyle: 'medium' }) : '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    warehouse.value = await warehousesApi.get(route.params.id)
  } catch (e) {
    error.value = e.response?.status === 404 ? 'Esta bodega no existe.' : 'No se pudo cargar la bodega.'
  } finally {
    loading.value = false
  }
}

async function toggle() {
  const w = warehouse.value
  const activate = !w.is_active
  const confirmed = await confirmAction({
    title: activate ? 'Activar bodega' : 'Desactivar bodega',
    text: activate
      ? `"${w.name}" volverá a estar disponible.`
      : `"${w.name}" dejará de aparecer en los movimientos, pero no se elimina.`,
    confirmText: activate ? 'Activar' : 'Desactivar',
    icon: activate ? 'question' : 'warning'
  })
  if (!confirmed) return
  try {
    await warehousesApi.update(w.id, { is_active: activate })
    await load()
    toastSuccess(activate ? 'Bodega activada' : 'Bodega desactivada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar.')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'warehouses' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a bodegas
    </RouterLink>

    <LoadingState v-if="loading" label="Cargando bodega…" />
    <ErrorState v-else-if="error" :message="error" :retryable="false" />

    <template v-else-if="warehouse">
      <!-- Cabecera -->
      <header class="head">
        <div class="head__left">
          <span class="thumb" :class="{ 'thumb--empty': !warehouse.photo }">
            <img v-if="warehouse.photo" :src="warehouse.photo" :alt="warehouse.name" />
            <Building2 v-else :size="30" />
          </span>
          <div>
            <h1 class="head__title">
              {{ warehouse.name }}
              <span class="badge" :class="warehouse.is_active ? 'badge--on' : 'badge--off'">
                {{ warehouse.is_active ? 'Activa' : 'Inactiva' }}
              </span>
              <span v-if="warehouse.show_in_store" class="badge badge--store">
                <Store :size="12" /> En tienda
              </span>
            </h1>
            <p class="head__sub">
              <span v-if="warehouse.code"><Hash :size="13" /> {{ warehouse.code }}</span>
              <span v-if="locality"><MapPin :size="13" /> {{ locality }}</span>
              <span>Creada el {{ dt(warehouse.created_at) }}</span>
            </p>
          </div>
        </div>
        <div class="head__actions">
          <button
            class="btn btn--ghost btn--sm"
            :class="{ 'btn--danger-ghost': warehouse.is_active }"
            @click="toggle"
          >
            <component :is="warehouse.is_active ? PowerOff : Power" :size="15" />
            {{ warehouse.is_active ? 'Desactivar' : 'Activar' }}
          </button>
          <RouterLink :to="{ name: 'warehouse-edit', params: { id: warehouse.id } }" class="btn btn--primary btn--sm">
            <Pencil :size="15" /> Editar
          </RouterLink>
        </div>
      </header>

      <!-- KPIs de inventario -->
      <div class="kpis">
        <div class="kpi">
          <span class="kpi__icon kpi__icon--units"><Boxes :size="20" /></span>
          <div>
            <span class="kpi__value">{{ num(warehouse.stats?.total_units) }}</span>
            <span class="kpi__label">Unidades en existencia</span>
          </div>
        </div>
        <div class="kpi">
          <span class="kpi__icon kpi__icon--refs"><Layers :size="20" /></span>
          <div>
            <span class="kpi__value">{{ num(warehouse.stats?.variant_count) }}</span>
            <span class="kpi__label">Referencias con stock</span>
          </div>
        </div>
        <div class="kpi">
          <span class="kpi__icon kpi__icon--prods"><Package :size="20" /></span>
          <div>
            <span class="kpi__value">{{ num(warehouse.stats?.product_count) }}</span>
            <span class="kpi__label">Productos distintos</span>
          </div>
        </div>
      </div>

      <div class="grid">
        <!-- Información -->
        <section class="card">
          <h2 class="card__title">Información</h2>
          <ul class="info">
            <li><Hash :size="16" /> <span>{{ warehouse.code || 'Sin código' }}</span></li>
            <li><MapPin :size="16" /> <span>{{ warehouse.address || 'Sin dirección' }}</span></li>
            <li><Globe :size="16" /> <span>{{ locality || 'Sin ubicación asignada' }}</span></li>
            <li><Phone :size="16" /> <span>{{ warehouse.phone || 'Sin teléfono' }}</span></li>
            <li><Mail :size="16" /> <span>{{ warehouse.email || 'Sin correo' }}</span></li>
          </ul>

          <template v-if="warehouse.description">
            <h3 class="card__subtitle">Descripción</h3>
            <p class="desc">{{ warehouse.description }}</p>
          </template>
        </section>

        <!-- Vitrina pública -->
        <section class="card">
          <div class="card__head">
            <h2 class="card__title">Vitrina pública</h2>
            <span class="badge" :class="warehouse.show_in_store ? 'badge--store' : 'badge--muted'">
              {{ warehouse.show_in_store ? 'Visible en el ecommerce' : 'Oculta' }}
            </span>
          </div>

          <!-- Horario -->
          <h3 class="card__subtitle"><Clock :size="15" /> Horario</h3>
          <dl v-if="warehouse.schedule_display && warehouse.schedule_display.length" class="hours">
            <div v-for="(row, i) in warehouse.schedule_display" :key="i" class="hours__row">
              <dt class="hours__days">{{ row.days }}</dt>
              <dd class="hours__time" :class="{ 'hours__time--closed': row.hours === 'Cerrado' }">
                {{ row.hours }}
              </dd>
            </div>
          </dl>
          <p v-else class="muted">Sin horario definido.</p>
          <p v-if="warehouse.hours" class="hours__note">{{ warehouse.hours }}</p>

          <!-- Mapa -->
          <template v-if="warehouse.map_embed_url">
            <h3 class="card__subtitle"><MapPin :size="15" /> Ubicación en el mapa</h3>
            <div class="map">
              <iframe
                :src="warehouse.map_embed_url"
                :title="`Mapa de ${warehouse.name}`"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
              ></iframe>
            </div>
          </template>
          <a v-if="directionsLink" class="map-link" :href="directionsLink" target="_blank" rel="noopener">
            <Navigation :size="15" /> Cómo llegar <ExternalLink :size="13" />
          </a>
        </section>
      </div>
    </template>
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

/* Cabecera */
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.head__left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb--empty {
  color: var(--color-muted);
}
.head__title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 1.5rem;
}
.head__sub {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--color-muted);
  font-size: 0.88rem;
  margin-top: 6px;
}
.head__sub span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.head__actions {
  display: flex;
  gap: 10px;
}
.btn--danger-ghost:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}

/* KPIs */
.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.kpi {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 18px 20px;
}
.kpi__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}
.kpi__icon--units {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.kpi__icon--refs {
  background: #eff6ff;
  color: #1d4ed8;
}
.kpi__icon--prods {
  background: var(--color-accent-soft, #f7eed8);
  color: var(--color-accent-dark);
}
.kpi__value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--color-ink);
}
.kpi__label {
  font-size: 0.82rem;
  color: var(--color-muted);
}

/* Grid */
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.card__title {
  font-size: 1.05rem;
}
.card__head .card__title {
  margin-bottom: 0;
}
.card > .card__title {
  margin-bottom: 16px;
}
.card__subtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  margin: 20px 0 12px;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.info li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.93rem;
  color: var(--color-body);
}
.info svg {
  color: var(--color-muted);
  flex-shrink: 0;
}
.desc {
  color: var(--color-body);
  line-height: 1.6;
  font-size: 0.92rem;
}

/* Horario */
.hours {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.hours__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  font-size: 0.9rem;
}
.hours__days {
  color: var(--color-body);
}
.hours__time {
  font-weight: 600;
  color: var(--color-ink);
  text-align: right;
  white-space: nowrap;
}
.hours__time--closed {
  font-weight: 500;
  color: var(--color-muted);
}
.hours__note {
  margin-top: 10px;
  font-size: 0.84rem;
  font-style: italic;
  color: var(--color-muted);
}

/* Mapa */
.map {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.map iframe {
  width: 100%;
  height: 240px;
  border: 0;
  display: block;
}
.map-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
}
.map-link:hover {
  text-decoration: underline;
}

.muted {
  color: var(--color-muted);
  font-size: 0.9rem;
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.badge--on {
  background: #ecfdf5;
  color: #047857;
}
.badge--off {
  background: #fef2f2;
  color: #b91c1c;
}
.badge--store {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.badge--muted {
  background: var(--color-surface-alt);
  color: var(--color-muted);
}

@media (max-width: 860px) {
  .kpis {
    grid-template-columns: 1fr;
  }
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
