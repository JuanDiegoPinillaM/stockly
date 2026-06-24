<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { ShoppingCart, Trash2, Minus, Plus, ImageOff, ArrowLeft, AlertTriangle } from 'lucide-vue-next'
import { storeApi } from '@/services/store'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'

const cart = useCartStore()
const auth = useAuthStore()
const router = useRouter()

const stockNotice = ref([])
const checking = ref(false)

function money(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v || 0)
}

const items = computed(() => cart.items)
const hasOutOfStock = computed(() => cart.items.some((i) => i.stock === 0))

function onQtyInput(item, e) {
  cart.setQuantity(item.variantId, e.target.value)
  // Refleja el valor ya topado en el input (por si el usuario escribió de más).
  e.target.value = cart.quantityOf(item.variantId)
}

/**
 * Consulta el stock real en el servidor (fuente de verdad) y reajusta el
 * carrito. Devuelve los cambios detectados para avisar al usuario.
 */
async function syncStock() {
  if (cart.isEmpty) return []
  const ids = cart.items.map((i) => i.variantId)
  const map = await storeApi.variantStock(ids)
  const byId = {}
  Object.entries(map).forEach(([k, v]) => (byId[Number(k)] = v))
  return cart.refreshStock(byId)
}

async function goToCheckout() {
  if (!auth.isAuthenticated) {
    router.push({ name: 'login', query: { redirect: '/checkout' } })
    return
  }
  // Re-valida contra el servidor por si el stock cambió mientras revisaba.
  checking.value = true
  try {
    const changes = await syncStock()
    if (changes.length) {
      stockNotice.value = changes
      return // que revise los cambios antes de continuar
    }
  } catch {
    /* si la verificación falla, el checkout y el backend igual validan */
  } finally {
    checking.value = false
  }
  if (hasOutOfStock.value) return
  router.push('/checkout')
}

// Al abrir el carrito, refresca el stock real (cubre ítems guardados antes de
// conocer el stock y compras de otros usuarios mientras tanto).
onMounted(async () => {
  try {
    const changes = await syncStock()
    if (changes.length) stockNotice.value = changes
  } catch {
    /* si falla, se mantiene el tope con el stock guardado */
  }
})
</script>

<template>
  <div class="container cartv">
    <RouterLink :to="{ name: 'catalog' }" class="back"><ArrowLeft :size="16" /> Seguir comprando</RouterLink>
    <h1 class="cartv__title">Tu carrito</h1>

    <!-- Aviso de cambios de stock -->
    <div v-if="stockNotice.length" class="notice">
      <AlertTriangle :size="20" class="notice__icon" />
      <div class="notice__body">
        <strong>Actualizamos tu carrito</strong>
        <p>El stock de estos productos cambió desde que los agregaste:</p>
        <ul>
          <li v-for="c in stockNotice" :key="c.variantId">
            {{ c.name }}<span v-if="c.variantLabel"> · {{ c.variantLabel }}</span> —
            <template v-if="c.outOfStock">se agotó, quítalo para continuar.</template>
            <template v-else>ajustamos la cantidad de {{ c.from }} a {{ c.to }} (máximo disponible).</template>
          </li>
        </ul>
        <button class="notice__dismiss" @click="stockNotice = []">Entendido</button>
      </div>
    </div>

    <div v-if="cart.isEmpty" class="empty">
      <span class="empty__icon"><ShoppingCart :size="34" /></span>
      <h2 class="empty__title">Tu carrito está vacío</h2>
      <p class="empty__text">Agrega productos desde la tienda para continuar.</p>
      <RouterLink :to="{ name: 'catalog' }" class="btn btn--primary">Ver productos</RouterLink>
    </div>

    <div v-else class="cartv__grid">
      <!-- Líneas -->
      <ul class="lines">
        <li v-for="item in items" :key="item.variantId" class="line" :class="{ 'line--out': item.stock === 0 }">
          <RouterLink :to="{ name: 'store-product', params: { slug: item.productSlug } }" class="line__img">
            <img v-if="item.image" :src="item.image" :alt="item.name" />
            <ImageOff v-else :size="26" />
          </RouterLink>
          <div class="line__info">
            <RouterLink :to="{ name: 'store-product', params: { slug: item.productSlug } }" class="line__name">
              {{ item.name }}
            </RouterLink>
            <span class="line__variant">{{ item.variantLabel }}</span>
            <span class="line__price">{{ money(item.price) }} c/u</span>
            <span v-if="item.stock === 0" class="line__oos">Agotado</span>
            <span v-else-if="item.stock && item.quantity >= item.stock" class="line__max">
              Máximo disponible ({{ item.stock }})
            </span>
          </div>
          <div class="line__qty">
            <button class="qty__btn" :disabled="item.stock === 0 || item.quantity <= 1" aria-label="Quitar uno" @click="cart.setQuantity(item.variantId, item.quantity - 1)">
              <Minus :size="15" />
            </button>
            <input
              class="qty__input"
              type="number"
              min="1"
              :max="item.stock || undefined"
              :value="item.quantity"
              :disabled="item.stock === 0"
              aria-label="Cantidad"
              @change="onQtyInput(item, $event)"
            />
            <button
              class="qty__btn"
              :disabled="item.stock != null && item.quantity >= item.stock"
              aria-label="Agregar uno"
              @click="cart.setQuantity(item.variantId, item.quantity + 1)"
            >
              <Plus :size="15" />
            </button>
          </div>
          <div class="line__total">{{ money(item.price * item.quantity) }}</div>
          <button class="line__remove" aria-label="Eliminar" @click="cart.remove(item.variantId)">
            <Trash2 :size="18" />
          </button>
        </li>
      </ul>

      <!-- Resumen -->
      <aside class="summary">
        <h2 class="summary__title">Resumen</h2>
        <div class="summary__row">
          <span>Productos ({{ cart.count }})</span>
          <span>{{ money(cart.subtotal) }}</span>
        </div>
        <p class="summary__note">El IVA ya está incluido en los precios. El punto de entrega y el pago se eligen en el siguiente paso.</p>
        <div class="summary__total">
          <span>Total</span>
          <strong>{{ money(cart.subtotal) }}</strong>
        </div>
        <button
          class="btn btn--primary btn--block"
          :disabled="checking || hasOutOfStock"
          @click="goToCheckout"
        >
          {{ checking ? 'Verificando…' : 'Continuar compra' }}
        </button>
        <p v-if="hasOutOfStock" class="summary__warn">
          Quita los productos agotados para continuar.
        </p>
        <button class="summary__clear" @click="cart.clear()">Vaciar carrito</button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.cartv {
  padding: 28px 0 60px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.9rem;
  margin-bottom: 14px;
}
.back:hover {
  color: var(--color-primary);
}
.cartv__title {
  font-size: 1.7rem;
  margin-bottom: 22px;
}
.cartv__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 28px;
  align-items: start;
}
.lines {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.line {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 16px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 12px 16px;
}
.line__img {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-alt);
  display: grid;
  place-items: center;
  color: #cbd5e1;
}
.line__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.line__info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.line__name {
  font-weight: 600;
  color: var(--color-ink);
}
.line__name:hover {
  color: var(--color-primary);
}
.line__variant {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.line__price {
  font-size: 0.85rem;
  color: var(--color-muted);
}
.line__max {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-accent-dark);
}
.line__oos {
  display: inline-block;
  width: fit-content;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #b91c1c;
  background: #fef2f2;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.line--out {
  opacity: 0.7;
}
.line--out .line__img,
.line--out .line__total {
  opacity: 0.5;
}

/* Aviso de cambios de stock */
.notice {
  display: flex;
  gap: 12px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  margin-bottom: 22px;
}
.notice__icon {
  color: #b45309;
  flex-shrink: 0;
  margin-top: 2px;
}
.notice__body strong {
  display: block;
  color: var(--color-ink);
  margin-bottom: 2px;
}
.notice__body p {
  font-size: 0.9rem;
  color: var(--color-body);
}
.notice__body ul {
  margin: 8px 0 10px;
  padding-left: 2px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.notice__body li {
  font-size: 0.88rem;
  color: var(--color-body);
}
.notice__dismiss {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}
.notice__dismiss:hover {
  text-decoration: underline;
}
.summary__warn {
  font-size: 0.82rem;
  color: #b91c1c;
  text-align: center;
  margin-top: 10px;
}
.line__qty {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
}
.qty__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 34px;
  color: var(--color-ink);
}
.qty__btn:hover:not(:disabled) {
  background: var(--color-surface-alt);
}
.qty__btn:disabled {
  color: #cbd5e1;
  cursor: not-allowed;
}
.qty__input {
  width: 44px;
  text-align: center;
  font-family: inherit;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-ink);
  border: none;
  border-left: 1px solid var(--color-line);
  border-right: 1px solid var(--color-line);
  background: transparent;
  padding: 6px 0;
  -moz-appearance: textfield;
  appearance: textfield;
}
.qty__input:focus {
  outline: none;
  background: var(--color-surface-alt);
}
.qty__input::-webkit-outer-spin-button,
.qty__input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.line__total {
  font-weight: 700;
  color: var(--color-ink);
  white-space: nowrap;
}
.line__remove {
  color: #94a3b8;
  transition: color 0.15s ease;
}
.line__remove:hover {
  color: #dc2626;
}
.summary {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 20px;
  position: sticky;
  top: 90px;
}
.summary__title {
  font-size: 1.1rem;
  margin-bottom: 16px;
}
.summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
  margin-bottom: 10px;
}
.summary__note {
  font-size: 0.82rem;
  color: var(--color-muted);
  margin: 12px 0;
  line-height: 1.5;
}
.summary__total {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-top: 14px;
  border-top: 1px solid var(--color-line);
  margin-bottom: 16px;
}
.summary__total strong {
  font-size: 1.3rem;
  color: var(--color-primary);
}
.summary__clear {
  display: block;
  width: 100%;
  text-align: center;
  margin-top: 12px;
  font-size: 0.85rem;
  color: var(--color-muted);
}
.summary__clear:hover {
  color: #dc2626;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 60px 24px;
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
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 8px;
}
.empty__title {
  font-size: 1.2rem;
}
.empty__text {
  color: var(--color-muted);
  margin-bottom: 12px;
}

@media (max-width: 820px) {
  .cartv__grid {
    grid-template-columns: 1fr;
  }
  .summary {
    position: static;
  }
  .line {
    grid-template-columns: 60px minmax(0, 1fr) auto;
    grid-template-areas:
      'img info remove'
      'img qty total';
    row-gap: 10px;
  }
  .line__img {
    grid-area: img;
    width: 60px;
    height: 60px;
  }
  .line__info {
    grid-area: info;
  }
  .line__qty {
    grid-area: qty;
  }
  .line__total {
    grid-area: total;
    text-align: right;
  }
  .line__remove {
    grid-area: remove;
    justify-self: end;
  }
}
</style>
