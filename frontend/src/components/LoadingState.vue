<script setup>
defineProps({
  label: { type: String, default: 'Cargando…' }
})
</script>

<template>
  <div class="loading-state" role="status" aria-live="polite">
    <span class="loading-state__spinner" aria-hidden="true"></span>
    <p class="loading-state__label">{{ label }}</p>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
}
.loading-state__spinner {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 3px solid var(--color-primary-soft);
  border-top-color: var(--color-primary);
  animation: loading-spin 0.7s linear infinite;
}
.loading-state__label {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-muted);
}
@keyframes loading-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .loading-state__spinner {
    animation-duration: 1.6s;
  }
}
</style>
