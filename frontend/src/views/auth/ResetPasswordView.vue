<script setup>
import { reactive, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Check, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import AuthCard from '@/components/AuthCard.vue'
import AuthStatus from '@/components/AuthStatus.vue'
import PasswordField from '@/components/PasswordField.vue'
import { minLength, matches } from '@/utils/validators'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()

const uid = route.query.uid || ''
const token = route.query.token || ''
const validLink = Boolean(uid && token)

const form = reactive({ password: '', password2: '' })
const errors = reactive({})
const apiError = ref('')
const done = ref(false)
const loading = ref(false)

function validate() {
  errors.password = minLength(form.password, 8)
  errors.password2 = matches(form.password, form.password2, 'Las contraseñas no coinciden')
  return !errors.password && !errors.password2
}

async function handleSubmit() {
  apiError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.confirmPasswordReset({
      uid,
      token,
      password: form.password,
      password2: form.password2
    })
    done.value = true
  } catch (err) {
    const data = err.response?.data
    const pwd = data?.errors?.password
    if (pwd) {
      errors.password = Array.isArray(pwd) ? pwd[0] : pwd
    } else {
      apiError.value =
        (typeof data?.detail === 'string' ? data.detail : '') ||
        'El enlace no es válido o expiró. Solicita uno nuevo.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthCard>
    <!-- Enlace inválido -->
    <AuthStatus v-if="!validLink" :icon="AlertCircle" variant="error" title="Enlace no válido">
      Este enlace está incompleto. Solicita un nuevo correo de restablecimiento.
      <template #actions>
        <RouterLink to="/forgot-password" class="btn btn--primary"
          >Solicitar nuevo enlace</RouterLink
        >
      </template>
    </AuthStatus>

    <!-- Contraseña cambiada -->
    <AuthStatus
      v-else-if="done"
      :icon="CheckCircle2"
      variant="success"
      title="Contraseña actualizada"
    >
      Ya puedes iniciar sesión con tu nueva contraseña.
      <template #actions>
        <RouterLink to="/login" class="btn btn--primary">Iniciar sesión</RouterLink>
      </template>
    </AuthStatus>

    <!-- Formulario -->
    <template v-else>
      <div class="auth-head">
        <h1 class="auth-title">Crea una nueva contraseña</h1>
        <p class="auth-subtitle">Elige una contraseña segura para tu cuenta.</p>
      </div>

      <div v-if="apiError" class="auth-alert">
        <AlertCircle :size="18" /> <span>{{ apiError }}</span>
      </div>

      <form class="auth-form" novalidate @submit.prevent="handleSubmit">
        <div class="auth-field">
          <label for="password">Nueva contraseña</label>
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
          <template v-if="loading">Guardando…</template>
          <template v-else>Cambiar contraseña <Check :size="17" /></template>
        </button>
      </form>
    </template>
  </AuthCard>
</template>
