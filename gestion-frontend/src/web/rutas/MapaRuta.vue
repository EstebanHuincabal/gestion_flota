<template>
  <div style="position: relative; height: 100%; width: 100%;">
    <!-- Buscador de ciudad (opcional) -->
    <div v-if="buscador" class="mapa-buscador">
      <div class="mapa-buscador-box">
        <svg class="mapa-buscador-icono" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input :value="q" @input="onBuscarCiudad" type="text" placeholder="Buscar ciudad..." class="mapa-buscador-input"/>
        <span v-if="buscandoCiudad" class="mapa-buscador-spinner"/>
      </div>
      <div v-if="resultadosCiudad.length" class="mapa-buscador-lista">
        <button v-for="(r, i) in resultadosCiudad" :key="i" type="button"
          class="mapa-buscador-item" @click="irACiudad(r)">
          {{ r.display_name }}
        </button>
      </div>
    </div>

    <div :id="mapId" style="height: 100%; width: 100%; border-radius: 0.5rem; z-index: 1;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  paradas:      { type: Array,   default: () => [] },
  polyline:     { type: Array,   default: () => [] },
  mapId:        { type: String,  default: 'mapa-ruta' },
  buscador:     { type: Boolean, default: false },
  seleccionable: { type: Boolean, default: false },
})
const emit = defineEmits(['map-click'])

let mapa           = null
let polylineLayer  = null
let marcadores     = []

// ── Buscador de ciudad ─────────────────────────────────────────────────────
const q               = ref('')
const resultadosCiudad = ref([])
const buscandoCiudad   = ref(false)
let buscadorTimer      = null

function onBuscarCiudad(e) {
  q.value = e.target.value
  clearTimeout(buscadorTimer)
  if (!q.value.trim() || q.value.trim().length < 3) { resultadosCiudad.value = []; return }
  buscadorTimer = setTimeout(buscarCiudad, 500)
}

async function buscarCiudad() {
  buscandoCiudad.value = true
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q.value)}&countrycodes=cl&limit=5&accept-language=es`
    const res = await fetch(url)
    resultadosCiudad.value = res.ok ? await res.json() : []
  } catch {
    resultadosCiudad.value = []
  } finally {
    buscandoCiudad.value = false
  }
}

function irACiudad(r) {
  resultadosCiudad.value = []
  q.value = r.display_name?.split(',')[0]?.trim() || q.value
  if (!mapa) return
  const bb = r.boundingbox
  if (bb && bb.length === 4) {
    // boundingbox = [latMin, latMax, lngMin, lngMax]
    mapa.fitBounds([[parseFloat(bb[0]), parseFloat(bb[2])], [parseFloat(bb[1]), parseFloat(bb[3])]], { padding: [24, 24] })
  } else {
    mapa.setView([parseFloat(r.lat), parseFloat(r.lon)], 12)
  }
}

const COLORES = {
  origen:  '#1D9E75',
  parada:  '#378ADD',
  destino: '#E24B4A',
}

async function cargarLeaflet() {
  if (window.L) return
  await new Promise((resolve) => {
    const css    = document.createElement('link')
    css.rel      = 'stylesheet'
    css.href     = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(css)

    const script  = document.createElement('script')
    script.src    = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = resolve
    document.head.appendChild(script)
  })
}

function crearIcono(color) {
  return window.L.divIcon({
    className: '',
    html: `<svg width="28" height="36" viewBox="0 0 28 36" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 0C6.268 0 0 6.268 0 14c0 9.625 14 22 14 22S28 23.625 28 14C28 6.268 21.732 0 14 0z" fill="${color}"/>
      <circle cx="14" cy="14" r="6" fill="white"/>
    </svg>`,
    iconSize:    [28, 36],
    iconAnchor:  [14, 36],
    popupAnchor: [0, -38],
  })
}

function renderMapa() {
  if (!window.L || !mapa) return

  marcadores.forEach(m => mapa.removeLayer(m))
  marcadores = []
  if (polylineLayer) { mapa.removeLayer(polylineLayer); polylineLayer = null }

  const puntos = []

  if (props.polyline && props.polyline.length > 0) {
    polylineLayer = window.L.polyline(props.polyline, { color: '#378ADD', weight: 4, opacity: 0.85 }).addTo(mapa)
    props.polyline.forEach(p => puntos.push(p))
  }

  props.paradas.forEach(p => {
    if (!p.latitud || !p.longitud) return
    const color = COLORES[p.tipo] || COLORES.parada
    const m = window.L.marker([p.latitud, p.longitud], { icon: crearIcono(color) })
      .bindPopup(`<strong>${p.nombre || p.tipo}</strong>${p.direccion ? '<br><small>' + p.direccion + '</small>' : ''}`)
      .addTo(mapa)
    marcadores.push(m)
    puntos.push([p.latitud, p.longitud])
  })

  if (puntos.length > 1) {
    mapa.fitBounds(puntos, { padding: [24, 24] })
  } else if (puntos.length === 1) {
    mapa.setView(puntos[0], 13)
  } else {
    mapa.setView([-33.4489, -70.6693], 7)
  }
}

onMounted(async () => {
  await cargarLeaflet()
  const el = document.getElementById(props.mapId)
  if (!el) return
  mapa = window.L.map(el, { zoomControl: true }).setView([-33.4489, -70.6693], 7)
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapa)

  if (props.seleccionable) {
    mapa.on('click', (e) => emit('map-click', { lat: e.latlng.lat, lng: e.latlng.lng }))
  }

  renderMapa()
})

watch(() => [props.paradas, props.polyline], renderMapa, { deep: true })

onUnmounted(() => {
  clearTimeout(buscadorTimer)
  if (mapa) { mapa.remove(); mapa = null }
})

// Necesario cuando el mapa se monta dentro de un v-if: Leaflet no puede medir
// el contenedor hasta que sea visible. Llama esto después de que el DOM aparezca.
function invalidarTamano() {
  if (mapa) mapa.invalidateSize()
}

defineExpose({ invalidarTamano })
</script>

<style scoped>
.mapa-buscador {
  position: absolute;
  top: 8px;
  left: 50px;          /* deja espacio al control de zoom de Leaflet */
  right: 8px;
  z-index: 1100;
}
.mapa-buscador-box {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 0.5rem;
  padding: 0.4rem 0.6rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.mapa-buscador-icono { width: 15px; height: 15px; color: #9CA3AF; flex-shrink: 0; }
.mapa-buscador-input { flex: 1; border: none; outline: none; font-size: 0.8rem; color: #111827; background: transparent; }
.mapa-buscador-spinner {
  width: 13px; height: 13px; flex-shrink: 0;
  border: 2px solid #D1D5DB; border-top-color: #6366F1;
  border-radius: 50%; animation: mapa-spin 0.7s linear infinite;
}
@keyframes mapa-spin { to { transform: rotate(360deg); } }
.mapa-buscador-lista {
  margin-top: 0.25rem;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  max-height: 11rem;
  overflow-y: auto;
}
.mapa-buscador-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.7rem;
  font-size: 0.72rem;
  color: #374151;
  background: transparent;
  border: none;
  border-bottom: 1px solid #F3F4F6;
  cursor: pointer;
}
.mapa-buscador-item:hover { background: #EEF2FF; }
.mapa-buscador-item:last-child { border-bottom: none; }
</style>
