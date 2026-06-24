<script setup>
import { computed } from 'vue'

const props = defineProps({
  // [{ label, value, meta? }]
  items: { type: Array, default: () => [] },
  format: { type: String, default: 'money' },
  color: { type: String, default: 'var(--color-primary)' },
  rank: { type: Boolean, default: false }
})

const max = computed(() => Math.max(1, ...props.items.map((i) => i.value || 0)))

function fmt(v) {
  if (props.format === 'money') {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
  }
  return new Intl.NumberFormat('es-CO').format(Math.round(v || 0))
}
function pct(v) {
  return `${Math.max(2, ((v || 0) / max.value) * 100)}%`
}
</script>

<template>
  <div class="bars">
    <div v-for="(it, i) in items" :key="i" class="bar">
      <div class="bar__head">
        <span class="bar__label">
          <span v-if="rank" class="bar__rank">{{ i + 1 }}</span>
          {{ it.label }}
        </span>
        <span class="bar__value">{{ fmt(it.value) }}</span>
      </div>
      <div class="bar__track">
        <div class="bar__fill" :style="{ width: pct(it.value), background: color }"></div>
      </div>
      <span v-if="it.meta" class="bar__meta">{{ it.meta }}</span>
    </div>
    <p v-if="!items.length" class="bars__empty">Sin datos en este periodo.</p>
  </div>
</template>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.bar__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.bar__label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar__rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.74rem;
  font-weight: 700;
  flex-shrink: 0;
}
.bar__value {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--color-ink);
  flex-shrink: 0;
}
.bar__track {
  height: 9px;
  background: var(--color-surface-alt);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.bar__fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}
.bar__meta {
  display: block;
  margin-top: 4px;
  font-size: 0.76rem;
  color: var(--color-muted);
}
.bars__empty {
  padding: 24px 0;
  text-align: center;
  color: var(--color-muted);
  font-size: 0.88rem;
}
</style>
