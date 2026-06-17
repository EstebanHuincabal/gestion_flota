import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { useTema } from './utils/tema.js'
import { initEmpresaActivaDefault } from './utils/empresaActiva.js'

const tema = useTema()
tema.aplicar()
tema.aplicarDensidad()
tema.aplicarRadio()
tema.aplicarFuente()

// SUPERADMIN con sesión ya abierta: deja "Todas las empresas" preseleccionada.
initEmpresaActivaDefault()

createApp(App).use(router).mount('#app')
