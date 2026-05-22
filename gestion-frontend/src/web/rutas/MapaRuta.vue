<template>
  <div :id="mapId" style="height: 100%; width: 100%; border-radius: 0.5rem; z-index: 0;"></div>
</template>

<script setup>
import { onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  paradas:  { type: Array,  default: () => [] },
  polyline: { type: Array,  default: () => [] },
  peajes:   { type: Array,  default: () => [] },
  mapId:    { type: String, default: 'mapa-ruta' },
})

let mapa           = null
let polylineLayer  = null
let marcadores     = []

const COLORES = {
  origen:  '#1D9E75',
  parada:  '#378ADD',
  destino: '#E24B4A',
  peaje:   '#EF9F27',
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

function crearIconoPeaje() {
  return window.L.divIcon({
    className: '',
    html: `<svg width="26" height="26" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg">
      <circle cx="13" cy="13" r="13" fill="${COLORES.peaje}"/>
      <text x="13" y="18" text-anchor="middle" font-size="14" font-weight="bold" fill="white" font-family="sans-serif">$</text>
    </svg>`,
    iconSize:    [26, 26],
    iconAnchor:  [13, 13],
    popupAnchor: [0, -14],
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

  props.peajes.forEach(p => {
    if (!p.latitud || !p.longitud) return
    const m = window.L.marker([p.latitud, p.longitud], { icon: crearIconoPeaje() })
      .bindPopup(`<strong>${p.nombre}</strong><br>$${Number(p.tarifa).toLocaleString('es-CL')}`)
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
  renderMapa()
})

watch(() => [props.paradas, props.polyline, props.peajes], renderMapa, { deep: true })

onUnmounted(() => {
  if (mapa) { mapa.remove(); mapa = null }
})
</script>
