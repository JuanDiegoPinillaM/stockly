<script setup>
import { computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import { brandIcon } from '@/utils/brandIcons'

defineProps({
  light: { type: Boolean, default: false }
})

const configStore = useConfigStore()
const name = computed(() => configStore.config?.business_name || 'Stockly')
const logo = computed(() => configStore.config?.logo || '')
const favicon = computed(() => configStore.config?.favicon || '')
const iconComp = computed(() => brandIcon(configStore.config?.icon))
</script>

<template>
  <!-- 1) Logo subido: ocupa toda la marca -->
  <span v-if="logo" class="brand brand--logo">
    <img :src="logo" :alt="name" class="brand__logo" />
  </span>

  <!-- 2) Sin logo: marca (favicon > icono elegido > SVG por defecto) + nombre -->
  <span v-else class="brand" :class="{ 'brand--light': light }">
    <span class="brand__mark" :class="{ 'brand__mark--img': !iconComp && favicon }" aria-hidden="true">
      <component :is="iconComp" v-if="iconComp" :size="22" :stroke-width="2" />
      <img v-else-if="favicon" :src="favicon" :alt="name" class="brand__mark-img" />
      <svg v-else viewBox="0 0 32 32" width="22" height="22">
        <path
          d="M16 4 L27 9.7 V22.3 L16 28 L5 22.3 V9.7 Z"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <path
          d="M5 9.7 L16 15.4 L27 9.7 M16 15.4 V28"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
      </svg>
    </span>
    <span class="brand__name">{{ name }}</span>
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  /* Hereda el color del contenedor (navbar/footer/sidebar) para contrastar con
     su fondo; cada superficie define su --color-*-ink. */
  color: inherit;
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: var(--color-primary);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
  overflow: hidden;
}
/* Cuando la marca es el favicon (imagen), el recuadro va neutro, no en color
   primario (la imagen trae sus propios colores). */
.brand__mark--img {
  background: #fff;
  box-shadow: inset 0 0 0 1px var(--color-line);
}
.brand__mark-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 4px;
}

.brand__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.42rem;
  letter-spacing: -0.02em;
  color: inherit;
}

/* Logo subido: se muestra grande, llenando la altura de la marca sin huecos */
.brand--logo {
  gap: 0;
}
.brand__logo {
  height: 46px;
  width: auto;
  max-width: 220px;
  object-fit: contain;
  display: block;
}

.brand--light {
  color: #fff;
}
.brand--light .brand__mark {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}
</style>
