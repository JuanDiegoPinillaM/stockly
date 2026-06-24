<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { ChevronDown, Search, Check, X } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: [Number, String], default: '' },
  options: { type: Array, default: () => [] },
  valueKey: { type: String, default: 'id' },
  labelKey: { type: String, default: 'name' },
  // Si se indica, muestra un cuadrito de color usando ese campo (p. ej. 'hex_code').
  swatchKey: { type: String, default: '' },
  placeholder: { type: String, default: 'Selecciona…' },
  clearable: { type: Boolean, default: false },
  clearLabel: { type: String, default: 'Sin selección' },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const search = ref('')
const root = ref(null)
const searchInput = ref(null)

const selected = computed(
  () => props.options.find((o) => o[props.valueKey] === props.modelValue) || null
)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => String(o[props.labelKey]).toLowerCase().includes(q))
})

function isSelected(option) {
  return option[props.valueKey] === props.modelValue
}

async function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    search.value = ''
    await nextTick()
    searchInput.value?.focus()
  }
}

function choose(value) {
  emit('update:modelValue', value)
  open.value = false
}

function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="ss" :class="{ 'ss--disabled': disabled }">
    <button type="button" class="ss__trigger" :disabled="disabled" @click="toggle">
      <span v-if="selected" class="ss__current">
        <span
          v-if="swatchKey"
          class="ss__dot"
          :style="{ background: selected[swatchKey] }"
        ></span>
        {{ selected[labelKey] }}
      </span>
      <span v-else class="ss__placeholder">{{ placeholder }}</span>
      <ChevronDown :size="16" class="ss__chevron" :class="{ open }" />
    </button>

    <div v-if="open" class="ss__panel">
      <div class="ss__search">
        <Search :size="15" class="ss__search-icon" />
        <input
          ref="searchInput"
          v-model="search"
          class="ss__search-input"
          type="text"
          placeholder="Buscar…"
          @keydown.esc="open = false"
        />
      </div>

      <ul class="ss__list">
        <li v-if="clearable">
          <button
            type="button"
            class="ss__option"
            :class="{ active: modelValue === '' || modelValue === null }"
            @click="choose('')"
          >
            <span v-if="swatchKey" class="ss__dot ss__dot--none"><X :size="11" /></span>
            <span class="ss__option-name ss__option-name--muted">{{ clearLabel }}</span>
            <Check v-if="modelValue === '' || modelValue === null" :size="15" class="ss__check" />
          </button>
        </li>
        <li v-for="o in filtered" :key="o[valueKey]">
          <button
            type="button"
            class="ss__option"
            :class="{ active: isSelected(o) }"
            @click="choose(o[valueKey])"
          >
            <span
              v-if="swatchKey"
              class="ss__dot"
              :style="{ background: o[swatchKey] }"
            ></span>
            <span class="ss__option-name">{{ o[labelKey] }}</span>
            <span v-if="swatchKey" class="ss__hex">{{ o[swatchKey] }}</span>
            <Check v-if="isSelected(o)" :size="15" class="ss__check" />
          </button>
        </li>
        <li v-if="!filtered.length" class="ss__empty">Sin resultados</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.ss {
  position: relative;
}
.ss__trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.ss__trigger:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.ss--disabled .ss__trigger {
  background: var(--color-surface-alt);
  color: var(--color-muted);
  cursor: default;
}
.ss__current {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.ss__current,
.ss__placeholder {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ss__placeholder {
  color: var(--color-muted);
}
.ss__chevron {
  color: var(--color-muted);
  transition: transform 0.18s ease;
  flex-shrink: 0;
}
.ss__chevron.open {
  transform: rotate(180deg);
}

.ss__dot {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid var(--color-line);
  flex-shrink: 0;
}
.ss__dot--none {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-muted);
  background: var(--color-surface-alt);
}

.ss__panel {
  position: absolute;
  z-index: 50;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  overflow: hidden;
}
.ss__search {
  position: relative;
  padding: 8px;
  border-bottom: 1px solid var(--color-line);
}
.ss__search-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}
.ss__search-input {
  width: 100%;
  padding: 8px 10px 8px 32px;
  font-family: inherit;
  font-size: 0.9rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.ss__search-input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.ss__list {
  max-height: 240px;
  overflow-y: auto;
  padding: 6px;
}
.ss__option {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.92rem;
  color: var(--color-ink);
  cursor: pointer;
  transition: background 0.14s ease;
}
.ss__option:hover {
  background: var(--color-surface-alt);
}
.ss__option.active {
  background: var(--color-primary-soft);
}
.ss__option-name {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ss__option-name--muted {
  color: var(--color-muted);
}
.ss__hex {
  font-size: 0.74rem;
  color: var(--color-muted);
}
.ss__check {
  color: var(--color-primary);
  flex-shrink: 0;
}
.ss__empty {
  padding: 14px 10px;
  text-align: center;
  font-size: 0.88rem;
  color: var(--color-muted);
}
</style>
