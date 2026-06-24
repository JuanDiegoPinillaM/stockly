<script setup>
import { RouterLink } from 'vue-router'
import {
  Target,
  Heart,
  Lightbulb,
  ShieldCheck,
  Users,
  Rocket,
  ArrowRight,
  Building2
} from 'lucide-vue-next'

const stats = [
  { value: '2021', label: 'Año de fundación' },
  { value: '+3.500', label: 'Negocios confían en nosotros' },
  { value: '32', label: 'Personas en el equipo' },
  { value: '5', label: 'Países en Latinoamérica' }
]

const values = [
  {
    icon: Heart,
    title: 'Cercanía',
    text: 'Hablamos el idioma de los negocios pequeños. Construimos pensando en quien atiende su tienda todos los días.'
  },
  {
    icon: Lightbulb,
    title: 'Simplicidad',
    text: 'Creemos que la tecnología debe ser fácil. Si una función no es intuitiva, la volvemos a diseñar.'
  },
  {
    icon: ShieldCheck,
    title: 'Confianza',
    text: 'Cuidamos los datos de cada negocio como si fueran nuestros. La transparencia guía cada decisión.'
  },
  {
    icon: Rocket,
    title: 'Mejora continua',
    text: 'Escuchamos a nuestros clientes y mejoramos el producto cada semana con sus ideas.'
  }
]

const timeline = [
  {
    year: '2021',
    title: 'El comienzo',
    text: 'Nace Stockly tras ver a comerciantes llevando su inventario en cuadernos y hojas de cálculo.'
  },
  {
    year: '2022',
    title: 'Primeros 500 negocios',
    text: 'Lanzamos la versión web y alcanzamos los primeros quinientos negocios activos.'
  },
  {
    year: '2023',
    title: 'App móvil y reportes',
    text: 'Llega el acceso desde el celular y los reportes avanzados que pedían nuestros usuarios.'
  },
  {
    year: '2024',
    title: 'Expansión regional',
    text: 'Stockly cruza fronteras y empieza a operar en cinco países de Latinoamérica.'
  }
]

const team = [
  { name: 'Juan D. Pinilla', role: 'CEO y cofundador' },
  { name: 'María Fernanda Ruiz', role: 'Directora de producto' },
  { name: 'Sebastián Llano', role: 'Líder de ingeniería' },
  { name: 'Valentina Ortiz', role: 'Éxito del cliente' }
]
</script>

<template>
  <!-- HERO -->
  <section class="about-hero">
    <div class="container about-hero__inner">
      <div>
        <span class="eyebrow"><Building2 :size="14" /> Sobre nosotros</span>
        <h1 class="about-hero__title">Ayudamos a los negocios a crecer con orden</h1>
        <p class="about-hero__text">
          Stockly nació para resolver un problema real: la mayoría de los pequeños negocios no sabe
          con certeza qué tiene en inventario. Construimos una herramienta simple y poderosa para
          que cualquier comerciante tenga el control de sus productos, sin importar su experiencia
          con la tecnología.
        </p>
        <RouterLink to="/contacto" class="btn btn--primary btn--lg">
          Conversemos <ArrowRight :size="18" />
        </RouterLink>
      </div>
      <div class="about-hero__art" aria-hidden="true">
        <span class="about-hero__blob"></span>
        <Users :size="120" stroke-width="1.2" />
      </div>
    </div>
  </section>

  <!-- STATS -->
  <section class="section--tight">
    <div class="container">
      <div class="about-stats">
        <div v-for="stat in stats" :key="stat.label" class="about-stats__item">
          <p class="about-stats__value">{{ stat.value }}</p>
          <p class="about-stats__label">{{ stat.label }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- MISSION / VISION -->
  <section class="section section--alt">
    <div class="container mv">
      <article class="mv__card card">
        <span class="icon-badge"><Target :size="24" /></span>
        <h2 class="mv__title">Nuestra misión</h2>
        <p class="mv__text">
          Darle a cada negocio, sin importar su tamaño, las herramientas para controlar su
          inventario de forma simple y tomar decisiones basadas en datos reales.
        </p>
      </article>
      <article class="mv__card card">
        <span class="icon-badge"><Lightbulb :size="24" /></span>
        <h2 class="mv__title">Nuestra visión</h2>
        <p class="mv__text">
          Ser la plataforma de gestión de inventario preferida por los pequeños y medianos comercios
          de Latinoamérica, reconocida por su simplicidad y cercanía.
        </p>
      </article>
    </div>
  </section>

  <!-- VALUES -->
  <section class="section">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><Heart :size="14" /> Nuestros valores</span>
        <h2 class="section-title">Lo que nos mueve</h2>
        <p class="section-subtitle">
          Cuatro principios que guían cómo construimos producto y atendemos a cada negocio.
        </p>
      </div>

      <div class="values">
        <article v-for="value in values" :key="value.title" class="value card">
          <span class="icon-badge"><component :is="value.icon" :size="24" /></span>
          <h3 class="value__title">{{ value.title }}</h3>
          <p class="value__text">{{ value.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- TIMELINE -->
  <section class="section section--alt">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><Rocket :size="14" /> Nuestra historia</span>
        <h2 class="section-title">El camino hasta aquí</h2>
      </div>

      <div class="timeline">
        <div v-for="item in timeline" :key="item.year" class="timeline__item">
          <div class="timeline__marker">
            <span class="timeline__dot"></span>
          </div>
          <div class="timeline__content card">
            <span class="timeline__year">{{ item.year }}</span>
            <h3 class="timeline__title">{{ item.title }}</h3>
            <p class="timeline__text">{{ item.text }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- TEAM -->
  <section class="section">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><Users :size="14" /> El equipo</span>
        <h2 class="section-title">Las personas detrás de Stockly</h2>
      </div>

      <div class="team">
        <article v-for="member in team" :key="member.name" class="team__card">
          <span class="team__avatar">{{ member.name.charAt(0) }}</span>
          <h3 class="team__name">{{ member.name }}</h3>
          <p class="team__role">{{ member.role }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* HERO */
.about-hero {
  padding: 72px 0;
  background:
    radial-gradient(800px 360px at 85% 0%, var(--color-primary-soft), transparent 60%), #fff;
}

.about-hero__inner {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  align-items: center;
  gap: 56px;
}

.about-hero__title {
  font-size: clamp(2.1rem, 4.5vw, 3rem);
  margin-bottom: 20px;
}

.about-hero__text {
  font-size: 1.1rem;
  color: var(--color-muted);
  margin-bottom: 30px;
}

.about-hero__art {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
}

.about-hero__blob {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 280px;
  height: 280px;
  background: var(--color-primary-soft);
  border-radius: 42% 58% 63% 37% / 41% 44% 56% 59%;
}

.about-hero__art svg {
  position: relative;
}

/* STATS */
.about-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  padding: 40px;
  background: var(--color-surface-dark);
  border-radius: var(--radius-xl);
}

.about-stats__item {
  text-align: center;
}

.about-stats__value {
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.03em;
}

.about-stats__label {
  font-size: 0.9rem;
  color: #94a3b8;
  margin-top: 4px;
}

/* MISSION / VISION */
.mv {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.mv__card {
  padding: 38px;
}

.mv__title {
  font-size: 1.5rem;
  margin: 20px 0 12px;
}

.mv__text {
  color: var(--color-muted);
  font-size: 1rem;
}

/* VALUES */
.values {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.value {
  padding: 30px;
}

.value__title {
  font-size: 1.12rem;
  margin: 18px 0 8px;
}

.value__text {
  color: var(--color-muted);
  font-size: 0.92rem;
}

/* TIMELINE */
.timeline {
  position: relative;
  max-width: 760px;
  margin: 0 auto;
  padding-left: 8px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--color-line);
}

.timeline__item {
  position: relative;
  display: flex;
  gap: 28px;
  padding-bottom: 28px;
}

.timeline__item:last-child {
  padding-bottom: 0;
}

.timeline__marker {
  position: relative;
  flex-shrink: 0;
  width: 24px;
  display: flex;
  justify-content: center;
}

.timeline__dot {
  position: relative;
  z-index: 1;
  width: 16px;
  height: 16px;
  margin-top: 26px;
  border-radius: 50%;
  background: var(--color-primary);
  border: 4px solid var(--color-surface-alt);
  box-shadow: 0 0 0 2px var(--color-primary-soft);
}

.timeline__content {
  flex: 1;
  padding: 24px 28px;
}

.timeline__year {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  padding: 3px 11px;
  border-radius: var(--radius-full);
  margin-bottom: 10px;
}

.timeline__title {
  font-size: 1.15rem;
  margin-bottom: 6px;
}

.timeline__text {
  color: var(--color-muted);
  font-size: 0.95rem;
}

/* TEAM */
.team {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.team__card {
  text-align: center;
  padding: 32px 20px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.team__card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.team__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin-bottom: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary-dark));
  color: #fff;
  font-size: 1.7rem;
  font-weight: 700;
}

.team__name {
  font-size: 1.08rem;
  margin-bottom: 4px;
}

.team__role {
  color: var(--color-muted);
  font-size: 0.9rem;
}

/* Responsive */
@media (max-width: 960px) {
  .about-hero__inner {
    grid-template-columns: 1fr;
  }
  .about-hero__art {
    display: none;
  }
  .values,
  .team {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .about-stats,
  .mv,
  .values,
  .team {
    grid-template-columns: 1fr 1fr;
  }
  .mv {
    grid-template-columns: 1fr;
  }
  .about-stats {
    padding: 28px 20px;
  }
}
</style>
