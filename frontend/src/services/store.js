import api from './api'

/**
 * Servicio de la tienda pública y del área de cuenta del comprador.
 */

export const storeApi = {
  categories() {
    return api.get('/store/categories/').then((r) => r.data)
  },
  brands(params = {}) {
    return api.get('/store/brands/', { params }).then((r) => r.data)
  },
  // Filtros por atributos de variación (Color, Talla, Almacenamiento…).
  attributeFilters(params = {}) {
    return api.get('/store/attribute-filters/', { params }).then((r) => r.data)
  },
  priceRange(params = {}) {
    return api.get('/store/price-range/', { params }).then((r) => r.data)
  },
  variantStock(ids) {
    return api.get('/store/variants/stock/', { params: { ids: ids.join(',') } }).then((r) => r.data)
  },
  products(params = {}) {
    return api.get('/store/products/', { params }).then((r) => r.data)
  },
  product(slug) {
    return api.get(`/store/products/${slug}/`).then((r) => r.data)
  },
  points() {
    return api.get('/store/points/').then((r) => r.data)
  }
}

// Carrito persistido por cuenta (solo para usuarios autenticados).
export const cartApi = {
  list() {
    return api.get('/account/cart/').then((r) => r.data)
  },
  // Fija la cantidad ABSOLUTA de una variante (crea o actualiza).
  set(variant, quantity) {
    return api.post('/account/cart/', { variant, quantity }).then((r) => r.data)
  },
  remove(variant) {
    return api.delete(`/account/cart/${variant}/`)
  },
  // Fusiona el carrito local del visitante al iniciar sesión.
  merge(items) {
    return api.post('/account/cart/merge/', { items }).then((r) => r.data)
  },
  clear() {
    return api.delete('/account/cart/clear/')
  }
}

// Favoritos persistidos por cuenta (solo usuarios autenticados).
export const favoritesApi = {
  list() {
    return api.get('/account/favorites/').then((r) => r.data)
  },
  add(product, value = null) {
    return api.post('/account/favorites/', { product, value }).then((r) => r.data)
  },
  remove(product, value = null) {
    return api.post('/account/favorites/remove/', { product, value })
  },
  merge(items) {
    return api.post('/account/favorites/merge/', { items }).then((r) => r.data)
  },
  clear() {
    return api.delete('/account/favorites/clear/')
  }
}

// Pedidos del comprador (compra en línea).
export const ordersApi = {
  list(params = {}) {
    return api.get('/account/orders/', { params }).then((r) => r.data)
  },
  // Historial unificado: pedidos en línea + ventas en tienda del comprador.
  purchases() {
    return api.get('/account/purchases/').then((r) => r.data)
  },
  // Detalle de una compra en tienda (POS) del comprador.
  sale(id) {
    return api.get(`/account/purchases/sale/${id}/`).then((r) => r.data)
  },
  // El comprador se reenvía el recibo de su venta (a su correo o a otro).
  resendSaleReceipt(id, email) {
    return api
      .post(`/account/purchases/sale/${id}/send-receipt/`, email ? { email } : {})
      .then((r) => r.data)
  },
  get(id) {
    return api.get(`/account/orders/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/account/orders/', payload).then((r) => r.data)
  },
  cancel(id) {
    return api.post(`/account/orders/${id}/cancel/`).then((r) => r.data)
  },
  checkAvailability(payload) {
    return api.post('/account/orders/availability/', payload).then((r) => r.data)
  },
  // Opciones de entrega del carrito: ¿se puede enviar? ¿en qué tiendas se recoge?
  fulfillmentOptions(payload) {
    return api.post('/account/orders/fulfillment-options/', payload).then((r) => r.data)
  }
}

// Pedidos en el back-office (gestión por el personal).
export const staffOrdersApi = {
  list(params = {}) {
    return api.get('/orders/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/orders/${id}/`).then((r) => r.data)
  },
  advance(id) {
    return api.post(`/orders/${id}/advance/`).then((r) => r.data)
  },
  cancel(id, reason = '') {
    return api.post(`/orders/${id}/cancel/`, { reason }).then((r) => r.data)
  }
}

// Ubicaciones (datos propios en la BD): país → departamento → ciudad.
export const geoApi = {
  countries() {
    return api.get('/geo/countries/').then((r) => r.data)
  },
  departments(country) {
    return api.get('/geo/departments/', { params: { country } }).then((r) => r.data)
  },
  cities(department) {
    return api.get('/geo/cities/', { params: { department } }).then((r) => r.data)
  }
}

export const addressesApi = {
  list() {
    return api.get('/account/addresses/').then((r) => r.data)
  },
  create(payload) {
    return api.post('/account/addresses/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/account/addresses/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/account/addresses/${id}/`)
  }
}

export const paymentMethodsApi = {
  list() {
    return api.get('/account/payment-methods/').then((r) => r.data)
  },
  create(payload) {
    return api.post('/account/payment-methods/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/account/payment-methods/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/account/payment-methods/${id}/`)
  }
}
