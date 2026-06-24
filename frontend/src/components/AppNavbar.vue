<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Menu, X, LayoutDashboard, ShoppingCart, Heart, Truck } from 'lucide-vue-next'
import BrandLogo from '@/components/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'

const auth = useAuthStore()
const cart = useCartStore()
const wishlist = useWishlistStore()
const route = useRoute()
const scrolled = ref(false)
const mobileOpen = ref(false)

const links = [
  { name: 'Inicio', to: '/' },
  { name: 'Productos', to: '/productos' },
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
    <!-- Barra de anuncio -->
    <div class="announce">
      <div class="container announce__inner">
        <Truck :size="15" />
        <span>Envío a todo el país · Atención cercana de lunes a sábado</span>
      </div>
    </div>

    <!-- Navegación -->
    <div class="nav" :class="{ 'nav--scrolled': scrolled }">
      <div class="container nav__inner">
        <router-link to="/" class="nav__brand" aria-label="Stockly inicio">
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
  background: var(--color-ink);
  color: #e9ecea;
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

/* Navegación */
.nav {
  background: rgba(250, 247, 240, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid transparent;
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    background 0.25s ease;
}

.nav--scrolled {
  background: rgba(255, 255, 255, 0.9);
  border-bottom-color: var(--color-line);
  box-shadow: var(--shadow-sm);
}

.nav__inner {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
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
  color: var(--color-body);
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
  color: var(--color-ink);
}

.nav__link:hover::after,
.nav__link--active::after {
  width: 100%;
}

.nav__link--active {
  color: var(--color-ink);
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
  background: var(--color-line);
}

.nav__cart {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  color: var(--color-ink);
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
  border: 2px solid var(--color-surface-alt);
  border-radius: var(--radius-full);
}

.nav__login {
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-body);
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
  border: 1px solid var(--color-line);
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
  color: var(--color-ink);
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
  color: var(--color-ink);
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
