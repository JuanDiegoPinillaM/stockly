<script setup>
import { computed } from 'vue'

/**
 * Slider de rango de precio con dos controles (mín/máx) sobre una misma barra.
 * Usa v-model:lo y v-model:hi (vacío '' = sin límite, cae a los topes min/max).
 */
const props = defineProps({
  min: { type: Number, default: 0 },
  max: { type: Number, default: 0 }
})
const lo = defineModel('lo', { type: [Number, String], default: '' })
const hi = defineModel('hi', { type: [Number, String], default: '' })

const loNum = computed(() => (lo.value === '' || lo.value == null ? props.min : Number(lo.value)))
const hiNum = computed(() => (hi.value === '' || hi.value == null ? props.max : Number(hi.value)))

const step = computed(() => Math.max(1, Math.round((props.max - props.min) / 100)))

const fillStyle = computed(() => {
  const span = props.max - props.min || 1
  const left = ((loNum.value - props.min) / span) * 100
  const right = ((props.max - hiNum.value) / span) * 100
  return { left: `${Math.max(0, left)}%`, right: `${Math.max(0, right)}%` }
})

function setLo(e) {
  let v = Number(e.target.value)
  if (v > hiNum.value) v = hiNum.value
  lo.value = v <= props.min ? '' : v
}
function setHi(e) {
  let v = Number(e.target.value)
  if (v < loNum.value) v = loNum.value
  hi.value = v >= props.max ? '' : v
}
</script>

<template>
  <div class="rng">
    <div class="rng__track"></div>
    <div class="rng__fill" :style="fillStyle"></div>
    <input
      class="rng__input"
      type="range"
      :min="min"
      :max="max"
      :step="step"
      :value="loNum"
      aria-label="Precio mínimo"
      @input="setLo"
    />
    <input
      class="rng__input"
      type="range"
      :min="min"
      :max="max"
      :step="step"
      :value="hiNum"
      aria-label="Precio máximo"
      @input="setHi"
    />
  </div>
</template>

<style scoped>
.rng {
  position: relative;
  height: 28px;
}
.rng__track,
.rng__fill {
  position: absolute;
  top: 50%;
  height: 4px;
  border-radius: 2px;
  transform: translateY(-50%);
}
.rng__track {
  left: 0;
  right: 0;
  background: var(--color-line);
}
.rng__fill {
  background: var(--color-primary);
}
.rng__input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 28px;
  margin: 0;
  background: none;
  pointer-events: none;
  -webkit-appearance: none;
  appearance: none;
}
.rng__input:focus {
  outline: none;
}
/* Thumbs: clickeables aunque los inputs se solapen */
.rng__input::-webkit-slider-thumb {
  -webkit-appearance: none;
  pointer-events: auto;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform 0.12s ease;
}
.rng__input::-webkit-slider-thumb:hover {
  transform: scale(1.12);
}
.rng__input::-moz-range-thumb {
  pointer-events: auto;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}
.rng__input::-moz-range-track {
  background: none;
}
</style>
