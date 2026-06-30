<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, X, LayoutDashboard, ShoppingCart, Heart, Truck } from 'lucide-vue-next'
import BrandLogo from '@/components/BrandLogo.vue'
import { announceIcon } from '@/utils/brandIcons'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useConfigStore } from '@/stores/config'

const auth = useAuthStore()
const cart = useCartStore()
const wishlist = useWishlistStore()
const configStore = useConfigStore()
const route = useRoute()
const scrolled = ref(false)
const mobileOpen = ref(false)

const announceText = computed(() => configStore.config?.announce_text ?? '')
const announceIconComp = computed(() => announceIcon(configStore.config?.announce_icon) || Truck)
const announceIconColor = computed(() => configStore.config?.announce_icon_color || '')
const announceAnim = computed(() => configStore.config?.announce_animation || 'static')
const marqueeDuration = computed(
  () => ({ slow: '36s', normal: '24s', fast: '14s' })[configStore.config?.announce_speed] || '24s'
)

const links = [
  { name: 'Inicio', to: '/' },
  { name: 'Productos', to: '/productos' },
  { name: 'Tiendas', to: '/tiendas' },
  { name: 'Quiénes somos', to: '/quienes-somos' }
]

function onScroll() {
  scrolled.value = window.scrollY > 8
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
  }
)
</script>

<template>
  <header class="hdr">
    <!-- Barra de anuncio (se oculta si no hay texto) -->
    <div v-if="announceText" class="announce">
      <!-- Estática -->
      <div v-if="announceAnim !== 'marquee'" class="container announce__inner">
        <component :is="announceIconComp" :size="15" :color="announceIconColor || undefined" />
        <span>{{ announceText }}</span>
      </div>
      <!-- Deslizante (marquee) -->
      <div v-else class="announce__viewport">
        <div class="announce__track" :style="{ animationDuration: marqueeDuration }">
          <div v-for="g in 2" :key="g" class="announce__group" :aria-hidden="g === 2 ? 'true' : undefined">
            <span v-for="n in 4" :key="n" class="announce__item">
              <component :is="announceIconComp" :size="15" :color="announceIconColor || undefined" />
              <span>{{ announceText }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Navegación -->
    <div class="nav" :class="{ 'nav--scrolled': scrolled }">
      <div class="container nav__inner">
        <router-link to="/" class="nav__brand" :aria-label="`${configStore.config?.business_name || 'Inicio'} — inicio`">
          <BrandLogo />
        </router-link>

        <nav class="nav__links" aria-label="Principal">
          <router-link
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="nav__link"
            exact-active-class="nav__link--active"
          >
            {{ link.name }}
          </router-link>
        </nav>

        <div class="nav__actions">
          <router-link
            v-if="!auth.isStaff"
            to="/favoritos"
            class="nav__cart"
            aria-label="Ver favoritos"
          >
            <Heart :size="20" />
            <span v-if="wishlist.count" class="nav__cart-badge">{{ wishlist.count }}</span>
          </router-link>

          <router-link
            v-if="!auth.isStaff"
            to="/carrito"
            class="nav__cart"
            aria-label="Ver carrito"
          >
            <ShoppingCart :size="20" />
            <span v-if="cart.count" class="nav__cart-badge">{{ cart.count }}</span>
          </router-link>

          <span class="nav__divider" aria-hidden="true"></span>

          <template v-if="auth.isStaff">
            <router-link to="/dashboard" class="btn btn--primary btn--sm">
              <LayoutDashboard :size="16" /> Dashboard
            </router-link>
          </template>
          <template v-else-if="auth.isAuthenticated">
            <router-link to="/cuenta" class="nav__user">
              <span class="nav__avatar">
                <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="" />
                <template v-else>{{ auth.initials }}</template>
              </span>
              <span class="nav__user-name">{{ auth.firstName }}</span>
            </router-link>
          </template>
          <template v-else>
            <router-link to="/login" class="nav__login">Iniciar sesión</router-link>
            <router-link to="/register" class="btn btn--primary btn--sm">Crear cuenta</router-link>
          </template>
        </div>

        <button
          class="nav__toggle"
          :aria-expanded="mobileOpen"
          aria-label="Abrir menú"
          @click="mobileOpen = !mobileOpen"
        >
          <X v-if="mobileOpen" :size="24" />
          <Menu v-else :size="24" />
        </button>
      </div>
    </div>

    <transition name="fade">
      <div v-if="mobileOpen" class="nav__mobile">
        <router-link
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="nav__mobile-link"
          exact-active-class="nav__mobile-link--active"
        >
          {{ link.name }}
        </router-link>
        <div class="nav__mobile-actions">
          <router-link v-if="!auth.isStaff" to="/favoritos" class="btn btn--ghost btn--block">
            <Heart :size="17" /> Favoritos<span v-if="wishlist.count"> ({{ wishlist.count }})</span>
          </router-link>
          <router-link v-if="!auth.isStaff" to="/carrito" class="btn btn--ghost btn--block">
            <ShoppingCart :size="17" /> Carrito<span v-if="cart.count"> ({{ cart.count }})</span>
          </router-link>
          <template v-if="auth.isStaff">
            <router-link to="/dashboard" class="btn btn--primary btn--block">
              <LayoutDashboard :size="17" /> Ir al dashboard
            </router-link>
          </template>
          <template v-else-if="auth.isAuthenticated">
            <router-link to="/cuenta" class="btn btn--ghost btn--block">Mi cuenta</router-link>
          </template>
          <template v-else>
            <router-link to="/login" class="btn btn--ghost btn--block">Iniciar sesión</router-link>
            <router-link to="/register" class="btn btn--primary btn--block">Crear cuenta</router-link>
          </template>
        </div>
      </div>
    </transition>
  </header>
</template>

<style scoped>
.hdr {
  position: sticky;
  top: 0;
  z-index: 50;
}

/* Barra de anuncio */
.announce {
  background: var(--color-announce);
  color: var(--color-announce-text);
}
.announce__inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  height: 38px;
  font-size: 0.82rem;
  letter-spacing: 0.01em;
}
.announce svg {
  color: var(--color-accent);
}

/* Barra deslizante (marquee) */
.announce__viewport {
  overflow: hidden;
}
.announce__track {
  display: flex;
  width: max-content;
  animation-name: announce-marquee;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
.announce__group {
  display: flex;
}
.announce__item {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  height: 38px;
  padding: 0 30px;
  white-space: nowrap;
  font-size: 0.82rem;
  letter-spacing: 0.01em;
}
@keyframes announce-marquee {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}
/* Respeta a quien prefiere menos movimiento. */
@media (prefers-reduced-motion: reduce) {
  .announce__track {
    animation: none;
  }
}

/* Navegación — color sólido siempre (sin transparencia). El scroll solo añade
   una sombra/borde sutil para dar profundidad. */
.nav {
  background: var(--color-navbar);
  border-bottom: 1px solid var(--color-navbar-line);
  transition:
    box-shadow 0.25s ease;
}

.nav--scrolled {
  box-shadow: var(--shadow-sm);
}

.nav__inner {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

/* El enlace de marca va como flex para que el logo quede centrado en Y sin el
   hueco de línea base (descender) que dejaría un <a> inline debajo de la imagen. */
.nav__brand {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  color: var(--color-navbar-ink);
}

.nav__links {
  display: flex;
  align-items: center;
  gap: 30px;
  margin: 0 auto;
}

.nav__link {
  position: relative;
  font-size: 0.93rem;
  font-weight: 500;
  color: var(--color-navbar-muted);
  padding: 6px 0;
  transition: color 0.18s ease;
}

.nav__link::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -2px;
  width: 0;
  height: 1.5px;
  background: var(--color-accent);
  transition: width 0.22s ease;
}

.nav__link:hover {
  color: var(--color-navbar-ink);
}

.nav__link:hover::after,
.nav__link--active::after {
  width: 100%;
}

.nav__link--active {
  color: var(--color-navbar-ink);
  font-weight: 600;
}

.nav__actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav__divider {
  width: 1px;
  height: 24px;
  background: var(--color-navbar-line);
}

.nav__cart {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  color: var(--color-navbar-ink);
  transition:
    color 0.18s ease,
    background 0.18s ease;
}

.nav__cart:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.nav__cart-badge {
  position: absolute;
  top: 3px;
  right: 1px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.66rem;
  font-weight: 700;
  color: #fff;
  background: var(--color-accent);
  border: 2px solid var(--color-navbar);
  border-radius: var(--radius-full);
}

.nav__login {
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-navbar-muted);
  transition: color 0.18s ease;
}

.nav__login:hover {
  color: var(--color-primary);
}

.nav__user {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 5px 14px 5px 5px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-navbar-line);
  transition:
    background 0.18s ease,
    border-color 0.18s ease;
}

.nav__user:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.nav__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  overflow: hidden;
}
.nav__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.nav__user-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-navbar-ink);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav__toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  color: var(--color-navbar-ink);
}

.nav__mobile {
  display: none;
}

@media (max-width: 900px) {
  .nav__links,
  .nav__actions {
    display: none;
  }

  .nav__toggle {
    display: inline-flex;
  }

  .nav__mobile {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 14px 24px 26px;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-line);
    box-shadow: var(--shadow-md);
  }

  .nav__mobile-link {
    padding: 13px 12px;
    font-size: 1.02rem;
    font-weight: 500;
    color: var(--color-body);
    border-radius: var(--radius-sm);
  }

  .nav__mobile-link--active {
    color: var(--color-primary);
    background: var(--color-primary-soft);
    font-weight: 600;
  }

  .nav__mobile-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 14px;
  }
}
</style>
