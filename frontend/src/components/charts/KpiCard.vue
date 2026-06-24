<script setup>
import { computed } from 'vue'
import { TrendingUp, TrendingDown } from 'lucide-vue-next'
import Sparkline from './Sparkline.vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  change: { type: Number, default: null }, // % vs periodo anterior
  format: { type: String, default: 'number' }, // 'money' | 'number' | 'raw'
  accent: { type: String, default: 'var(--color-primary)' },
  spark: { type: Array, default: () => [] },
  icon: { type: Object, default: null },
  // Para algunos KPIs (p. ej. costo) una baja es buena.
  invert: { type: Boolean, default: false }
})

function fmt(v) {
  if (props.format === 'money') {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP', maximumFractionDigits: 0
    }).format(v || 0)
  }
  if (props.format === 'number') {
    return new Intl.NumberFormat('es-CO').format(Math.round(v || 0))
  }
  return v
}

const display = computed(() => (typeof props.value === 'number' ? fmt(props.value) : props.value))
const hasChange = computed(() => props.change !== null && props.change !== undefined)
const positive = computed(() => {
  if (!hasChange.value) return null
  const up = props.change >= 0
  return props.invert ? !up : up
})
</script>

<template>
  <article class="kpi">
    <div class="kpi__top">
      <span class="kpi__label">{{ label }}</span>
      <span v-if="icon" class="kpi__icon" :style="{ color: accent, background: 'color-mix(in srgb, ' + accent + ' 12%, transparent)' }">
        <component :is="icon" :size="18" />
      </span>
    </div>
    <p class="kpi__value">{{ display }}</p>
    <div class="kpi__foot">
      <span
        v-if="hasChange"
        class="kpi__delta"
        :class="positive ? 'kpi__delta--up' : 'kpi__delta--down'"
      >
        <component :is="change >= 0 ? TrendingUp : TrendingDown" :size="14" />
        {{ Math.abs(change) }}%
      </span>
      <span v-else class="kpi__delta kpi__delta--flat">—</span>
      <span class="kpi__caption">vs. periodo anterior</span>
    </div>
    <div v-if="spark.length" class="kpi__spark">
      <Sparkline :values="spark" :color="accent" :height="34" />
    </div>
  </article>
</template>

<style scoped>
.kpi {
  position: relative;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 16px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
}
.kpi:hover {
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--color-primary) 30%, var(--color-line));
}
.kpi__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.kpi__label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}
.kpi__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.kpi__value {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-ink);
  line-height: 1.1;
}
.kpi__foot {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.kpi__delta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-full);
}
.kpi__delta--up {
  color: #047857;
  background: #ecfdf5;
}
.kpi__delta--down {
  color: #b91c1c;
  background: #fef2f2;
}
.kpi__delta--flat {
  color: var(--color-muted);
  background: var(--color-surface-alt);
}
.kpi__caption {
  font-size: 0.76rem;
  color: var(--color-muted);
}
.kpi__spark {
  margin: 4px -18px -12px;
}
</style>
