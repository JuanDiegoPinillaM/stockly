<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  // [{ name, color, values: [] }]
  series: { type: Array, default: () => [] },
  format: { type: String, default: 'money' }, // 'money' | 'number'
  height: { type: Number, default: 280 }
})

const W = 760
const H = computed(() => props.height)
const PAD = { l: 56, r: 16, t: 16, b: 28 }

const active = ref(null)

const maxV = computed(() => {
  let m = 0
  props.series.forEach((s) => s.values.forEach((v) => (m = Math.max(m, v || 0))))
  return m || 1
})

const innerW = computed(() => W - PAD.l - PAD.r)
const innerH = computed(() => H.value - PAD.t - PAD.b)
const n = computed(() => props.labels.length)

function x(i) {
  if (n.value <= 1) return PAD.l + innerW.value / 2
  return PAD.l + (i / (n.value - 1)) * innerW.value
}
function y(v) {
  return PAD.t + innerH.value - (Math.max(0, v || 0) / maxV.value) * innerH.value
}

function linePath(values) {
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
}
function areaPath(values) {
  if (!values.length) return ''
  return `${linePath(values)} L${x(values.length - 1).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z`
}

function compact(v) {
  const abs = Math.abs(v)
  if (props.format === 'money') {
    if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`
    if (abs >= 1e3) return `$${Math.round(v / 1e3)}k`
    return `$${Math.round(v)}`
  }
  if (abs >= 1e3) return `${(v / 1e3).toFixed(1)}k`
  return `${Math.round(v)}`
}
function full(v) {
  if (props.format === 'money') {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
  }
  return new Intl.NumberFormat('es-CO').format(Math.round(v || 0))
}

// 4 líneas de cuadrícula horizontales con sus etiquetas.
const ticks = computed(() => {
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, k) => {
    const val = (maxV.value / steps) * k
    return { val, y: y(val) }
  })
})

// Etiquetas X: muestra como máximo ~8 para no saturar.
const xLabels = computed(() => {
  const every = Math.ceil(n.value / 8) || 1
  return props.labels.map((l, i) => ({ l, i, show: i % every === 0 || i === n.value - 1 }))
})

const gid = `area-${Math.random().toString(36).slice(2, 8)}`
const tooltipLeft = computed(() => (active.value === null ? 0 : (x(active.value) / W) * 100))
</script>

<template>
  <div class="chart">
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart__svg" @mouseleave="active = null">
      <defs>
        <linearGradient v-for="(s, si) in series" :id="`${gid}-${si}`" :key="si" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="s.color" stop-opacity="0.22" />
          <stop offset="100%" :stop-color="s.color" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- Cuadrícula -->
      <g class="grid">
        <line v-for="(t, i) in ticks" :key="i" :x1="PAD.l" :x2="W - PAD.r" :y1="t.y" :y2="t.y" />
        <text v-for="(t, i) in ticks" :key="`t${i}`" :x="PAD.l - 8" :y="t.y + 3" class="grid__label">{{ compact(t.val) }}</text>
      </g>

      <!-- Áreas + líneas -->
      <g v-for="(s, si) in series" :key="`s${si}`">
        <path :d="areaPath(s.values)" :fill="`url(#${gid}-${si})`" />
        <path :d="linePath(s.values)" fill="none" :stroke="s.color" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
      </g>

      <!-- Guía + puntos activos -->
      <g v-if="active !== null">
        <line class="cursor" :x1="x(active)" :x2="x(active)" :y1="PAD.t" :y2="H - PAD.b" />
        <circle v-for="(s, si) in series" :key="`d${si}`" :cx="x(active)" :cy="y(s.values[active])" r="4.5" :fill="s.color" stroke="#fff" stroke-width="2" />
      </g>

      <!-- Etiquetas X -->
      <text v-for="xl in xLabels" v-show="xl.show" :key="`x${xl.i}`" :x="x(xl.i)" :y="H - 8" class="x-label">{{ xl.l }}</text>

      <!-- Bandas de hover (transparentes) -->
      <rect
        v-for="(l, i) in labels"
        :key="`b${i}`"
        :x="n > 1 ? x(i) - (innerW / (n - 1)) / 2 : PAD.l"
        :y="PAD.t"
        :width="n > 1 ? innerW / (n - 1) : innerW"
        :height="innerH"
        fill="transparent"
        @mouseenter="active = i"
      />
    </svg>

    <!-- Tooltip -->
    <div v-if="active !== null" class="tip" :style="{ left: `${tooltipLeft}%` }">
      <p class="tip__title">{{ labels[active] }}</p>
      <p v-for="(s, si) in series" :key="si" class="tip__row">
        <span class="tip__dot" :style="{ background: s.color }"></span>
        <span class="tip__name">{{ s.name }}</span>
        <span class="tip__val">{{ full(s.values[active]) }}</span>
      </p>
    </div>
  </div>
</template>

<style scoped>
.chart {
  position: relative;
  width: 100%;
}
.chart__svg {
  width: 100%;
  height: auto;
  display: block;
  overflow: visible;
}
.grid line {
  stroke: var(--color-line);
  stroke-dasharray: 3 4;
}
.grid__label {
  fill: var(--color-muted);
  font-size: 11px;
  text-anchor: end;
}
.x-label {
  fill: var(--color-muted);
  font-size: 11px;
  text-anchor: middle;
}
.cursor {
  stroke: var(--color-muted);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}
.tip {
  position: absolute;
  top: 8px;
  transform: translateX(-50%);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
  padding: 8px 10px;
  pointer-events: none;
  min-width: 130px;
  z-index: 3;
}
.tip__title {
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--color-ink);
  margin-bottom: 4px;
}
.tip__row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--color-body);
}
.tip__dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tip__name {
  color: var(--color-muted);
}
.tip__val {
  margin-left: auto;
  font-weight: 700;
  color: var(--color-ink);
}
</style>
