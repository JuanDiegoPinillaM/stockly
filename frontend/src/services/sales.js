import api from './api'

/**
 * Servicio del módulo de Ventas (POS): clientes y ventas.
 */

export const customersApi = {
  list(params = {}) {
    return api.get('/customers/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/customers/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/customers/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/customers/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/customers/${id}/`)
  }
}

export const salesApi = {
  list(params = {}) {
    return api.get('/sales/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/sales/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/sales/', payload).then((r) => r.data)
  },
  void(id) {
    return api.post(`/sales/${id}/void/`).then((r) => r.data)
  },
  sendReceipt(id, email) {
    return api.post(`/sales/${id}/send-receipt/`, { email }).then((r) => r.data)
  }
}
