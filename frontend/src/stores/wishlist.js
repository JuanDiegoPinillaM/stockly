import { defineStore } from 'pinia'
import { favoritesApi } from '@/services/store'
import { useAuthStore } from './auth'

const KEY = 'stockly_wishlist'

function loadGuest() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}
function isAuthed() {
  return useAuthStore().isAuthenticated
}
function keyOf(productId, colorId) {
  return `${productId}:${colorId ?? ''}`
}

/**
 * Favoritos (lista de deseos).
 * - Visitante: en el navegador (localStorage), con la tarjeta completa.
 * - Con sesión: en el servidor (tabla WishlistItem), atado a la cuenta.
 * - Al iniciar sesión, los favoritos locales se fusionan con los de la cuenta.
 *
 * Cada ítem es una "tarjeta" lista para mostrarse (mismos campos que ProductCard)
 * e incluye product_id y color_id para identificarlo.
 */
export const useWishlistStore = defineStore('wishlist', {
  state: () => ({ items: [], ready: false }),

  getters: {
    count: (s) => s.items.length,
    has: (s) => (productId, colorId) =>
      s.items.some((i) => keyOf(i.product_id, i.color_id) === keyOf(productId, colorId))
  },

  actions: {
    persistGuest() {
      localStorage.setItem(KEY, JSON.stringify(this.items))
    },

    async hydrate() {
      if (this.ready) return
      if (isAuthed()) await this.loadFromServer()
      else this.items = loadGuest()
      this.ready = true
    },

    async loadFromServer() {
      try {
        this.items = (await favoritesApi.list()) || []
      } catch {
        /* deja lo que haya */
      }
    },

    async onLogin() {
      const guest = loadGuest()
      try {
        if (guest.length) {
          const payload = guest.map((i) => ({ product: i.product_id, value: i.color_id || null }))
          this.items = (await favoritesApi.merge(payload)) || []
        } else {
          await this.loadFromServer()
        }
      } catch {
        await this.loadFromServer()
      }
      localStorage.removeItem(KEY)
      this.ready = true
    },

    onLogout() {
      this.items = []
      localStorage.removeItem(KEY)
    },

    /** Alterna un favorito. `card` es la tarjeta completa (con product_id/color_id). */
    toggle(card) {
      const k = keyOf(card.product_id, card.color_id)
      const idx = this.items.findIndex((i) => keyOf(i.product_id, i.color_id) === k)
      if (idx >= 0) {
        this.items.splice(idx, 1)
        if (isAuthed()) favoritesApi.remove(card.product_id, card.color_id || null).catch(() => {})
        else this.persistGuest()
      } else {
        this.items.unshift({ ...card })
        if (isAuthed()) favoritesApi.add(card.product_id, card.color_id || null).catch(() => {})
        else this.persistGuest()
      }
    },

    clear() {
      this.items = []
      if (isAuthed()) favoritesApi.clear().catch(() => {})
      else this.persistGuest()
    }
  }
})
