<script setup>
import { computed } from 'vue'

const props = defineProps({
  values: { type: Array, default: () => [] },
  color: { type: String, default: 'var(--color-primary)' },
  height: { type: Number, default: 36 }
})

const W = 100
const H = computed(() => props.height)

// Genera el path de la mini línea normalizada al alto/ancho del recuadro.
const path = computed(() => {
  const v = props.values
  if (!v.length) return ''
  const max = Math.max(...v)
  const min = Math.min(...v)
  const span = max - min || 1
  const step = v.length > 1 ? W / (v.length - 1) : 0
  const pad = 3
  const h = H.value - pad * 2
  return v
    .map((val, i) => {
      const x = i * step
      const y = pad + h - ((val - min) / span) * h
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const areaPath = computed(() => {
  if (!path.value) return ''
  return `${path.value} L${W},${H.value} L0,${H.value} Z`
})
const gid = `spark-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <svg class="spark" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" :style="{ height: `${H}px` }">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.28" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <path v-if="areaPath" :d="areaPath" :fill="`url(#${gid})`" />
    <path v-if="path" :d="path" fill="none" :stroke="color" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round" />
  </svg>
</template>

<style scoped>
.spark {
  width: 100%;
  display: block;
}
</style>
