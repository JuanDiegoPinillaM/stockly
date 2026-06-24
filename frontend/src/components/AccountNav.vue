<script setup>
import { RouterLink } from 'vue-router'
import { User, MapPin, CreditCard, ShoppingBag } from 'lucide-vue-next'

const tabs = [
  { to: { name: 'account' }, label: 'Mi perfil', icon: User },
  { to: { name: 'account-addresses' }, label: 'Direcciones', icon: MapPin },
  { to: { name: 'account-payments' }, label: 'Métodos de pago', icon: CreditCard },
  { to: { name: 'account-orders' }, label: 'Mis compras', icon: ShoppingBag }
]
</script>

<template>
  <nav class="acc-nav">
    <RouterLink
      v-for="t in tabs"
      :key="t.label"
      :to="t.to"
      class="acc-nav__tab"
      active-class="acc-nav__tab--active"
    >
      <component :is="t.icon" :size="17" />
      <span>{{ t.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.acc-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  border-bottom: 1px solid var(--color-line);
  margin-bottom: 24px;
}
.acc-nav__tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.acc-nav__tab:hover {
  color: var(--color-ink);
}
.acc-nav__tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}
</style>
