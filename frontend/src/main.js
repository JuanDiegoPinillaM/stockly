import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useConfigStore } from '@/stores/config'
import './assets/styles/main.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Carga la configuración del ecommerce (marca, identidad) y aplica el tema antes
// de montar, para que no haya parpadeo de colores. Si falla, monta igual con los
// valores de fábrica.
const config = useConfigStore(pinia)
config.load().finally(() => app.mount('#app'))
