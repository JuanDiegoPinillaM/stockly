<script setup>
import { RouterLink } from 'vue-router'
import {
  ArrowRight,
  PackageCheck,
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  Bell,
  ScanLine,
  Users,
  ShieldCheck,
  Smartphone,
  Store,
  Coffee,
  Pill,
  Shirt,
  Check,
  Star,
  TrendingUp,
  Boxes,
  Clock
} from 'lucide-vue-next'

const stats = [
  { value: '+3.500', label: 'Negocios activos' },
  { value: '12M', label: 'Productos gestionados' },
  { value: '99,9%', label: 'Tiempo en línea' },
  { value: '4,9/5', label: 'Valoración media' }
]

const features = [
  {
    icon: ArrowDownToLine,
    title: 'Registro de entradas',
    text: 'Carga compras y reabastecimientos en segundos. El stock se actualiza al instante.'
  },
  {
    icon: ArrowUpFromLine,
    title: 'Control de salidas',
    text: 'Registra cada venta o salida de producto y mantén tu inventario siempre exacto.'
  },
  {
    icon: Bell,
    title: 'Alertas de stock bajo',
    text: 'Recibe avisos automáticos antes de quedarte sin tus productos más vendidos.'
  },
  {
    icon: BarChart3,
    title: 'Reportes en tiempo real',
    text: 'Visualiza ventas, rotación y márgenes con paneles claros y exportables.'
  },
  {
    icon: ScanLine,
    title: 'Lectura por código de barras',
    text: 'Escanea con la cámara de tu celular y agiliza el ingreso de productos.'
  },
  {
    icon: Users,
    title: 'Equipo y permisos',
    text: 'Suma a tus empleados con roles definidos y mantén el control de cada acción.'
  }
]

const steps = [
  {
    icon: Boxes,
    title: 'Crea tu catálogo',
    text: 'Agrega tus productos con precio, costo y categoría, o impórtalos desde una hoja de cálculo.'
  },
  {
    icon: PackageCheck,
    title: 'Registra movimientos',
    text: 'Anota entradas y salidas a medida que ocurren. Stockly recalcula tu stock automáticamente.'
  },
  {
    icon: TrendingUp,
    title: 'Toma mejores decisiones',
    text: 'Consulta reportes para saber qué reponer, qué se vende más y cuánto estás ganando.'
  }
]

const useCases = [
  {
    icon: Store,
    title: 'Rapitiendas',
    text: 'Controla cientos de referencias y evita quiebres de stock.'
  },
  {
    icon: Coffee,
    title: 'Cafeterías y restaurantes',
    text: 'Gestiona insumos y controla el costo de cada plato.'
  },
  {
    icon: Pill,
    title: 'Droguerías',
    text: 'Lleva el inventario al día con fechas y lotes bajo control.'
  },
  {
    icon: Shirt,
    title: 'Tiendas de ropa',
    text: 'Administra tallas, colores y temporadas sin perder ventas.'
  }
]

const highlights = [
  'Sin instalaciones: funciona en cualquier navegador',
  'Acceso desde el celular, tablet o computador',
  'Tus datos respaldados y cifrados en la nube',
  'Soporte en español cuando lo necesites'
]

const testimonials = [
  {
    quote:
      'Antes anotaba el inventario en un cuaderno y siempre se me acababan los productos. Con Stockly sé exactamente qué reponer cada semana.',
    name: 'Carolina Restrepo',
    role: 'Dueña de rapitienda · Medellín'
  },
  {
    quote:
      'Lo que más me gustó es lo fácil que es. Mis empleados aprendieron a usarlo el mismo día y los reportes me ahorran horas.',
    name: 'Andrés Gómez',
    role: 'Minimercado La Esquina · Bogotá'
  }
]
</script>

<template>
  <!-- ============ HERO ============ -->
  <section class="hero">
    <div class="container hero__inner">
      <div class="hero__content">
        <span class="eyebrow"> <Star :size="14" /> Software de inventario para tu negocio </span>
        <h1 class="hero__title">
          Controla tu inventario <span class="hero__accent">sin complicaciones</span>
        </h1>
        <p class="hero__subtitle">
          Stockly te ayuda a registrar entradas y salidas, controlar el stock y entender tus ventas
          en tiempo real. Ideal para rapitiendas, minimercados y cualquier negocio con productos.
        </p>
        <div class="hero__actions">
          <RouterLink to="/precios" class="btn btn--primary btn--lg">
            Comenzar gratis <ArrowRight :size="18" />
          </RouterLink>
          <RouterLink to="/contacto" class="btn btn--ghost btn--lg"> Solicitar demo </RouterLink>
        </div>
        <ul class="hero__checks">
          <li><Check :size="16" /> 14 días de prueba</li>
          <li><Check :size="16" /> Sin tarjeta de crédito</li>
          <li><Check :size="16" /> Cancela cuando quieras</li>
        </ul>
      </div>

      <!-- Dashboard mockup -->
      <div class="hero__visual" aria-hidden="true">
        <div class="mock">
          <div class="mock__bar">
            <span class="mock__dot"></span>
            <span class="mock__dot"></span>
            <span class="mock__dot"></span>
          </div>
          <div class="mock__body">
            <div class="mock__row">
              <div class="mock__card">
                <span class="mock__icon mock__icon--green"><TrendingUp :size="18" /></span>
                <div>
                  <p class="mock__label">Ventas hoy</p>
                  <p class="mock__value">$1.284.500</p>
                </div>
              </div>
              <div class="mock__card">
                <span class="mock__icon"><Boxes :size="18" /></span>
                <div>
                  <p class="mock__label">Productos</p>
                  <p class="mock__value">842</p>
                </div>
              </div>
            </div>

            <div class="mock__panel">
              <div class="mock__panel-head">
                <span>Movimientos recientes</span>
                <Clock :size="15" />
              </div>
              <ul class="mock__list">
                <li>
                  <span class="mock__tag mock__tag--in"
                    ><ArrowDownToLine :size="13" /> Entrada</span
                  >
                  <span class="mock__item">Gaseosa 1.5L × 24</span>
                  <span class="mock__amount mock__amount--in">+24</span>
                </li>
                <li>
                  <span class="mock__tag mock__tag--out"
                    ><ArrowUpFromLine :size="13" /> Salida</span
                  >
                  <span class="mock__item">Pan tajado × 6</span>
                  <span class="mock__amount mock__amount--out">−6</span>
                </li>
                <li>
                  <span class="mock__tag mock__tag--in"
                    ><ArrowDownToLine :size="13" /> Entrada</span
                  >
                  <span class="mock__item">Café 500g × 12</span>
                  <span class="mock__amount mock__amount--in">+12</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div class="mock__float">
          <span class="mock__icon mock__icon--amber"><Bell :size="16" /></span>
          <div>
            <p class="mock__float-title">Stock bajo</p>
            <p class="mock__float-text">Arroz 1kg · quedan 4</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ============ STATS ============ -->
  <section class="stats">
    <div class="container">
      <div class="stats__grid">
        <div v-for="stat in stats" :key="stat.label" class="stats__item">
          <p class="stats__value">{{ stat.value }}</p>
          <p class="stats__label">{{ stat.label }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ============ FEATURES ============ -->
  <section id="funcionalidades" class="section">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><PackageCheck :size="14" /> Funcionalidades</span>
        <h2 class="section-title">Todo lo que necesitas para gestionar tus productos</h2>
        <p class="section-subtitle">
          Una plataforma completa para mantener tu inventario bajo control, sin hojas de cálculo ni
          cuadernos.
        </p>
      </div>

      <div class="features">
        <article v-for="feature in features" :key="feature.title" class="feature card">
          <span class="icon-badge"><component :is="feature.icon" :size="24" /></span>
          <h3 class="feature__title">{{ feature.title }}</h3>
          <p class="feature__text">{{ feature.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ============ HOW IT WORKS ============ -->
  <section class="section section--alt">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><ScanLine :size="14" /> Cómo funciona</span>
        <h2 class="section-title">Empieza en tres pasos simples</h2>
        <p class="section-subtitle">
          No necesitas conocimientos técnicos. En minutos tendrás tu inventario funcionando.
        </p>
      </div>

      <div class="steps">
        <article v-for="(step, i) in steps" :key="step.title" class="step">
          <span class="step__num">{{ i + 1 }}</span>
          <span class="icon-badge"><component :is="step.icon" :size="24" /></span>
          <h3 class="step__title">{{ step.title }}</h3>
          <p class="step__text">{{ step.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ============ HIGHLIGHT SPLIT ============ -->
  <section class="section">
    <div class="container split">
      <div class="split__text">
        <span class="eyebrow"><Smartphone :size="14" /> En cualquier lugar</span>
        <h2 class="section-title">Tu negocio en la palma de tu mano</h2>
        <p class="section-subtitle">
          Accede a Stockly desde donde estés. Revisa tu stock, registra una venta o consulta tus
          reportes desde el celular mientras atiendes.
        </p>
        <ul class="split__list">
          <li v-for="item in highlights" :key="item">
            <span class="split__check"><Check :size="15" /></span>{{ item }}
          </li>
        </ul>
        <RouterLink to="/precios" class="btn btn--primary">
          Ver planes <ArrowRight :size="18" />
        </RouterLink>
      </div>

      <div class="split__visual" aria-hidden="true">
        <div class="phone">
          <div class="phone__notch"></div>
          <div class="phone__screen">
            <div class="phone__head">
              <ShieldCheck :size="18" />
              <span>Inventario</span>
            </div>
            <div class="phone__stat">
              <p class="phone__stat-label">Valor del inventario</p>
              <p class="phone__stat-value">$18.940.000</p>
            </div>
            <div class="phone__items">
              <div v-for="n in 4" :key="n" class="phone__item">
                <span class="phone__bar" :style="{ width: 90 - n * 14 + '%' }"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ============ USE CASES ============ -->
  <section id="casos" class="section section--alt">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><Store :size="14" /> Casos de uso</span>
        <h2 class="section-title">Pensado para negocios como el tuyo</h2>
        <p class="section-subtitle">
          Cualquier negocio que maneje productos puede sacarle provecho a Stockly.
        </p>
      </div>

      <div class="usecases">
        <article v-for="uc in useCases" :key="uc.title" class="usecase card">
          <span class="icon-badge"><component :is="uc.icon" :size="24" /></span>
          <h3 class="usecase__title">{{ uc.title }}</h3>
          <p class="usecase__text">{{ uc.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ============ TESTIMONIALS ============ -->
  <section class="section">
    <div class="container">
      <div class="section-head">
        <span class="eyebrow"><Star :size="14" /> Testimonios</span>
        <h2 class="section-title">Negocios que ya tienen el control</h2>
      </div>

      <div class="testimonials">
        <figure v-for="t in testimonials" :key="t.name" class="testimonial card">
          <div class="testimonial__stars">
            <Star v-for="n in 5" :key="n" :size="16" fill="currentColor" />
          </div>
          <blockquote class="testimonial__quote">"{{ t.quote }}"</blockquote>
          <figcaption class="testimonial__author">
            <span class="testimonial__avatar">{{ t.name.charAt(0) }}</span>
            <span>
              <strong>{{ t.name }}</strong>
              <small>{{ t.role }}</small>
            </span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>

  <!-- ============ CTA ============ -->
  <section class="section--tight">
    <div class="container">
      <div class="cta">
        <h2 class="cta__title">Empieza a controlar tu inventario hoy</h2>
        <p class="cta__text">
          Prueba Stockly gratis durante 14 días. Sin tarjeta, sin compromisos.
        </p>
        <div class="cta__actions">
          <RouterLink to="/precios" class="btn btn--light btn--lg">
            Comenzar gratis <ArrowRight :size="18" />
          </RouterLink>
          <RouterLink to="/contacto" class="btn cta__ghost btn--lg"> Hablar con ventas </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* ---------------- HERO ---------------- */
.hero {
  position: relative;
  padding: 80px 0 96px;
  overflow: hidden;
  background:
    radial-gradient(1100px 480px at 78% -8%, var(--color-primary-soft), transparent 60%),
    linear-gradient(180deg, #fff 0%, var(--color-surface-alt) 100%);
}

.hero__inner {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  align-items: center;
  gap: 56px;
}

.hero__title {
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  line-height: 1.08;
  margin-bottom: 22px;
}

.hero__accent {
  color: var(--color-primary);
}

.hero__subtitle {
  font-size: 1.15rem;
  color: var(--color-muted);
  max-width: 520px;
  margin-bottom: 32px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 28px;
}

.hero__checks {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.hero__checks li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--color-body);
}

.hero__checks svg {
  color: var(--color-success);
}

/* Mockup */
.hero__visual {
  position: relative;
}

.mock {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.mock__bar {
  display: flex;
  gap: 7px;
  padding: 15px 18px;
  background: var(--color-surface-alt);
  border-bottom: 1px solid var(--color-line);
}

.mock__dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #cbd5e1;
}

.mock__body {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.mock__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.mock__card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
}

.mock__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  flex-shrink: 0;
}

.mock__icon--green {
  background: #d1fae5;
  color: var(--color-success);
}

.mock__icon--amber {
  background: #fef3c7;
  color: var(--color-amber);
}

.mock__label {
  font-size: 0.78rem;
  color: var(--color-muted);
}

.mock__value {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-ink);
}

.mock__panel {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.mock__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
  background: var(--color-surface-alt);
  border-bottom: 1px solid var(--color-line);
}

.mock__list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--color-line);
}

.mock__list li:last-child {
  border-bottom: none;
}

.mock__tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 0.72rem;
  font-weight: 600;
}

.mock__tag--in {
  background: #d1fae5;
  color: #047857;
}

.mock__tag--out {
  background: #fee2e2;
  color: #b91c1c;
}

.mock__item {
  flex: 1;
  color: var(--color-body);
}

.mock__amount {
  font-weight: 700;
}

.mock__amount--in {
  color: var(--color-success);
}

.mock__amount--out {
  color: #ef4444;
}

.mock__float {
  position: absolute;
  bottom: -22px;
  left: -28px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.mock__float-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-ink);
}

.mock__float-text {
  font-size: 0.78rem;
  color: var(--color-muted);
}

/* ---------------- STATS ---------------- */
.stats {
  border-top: 1px solid var(--color-line);
  border-bottom: 1px solid var(--color-line);
  background: #fff;
  padding: 40px 0;
}

.stats__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.stats__item {
  text-align: center;
}

.stats__value {
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  font-weight: 800;
  color: var(--color-ink);
  letter-spacing: -0.03em;
}

.stats__label {
  font-size: 0.92rem;
  color: var(--color-muted);
}

/* ---------------- FEATURES ---------------- */
.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature {
  padding: 30px;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.feature:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
  border-color: #c7d2fe;
}

.feature__title {
  font-size: 1.15rem;
  margin: 18px 0 8px;
}

.feature__text {
  color: var(--color-muted);
  font-size: 0.95rem;
}

/* ---------------- STEPS ---------------- */
.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.step {
  position: relative;
  padding: 32px 28px;
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
}

.step__num {
  position: absolute;
  top: 24px;
  right: 26px;
  font-size: 2.4rem;
  font-weight: 800;
  color: var(--color-primary-soft);
  line-height: 1;
}

.step__title {
  font-size: 1.15rem;
  margin: 18px 0 8px;
}

.step__text {
  color: var(--color-muted);
  font-size: 0.95rem;
}

/* ---------------- SPLIT ---------------- */
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 64px;
}

.split__list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 26px 0 32px;
}

.split__list li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1rem;
  color: var(--color-body);
}

.split__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #d1fae5;
  color: var(--color-success);
  flex-shrink: 0;
}

.split__visual {
  display: flex;
  justify-content: center;
}

.phone {
  position: relative;
  width: 290px;
  padding: 14px;
  background: #0b1120;
  border-radius: 40px;
  box-shadow: var(--shadow-lg);
}

.phone__notch {
  position: absolute;
  top: 22px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 22px;
  background: #0b1120;
  border-radius: var(--radius-full);
  z-index: 2;
}

.phone__screen {
  background: linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-radius: 30px;
  padding: 44px 22px 30px;
  min-height: 460px;
  color: #fff;
}

.phone__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 26px;
}

.phone__stat {
  background: rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-md);
  padding: 18px;
  margin-bottom: 20px;
}

.phone__stat-label {
  font-size: 0.82rem;
  opacity: 0.85;
}

.phone__stat-value {
  font-size: 1.6rem;
  font-weight: 800;
}

.phone__items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.phone__item {
  background: rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  height: 44px;
  display: flex;
  align-items: center;
  padding: 0 12px;
}

.phone__bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.65);
  border-radius: var(--radius-full);
}

/* ---------------- USE CASES ---------------- */
.usecases {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.usecase {
  padding: 28px;
  text-align: left;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.usecase:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.usecase__title {
  font-size: 1.08rem;
  margin: 16px 0 6px;
}

.usecase__text {
  color: var(--color-muted);
  font-size: 0.92rem;
}

/* ---------------- TESTIMONIALS ---------------- */
.testimonials {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.testimonial {
  padding: 34px;
}

.testimonial__stars {
  display: flex;
  gap: 3px;
  color: var(--color-amber);
  margin-bottom: 18px;
}

.testimonial__quote {
  font-size: 1.1rem;
  color: var(--color-ink);
  line-height: 1.6;
  margin-bottom: 24px;
}

.testimonial__author {
  display: flex;
  align-items: center;
  gap: 14px;
}

.testimonial__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-weight: 700;
  font-size: 1.1rem;
}

.testimonial__author strong {
  display: block;
  color: var(--color-ink);
  font-size: 0.98rem;
}

.testimonial__author small {
  color: var(--color-muted);
  font-size: 0.85rem;
}

/* ---------------- CTA ---------------- */
.cta {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: 72px 32px;
  border-radius: var(--radius-xl);
  background:
    radial-gradient(700px 300px at 50% 0%, var(--color-primary-light), transparent 70%),
    var(--color-primary);
  box-shadow: var(--shadow-lg);
}

.cta__title {
  color: #fff;
  font-size: clamp(1.8rem, 3.5vw, 2.4rem);
  margin-bottom: 14px;
}

.cta__text {
  color: rgba(255, 255, 255, 0.88);
  font-size: 1.1rem;
  margin-bottom: 30px;
}

.cta__actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
}

.cta__ghost {
  background: transparent;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.cta__ghost:hover {
  background: rgba(255, 255, 255, 0.12);
}

/* ---------------- RESPONSIVE ---------------- */
@media (max-width: 960px) {
  .hero__inner,
  .split {
    grid-template-columns: 1fr;
    gap: 48px;
  }
  .hero__visual {
    max-width: 480px;
  }
  .features,
  .steps {
    grid-template-columns: 1fr 1fr;
  }
  .usecases {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .stats__grid {
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }
  .features,
  .steps,
  .usecases,
  .testimonials {
    grid-template-columns: 1fr;
  }
  .mock__float {
    left: 0;
  }
}
</style>
