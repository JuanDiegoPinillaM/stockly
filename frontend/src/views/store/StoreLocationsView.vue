<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { MapPin, Phone, Mail, Clock, Store, Navigation, ArrowUpRight, Map, X } from 'lucide-vue-next'
import { storeApi } from '@/services/store'
import LoadingState from '@/components/LoadingState.vue'

const locations = ref([])
const loading = ref(true)
const error = ref('')

// Sede cuyo mapa se muestra en el modal (null = cerrado). El iframe solo se
// monta al abrirlo, y abrir el mapa NO reacomoda la cuadrícula de tarjetas.
const activeMap = ref(null)
function openMap(loc) {
  activeMap.value = loc
}
function closeMap() {
  activeMap.value = null
}
function onKeydown(e) {
  if (e.key === 'Escape') closeMap()
}
// Bloquea el scroll del fondo mientras el modal está abierto.
watch(activeMap, (loc) => {
  document.body.style.overflow = loc ? 'hidden' : ''
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKeydown)
})

// "Ciudad, Departamento, País" omitiendo lo que falte.
function localityOf(loc) {
  return [loc.city_name, loc.department_name, loc.country_name].filter(Boolean).join(', ')
}

// Enlace de "Cómo llegar": busca la dirección en Google Maps; si no hay
// dirección, cae al enlace del mapa que se configuró en la bodega.
function directionsLink(loc) {
  const query = [loc.address, localityOf(loc)].filter(Boolean).join(', ')
  if (query) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
  return loc.map_embed_url || ''
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  try {
    locations.value = await storeApi.points()
  } catch {
    error.value = 'No pudimos cargar las tiendas. Intenta de nuevo más tarde.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="locations">
    <!-- Hero -->
    <section class="loc-hero">
      <div class="container">
        <span class="eyebrow">Nuestras tiendas</span>
        <h1 class="loc-hero__title">Visítanos o recoge tu pedido</h1>
        <p class="loc-hero__text">
          Estos son nuestros puntos de atención. Encuentra el más cercano, conoce sus
          horarios y cómo llegar.
        </p>
      </div>
    </section>

    <section class="container loc-body">
      <LoadingState v-if="loading" label="Cargando tiendas…" />
      <p v-else-if="error" class="loc-alert">{{ error }}</p>
      <div v-else-if="!locations.length" class="loc-empty">
        <Store :size="40" />
        <p>Aún no hay tiendas para mostrar.</p>
      </div>

      <div v-else class="loc-grid">
        <article v-for="loc in locations" :key="loc.id" class="store-card">
          <!-- Cabecera: foto (o marca) con el nombre superpuesto -->
          <header class="store-card__head" :class="{ 'store-card__head--brand': !loc.photo }">
            <img v-if="loc.photo" :src="loc.photo" :alt="loc.name" class="store-card__photo" loading="lazy" />
            <Store v-else :size="42" class="store-card__brand-icon" />
            <div class="store-card__overlay">
              <span v-if="localityOf(loc)" class="store-card__locality">
                <Navigation :size="13" /> {{ localityOf(loc) }}
              </span>
              <h2 class="store-card__name">{{ loc.name }}</h2>
            </div>
          </header>

          <div class="store-card__body">
            <p v-if="loc.description" class="store-card__desc">{{ loc.description }}</p>

            <ul class="store-card__info">
              <li v-if="loc.address">
                <span class="store-card__icon"><MapPin :size="16" /></span>
                <span>{{ loc.address }}</span>
              </li>
              <li v-if="loc.phone">
                <span class="store-card__icon"><Phone :size="16" /></span>
                <a :href="`tel:${loc.phone.replace(/\s+/g, '')}`">{{ loc.phone }}</a>
              </li>
              <li v-if="loc.email">
                <span class="store-card__icon"><Mail :size="16" /></span>
                <a :href="`mailto:${loc.email}`">{{ loc.email }}</a>
              </li>
            </ul>

            <!-- Horario agrupado por días con el mismo horario -->
            <div v-if="loc.schedule_display && loc.schedule_display.length" class="hours">
              <div class="hours__head">
                <Clock :size="15" /> <span>Horario</span>
              </div>
              <dl class="hours__list">
                <div v-for="(row, i) in loc.schedule_display" :key="i" class="hours__row">
                  <dt class="hours__days">{{ row.days }}</dt>
                  <dd class="hours__time" :class="{ 'hours__time--closed': row.hours === 'Cerrado' }">
                    {{ row.hours }}
                  </dd>
                </div>
              </dl>
              <p v-if="loc.hours" class="hours__note">{{ loc.hours }}</p>
            </div>
            <div v-else-if="loc.hours" class="hours">
              <div class="hours__head">
                <Clock :size="15" /> <span>Horario</span>
              </div>
              <p class="hours__note hours__note--solo">{{ loc.hours }}</p>
            </div>

            <div v-if="directionsLink(loc) || loc.map_embed_url" class="store-card__actions">
              <a
                v-if="directionsLink(loc)"
                class="btn-pill btn-pill--primary"
                :href="directionsLink(loc)"
                target="_blank"
                rel="noopener"
              >
                <Navigation :size="16" /> Cómo llegar
                <ArrowUpRight :size="15" class="btn-pill__arrow" />
              </a>
              <button
                v-if="loc.map_embed_url"
                type="button"
                class="btn-pill btn-pill--ghost"
                @click="openMap(loc)"
              >
                <Map :size="16" /> Ver mapa
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- Modal del mapa: no afecta la cuadrícula de tarjetas -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="activeMap" class="map-modal" @click.self="closeMap">
          <div class="map-modal__dialog" role="dialog" aria-modal="true" :aria-label="`Mapa de ${activeMap.name}`">
            <header class="map-modal__head">
              <div class="map-modal__titles">
                <h2 class="map-modal__name">{{ activeMap.name }}</h2>
                <p v-if="activeMap.address" class="map-modal__address">
                  <MapPin :size="14" /> {{ activeMap.address }}
                </p>
              </div>
              <button type="button" class="map-modal__close" aria-label="Cerrar" @click="closeMap">
                <X :size="20" />
              </button>
            </header>

            <div class="map-modal__frame">
              <iframe
                :src="activeMap.map_embed_url"
                :title="`Mapa de ${activeMap.name}`"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
              ></iframe>
            </div>

            <footer v-if="directionsLink(activeMap)" class="map-modal__foot">
              <a class="btn-pill btn-pill--primary" :href="directionsLink(activeMap)" target="_blank" rel="noopener">
                <Navigation :size="16" /> Cómo llegar
                <ArrowUpRight :size="15" class="btn-pill__arrow" />
              </a>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.loc-hero {
  background:
    radial-gradient(800px 360px at 88% -30%, rgba(var(--color-primary-rgb), 0.1), transparent 60%),
    radial-gradient(600px 360px at 0% 120%, rgba(var(--color-accent-rgb), 0.1), transparent 55%),
    var(--color-hero);
  color: var(--color-hero-ink);
  border-bottom: 1px solid var(--color-line);
  padding: 72px 0;
  text-align: center;
}
.loc-hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(2.2rem, 4.5vw, 3.1rem);
  line-height: 1.08;
  letter-spacing: -0.02em;
  color: var(--color-hero-ink);
  margin-bottom: 18px;
}
.loc-hero__text {
  max-width: 600px;
  margin: 0 auto;
  font-size: 1.1rem;
  color: var(--color-hero-text);
}
.loc-body {
  padding: 56px 0 72px;
}
.loc-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
}
.loc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--color-muted);
}

.loc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 28px;
  /* Cada tarjeta toma su altura natural: al desplegar el mapa, la tarjeta crece
     sola y NO estira a sus vecinas (evita el espacio en blanco gigante). */
  align-items: start;
}

/* ---------- Tarjeta ---------- */
.store-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg, 18px);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.store-card:hover {
  box-shadow: var(--shadow-lg, 0 18px 40px -18px rgba(20, 32, 26, 0.28));
  transform: translateY(-3px);
}

/* Cabecera con nombre superpuesto */
.store-card__head {
  position: relative;
  height: 198px;
  overflow: hidden;
}
.store-card__photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}
.store-card:hover .store-card__photo {
  transform: scale(1.05);
}
.store-card__head--brand {
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(120% 120% at 80% 0%, rgba(255, 255, 255, 0.12), transparent 60%),
    linear-gradient(155deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
}
.store-card__brand-icon {
  color: rgba(255, 255, 255, 0.5);
}
.store-card__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 6px;
  padding: 18px 20px;
  background: linear-gradient(to top, rgba(12, 24, 18, 0.82) 0%, rgba(12, 24, 18, 0.25) 45%, transparent 75%);
}
.store-card__locality {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  align-self: flex-start;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(4px);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #fff;
}
.store-card__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.45rem;
  line-height: 1.15;
  color: #fff;
}

/* Cuerpo */
.store-card__body {
  padding: 20px 22px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}
.store-card__desc {
  font-size: 0.92rem;
  color: var(--color-body);
  line-height: 1.6;
}
.store-card__info {
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.store-card__info li {
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 0.92rem;
  color: var(--color-body);
}
.store-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.store-card__info a:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

/* Horario */
.hours {
  background: var(--color-surface-alt, #faf7f0);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-top: auto;
}
.hours__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink);
  margin-bottom: 10px;
}
.hours__head svg {
  color: var(--color-primary);
}
.hours__list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.hours__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  font-size: 0.88rem;
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
  padding-top: 10px;
  border-top: 1px dashed var(--color-line);
  font-size: 0.82rem;
  font-style: italic;
  color: var(--color-muted);
}
.hours__note--solo {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
  font-style: normal;
  color: var(--color-body);
}

/* Acciones (Cómo llegar / Ver mapa) */
.store-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.btn-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: var(--radius-full);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}
.btn-pill--primary {
  background: var(--color-primary);
  color: #fff;
  border: 1px solid var(--color-primary);
}
.btn-pill--primary:hover {
  background: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
}
.btn-pill__arrow {
  opacity: 0.85;
}
.btn-pill--ghost {
  background: #fff;
  color: var(--color-ink);
  border: 1px solid var(--color-line);
}
.btn-pill--ghost:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.btn-pill--active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-soft);
  color: var(--color-primary);
}
/* ---------- Modal del mapa ---------- */
.map-modal {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(12, 24, 18, 0.55);
  backdrop-filter: blur(3px);
}
.map-modal__dialog {
  width: 100%;
  max-width: 760px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 40px 80px -20px rgba(12, 24, 18, 0.5);
}
.map-modal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-line);
}
.map-modal__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.3rem;
  color: var(--color-ink);
}
.map-modal__address {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 0.88rem;
  color: var(--color-body);
}
.map-modal__address svg {
  color: var(--color-primary);
  flex-shrink: 0;
}
.map-modal__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--color-surface-alt, #faf7f0);
  color: var(--color-body);
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
}
.map-modal__close:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.map-modal__frame {
  flex: 1;
  min-height: 0;
}
.map-modal__frame iframe {
  width: 100%;
  height: 60vh;
  max-height: 460px;
  border: 0;
  display: block;
}
.map-modal__foot {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--color-line);
}

/* Transición del modal */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}
.modal-enter-active .map-modal__dialog,
.modal-leave-active .map-modal__dialog {
  transition: transform 0.24s ease, opacity 0.24s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .map-modal__dialog,
.modal-leave-to .map-modal__dialog {
  transform: translateY(14px) scale(0.98);
  opacity: 0;
}
</style>
