<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import AuthCard from '@/components/AuthCard.vue'
import AuthStatus from '@/components/AuthStatus.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()

const status = ref('loading') // loading | success | error
const message = ref('')

onMounted(async () => {
  const uid = route.query.uid
  const token = route.query.token
  if (!uid || !token) {
    status.value = 'error'
    message.value = 'El enlace está incompleto o no es válido.'
    return
  }
  try {
    const data = await auth.verifyEmail({ uid, token })
    status.value = 'success'
    message.value = data.message || 'Tu cuenta fue verificada correctamente.'
  } catch (err) {
    status.value = 'error'
    const data = err.response?.data
    message.value =
      (typeof data?.detail === 'string' ? data.detail : '') ||
      'El enlace expiró o ya fue usado. Solicita uno nuevo desde el inicio de sesión.'
  }
})
</script>

<template>
  <AuthCard>
    <!-- Cargando: spinner propio -->
    <div v-if="status === 'loading'" class="status">
      <span class="status__icon status__icon--loading"><Loader2 :size="44" /></span>
      <h1 class="auth-title">Verificando tu cuenta…</h1>
      <div class="status__body">Un momento, estamos activando tu cuenta.</div>
    </div>

    <AuthStatus
      v-else-if="status === 'success'"
      :icon="CheckCircle2"
      variant="success"
      title="¡Cuenta verificada!"
    >
      {{ message }}
      <template #actions>
        <RouterLink to="/login" class="btn btn--primary">Iniciar sesión</RouterLink>
      </template>
    </AuthStatus>

    <AuthStatus v-else :icon="AlertCircle" variant="error" title="No pudimos verificar tu cuenta">
      {{ message }}
      <template #actions>
        <RouterLink to="/login" class="btn btn--ghost">Volver a iniciar sesión</RouterLink>
      </template>
    </AuthStatus>
  </AuthCard>
</template>

<style scoped>
.status {
  text-align: center;
}

.status__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  margin-bottom: 20px;
}

.status__icon--loading {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.status__icon--loading svg {
  animation: spin 0.9s linear infinite;
}

.status__body {
  max-width: 360px;
  margin: 0 auto;
  color: var(--color-muted);
  font-size: 0.98rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
