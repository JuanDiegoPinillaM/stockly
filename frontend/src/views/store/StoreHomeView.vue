<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Truck,
  ShieldCheck,
  Headphones,
  ArrowRight,
  ArrowUpRight,
  Store,
  Leaf,
  BadgeCheck,
  Sparkles
} from 'lucide-vue-next'
import { storeApi } from '@/services/store'
import ProductCard from '@/components/store/ProductCard.vue'
import LoadingState from '@/components/LoadingState.vue'

const categories = ref([])
const products = ref([])
const loading = ref(true)

const PERKS = [
  { icon: Truck, title: 'Envío a todo el país', text: 'Recíbelo donde estés.' },
  { icon: ShieldCheck, title: 'Compra protegida', text: 'Tus datos siempre seguros.' },
  { icon: BadgeCheck, title: 'Calidad garantizada', text: 'Selección cuidada.' },
  { icon: Headphones, title: 'Atención cercana', text: 'Te acompañamos siempre.' }
]

const VALUES = [
  { icon: Leaf, title: 'Selección con criterio', text: 'Cada producto entra a nuestro catálogo por su calidad, no por llenar estantería.' },
  { icon: Sparkles, title: 'Experiencia simple', text: 'Comprar debe ser fácil: claridad en precios, stock real y entrega puntual.' },
  { icon: ShieldCheck, title: 'Confianza ante todo', text: 'Pago seguro, datos protegidos y un trato honesto en cada pedido.' }
]

const featured = computed(() => products.value.slice(0, 8))
const heroImage = computed(() => products.value.find((p) => p.main_image)?.main_image || null)
const heroProduct = computed(() => products.value.find((p) => p.main_image) || null)

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

// Imagen representativa por categoría (primera con foto del lote cargado).
function categoryImage(catId) {
  const p = products.value.find((x) => x.category_id === catId && x.main_image)
  return p ? p.main_image : null
}

onMounted(async () => {
  try {
    const [cats, prods] = await Promise.all([storeApi.categories(), storeApi.products()])
    categories.value = cats
    products.value = prods.results || prods
  } catch {
    /* sin datos, igual se muestra la landing */
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="container hero__inner">
        <div class="hero__content">
          <span class="eyebrow">Tienda en línea</span>
          <h1 class="hero__title">
            Calidad seleccionada,<br />
            <span class="hero__accent">directo a tu puerta</span>
          </h1>
          <p class="hero__lead">
            Descubre un catálogo cuidado al detalle. Productos de calidad, precios
            claros y una experiencia de compra simple y confiable.
          </p>
          <div class="hero__actions">
            <RouterLink :to="{ name: 'catalog' }" class="btn btn--primary btn--lg">
              Explorar catálogo <ArrowRight :size="18" />
            </RouterLink>
            <RouterLink :to="{ name: 'about' }" class="btn btn--ghost btn--lg">Conócenos</RouterLink>
          </div>
          <ul class="hero__trust">
            <li><Truck :size="17" /> Envío nacional</li>
            <li><ShieldCheck :size="17" /> Pago seguro</li>
            <li><Headphones :size="17" /> Atención cercana</li>
          </ul>
        </div>

        <div class="hero__media">
          <div class="hero__frame">
            <img v-if="heroImage" :src="heroImage" alt="Producto destacado" />
            <div v-else class="hero__motif"><Store :size="120" /></div>
          </div>
          <div class="hero__badge-float">
            <span class="hero__badge-icon"><BadgeCheck :size="20" /></span>
            <div>
              <strong>Calidad garantizada</strong>
              <small>Selección cuidada</small>
            </div>
          </div>
          <RouterLink
            v-if="heroProduct"
            :to="{ name: 'store-product', params: { slug: heroProduct.slug } }"
            class="hero__chip"
          >
            <span class="hero__chip-cat">{{ heroProduct.category }}</span>
            <span class="hero__chip-name">{{ heroProduct.name }}</span>
            <span class="hero__chip-price">{{ money(heroProduct.price_min) }}</span>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- Beneficios -->
    <section class="container perks">
      <div v-for="perk in PERKS" :key="perk.title" class="perk">
        <span class="perk__icon"><component :is="perk.icon" :size="22" /></span>
        <div>
          <h3 class="perk__title">{{ perk.title }}</h3>
          <p class="perk__text">{{ perk.text }}</p>
        </div>
      </div>
    </section>

    <LoadingState v-if="loading" label="Cargando tienda…" />

    <template v-else>
      <!-- Categorías -->
      <section v-if="categories.length" class="container block">
        <div class="block__head">
          <div>
            <span class="eyebrow">Explora</span>
            <h2 class="block__title">Compra por categoría</h2>
          </div>
          <RouterLink :to="{ name: 'catalog' }" class="block__link">Ver todo <ArrowRight :size="16" /></RouterLink>
        </div>
        <div class="cats">
          <RouterLink
            v-for="c in categories"
            :key="c.id"
            :to="{ name: 'catalog', query: { category: c.id } }"
            class="cat"
          >
            <div class="cat__img" :class="{ 'cat__img--ph': !categoryImage(c.id) }">
              <img v-if="categoryImage(c.id)" :src="categoryImage(c.id)" :alt="c.name" loading="lazy" />
              <span v-else>{{ c.name.charAt(0) }}</span>
              <span class="cat__overlay"></span>
            </div>
            <span class="cat__name">{{ c.name }} <ArrowUpRight :size="15" /></span>
          </RouterLink>
        </div>
      </section>

      <!-- Destacados -->
      <section v-if="featured.length" class="container block">
        <div class="block__head">
          <div>
            <span class="eyebrow">Lo más visto</span>
            <h2 class="block__title">Destacados</h2>
          </div>
          <RouterLink :to="{ name: 'catalog' }" class="block__link">Ver todo <ArrowRight :size="16" /></RouterLink>
        </div>
        <div class="grid">
          <ProductCard v-for="p in featured" :key="p.id" :product="p" />
        </div>
      </section>

      <!-- Promesa / valores -->
      <section class="promise">
        <div class="container">
          <div class="promise__head">
            <span class="eyebrow">Por qué Stockly</span>
            <h2 class="block__title">Una tienda pensada al detalle</h2>
          </div>
          <div class="promise__grid">
            <div v-for="v in VALUES" :key="v.title" class="promise__card">
              <span class="promise__icon"><component :is="v.icon" :size="22" /></span>
              <h3 class="promise__title">{{ v.title }}</h3>
              <p class="promise__text">{{ v.text }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA quiénes somos -->
      <section class="container">
        <div class="cta">
          <div class="cta__bg" aria-hidden="true"></div>
          <div class="cta__content">
            <h2 class="cta__title">Conoce la historia detrás de la tienda</h2>
            <p class="cta__text">
              Somos un negocio comprometido con la calidad y con una experiencia de
              compra cercana y confiable.
            </p>
            <RouterLink :to="{ name: 'about' }" class="btn btn--accent btn--lg">
              Nuestra historia <ArrowRight :size="18" />
            </RouterLink>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* ---------------- Hero ---------------- */
.hero {
  background:
    radial-gradient(900px 500px at 88% -10%, rgba(14, 110, 78, 0.08), transparent 60%),
    radial-gradient(700px 500px at 0% 110%, rgba(184, 146, 58, 0.08), transparent 55%),
    var(--color-surface-alt);
  border-bottom: 1px solid var(--color-line);
  overflow: hidden;
}
.hero__inner {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  align-items: center;
  gap: 56px;
  padding: 84px 0 92px;
}
.hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  line-height: 1.06;
  letter-spacing: -0.02em;
  margin-bottom: 22px;
}
.hero__accent {
  color: var(--color-primary);
}
.hero__lead {
  font-size: 1.1rem;
  color: var(--color-body);
  max-width: 480px;
  margin-bottom: 30px;
}
.hero__actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 34px;
}
.hero__trust {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.hero__trust li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-body);
}
.hero__trust svg {
  color: var(--color-primary);
}

.hero__media {
  position: relative;
}
.hero__frame {
  position: relative;
  aspect-ratio: 4 / 5;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: linear-gradient(150deg, var(--color-primary) 0%, #0a4d38 100%);
  box-shadow: var(--shadow-lg);
  display: grid;
  place-items: center;
}
.hero__frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero__motif {
  color: rgba(255, 255, 255, 0.22);
}
.hero__badge-float {
  position: absolute;
  top: 22px;
  left: -22px;
  display: flex;
  align-items: center;
  gap: 11px;
  background: #fff;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}
.hero__badge-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.hero__badge-float strong {
  display: block;
  font-size: 0.86rem;
  color: var(--color-ink);
}
.hero__badge-float small {
  font-size: 0.76rem;
  color: var(--color-muted);
}
.hero__chip {
  position: absolute;
  bottom: 22px;
  right: -20px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #fff;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  max-width: 220px;
  transition: transform 0.2s ease;
}
.hero__chip:hover {
  transform: translateY(-3px);
}
.hero__chip-cat {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  color: var(--color-accent-dark);
}
.hero__chip-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hero__chip-price {
  font-weight: 700;
  color: var(--color-primary);
}

/* ---------------- Beneficios ---------------- */
.perks {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  margin-top: -36px;
  margin-bottom: 16px;
  position: relative;
  z-index: 2;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.perk {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 22px 24px;
  border-right: 1px solid var(--color-line);
}
.perk:last-child {
  border-right: none;
}
.perk__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex-shrink: 0;
}
.perk__title {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--color-ink);
}
.perk__text {
  font-size: 0.82rem;
  color: var(--color-muted);
}

/* ---------------- Bloques ---------------- */
.block {
  padding: 64px 0 8px;
}
.block__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 30px;
}
.block__head .eyebrow {
  margin-bottom: 10px;
}
.block__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.7rem, 3vw, 2.2rem);
  letter-spacing: -0.015em;
}
.block__link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.92rem;
  white-space: nowrap;
}
.block__link:hover {
  gap: 10px;
}

.cats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 18px;
}
.cat__img {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-surface-alt);
  margin-bottom: 12px;
}
.cat__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}
.cat:hover .cat__img img {
  transform: scale(1.06);
}
.cat__overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(20, 32, 25, 0.28), transparent 55%);
}
.cat__img--ph {
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 2.6rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-soft);
}
.cat__name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--color-ink);
}
.cat__name svg {
  color: var(--color-accent);
  opacity: 0;
  transform: translate(-4px, 4px);
  transition: all 0.2s ease;
}
.cat:hover .cat__name svg {
  opacity: 1;
  transform: translate(0, 0);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 22px;
}

/* ---------------- Promesa ---------------- */
.promise {
  margin-top: 72px;
  padding: 72px 0;
  background: var(--color-surface-alt);
  border-top: 1px solid var(--color-line);
  border-bottom: 1px solid var(--color-line);
}
.promise__head {
  max-width: 560px;
  margin-bottom: 40px;
}
.promise__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
}
.promise__card {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 30px 26px;
  transition:
    box-shadow 0.22s ease,
    transform 0.22s ease;
}
.promise__card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
}
.promise__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  margin-bottom: 18px;
}
.promise__title {
  font-size: 1.12rem;
  margin-bottom: 8px;
}
.promise__text {
  color: var(--color-muted);
  font-size: 0.94rem;
  line-height: 1.7;
}

/* ---------------- CTA ---------------- */
.cta {
  position: relative;
  margin: 72px 0;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: var(--color-surface-dark);
  color: #fff;
}
.cta__bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(600px 300px at 90% 0%, rgba(14, 110, 78, 0.5), transparent 60%),
    radial-gradient(500px 300px at 0% 100%, rgba(184, 146, 58, 0.25), transparent 55%);
}
.cta__content {
  position: relative;
  max-width: 600px;
  padding: 64px 56px;
}
.cta__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.7rem, 3vw, 2.3rem);
  color: #fff;
  margin-bottom: 14px;
}
.cta__text {
  color: #b9c4be;
  font-size: 1.05rem;
  margin-bottom: 28px;
}

/* ---------------- Responsive ---------------- */
@media (max-width: 980px) {
  .hero__inner {
    grid-template-columns: 1fr;
    gap: 40px;
    padding: 56px 0 64px;
  }
  .hero__media {
    max-width: 420px;
  }
  .perks {
    grid-template-columns: repeat(2, 1fr);
  }
  .perk:nth-child(2) {
    border-right: none;
  }
  .perk:nth-child(1),
  .perk:nth-child(2) {
    border-bottom: 1px solid var(--color-line);
  }
  .promise__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .perks {
    grid-template-columns: 1fr;
  }
  .perk {
    border-right: none;
    border-bottom: 1px solid var(--color-line);
  }
  .perk:last-child {
    border-bottom: none;
  }
  .hero__badge-float {
    left: 0;
  }
  .hero__chip {
    right: 0;
  }
  .cta__content {
    padding: 48px 28px;
  }
}
</style>
