<script setup>
import { TriangleAlert, RotateCcw } from 'lucide-vue-next'

defineProps({
  title: { type: String, default: 'No se pudo cargar' },
  message: { type: String, default: 'Ocurrió un problema al cargar la información.' },
  retryable: { type: Boolean, default: true }
})
defineEmits(['retry'])
</script>

<template>
  <div class="error-state">
    <span class="error-state__icon"><TriangleAlert :size="30" /></span>
    <h2 class="error-state__title">{{ title }}</h2>
    <p class="error-state__text">{{ message }}</p>
    <button v-if="retryable" type="button" class="btn btn--ghost" @click="$emit('retry')">
      <RotateCcw :size="16" /> Reintentar
    </button>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 6px;
  padding: 56px 24px;
  background: var(--color-surface);
  border: 1px dashed #fca5a5;
  border-radius: var(--radius-lg);
}
.error-state__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: #fef2f2;
  color: #dc2626;
  margin-bottom: 10px;
}
.error-state__title {
  font-size: 1.2rem;
  color: var(--color-ink);
}
.error-state__text {
  color: var(--color-muted);
  max-width: 440px;
}
.error-state .btn {
  margin-top: 16px;
}
</style>
