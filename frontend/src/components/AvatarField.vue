<script setup>
import { ref, reactive, computed, onUnmounted } from 'vue'
import { Camera, Eye, Pencil, Trash2, X, ZoomIn, ZoomOut, RefreshCw } from 'lucide-vue-next'

const props = defineProps({
  src: { type: String, default: '' },
  name: { type: String, default: '' },
  size: { type: Number, default: 96 },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['save', 'remove'])

const VIEW = 260 // lado del recuadro de recorte (px)
const OUT = 512 // lado de la imagen exportada (px)

const initial = computed(() => (props.name || '?').charAt(0).toUpperCase())

const menu = ref(false)
const viewer = ref(false)
const editor = ref(false)

const fileInput = ref(null)
const imgEl = ref(null)
const imgSrc = ref('') // imagen en edición (objectURL nuevo o avatar actual)
const isObjectUrl = ref(false)
const zoom = ref(1)
const offset = reactive({ x: 0, y: 0 })
const natural = reactive({ w: 0, h: 0 })

// Convierte una URL absoluta de /media a ruta relativa (mismo origen → canvas
// sin contaminar al exportar). Si no es de media, la deja igual.
function localMedia(url) {
  if (!url) return ''
  const i = url.indexOf('/media/')
  return i >= 0 ? url.slice(i) : url
}

function baseScale() {
  if (!natural.w || !natural.h) return 1
  return Math.max(VIEW / natural.w, VIEW / natural.h)
}
const dw = computed(() => natural.w * baseScale() * zoom.value)
const dh = computed(() => natural.h * baseScale() * zoom.value)

function clamp() {
  const maxX = Math.max(0, (dw.value - VIEW) / 2)
  const maxY = Math.max(0, (dh.value - VIEW) / 2)
  offset.x = Math.min(maxX, Math.max(-maxX, offset.x))
  offset.y = Math.min(maxY, Math.max(-maxY, offset.y))
}

const imgStyle = computed(() => ({
  width: `${dw.value}px`,
  height: `${dh.value}px`,
  left: `${VIEW / 2 - dw.value / 2 + offset.x}px`,
  top: `${VIEW / 2 - dh.value / 2 + offset.y}px`
}))

function onImgLoad() {
  natural.w = imgEl.value?.naturalWidth || 0
  natural.h = imgEl.value?.naturalHeight || 0
  clamp()
}

// --- Menú al hacer clic en la foto ---
function openMenu() {
  if (props.src) menu.value = !menu.value
  else startEdit() // sin foto: directo al editor
}
function onDocClick(e) {
  if (!e.target.closest?.('.af')) menu.value = false
}
document.addEventListener('click', onDocClick)
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  if (isObjectUrl.value && imgSrc.value) URL.revokeObjectURL(imgSrc.value)
})

function view() {
  menu.value = false
  viewer.value = true
}

function startEdit() {
  menu.value = false
  resetEdit()
  if (props.src) {
    imgSrc.value = localMedia(props.src)
    isObjectUrl.value = false
  }
  editor.value = true
}

function resetEdit() {
  if (isObjectUrl.value && imgSrc.value) URL.revokeObjectURL(imgSrc.value)
  imgSrc.value = ''
  isObjectUrl.value = false
  zoom.value = 1
  offset.x = 0
  offset.y = 0
  natural.w = 0
  natural.h = 0
}

function pick() {
  fileInput.value?.click()
}
function onFile(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  if (isObjectUrl.value && imgSrc.value) URL.revokeObjectURL(imgSrc.value)
  imgSrc.value = URL.createObjectURL(file)
  isObjectUrl.value = true
  zoom.value = 1
  offset.x = 0
  offset.y = 0
  if (!editor.value) editor.value = true
}

// --- Arrastrar para reposicionar ---
const drag = reactive({ active: false, sx: 0, sy: 0, ox: 0, oy: 0 })
function onPointerDown(e) {
  if (!imgSrc.value) return
  drag.active = true
  drag.sx = e.clientX
  drag.sy = e.clientY
  drag.ox = offset.x
  drag.oy = offset.y
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}
function onPointerMove(e) {
  if (!drag.active) return
  offset.x = drag.ox + (e.clientX - drag.sx)
  offset.y = drag.oy + (e.clientY - drag.sy)
  clamp()
}
function onPointerUp() {
  drag.active = false
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
}
function onZoom() {
  clamp()
}

function cancel() {
  editor.value = false
  resetEdit()
}

function remove() {
  emit('remove')
  editor.value = false
  resetEdit()
}

function save() {
  const img = imgEl.value
  if (!img || !natural.w) return
  const ratio = natural.w / dw.value // px de origen por px de recuadro
  const imageLeft = VIEW / 2 - dw.value / 2 + offset.x
  const imageTop = VIEW / 2 - dh.value / 2 + offset.y
  const sSize = VIEW * ratio
  let sx = -imageLeft * ratio
  let sy = -imageTop * ratio
  sx = Math.min(Math.max(0, sx), Math.max(0, natural.w - sSize))
  sy = Math.min(Math.max(0, sy), Math.max(0, natural.h - sSize))

  const canvas = document.createElement('canvas')
  canvas.width = OUT
  canvas.height = OUT
  const ctx = canvas.getContext('2d')
  try {
    ctx.drawImage(img, sx, sy, sSize, sSize, 0, 0, OUT, OUT)
    canvas.toBlob(
      (blob) => {
        if (blob) emit('save', blob)
        editor.value = false
        resetEdit()
      },
      'image/jpeg',
      0.9
    )
  } catch {
    // Por seguridad ante imágenes de otro origen no recortables.
    editor.value = false
    resetEdit()
  }
}
</script>

<template>
  <div class="af">
    <button
      type="button"
      class="af__avatar"
      :style="{ width: `${size}px`, height: `${size}px` }"
      :title="src ? 'Ver o editar foto' : 'Subir foto'"
      @click.stop="openMenu"
    >
      <img v-if="src" :src="src" alt="Foto de perfil" />
      <span v-else class="af__initial">{{ initial }}</span>
      <span class="af__overlay"><Camera :size="size > 80 ? 20 : 16" /></span>
    </button>

    <!-- Menú: ver / editar -->
    <transition name="af-pop">
      <div v-if="menu" class="af__menu" @click.stop>
        <button v-if="src" @click="view"><Eye :size="16" /> Ver foto</button>
        <button @click="startEdit"><Pencil :size="16" /> Editar foto</button>
      </div>
    </transition>

    <!-- Visor -->
    <Teleport to="body">
      <transition name="af-fade">
        <div v-if="viewer" class="af__lightbox" @click.self="viewer = false">
          <button class="af__close" @click="viewer = false"><X :size="22" /></button>
          <img :src="src" alt="Foto de perfil" />
        </div>
      </transition>
    </Teleport>

    <!-- Editor -->
    <Teleport to="body">
      <transition name="af-fade">
        <div v-if="editor" class="af__modal" @click.self="cancel">
          <div class="af__dialog">
            <div class="af__dialog-head">
              <h3>Editar foto de perfil</h3>
              <button class="af__close af__close--dark" @click="cancel"><X :size="20" /></button>
            </div>

            <template v-if="imgSrc">
              <div
                class="cropper"
                :style="{ width: `${VIEW}px`, height: `${VIEW}px` }"
                @pointerdown="onPointerDown"
              >
                <img
                  ref="imgEl"
                  :src="imgSrc"
                  :style="imgStyle"
                  class="cropper__img"
                  crossorigin="anonymous"
                  draggable="false"
                  @load="onImgLoad"
                />
                <div class="cropper__mask"></div>
              </div>
              <p class="cropper__hint">Arrastra para reubicar · usa el control para acercar</p>
              <div class="zoom">
                <ZoomOut :size="18" />
                <input v-model.number="zoom" type="range" min="1" max="3" step="0.01" @input="onZoom" />
                <ZoomIn :size="18" />
              </div>
            </template>

            <button v-else type="button" class="cropper-empty" @click="pick">
              <Camera :size="26" />
              <span>Seleccionar una foto</span>
            </button>

            <div class="af__actions">
              <button type="button" class="af__btn" @click="pick">
                <RefreshCw :size="16" /> Cambiar
              </button>
              <button v-if="src" type="button" class="af__btn af__btn--danger" @click="remove">
                <Trash2 :size="16" /> Eliminar
              </button>
              <span class="af__spacer"></span>
              <button type="button" class="af__btn" @click="cancel">Cancelar</button>
              <button
                type="button"
                class="af__btn af__btn--primary"
                :disabled="!imgSrc || busy"
                @click="save"
              >
                {{ busy ? 'Guardando…' : 'Guardar' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
  </div>
</template>

<style scoped>
.af {
  position: relative;
  display: inline-block;
}
.af__avatar {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--color-line);
}
.af__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.af__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: rgba(15, 23, 42, 0.45);
  opacity: 0;
  transition: opacity 0.16s ease;
}
.af__avatar:hover .af__overlay {
  opacity: 1;
}

.af__menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 30;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.16);
  padding: 6px;
  min-width: 160px;
}
.af__menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  font-size: 0.9rem;
  color: var(--color-ink);
  border-radius: var(--radius-sm);
}
.af__menu button:hover {
  background: var(--color-surface-alt);
  color: var(--color-primary);
}

/* Visor */
.af__lightbox {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(14, 26, 20, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.af__lightbox img {
  max-width: min(86vw, 560px);
  max-height: 82vh;
  border-radius: var(--radius-md);
  object-fit: contain;
}
.af__close {
  position: absolute;
  top: 20px;
  right: 22px;
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}
.af__close:hover {
  background: rgba(255, 255, 255, 0.26);
}

/* Editor */
.af__modal {
  position: fixed;
  inset: 0;
  z-index: 210;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.af__dialog {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 22px;
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.af__dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.af__dialog-head h3 {
  font-size: 1.05rem;
}
.af__close--dark {
  position: static;
  width: 32px;
  height: 32px;
  background: var(--color-surface-alt);
  color: var(--color-muted);
}
.af__close--dark:hover {
  background: var(--color-line);
  color: var(--color-ink);
}

.cropper {
  position: relative;
  margin: 0 auto;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: #0f172a;
  touch-action: none;
  cursor: grab;
}
.cropper:active {
  cursor: grabbing;
}
.cropper__img {
  position: absolute;
  user-select: none;
  -webkit-user-drag: none;
  max-width: none;
}
.cropper__mask {
  position: absolute;
  inset: 0;
  pointer-events: none;
  box-shadow: 0 0 0 999px rgba(15, 23, 42, 0.5);
  border-radius: 50%;
}
.cropper__hint {
  text-align: center;
  font-size: 0.8rem;
  color: var(--color-muted);
}
.zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-muted);
}
.zoom input {
  flex: 1;
  accent-color: var(--color-primary);
}

.cropper-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 200px;
  border: 1.5px dashed var(--color-line);
  border-radius: var(--radius-md);
  color: var(--color-muted);
  font-size: 0.9rem;
}
.cropper-empty:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.af__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.af__spacer {
  flex: 1;
}
.af__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  font-size: 0.88rem;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-line);
  background: #fff;
  color: var(--color-ink);
  cursor: pointer;
  transition: all 0.15s ease;
}
.af__btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.af__btn--danger:hover {
  border-color: #fca5a5;
  color: #dc2626;
  background: #fef2f2;
}
.af__btn--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.af__btn--primary:hover {
  filter: brightness(1.05);
  color: #fff;
}
.af__btn--primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.af-pop-enter-active,
.af-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.af-pop-enter-from,
.af-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.af-fade-enter-active,
.af-fade-leave-active {
  transition: opacity 0.18s ease;
}
.af-fade-enter-from,
.af-fade-leave-to {
  opacity: 0;
}
</style>
