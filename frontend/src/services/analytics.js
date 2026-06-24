import api from './api'

/**
 * Analítica del panel: un endpoint trae todo el panorama (KPIs, series, top,
 * inventario…) y otro genera reportes CSV descargables.
 */
export const analyticsApi = {
  overview(params = {}) {
    return api.get('/analytics/overview/', { params }).then((r) => r.data)
  },

  // Descarga un reporte CSV (respeta el periodo/bodega actuales).
  async download(params = {}) {
    const res = await api.get('/analytics/export/', { params, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `stockly-${params.dataset || 'reporte'}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  }
}
