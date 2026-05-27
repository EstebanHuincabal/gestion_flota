<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  paradas:  { type: Array,  default: () => [] },
  polyline: { type: Array,  default: () => [] },
  altura:   { type: String, default: '220px'  },
})

const contenedor  = ref(null)
const mapaError   = ref(false)
let   mapa        = null

const LEAFLET_VER = '1.9.4'

// ── Carga dinámica de Leaflet desde CDN ──────────────────────────────────────
async function cargarLeaflet() {
  if (window.L) return true

  const CDN = `https://unpkg.com/leaflet@${LEAFLET_VER}/dist/`

  if (!document.querySelector('[data-mapa-css]')) {
    const link     = document.createElement('link')
    link.rel       = 'stylesheet'
    link.href      = `${CDN}leaflet.css`
    link.setAttribute('data-mapa-css', '')
    document.head.appendChild(link)
  }

  return new Promise(resolve => {
    const script   = document.createElement('script')
    script.src     = `${CDN}leaflet.js`
    script.onload  = () => resolve(true)
    script.onerror = () => resolve(false)
    document.head.appendChild(script)
  })
}

// ── Íconos SVG pin por tipo ──────────────────────────────────────────────────
function crearIcono(tipo) {
  const colores = {
    origen:  '#1D9E75',
    parada:  '#378ADD',
    destino: '#E24B4A',
  }
  const color = colores[tipo] || '#378ADD'
  const sz    = 26
  const h     = Math.round(sz * 1.3)

  const html = `<svg width="${sz}" height="${h}" viewBox="0 0 24 32"
    xmlns="http://www.w3.org/2000/svg">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20S24 21 24 12C24 5.4 18.6 0 12 0z"
      fill="${color}"/>
    <circle cx="12" cy="12" r="5" fill="white"/>
  </svg>`

  return window.L.divIcon({
    html,
    className:   '',
    iconSize:    [sz, h],
    iconAnchor:  [sz / 2, h],
    popupAnchor: [0, -h],
  })
}

// ── Renderizado principal ────────────────────────────────────────────────────
async function renderMapa() {
  if (!contenedor.value) return
  mapaError.value = false

  const paradasConCoords = props.paradas.filter(p => p.latitud != null && p.longitud != null)

  if (!paradasConCoords.length) return

  const ok = await cargarLeaflet()
  if (!ok) { mapaError.value = true; return }

  const L = window.L

  if (mapa) { mapa.remove(); mapa = null }

  const centro = paradasConCoords[0]
  mapa = L.map(contenedor.value, { zoomControl: false })
    .setView([centro.latitud, centro.longitud], 11)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(mapa)

  // Marcadores paradas
  paradasConCoords.forEach(p => {
    L.marker([p.latitud, p.longitud], { icon: crearIcono(p.tipo) })
      .bindPopup(`<b style="font-size:12px">${p.nombre}</b>`)
      .addTo(mapa)
  })

  // Polilínea OSRM o línea punteada entre paradas
  if (props.polyline?.length > 1) {
    L.polyline(props.polyline, { color: '#378ADD', weight: 4, opacity: 0.8 }).addTo(mapa)
  } else if (paradasConCoords.length > 1) {
    L.polyline(paradasConCoords.map(p => [p.latitud, p.longitud]), {
      color: '#378ADD', weight: 3, opacity: 0.6, dashArray: '8 10',
    }).addTo(mapa)
  }

  // Ajustar vista
  if (paradasConCoords.length > 1) {
    mapa.fitBounds(paradasConCoords.map(p => [p.latitud, p.longitud]), { padding: [20, 20] })
  }
}

watch(() => [props.paradas, props.polyline], renderMapa, { deep: true })
onMounted(renderMapa)
onUnmounted(() => { if (mapa) { mapa.remove(); mapa = null } })
</script>

<template>
  <div class="relative w-full bg-gray-100 overflow-hidden"
       :style="{ height: altura }">

    <!-- Contenedor Leaflet -->
    <div ref="contenedor" class="absolute inset-0" style="z-index:1"/>

    <!-- Sin coordenadas -->
    <div v-if="!paradas.some(p => p.latitud)"
         class="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-gray-100">
      <svg class="w-10 h-10 text-gray-300 mb-1" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
      </svg>
      <p class="text-xs">Sin coordenadas registradas</p>
    </div>

    <!-- Error de carga (sin conexión) -->
    <div v-else-if="mapaError"
         class="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-gray-100">
      <svg class="w-10 h-10 text-gray-300 mb-1" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12h.01M8.464 15.536a5 5 0 01-.001-7.072m-2.827 9.9a9 9 0 010-12.728"/>
      </svg>
      <p class="text-xs font-medium">Mapa no disponible sin conexión</p>
    </div>

  </div>
</template>
