<template>
  <div v-if="visible" class="relative" ref="rootRef">
    <button
      @click="toggle"
      class="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
      title="Instalar app"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
          d="M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/>
      </svg>
    </button>

    <!-- Dropdown -->
    <div
      v-if="abierto"
      class="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-lg border border-gray-100 z-[9999] overflow-hidden"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span class="text-sm font-semibold text-gray-900">Instalar esta app</span>
        <button @click="ocultarSiempre" class="text-xs text-gray-400 hover:text-gray-600" title="No volver a mostrar">
          ✕
        </button>
      </div>

      <div class="px-4 py-3">
        <template v-if="modo === 'directo'">
          <p class="text-xs text-gray-600 mb-3">
            Instala esta app en tu dispositivo para acceder más rápido, incluso desde la pantalla de inicio.
          </p>
          <button
            @click="instalar"
            class="w-full bg-indigo-600 text-white text-sm font-medium rounded-lg py-2 hover:bg-indigo-700 transition"
          >
            Instalar
          </button>
        </template>

        <template v-else-if="modo === 'instrucciones'">
          <p class="text-xs font-medium text-gray-700 mb-2">{{ instrucciones.titulo }}</p>
          <ol class="text-xs text-gray-600 space-y-1.5 list-decimal list-inside">
            <li v-for="(paso, i) in instrucciones.pasos" :key="i">{{ paso }}</li>
          </ol>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const STORAGE_KEY = 'pwa_install_dismissed'

const visible = ref(false)
const abierto = ref(false)
const modo = ref(null) // 'directo' | 'instrucciones'
const instrucciones = ref({ titulo: '', pasos: [] })
const rootRef = ref(null)

let deferredPrompt = null
let fallbackTimer = null

const INSTRUCCIONES = {
  ios: {
    titulo: 'En iPhone/iPad (Safari)',
    pasos: [
      'Toca el botón Compartir (el cuadro con la flecha hacia arriba).',
      'Selecciona "Agregar a pantalla de inicio".',
      'Confirma tocando "Agregar".',
    ],
  },
  android: {
    titulo: 'En Android (Chrome)',
    pasos: [
      'Toca el menú ⋮ (arriba a la derecha).',
      'Selecciona "Agregar a pantalla de inicio".',
      'Confirma tocando "Agregar".',
    ],
  },
  'desktop-edge': {
    titulo: 'En Edge (escritorio)',
    pasos: [
      'Toca el menú ··· (arriba a la derecha).',
      'Ve a "Aplicaciones" → "Instalar este sitio como aplicación".',
    ],
  },
  'desktop-chrome': {
    titulo: 'En Chrome (escritorio)',
    pasos: [
      'Toca el menú ⋮ (arriba a la derecha).',
      'Ve a "Más herramientas" → "Crear acceso directo".',
      'Marca la opción "Abrir como ventana" y confirma.',
    ],
  },
}

function detectarPlataforma() {
  const ua = navigator.userAgent
  const esStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true
  if (esStandalone) return 'standalone'
  if (/iPad|iPhone|iPod/.test(ua) && !window.MSStream) return 'ios'
  if (/Android/.test(ua)) return 'android'
  if (/Edg\//.test(ua)) return 'desktop-edge'
  if (/Chrome\//.test(ua)) return 'desktop-chrome'
  return null
}

function onBeforeInstallPrompt(e) {
  e.preventDefault()
  deferredPrompt = e
  clearTimeout(fallbackTimer)
  modo.value = 'directo'
  visible.value = true
}

function onAppInstalled() {
  visible.value = false
  abierto.value = false
  localStorage.setItem(STORAGE_KEY, '1')
}

const toggle = () => { abierto.value = !abierto.value }

const cerrarSiAfuera = (e) => {
  if (rootRef.value && !rootRef.value.contains(e.target)) abierto.value = false
}

const instalar = async () => {
  if (!deferredPrompt) return
  deferredPrompt.prompt()
  const { outcome } = await deferredPrompt.userChoice
  deferredPrompt = null
  abierto.value = false
  if (outcome === 'accepted') visible.value = false
}

const ocultarSiempre = () => {
  localStorage.setItem(STORAGE_KEY, '1')
  visible.value = false
  abierto.value = false
}

onMounted(() => {
  if (localStorage.getItem(STORAGE_KEY)) return

  const plataforma = detectarPlataforma()
  if (!plataforma || plataforma === 'standalone') return

  window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.addEventListener('appinstalled', onAppInstalled)
  document.addEventListener('click', cerrarSiAfuera)

  // Si el navegador no dispara beforeinstallprompt (sin HTTPS o sin soporte),
  // mostramos las instrucciones manuales para "instalar" como acceso directo.
  fallbackTimer = setTimeout(() => {
    if (!deferredPrompt && INSTRUCCIONES[plataforma]) {
      modo.value = 'instrucciones'
      instrucciones.value = INSTRUCCIONES[plataforma]
      visible.value = true
    }
  }, 1500)
})

onUnmounted(() => {
  clearTimeout(fallbackTimer)
  window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.removeEventListener('appinstalled', onAppInstalled)
  document.removeEventListener('click', cerrarSiAfuera)
})
</script>
