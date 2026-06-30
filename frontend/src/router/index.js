import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { useConfigStore } from '@/stores/config'

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
        meta: { title: 'Tienda' }
      },
      {
        path: 'productos',
        name: 'catalog',
        component: () => import('@/views/store/StoreCatalogView.vue'),
        meta: { title: 'Productos' }
      },
      {
        path: 'tiendas',
        name: 'locations',
        component: () => import('@/views/store/StoreLocationsView.vue'),
        meta: { title: 'Tiendas' }
      },
      {
        path: 'quienes-somos',
        name: 'about',
        component: () => import('@/views/store/StoreAboutView.vue'),
        meta: { title: 'Quiénes somos' }
      },
      {
        path: 'producto/:slug',
        name: 'store-product',
        component: () => import('@/views/store/StoreProductView.vue'),
        meta: { title: 'Producto' }
      },
      {
        path: 'carrito',
        name: 'cart',
        component: () => import('@/views/store/CartView.vue'),
        meta: { title: 'Carrito' }
      },
      {
        path: 'favoritos',
        name: 'wishlist',
        component: () => import('@/views/store/WishlistView.vue'),
        meta: { title: 'Mis favoritos' }
      },
      {
        path: 'checkout',
        name: 'checkout',
        component: () => import('@/views/store/CheckoutView.vue'),
        meta: { title: 'Finalizar compra', requiresAuth: true }
      },
      // ---- Área de cuenta del comprador ----
      {
        path: 'cuenta',
        name: 'account',
        component: () => import('@/views/store/AccountProfileView.vue'),
        meta: { title: 'Mi cuenta', requiresAuth: true }
      },
      {
        path: 'cuenta/direcciones',
        name: 'account-addresses',
        component: () => import('@/views/store/AccountAddressesView.vue'),
        meta: { title: 'Mis direcciones', requiresAuth: true }
      },
      {
        path: 'cuenta/metodos-pago',
        name: 'account-payments',
        component: () => import('@/views/store/AccountPaymentsView.vue'),
        meta: { title: 'Métodos de pago', requiresAuth: true }
      },
      {
        path: 'cuenta/compras',
        name: 'account-orders',
        component: () => import('@/views/store/AccountOrdersView.vue'),
        meta: { title: 'Mis compras', requiresAuth: true }
      },
      {
        path: 'cuenta/compras/pedido/:id',
        name: 'account-order-detail',
        component: () => import('@/views/store/AccountOrderDetailView.vue'),
        meta: { title: 'Detalle de compra', requiresAuth: true }
      },
      {
        path: 'cuenta/compras/venta/:id',
        name: 'account-sale-detail',
        component: () => import('@/views/store/AccountSaleDetailView.vue'),
        meta: { title: 'Detalle de compra', requiresAuth: true }
      },

      // ---- Autenticación (integrada en la tienda: navbar + footer) ----
      {
        path: 'login',
        name: 'login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { title: 'Iniciar sesión', guestOnly: true }
      },
      {
        path: 'register',
        name: 'register',
        component: () => import('@/views/auth/RegisterView.vue'),
        meta: { title: 'Crear cuenta', guestOnly: true }
      },
      {
        path: 'forgot-password',
        name: 'forgot-password',
        component: () => import('@/views/auth/ForgotPasswordView.vue'),
        meta: { title: 'Recuperar contraseña', guestOnly: true }
      },
      {
        path: 'reset-password',
        name: 'reset-password',
        component: () => import('@/views/auth/ResetPasswordView.vue'),
        meta: { title: 'Restablecer contraseña' }
      },
      {
        path: 'verify-email',
        name: 'verify-email',
        component: () => import('@/views/auth/VerifyEmailView.vue'),
        meta: { title: 'Verificar correo' }
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
        meta: { title: 'Dashboard', breadcrumb: 'Inicio' }
      },
      {
        path: 'categorias',
        name: 'categories',
        component: () => import('@/views/dashboard/CategoriesView.vue'),
        meta: { title: 'Categorías', breadcrumb: 'Categorías' }
      },
      {
        path: 'categorias/nueva',
        name: 'category-new',
        component: () => import('@/views/dashboard/CategoryFormView.vue'),
        meta: {
          title: 'Nueva categoría',
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
          title: 'Editar categoría',
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
          title: 'Nueva subcategoría',
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
          title: 'Editar subcategoría',
          breadcrumb: 'Editar subcategoría',
          breadcrumbParent: { label: 'Categorías', to: '/dashboard/categorias' },
          requiresAdmin: true
        }
      },
      {
        path: 'productos',
        name: 'products',
        component: () => import('@/views/dashboard/ProductsView.vue'),
        meta: { title: 'Productos', breadcrumb: 'Productos' }
      },
      {
        path: 'productos/nuevo',
        name: 'product-new',
        component: () => import('@/views/dashboard/ProductFormView.vue'),
        meta: {
          title: 'Nuevo producto',
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
          title: 'Detalle del producto',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Productos', to: '/dashboard/productos' }
        }
      },
      {
        path: 'productos/:id/editar',
        name: 'product-edit',
        component: () => import('@/views/dashboard/ProductFormView.vue'),
        meta: {
          title: 'Editar producto',
          breadcrumb: 'Editar producto',
          breadcrumbParent: { label: 'Productos', to: '/dashboard/productos' },
          requiresAdmin: true
        }
      },
      {
        path: 'atributos',
        name: 'attributes',
        component: () => import('@/views/dashboard/AttributesView.vue'),
        meta: { title: 'Atributos', breadcrumb: 'Atributos', requiresAdmin: true }
      },
      {
        path: 'inventario',
        name: 'inventory',
        component: () => import('@/views/dashboard/InventoryView.vue'),
        meta: { title: 'Inventario', breadcrumb: 'Inventario' }
      },
      {
        path: 'bodegas',
        name: 'warehouses',
        component: () => import('@/views/dashboard/WarehousesView.vue'),
        meta: { title: 'Bodegas', breadcrumb: 'Bodegas', requiresAdmin: true }
      },
      {
        path: 'bodegas/nueva',
        name: 'warehouse-new',
        component: () => import('@/views/dashboard/WarehouseFormView.vue'),
        meta: {
          title: 'Nueva bodega',
          breadcrumb: 'Nueva bodega',
          breadcrumbParent: { label: 'Bodegas', to: '/dashboard/bodegas' },
          requiresAdmin: true
        }
      },
      {
        path: 'bodegas/:id',
        name: 'warehouse-detail',
        component: () => import('@/views/dashboard/WarehouseDetailView.vue'),
        meta: {
          title: 'Bodega',
          breadcrumb: 'Bodega',
          breadcrumbParent: { label: 'Bodegas', to: '/dashboard/bodegas' },
          requiresAdmin: true
        }
      },
      {
        path: 'bodegas/:id/editar',
        name: 'warehouse-edit',
        component: () => import('@/views/dashboard/WarehouseFormView.vue'),
        meta: {
          title: 'Editar bodega',
          breadcrumb: 'Editar bodega',
          breadcrumbParent: { label: 'Bodegas', to: '/dashboard/bodegas' },
          requiresAdmin: true
        }
      },
      {
        path: 'configuracion',
        name: 'site-config',
        component: () => import('@/views/dashboard/EcommerceConfigView.vue'),
        meta: {
          title: 'Personalización',
          breadcrumb: 'Personalización',
          requiresAdmin: true
        }
      },
      {
        path: 'reportes',
        name: 'reports',
        component: () => import('@/views/dashboard/ReportsView.vue'),
        meta: {
          title: 'Reportes',
          breadcrumb: 'Reportes',
          requiresAdmin: true
        }
      },
      {
        path: 'movimientos',
        name: 'movements',
        component: () => import('@/views/dashboard/MovementsView.vue'),
        meta: { title: 'Movimientos', breadcrumb: 'Movimientos', requiresAdmin: true }
      },
      {
        path: 'transferencias',
        name: 'transfers',
        component: () => import('@/views/dashboard/TransfersView.vue'),
        meta: { title: 'Transferencias', breadcrumb: 'Transferencias', requiresManager: true }
      },
      {
        path: 'pos',
        name: 'pos',
        component: () => import('@/views/dashboard/PointOfSaleView.vue'),
        meta: { title: 'Punto de venta', breadcrumb: 'Punto de venta' }
      },
      {
        path: 'ventas',
        name: 'sales',
        component: () => import('@/views/dashboard/SalesView.vue'),
        meta: { title: 'Ventas', breadcrumb: 'Ventas' }
      },
      {
        path: 'pedidos',
        name: 'orders',
        component: () => import('@/views/dashboard/OrdersView.vue'),
        meta: { title: 'Pedidos', breadcrumb: 'Pedidos' }
      },
      {
        path: 'pedidos/:id',
        name: 'order-detail',
        component: () => import('@/views/dashboard/OrderDetailView.vue'),
        meta: {
          title: 'Detalle de pedido',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Pedidos', to: '/dashboard/pedidos' }
        }
      },
      {
        path: 'ventas/:id',
        name: 'sale-detail',
        component: () => import('@/views/dashboard/SaleDetailView.vue'),
        meta: {
          title: 'Detalle de venta',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Ventas', to: '/dashboard/ventas' }
        }
      },
      {
        path: 'clientes',
        name: 'customers',
        component: () => import('@/views/dashboard/CustomersView.vue'),
        meta: { title: 'Clientes', breadcrumb: 'Clientes' }
      },
      {
        path: 'clientes/nuevo',
        name: 'customer-new',
        component: () => import('@/views/dashboard/CustomerFormView.vue'),
        meta: {
          title: 'Nuevo cliente',
          breadcrumb: 'Nuevo cliente',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'clientes/:id',
        name: 'customer-detail',
        component: () => import('@/views/dashboard/CustomerDetailView.vue'),
        meta: {
          title: 'Detalle del cliente',
          breadcrumb: 'Detalle',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'clientes/:id/editar',
        name: 'customer-edit',
        component: () => import('@/views/dashboard/CustomerFormView.vue'),
        meta: {
          title: 'Editar cliente',
          breadcrumb: 'Editar cliente',
          breadcrumbParent: { label: 'Clientes', to: '/dashboard/clientes' }
        }
      },
      {
        path: 'usuarios',
        name: 'users',
        component: () => import('@/views/dashboard/UsersView.vue'),
        meta: { title: 'Usuarios', breadcrumb: 'Usuarios', requiresAdmin: true }
      },
      {
        path: 'usuarios/nuevo',
        name: 'user-new',
        component: () => import('@/views/dashboard/UserFormView.vue'),
        meta: {
          title: 'Nuevo usuario',
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
          title: 'Editar usuario',
          breadcrumb: 'Editar usuario',
          breadcrumbParent: { label: 'Usuarios', to: '/dashboard/usuarios' },
          requiresAdmin: true
        }
      },
      {
        path: 'perfil',
        name: 'profile',
        component: () => import('@/views/dashboard/ProfileView.vue'),
        meta: { title: 'Mi perfil', breadcrumb: 'Mi perfil' }
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
  // El store compone "Nombre del negocio — Etiqueta" y lo mantiene aunque se
  // cambie el nombre desde Configuración sin navegar.
  useConfigStore().setRouteTitle(to.meta.title)
})

export default router
