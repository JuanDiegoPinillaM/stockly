<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { User, Mail, Lock, ShieldAlert } from 'lucide-vue-next'
import PasswordField from '@/components/PasswordField.vue'
import AvatarField from '@/components/AvatarField.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { useAuthStore } from '@/stores/auth'
import { ID_TYPES } from '@/utils/identification'
import { confirmDelete, toastSuccess, toastError } from '@/utils/notify'

const auth = useAuthStore()

const form = reactive({ first_name: '', last_name: '', id_type: 'CC', id_number: '', phone: '', email: '' })
const profileErrors = reactive({})
const savingProfile = ref(false)

// Foto de perfil (gestionada por el editor de avatar).
const avatarSaving = ref(false)
const avatarName = computed(() => auth.user?.first_name || auth.user?.email || '?')

// Cambio de contraseña
const pwd = reactive({ current_password: '', password: '', password2: '' })
const pwdErrors = reactive({})
const savingPwd = ref(false)

function loadForm() {
  form.first_name = auth.user?.first_name || ''
  form.last_name = auth.user?.last_name || ''
  form.id_type = auth.user?.id_type || 'CC'
  form.id_number = auth.user?.id_number || ''
  form.phone = auth.user?.phone || ''
  form.email = auth.user?.email || ''
}

async function onAvatarSave(blob) {
  avatarSaving.value = true
  try {
    const fd = new FormData()
    fd.append('avatar', blob, 'avatar.jpg')
    await auth.updateProfile(fd)
    toastSuccess('Foto de perfil actualizada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo actualizar la foto.')
  } finally {
    avatarSaving.value = false
  }
}

async function onAvatarRemove() {
  const ok = await confirmDelete(
    'Se quitará tu foto de perfil. El archivo se conserva, solo deja de mostrarse.'
  )
  if (!ok) return
  avatarSaving.value = true
  try {
    // avatar: null desvincula la foto; el archivo no se borra del servidor.
    await auth.updateProfile({ avatar: null })
    toastSuccess('Foto de perfil quitada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo quitar la foto.')
  } finally {
    avatarSaving.value = false
  }
}

async function saveProfile() {
  Object.keys(profileErrors).forEach((k) => delete profileErrors[k])
  if (!form.first_name.trim()) {
    profileErrors.first_name = 'El nombre es obligatorio.'
    return
  }
  if (!form.id_number.trim()) {
    profileErrors.id_number = 'El número de identificación es obligatorio.'
    return
  }
  savingProfile.value = true
  try {
    const emailChanged = form.email.toLowerCase() !== (auth.user?.email || '').toLowerCase()
    const payload = {
      first_name: form.first_name,
      last_name: form.last_name,
      id_type: form.id_type,
      id_number: form.id_number,
      phone: form.phone,
      email: form.email.toLowerCase()
    }
    const data = await auth.updateProfile(payload)
    if (data.email_changed || emailChanged) {
      toastSuccess('Perfil actualizado. Te enviamos un enlace para verificar el nuevo correo.')
    } else {
      toastSuccess('Perfil actualizado')
    }
  } catch (e) {
    const data = e.response?.data
    if (data?.errors) {
      for (const [field, msgs] of Object.entries(data.errors)) {
        if (field in profileErrors || ['first_name', 'last_name', 'email', 'id_type', 'id_number', 'phone'].includes(field)) {
          profileErrors[field] = Array.isArray(msgs) ? msgs[0] : msgs
        }
      }
    }
    toastError(data?.detail || 'No se pudo guardar el perfil.')
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  Object.keys(pwdErrors).forEach((k) => delete pwdErrors[k])
  if (pwd.password !== pwd.password2) {
    pwdErrors.password2 = 'Las contraseñas no coinciden.'
    return
  }
  savingPwd.value = true
  try {
    await auth.changePassword({ ...pwd })
    pwd.current_password = ''
    pwd.password = ''
    pwd.password2 = ''
    toastSuccess('Contraseña actualizada')
  } catch (e) {
    const data = e.response?.data
    if (data?.errors) {
      for (const [field, msgs] of Object.entries(data.errors)) {
        pwdErrors[field] = Array.isArray(msgs) ? msgs[0] : msgs
      }
    }
    toastError(data?.detail || 'No se pudo cambiar la contraseña.')
  } finally {
    savingPwd.value = false
  }
}

onMounted(loadForm)
</script>

<template>
  <div class="page">
    <header class="page__head">
      <h1 class="page__title">Mi perfil</h1>
      <p class="page__subtitle">Actualiza tu información, tu foto y tu contraseña.</p>
    </header>

    <div class="grid">
      <!-- Datos del perfil -->
      <section class="card-box">
        <h2 class="card-box__title"><User :size="18" /> Información personal</h2>

        <div class="avatar-row">
          <AvatarField
            :src="auth.user?.avatar || ''"
            :name="avatarName"
            :size="76"
            :busy="avatarSaving"
            @save="onAvatarSave"
            @remove="onAvatarRemove"
          />
          <p class="avatar-hint">Haz clic en tu foto para verla o editarla.</p>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Nombre *</span>
            <input v-model="form.first_name" class="field__input" maxlength="150" />
            <span v-if="profileErrors.first_name" class="field__error">{{ profileErrors.first_name }}</span>
          </label>
          <label class="field">
            <span class="field__label">Apellido</span>
            <input v-model="form.last_name" class="field__input" maxlength="150" />
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span class="field__label">Tipo de identificación *</span>
            <SearchSelect v-model="form.id_type" :options="ID_TYPES" value-key="value" label-key="label" />
          </label>
          <label class="field">
            <span class="field__label">Número de identificación *</span>
            <input v-model="form.id_number" class="field__input" maxlength="40" />
            <span v-if="profileErrors.id_number" class="field__error">{{ profileErrors.id_number }}</span>
          </label>
        </div>

        <label class="field">
          <span class="field__label">Teléfono</span>
          <input v-model="form.phone" class="field__input" maxlength="40" placeholder="Opcional" />
        </label>

        <label class="field">
          <span class="field__label">Correo electrónico</span>
          <div class="field-icon">
            <Mail :size="17" />
            <input v-model="form.email" type="email" class="field__input" />
          </div>
          <span v-if="profileErrors.email" class="field__error">{{ profileErrors.email }}</span>
        </label>

        <p class="note">
          <ShieldAlert :size="15" />
          Si cambias el correo, te enviaremos un enlace para verificarlo; deberás
          confirmarlo antes de volver a iniciar sesión.
        </p>

        <button class="btn btn--primary" :disabled="savingProfile" @click="saveProfile">
          {{ savingProfile ? 'Guardando…' : 'Guardar cambios' }}
        </button>
      </section>

      <!-- Seguridad -->
      <section class="card-box">
        <h2 class="card-box__title"><Lock :size="18" /> Cambiar contraseña</h2>

        <label class="field">
          <span class="field__label">Contraseña actual</span>
          <PasswordField v-model="pwd.current_password" />
          <span v-if="pwdErrors.current_password" class="field__error">{{ pwdErrors.current_password }}</span>
        </label>
        <label class="field">
          <span class="field__label">Nueva contraseña</span>
          <PasswordField v-model="pwd.password" />
          <span v-if="pwdErrors.password" class="field__error">{{ pwdErrors.password }}</span>
        </label>
        <label class="field">
          <span class="field__label">Repite la nueva contraseña</span>
          <PasswordField v-model="pwd.password2" />
          <span v-if="pwdErrors.password2" class="field__error">{{ pwdErrors.password2 }}</span>
        </label>

        <button class="btn btn--primary" :disabled="savingPwd" @click="changePassword">
          {{ savingPwd ? 'Actualizando…' : 'Actualizar contraseña' }}
        </button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page__head {
  margin-bottom: 24px;
}
.page__title {
  font-size: 1.6rem;
  margin-bottom: 4px;
}
.page__subtitle {
  color: var(--color-muted);
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-box__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.avatar-hint {
  font-size: 0.86rem;
  color: var(--color-muted);
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
}
.field__input {
  width: 100%;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 0.93rem;
  color: var(--color-ink);
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field-icon {
  position: relative;
  display: flex;
  align-items: center;
}
.field-icon svg {
  position: absolute;
  left: 12px;
  color: #94a3b8;
}
.field-icon .field__input {
  padding-left: 38px;
}
.field__error {
  font-size: 0.8rem;
  color: #ef4444;
}
.note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.82rem;
  color: var(--color-muted);
  background: var(--color-surface-alt);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
}
.note svg {
  flex-shrink: 0;
  margin-top: 1px;
}
.btn {
  align-self: flex-start;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
