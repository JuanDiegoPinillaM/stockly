import api from './api'

/**
 * Servicio del catálogo: categorías, subcategorías y productos.
 * Reutiliza el cliente axios central (token + refresh automáticos).
 *
 * Los listados usan paginación de DRF: { count, next, previous, results }.
 */

// --------------------------- Categorías ---------------------------
export const categoriesApi = {
  list(params = {}) {
    return api.get('/categories/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/categories/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/categories/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/categories/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/categories/${id}/`)
  }
}

// -------------------------- Subcategorías --------------------------
export const subcategoriesApi = {
  list(params = {}) {
    return api.get('/subcategories/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/subcategories/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/subcategories/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/subcategories/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/subcategories/${id}/`)
  }
}

// ------------------------------ Marcas ------------------------------
export const brandsApi = {
  list(params = {}) {
    return api.get('/brands/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/brands/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/brands/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/brands/${id}/`)
  }
}

// ----------------------------- Colores -----------------------------
export const colorsApi = {
  list(params = {}) {
    return api.get('/colors/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/colors/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/colors/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/colors/${id}/`)
  }
}

// ------------------------------ Tallas ------------------------------
export const sizesApi = {
  list(params = {}) {
    return api.get('/sizes/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/sizes/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/sizes/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/sizes/${id}/`)
  }
}

// ------------------ Catálogo de atributos (reutilizable) ------------------
// Atributos genéricos (Color, Talla, Almacenamiento…) con sus opciones.
export const attributeDefinitionsApi = {
  list(params = {}) {
    return api.get('/attribute-definitions/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/attribute-definitions/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/attribute-definitions/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/attribute-definitions/${id}/`)
  }
}

export const attributeOptionsApi = {
  list(params = {}) {
    return api.get('/attribute-options/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/attribute-options/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/attribute-options/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/attribute-options/${id}/`)
  }
}

// --------------------------- Variantes ---------------------------
// Dueñas del SKU, código de barras, precios y stock de cada combinación.
// Su combinación se define con `value_ids` (valores de atributo elegidos).
const MULTIPART = { headers: { 'Content-Type': 'multipart/form-data' } }

export const variantsApi = {
  list(params = {}) {
    return api.get('/variants/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/variants/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/variants/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/variants/${id}/`)
  }
}

// ----------------- Atributos de variación (por producto) -----------------
export const productAttributesApi = {
  list(params = {}) {
    return api.get('/product-attributes/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/product-attributes/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/product-attributes/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/product-attributes/${id}/`)
  }
}

export const attributeValuesApi = {
  list(params = {}) {
    return api.get('/attribute-values/', { params }).then((r) => r.data)
  },
  create(payload) {
    return api.post('/attribute-values/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/attribute-values/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/attribute-values/${id}/`)
  }
}

// ----------------- Imágenes del producto (por valor del eje visual) -----------------
export const productImagesApi = {
  list(params = {}) {
    return api.get('/product-images/', { params }).then((r) => r.data)
  },
  add(productId, file, { value = null, altText = '' } = {}) {
    const fd = new FormData()
    fd.append('product', productId)
    fd.append('image', file)
    if (value != null) fd.append('value', value)
    if (altText) fd.append('alt_text', altText)
    return api.post('/product-images/', fd, MULTIPART).then((r) => r.data)
  },
  remove(imageId) {
    return api.delete(`/product-images/${imageId}/`)
  },
  reorder(orderedIds) {
    return api.post('/product-images/reorder/', { order: orderedIds }).then((r) => r.data)
  }
}

// ---------------------------- Productos ----------------------------
export const productsApi = {
  list(params = {}) {
    return api.get('/products/', { params }).then((r) => r.data)
  },
  get(id) {
    return api.get(`/products/${id}/`).then((r) => r.data)
  },
  create(payload) {
    return api.post('/products/', payload).then((r) => r.data)
  },
  update(id, payload) {
    return api.patch(`/products/${id}/`, payload).then((r) => r.data)
  },
  remove(id) {
    return api.delete(`/products/${id}/`)
  }
}
