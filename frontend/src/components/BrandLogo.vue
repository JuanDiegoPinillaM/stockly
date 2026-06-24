<script setup>
defineProps({
  light: { type: Boolean, default: false }
})
</script>

<template>
  <span class="brand" :class="{ 'brand--light': light }">
    <span class="brand__mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" width="22" height="22">
        <path
          d="M16 4 L27 9.7 V22.3 L16 28 L5 22.3 V9.7 Z"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <path
          d="M5 9.7 L16 15.4 L27 9.7 M16 15.4 V28"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
      </svg>
    </span>
    <span class="brand__name">Stockly</span>
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  color: var(--color-ink);
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: var(--color-primary);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.brand__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.42rem;
  letter-spacing: -0.02em;
  color: inherit;
}

.brand--light {
  color: #fff;
}

.brand--light .brand__mark {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}
</style>
