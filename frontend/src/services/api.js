import axios from 'axios'

/**
 * Cliente HTTP central de Stockly.
 * - baseURL: en desarrollo usa '/api' (proxy de Vite hacia Django). En
 *   producción se define con la variable de entorno VITE_API_URL al compilar.
 * - Adjunta el access token en cada petición.
 * - Si el access token expira (401), intenta renovarlo con el refresh token
 *   una sola vez y reintenta la petición original.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const ACCESS_KEY = 'stockly_access'
const REFRESH_KEY = 'stockly_refresh'

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }
}

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
})

// --- Request: adjunta el token ---
api.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- Response: renueva el token ante un 401 ---
let isRefreshing = false
let queue = []

function resolveQueue(error, token = null) {
  queue.forEach((p) => (error ? p.reject(error) : p.resolve(token)))
  queue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    // No reintentar el propio refresh ni peticiones ya reintentadas.
    const isAuthEndpoint =
      original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh')

    if (status === 401 && !original._retry && !isAuthEndpoint && tokenStore.refresh) {
      if (isRefreshing) {
        // Espera a que termine el refresh en curso.
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject })
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`
          return api(original)
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh/`, {
          refresh: tokenStore.refresh
        })
        tokenStore.set({ access: data.access, refresh: data.refresh })
        resolveQueue(null, data.access)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (refreshError) {
        resolveQueue(refreshError, null)
        tokenStore.clear()
        // Redirige al login si la sesión ya no es válida.
        if (window.location.pathname.startsWith('/dashboard')) {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
