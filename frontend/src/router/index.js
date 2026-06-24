import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'

const routes = [
  // ---- Sitio público ----
  {
    path: '/',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/store/StoreHomeView.vue'),
        meta: { title: 'Stockly — Tienda' }
      },
      {
        path: 'productos',
        name: 'catalog',
        component: () => import('@/views/store/StoreCatalogView.vue'),
        meta: { title: 'Stockly — Productos' }
      },
      {
        path: 'quienes-somos',
        name: 'about',
        component: () => import('@/views/store/StoreAboutView.vue'),
        meta: { title: 'Stockly — Quiénes somos' }
      },
      {
        path: 'producto/:slug',
        name: 'store-product',
        component: () => import('@/views/store/StoreProductView.vue'),
        meta: { title: 'Stockly — Producto' }
      },
      {
        path: 'carrito',
        name: 'cart',
        component: () => import('@/views/store/CartView.vue'),
        meta: { title: 'Stockly — Carrito' }
      },
      {
        path: 'favoritos',
        name: 'wishlist',
        component: () => import('@/views/store/WishlistView.vue'),
        meta: { title: 'Stockly — Mis favoritos' }
      },
      {
        path: 'checkout',
        name: 'checkout',
        component: () => import('@/views/store/CheckoutView.vue'),
        meta: { title: 'Stockly — Finalizar compra', requiresAuth: true }
      },
      // ---- Área de cuenta del comprador ----
      {
        path: 'cuenta',
        name: 'account',
        component: () => import('@/views/store/AccountProfileView.vue'),
        meta: { title: 'Stockly — Mi cuenta', requiresAuth: true }
      },
      {
        path: 'cuenta/direcciones',
        name: 'account-addresses',
        component: () => import('@/views/store/AccountAddressesView.vue'),
        meta: { title: 'Stockly — Mis direcciones', requiresAuth: true }
      },
      {
        path: 'cuenta/metodos-pago',
        name: 'account-payments',
        component: () => import('@/views/store/AccountPaymentsView.vue'),
        meta: { title: 'Stockly — Métodos de pago', requiresAuth: true }
      },
      {
        path: 'cuenta/compras',
        name: 'account-orders',
        component: () => import('@/views/store/AccountOrdersView.vue'),
        meta: { title: 'Stockly — Mis compras', requiresAuth: true }
      },
      {
        path: 'cuenta/compras/pedido/:id',
        name: 'account-order-detail',
        component: () => import('@/views/store/AccountOrderDetailView.vue'),
        meta: { title: 'Stockly — Detalle de compra', requiresAuth: true }
      },
      {
        path: 'cuenta/compras/venta/:id',
        name: 'account-sale-detail',
        component: () => import('@/views/store/AccountSaleDetailView.vue'),
        meta: { title: 'Stockly — Detalle de compra', requiresAuth: true }
      },

      // ---- Autenticación (integrada en la tienda: navbar + footer) ----
      {
        path: 'login',
        name: 'login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { title: 'Stockly — Iniciar sesión', guestOnly: true }
      },
      {
        path: 'register',
        name: 'register',
        component: () => import('@/views/auth/RegisterView.vue'),
        meta: { title: 'Stockly — Crear cuenta', guestOnly: true }
      },
      {
        path: 'forgot-password',
        name: 'forgot-password',
        component: () => import('@/views/auth/ForgotPasswordView.vue'),
        meta: { title: 'Stockly — Recuperar contraseña', guestOnly: true }
      },
      {
        path: 'reset-password',
        name: 'reset-password',
        component: () => import('@/views/auth/ResetPasswordView.vue'),
        meta: { title: 'Stockly — Restablecer contraseña' }
      },
      {
        path: 'verify-email',
        name: 'verify-email',
        component: () => import('@/views/auth/VerifyEmailView.vue'),
        meta: { title: 'Stockly — Verificar correo' }
      }
    ]
  },

  // ---- Dashboard (protegido) ----
  {
    path: '/dashboard',
    component: () => import('@/layouts/DashboardLayout.vue'),
    meta: { requiresAuth: true, requiresStaff: true, breadcrumb: 'Dashboard' },
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardHome.vue'),
        meta: { title: 'Stockly — Dashboard', breadcrumb: 'Inicio' }
      },
      {
        path: 'categorias',
        name: 'categories',
        component: () => import('@/views/dashboard/CategoriesView.vue'),
        meta: { title: 'Stockly — Categorías', breadcrumb: 'Categorías' }
      },
      {
        path: 'categorias/nueva',
        name: 'category-new',
        component: () => import('@/views/dashboard/CategoryFormView.vue'),
        meta: {
          title: 'Stockly — Nueva categoría',
          breadcrumb: 'Nueva categoría',
          breadcrumbParent: { label: 'Categorías', to: '/dashboard/categorias' },
          requiresAdmin: true
        }
      },
      {
        path: 'categorias/:id/editar',
        name: 'category-edit',
        component: () => import('@/views/dashboard/CategoryFormView.vue'),
        meta: {
          title: 'Stockly — Editar categoría',
          breadcrumb: 'Editar categoría',
          breadcrumbParent: { label: 'Categorías', to: '/dashboard/categorias' },
          requiresAdmin: true
        }
      },
      {
        path: 'subcategorias/nueva',
        name: 'subcategory-new',
        component: () => import('@/views/dashboard/SubcategoryFormView.vue'),
        meta: {
          title: 'Stockly — Nueva subcategoría',
          breadcrumb: 'Nueva subcategoría',
          breadcrumbParent: { label: 'Categorías', to: '/dashboard/categorias' },
          requiresAdmin: true
        }
      },
      {
        path: 'subcategorias/:id/editar',
        name: 'subcategory-edit',
        component: () => import('@/views/dashboard/SubcategoryFormView.vue'),
        meta: {
          title: 'Stockly — Editar subcategoría',
          breadcrumb: 'Editar subcategoría',
          breadcrumbParent: { label: 'Categorías', to: '/dashboard/categorias' },
          requiresAdmin: true
        }
      },
      {
        path: 'productos',
        name: 'products',
        component: () => import('@/views/dashboard/ProductsView.vue'),
        meta: { title: 'Stockly — Productos', breadcrumb: 'Productos' }
      },
      {
        path: 'productos/nuevo',
        name: 'product-new',
        component: () => import('@/views/dashboard/ProductFormView.vue'),
        meta: {
          title: 'Stockly — Nuevo producto',
          breadcrumb: 'Nuevo producto',
          breadcrumbParent: { label: 'Productos', to: '/dashboard/productos' },
          requiresAdmin: true
        }
      },
      {
        path: 'productos/:id',
        name: 'product-detail',
        component: () => import('@/views/dashboard/ProductDetailView.vue'),
        meta: {
          title: 'Stockly — Detalle del producto',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Productos', to: '/dashboard/productos' }
        }
      },
      {
        path: 'productos/:id/editar',
        name: 'product-edit',
        component: () => import('@/views/dashboard/ProductFormView.vue'),
        meta: {
          title: 'Stockly — Editar producto',
          breadcrumb: 'Editar producto',
          breadcrumbParent: { label: 'Productos', to: '/dashboard/productos' },
          requiresAdmin: true
        }
      },
      {
        path: 'atributos',
        name: 'attributes',
        component: () => import('@/views/dashboard/AttributesView.vue'),
        meta: { title: 'Stockly — Atributos', breadcrumb: 'Atributos', requiresAdmin: true }
      },
      {
        path: 'inventario',
        name: 'inventory',
        component: () => import('@/views/dashboard/InventoryView.vue'),
        meta: { title: 'Stockly — Inventario', breadcrumb: 'Inventario' }
      },
      {
        path: 'bodegas',
        name: 'warehouses',
        component: () => import('@/views/dashboard/WarehousesView.vue'),
        meta: { title: 'Stockly — Bodegas', breadcrumb: 'Bodegas', requiresAdmin: true }
      },
      {
        path: 'bodegas/nueva',
        name: 'warehouse-new',
        component: () => import('@/views/dashboard/WarehouseFormView.vue'),
        meta: {
          title: 'Stockly — Nueva bodega',
          breadcrumb: 'Nueva bodega',
          breadcrumbParent: { label: 'Bodegas', to: '/dashboard/bodegas' },
          requiresAdmin: true
        }
      },
      {
        path: 'bodegas/:id/editar',
        name: 'warehouse-edit',
        component: () => import('@/views/dashboard/WarehouseFormView.vue'),
        meta: {
          title: 'Stockly — Editar bodega',
          breadcrumb: 'Editar bodega',
          breadcrumbParent: { label: 'Bodegas', to: '/dashboard/bodegas' },
          requiresAdmin: true
        }
      },
      {
        path: 'movimientos',
        name: 'movements',
        component: () => import('@/views/dashboard/MovementsView.vue'),
        meta: { title: 'Stockly — Movimientos', breadcrumb: 'Movimientos', requiresAdmin: true }
      },
      {
        path: 'transferencias',
        name: 'transfers',
        component: () => import('@/views/dashboard/TransfersView.vue'),
        meta: { title: 'Stockly — Transferencias', breadcrumb: 'Transferencias', requiresManager: true }
      },
      {
        path: 'pos',
        name: 'pos',
        component: () => import('@/views/dashboard/PointOfSaleView.vue'),
        meta: { title: 'Stockly — Punto de venta', breadcrumb: 'Punto de venta' }
      },
      {
        path: 'ventas',
        name: 'sales',
        component: () => import('@/views/dashboard/SalesView.vue'),
        meta: { title: 'Stockly — Ventas', breadcrumb: 'Ventas' }
      },
      {
        path: 'pedidos',
        name: 'orders',
        component: () => import('@/views/dashboard/OrdersView.vue'),
        meta: { title: 'Stockly — Pedidos', breadcrumb: 'Pedidos' }
      },
      {
        path: 'pedidos/:id',
        name: 'order-detail',
        component: () => import('@/views/dashboard/OrderDetailView.vue'),
        meta: {
          title: 'Stockly — Detalle de pedido',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Pedidos', to: '/dashboard/pedidos' }
        }
      },
      {
        path: 'ventas/:id',
        name: 'sale-detail',
        component: () => import('@/views/dashboard/SaleDetailView.vue'),
        meta: {
          title: 'Stockly — Detalle de venta',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Ventas', to: '/dashboard/ventas' }
        }
      },
      {
        path: 'clientes',
        name: 'customers',
        component: () => import('@/views/dashboard/CustomersView.vue'),
        meta: { title: 'Stockly — Clientes', breadcrumb: 'Clientes' }
      },
      {
        path: 'clientes/nuevo',
        name: 'customer-new',
        component: () => import('@/views/dashboard/CustomerFormView.vue'),
        meta: {
          title: 'Stockly — Nuevo cliente',
          breadcrumb: 'Nuevo cliente',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'clientes/:id',
        name: 'customer-detail',
        component: () => import('@/views/dashboard/CustomerDetailView.vue'),
        meta: {
          title: 'Stockly — Detalle del cliente',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'clientes/:id/editar',
        name: 'customer-edit',
        component: () => import('@/views/dashboard/CustomerFormView.vue'),
        meta: {
          title: 'Stockly — Editar cliente',
          breadcrumb: 'Editar cliente',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'usuarios',
        name: 'users',
        component: () => import('@/views/dashboard/UsersView.vue'),
        meta: { title: 'Stockly — Usuarios', breadcrumb: 'Usuarios', requiresAdmin: true }
      },
      {
        path: 'usuarios/nuevo',
        name: 'user-new',
        component: () => import('@/views/dashboard/UserFormView.vue'),
        meta: {
          title: 'Stockly — Nuevo usuario',
          breadcrumb: 'Nuevo usuario',
          breadcrumbParent: { label: 'Usuarios', to: '/dashboard/usuarios' },
          requiresAdmin: true
        }
      },
      {
        path: 'usuarios/:id/editar',
        name: 'user-edit',
        component: () => import('@/views/dashboard/UserFormView.vue'),
        meta: {
          title: 'Stockly — Editar usuario',
          breadcrumb: 'Editar usuario',
          breadcrumbParent: { label: 'Usuarios', to: '/dashboard/usuarios' },
          requiresAdmin: true
        }
      },
      {
        path: 'perfil',
        name: 'profile',
        component: () => import('@/views/dashboard/ProfileView.vue'),
        meta: { title: 'Stockly — Mi perfil', breadcrumb: 'Mi perfil' }
      }
    ]
  },

  // ---- 404 ----
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 90 }
    return { top: 0 }
  }
})

// Guard global de autenticación.
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Revalida la sesión una sola vez al cargar la app.
  if (!auth.initialized) {
    await auth.fetchMe()
  }

  // Carga carrito y favoritos una sola vez (del servidor si hay sesión; local si no).
  const cart = useCartStore()
  if (!cart.ready) await cart.hydrate()
  const wishlist = useWishlistStore()
  if (!wishlist.ready) await wishlist.hydrate()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // El back-office (dashboard) es solo para staff. El comprador va a su cuenta.
  if (to.meta.requiresStaff && !auth.isStaff) {
    return auth.isAuthenticated ? { name: 'account' } : { name: 'login', query: { redirect: to.fullPath } }
  }

  // Rutas solo para administradores: un usuario sin rol admin no entra.
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'products' }
  }

  // Rutas de jefe de punto / admin (p. ej. transferencias): el cajero no entra.
  if (to.meta.requiresManager && !auth.isManager) {
    return { name: 'dashboard' }
  }

  // Un usuario ya autenticado no ve login/registro: staff al dashboard, comprador a la tienda.
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return auth.isStaff ? { name: 'dashboard' } : { name: 'home' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title || 'Stockly'
})

export default router
