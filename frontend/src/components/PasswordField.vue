<script setup>
import { ref } from 'vue'
import { Lock, Eye, EyeOff } from 'lucide-vue-next'

defineProps({
  modelValue: { type: String, default: '' },
  id: { type: String, required: true },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'current-password' },
  hasError: { type: Boolean, default: false }
})

defineEmits(['update:modelValue'])

const show = ref(false)
</script>

<template>
  <div class="auth-input" :class="{ 'auth-input--error': hasError }">
    <Lock :size="18" />
    <input
      :id="id"
      :type="show ? 'text' : 'password'"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <span
      class="auth-input__toggle"
      role="button"
      tabindex="0"
      :aria-label="show ? 'Ocultar contraseña' : 'Mostrar contraseña'"
      @click="show = !show"
      @keydown.enter.prevent="show = !show"
      @keydown.space.prevent="show = !show"
    >
      <EyeOff v-if="show" :size="18" />
      <Eye v-else :size="18" />
    </span>
  </div>
</template>
