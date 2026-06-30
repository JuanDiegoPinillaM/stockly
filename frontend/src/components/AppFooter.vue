<script setup>
import { computed } from 'vue'
import { Mail, Phone, MapPin, Building2, Send } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import BrandLogo from '@/components/BrandLogo.vue'
import { useConfigStore } from '@/stores/config'
import { socialIcon, socialLabel } from '@/utils/socials'

const year = new Date().getFullYear()

const configStore = useConfigStore()
const cfg = computed(() => configStore.config || {})
const name = computed(() => cfg.value.business_name || 'Stockly')
const tagline = computed(
  () => cfg.value.tagline ||
    'Productos seleccionados con calidad y una experiencia de compra simple, cercana y confiable.'
)

const columns = [
  {
    title: 'Tienda',
    links: [
      { label: 'Inicio', to: '/' },
      { label: 'Productos', to: '/productos' },
      { label: 'Tiendas', to: '/tiendas' },
      { label: 'Quiénes somos', to: '/quienes-somos' }
    ]
  },
  {
    title: 'Mi cuenta',
    links: [
      { label: 'Mi perfil', to: '/cuenta' },
      { label: 'Mis direcciones', to: '/cuenta/direcciones' },
      { label: 'Mis compras', to: '/cuenta/compras' }
    ]
  }
]

// Redes configuradas (cada una con su icono y enlace).
const socials = computed(() =>
  (cfg.value.socials || [])
    .filter((s) => s.url)
    .map((s) => ({ icon: socialIcon(s.network), label: socialLabel(s.network), href: s.url }))
)
</script>

<template>
  <footer class="footer">
    <div class="container">
      <!-- Boletín -->
      <div class="footer__news">
        <div class="footer__news-text">
          <h3 class="footer__news-title">Únete a nuestra lista</h3>
          <p>Recibe novedades y ofertas seleccionadas, sin spam.</p>
        </div>
        <form class="footer__news-form" @submit.prevent>
          <input type="email" placeholder="Tu correo electrónico" aria-label="Correo" />
          <button type="submit" class="btn btn--accent">
            Suscribirme <Send :size="16" />
          </button>
        </form>
      </div>

      <div class="footer__top">
        <div class="footer__brand">
          <BrandLogo />
          <p class="footer__tagline">{{ tagline }}</p>
          <ul class="footer__contact">
            <li v-if="cfg.contact_email"><Mail :size="16" /> {{ cfg.contact_email }}</li>
            <li v-if="cfg.contact_phone"><Phone :size="16" /> {{ cfg.contact_phone }}</li>
            <li v-if="cfg.full_address"><MapPin :size="16" /> {{ cfg.full_address }}</li>
            <li v-if="cfg.nit"><Building2 :size="16" /> NIT {{ cfg.nit }}</li>
          </ul>
        </div>

        <div class="footer__cols">
          <div v-for="col in columns" :key="col.title" class="footer__col">
            <h4 class="footer__col-title">{{ col.title }}</h4>
            <ul>
              <li v-for="link in col.links" :key="link.label">
                <RouterLink :to="link.to" class="footer__link">{{ link.label }}</RouterLink>
              </li>
            </ul>
          </div>
          <div v-if="socials.length" class="footer__col">
            <h4 class="footer__col-title">Síguenos</h4>
            <div class="footer__socials">
              <a
                v-for="social in socials"
                :key="social.label"
                :href="social.href"
                target="_blank"
                rel="noopener"
                class="footer__social"
                :aria-label="social.label"
              >
                <component :is="social.icon" :size="18" />
              </a>
            </div>
          </div>
        </div>
      </div>

      <div class="footer__bottom">
        <p class="footer__copy">© {{ year }} {{ name }}. {{ cfg.footer_note || 'Todos los derechos reservados.' }}</p>
        <div class="footer__legal">
          <a href="#">Términos</a>
          <a href="#">Privacidad</a>
          <a href="#">Cookies</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background: var(--color-footer);
  color: var(--color-footer-text);
  padding: 0 0 32px;
  border-top: 3px solid var(--color-accent);
}
/* El nombre/marca del footer toma el contraste del fondo elegido. */
.footer__brand {
  color: var(--color-footer-ink);
}

/* Boletín */
.footer__news {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  flex-wrap: wrap;
  padding: 40px 0;
  border-bottom: 1px solid var(--color-footer-line);
}
.footer__news-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.5rem;
  color: var(--color-footer-ink);
  margin-bottom: 4px;
}
.footer__news-text p {
  color: var(--color-footer-muted);
  font-size: 0.92rem;
}
.footer__news-form {
  display: flex;
  gap: 10px;
  flex: 1;
  max-width: 440px;
  min-width: 280px;
}
.footer__news-form input {
  flex: 1;
  padding: 13px 18px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-footer-line);
  background: var(--color-footer-field);
  color: var(--color-footer-ink);
  font-family: inherit;
  font-size: 0.92rem;
}
.footer__news-form input::placeholder {
  color: var(--color-footer-muted);
}
.footer__news-form input:focus {
  outline: none;
  border-color: var(--color-accent);
}

.footer__top {
  display: grid;
  grid-template-columns: 1.5fr 2fr;
  gap: 56px;
  padding: 52px 0;
  border-bottom: 1px solid var(--color-footer-line);
}

.footer__tagline {
  margin: 20px 0 24px;
  max-width: 340px;
  color: var(--color-footer-muted);
  font-size: 0.94rem;
  line-height: 1.7;
}

.footer__contact {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer__contact li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.9rem;
  color: var(--color-footer-text);
}

.footer__contact svg {
  color: var(--color-accent);
}

.footer__cols {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}

.footer__col-title {
  color: var(--color-footer-ink);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 18px;
}

.footer__col li {
  margin-bottom: 12px;
}

.footer__link {
  color: var(--color-footer-muted);
  font-size: 0.92rem;
  transition: color 0.18s ease;
}

.footer__link:hover {
  color: var(--color-footer-ink);
}

.footer__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  padding-top: 28px;
}

.footer__copy {
  font-size: 0.86rem;
  color: var(--color-footer-muted);
}

.footer__legal {
  display: flex;
  gap: 24px;
}

.footer__legal a {
  font-size: 0.86rem;
  color: var(--color-footer-muted);
  transition: color 0.18s ease;
}

.footer__legal a:hover {
  color: var(--color-footer-ink);
}

.footer__socials {
  display: flex;
  gap: 10px;
}

.footer__social {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-footer-field);
  color: var(--color-footer-text);
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.footer__social:hover {
  background: var(--color-accent);
  color: #fff;
  transform: translateY(-2px);
}

@media (max-width: 900px) {
  .footer__top {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}

@media (max-width: 600px) {
  .footer__cols {
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }
  .footer__bottom {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
