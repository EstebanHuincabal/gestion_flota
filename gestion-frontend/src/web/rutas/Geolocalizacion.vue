<template>
  <div class="h-full flex flex-col bg-gray-50 overflow-hidden">

    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-6 py-3 flex flex-wrap gap-4 justify-between items-center shrink-0">
      <div>
        <h1 class="text-xl font-bold text-gray-900 flex items-center gap-2">
          Geolocalización en tiempo real
          <span v-if="conectado" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>En vivo
          </span>
          <span v-else class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>Reconectando...
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-0.5">Última actualización: {{ tiempoDesdeActualizacion }}</p>
      </div>

      <!-- KPI cards -->
      <div class="flex gap-2 flex-wrap">
        <button v-for="(item, key) in FILTROS" :key="key" @click="filtroActivo = key"
          :class="['border rounded-lg px-3 py-1.5 flex flex-col items-center min-w-[76px] text-xs transition',
            filtroActivo === key ? 'ring-2 bg-white ' + item.ring : 'bg-white border-gray-200 hover:bg-gray-50']">
          <span class="text-lg font-bold" :class="item.color">{{ resumen[key] ?? 0 }}</span>
          <span class="text-gray-500">{{ item.label }}</span>
        </button>
      </div>
    </header>

    <!-- Error de carga -->
    <div v-if="errorCarga" class="flex-1 flex items-center justify-center text-center p-8">
      <div>
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4"/>
        </svg>
        <p class="text-gray-600 font-medium mb-1">Módulo no disponible</p>
        <p class="text-sm text-gray-400">{{ errorCarga }}</p>
      </div>
    </div>

    <div v-else class="flex-1 flex overflow-hidden relative">

      <!-- Lista vehículos -->
      <div class="w-72 xl:w-80 flex flex-col bg-white border-r border-gray-200 shrink-0">
        <!-- Buscador -->
        <div class="p-3 border-b border-gray-100">
          <input v-model="busqueda" type="text" placeholder="Buscar patente o conductor..."
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400"/>
        </div>

        <!-- Cards -->
        <div class="flex-1 overflow-y-auto divide-y divide-gray-50">
          <button v-for="v in vehiculosFiltrados" :key="v.id"
            @click="seleccionarVehiculo(v)"
            :class="['w-full text-left p-3 transition hover:bg-gray-50',
              vehiculoSeleccionado?.id === v.id ? 'bg-indigo-50 border-l-2 border-indigo-500' : '']">
            <div class="flex items-center gap-2 mb-1">
              <span :class="['w-2.5 h-2.5 rounded-full shrink-0', claseColor(v.estado, true)]"></span>
              <span class="font-bold text-gray-900 text-sm">{{ v.patente }}</span>
              <span class="text-gray-400 text-xs truncate">{{ v.marca }} {{ v.modelo }}</span>
            </div>
            <div class="text-xs text-gray-600 mb-0.5">{{ v.conductor || 'Sin conductor asignado' }}</div>
            <div class="flex items-center gap-3 text-xs text-gray-500">
              <span>{{ Math.round(v.ultima_ubicacion?.velocidad ?? 0) }} km/h</span>
            </div>
            <div v-if="v.ruta_activa" class="mt-1 text-xs text-indigo-600 truncate">
              ● {{ v.ruta_activa.nombre }}
            </div>
            <div v-if="v.ultima_ubicacion?.timestamp" class="mt-0.5 text-xs text-gray-400">
              {{ tiempoDesde(v.ultima_ubicacion.timestamp) }}
            </div>
          </button>
          <div v-if="!vehiculosFiltrados.length" class="p-6 text-center text-gray-400 text-sm">Sin vehículos</div>
        </div>
      </div>

      <!-- Mapa -->
      <div id="mapa-geolocalizacion" class="flex-1"></div>

      <!-- Panel detalle -->
      <Transition name="slide">
        <div v-if="vehiculoSeleccionado"
          class="absolute top-0 right-0 bottom-0 w-80 bg-white shadow-2xl border-l border-gray-200 z-[1200] flex flex-col overflow-hidden">
          <!-- Header panel -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <div>
              <h2 class="font-bold text-gray-900">{{ vehiculoSeleccionado.patente }}</h2>
              <p class="text-xs text-gray-400">{{ vehiculoSeleccionado.marca }} {{ vehiculoSeleccionado.modelo }}</p>
            </div>
            <button @click="vehiculoSeleccionado = null" class="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
            <!-- Estado -->
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg"
              :style="{ background: COLORES[vehiculoSeleccionado.estado] + '18' }">
              <span class="w-2.5 h-2.5 rounded-full" :class="claseColor(vehiculoSeleccionado.estado, true)"></span>
              <span class="font-semibold" :style="{ color: COLORES[vehiculoSeleccionado.estado] }">
                {{ labelEstado(vehiculoSeleccionado.estado) }}
              </span>
            </div>

            <!-- Datos -->
            <div class="bg-gray-50 rounded-lg p-3 space-y-2">
              <div class="flex justify-between text-xs">
                <span class="text-gray-400">Conductor</span>
                <span class="font-medium text-gray-800">{{ vehiculoSeleccionado.conductor || '—' }}</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-gray-400">Velocidad</span>
                <span class="font-medium text-gray-800">{{ Math.round(vehiculoSeleccionado.ultima_ubicacion?.velocidad ?? 0) }} km/h</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-gray-400">Última señal</span>
                <span class="font-medium text-gray-800">{{ vehiculoSeleccionado.ultima_ubicacion ? tiempoDesde(vehiculoSeleccionado.ultima_ubicacion.timestamp) : '—' }}</span>
              </div>
              <div v-if="vehiculoSeleccionado.ultima_ubicacion" class="flex justify-between text-xs">
                <span class="text-gray-400">Coordenadas</span>
                <span class="font-mono text-gray-600">
                  {{ vehiculoSeleccionado.ultima_ubicacion.latitud?.toFixed(4) }},
                  {{ vehiculoSeleccionado.ultima_ubicacion.longitud?.toFixed(4) }}
                </span>
              </div>
            </div>

            <!-- Ruta activa -->
            <div v-if="vehiculoSeleccionado.ruta_activa" class="border border-indigo-100 rounded-lg overflow-hidden">
              <div class="bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-700 border-b border-indigo-100">
                Ruta activa
              </div>
              <div class="p-3 space-y-2">
                <p class="font-semibold text-gray-900 text-sm">{{ vehiculoSeleccionado.ruta_activa.nombre }}</p>
                <template v-if="vehiculoSeleccionado.ruta_activa.paradas.length >= 2">
                  <div class="flex items-center gap-2 text-xs text-gray-600">
                    <span class="w-2 h-2 rounded-full bg-green-500 shrink-0"></span>
                    {{ vehiculoSeleccionado.ruta_activa.paradas[0]?.nombre || '—' }}
                  </div>
                  <div class="flex items-center gap-2 text-xs text-gray-600">
                    <span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
                    {{ vehiculoSeleccionado.ruta_activa.paradas[vehiculoSeleccionado.ruta_activa.paradas.length - 1]?.nombre || '—' }}
                  </div>
                </template>
              </div>
            </div>

            <!-- Sin ubicación -->
            <div v-if="!vehiculoSeleccionado.ultima_ubicacion"
              class="text-xs text-gray-400 bg-gray-50 rounded-lg p-3 text-center">
              Sin datos de ubicación recientes
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { apiFetch } from '../../utils/api.js'

const COLORES = {
  en_ruta:       '#1D9E75',
  en_movimiento: '#378ADD',
  detenido:      '#EF9F27',
  sin_señal:     '#9CA3AF',
}

const FILTROS = {
  total:         { label: 'Todos',      color: 'text-gray-800',   ring: 'ring-gray-400'   },
  en_ruta:       { label: 'En ruta',    color: 'text-green-600',  ring: 'ring-green-500'  },
  en_movimiento: { label: 'En movim.',  color: 'text-blue-600',   ring: 'ring-blue-400'   },
  detenido:      { label: 'Detenidos',  color: 'text-orange-500', ring: 'ring-orange-400' },
  sin_señal:     { label: 'Sin señal',  color: 'text-gray-500',   ring: 'ring-gray-400'   },
}

const vehiculos            = ref([])
const resumen              = ref({ total: 0, en_ruta: 0, en_movimiento: 0, detenido: 0, sin_señal: 0 })
const busqueda             = ref('')
const filtroActivo         = ref('total')
const vehiculoSeleccionado = ref(null)
const conectado            = ref(false)
const ultimaActualizacion  = ref(null)
const tiempoDesdeActualizacion = ref('—')
const errorCarga           = ref('')

let mapaInstance    = null
let intervaloTiempo = null
let ws              = null
const markers    = {}
const trailLines = {}
const trails     = {}
const rutaLines  = {}
const estadosAnteriores = {}

const vehiculosFiltrados = computed(() => {
  const q = busqueda.value.toLowerCase()
  return vehiculos.value.filter(v => {
    const matchFiltro = filtroActivo.value === 'total' || v.estado === filtroActivo.value
    const matchQ = !q || v.patente.toLowerCase().includes(q) || (v.conductor || '').toLowerCase().includes(q)
    return matchFiltro && matchQ
  })
})

function labelEstado(e) {
  return { en_ruta: 'En ruta', en_movimiento: 'En movimiento', detenido: 'Detenido', sin_señal: 'Sin señal' }[e] || e
}

function claseColor(estado, pulso = false) {
  const base = { en_ruta: 'bg-green-500', en_movimiento: 'bg-blue-500', detenido: 'bg-orange-400', sin_señal: 'bg-gray-400' }
  return (base[estado] || 'bg-gray-400') + (pulso && ['en_ruta', 'en_movimiento'].includes(estado) ? ' animate-pulse' : '')
}


function tiempoDesde(ts) {
  if (!ts) return '—'
  const s = Math.floor((Date.now() - new Date(ts)) / 1000)
  if (s < 60)   return `hace ${s}s`
  if (s < 3600) return `hace ${Math.floor(s / 60)}min`
  return `hace ${Math.floor(s / 3600)}h`
}

function toast(msg, tipo = 'info') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { msg, tipo } }))
}

// ── Leaflet ──────────────────────────────────────────────────────────────────
async function cargarLeaflet() {
  if (window.L) return
  await new Promise(resolve => {
    if (!document.querySelector('link[href*="leaflet.css"]')) {
      const css = document.createElement('link')
      css.rel = 'stylesheet'
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      document.head.appendChild(css)
    }
    const s = document.createElement('script')
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    s.onload = resolve
    document.head.appendChild(s)
  })
}

const ICONO_ORIGEN  = '#1D9E75'
const ICONO_DESTINO = '#E24B4A'

function crearIconoVehiculo(v) {
  const color = COLORES[v.estado] || COLORES.sin_señal
  return window.L.divIcon({
    className: '',
    html: `<svg width="36" height="44" viewBox="0 0 36 44" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 0C8.1 0 0 8.1 0 18c0 13.5 18 26 18 26S36 31.5 36 18C36 8.1 27.9 0 18 0z"
        fill="${color}" stroke="white" stroke-width="2"/>
      <text x="18" y="23" text-anchor="middle" fill="white" font-size="9" font-weight="bold" font-family="Arial">
        ${v.patente.slice(-4)}
      </text></svg>`,
    iconSize: [36, 44], iconAnchor: [18, 44], popupAnchor: [0, -46],
  })
}

function crearIconoPunto(color) {
  return window.L.divIcon({
    className: '',
    html: `<svg width="14" height="14" viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7" cy="7" r="6" fill="${color}" stroke="white" stroke-width="2"/></svg>`,
    iconSize: [14, 14], iconAnchor: [7, 7],
  })
}

function popupVehiculo(v) {
  const vel = Math.round(v.ultima_ubicacion?.velocidad ?? 0)
  const ts  = v.ultima_ubicacion ? tiempoDesde(v.ultima_ubicacion.timestamp) : '—'
  return `<div style="font-family:system-ui;font-size:13px;min-width:160px">
    <div style="font-weight:700;margin-bottom:3px">${v.patente} — ${v.marca}</div>
    <div style="color:${COLORES[v.estado]};font-weight:600;margin-bottom:4px">${labelEstado(v.estado)}</div>
    ${v.conductor ? `<div>Conductor: ${v.conductor}</div>` : ''}
    <div>Velocidad: ${vel} km/h</div>
    <div style="color:#9CA3AF;font-size:11px;margin-top:3px">Última señal: ${ts}</div>
  </div>`
}

function inicializarMapa() {
  const el = document.getElementById('mapa-geolocalizacion')
  if (!el || mapaInstance) return
  mapaInstance = window.L.map(el, { zoomControl: false }).setView([-33.4489, -70.6693], 6)
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors', maxZoom: 19,
  }).addTo(mapaInstance)
  window.L.control.zoom({ position: 'bottomright' }).addTo(mapaInstance)

  const bounds = window.L.latLngBounds()
  let hay = false
  vehiculos.value.forEach(v => {
    if (v.ultima_ubicacion) { bounds.extend([v.ultima_ubicacion.latitud, v.ultima_ubicacion.longitud]); hay = true }
  })
  if (hay) mapaInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
}

function dibujarRuta(v) {
  if (!mapaInstance || !v.ruta_activa) return
  const polyline = v.ruta_activa.polyline
  if (polyline && polyline.length > 1) {
    rutaLines[v.id] = window.L.polyline(polyline, {
      color: '#3B82F6', weight: 3, opacity: 0.7, dashArray: '8 4',
    }).addTo(mapaInstance)
  }
  // Marcadores origen/destino
  const paradas = v.ruta_activa.paradas || []
  const origen  = paradas.find(p => p.tipo === 'origen')
  const destino = paradas.find(p => p.tipo === 'destino')
  if (origen?.latitud) window.L.marker([origen.latitud, origen.longitud], { icon: crearIconoPunto(ICONO_ORIGEN)  }).bindPopup(`Origen: ${origen.nombre}`).addTo(mapaInstance)
  if (destino?.latitud) window.L.marker([destino.latitud, destino.longitud], { icon: crearIconoPunto(ICONO_DESTINO) }).bindPopup(`Destino: ${destino.nombre}`).addTo(mapaInstance)
}

function agregarMarcador(v) {
  if (!mapaInstance || !v.ultima_ubicacion) return
  const { latitud: lat, longitud: lng } = v.ultima_ubicacion
  const m = window.L.marker([lat, lng], { icon: crearIconoVehiculo(v) })
    .bindPopup(popupVehiculo(v))
    .addTo(mapaInstance)
  m.on('click', () => seleccionarVehiculo(v))
  markers[v.id] = m
  estadosAnteriores[v.id] = v.estado
  agregarTrail(v.id, lat, lng)
  dibujarRuta(v)
}

function agregarTrail(id, lat, lng) {
  if (!trails[id]) trails[id] = []
  trails[id].push([lat, lng])
  if (trails[id].length > 5) trails[id].shift()
  if (!mapaInstance) return
  if (trailLines[id]) {
    trailLines[id].setLatLngs(trails[id])
  } else {
    const v = vehiculos.value.find(x => x.id === id)
    trailLines[id] = window.L.polyline(trails[id], {
      color: COLORES[v?.estado] || '#9CA3AF', weight: 3, opacity: 0.35, dashArray: '4 4',
    }).addTo(mapaInstance)
  }
}

function animarMarcador(marker, lat, lng, ms = 900) {
  const ini = marker.getLatLng(), t0 = Date.now()
  const step = () => {
    const t = Math.min((Date.now() - t0) / ms, 1)
    marker.setLatLng([ini.lat + (lat - ini.lat) * t, ini.lng + (lng - ini.lng) * t])
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function actualizarVehiculo(data) {
  const idx = vehiculos.value.findIndex(v => v.id === data.vehiculo_id)
  if (idx === -1) return
  const v = vehiculos.value[idx]
  const anterior = estadosAnteriores[data.vehiculo_id]
  if (anterior && anterior !== data.estado) {
    if (anterior === 'en_ruta'   && data.estado === 'detenido')  toast(`${v.patente} se detuvo en ruta`, 'advertencia')
    if (anterior !== 'sin_señal' && data.estado === 'sin_señal') toast(`${v.patente} perdió señal GPS`, 'error')
    if (anterior === 'sin_señal' && data.estado !== 'sin_señal') toast(`${v.patente} recuperó señal GPS`, 'exito')
  }
  estadosAnteriores[data.vehiculo_id] = data.estado
  vehiculos.value[idx].ultima_ubicacion = {
    latitud: data.latitud, longitud: data.longitud,
    velocidad: data.velocidad,
    timestamp: data.timestamp,
  }
  vehiculos.value[idx].estado = data.estado
  calcularResumen()

  const marker = markers[data.vehiculo_id]
  if (marker) {
    if (anterior !== data.estado) {
      marker.setIcon(crearIconoVehiculo(vehiculos.value[idx]))
      marker.setPopupContent(popupVehiculo(vehiculos.value[idx]))
      if (trailLines[data.vehiculo_id]) trailLines[data.vehiculo_id].setStyle({ color: COLORES[data.estado] || '#9CA3AF' })
    }
    animarMarcador(marker, data.latitud, data.longitud)
    agregarTrail(data.vehiculo_id, data.latitud, data.longitud)
  } else {
    agregarMarcador(vehiculos.value[idx])
  }

  if (vehiculoSeleccionado.value?.id === data.vehiculo_id) {
    vehiculoSeleccionado.value = { ...vehiculos.value[idx] }
  }
}

function calcularResumen() {
  const r = { total: vehiculos.value.length, en_ruta: 0, en_movimiento: 0, detenido: 0, sin_señal: 0 }
  vehiculos.value.forEach(v => { if (r[v.estado] !== undefined) r[v.estado]++ })
  resumen.value = r
}

function seleccionarVehiculo(v) {
  vehiculoSeleccionado.value = v
  if (mapaInstance && v.ultima_ubicacion) {
    mapaInstance.flyTo([v.ultima_ubicacion.latitud, v.ultima_ubicacion.longitud], 15, { duration: 1.2 })
  }
}

// ── WebSocket ──────────────────────────────────────────────────────────────
function conectarWS(empresaId) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host  = import.meta.env.DEV ? 'localhost:8000' : window.location.host
  const token = localStorage.getItem('access_token') || ''
  ws = new WebSocket(`${proto}://${host}/ws/geolocalizacion/${empresaId}/?token=${token}`)
  ws.onopen    = () => { conectado.value = true }
  ws.onmessage = e => {
    const msg = JSON.parse(e.data)
    if (msg.tipo === 'ubicacion_update') {
      actualizarVehiculo(msg.data)
      ultimaActualizacion.value = new Date()
    }
  }
  ws.onclose  = () => { conectado.value = false; setTimeout(() => conectarWS(empresaId), 5000) }
  ws.onerror  = () => ws.close()
}

onMounted(async () => {
  await cargarLeaflet()
  try {
    const res = await apiFetch('/api/empresa/geolocalizacion/')
    if (!res.ok) throw new Error(`${res.status}`)
    const data = await res.json()
    vehiculos.value = data.vehiculos || []
    calcularResumen()
    await nextTick()
    inicializarMapa()
    vehiculos.value.forEach(v => agregarMarcador(v))
  } catch (e) {
    errorCarga.value = 'No se pudieron cargar los datos de geolocalización. Verifica que el módulo esté habilitado en tu plan.'
    await nextTick()
    inicializarMapa()
  }

  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.empresa_id) conectarWS(usuario.empresa_id)

  intervaloTiempo = setInterval(() => {
    if (!ultimaActualizacion.value) return
    const s = Math.floor((Date.now() - ultimaActualizacion.value) / 1000)
    tiempoDesdeActualizacion.value = s < 60 ? `hace ${s}s` : `hace ${Math.floor(s / 60)}min`
  }, 1000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (mapaInstance) { mapaInstance.remove(); mapaInstance = null }
  if (intervaloTiempo) clearInterval(intervaloTiempo)
})
</script>

<style scoped>
#mapa-geolocalizacion { height: 100%; width: 100%; }
.slide-enter-active, .slide-leave-active { transition: transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
