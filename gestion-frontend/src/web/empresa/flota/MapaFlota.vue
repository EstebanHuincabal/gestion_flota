<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { apiFetch, safeJsonParse } from '../../../utils/api.js'
import { getEmpresaActiva, useEmpresaNav } from '../../../utils/empresaActiva.js'
import SelectorEmpresa from '../../../components/SelectorEmpresa.vue'

const { ruta } = useEmpresaNav()

// ── Estado ────────────────────────────────────────────────────────────────────
const cargando  = ref(true)
const vehiculos = ref([])              // última posición conocida de cada vehículo
const conectado = ref(false)

// SUPERADMIN debe elegir una empresa antes de ver el mapa (sistema unificado).
const esSuperadmin = computed(() => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  return usuario.rol === 'SUPERADMIN'
})
const empresaActiva = ref(getEmpresaActiva())
const sinEmpresa = computed(() => esSuperadmin.value && !empresaActiva.value)

let mapa       = null
const marcadores = {}                  // vehiculo_id → L.marker
const rutasLayers = {}                 // vehiculo_id → L.polyline (trazado de la ruta activa)
const mostrarRutas = ref(true)         // toggle de visibilidad de las rutas
let ws          = null
let reconnectTimer = null
let reconnectDelay = 1000
let desmontado  = false

const COLORES = {
  movimiento: '#2563EB',   // azul
  detenido:   '#6B7280',   // gris
  sin_señal:  '#DC2626',   // rojo
}
const LABEL_ESTADO = {
  movimiento: 'En movimiento',
  detenido:   'Detenido',
  sin_señal:  'Sin señal',
}

function colorEstado(estado) {
  return COLORES[estado] || COLORES.sin_señal
}
function labelEstado(estado) {
  return LABEL_ESTADO[estado] || 'Sin señal'
}

// ── Panel lateral: selección y enfoque ────────────────────────────────────────
const seleccionado = ref(null)   // vehiculo_id actualmente enfocado

function enfocarVehiculo(v) {
  seleccionado.value = v.vehiculo_id
  resaltarRutaSeleccionada()
  if (!mapa || v.latitud == null || v.longitud == null) return
  mapa.setView([v.latitud, v.longitud], 15, { animate: true })
  const m = marcadores[v.vehiculo_id]
  if (m) m.openPopup()
}

// ── Rutas activas en el mapa ──────────────────────────────────────────────────
// Pin SVG para los puntos de inicio (verde) y fin (rojo) de cada ruta.
function crearIconoPunto(color) {
  return window.L.divIcon({
    className: '',
    html: `<svg width="24" height="31" viewBox="0 0 28 36" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 0C6.268 0 0 6.268 0 14c0 9.625 14 22 14 22S28 23.625 28 14C28 6.268 21.732 0 14 0z" fill="${color}"/>
      <circle cx="14" cy="14" r="5.5" fill="white"/>
    </svg>`,
    iconSize:    [24, 31],
    iconAnchor:  [12, 31],
    popupAnchor: [0, -32],
  })
}

function limpiarRutas() {
  for (const r of Object.values(rutasLayers)) {
    try {
      mapa?.removeLayer(r.linea)
      if (r.inicio) mapa?.removeLayer(r.inicio)
      if (r.fin)    mapa?.removeLayer(r.fin)
    } catch { /* noop */ }
  }
  for (const k of Object.keys(rutasLayers)) delete rutasLayers[k]
}

function dibujarRutas() {
  if (!mapa || !window.L) return
  limpiarRutas()
  if (!mostrarRutas.value) return

  for (const v of vehiculos.value) {
    if (!v.ruta_polyline || v.ruta_polyline.length < 2) continue

    // Trazado sólido azul
    const linea = window.L.polyline(v.ruta_polyline, {
      color: '#2563EB', weight: 4, opacity: 0.85,
    }).addTo(mapa)

    // Marcadores de inicio (verde) y fin (rojo)
    const pIni = v.ruta_polyline[0]
    const pFin = v.ruta_polyline[v.ruta_polyline.length - 1]
    const etiqueta = v.ruta_activa || 'Ruta'
    const inicio = window.L.marker(pIni, { icon: crearIconoPunto('#16A34A') })
      .bindPopup(`<strong>Inicio</strong><br><small>${etiqueta}</small>`)
      .addTo(mapa)
    const fin = window.L.marker(pFin, { icon: crearIconoPunto('#DC2626') })
      .bindPopup(`<strong>Destino</strong><br><small>${etiqueta}</small>`)
      .addTo(mapa)

    rutasLayers[v.vehiculo_id] = { linea, inicio, fin }
  }
  resaltarRutaSeleccionada()
}

// Resalta el trazado del vehículo seleccionado y atenúa el resto.
function resaltarRutaSeleccionada() {
  const hayseleccion = seleccionado.value != null
  for (const [id, r] of Object.entries(rutasLayers)) {
    const activo = String(id) === String(seleccionado.value)
    r.linea.setStyle({
      opacity: hayseleccion ? (activo ? 1 : 0.4) : 0.85,
      weight:  activo ? 6 : 4,
    })
    if (activo) r.linea.bringToFront()
  }
}

function toggleRutas() {
  mostrarRutas.value = !mostrarRutas.value
  dibujarRutas()
}

// Resumen de estados para el encabezado del panel
const resumen = computed(() => {
  const r = { movimiento: 0, detenido: 0, sin_señal: 0 }
  for (const v of vehiculos.value) r[v.estado] = (r[v.estado] || 0) + 1
  return r
})

// ── Leaflet ───────────────────────────────────────────────────────────────────
async function cargarLeaflet() {
  if (window.L) return
  await new Promise((resolve) => {
    const css  = document.createElement('link')
    css.rel    = 'stylesheet'
    css.href   = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(css)

    const script  = document.createElement('script')
    script.src    = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = resolve
    document.head.appendChild(script)
  })
}

function iconoVehiculo(estado) {
  const color = colorEstado(estado)
  return window.L.divIcon({
    className: '',
    html: `<svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg">
      <circle cx="15" cy="15" r="11" fill="${color}" stroke="white" stroke-width="3"/>
      <path d="M9 17a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM24 17a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" fill="white"/>
      <path d="M8 16v-3a1 1 0 011-1h7l3 2v2" stroke="white" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    iconSize:    [30, 30],
    iconAnchor:  [15, 15],
    popupAnchor: [0, -16],
  })
}

function tiempoRelativo(iso) {
  if (!iso) return '—'
  const seg = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (seg < 60)   return `hace ${seg} s`
  if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`
  return `hace ${Math.floor(seg / 3600)} h`
}

function popupHtml(v) {
  const nombre   = [v.marca, v.modelo].filter(Boolean).join(' ')
  const conductor = v.tiene_conductor ? (v.conductor_nombre || 'Asignado') : 'Sin conductor'
  return `<div style="min-width:160px">
    <strong>${v.patente}</strong>${nombre ? ' — ' + nombre : ''}<br>
    <span style="color:#6B7280;font-size:12px">
      Velocidad: ${Math.round(v.velocidad || 0)} km/h<br>
      Conductor: ${conductor}<br>
      Última señal: ${tiempoRelativo(v.timestamp)}
    </span>
  </div>`
}

function pintarMarcador(v) {
  if (!mapa || !window.L) return
  if (v.latitud == null || v.longitud == null) return

  const existente = marcadores[v.vehiculo_id]
  if (existente) {
    existente.setLatLng([v.latitud, v.longitud])
    existente.setIcon(iconoVehiculo(v.estado))
    existente.getPopup()?.setContent(popupHtml(v))
  } else {
    const m = window.L.marker([v.latitud, v.longitud], { icon: iconoVehiculo(v.estado) })
      .bindPopup(popupHtml(v))
      .addTo(mapa)
    marcadores[v.vehiculo_id] = m
  }
}

// ── Carga inicial / refresco ──────────────────────────────────────────────────
// `ajustar` solo en la carga inicial; en refrescos en vivo no movemos la vista.
async function cargarPosiciones(ajustar = true) {
  try {
    const res = await apiFetch('/api/empresa/gps/vehiculos/posicion/')
    if (res.ok) {
      const data = await res.json()
      vehiculos.value = data.vehiculos || []
      vehiculos.value.forEach(pintarMarcador)
      dibujarRutas()
      if (ajustar) ajustarVista()
    }
  } catch { /* manejado por apiFetch */ }
}

function ajustarVista() {
  const puntos = vehiculos.value
    .filter(v => v.latitud != null && v.longitud != null)
    .map(v => [v.latitud, v.longitud])
  if (puntos.length > 1) mapa.fitBounds(puntos, { padding: [40, 40] })
  else if (puntos.length === 1) mapa.setView(puntos[0], 14)
}

// ── WebSocket tiempo real ─────────────────────────────────────────────────────
function empresaIdActual() {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  if (usuario.rol === 'SUPERADMIN') {
    return safeJsonParse(sessionStorage.getItem('empresaActiva'), null)?.id || null
  }
  return usuario.empresa_id || null
}

function conectarWS() {
  if (desmontado) return
  const empresaId = empresaIdActual()
  const token     = localStorage.getItem('access_token')
  if (!empresaId || !token) return

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/gps/${empresaId}/?token=${token}`)

  ws.onopen = () => {
    conectado.value = true
    reconnectDelay  = 1000
  }

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.type === 'position_update') {
        // Actualizar la lista reactiva (para conservar marca/modelo/conductor del
        // estado inicial) y repintar el marcador.
        const idx = vehiculos.value.findIndex(v => v.vehiculo_id === msg.vehiculo_id)
        const estado = (msg.velocidad || 0) > 2 ? 'movimiento' : 'detenido'
        if (idx >= 0) {
          vehiculos.value[idx] = {
            ...vehiculos.value[idx],
            latitud:   msg.latitud,
            longitud:  msg.longitud,
            velocidad: msg.velocidad,
            timestamp: msg.timestamp,
            estado,
          }
          pintarMarcador(vehiculos.value[idx])
        } else {
          const nuevo = {
            vehiculo_id: msg.vehiculo_id,
            patente:     msg.patente,
            marca:       '', modelo: '',
            latitud:     msg.latitud,
            longitud:    msg.longitud,
            velocidad:   msg.velocidad,
            timestamp:   msg.timestamp,
            tiene_conductor: false,
            conductor_nombre: null,
            estado,
          }
          vehiculos.value.push(nuevo)
          pintarMarcador(nuevo)
        }
      } else if (msg.type === 'rutas_cambiadas') {
        // Alguna ruta se inició/finalizó/canceló: recargar trazados sin mover la vista.
        cargarPosiciones(false)
      }
    } catch { /* ignorar mensajes mal formados */ }
  }

  ws.onclose = () => {
    conectado.value = false
    if (desmontado) return
    clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(conectarWS, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, 30000)
  }

  ws.onerror = () => {
    try { ws.close() } catch { /* noop */ }
  }
}

// ── Cambio de empresa (SUPERADMIN) ────────────────────────────────────────────
function limpiarMarcadores() {
  Object.values(marcadores).forEach(m => { try { mapa?.removeLayer(m) } catch { /* noop */ } })
  for (const k of Object.keys(marcadores)) delete marcadores[k]
  limpiarRutas()
  vehiculos.value = []
  seleccionado.value = null
}

// Crea el mapa Leaflet si aún no existe y su contenedor está en el DOM.
// Necesario porque el contenedor vive dentro de un v-else: para SUPERADMIN
// sin empresa no existe al montar, sino al elegir empresa.
async function inicializarMapa() {
  if (mapa) return
  await cargarLeaflet()
  await nextTick()
  const el = document.getElementById('mapa-flota')
  if (!el) return
  mapa = window.L.map(el, { zoomControl: true }).setView([-33.45, -70.65], 12)
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapa)
  // El contenedor vive en un layout flex; aseguramos que Leaflet remida tras el render.
  await nextTick()
  setTimeout(() => { try { mapa?.invalidateSize() } catch { /* noop */ } }, 100)
}

async function onCambioEmpresa(empresa) {
  empresaActiva.value = empresa
  // Cerrar WS anterior y limpiar el mapa
  clearTimeout(reconnectTimer)
  reconnectDelay = 1000
  if (ws) { try { ws.close() } catch { /* noop */ } ; ws = null }
  conectado.value = false
  limpiarMarcadores()

  if (!empresa) { cargando.value = false; return }

  cargando.value = true
  await inicializarMapa()
  await cargarPosiciones()
  cargando.value = false
  conectarWS()
}

// ── Ciclo de vida ─────────────────────────────────────────────────────────────
onMounted(async () => {
  // SUPERADMIN sin empresa: el mapa se inicializa al elegir una.
  if (sinEmpresa.value) {
    cargando.value = false
    return
  }
  await inicializarMapa()
  await cargarPosiciones()
  cargando.value = false
  conectarWS()
})

onUnmounted(() => {
  desmontado = true
  clearTimeout(reconnectTimer)
  if (ws) { try { ws.close() } catch { /* noop */ } ; ws = null }
  if (mapa) { mapa.remove(); mapa = null }
})
</script>

<template>
  <div class="p-6 max-w-[1500px] mx-auto">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-800">Mapa de flota</h1>
        <p class="text-sm text-gray-500">Posición de los vehículos con GPS en tiempo real.</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-1.5 text-xs font-medium"
          :class="conectado ? 'text-green-600' : 'text-gray-400'">
          <span :class="['w-2 h-2 rounded-full', conectado ? 'bg-green-500' : 'bg-gray-300']"></span>
          {{ conectado ? 'En vivo' : 'Reconectando...' }}
        </span>
        <button @click="toggleRutas"
          :class="['px-3 py-2 text-sm font-semibold rounded-lg border transition flex items-center gap-1.5',
                   mostrarRutas ? 'border-indigo-300 text-indigo-700 bg-indigo-50' : 'border-gray-200 text-gray-500 bg-white']">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
          {{ mostrarRutas ? 'Rutas visibles' : 'Rutas ocultas' }}
        </button>
        <router-link :to="ruta('/gps')"
          class="px-4 py-2 text-sm font-semibold rounded-lg border border-indigo-200 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition">
          Gestionar GPS
        </router-link>
      </div>
    </div>

    <!-- Selector de empresa (solo SUPERADMIN) -->
    <SelectorEmpresa @cambio="onCambioEmpresa" />

    <!-- Estado vacío: SUPERADMIN sin empresa seleccionada -->
    <div v-if="sinEmpresa" class="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
      <p class="text-gray-500">Selecciona una empresa para ver su flota en el mapa.</p>
    </div>

    <template v-else>
    <div class="flex gap-4" style="height: 72vh;">

      <!-- ── Panel lateral de vehículos ─────────────────────────────────────── -->
      <aside class="w-80 shrink-0 flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <!-- Resumen -->
        <div class="px-4 py-3 border-b border-gray-100">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-sm font-bold text-gray-700">Vehículos</h2>
            <span class="text-xs text-gray-400">{{ vehiculos.length }} con GPS</span>
          </div>
          <div class="flex gap-3 text-xs">
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#2563EB"></span>{{ resumen.movimiento }}</span>
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#6B7280"></span>{{ resumen.detenido }}</span>
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#DC2626"></span>{{ resumen.sin_señal }}</span>
          </div>
        </div>

        <!-- Lista -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="cargando" class="p-4 space-y-2">
            <div v-for="i in 4" :key="i" class="h-16 bg-gray-100 rounded-lg animate-pulse"></div>
          </div>

          <div v-else-if="!vehiculos.length" class="p-6 text-center text-sm text-gray-400">
            No hay vehículos con GPS activo y posición registrada.
          </div>

          <button
            v-for="v in vehiculos"
            :key="v.vehiculo_id"
            @click="enfocarVehiculo(v)"
            :class="['w-full text-left px-4 py-3 border-b border-gray-50 transition hover:bg-gray-50',
                     seleccionado === v.vehiculo_id ? 'bg-indigo-50/70' : '']"
          >
            <div class="flex items-center gap-2 mb-1">
              <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ background: colorEstado(v.estado) }"></span>
              <span class="font-semibold text-gray-800 text-sm">{{ v.patente }}</span>
              <span class="text-xs text-gray-400 truncate">{{ [v.marca, v.modelo].filter(Boolean).join(' ') }}</span>
            </div>
            <div class="pl-[1.1rem] space-y-0.5">
              <div class="flex items-center justify-between text-xs">
                <span class="text-gray-500">{{ labelEstado(v.estado) }}</span>
                <span class="font-semibold text-gray-700">{{ Math.round(v.velocidad || 0) }} km/h</span>
              </div>
              <div class="text-xs text-gray-500 flex items-center gap-1">
                <svg class="w-3 h-3 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                {{ v.tiene_conductor ? (v.conductor_nombre || 'Asignado') : 'Sin conductor' }}
              </div>
              <div v-if="v.ruta_activa" class="text-xs text-indigo-600 flex items-center gap-1 truncate">
                <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
                <span class="truncate">{{ v.ruta_activa }}</span>
              </div>
              <div class="text-[11px] text-gray-400">Última señal: {{ tiempoRelativo(v.timestamp) }}</div>
            </div>
          </button>
        </div>
      </aside>

      <!-- ── Mapa ───────────────────────────────────────────────────────────── -->
      <div class="relative flex-1 rounded-xl overflow-hidden border border-gray-200 shadow-sm">
        <div v-if="cargando" class="absolute inset-0 z-[5] flex items-center justify-center bg-gray-50/80">
          <span class="text-sm text-gray-500">Cargando mapa...</span>
        </div>
        <div id="mapa-flota" style="height: 100%; width: 100%;"></div>
      </div>

    </div>
    </template>
  </div>
</template>
