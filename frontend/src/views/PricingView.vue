<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Check, X, ArrowRight, Star, HelpCircle, ShieldCheck } from 'lucide-vue-next'

const annual = ref(false)

const plans = [
  {
    name: 'Básico',
    description: 'Para emprendedores que empiezan a ordenar su inventario.',
    monthly: 39000,
    annual: 31000,
    cta: 'Comenzar gratis',
    featured: false,
    features: [
      { text: '1 punto de venta', ok: true },
      { text: 'Hasta 500 productos', ok: true },
      { text: 'Registro de entradas y salidas', ok: true },
      { text: 'Alertas de stock bajo', ok: true },
      { text: 'Reportes básicos de ventas', ok: true },
      { text: '1 usuario', ok: true },
      { text: 'Lectura por código de barras', ok: false },
      { text: 'Acceso a la API', ok: false }
    ]
  },
  {
    name: 'Profesional',
    description: 'Para negocios en crecimiento que necesitan más control.',
    monthly: 79000,
    annual: 63000,
    cta: 'Comenzar prueba',
    featured: true,
    features: [
      { text: 'Hasta 3 puntos de venta', ok: true },
      { text: 'Productos ilimitados', ok: true },
      { text: 'Registro de entradas y salidas', ok: true },
      { text: 'Alertas de stock bajo', ok: true },
      { text: 'Reportes avanzados y exportables', ok: true },
      { text: 'Hasta 10 usuarios con roles', ok: true },
      { text: 'Lectura por código de barras', ok: true },
      { text: 'Soporte prioritario', ok: true }
    ]
  },
  {
    name: 'Empresarial',
    description: 'Para cadenas y operaciones con múltiples sedes.',
    monthly: 159000,
    annual: 127000,
    cta: 'Hablar con ventas',
    featured: false,
    features: [
      { text: 'Puntos de venta ilimitados', ok: true },
      { text: 'Productos ilimitados', ok: true },
      { text: 'Usuarios ilimitados con roles', ok: true },
      { text: 'Reportes avanzados y personalizados', ok: true },
      { text: 'Acceso completo a la API', ok: true },
      { text: 'Integraciones a la medida', ok: true },
      { text: 'Soporte 24/7 y gerente de cuenta', ok: true },
      { text: 'Capacitación para tu equipo', ok: true }
    ]
  }
]

const formatPrice = (value) =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0
  }).format(value)

const billingNote = computed(() =>
  annual.value ? 'Facturado anualmente · ahorra 20%' : 'Facturado mensualmente'
)

const faqs = [
  {
    q: '¿Puedo probar Stockly antes de pagar?',
    a: 'Sí. Todos los planes incluyen 14 días de prueba gratuita con acceso completo. No pedimos tarjeta de crédito para empezar.'
  },
  {
    q: '¿Puedo cambiar de plan más adelante?',
    a: 'Claro. Puedes subir o bajar de plan en cualquier momento desde tu panel y el cobro se ajusta de forma proporcional.'
  },
  {
    q: '¿Necesito instalar algo?',
    a: 'No. Stockly funciona en la nube desde cualquier navegador, en computador, tablet o celular. Solo inicias sesión y listo.'
  },
  {
    q: '¿Mis datos están seguros?',
    a: 'Tus datos viajan cifrados y se respaldan automáticamente. Tú decides quién de tu equipo tiene acceso y a qué.'
  }
]
</script>

<template>
  <!-- HEADER -->
  <section class="pricing-hero">
    <div class="container text-center">
      <span class="eyebrow"><Star :size="14" /> Planes y precios</span>
      <h1 class="pricing-hero__title">Un precio claro para cada negocio</h1>
      <p class="pricing-hero__subtitle">
        Elige el plan que se ajusta a tu operación. Sin contratos forzosos y con 14 días de prueba
        gratis en todos los planes.
      </p>

      <div class="toggle" role="group" aria-label="Periodo de facturación">
        <button
          :class="{ 'toggle__btn--active': !annual }"
          class="toggle__btn"
          @click="annual = false"
        >
          Mensual
        </button>
        <button
          :class="{ 'toggle__btn--active': annual }"
          class="toggle__btn"
          @click="annual = true"
        >
          Anual <span class="toggle__save">−20%</span>
        </button>
      </div>
    </div>
  </section>

  <!-- PLANS -->
  <section class="section--tight">
    <div class="container">
      <div class="plans">
        <article
          v-for="plan in plans"
          :key="plan.name"
          class="plan card"
          :class="{ 'plan--featured': plan.featured }"
        >
          <div v-if="plan.featured" class="plan__badge">Más popular</div>
          <h3 class="plan__name">{{ plan.name }}</h3>
          <p class="plan__desc">{{ plan.description }}</p>

          <div class="plan__price">
            <span class="plan__amount">{{ formatPrice(annual ? plan.annual : plan.monthly) }}</span>
            <span class="plan__period">/mes</span>
          </div>
          <p class="plan__billing">{{ billingNote }}</p>

          <RouterLink
            to="/contacto"
            class="btn btn--block"
            :class="plan.featured ? 'btn--primary' : 'btn--ghost'"
          >
            {{ plan.cta }} <ArrowRight :size="17" />
          </RouterLink>

          <ul class="plan__features">
            <li v-for="f in plan.features" :key="f.text" :class="{ 'plan__feature--off': !f.ok }">
              <span class="plan__check" :class="f.ok ? 'plan__check--yes' : 'plan__check--no'">
                <Check v-if="f.ok" :size="14" />
                <X v-else :size="14" />
              </span>
              {{ f.text }}
            </li>
          </ul>
        </article>
      </div>

      <p class="plans__note">
        <ShieldCheck :size="16" /> Todos los precios están en pesos colombianos (COP) e incluyen
        actualizaciones y respaldo en la nube.
      </p>
    </div>
  </section>

  <!-- FAQ -->
  <section class="section section--alt">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><HelpCircle :size="14" /> Preguntas frecuentes</span>
        <h2 class="section-title">Resolvemos tus dudas</h2>
      </div>

      <div class="faqs">
        <details v-for="(faq, i) in faqs" :key="i" class="faq" :open="i === 0">
          <summary class="faq__q">
            {{ faq.q }}
            <span class="faq__icon"></span>
          </summary>
          <p class="faq__a">{{ faq.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="section--tight">
    <div class="container text-center">
      <h2 class="section-title">¿Aún no estás seguro de qué plan elegir?</h2>
      <p class="section-subtitle" style="margin-bottom: 28px">
        Cuéntanos sobre tu negocio y te ayudamos a encontrar el plan ideal.
      </p>
      <RouterLink to="/contacto" class="btn btn--primary btn--lg">
        Hablar con un asesor <ArrowRight :size="18" />
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.pricing-hero {
  padding: 72px 0 40px;
  background:
    radial-gradient(900px 360px at 50% -10%, var(--color-primary-soft), transparent 60%), #fff;
}

.pricing-hero__title {
  font-size: clamp(2.1rem, 4.5vw, 3rem);
  margin-bottom: 16px;
}

.pricing-hero__subtitle {
  max-width: 600px;
  margin: 0 auto 32px;
  font-size: 1.1rem;
  color: var(--color-muted);
}

/* Toggle */
.toggle {
  display: inline-flex;
  gap: 4px;
  padding: 5px;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-full);
}

.toggle__btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 20px;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: 0.92rem;
  color: var(--color-muted);
  transition:
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.toggle__btn--active {
  background: #fff;
  color: var(--color-ink);
  box-shadow: var(--shadow-sm);
}

.toggle__save {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-success);
  background: #d1fae5;
  padding: 2px 7px;
  border-radius: var(--radius-full);
}

/* Plans */
.plans {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  align-items: start;
}

.plan {
  position: relative;
  padding: 34px 30px;
  display: flex;
  flex-direction: column;
}

.plan--featured {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-lg);
  transform: translateY(-8px);
}

.plan__badge {
  position: absolute;
  top: -13px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-primary);
}

.plan__name {
  font-size: 1.35rem;
  margin-bottom: 8px;
}

.plan__desc {
  color: var(--color-muted);
  font-size: 0.92rem;
  min-height: 42px;
  margin-bottom: 20px;
}

.plan__price {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.plan__amount {
  font-size: 2.4rem;
  font-weight: 800;
  color: var(--color-ink);
  letter-spacing: -0.03em;
}

.plan__period {
  color: var(--color-muted);
  font-weight: 500;
}

.plan__billing {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin: 4px 0 24px;
}

.plan__features {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--color-line);
}

.plan__features li {
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 0.92rem;
  color: var(--color-body);
}

.plan__feature--off {
  color: #94a3b8;
}

.plan__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex-shrink: 0;
}

.plan__check--yes {
  background: #d1fae5;
  color: var(--color-success);
}

.plan__check--no {
  background: var(--color-surface-alt);
  color: #94a3b8;
}

.plans__note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 40px;
  font-size: 0.9rem;
  color: var(--color-muted);
}

.plans__note svg {
  color: var(--color-primary);
}

/* FAQ */
.faqs {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.faq {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 4px 24px;
}

.faq__q {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 0;
  font-weight: 600;
  font-size: 1.02rem;
  color: var(--color-ink);
  cursor: pointer;
  list-style: none;
}

.faq__q::-webkit-details-marker {
  display: none;
}

.faq__icon {
  position: relative;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.faq__icon::before,
.faq__icon::after {
  content: '';
  position: absolute;
  background: var(--color-primary);
  border-radius: 2px;
  transition: transform 0.2s ease;
}

.faq__icon::before {
  top: 7px;
  left: 0;
  width: 16px;
  height: 2px;
}

.faq__icon::after {
  top: 0;
  left: 7px;
  width: 2px;
  height: 16px;
}

.faq[open] .faq__icon::after {
  transform: scaleY(0);
}

.faq__a {
  padding: 0 0 20px;
  color: var(--color-muted);
  font-size: 0.95rem;
}

/* Responsive */
@media (max-width: 960px) {
  .plans {
    grid-template-columns: 1fr;
    max-width: 460px;
    margin: 0 auto;
  }
  .plan--featured {
    transform: none;
  }
}
</style>
