<script setup>
import { reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { User, Mail, UserPlus, AlertCircle, MailCheck, IdCard, Phone } from 'lucide-vue-next'
import AuthCard from '@/components/AuthCard.vue'
import AuthStatus from '@/components/AuthStatus.vue'
import PasswordField from '@/components/PasswordField.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { required, email as validateEmail, minLength, matches } from '@/utils/validators'
import { ID_TYPES } from '@/utils/identification'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const registered = ref(false)
const resendMsg = ref('')
const resending = ref(false)

const form = reactive({
  first_name: '',
  last_name: '',
  id_type: 'CC',
  id_number: '',
  phone: '',
  email: '',
  password: '',
  password2: ''
})
const errors = reactive({})
const apiError = ref('')
const loading = ref(false)

function validate() {
  errors.first_name = required(form.first_name, 'Ingresa tu nombre')
  errors.id_type = required(form.id_type, 'Elige el tipo')
  errors.id_number = required(form.id_number, 'Ingresa tu número de identificación')
  errors.email = validateEmail(form.email)
  errors.password = minLength(form.password, 8)
  errors.password2 = matches(form.password, form.password2, 'Las contraseñas no coinciden')
  return Object.values(errors).every((e) => !e)
}

/** Mapea errores de validación del backend (contrato { errors }) a los campos. */
function applyServerErrors(data) {
  let handled = false
  for (const [field, messages] of Object.entries(data?.errors || {})) {
    const msg = Array.isArray(messages) ? messages[0] : messages
    if (field in errors) {
      errors[field] = msg
      handled = true
    }
  }
  return handled
}

async function handleSubmit() {
  apiError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.register({
      first_name: form.first_name,
      last_name: form.last_name,
      id_type: form.id_type,
      id_number: form.id_number,
      phone: form.phone,
      email: form.email.toLowerCase(),
      password: form.password,
      password2: form.password2
    })
    // No se inicia sesión: la cuenta debe verificarse por correo primero.
    registered.value = true
  } catch (err) {
    const data = err.response?.data
    if (!applyServerErrors(data)) {
      apiError.value = 'No pudimos crear tu cuenta. Inténtalo de nuevo.'
    }
  } finally {
    loading.value = false
  }
}

async function resend() {
  resendMsg.value = ''
  resending.value = true
  try {
    await auth.resendVerification(form.email.toLowerCase())
    resendMsg.value = 'Te reenviamos el correo de activación.'
  } catch {
    resendMsg.value = 'No pudimos reenviar el correo. Inténtalo más tarde.'
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <AuthCard>
    <!-- Estado: cuenta creada, falta verificar el correo -->
    <AuthStatus v-if="registered" :icon="MailCheck" variant="info" title="Revisa tu correo">
      Enviamos un enlace de activación a
      <strong>{{ form.email.toLowerCase() }}</strong
      >. Haz clic en él para activar tu cuenta y poder iniciar sesión.
      <div v-if="resendMsg" class="auth-alert auth-alert--success" style="margin-top: 18px">
        <MailCheck :size="18" /> <span>{{ resendMsg }}</span>
      </div>
      <template #actions>
        <button class="btn btn--ghost" :disabled="resending" @click="resend">
          {{ resending ? 'Reenviando…' : '¿No te llegó? Reenviar correo' }}
        </button>
        <RouterLink to="/login" class="btn btn--primary">Ir a iniciar sesión</RouterLink>
      </template>
    </AuthStatus>

    <!-- Formulario de registro -->
    <template v-else>
      <div class="auth-head">
        <h1 class="auth-title">Crea tu cuenta</h1>
        <p class="auth-subtitle">Regístrate para comprar más rápido y seguir tus pedidos.</p>
      </div>

      <div v-if="apiError" class="auth-alert">
        <AlertCircle :size="18" /> <span>{{ apiError }}</span>
      </div>

      <form class="auth-form" novalidate @submit.prevent="handleSubmit">
        <div class="auth-row">
          <div class="auth-field">
            <label for="first_name">Nombre</label>
            <div class="auth-input" :class="{ 'auth-input--error': errors.first_name }">
              <User :size="18" />
              <input id="first_name" v-model="form.first_name" type="text" placeholder="Juan" />
            </div>
            <span v-if="errors.first_name" class="auth-error">{{ errors.first_name }}</span>
          </div>
          <div class="auth-field">
            <label for="last_name">Apellido</label>
            <div class="auth-input">
              <User :size="18" />
              <input id="last_name" v-model="form.last_name" type="text" placeholder="Pérez" />
            </div>
          </div>
        </div>

        <div class="auth-field">
          <label>Tipo de identificación</label>
          <SearchSelect
            v-model="form.id_type"
            :options="ID_TYPES"
            value-key="value"
            label-key="label"
            placeholder="Elige el tipo"
          />
          <span v-if="errors.id_type" class="auth-error">{{ errors.id_type }}</span>
        </div>

        <div class="auth-field">
          <label for="id_number">Número de identificación</label>
          <div class="auth-input" :class="{ 'auth-input--error': errors.id_number }">
            <IdCard :size="18" />
            <input id="id_number" v-model="form.id_number" type="text" maxlength="40" placeholder="1234567890" />
          </div>
          <span v-if="errors.id_number" class="auth-error">{{ errors.id_number }}</span>
        </div>

        <div class="auth-field">
          <label for="email">Correo electrónico</label>
          <div class="auth-input" :class="{ 'auth-input--error': errors.email }">
            <Mail :size="18" />
            <input
              id="email"
              v-model="form.email"
              type="email"
              placeholder="tucorreo@ejemplo.com"
            />
          </div>
          <span v-if="errors.email" class="auth-error">{{ errors.email }}</span>
        </div>

        <div class="auth-field">
          <label for="phone">Teléfono <span class="auth-optional">(opcional)</span></label>
          <div class="auth-input">
            <Phone :size="18" />
            <input id="phone" v-model="form.phone" type="tel" maxlength="40" placeholder="300 123 4567" />
          </div>
        </div>

        <div class="auth-field">
          <label for="password">Contraseña</label>
          <PasswordField
            id="password"
            v-model="form.password"
            placeholder="Mínimo 8 caracteres"
            autocomplete="new-password"
            :has-error="Boolean(errors.password)"
          />
          <span v-if="errors.password" class="auth-error">{{ errors.password }}</span>
        </div>

        <div class="auth-field">
          <label for="password2">Confirmar contraseña</label>
          <PasswordField
            id="password2"
            v-model="form.password2"
            placeholder="Repite tu contraseña"
            autocomplete="new-password"
            :has-error="Boolean(errors.password2)"
          />
          <span v-if="errors.password2" class="auth-error">{{ errors.password2 }}</span>
        </div>

        <button type="submit" class="btn btn--primary btn--block btn--lg" :disabled="loading">
          <template v-if="loading">Creando cuenta…</template>
          <template v-else>Crear cuenta <UserPlus :size="17" /></template>
        </button>
      </form>

      <p class="auth-foot">
        ¿Ya tienes cuenta?
        <RouterLink to="/login">Inicia sesión</RouterLink>
      </p>
    </template>
  </AuthCard>
</template>
