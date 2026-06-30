<script setup>
/**
 * Contenedor de las vistas de autenticación dentro del ecommerce: una tarjeta
 * centrada que se muestra entre el navbar y el footer de la tienda (PublicLayout).
 */
</script>

<template>
  <section class="auth-page">
    <div class="auth-page__bg" aria-hidden="true"></div>
    <div class="container auth-page__inner">
      <div class="auth-card">
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.auth-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72vh;
  padding: 56px 0 72px;
  overflow: hidden;
}
.auth-page__bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(700px 320px at 85% -10%, rgba(var(--color-primary-rgb), 0.07), transparent 60%),
    radial-gradient(560px 320px at 5% 110%, rgba(var(--color-accent-rgb), 0.08), transparent 55%),
    var(--color-surface-alt);
}
.auth-page__inner {
  position: relative;
  display: flex;
  justify-content: center;
}
.auth-card {
  width: 100%;
  max-width: 460px;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: 40px;
}

@media (max-width: 520px) {
  .auth-card {
    padding: 28px 22px;
    border-radius: var(--radius-lg);
  }
}
</style>
