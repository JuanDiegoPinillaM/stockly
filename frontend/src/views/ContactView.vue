<script setup>
import { reactive, ref } from 'vue'
import {
  Mail,
  Phone,
  MapPin,
  Clock,
  MessageSquare,
  Send,
  CheckCircle2,
  Headphones
} from 'lucide-vue-next'
import { required, email as validateEmail, minLength } from '@/utils/validators'

const form = reactive({
  name: '',
  email: '',
  business: '',
  topic: 'ventas',
  message: ''
})

const submitted = ref(false)
const errors = reactive({})

const channels = [
  {
    icon: Mail,
    title: 'Correo',
    value: 'hola@stockly.com',
    note: 'Respondemos en menos de 24 horas'
  },
  {
    icon: Phone,
    title: 'Teléfono',
    value: '+57 300 123 4567',
    note: 'Lunes a viernes'
  },
  {
    icon: MapPin,
    title: 'Oficina',
    value: 'Medellín, Colombia',
    note: 'Cra. 43A # 1-50, El Poblado'
  },
  {
    icon: Clock,
    title: 'Horario',
    value: '8:00 a.m. – 6:00 p.m.',
    note: 'Hora de Colombia (GMT-5)'
  }
]

function validate() {
  errors.name = required(form.name, 'Ingresa tu nombre')
  errors.email = validateEmail(form.email)
  errors.message = minLength(
    form.message.trim(),
    10,
    'Cuéntanos un poco más (mínimo 10 caracteres)'
  )
  return !errors.name && !errors.email && !errors.message
}

function handleSubmit() {
  if (!validate()) return
  // El envío real se conectará al backend de Django más adelante.
  submitted.value = true
}

function resetForm() {
  Object.assign(form, { name: '', email: '', business: '', topic: 'ventas', message: '' })
  submitted.value = false
}
</script>

<template>
  <section class="contact-hero">
    <div class="container text-center">
      <span class="eyebrow"><Headphones :size="14" /> Contáctanos</span>
      <h1 class="contact-hero__title">Estamos aquí para ayudarte</h1>
      <p class="contact-hero__subtitle">
        ¿Tienes preguntas sobre Stockly o quieres una demostración? Escríbenos y nuestro equipo te
        responderá lo antes posible.
      </p>
    </div>
  </section>

  <section class="section--tight">
    <div class="container contact">
      <!-- INFO -->
      <aside class="contact__info">
        <h2 class="contact__info-title">Otras formas de contacto</h2>
        <p class="contact__info-text">
          Elige el canal que prefieras. Siempre hay alguien dispuesto a ayudarte.
        </p>

        <ul class="channels">
          <li v-for="ch in channels" :key="ch.title" class="channel">
            <span class="icon-badge"><component :is="ch.icon" :size="22" /></span>
            <div>
              <p class="channel__title">{{ ch.title }}</p>
              <p class="channel__value">{{ ch.value }}</p>
              <p class="channel__note">{{ ch.note }}</p>
            </div>
          </li>
        </ul>
      </aside>

      <!-- FORM -->
      <div class="contact__form-wrap card">
        <transition name="fade" mode="out-in">
          <div v-if="submitted" key="success" class="success">
            <span class="success__icon"><CheckCircle2 :size="46" /></span>
            <h3 class="success__title">¡Mensaje enviado!</h3>
            <p class="success__text">
              Gracias por escribirnos, {{ form.name.split(' ')[0] || 'amigo' }}. Nuestro equipo te
              contactará muy pronto.
            </p>
            <button class="btn btn--ghost" @click="resetForm">Enviar otro mensaje</button>
          </div>

          <form v-else key="form" class="form" novalidate @submit.prevent="handleSubmit">
            <div class="form__head">
              <MessageSquare :size="20" />
              <h2 class="form__title">Envíanos un mensaje</h2>
            </div>

            <div class="form__row">
              <div class="field">
                <label for="name">Nombre completo</label>
                <input
                  id="name"
                  v-model="form.name"
                  type="text"
                  placeholder="Tu nombre"
                  :class="{ 'field--error': errors.name }"
                />
                <span v-if="errors.name" class="field__error">{{ errors.name }}</span>
              </div>

              <div class="field">
                <label for="email">Correo electrónico</label>
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  placeholder="tucorreo@ejemplo.com"
                  :class="{ 'field--error': errors.email }"
                />
                <span v-if="errors.email" class="field__error">{{ errors.email }}</span>
              </div>
            </div>

            <div class="form__row">
              <div class="field">
                <label for="business">Nombre del negocio <span>(opcional)</span></label>
                <input id="business" v-model="form.business" type="text" placeholder="Mi tienda" />
              </div>

              <div class="field">
                <label for="topic">Motivo</label>
                <select id="topic" v-model="form.topic">
                  <option value="ventas">Quiero conocer los planes</option>
                  <option value="demo">Solicitar una demo</option>
                  <option value="soporte">Soporte técnico</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
            </div>

            <div class="field">
              <label for="message">Mensaje</label>
              <textarea
                id="message"
                v-model="form.message"
                rows="5"
                placeholder="Cuéntanos en qué podemos ayudarte..."
                :class="{ 'field--error': errors.message }"
              ></textarea>
              <span v-if="errors.message" class="field__error">{{ errors.message }}</span>
            </div>

            <button type="submit" class="btn btn--primary btn--block btn--lg">
              Enviar mensaje <Send :size="17" />
            </button>
            <p class="form__legal">
              Al enviar aceptas nuestra política de privacidad y el tratamiento de tus datos.
            </p>
          </form>
        </transition>
      </div>
    </div>
  </section>
</template>

<style scoped>
.contact-hero {
  padding: 72px 0 40px;
  background:
    radial-gradient(800px 340px at 50% -10%, var(--color-primary-soft), transparent 60%), #fff;
}

.contact-hero__title {
  font-size: clamp(2.1rem, 4.5vw, 3rem);
  margin-bottom: 16px;
}

.contact-hero__subtitle {
  max-width: 580px;
  margin: 0 auto;
  font-size: 1.1rem;
  color: var(--color-muted);
}

.contact {
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 48px;
  align-items: start;
}

/* INFO */
.contact__info-title {
  font-size: 1.5rem;
  margin-bottom: 10px;
}

.contact__info-text {
  color: var(--color-muted);
  margin-bottom: 32px;
}

.channels {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.channel {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.channel__title {
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}

.channel__value {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-ink);
}

.channel__note {
  font-size: 0.88rem;
  color: var(--color-muted);
}

/* FORM */
.contact__form-wrap {
  padding: 38px;
  box-shadow: var(--shadow-md);
}

.form__head {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-primary);
  margin-bottom: 26px;
}

.form__title {
  font-size: 1.35rem;
}

.form__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 18px;
}

.form__row .field {
  margin-bottom: 0;
}

.field label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-ink);
}

.field label span {
  font-weight: 400;
  color: var(--color-muted);
}

.field input,
.field select,
.field textarea {
  width: 100%;
  padding: 12px 14px;
  font-family: inherit;
  font-size: 0.95rem;
  color: var(--color-ink);
  background: var(--color-surface-alt);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.field input::placeholder,
.field textarea::placeholder {
  color: #94a3b8;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  background: #fff;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.field textarea {
  resize: vertical;
  min-height: 120px;
}

.field--error {
  border-color: #ef4444 !important;
}

.field__error {
  font-size: 0.82rem;
  color: #ef4444;
}

.form__legal {
  margin-top: 14px;
  font-size: 0.82rem;
  color: var(--color-muted);
  text-align: center;
}

/* SUCCESS */
.success {
  text-align: center;
  padding: 40px 10px;
}

.success__icon {
  display: inline-flex;
  color: var(--color-success);
  margin-bottom: 18px;
}

.success__title {
  font-size: 1.6rem;
  margin-bottom: 10px;
}

.success__text {
  color: var(--color-muted);
  max-width: 380px;
  margin: 0 auto 26px;
}

/* Responsive */
@media (max-width: 900px) {
  .contact {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}

@media (max-width: 560px) {
  .form__row {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .form__row .field {
    margin-bottom: 18px;
  }
  .contact__form-wrap {
    padding: 26px 22px;
  }
}
</style>
