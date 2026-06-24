<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { Mail, LogIn, AlertCircle } from 'lucide-vue-next'
import AuthCard from '@/components/AuthCard.vue'
import PasswordField from '@/components/PasswordField.vue'
import { email as validateEmail, required } from '@/utils/validators'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ email: '', password: '' })
const errors = reactive({})
const apiError = ref('')
const needsVerification = ref(false)
const resendMsg = ref('')
const resending = ref(false)
const loading = ref(false)

function validate() {
  errors.email = validateEmail(form.email)
  errors.password = required(form.password, 'Ingresa tu contraseña')
  return !errors.email && !errors.password
}

function getCode(data) {
  const code = data?.code
  return Array.isArray(code) ? code[0] : code
}

async function handleSubmit() {
  apiError.value = ''
  needsVerification.value = false
  resendMsg.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.login({ email: form.email.toLowerCase(), password: form.password })
    // Staff entra al back-office; el comprador a la tienda.
    const fallback = auth.isStaff ? '/dashboard' : '/'
    router.push(route.query.redirect || fallback)
  } catch (err) {
    const status = err.response?.status
    if (getCode(err.response?.data) === 'email_not_verified') {
      needsVerification.value = true
      apiError.value = 'Debes confirmar tu correo antes de iniciar sesión.'
    } else {
      apiError.value =
        status === 401
          ? 'Correo o contraseña incorrectos.'
          : 'No pudimos iniciar sesión. Inténtalo de nuevo.'
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
    <div class="auth-head">
      <h1 class="auth-title">Bienvenido de nuevo</h1>
      <p class="auth-subtitle">Inicia sesión para continuar tu compra y ver tus pedidos.</p>
    </div>

    <div v-if="apiError" class="auth-alert">
      <AlertCircle :size="18" />
      <span>
        {{ apiError }}
        <button
          v-if="needsVerification"
          type="button"
          class="auth-alert__action"
          :disabled="resending"
          @click="resend"
        >
          {{ resending ? 'Reenviando…' : 'Reenviar correo de activación' }}
        </button>
      </span>
    </div>

    <div v-if="resendMsg" class="auth-alert auth-alert--success">
      <AlertCircle :size="18" /> <span>{{ resendMsg }}</span>
    </div>

    <form class="auth-form" novalidate @submit.prevent="handleSubmit">
      <div class="auth-field">
        <label for="email">Correo electrónico</label>
        <div class="auth-input" :class="{ 'auth-input--error': errors.email }">
          <Mail :size="18" />
          <input
            id="email"
            v-model="form.email"
            type="email"
            autocomplete="email"
            placeholder="tucorreo@ejemplo.com"
          />
        </div>
        <span v-if="errors.email" class="auth-error">{{ errors.email }}</span>
      </div>

      <div class="auth-field">
        <div class="auth-label-row">
          <label for="password">Contraseña</label>
          <RouterLink to="/forgot-password" class="auth-forgot"
            >¿Olvidaste tu contraseña?</RouterLink
          >
        </div>
        <PasswordField
          id="password"
          v-model="form.password"
          placeholder="Tu contraseña"
          autocomplete="current-password"
          :has-error="Boolean(errors.password)"
        />
        <span v-if="errors.password" class="auth-error">{{ errors.password }}</span>
      </div>

      <button type="submit" class="btn btn--primary btn--block btn--lg" :disabled="loading">
        <template v-if="loading">Ingresando…</template>
        <template v-else>Iniciar sesión <LogIn :size="17" /></template>
      </button>
    </form>

    <p class="auth-foot">
      ¿No tienes cuenta?
      <RouterLink to="/register">Regístrate gratis</RouterLink>
    </p>
  </AuthCard>
</template>
