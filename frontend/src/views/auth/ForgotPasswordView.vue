<script setup>
import { reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Mail, Send, MailCheck, ArrowLeft, AlertCircle } from 'lucide-vue-next'
import AuthCard from '@/components/AuthCard.vue'
import AuthStatus from '@/components/AuthStatus.vue'
import { email as validateEmail } from '@/utils/validators'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = reactive({ email: '' })
const error = ref('')
const sent = ref(false)
const loading = ref(false)

async function handleSubmit() {
  error.value = validateEmail(form.email)
  if (error.value) return
  loading.value = true
  try {
    await auth.requestPasswordReset(form.email.toLowerCase())
    sent.value = true
  } catch {
    error.value = 'No pudimos procesar la solicitud. Inténtalo de nuevo.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthCard>
    <AuthStatus v-if="sent" :icon="MailCheck" variant="info" title="Revisa tu correo">
      Si <strong>{{ form.email.toLowerCase() }}</strong> está registrado, te enviamos un enlace para
      restablecer tu contraseña.
      <template #actions>
        <RouterLink to="/login" class="btn btn--primary">Volver a iniciar sesión</RouterLink>
      </template>
    </AuthStatus>

    <template v-else>
      <div class="auth-head">
        <h1 class="auth-title">¿Olvidaste tu contraseña?</h1>
        <p class="auth-subtitle">
          Ingresa tu correo y te enviaremos un enlace para crear una nueva.
        </p>
      </div>

      <div v-if="error" class="auth-alert">
        <AlertCircle :size="18" /> <span>{{ error }}</span>
      </div>

      <form class="auth-form" novalidate @submit.prevent="handleSubmit">
        <div class="auth-field">
          <label for="email">Correo electrónico</label>
          <div class="auth-input" :class="{ 'auth-input--error': error }">
            <Mail :size="18" />
            <input
              id="email"
              v-model="form.email"
              type="email"
              placeholder="tucorreo@ejemplo.com"
            />
          </div>
        </div>

        <button type="submit" class="btn btn--primary btn--block btn--lg" :disabled="loading">
          <template v-if="loading">Enviando…</template>
          <template v-else>Enviar enlace <Send :size="17" /></template>
        </button>
      </form>

      <p class="auth-foot">
        <RouterLink to="/login" class="auth-back-link">
          <ArrowLeft :size="15" /> Volver a iniciar sesión
        </RouterLink>
      </p>
    </template>
  </AuthCard>
</template>

<style scoped>
.auth-back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
