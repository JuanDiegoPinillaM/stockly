import { defineStore } from 'pinia'
import { cartApi } from '@/services/store'
import { useAuthStore } from './auth'

const STORAGE_KEY = 'stockly_cart'

function loadGuest() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function isAuthed() {
  return useAuthStore().isAuthenticated
}

// Convierte una línea del servidor al formato local del carrito.
function fromServer(it) {
  return {
    variantId: it.variant,
    productSlug: it.product_slug,
    name: it.name,
    variantLabel: it.variant_label,
    price: Number(it.price),
    image: it.image || '',
    quantity: it.quantity,
    stock: it.stock
  }
}

/**
 * Carrito de compra de la tienda.
 *
 * - Visitante (sin sesión): vive en el navegador (localStorage).
 * - Con sesión: vive en el servidor (tabla CartItem), atado a la CUENTA, así el
 *   carrito te sigue entre dispositivos y cambiar de cuenta no mezcla carritos.
 * - Al iniciar sesión, el carrito de invitado se fusiona con el de la cuenta.
 *
 * Cada línea guarda lo mínimo para mostrarse; la disponibilidad real se revalida
 * contra el punto elegido al pagar.
 */
export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [],
    ready: false
  }),

  getters: {
    count: (state) => state.items.reduce((n, i) => n + i.quantity, 0),
    lineCount: (state) => state.items.length,
    subtotal: (state) => state.items.reduce((n, i) => n + i.price * i.quantity, 0),
    isEmpty: (state) => state.items.length === 0,
    has: (state) => (variantId) => state.items.some((i) => i.variantId === variantId),
    quantityOf: (state) => (variantId) =>
      state.items.find((i) => i.variantId === variantId)?.quantity || 0
  },

  actions: {
    // --------------------- Sesión / carga ---------------------
    persistGuest() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.items))
    },

    // Tope de existencias de una línea (Infinity si no se conoce el stock).
    _cap(item) {
      return Number.isFinite(item?.stock) ? item.stock : Infinity
    },

    /** Carga inicial (una vez): del servidor si hay sesión, del navegador si no. */
    async hydrate() {
      if (this.ready) return
      if (isAuthed()) await this.loadFromServer()
      else this.items = loadGuest()
      this.ready = true
    },

    async loadFromServer() {
      try {
        const data = await cartApi.list()
        this.items = (data || []).map(fromServer)
      } catch {
        /* si falla, deja el carrito como esté */
      }
    },

    /** Al iniciar sesión: fusiona el carrito de invitado con el de la cuenta. */
    async onLogin() {
      const guest = loadGuest()
      try {
        if (guest.length) {
          const payload = guest.map((i) => ({ variant: i.variantId, quantity: i.quantity }))
          const data = await cartApi.merge(payload)
          this.items = (data || []).map(fromServer)
        } else {
          await this.loadFromServer()
        }
      } catch {
        await this.loadFromServer()
      }
      localStorage.removeItem(STORAGE_KEY) // ya se fusionó al de la cuenta
      this.ready = true
    },

    /** Al cerrar sesión: el carrito es de la cuenta, queda vacío para el invitado. */
    onLogout() {
      this.items = []
      localStorage.removeItem(STORAGE_KEY)
    },

    // Sincroniza una línea (cantidad absoluta) según la sesión.
    _syncSet(variantId, quantity) {
      if (isAuthed()) cartApi.set(variantId, quantity).catch(() => {})
      else this.persistGuest()
    },
    _syncRemove(variantId) {
      if (isAuthed()) cartApi.remove(variantId).catch(() => {})
      else this.persistGuest()
    },

    // --------------------- Operaciones ---------------------
    add(line, quantity = 1) {
      const existing = this.items.find((i) => i.variantId === line.variantId)
      let qty
      if (existing) {
        // Refresca el stock al más reciente y nunca supera el disponible.
        if (Number.isFinite(line.stock)) existing.stock = line.stock
        existing.quantity = Math.min(existing.quantity + quantity, this._cap(existing))
        qty = existing.quantity
      } else {
        const cap = Number.isFinite(line.stock) ? line.stock : Infinity
        qty = Math.min(quantity, cap)
        this.items.push({ ...line, quantity: qty })
      }
      this._syncSet(line.variantId, qty)
    },

    setQuantity(variantId, quantity) {
      const item = this.items.find((i) => i.variantId === variantId)
      if (!item) return
      const qty = Number(quantity)
      if (!Number.isFinite(qty)) return
      item.quantity = Math.min(Math.max(1, Math.floor(qty)), this._cap(item))
      this._syncSet(variantId, item.quantity)
    },

    /**
     * Aplica el stock real (mapa {variantId: stock}) y reajusta cantidades.
     * Devuelve la lista de cambios para avisar al usuario:
     *   [{ variantId, name, variantLabel, from, to, outOfStock }]
     */
    refreshStock(stockMap) {
      const changes = []
      const touched = []
      this.items.forEach((i) => {
        const s = stockMap[i.variantId]
        if (s == null) return
        const prev = i.quantity
        i.stock = s
        if (s <= 0) {
          changes.push({
            variantId: i.variantId,
            name: i.name,
            variantLabel: i.variantLabel,
            from: prev,
            to: 0,
            outOfStock: true
          })
        } else if (prev > s) {
          i.quantity = s
          touched.push(i.variantId)
          changes.push({
            variantId: i.variantId,
            name: i.name,
            variantLabel: i.variantLabel,
            from: prev,
            to: s,
            outOfStock: false
          })
        }
      })
      if (isAuthed()) {
        touched.forEach((v) => {
          const it = this.items.find((x) => x.variantId === v)
          if (it) cartApi.set(v, it.quantity).catch(() => {})
        })
      } else {
        this.persistGuest()
      }
      return changes
    },

    remove(variantId) {
      this.items = this.items.filter((i) => i.variantId !== variantId)
      this._syncRemove(variantId)
    },

    clear() {
      this.items = []
      if (isAuthed()) cartApi.clear().catch(() => {})
      else this.persistGuest()
    },

    /** Líneas en el formato que espera el backend para crear/consultar. */
    toItemsPayload() {
      return this.items.map((i) => ({ variant: i.variantId, quantity: i.quantity }))
    }
  }
})
