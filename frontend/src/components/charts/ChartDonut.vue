<script setup>
import { computed } from 'vue'

const props = defineProps({
  // [{ name, value }]
  items: { type: Array, default: () => [] },
  format: { type: String, default: 'money' },
  palette: {
    type: Array,
    default: () => ['#0f766e', '#d4a437', '#0ea5a3', '#6366f1', '#f97316', '#64748b']
  }
})

const R = 60
const C = 2 * Math.PI * R
const total = computed(() => props.items.reduce((s, i) => s + (i.value || 0), 0))

const segments = computed(() => {
  let acc = 0
  return props.items.map((it, i) => {
    const frac = total.value ? (it.value || 0) / total.value : 0
    const seg = {
      name: it.name,
      value: it.value || 0,
      color: props.palette[i % props.palette.length],
      dash: frac * C,
      offset: -acc * C,
      pct: Math.round(frac * 100)
    }
    acc += frac
    return seg
  })
})

function fmt(v) {
  if (props.format === 'money') {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
  }
  return new Intl.NumberFormat('es-CO').format(Math.round(v || 0))
}
function compact(v) {
  if (props.format !== 'money') return fmt(v)
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`
  if (Math.abs(v) >= 1e3) return `$${Math.round(v / 1e3)}k`
  return `$${Math.round(v)}`
}
</script>

<template>
  <div class="donut-wrap">
    <div class="donut">
      <svg viewBox="0 0 160 160">
        <g v-if="total" transform="translate(80,80) rotate(-90)">
          <circle
            v-for="(s, i) in segments"
            :key="i"
            :r="R"
            cx="0"
            cy="0"
            fill="none"
            :stroke="s.color"
            stroke-width="20"
            :stroke-dasharray="`${s.dash} ${C - s.dash}`"
            :stroke-dashoffset="s.offset"
            class="donut__seg"
          />
        </g>
        <circle v-else :r="R" cx="80" cy="80" fill="none" stroke="var(--color-surface-alt)" stroke-width="20" />
      </svg>
      <div class="donut__center">
        <span class="donut__total">{{ compact(total) }}</span>
        <span class="donut__caption">Total</span>
      </div>
    </div>
    <ul class="legend">
      <li v-for="(s, i) in segments" :key="i" class="legend__row">
        <span class="legend__dot" :style="{ background: s.color }"></span>
        <span class="legend__name">{{ s.name }}</span>
        <span class="legend__pct">{{ s.pct }}%</span>
        <span class="legend__val">{{ fmt(s.value) }}</span>
      </li>
      <li v-if="!items.length" class="legend__empty">Sin datos en este periodo.</li>
    </ul>
  </div>
</template>

<style scoped>
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
}
.donut {
  position: relative;
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}
.donut svg {
  width: 100%;
  height: 100%;
}
.donut__seg {
  transition: stroke-dasharray 0.5s ease;
}
.donut__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.donut__total {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-ink);
}
.donut__caption {
  font-size: 0.74rem;
  color: var(--color-muted);
}
.legend {
  flex: 1;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.legend__row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.86rem;
}
.legend__dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}
.legend__name {
  color: var(--color-body);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.legend__pct {
  margin-left: auto;
  color: var(--color-muted);
  font-size: 0.78rem;
}
.legend__val {
  font-weight: 700;
  color: var(--color-ink);
  min-width: 70px;
  text-align: right;
}
.legend__empty {
  color: var(--color-muted);
  font-size: 0.88rem;
}
</style>
