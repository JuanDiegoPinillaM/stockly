<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  LayoutDashboard,
  FolderTree,
  Package,
  Boxes,
  Palette,
  Warehouse,
  Users,
  Contact,
  ShoppingCart,
  Receipt,
  ArrowLeftRight,
  Send,
  BarChart3,
  Settings,
  ChevronRight,
  Menu,
  LogOut,
  ShieldCheck,
  Home,
  Globe
} from 'lucide-vue-next'
import BrandLogo from '@/components/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(false)

// Navegación lateral agrupada por área. Los módulos pendientes se marcan como
// "próximamente". `adminOnly` oculta el ítem a usuarios sin rol admin.
const navGroups = [
  {
    label: '',
    items: [{ label: 'Inicio', to: '/dashboard', icon: LayoutDashboard, ready: true }]
  },
  {
    label: 'Catálogo',
    items: [
      { label: 'Productos', to: '/dashboard/productos', icon: Package, ready: true },
      { label: 'Categorías', to: '/dashboard/categorias', icon: FolderTree, ready: true },
      { label: 'Atributos', to: '/dashboard/atributos', icon: Palette, ready: true, adminOnly: true }
    ]
  },
  {
    label: 'Inventario',
    items: [
      { label: 'Existencias', to: '/dashboard/inventario', icon: Boxes, ready: true },
      { label: 'Movimientos', to: '/dashboard/movimientos', icon: ArrowLeftRight, ready: true, adminOnly: true },
      { label: 'Transferencias', to: '/dashboard/transferencias', icon: Send, ready: true, managerOnly: true },
      { label: 'Bodegas', to: '/dashboard/bodegas', icon: Warehouse, ready: true, adminOnly: true }
    ]
  },
  {
    label: 'Ventas',
    items: [
      { label: 'Punto de venta', to: '/dashboard/pos', icon: ShoppingCart, ready: true },
      { label: 'Ventas', to: '/dashboard/ventas', icon: Receipt, ready: true },
      { label: 'Pedidos', to: '/dashboard/pedidos', icon: Package, ready: true },
      { label: 'Clientes', to: '/dashboard/clientes', icon: Contact, ready: true }
    ]
  },
  {
    label: 'Administración',
    items: [
      { label: 'Usuarios', to: '/dashboard/usuarios', icon: Users, ready: true, adminOnly: true },
      { label: 'Reportes', to: '/dashboard', icon: BarChart3, ready: false }
    ]
  },
  {
    label: 'Cuenta',
    items: [{ label: 'Configuración', to: '/dashboard/perfil', icon: Settings, ready: true }]
  }
]

// Grupos con sus ítems visibles según el rol; descarta grupos vacíos.
const visibleNavGroups = computed(() =>
  navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) =>
          (!item.adminOnly || auth.isAdmin) && (!item.managerOnly || auth.isManager)
      )
    }))
    .filter((group) => group.items.length)
)

// Breadcrumb a partir de los metadatos de la ruta.
const crumbs = computed(() => {
  const items = [{ label: 'Dashboard', to: '/dashboard', icon: Home }]
  // Crumb intermedio para rutas anidadas (p. ej. Productos > Nuevo producto).
  const parent = route.meta.breadcrumbParent
  if (parent) items.push({ label: parent.label, to: parent.to })
  const current = route.meta.breadcrumb
  if (current && current !== 'Dashboard') {
    items.push({ label: current, to: route.path })
  }
  return items
})

// Marca el módulo activo en el sidebar, incluyendo sus subrutas
// (p. ej. /dashboard/productos/nuevo resalta "Productos").
function isNavActive(item) {
  if (!item.ready) return false
  if (item.to === '/dashboard') return route.path === '/dashboard'
  return route.path === item.to || route.path.startsWith(item.to + '/')
}

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="dash" :class="{ 'dash--open': sidebarOpen }">
    <!-- Sidebar -->
    <aside class="dash__sidebar">
      <div class="dash__brand">
        <RouterLink to="/dashboard"><BrandLogo /></RouterLink>
      </div>

      <nav class="dash__nav" aria-label="Navegación principal">
        <div v-for="group in visibleNavGroups" :key="group.label || 'main'" class="dash__nav-group">
          <p v-if="group.label" class="dash__nav-label">{{ group.label }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.label"
            :to="item.to"
            class="dash__nav-item"
            :class="{
              'dash__nav-item--soon': !item.ready,
              'dash__nav-item--active': isNavActive(item)
            }"
            @click="sidebarOpen = false"
          >
            <component :is="item.icon" :size="19" />
            <span>{{ item.label }}</span>
            <span v-if="!item.ready" class="dash__soon">Pronto</span>
          </RouterLink>
        </div>
      </nav>

      <div class="dash__sidebar-foot">
        <RouterLink to="/" class="dash__site-link">
          <Globe :size="18" />
          <span>Volver al sitio</span>
        </RouterLink>
        <RouterLink to="/dashboard/perfil" class="dash__user" @click="sidebarOpen = false">
          <span class="dash__avatar">
            <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="" />
            <template v-else>{{ auth.initials }}</template>
          </span>
          <div class="dash__user-info">
            <p class="dash__user-name">{{ auth.firstName }}</p>
            <p class="dash__user-mail">{{ auth.user?.email }}</p>
          </div>
        </RouterLink>
      </div>
    </aside>

    <!-- Overlay móvil -->
    <div class="dash__overlay" @click="sidebarOpen = false"></div>

    <!-- Área principal -->
    <div class="dash__main">
      <!-- Topbar con breadcrumb -->
      <header class="dash__topbar">
        <div class="dash__topbar-left">
          <button class="dash__menu-btn" aria-label="Abrir menú" @click="sidebarOpen = true">
            <Menu :size="22" />
          </button>
          <nav class="breadcrumb" aria-label="Ruta de navegación">
            <template v-for="(crumb, i) in crumbs" :key="crumb.to">
              <ChevronRight v-if="i > 0" :size="15" class="breadcrumb__sep" />
              <RouterLink
                :to="crumb.to"
                class="breadcrumb__item"
                :class="{ 'breadcrumb__item--current': i === crumbs.length - 1 }"
              >
                <component :is="crumb.icon" v-if="crumb.icon" :size="15" />
                {{ crumb.label }}
              </RouterLink>
            </template>
          </nav>
        </div>

        <div class="dash__topbar-right">
          <span class="dash__role" :class="auth.isAdmin ? 'dash__role--admin' : 'dash__role--user'">
            <ShieldCheck :size="14" />
            {{ auth.isAdmin ? 'Administrador' : 'Usuario' }}
          </span>
          <RouterLink to="/dashboard/perfil" class="dash__avatar dash__avatar--sm" title="Mi perfil">
            <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="" />
            <template v-else>{{ auth.initials }}</template>
          </RouterLink>
          <button class="dash__logout" @click="logout">
            <LogOut :size="18" />
            <span>Salir</span>
          </button>
        </div>
      </header>

      <!-- Contenido (vacío por ahora) -->
      <main class="dash__content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.dash {
  --sidebar-width: 264px;
  min-height: 100vh;
  background: var(--color-surface-alt);
}

/* Sidebar */
.dash__sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid var(--color-line);
  z-index: 40;
}

.dash__brand {
  padding: 22px 24px;
  border-bottom: 1px solid var(--color-line);
}

.dash__nav {
  flex: 1;
  padding: 20px 16px;
  overflow-y: auto;
}

.dash__nav-group {
  margin-bottom: 18px;
}
.dash__nav-group:last-child {
  margin-bottom: 0;
}

.dash__nav-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-muted);
  padding: 0 12px;
  margin-bottom: 8px;
}

.dash__nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  margin-bottom: 4px;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-body);
  transition:
    background 0.16s ease,
    color 0.16s ease;
}

.dash__nav-item:hover {
  background: var(--color-surface-alt);
  color: var(--color-ink);
}

.dash__nav-item--active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}

.dash__nav-item--soon {
  color: var(--color-muted);
  cursor: default;
}

.dash__soon {
  margin-left: auto;
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  background: var(--color-surface-alt);
  padding: 2px 7px;
  border-radius: var(--radius-full);
}

.dash__sidebar-foot {
  padding: 16px;
  border-top: 1px solid var(--color-line);
}

.dash__site-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-body);
  border: 1px solid var(--color-line);
  transition:
    background 0.16s ease,
    color 0.16s ease,
    border-color 0.16s ease;
}

.dash__site-link:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: #c7d2fe;
}

.dash__user {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
  padding: 6px;
  margin: -6px;
  border-radius: var(--radius-sm);
  transition: background 0.16s ease;
}
.dash__user:hover {
  background: var(--color-surface-alt);
}

.dash__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
  text-decoration: none;
}
.dash__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.dash__avatar--sm {
  width: 34px;
  height: 34px;
  font-size: 0.9rem;
}

.dash__user-info {
  min-width: 0;
}

.dash__user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dash__user-mail {
  font-size: 0.8rem;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Main */
.dash__main {
  margin-left: var(--sidebar-width);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.dash__topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 68px;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--color-line);
}

.dash__topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.dash__menu-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  color: var(--color-ink);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
}

.breadcrumb__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.92rem;
  color: var(--color-muted);
  transition: color 0.16s ease;
}

.breadcrumb__item:hover {
  color: var(--color-primary);
}

.breadcrumb__item--current {
  color: var(--color-ink);
  font-weight: 600;
  pointer-events: none;
}

.breadcrumb__sep {
  color: #cbd5e1;
}

.dash__topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.dash__role {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: var(--radius-full);
}

.dash__role--admin {
  background: #fef3c7;
  color: #b45309;
}

.dash__role--user {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.dash__logout {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-body);
  border: 1px solid var(--color-line);
  transition:
    border-color 0.16s ease,
    color 0.16s ease,
    background 0.16s ease;
}

.dash__logout:hover {
  border-color: #fca5a5;
  color: #dc2626;
  background: #fef2f2;
}

.dash__content {
  flex: 1;
  padding: 32px 28px;
}

/* Overlay (móvil) */
.dash__overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: 35;
}

/* Responsive */
@media (max-width: 980px) {
  .dash__sidebar {
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }
  .dash--open .dash__sidebar {
    transform: translateX(0);
  }
  .dash--open .dash__overlay {
    display: block;
  }
  .dash__main {
    margin-left: 0;
  }
  .dash__menu-btn {
    display: inline-flex;
  }
}

@media (max-width: 600px) {
  .dash__role span,
  .dash__logout span {
    display: none;
  }
  .dash__content {
    padding: 22px 18px;
  }
  .dash__topbar {
    padding: 0 18px;
  }
}
</style>
