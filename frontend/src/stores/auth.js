import { defineStore } from 'pinia'
import api, { tokenStore } from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('stockly_user') || 'null'),
    // Espejo reactivo del token: los getters de Pinia son computed y solo
    // reaccionan a estado reactivo, no a localStorage directamente.
    accessToken: tokenStore.access,
    initialized: false
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
    isAdmin: (state) => state.user?.role === 'admin',
    // Staff = back-office (admin, jefe de punto, cajero). El comprador no entra.
    isStaff: (state) => ['admin', 'jefe_punto', 'cajero'].includes(state.user?.role),
    // Manager = admin o jefe de punto: opera transferencias entre puntos.
    isManager: (state) => ['admin', 'jefe_punto'].includes(state.user?.role),
    isBuyer: (state) => state.user?.role === 'comprador',
    fullName: (state) => {
      if (!state.user) return ''
      const name = `${state.user.first_name || ''} ${state.user.last_name || ''}`.trim()
      return name || state.user.email
    },
    firstName: (state) => {
      if (!state.user) return ''
      return state.user.first_name || state.user.email
    },
    initials: (state) => {
      if (!state.user) return '?'
      const base = state.user.first_name || state.user.email
      return base.charAt(0).toUpperCase()
    }
  },

  actions: {
    persistUser(user) {
      this.user = user
      localStorage.setItem('stockly_user', JSON.stringify(user))
    },

    async register(payload) {
      const { data } = await api.post('/auth/register/', payload)
      return data
    },

    async verifyEmail(payload) {
      const { data } = await api.post('/auth/verify-email/', payload)
      return data
    },

    async resendVerification(email) {
      const { data } = await api.post('/auth/resend-verification/', { email })
      return data
    },

    async requestPasswordReset(email) {
      const { data } = await api.post('/auth/password-reset/', { email })
      return data
    },

    async confirmPasswordReset(payload) {
      const { data } = await api.post('/auth/password-reset/confirm/', payload)
      return data
    },

    async login(credentials) {
      const { data } = await api.post('/auth/login/', credentials)
      tokenStore.set({ access: data.access, refresh: data.refresh })
      this.accessToken = data.access
      this.persistUser(data.user)
      // Fusiona carrito y favoritos de invitado con los de la cuenta (no bloquea el login).
      try {
        const { useCartStore } = await import('./cart')
        const { useWishlistStore } = await import('./wishlist')
        await Promise.all([useCartStore().onLogin(), useWishlistStore().onLogin()])
      } catch {
        /* el login no debe fallar por carrito/favoritos */
      }
      return data.user
    },

    /** Actualiza el perfil propio. payload puede ser FormData (con foto). */
    async updateProfile(payload) {
      const config =
        payload instanceof FormData
          ? { headers: { 'Content-Type': 'multipart/form-data' } }
          : {}
      const { data } = await api.patch('/auth/me/', payload, config)
      this.persistUser(data)
      return data
    },

    async changePassword(payload) {
      const { data } = await api.post('/auth/change-password/', payload)
      return data
    },

    /** Revalida la sesión con el backend (al recargar la app). */
    async fetchMe() {
      if (!tokenStore.access) {
        this.initialized = true
        return null
      }
      try {
        const { data } = await api.get('/auth/me/')
        this.persistUser(data)
        return data
      } catch {
        this.logout()
        return null
      } finally {
        this.initialized = true
      }
    },

    async logout() {
      // Invalida el refresh token en el servidor (blacklist). No bloquea el
      // cierre de sesión local si la petición falla.
      const refresh = tokenStore.refresh
      if (refresh) {
        try {
          await api.post('/auth/logout/', { refresh })
        } catch {
          /* sesión local se cierra igual */
        }
      }
      tokenStore.clear()
      localStorage.removeItem('stockly_user')
      this.user = null
      this.accessToken = null
      // Carrito y favoritos son de la cuenta: al salir quedan vacíos para el siguiente.
      try {
        const { useCartStore } = await import('./cart')
        const { useWishlistStore } = await import('./wishlist')
        useCartStore().onLogout()
        useWishlistStore().onLogout()
      } catch {
        /* ignore */
      }
    }
  }
})
