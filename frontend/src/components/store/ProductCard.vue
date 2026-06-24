<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ImageOff, Heart, ArrowRight } from 'lucide-vue-next'
import { useWishlistStore } from '@/stores/wishlist'

const props = defineProps({
  product: { type: Object, required: true }
})

const wishlist = useWishlistStore()

// Acepta tanto tarjetas del catálogo (product_id) como productos crudos (id).
const productId = computed(() => props.product.product_id ?? props.product.id)
const colorId = computed(() => props.product.color_id ?? null)
const faved = computed(() => wishlist.has(productId.value, colorId.value))
function toggleFav() {
  wishlist.toggle({ ...props.product, product_id: productId.value, color_id: colorId.value })
}

function money(v) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(v || 0)
}

const priceLabel = computed(() => {
  const p = props.product
  if (p.price_min == null) return '—'
  if (p.price_min === p.price_max) return money(p.price_min)
  return `Desde ${money(p.price_min)}`
})
const isRange = computed(
  () => props.product.price_min != null && props.product.price_min !== props.product.price_max
)
</script>

<template>
  <RouterLink
    :to="{ name: 'store-product', params: { slug: product.slug }, query: product.color_id ? { color: product.color_id } : {} }"
    class="card"
    :class="{ 'card--out': !product.available }"
  >
    <div class="card__media">
      <img
        v-if="product.main_image"
        class="card__img card__img--main"
        :src="product.main_image"
        :alt="product.name"
        loading="lazy"
      />
      <img
        v-if="product.main_image && product.hover_image"
        class="card__img card__img--hover"
        :src="product.hover_image"
        :alt="product.name"
        loading="lazy"
      />
      <ImageOff v-if="!product.main_image" :size="32" />

      <!-- Badges -->
      <div class="card__badges">
        <span v-if="product.is_new && product.available" class="badge badge--new">Nuevo</span>
        <span v-if="!product.available" class="badge badge--out">Agotado</span>
      </div>

      <!-- Favorito -->
      <button
        type="button"
        class="card__fav"
        :class="{ 'card__fav--on': faved }"
        :aria-label="faved ? 'Quitar de favoritos' : 'Agregar a favoritos'"
        :aria-pressed="faved"
        @click.prevent.stop="toggleFav"
      >
        <Heart :size="18" :fill="faved ? 'currentColor' : 'none'" />
      </button>

      <!-- CTA -->
      <span class="card__cta">
        {{ product.available ? 'Ver producto' : 'Sin stock' }}
        <ArrowRight v-if="product.available" :size="15" />
      </span>
    </div>

    <div class="card__body">
      <span class="card__cat">{{ product.category }}</span>
      <h3 class="card__name">{{ product.name }}</h3>
      <p v-if="product.color_label" class="card__variant">
        <span class="card__swatch" :style="{ background: product.swatch_hex || '#cbd5cf' }"></span>
        {{ product.color_label }}
      </p>
      <p class="card__price">
        <span v-if="isRange" class="card__from">Desde</span>
        {{ isRange ? money(product.price_min) : priceLabel }}
      </p>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition:
    box-shadow 0.28s ease,
    transform 0.28s ease,
    border-color 0.28s ease;
}
.card:hover {
  box-shadow: 0 18px 40px -16px rgba(15, 23, 42, 0.28);
  transform: translateY(-6px);
  border-color: transparent;
}
.card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.card__media {
  position: relative;
  aspect-ratio: 4 / 5;
  display: grid;
  place-items: center;
  background: var(--color-surface-alt);
  color: #c7cfc8;
  overflow: hidden;
}
.card__img {
  grid-area: 1 / 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card__img--main {
  transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.4s ease;
}
.card__img--hover {
  opacity: 0;
  transform: scale(1.04);
  transition: opacity 0.45s ease;
}
.card:hover .card__img--hover {
  opacity: 1;
}
/* Si no hay segunda foto, hacemos zoom suave a la principal. */
.card:hover .card__img--main {
  transform: scale(1.05);
}
.card--out .card__media {
  filter: grayscale(0.4);
}
.card--out .card__img {
  opacity: 0.78;
}

.card__badges {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 2;
}
.badge {
  font-size: 0.64rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  backdrop-filter: blur(2px);
}
.badge--new {
  background: var(--color-primary);
  color: #fff;
}
.badge--out {
  background: rgba(20, 32, 25, 0.82);
  color: #fff;
}

.card__fav {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-muted);
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
  transition:
    color 0.18s ease,
    transform 0.18s ease,
    background 0.18s ease;
}
.card__fav:hover {
  transform: scale(1.1);
  color: #e11d48;
}
.card__fav--on {
  color: #e11d48;
}

.card__cta {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-ink);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(4px);
  padding: 11px;
  border-radius: var(--radius-sm);
  opacity: 0;
  transform: translateY(10px);
  transition:
    opacity 0.28s ease,
    transform 0.28s ease;
}
.card:hover .card__cta {
  opacity: 1;
  transform: translateY(0);
}

.card__body {
  flex: 1;
  padding: 15px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.card__cat {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  color: var(--color-accent-dark);
}
.card__name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-ink);
  line-height: 1.35;
  letter-spacing: -0.01em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  /* Reserva 2 líneas para que las tarjetas queden parejas con títulos cortos. */
  min-height: 2.7em;
}
.card__variant {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--color-muted);
}
.card__swatch {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}
.card__price {
  /* Ancla el precio al fondo: las tarjetas más altas no dejan hueco abajo. */
  margin-top: auto;
  padding-top: 6px;
  font-weight: 700;
  font-size: 1.08rem;
  color: var(--color-ink);
}
.card__from {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-muted);
  margin-right: 2px;
}

@media (hover: none) {
  .card__cta {
    display: none;
  }
}
</style>
