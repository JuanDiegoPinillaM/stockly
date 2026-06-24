<script setup>
import { Heart, Trash2 } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useWishlistStore } from '@/stores/wishlist'
import { confirmAction } from '@/utils/notify'
import ProductCard from '@/components/store/ProductCard.vue'

const wishlist = useWishlistStore()

async function clearAll() {
  const ok = await confirmAction({
    title: 'Vaciar favoritos',
    text: 'Se quitarán todos los productos de tu lista de deseos.',
    confirmText: 'Vaciar',
    icon: 'warning'
  })
  if (ok) wishlist.clear()
}
</script>

<template>
  <div class="container wl">
    <header class="wl__head">
      <div>
        <h1 class="wl__title"><Heart :size="24" /> Mis favoritos</h1>
        <p class="wl__sub">
          {{ wishlist.count
            ? `${wishlist.count} producto${wishlist.count === 1 ? '' : 's'} guardado${wishlist.count === 1 ? '' : 's'}`
            : 'Aún no has guardado productos.' }}
        </p>
      </div>
      <button v-if="wishlist.count" class="btn btn--ghost btn--sm" @click="clearAll">
        <Trash2 :size="16" /> Vaciar
      </button>
    </header>

    <div v-if="wishlist.count" class="grid">
      <ProductCard v-for="item in wishlist.items" :key="`${item.product_id}:${item.color_id ?? ''}`" :product="item" />
    </div>

    <div v-else class="empty">
      <span class="empty__icon"><Heart :size="34" /></span>
      <h2 class="empty__title">Tu lista está vacía</h2>
      <p class="empty__text">
        Toca el corazón en cualquier producto para guardarlo aquí y encontrarlo fácil después.
      </p>
      <RouterLink :to="{ name: 'catalog' }" class="btn btn--primary">Explorar productos</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.wl {
  padding: 32px 0 64px;
}
.wl__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 26px;
}
.wl__title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  letter-spacing: -0.015em;
}
.wl__title svg {
  color: #e11d48;
}
.wl__sub {
  color: var(--color-muted);
  margin-top: 6px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 22px;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 72px 24px;
  background: #fff;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-lg);
}
.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: #fef2f2;
  color: #e11d48;
  margin-bottom: 8px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  margin-bottom: 12px;
  max-width: 420px;
}
</style>
