<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { LogOut, Eye, EyeOff } from 'lucide-vue-next'
import AccountNav from '@/components/AccountNav.vue'
import AvatarField from '@/components/AvatarField.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { useAuthStore } from '@/stores/auth'
import { ID_TYPES } from '@/utils/identification'
import { confirmDelete, toastSuccess, toastError } from '@/utils/notify'

const auth = useAuthStore()
const router = useRouter()

const form = ref({
  first_name: auth.user?.first_name || '',
  last_name: auth.user?.last_name || '',
  id_type: auth.user?.id_type || 'CC',
  id_number: auth.user?.id_number || '',
  phone: auth.user?.phone || '',
  email: auth.user?.email || ''
})
const savingProfile = ref(false)

// Foto de perfil (gestionada por el editor de avatar).
const avatarSaving = ref(false)
const avatarName = computed(() => auth.user?.first_name || auth.user?.email || '?')

const pwd = ref({ current_password: '', password: '', password2: '' })
const savingPwd = ref(false)
// Mostrar/ocultar cada campo de contraseña.
const showPwd = ref({ current_password: false, password: false, password2: false })

const canSaveProfile = computed(
  () => form.value.first_name.trim() && form.value.id_number.trim() && form.value.email.trim()
)
const canSavePwd = computed(
  () => pwd.value.current_password && pwd.value.password && pwd.value.password === pwd.value.password2
)

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
  const ok = await confirmDelete('Se quitará tu foto de perfil. El archivo se conserva, solo deja de mostrarse.')
  if (!ok) return
  avatarSaving.value = true
  try {
    await auth.updateProfile({ avatar: null })
    toastSuccess('Foto de perfil quitada')
  } catch (e) {
    toastError(e.response?.data?.detail || 'No se pudo quitar la foto.')
  } finally {
    avatarSaving.value = false
  }
}

async function saveProfile() {
  if (!canSaveProfile.value) return
  savingProfile.value = true
  try {
    const payload = { ...form.value }
    payload.email = payload.email.toLowerCase()
    const data = await auth.updateProfile(payload)
    toastSuccess(data.email_changed ? 'Perfil guardado. Revisa tu correo para verificar el cambio.' : 'Perfil guardado')
  } catch (e) {
    const err = e.response?.data
    toastError(
      err?.errors?.id_number?.[0] ||
        err?.errors?.email?.[0] ||
        err?.detail ||
        'No se pudo guardar.'
    )
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  if (!canSavePwd.value) return
  savingPwd.value = true
  try {
    await auth.changePassword({ ...pwd.value })
    pwd.value = { current_password: '', password: '', password2: '' }
    toastSuccess('Contraseña actualizada')
  } catch (e) {
    toastError(e.response?.data?.current_password?.[0] || e.response?.data?.detail || 'No se pudo cambiar la contraseña.')
  } finally {
    savingPwd.value = false
  }
}

async function logout() {
  await auth.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="container account">
    <header class="account__head">
      <h1 class="account__title">Mi cuenta</h1>
      <button class="btn btn--ghost" @click="logout"><LogOut :size="16" /> Cerrar sesión</button>
    </header>

    <AccountNav />

    <div class="cards">
      <section class="card-box">
        <h2 class="card-box__title">Datos personales</h2>

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
          </label>
        </div>
        <div class="field-row">
          <label class="field">
            <span class="field__label">Correo *</span>
            <input v-model="form.email" type="email" class="field__input" />
          </label>
          <label class="field">
            <span class="field__label">Teléfono</span>
            <input v-model="form.phone" class="field__input" maxlength="40" placeholder="Opcional" />
          </label>
        </div>
        <button class="btn btn--primary" :disabled="savingProfile || !canSaveProfile" @click="saveProfile">
          {{ savingProfile ? 'Guardando…' : 'Guardar cambios' }}
        </button>
      </section>

      <section class="card-box">
        <h2 class="card-box__title">Cambiar contraseña</h2>
        <label class="field">
          <span class="field__label">Contraseña actual</span>
          <div class="pwd">
            <input
              v-model="pwd.current_password"
              :type="showPwd.current_password ? 'text' : 'password'"
              class="field__input"
              autocomplete="current-password"
            />
            <button
              type="button"
              class="pwd__toggle"
              :aria-label="showPwd.current_password ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              @click="showPwd.current_password = !showPwd.current_password"
            >
              <EyeOff v-if="showPwd.current_password" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
        </label>
        <div class="field-row">
          <label class="field">
            <span class="field__label">Nueva contraseña</span>
            <div class="pwd">
              <input
                v-model="pwd.password"
                :type="showPwd.password ? 'text' : 'password'"
                class="field__input"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="pwd__toggle"
                :aria-label="showPwd.password ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                @click="showPwd.password = !showPwd.password"
              >
                <EyeOff v-if="showPwd.password" :size="18" />
                <Eye v-else :size="18" />
              </button>
            </div>
          </label>
          <label class="field">
            <span class="field__label">Repetir contraseña</span>
            <div class="pwd">
              <input
                v-model="pwd.password2"
                :type="showPwd.password2 ? 'text' : 'password'"
                class="field__input"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="pwd__toggle"
                :aria-label="showPwd.password2 ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                @click="showPwd.password2 = !showPwd.password2"
              >
                <EyeOff v-if="showPwd.password2" :size="18" />
                <Eye v-else :size="18" />
              </button>
            </div>
          </label>
        </div>
        <button class="btn btn--primary" :disabled="savingPwd || !canSavePwd" @click="changePassword">
          {{ savingPwd ? 'Guardando…' : 'Actualizar contraseña' }}
        </button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.account {
  padding: 28px 0 60px;
}
.account__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.account__title {
  font-size: 1.6rem;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
  align-items: start;
}
.card-box {
  background: #fff;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card-box__title {
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
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.pwd {
  position: relative;
}
.pwd .field__input {
  padding-right: 44px;
}
.pwd__toggle {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition: color 0.15s ease, background 0.15s ease;
}
.pwd__toggle:hover {
  color: var(--color-primary);
  background: var(--color-surface-alt);
}
.btn--primary {
  align-self: flex-start;
}
</style>
