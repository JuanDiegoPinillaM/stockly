<script setup>
import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
</script>

<template>
  <div class="site">
    <AppNavbar />
    <main class="site__main">
      <router-view v-slot="{ Component, route }">
        <transition name="fade" mode="out-in">
          <div :key="route.path">
            <component :is="Component" />
          </div>
        </transition>
      </router-view>
    </main>
    <AppFooter />
  </div>
</template>

<style scoped>
/* Footer pegado al fondo: el layout ocupa al menos toda la pantalla y el
   contenido principal crece para rellenar cuando la página es corta. */
.site {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.site__main {
  flex: 1 0 auto;
}
</style>
