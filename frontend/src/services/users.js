import api from './api'

/**
 * Servicio del módulo de Usuarios (solo admin). Crear envía una invitación
 * por correo; eliminar desactiva (soft-delete).
 */
export const usersApi = {
  list(params = {}) {
    return api.get('/users/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/users/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/users/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/users/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/users/${id}/`)
  },
  resendInvitation(id) {
    return api.post(`/users/${id}/resend-invitation/`).then((r) => r.data)
  }
}
