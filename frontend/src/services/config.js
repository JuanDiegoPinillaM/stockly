import api from './api'

/**
 * Configuración global del ecommerce (identidad, marca, contacto, redes).
 * GET es público; el PATCH (solo admin) admite multipart para el logo.
 */

function cfg(payload) {
  return payload instanceof FormData
    ? { headers: { 'Content-Type': 'multipart/form-data' } }
    : undefined
}

export const configApi = {
  get() {
    return api.get('/config/').then((r) => r.data)
  },
  update(payload) {
    return api.patch('/config/', payload, cfg(payload)).then((r) => r.data)
  }
}
