<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter, RouterLink, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, ImagePlus, X, Plus, Trash2, Star, RotateCcw, ChevronDown } from 'lucide-vue-next'
import {
  productsApi,
  categoriesApi,
  brandsApi,
  variantsApi,
  productAttributesApi,
  attributeValuesApi,
  attributeDefinitionsApi,
  attributeOptionsApi,
  productImagesApi
} from '@/services/catalog'
import { warehousesApi, movementsApi } from '@/services/inventory'
import SearchSelect from '@/components/SearchSelect.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import LoadingState from '@/components/LoadingState.vue'
import { confirmDelete, confirmAction, toastSuccess, toastError } from '@/utils/notify'

const route = useRoute()
const router = useRouter()

const productId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(productId.value))

function money(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', maximumFractionDigits: 0
  }).format(value || 0)
}

const categories = ref([])
const selectedCategory = ref('')
const brands = ref([])
const definitions = ref([]) // catálogo de atributos (Color, Talla…) con sus opciones
const warehouses = ref([])

const unitOptions = [
  { value: 'unidad', label: 'Unidad' }, { value: 'kg', label: 'Kilogramo' },
  { value: 'g', label: 'Gramo' }, { value: 'lb', label: 'Libra' },
  { value: 'l', label: 'Litro' }, { value: 'ml', label: 'Mililitro' },
  { value: 'paquete', label: 'Paquete' }, { value: 'caja', label: 'Caja' },
  { value: 'docena', label: 'Docena' }
]
const taxOptions = [
  { value: 19, label: 'IVA 19%' }, { value: 5, label: 'IVA 5%' },
  { value: 0, label: 'Excluido / 0%' }
]

const form = ref({
  name: '', description: '', subcategory: '', brand: '',
  unit_of_measure: 'unidad', tax_rate: 19, expiration_date: '', is_active: true
})
const isPerishable = ref(false)
watch(isPerishable, (v) => { if (!v) form.value.expiration_date = '' })

// Estado del producto ya persistido (modo edición).
const attributes = ref([]) // [{id,name,position,is_image_axis,values:[{id,value,swatch_hex,position}]}]
const images = ref([]) // [{id,image,alt_text,position,value}]
const variants = ref([]) // [{id,sku,barcode,cost_price,sale_price,average_cost,stock,min_stock,options_label,values:[],selected:{}}]
const inactiveVariants = ref([]) // variantes desactivadas (soft-delete) para reactivar
const showInactive = ref(false)

const loading = ref(true)
const savingGeneral = ref(false)
const creating = ref(false)
const error = ref('')
const fieldErrors = ref({})

const subcategories = computed(() => {
  const cat = categories.value.find((c) => c.id === Number(selectedCategory.value))
  return cat ? cat.subcategories.filter((s) => s.is_active) : []
})
watch(selectedCategory, (n, o) => {
  if (o !== '' && n !== o) form.value.subcategory = ''
})

const canSaveGeneral = computed(() => form.value.name.trim() && form.value.subcategory)

// Dirty-tracking: el botón "Guardar cambios" solo se habilita (y se pone verde)
// si cambió la información general O los campos de alguna variante. Lo demás
// (fotos, crear/eliminar variante) se guarda al instante.
const generalSnapshot = ref('')
const variantsSnapshot = ref({}) // id -> JSON de campos editables
function generalState() {
  return JSON.stringify({ ...form.value, category: selectedCategory.value })
}
function variantState(v) {
  return JSON.stringify({
    sku: v.sku,
    barcode: v.barcode,
    cost_price: String(v.cost_price ?? ''),
    sale_price: String(v.sale_price ?? ''),
    min_stock: v.min_stock,
    values: attributes.value.map((a) => v.selected?.[a.id] ?? null)
  })
}
function snapshotVariants() {
  const snap = {}
  for (const v of variants.value) snap[v.id] = variantState(v)
  variantsSnapshot.value = snap
}
const generalDirty = computed(() => generalState() !== generalSnapshot.value)
const dirtyVariants = computed(() =>
  variants.value.filter((v) => variantsSnapshot.value[v.id] !== variantState(v))
)
const isDirty = computed(() => generalDirty.value || dirtyVariants.value.length > 0)

// ----------------------- Atributos / valores -----------------------
const imageAxis = computed(() => attributes.value.find((a) => a.is_image_axis) || null)
// Para "agregar existente" y "crear nuevo" desde el catálogo.
const attrPick = ref('')
const newAttr = ref({ name: '', has_swatch: false })

// Atributos del catálogo que aún no usa este producto.
const availableDefinitions = computed(() => {
  const used = new Set(attributes.value.map((a) => a.definition).filter(Boolean))
  return definitions.value.filter((d) => d.is_active && !used.has(d.id))
})

// Agrega al producto un atributo (ya enlazado a su definición del catálogo).
async function attachAttribute(def) {
  const a = await productAttributesApi.create({
    product: Number(productId.value),
    definition: def.id,
    name: def.name,
    position: attributes.value.length,
    // Por defecto, el atributo con color es el eje de fotos (si no hay otro).
    is_image_axis: def.has_swatch && !imageAxis.value
  })
  a.values = []
  attributes.value.push(a)
}

async function addExistingAttribute(defId) {
  if (!defId) return
  const def = definitions.value.find((d) => d.id === defId)
  attrPick.value = ''
  if (!def) return
  try {
    await attachAttribute(def)
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo agregar el atributo.')
  }
}

async function createNewAttribute() {
  const name = newAttr.value.name.trim()
  if (!name) return
  // Si ya existe en el catálogo, lo reutilizamos en vez de duplicarlo.
  const existing = definitions.value.find((d) => d.name.toLowerCase() === name.toLowerCase())
  if (existing) {
    if (attributes.value.some((a) => a.definition === existing.id)) {
      toastError(`El producto ya usa "${existing.name}".`)
      return
    }
    newAttr.value = { name: '', has_swatch: false }
    await addExistingAttribute(existing.id)
    return
  }
  try {
    // 1) Lo creamos en el catálogo para poder reutilizarlo en otros productos.
    const def = await attributeDefinitionsApi.create({
      name,
      has_swatch: newAttr.value.has_swatch,
      position: definitions.value.length
    })
    def.options = def.options || []
    definitions.value.push(def)
    // 2) Lo agregamos a este producto.
    await attachAttribute(def)
    newAttr.value = { name: '', has_swatch: false }
  } catch (e) {
    toastError(
      e.response?.data?.errors?.name?.[0] ||
        e.response?.data?.detail ||
        'No se pudo crear el atributo.'
    )
  }
}

// Toggle mutuamente excluyente: encender uno apaga los demás (como "Producto activo").
async function toggleImageAxis(a, e) {
  const on = e.target.checked
  try {
    if (on) {
      for (const other of attributes.value) {
        if (other.id !== a.id && other.is_image_axis) {
          await productAttributesApi.update(other.id, { is_image_axis: false })
          other.is_image_axis = false
        }
      }
      await productAttributesApi.update(a.id, { is_image_axis: true })
      a.is_image_axis = true
    } else {
      await productAttributesApi.update(a.id, { is_image_axis: false })
      a.is_image_axis = false
    }
  } catch (err) {
    e.target.checked = !on // revertir el DOM si falló
    toastError(err.response?.data?.detail || 'No se pudo cambiar el eje de fotos.')
  }
}

async function removeAttribute(a) {
  const msg =
    `Se quitará "${a.name}" de este producto y de sus variantes. ` +
    (a.is_image_axis ? 'Sus fotos pasarán a "Generales". ' : '') +
    'Esto no se puede deshacer.'
  if (!(await confirmDelete(msg))) return
  try {
    await productAttributesApi.remove(a.id)
    // Las combinaciones de las variantes y las fotos cambian en el servidor.
    await refreshStructure()
    toastSuccess('Atributo quitado')
  } catch (e) {
    toastError(
      e.response?.data?.detail ||
        'No se pudo quitar: hay variantes que usan este atributo.'
    )
  }
}

// Opciones que ofrece el catálogo para este atributo (según su definición).
const libPick = ref({}) // attrId -> id elegido (temporal)
const newOptByAttr = ref({}) // attrId -> { value, hex }
function optDraft(attrId) {
  if (!newOptByAttr.value[attrId]) newOptByAttr.value[attrId] = { value: '', hex: '#4F46E5' }
  return newOptByAttr.value[attrId]
}
function libraryFor(a) {
  const def = definitions.value.find((d) => d.id === a.definition)
  return def ? def.options.filter((o) => o.is_active) : []
}
// Solo ofrece las opciones del catálogo que aún no están en este atributo.
function availableLibrary(a) {
  const used = new Set(a.values.map((v) => v.value.toLowerCase()))
  return libraryFor(a).filter((o) => !used.has(o.value.toLowerCase()))
}

async function createValue(a, value, hex) {
  value = (value || '').trim()
  if (!value) return
  if (a.values.some((v) => v.value.toLowerCase() === value.toLowerCase())) {
    toastError(`"${value}" ya está en ${a.name}.`)
    return
  }
  try {
    const v = await attributeValuesApi.create({
      attribute: a.id,
      value,
      swatch_hex: a.has_swatch ? hex || '' : '',
      position: a.values.length
    })
    a.values.push(v)
  } catch (e) {
    toastError(e.response?.data?.errors?.value?.[0] || e.response?.data?.detail || 'No se pudo agregar el valor.')
  }
}

async function pickFromLibrary(a, id) {
  if (!id) return
  const opt = libraryFor(a).find((o) => o.id === id)
  if (opt) await createValue(a, opt.value, opt.swatch_hex || '')
  libPick.value[a.id] = ''
}

// Crea una opción nueva: la guarda en el catálogo (para reusarla) y la agrega aquí.
async function createOptionInline(a) {
  const draft = optDraft(a.id)
  const value = draft.value.trim()
  if (!value) return
  if (a.definition) {
    try {
      const opt = await attributeOptionsApi.create({
        definition: a.definition,
        value,
        swatch_hex: a.has_swatch ? draft.hex : '',
        position: libraryFor(a).length
      })
      const def = definitions.value.find((d) => d.id === a.definition)
      if (def) def.options.push(opt)
    } catch (e) {
      // Si ya existía en el catálogo (409/400 por único), seguimos y la agregamos al producto.
      if (e.response?.status !== 400) {
        toastError(e.response?.data?.detail || 'No se pudo crear la opción.')
        return
      }
    }
  }
  await createValue(a, value, a.has_swatch ? draft.hex : '')
  newOptByAttr.value[a.id] = { value: '', hex: '#4F46E5' }
}

async function removeValue(a, val) {
  if (!(await confirmDelete(`Se eliminará el valor "${val.value}".`))) return
  try {
    await attributeValuesApi.remove(val.id)
    a.values = a.values.filter((v) => v.id !== val.id)
    images.value = images.value.filter((im) => im.value !== val.id)
  } catch (e) {
    toastError(
      e.response?.data?.detail || 'No se pudo eliminar: hay variantes que usan este valor.'
    )
  }
}

// ----------------------------- Fotos -----------------------------
// Grupos de galería: uno por valor del eje visual + uno "general" (sin valor).
const galleryGroups = computed(() => {
  const groups = []
  if (imageAxis.value) {
    imageAxis.value.values.forEach((val) => {
      groups.push({ key: `v${val.id}`, label: val.value, value: val.id, swatch: val.swatch_hex })
    })
  }
  groups.push({ key: 'general', label: imageAxis.value ? 'Generales' : 'Fotos del producto', value: null })
  return groups
})
function imagesForValue(valueId) {
  return images.value.filter((im) => im.value === valueId)
}
const uploadingValue = ref(null)
const MAX_IMAGES = 8

async function onPickImages(valueId, e) {
  const files = Array.from(e.target.files)
  e.target.value = ''
  const current = imagesForValue(valueId).length
  const room = MAX_IMAGES - current
  if (room <= 0) {
    toastError(`Máximo ${MAX_IMAGES} fotos por grupo.`)
    return
  }
  uploadingValue.value = valueId ?? 'general'
  try {
    for (const file of files.slice(0, room)) {
      const img = await productImagesApi.add(Number(productId.value), file, { value: valueId })
      images.value.push(img)
    }
    toastSuccess('Fotos subidas')
  } catch (err) {
    toastError(err.response?.data?.detail || 'No se pudo subir la foto.')
  } finally {
    uploadingValue.value = null
  }
}

async function removeImage(img) {
  if (!(await confirmDelete('Se eliminará esta foto.'))) return
  try {
    await productImagesApi.remove(img.id)
    images.value = images.value.filter((i) => i.id !== img.id)
  } catch (err) {
    toastError(err.response?.data?.detail || 'No se pudo eliminar.')
  }
}

// --- Orden de las fotos dentro de un grupo (la 1.ª es la principal) ---
async function persistGroupOrder(ordered) {
  ordered.forEach((img, i) => (img.position = i))
  images.value = [...images.value].sort(
    (a, b) => (a.value ?? -1) - (b.value ?? -1) || a.position - b.position
  )
  try {
    await productImagesApi.reorder(ordered.map((i) => i.id))
  } catch (err) {
    toastError(err.response?.data?.detail || 'No se pudo reordenar.')
  }
}
async function makeMain(g, img) {
  const list = imagesForValue(g.value)
  if (list[0] === img) return
  await persistGroupOrder([img, ...list.filter((x) => x !== img)])
}

const dragGroup = ref(null)
const dragIndex = ref(null)
function onImgDragStart(g, i) {
  dragGroup.value = g.key
  dragIndex.value = i
}
function onImgDragEnd() {
  dragGroup.value = null
  dragIndex.value = null
}
async function onImgDrop(g, i) {
  if (dragGroup.value !== g.key || dragIndex.value === null || dragIndex.value === i) {
    onImgDragEnd()
    return
  }
  const list = imagesForValue(g.value)
  const [moved] = list.splice(dragIndex.value, 1)
  list.splice(i, 0, moved)
  onImgDragEnd()
  await persistGroupOrder(list)
}

// ----------------------------- Variantes -----------------------------
// Variantes existentes colapsables (acordeón) para que la lista no se alargue.
const expandedVariants = ref(new Set())
function toggleVariant(id) {
  const next = new Set(expandedVariants.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expandedVariants.value = next
}

// Borrador para crear una variante (un valor por atributo + datos). El stock
// inicial se puede REPARTIR entre varias bodegas (una fila por bodega).
const newVariant = ref(null)
function startNewVariant() {
  newVariant.value = {
    selected: {}, sku: '', barcode: '', cost_price: '', sale_price: '', min_stock: 0,
    stockRows: [{ warehouse: warehouses.value[0]?.id ?? '', quantity: '' }]
  }
}
function cancelNewVariant() {
  newVariant.value = null
}
function addStockRow() {
  newVariant.value.stockRows.push({ warehouse: '', quantity: '' })
}
function removeStockRow(i) {
  newVariant.value.stockRows.splice(i, 1)
}
// Bodegas aún no usadas por OTRA fila (evita repetir bodega en el reparto).
function warehousesForRow(row) {
  const used = new Set(
    newVariant.value.stockRows.filter((r) => r !== row && r.warehouse).map((r) => r.warehouse)
  )
  return warehouses.value.filter((w) => !used.has(w.id))
}
const newVariantStockTotal = computed(() =>
  (newVariant.value?.stockRows || []).reduce((s, r) => s + (Number(r.quantity) || 0), 0)
)

const newVariantValid = computed(() => {
  const nv = newVariant.value
  if (!nv || !nv.sku.trim()) return false
  // Debe elegir un valor por cada atributo del producto.
  return attributes.value.every((a) => nv.selected[a.id])
})

async function saveNewVariant() {
  const nv = newVariant.value
  if (!newVariantValid.value) return
  const valueIds = attributes.value.map((a) => nv.selected[a.id])
  // Filas de stock con cantidad > 0; cada una necesita su bodega.
  const stockRows = (nv.stockRows || []).filter((r) => Number(r.quantity) > 0)
  if (stockRows.some((r) => !r.warehouse)) {
    toastError('Elige la bodega para cada cantidad de stock inicial.')
    return
  }
  try {
    const v = await variantsApi.create({
      product: Number(productId.value),
      sku: nv.sku.trim(),
      barcode: (nv.barcode || '').trim(),
      cost_price: nv.cost_price || 0,
      sale_price: nv.sale_price || 0,
      min_stock: nv.min_stock || 0,
      value_ids: valueIds
    })
    // Un movimiento de entrada (saldo inicial) por cada bodega del reparto.
    for (const r of stockRows) {
      await movementsApi.create({
        variant: v.id, warehouse: r.warehouse, type: 'entrada',
        reason: 'saldo_inicial', quantity: Number(r.quantity), unit_cost: nv.cost_price || 0,
        note: 'Saldo inicial al crear la variante'
      })
    }
    newVariant.value = null
    await reloadVariants()
    toastSuccess('Variante creada')
  } catch (e) {
    toastError(
      e.response?.data?.errors?.sku?.[0] ||
        e.response?.data?.errors?.value_ids?.[0] ||
        e.response?.data?.detail ||
        'No se pudo crear la variante.'
    )
  }
}

async function removeVariant(v) {
  if (!(await confirmDelete(`Se desactivará la variante ${v.sku}.`))) return
  try {
    await variantsApi.remove(v.id)
    await reloadVariants()
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo eliminar la variante.')
  }
}

async function reloadVariants() {
  const p = await productsApi.get(productId.value)
  setVariants(p.variants || [])
  snapshotVariants()
}
function setVariants(all) {
  variants.value = all.filter((v) => v.is_active).map(mapVariant)
  inactiveVariants.value = all
    .filter((v) => !v.is_active)
    .map((v) => ({ id: v.id, sku: v.sku, options_label: v.options_label }))
}
function mapVariant(v) {
  // `selected` mapea atributo->valor elegido, para poder editar la combinación.
  const selected = {}
  for (const it of v.values || []) selected[it.attribute] = it.value
  return {
    id: v.id, sku: v.sku, barcode: v.barcode || '',
    cost_price: v.cost_price, sale_price: v.sale_price, average_cost: v.average_cost,
    stock: v.stock, min_stock: v.min_stock, options_label: v.options_label,
    values: v.values || [], selected
  }
}

async function reactivateVariant(v) {
  try {
    await variantsApi.update(v.id, { is_active: true })
    await reloadVariants()
    toastSuccess('Variante reactivada')
  } catch (e) {
    toastError(
      e.response?.data?.errors?.is_active?.[0] ||
        e.response?.data?.detail ||
        'No se pudo reactivar la variante.'
    )
  }
}

// ----------------------------- Carga -----------------------------
function fillForm(p) {
  form.value = {
    name: p.name, description: p.description, subcategory: p.subcategory,
    brand: p.brand ?? '', unit_of_measure: p.unit_of_measure, tax_rate: p.tax_rate,
    expiration_date: p.expiration_date || '', is_active: p.is_active
  }
  selectedCategory.value = p.category
  isPerishable.value = Boolean(p.expiration_date)
  attributes.value = (p.attributes || []).map((a) => ({ ...a, values: [...(a.values || [])] }))
  images.value = [...(p.images || [])]
  setVariants(p.variants || [])
  generalSnapshot.value = generalState()
  snapshotVariants()
}

async function loadProduct() {
  const p = await productsApi.get(productId.value)
  fillForm(p)
}

// Refresca atributos, fotos y variantes desde el servidor SIN tocar la info
// general (preserva cambios sin guardar de los campos generales). Útil tras una
// acción estructural inmediata (quitar atributo, etc.).
async function refreshStructure() {
  const p = await productsApi.get(productId.value)
  attributes.value = (p.attributes || []).map((a) => ({ ...a, values: [...(a.values || [])] }))
  images.value = [...(p.images || [])]
  setVariants(p.variants || [])
  snapshotVariants()
}

// Guardado GENERAL: persiste la info general (si cambió) y los campos de las
// variantes editadas, todo con un solo botón.
async function saveAll() {
  if (!isDirty.value || savingGeneral.value) return
  if (generalDirty.value && !canSaveGeneral.value) {
    toastError('Completa el nombre y la subcategoría antes de guardar.')
    return
  }
  savingGeneral.value = true
  error.value = ''
  fieldErrors.value = {}
  try {
    if (generalDirty.value) {
      const payload = { ...form.value }
      payload.expiration_date = payload.expiration_date || null
      payload.brand = payload.brand || null
      await productsApi.update(productId.value, payload)
      generalSnapshot.value = generalState()
    }
    for (const v of dirtyVariants.value) {
      const payload = {
        sku: (v.sku || '').trim(),
        barcode: (v.barcode || '').trim(),
        cost_price: v.cost_price || 0,
        sale_price: v.sale_price || 0,
        min_stock: v.min_stock || 0
      }
      // Si el producto tiene atributos, guardamos también la combinación editada.
      // Filtra vacíos: si falta alguno, el backend responde "Elige un valor para
      // cada atributo del producto." en vez de un error de validación poco claro.
      if (attributes.value.length) {
        payload.value_ids = attributes.value.map((a) => v.selected[a.id]).filter(Boolean)
      }
      await variantsApi.update(v.id, payload)
    }
    // Recargamos para reflejar etiquetas (options_label) actualizadas.
    await reloadVariants()
    toastSuccess('Cambios guardados')
  } catch (e) {
    const data = e.response?.data
    error.value = data?.errors?.sku?.[0] || data?.detail || 'No se pudo guardar.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    savingGeneral.value = false
  }
}

// Descartar: revierte los cambios no guardados al último estado guardado.
async function discardChanges() {
  if (!isDirty.value) return
  const ok = await confirmAction({
    title: 'Descartar cambios',
    text: 'Se perderán los cambios de información general y variantes que no has guardado.',
    confirmText: 'Descartar',
    icon: 'warning'
  })
  if (!ok) return
  await loadProduct()
  toastSuccess('Cambios descartados')
}

async function createProduct() {
  if (!canSaveGeneral.value) return
  creating.value = true
  error.value = ''
  fieldErrors.value = {}
  try {
    const payload = { ...form.value }
    payload.expiration_date = payload.expiration_date || null
    payload.brand = payload.brand || null
    const created = await productsApi.create(payload)
    toastSuccess('Producto creado. Ahora configura sus atributos, fotos y variantes.')
    router.replace({ name: 'product-edit', params: { id: created.id } })
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || 'No se pudo crear el producto.'
    if (data?.errors) fieldErrors.value = data.errors
    toastError(error.value)
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    const [cats, brs, defs, whs] = await Promise.all([
      categoriesApi.list({ page_size: 100, is_active: true }),
      brandsApi.list({ page_size: 200, is_active: true }),
      attributeDefinitionsApi.list({ page_size: 200 }),
      warehousesApi.list({ page_size: 200, is_active: true })
    ])
    categories.value = cats.results
    brands.value = brs.results
    definitions.value = defs.results
    warehouses.value = whs.results
    if (isEdit.value) await loadProduct()
  } catch {
    error.value = 'No se pudo cargar la información.'
  } finally {
    loading.value = false
  }
})

watch(productId, async (id) => {
  if (!id) return
  loading.value = true
  try {
    await loadProduct()
  } catch {
    error.value = 'No se pudo cargar el producto.'
  } finally {
    loading.value = false
  }
})

// Aviso si intentan salir con cambios de campos sin guardar.
onBeforeRouteLeave(async () => {
  if (!isEdit.value || !isDirty.value) return true
  return await confirmAction({
    title: 'Cambios sin guardar',
    text: 'Tienes cambios sin guardar. ¿Salir de todas formas?',
    confirmText: 'Salir sin guardar',
    icon: 'warning'
  })
})
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'products' }" class="back-link">
      <ArrowLeft :size="17" /> Volver a productos
    </RouterLink>

    <header class="page__head">
      <h1 class="page__title">{{ isEdit ? 'Editar producto' : 'Nuevo producto' }}</h1>
    </header>

    <LoadingState v-if="loading" label="Cargando…" />
    <p v-if="error && !loading" class="form-alert">{{ error }}</p>

    <div v-if="!loading" class="form-main">
      <!-- General -->
      <section class="card-box">
        <h2 class="card-box__title">Información general</h2>
        <label class="field">
          <span class="field__label">Nombre *</span>
          <input v-model="form.name" class="field__input" maxlength="200" />
          <span v-if="fieldErrors.name" class="field__error">{{ fieldErrors.name[0] }}</span>
        </label>
        <label class="field">
          <span class="field__label">Descripción</span>
          <textarea v-model="form.description" class="field__input" rows="4"></textarea>
        </label>
        <div class="field-row">
          <label class="field">
            <span class="field__label">Categoría *</span>
            <SearchSelect v-model="selectedCategory" :options="categories" placeholder="Selecciona…" />
          </label>
          <label class="field">
            <span class="field__label">Subcategoría *</span>
            <SearchSelect
              v-model="form.subcategory" :options="subcategories" :disabled="!selectedCategory"
              :placeholder="selectedCategory ? 'Selecciona…' : 'Elige una categoría primero'"
            />
          </label>
        </div>
        <div class="field-row">
          <label class="field">
            <span class="field__label">Marca</span>
            <SearchSelect v-model="form.brand" :options="brands" placeholder="Sin marca" clearable />
          </label>
          <label class="field">
            <span class="field__label">Unidad de medida</span>
            <SearchSelect v-model="form.unit_of_measure" :options="unitOptions" value-key="value" label-key="label" />
          </label>
        </div>
        <div class="field-row">
          <label class="field">
            <span class="field__label">IVA</span>
            <SearchSelect v-model="form.tax_rate" :options="taxOptions" value-key="value" label-key="label" />
          </label>
          <div class="field">
            <span class="field__label">Estado</span>
            <label class="toggle"><input v-model="form.is_active" type="checkbox" /> <span>Producto activo</span></label>
          </div>
        </div>
        <div class="toggle-attr">
          <label class="toggle">
            <input v-model="isPerishable" type="checkbox" /> <span>¿Es perecedero?</span>
          </label>
          <input v-if="isPerishable" v-model="form.expiration_date" type="date" class="field__input" />
        </div>
      </section>

      <!-- Solo en edición: atributos, fotos y variantes -->
      <template v-if="isEdit">
        <!-- Atributos -->
        <section class="card-box">
          <h2 class="card-box__title">Atributos de variación</h2>
          <p class="muted-hint">
            Define cómo varía el producto (Color, Talla, Almacenamiento…). Marca UNO como
            <strong>eje de fotos</strong>: sus valores tendrán galería propia (normalmente el color).
          </p>

          <div v-for="a in attributes" :key="a.id" class="attr">
            <div class="attr__head">
              <span class="attr__name">{{ a.name }}</span>
              <label class="toggle toggle--inline" title="Las fotos se agrupan por este atributo">
                <input type="checkbox" :checked="a.is_image_axis" @change="toggleImageAxis(a, $event)" />
                <span>eje de fotos</span>
              </label>
              <button class="icon-btn icon-btn--danger" title="Eliminar atributo" @click="removeAttribute(a)">
                <Trash2 :size="14" />
              </button>
            </div>
            <div class="chips">
              <span v-for="val in a.values" :key="val.id" class="vchip">
                <span v-if="val.swatch_hex" class="vchip__dot" :style="{ background: val.swatch_hex }"></span>
                {{ val.value }}
                <button class="vchip__x" title="Quitar valor" @click="removeValue(a, val)"><X :size="12" /></button>
              </span>
            </div>
            <span v-if="a.values.length > 1" class="muted-hint">
              El orden de los valores se define en <RouterLink :to="{ name: 'attributes' }">Atributos</RouterLink> y se respeta en la tienda y el POS.
            </span>
            <div v-if="availableLibrary(a).length" class="value-lib">
              <SearchSelect
                :model-value="libPick[a.id] || ''"
                :options="availableLibrary(a)"
                value-key="id"
                label-key="value"
                :swatch-key="a.has_swatch ? 'swatch_hex' : ''"
                clearable
                placeholder="Agregar opción del catálogo…"
                @update:model-value="pickFromLibrary(a, $event)"
              />
            </div>
            <div class="value-new">
              <input
                v-if="a.has_swatch"
                v-model="optDraft(a.id).hex"
                type="color"
                class="color-input"
                title="Elegir color"
              />
              <input
                v-model="optDraft(a.id).value"
                class="field__input field__input--sm"
                :placeholder="a.has_swatch ? 'Crear color nuevo (Rojo…)' : 'Crear opción nueva (256GB, M…)'"
                maxlength="80"
                @keyup.enter="createOptionInline(a)"
              />
              <button class="btn btn--ghost btn--sm" :disabled="!optDraft(a.id).value.trim()" @click="createOptionInline(a)">
                <Plus :size="14" /> Opción
              </button>
            </div>
          </div>

          <div class="attr-new">
            <SearchSelect
              v-if="availableDefinitions.length"
              :model-value="attrPick"
              :options="availableDefinitions"
              value-key="id"
              label-key="name"
              clearable
              placeholder="Agregar atributo del catálogo…"
              @update:model-value="addExistingAttribute"
            />
            <div class="attr-new__create">
              <input
                v-model="newAttr.name"
                class="field__input field__input--sm"
                placeholder="…o crea uno nuevo (RAM, Material…)"
                maxlength="60"
                @keyup.enter="createNewAttribute"
              />
              <label class="toggle toggle--inline" title="Sus opciones llevan un color">
                <input v-model="newAttr.has_swatch" type="checkbox" /> <span>usa color</span>
              </label>
              <button class="btn btn--ghost btn--sm" :disabled="!newAttr.name.trim()" @click="createNewAttribute">
                <Plus :size="14" /> Crear
              </button>
            </div>
          </div>
          <p class="attr-link-note">
            Atributos y opciones se guardan en el
            <RouterLink :to="{ name: 'attributes' }">catálogo de Atributos</RouterLink>
            para reutilizarlos en otros productos.
          </p>
        </section>

        <!-- Fotos -->
        <section class="card-box">
          <h2 class="card-box__title">Fotos</h2>
          <p class="muted-hint">
            Las fotos se agrupan por {{ imageAxis ? `valor de "${imageAxis.name}"` : 'producto' }}.
            Así, al agregar otra talla del mismo color no hay que volver a subirlas.
          </p>
          <div v-for="g in galleryGroups" :key="g.key" class="photo-group">
            <div class="photo-group__head">
              <span v-if="g.swatch" class="vchip__dot" :style="{ background: g.swatch }"></span>
              <strong>{{ g.label }}</strong>
            </div>
            <div class="gallery">
              <div
                v-for="(img, gi) in imagesForValue(g.value)"
                :key="img.id"
                class="gallery__item"
                :class="{
                  'gallery__item--main': gi === 0,
                  'gallery__item--drag': dragGroup === g.key && dragIndex === gi
                }"
                draggable="true"
                @dragstart="onImgDragStart(g, gi)"
                @dragover.prevent
                @drop.prevent="onImgDrop(g, gi)"
                @dragend="onImgDragEnd"
              >
                <img :src="img.image" :alt="img.alt_text || 'Foto'" draggable="false" />
                <span v-if="gi === 0" class="gallery__badge">Principal</span>
                <div class="gallery__actions">
                  <button v-if="gi !== 0" class="gallery__btn" title="Hacer principal" @click="makeMain(g, img)">
                    <Star :size="13" />
                  </button>
                  <button class="gallery__btn gallery__btn--danger" title="Quitar" @click="removeImage(img)">
                    <X :size="13" />
                  </button>
                </div>
              </div>
              <label v-if="imagesForValue(g.value).length < MAX_IMAGES" class="gallery__add">
                <ImagePlus :size="20" />
                <span>{{ uploadingValue === (g.value ?? 'general') ? 'Subiendo…' : 'Agregar' }}</span>
                <input type="file" accept="image/*" multiple hidden @change="onPickImages(g.value, $event)" />
              </label>
            </div>
            <span class="muted-hint">Arrastra para ordenar; la 1.ª es la principal (o usa ★).</span>
          </div>
        </section>

        <!-- Variantes -->
        <section class="card-box">
          <div class="variants-head">
            <h2 class="card-box__title">Variantes <span class="muted">({{ variants.length }})</span></h2>
            <button v-if="!newVariant" class="btn btn--ghost btn--sm" @click="startNewVariant">
              <Plus :size="16" /> Agregar variante
            </button>
          </div>

          <!-- Nueva variante -->
          <div v-if="newVariant" class="variant variant--new">
            <div class="variant__body">
              <div class="field-row">
                <label v-for="a in attributes" :key="a.id" class="field">
                  <span class="field__label">{{ a.name }} *</span>
                  <SearchSelect
                    v-model="newVariant.selected[a.id]"
                    :options="a.values" value-key="id" label-key="value"
                    :swatch-key="a.has_swatch ? 'swatch_hex' : ''"
                    clearable clear-label="Sin elegir"
                    placeholder="Elige…"
                  />
                </label>
              </div>
              <div class="field-row">
                <label class="field"><span class="field__label">SKU *</span><input v-model="newVariant.sku" class="field__input" maxlength="64" /></label>
                <label class="field"><span class="field__label">Código de barras</span><input v-model="newVariant.barcode" class="field__input" maxlength="14" /></label>
              </div>
              <div class="field-row">
                <label class="field"><span class="field__label">Costo de referencia</span><MoneyInput v-model="newVariant.cost_price" /></label>
                <label class="field"><span class="field__label">Precio de venta</span><MoneyInput v-model="newVariant.sale_price" /></label>
              </div>
              <div class="field-row">
                <label class="field"><span class="field__label">Stock mínimo</span><input v-model.number="newVariant.min_stock" type="number" min="0" class="field__input" /></label>
                <div class="field"></div>
              </div>
              <div class="field">
                <span class="field__label">Stock inicial por bodega</span>
                <div v-for="(row, i) in newVariant.stockRows" :key="i" class="stock-row">
                  <SearchSelect
                    v-model="row.warehouse"
                    :options="warehousesForRow(row)"
                    :placeholder="warehouses.length ? 'Bodega' : 'No hay bodegas'"
                  />
                  <input v-model.number="row.quantity" type="number" min="0" class="field__input" placeholder="Cant." />
                  <button v-if="newVariant.stockRows.length > 1" type="button" class="icon-btn icon-btn--danger" title="Quitar" @click="removeStockRow(i)">
                    <X :size="14" />
                  </button>
                </div>
                <div class="stock-foot">
                  <button
                    v-if="newVariant.stockRows.length < warehouses.length"
                    type="button"
                    class="btn btn--ghost btn--sm"
                    @click="addStockRow"
                  >
                    <Plus :size="14" /> Otra bodega
                  </button>
                  <span class="muted-hint">
                    Total inicial: <strong>{{ newVariantStockTotal }}</strong> unidad(es). Déjalo en 0 si aún no quieres stock.
                  </span>
                </div>
              </div>
              <div class="variant__actions">
                <button class="btn btn--ghost btn--sm" @click="cancelNewVariant">Cancelar</button>
                <button class="btn btn--primary btn--sm" :disabled="!newVariantValid" @click="saveNewVariant">Crear variante</button>
              </div>
            </div>
          </div>

          <!-- Variantes existentes (colapsables) -->
          <div v-for="v in variants" :key="v.id" class="variant">
            <div class="variant__head" @click="toggleVariant(v.id)">
              <ChevronDown :size="18" class="variant__chevron" :class="{ open: expandedVariants.has(v.id) }" />
              <span class="variant__attrs">{{ v.options_label || 'Estándar' }}</span>
              <span v-if="variantsSnapshot[v.id] !== variantState(v)" class="dirty-chip">sin guardar</span>
              <code class="variant__sku">{{ v.sku }}</code>
              <span class="muted variant__stock">stock {{ v.stock }}</span>
              <button class="icon-btn icon-btn--danger" title="Eliminar" @click.stop="removeVariant(v)"><Trash2 :size="14" /></button>
            </div>
            <div v-if="expandedVariants.has(v.id)" class="variant__body">
              <div v-if="attributes.length" class="field-row">
                <label v-for="a in attributes" :key="a.id" class="field">
                  <span class="field__label">{{ a.name }} *</span>
                  <SearchSelect
                    v-model="v.selected[a.id]"
                    :options="a.values" value-key="id" label-key="value"
                    :swatch-key="a.has_swatch ? 'swatch_hex' : ''"
                    clearable clear-label="Sin elegir"
                    placeholder="Elige…"
                  />
                </label>
              </div>
              <div class="field-row">
                <label class="field"><span class="field__label">SKU *</span><input v-model="v.sku" class="field__input" maxlength="64" /></label>
                <label class="field"><span class="field__label">Código de barras</span><input v-model="v.barcode" class="field__input" maxlength="14" /></label>
              </div>
              <div class="field-row">
                <label class="field">
                  <span class="field__label">Costo de referencia</span>
                  <MoneyInput v-model="v.cost_price" />
                  <span class="muted-hint">Promedio real: <strong>{{ money(v.average_cost) }}</strong></span>
                </label>
                <label class="field"><span class="field__label">Precio de venta</span><MoneyInput v-model="v.sale_price" /></label>
              </div>
              <div class="field-row">
                <label class="field">
                  <span class="field__label">Stock mínimo</span>
                  <input v-model.number="v.min_stock" type="number" min="0" class="field__input" />
                  <span class="muted-hint">El stock ({{ v.stock }}) se ajusta en Movimientos.</span>
                </label>
                <div class="field"></div>
              </div>
            </div>
          </div>
          <p v-if="!variants.length" class="muted empty-variants">Sin variantes activas.</p>

          <!-- Variantes desactivadas (soft-delete): se pueden reactivar. -->
          <div v-if="inactiveVariants.length" class="inactive">
            <button type="button" class="inactive__toggle" @click="showInactive = !showInactive">
              {{ showInactive ? 'Ocultar' : 'Ver' }} variantes desactivadas ({{ inactiveVariants.length }})
            </button>
            <div v-if="showInactive" class="inactive__list">
              <div v-for="v in inactiveVariants" :key="v.id" class="inactive__row">
                <span class="inactive__attrs">{{ v.options_label || 'Estándar' }}</span>
                <span class="muted">{{ v.sku }}</span>
                <button class="btn btn--ghost btn--sm" @click="reactivateVariant(v)">
                  <RotateCcw :size="14" /> Reactivar
                </button>
              </div>
            </div>
          </div>
        </section>
      </template>

      <!-- Barra de acción general: guardar la información general del producto. -->
      <div class="form-actions">
        <template v-if="!isEdit">
          <p class="muted-hint">Primero crea el producto; luego configuras atributos, fotos y variantes.</p>
          <button class="btn btn--primary" :disabled="creating || !canSaveGeneral" @click="createProduct">
            {{ creating ? 'Creando…' : 'Crear y continuar' }}
          </button>
        </template>
        <template v-else>
          <span class="form-actions__note">
            {{ isDirty ? 'Tienes cambios sin guardar.' : 'Todo guardado.' }}
          </span>
          <button class="btn btn--ghost" :disabled="savingGeneral || !isDirty" @click="discardChanges">
            Descartar
          </button>
          <button class="btn btn--primary" :disabled="savingGeneral || !isDirty" @click="saveAll">
            {{ savingGeneral ? 'Guardando…' : 'Guardar cambios' }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-muted);
  margin-bottom: 14px;
}
.back-link:hover {
  color: var(--color-primary);
}
.page__head {
  margin-bottom: 22px;
}
.page__title {
  font-size: 1.6rem;
}
.form-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-box__title {
  font-size: 1rem;
  color: var(--color-ink);
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
}
.field__input {
  width: 100%;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input--sm {
  padding: 9px 12px;
  font-size: 0.9rem;
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field__error {
  font-size: 0.8rem;
  color: #ef4444;
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-ink);
}
.toggle input {
  appearance: none;
  -webkit-appearance: none;
  position: relative;
  flex-shrink: 0;
  width: 38px;
  height: 22px;
  border-radius: var(--radius-full);
  background: var(--color-line);
  cursor: pointer;
  transition: background 0.18s ease;
}
.toggle input:checked {
  background: var(--color-primary);
}
.toggle input::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s ease;
}
.toggle input:checked::after {
  transform: translateX(16px);
}
.toggle--inline {
  font-size: 0.86rem;
  white-space: nowrap;
}
.toggle-attr {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form-actions {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  flex-wrap: wrap;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: 0 -2px 10px rgba(15, 23, 42, 0.05);
}
.form-actions .muted-hint {
  margin-right: auto;
}
.form-actions__note {
  margin-right: auto;
  font-size: 0.85rem;
  color: var(--color-muted);
}
.dirty-chip {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: #fef3c7;
  color: #92400e;
}
.muted-hint {
  font-size: 0.82rem;
  color: var(--color-muted);
}
.muted {
  font-weight: 400;
  color: var(--color-muted);
}

/* Atributos */
.attr {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.attr__head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.attr__name {
  font-weight: 600;
  color: var(--color-ink);
  flex: 1;
}
.attr__axis {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--color-muted);
  cursor: pointer;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.vchip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
  font-size: 0.85rem;
}
.vchip__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.12);
}
.vchip__x {
  display: inline-flex;
  color: var(--color-muted);
}
.vchip__x:hover {
  color: #dc2626;
}
.value-new {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.value-new .field__input {
  flex: 1;
  min-width: 160px;
}
.color-input {
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  padding: 2px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
  cursor: pointer;
}
.attr-new {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px dashed var(--color-line);
  padding-top: 14px;
}
.attr-new__create {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.attr-new__create .field__input {
  flex: 1;
  min-width: 160px;
}
.attr-link-note {
  font-size: 0.82rem;
  color: var(--color-muted);
}
.attr-link-note a {
  color: var(--color-primary);
  font-weight: 500;
}

/* Fotos */
.photo-group {
  border-top: 1px solid var(--color-surface-alt);
  padding-top: 12px;
}
.photo-group__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.9rem;
}
.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
}
.gallery__item {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 2px solid transparent;
  cursor: grab;
}
.gallery__item:active {
  cursor: grabbing;
}
.gallery__item--main {
  border-color: var(--color-amber);
}
.gallery__item--drag {
  opacity: 0.4;
}
.gallery__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gallery__actions {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  gap: 4px;
}
.gallery__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.65);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease;
}
.gallery__btn:hover {
  background: var(--color-primary);
}
.gallery__btn--danger:hover {
  background: #dc2626;
}
.gallery__badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.64rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #fff;
  background: var(--color-amber);
  padding: 2px 0;
}
.value-lib {
  max-width: 360px;
}
.gallery__add {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  aspect-ratio: 1;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  font-size: 0.78rem;
  cursor: pointer;
}
.gallery__add:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Variantes */
.variants-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.btn--ghost {
  background: var(--color-surface-alt);
  color: var(--color-ink);
}
.btn--ghost:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.btn--sm {
  padding: 7px 12px;
  font-size: 0.84rem;
  gap: 5px;
}
.variant {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: #fff;
}
.variant__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  user-select: none;
}
.variant__head:hover {
  background: var(--color-surface-alt);
}
.variant__chevron {
  color: var(--color-muted);
  transition: transform 0.18s ease;
  flex-shrink: 0;
}
.variant__chevron.open {
  transform: rotate(180deg);
}
.variant__sku {
  font-size: 0.78rem;
  color: var(--color-muted);
}
.variant__stock {
  font-size: 0.82rem;
  white-space: nowrap;
}
.variant__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 14px 14px;
  border-top: 1px solid var(--color-surface-alt);
}
.variant--new {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.variant--new .variant__body {
  border-top: none;
  padding-top: 14px;
}
.variant__title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.variant__attrs {
  font-weight: 600;
  color: var(--color-ink);
  flex: 1;
}
.stock-row {
  display: grid;
  grid-template-columns: 1fr 120px auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.stock-foot {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.variant__actions,
.variant__save {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 10px;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  border: 1px solid var(--color-line);
  background: #fff;
}
.icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fca5a5;
  background: #fef2f2;
}
.empty-variants {
  text-align: center;
  padding: 16px;
  font-size: 0.88rem;
}
.inactive {
  margin-top: 6px;
  border-top: 1px dashed var(--color-line);
  padding-top: 12px;
}
.inactive__toggle {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}
.inactive__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}
.inactive__row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}
.inactive__attrs {
  flex: 1;
  font-weight: 600;
  color: var(--color-ink);
}
.form-alert {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  margin-bottom: 16px;
}
</style>
