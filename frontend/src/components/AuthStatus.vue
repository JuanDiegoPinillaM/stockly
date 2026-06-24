<script setup>
defineProps({
  icon: { type: [Object, Function], required: true },
  title: { type: String, required: true },
  // info (índigo) | success (verde) | error (rojo)
  variant: { type: String, default: 'info' }
})
</script>

<template>
  <div class="status">
    <span class="status__icon" :class="`status__icon--${variant}`">
      <component :is="icon" :size="44" />
    </span>
    <h1 class="auth-title">{{ title }}</h1>
    <div class="status__body"><slot /></div>
    <div v-if="$slots.actions" class="status__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.status {
  text-align: center;
}

.status__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  margin-bottom: 20px;
}

.status__icon--info {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.status__icon--success {
  background: #ecfdf5;
  color: var(--color-success);
}

.status__icon--error {
  background: #fef2f2;
  color: #dc2626;
}

.status__body {
  max-width: 360px;
  margin: 0 auto;
  color: var(--color-muted);
  font-size: 0.98rem;
}

.status__actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 26px;
}
</style>
