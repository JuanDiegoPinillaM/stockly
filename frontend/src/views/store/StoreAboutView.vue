<script setup>
import { RouterLink } from 'vue-router'
import { Target, Heart, Sparkles, Users, ArrowRight, Quote } from 'lucide-vue-next'

const values = [
  { icon: Heart, title: 'Cercanía', text: 'Tratamos a cada cliente como nos gustaría que nos trataran.' },
  { icon: Sparkles, title: 'Calidad', text: 'Seleccionamos con cuidado cada producto de nuestro catálogo.' },
  { icon: Target, title: 'Compromiso', text: 'Cumplimos lo que prometemos, en tiempo y forma.' },
  { icon: Users, title: 'Comunidad', text: 'Crecemos junto a quienes confían en nosotros.' }
]

const stats = [
  { value: '+1.000', label: 'Pedidos entregados' },
  { value: '98%', label: 'Clientes satisfechos' },
  { value: '24 h', label: 'Despacho promedio' },
  { value: '100%', label: 'Pago seguro' }
]
</script>

<template>
  <div class="about">
    <!-- Hero -->
    <section class="about-hero">
      <div class="container">
        <span class="eyebrow">Quiénes somos</span>
        <h1 class="about-hero__title">Más que una tienda,<br />una promesa de calidad</h1>
        <p class="about-hero__text">
          Nacimos con una idea simple: acercar buenos productos a las personas, con un
          servicio honesto y una experiencia de compra fácil.
        </p>
      </div>
    </section>

    <!-- Historia -->
    <section class="container story">
      <div class="story__col">
        <span class="eyebrow">Nuestra historia</span>
        <h2 class="story__title">De un pequeño negocio a tu tienda de confianza</h2>
        <p>
          Empezamos con la convicción de que comprar debería ser simple y confiable.
          Hoy seguimos con la misma esencia: ofrecer variedad, calidad y una atención
          cercana que marque la diferencia.
        </p>
        <p>
          Cada producto de nuestro catálogo está pensado para ti, y trabajamos día a
          día para que tu experiencia sea cada vez mejor.
        </p>
      </div>
      <div class="story__card">
        <Quote :size="30" class="story__quote" />
        <h3 class="story__mission-title">Nuestra misión</h3>
        <p>
          Brindar una experiencia de compra sencilla, segura y cercana, ofreciendo
          productos de calidad que mejoren el día a día de nuestros clientes.
        </p>
      </div>
    </section>

    <!-- Cifras -->
    <section class="stats">
      <div class="container stats__grid">
        <div v-for="s in stats" :key="s.label" class="stat">
          <span class="stat__value">{{ s.value }}</span>
          <span class="stat__label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Valores -->
    <section class="values">
      <div class="container">
        <div class="values__head">
          <span class="eyebrow">Lo que nos mueve</span>
          <h2 class="values__title">Nuestros valores</h2>
        </div>
        <div class="values__grid">
          <div v-for="v in values" :key="v.title" class="value">
            <span class="value__icon"><component :is="v.icon" :size="22" /></span>
            <h3 class="value__name">{{ v.title }}</h3>
            <p class="value__text">{{ v.text }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="container">
      <div class="cta">
        <div class="cta__bg" aria-hidden="true"></div>
        <div class="cta__content">
          <h2 class="cta__title">¿Listo para descubrir nuestro catálogo?</h2>
          <p class="cta__text">Productos seleccionados, envío a todo el país y atención cercana.</p>
          <RouterLink :to="{ name: 'catalog' }" class="btn btn--accent btn--lg">
            Ver productos <ArrowRight :size="18" />
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about {
  padding-bottom: 80px;
}

/* Hero */
.about-hero {
  background:
    radial-gradient(800px 360px at 88% -30%, rgba(var(--color-primary-rgb), 0.1), transparent 60%),
    radial-gradient(600px 360px at 0% 120%, rgba(var(--color-accent-rgb), 0.1), transparent 55%),
    var(--color-hero);
  color: var(--color-hero-ink);
  border-bottom: 1px solid var(--color-line);
  padding: 72px 0;
  text-align: center;
}
.about-hero__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(2.2rem, 4.5vw, 3.1rem);
  line-height: 1.08;
  letter-spacing: -0.02em;
  margin-bottom: 18px;
  color: var(--color-hero-ink);
}
.about-hero__text {
  max-width: 600px;
  margin: 0 auto;
  font-size: 1.1rem;
  color: var(--color-hero-text);
}

/* Historia */
.story {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 48px;
  padding: 72px 0;
  align-items: center;
}
.story__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  letter-spacing: -0.015em;
  margin-bottom: 18px;
}
.story__col p {
  color: var(--color-body);
  line-height: 1.85;
  margin-bottom: 16px;
}
.story__card {
  position: relative;
  background: linear-gradient(155deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  border-radius: var(--radius-xl);
  padding: 36px 32px;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.story__quote {
  color: var(--color-accent);
  margin-bottom: 14px;
}
.story__mission-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.35rem;
  color: #fff;
  margin-bottom: 12px;
}
.story__card p {
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.75;
}

/* Cifras */
.stats {
  background: var(--color-ink);
  color: #fff;
  padding: 44px 0;
}
.stats__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}
.stat {
  text-align: center;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}
.stat:last-child {
  border-right: none;
}
.stat__value {
  display: block;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 2.4rem;
  color: #fff;
  letter-spacing: -0.02em;
}
.stat__label {
  font-size: 0.88rem;
  color: #9fb0a8;
}

/* Valores */
.values {
  padding: 72px 0;
}
.values__head {
  text-align: center;
  margin-bottom: 44px;
}
.values__head .eyebrow {
  justify-content: center;
}
.values__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  letter-spacing: -0.015em;
}
.values__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 22px;
}
.value {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  padding: 30px 26px;
  text-align: center;
  transition:
    box-shadow 0.22s ease,
    transform 0.22s ease;
}
.value:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
}
.value__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  margin-bottom: 16px;
}
.value__name {
  font-size: 1.1rem;
  margin-bottom: 6px;
}
.value__text {
  font-size: 0.9rem;
  color: var(--color-muted);
  line-height: 1.65;
}

/* CTA */
.cta {
  position: relative;
  margin-top: 16px;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: var(--color-surface-dark);
  text-align: center;
}
.cta__bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(600px 300px at 80% 0%, rgba(var(--color-primary-rgb), 0.5), transparent 60%),
    radial-gradient(500px 300px at 10% 100%, rgba(var(--color-accent-rgb), 0.22), transparent 55%);
}
.cta__content {
  position: relative;
  padding: 64px 32px;
}
.cta__title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.7rem, 3vw, 2.3rem);
  color: #fff;
  margin-bottom: 12px;
}
.cta__text {
  color: #b9c4be;
  margin-bottom: 28px;
}

@media (max-width: 820px) {
  .story {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  .stats__grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 28px 24px;
  }
  .stat:nth-child(2) {
    border-right: none;
  }
  .values__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .values__grid {
    grid-template-columns: 1fr;
  }
}
</style>
