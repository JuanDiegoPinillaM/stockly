<script setup>
import { ref, watch } from 'vue'

/**
 * Campo de moneda en pesos colombianos. Muestra "$" y separadores de miles
 * (p. ej. $1.250.000) mientras se escribe, pero emite un número limpio.
 * COP se maneja sin centavos (números enteros).
 */
const props = defineProps({
  modelValue: { type: [Number, String], default: '' },
  placeholder: { type: String, default: '0' }
})
const emit = defineEmits(['update:modelValue'])

const formatter = new Intl.NumberFormat('es-CO')
const display = ref('')

function format(value) {
  if (value === '' || value === null || value === undefined) return ''
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  return formatter.format(Math.trunc(Math.abs(n)))
}

// Sincroniza con cambios externos (carga del producto, reset…) sin reformatear
// mientras el usuario teclea el mismo valor.
watch(
  () => props.modelValue,
  (v) => {
    const currentDigits = display.value.replace(/\D/g, '')
    const incoming = v === '' || v === null || v === undefined ? '' : String(Math.trunc(Math.abs(Number(v))))
    if (incoming !== currentDigits) display.value = format(v)
  },
  { immediate: true }
)

function onInput(e) {
  const digits = e.target.value.replace(/\D/g, '')
  if (digits === '') {
    display.value = ''
    emit('update:modelValue', '')
    return
  }
  const n = parseInt(digits, 10)
  display.value = formatter.format(n)
  emit('update:modelValue', n)
}
</script>

<template>
  <div class="money">
    <span class="money__symbol">$</span>
    <input
      class="money__input"
      type="text"
      inputmode="numeric"
      :value="display"
      :placeholder="placeholder"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
.money {
  display: flex;
  align-items: center;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.money:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.money__symbol {
  padding: 0 4px 0 13px;
  color: var(--color-muted);
  font-weight: 600;
}
.money__input {
  flex: 1;
  width: 100%;
  padding: 11px 13px 11px 4px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: transparent;
  border: none;
}
.money__input:focus {
  outline: none;
}
</style>
