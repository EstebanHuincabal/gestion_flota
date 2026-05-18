import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { useTema } from './utils/tema.js'

const tema = useTema()
tema.aplicar()
tema.aplicarDensidad()
tema.aplicarRadio()
tema.aplicarFuente()

createApp(App).use(router).mount('#app')
