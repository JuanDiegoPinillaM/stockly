import api from './api'

/**
 * Servicio del módulo de inventario: bodegas, movimientos (kardex),
 * existencias por bodega y bajo stock. Reutiliza el cliente axios central.
 */

// ----------------------------- Bodegas -----------------------------
export const warehousesApi = {
  list(params = {}) {
    return api.get('/warehouses/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/warehouses/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/warehouses/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/warehouses/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/warehouses/${id}/`)
  }
}

// ------------------------- Movimientos (kardex) -------------------------
// El libro es inmutable: solo se listan y se crean.
export const movementsApi = {
  list(params = {}) {
    return api.get('/movements/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/movements/', payload).then((r) => r.data)
  }
}

// ----------------------- Existencias por bodega -----------------------
export const stockLevelsApi = {
  list(params = {}) {
    return api.get('/stock-levels/', { params }).then((r) => r.data)
  }
}

// ------------------- Existencias valorizadas (reporte) -------------------
// Devuelve { results, summary, count, ... }: cada variante con su valor y
// desglose por bodega, más el resumen global del inventario.
export const stockApi = {
  list(params = {}) {
    return api.get('/stock/', { params }).then((r) => r.data)
  }
}

// ----------------------------- Bajo stock -----------------------------
export const lowStockApi = {
  list(params = {}) {
    return api.get('/low-stock/', { params }).then((r) => r.data)
  }
}

// ------------------------- Transferencias entre puntos -------------------------
// Flujo con aprobación: solicitar (reserva stock), aceptar/rechazar (jefe destino),
// cancelar (solicitante). Inmutables salvo el cambio de estado.
export const transfersApi = {
  list(params = {}) {
    return api.get('/transfers/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/transfers/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/transfers/', payload).then((r) => r.data)
  },
  accept(id) {
    return api.post(`/transfers/${id}/accept/`).then((r) => r.data)
  },
  reject(id) {
    return api.post(`/transfers/${id}/reject/`).then((r) => r.data)
  },
  cancel(id) {
    return api.post(`/transfers/${id}/cancel/`).then((r) => r.data)
  }
}
