<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRutasStore } from '@/stores/rutas.js'
import { apiFetch }      from '@/services/api.js'
import BottomNav  from '@/components/BottomNav.vue'
import MapaRuta   from '@/components/MapaRuta.vue'
import { formatDuracion, formatFechaRuta } from '@/utils/formato.js'

const vueRoute   = useRoute()
const router     = useRouter()
const rutasStore = useRutasStore()

const rutaId   = computed(() => Number(vueRoute.params.id))
const ruta     = ref(null)
const cargando = ref(true)
const errorMsg = ref('')

// ── Tabs ─────────────────────────────────────────────────────────────────────
const tab = ref('ruta') // 'ruta' | 'detalles' | 'historial'

// ── Modales ───────────────────────────────────────────────────────────────────
const modalIniciar   = ref(false)
const modalFinalizar = ref(false)
const kmInicio       = ref('')
const kmFin          = ref('')
const procesando     = ref(false)
const errorModal     = ref('')

// ── Navegación externa (Google Maps / Waze) ──────────────────────────────────
const menuNavegar = ref(false)

// Paradas con coordenadas, ordenadas (origen → intermedias → destino).
const paradasOrdenadas = computed(() =>
  (ruta.value?.paradas || [])
    .filter(p => p.latitud != null && p.longitud != null)
    .slice()
    .sort((a, b) => a.orden - b.orden)
)
const tieneCoordsNavegacion = computed(() => paradasOrdenadas.value.length >= 1)

// Abre una URL en la app externa del sistema (no in-app browser).
function abrirExterno(url) {
  window.open(url, '_system')
}

// Google Maps: ruta completa con paradas. Origen = 1ª, destino = última,
// intermedias como waypoints.
function navegarGoogleMaps() {
  menuNavegar.value = false
  const ps = paradasOrdenadas.value
  if (!ps.length) return
  const destino = ps[ps.length - 1]
  let url = `https://www.google.com/maps/dir/?api=1&destination=${destino.latitud},${destino.longitud}&travelmode=driving`
  if (ps.length >= 2) {
    url += `&origin=${ps[0].latitud},${ps[0].longitud}`
    const waypoints = ps.slice(1, -1)
    if (waypoints.length) {
      url += '&waypoints=' + waypoints.map(p => `${p.latitud},${p.longitud}`).join('|')
    }
  }
  abrirExterno(url)
}

// Waze: solo soporta un destino → navega al destino final.
function navegarWaze() {
  menuNavegar.value = false
  const ps = paradasOrdenadas.value
  if (!ps.length) return
  const destino = ps[ps.length - 1]
  abrirExterno(`https://waze.com/ul?ll=${destino.latitud},${destino.longitud}&navigate=yes`)
}

// ── Toast ─────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', ok: true })
let   toastTimer = null

function mostrarToast(mensaje, ok = true) {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, ok }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3000)
}

// ── Historial / comentarios ───────────────────────────────────────────────────
const eventos           = ref([])
const cargandoEventos   = ref(false)
const nuevoComentario   = ref('')
const enviandoComentario = ref(false)

async function cargarEventos() {
  if (!rutaId.value) return
  cargandoEventos.value = true
  try {
    const data = await apiFetch(`/api/conductor/rutas/${rutaId.value}/comentarios/`)
    if (Array.isArray(data)) eventos.value = data
  } catch {
    // Fallo silencioso
  } finally {
    cargandoEventos.value = false
  }
}

async function enviarComentario() {
  if (!nuevoComentario.value.trim() || enviandoComentario.value) return
  enviandoComentario.value = true
  try {
    const data = await rutasStore.agregarComentario(rutaId.value, nuevoComentario.value.trim())
    if (data) {
      eventos.value.push(data)
      nuevoComentario.value = ''
    }
  } catch (e) {
    mostrarToast('Error al enviar comentario', false)
  } finally {
    enviandoComentario.value = false
  }
}

async function cambiarTab(t) {
  tab.value = t
  if (t === 'historial') await cargarEventos()
}

function formatTimestamp(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' }) +
    ' ' + d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
}

// ── Drag handle del bottom sheet ─────────────────────────────────────────────
let dragStartY = 0

function onDragStart(e) { dragStartY = e.touches[0].clientY }
function onDragEnd(e) {
  if (e.changedTouches[0].clientY - dragStartY > 80) {
    modalIniciar.value   = false
    modalFinalizar.value = false
  }
}

// ── Acciones de modales ───────────────────────────────────────────────────────
function abrirIniciar() {
  errorModal.value   = ''
  kmInicio.value     = ruta.value?.vehiculo?.km_actuales?.toString() || ''
  modalIniciar.value = true
}

function abrirFinalizar() {
  errorModal.value     = ''
  // Pre-completar con km estimado: km_inicio + distancia de ruta
  const r = ruta.value
  if (r?.km_inicio != null && r?.distancia_km != null) {
    kmFin.value = String(Math.round(r.km_inicio + r.distancia_km))
  } else if (r?.distancia_km != null) {
    kmFin.value = String(Math.round(r.distancia_km))
  } else {
    kmFin.value = ''
  }
  modalFinalizar.value = true
}

async function confirmarIniciar() {
  procesando.value = true
  errorModal.value = ''
  try {
    await rutasStore.iniciarRuta(
      rutaId.value,
      kmInicio.value ? Number(kmInicio.value) : undefined,
    )
    modalIniciar.value = false
    await cargarDetalle()
  } catch (e) {
    errorModal.value = e.message
  } finally {
    procesando.value = false
  }
}

async function confirmarFinalizar() {
  if (!kmFin.value && kmFin.value !== 0) {
    errorModal.value = 'Ingresa el km final del vehículo.'
    return
  }
  procesando.value = true
  errorModal.value = ''
  try {
    await rutasStore.finalizarRuta(rutaId.value, {
      km_fin: Number(kmFin.value),
    })
    modalFinalizar.value = false
    mostrarToast('Ruta finalizada correctamente.')
    setTimeout(() => router.push('/rutas'), 1600)
  } catch (e) {
    errorModal.value = e.message
  } finally {
    procesando.value = false
  }
}

// ── Carga del detalle ─────────────────────────────────────────────────────────
async function cargarDetalle() {
  const cached = rutasStore.rutas.find(r => r.id === rutaId.value)
  if (cached && !ruta.value) ruta.value = cached

  try {
    const data = await apiFetch(`/api/conductor/rutas/${rutaId.value}/`)
    ruta.value = data
    const idx  = rutasStore.rutas.findIndex(r => r.id === rutaId.value)
    if (idx > -1) rutasStore.rutas[idx] = data
    else          rutasStore.rutas.push(data)
  } catch (e) {
    if (!ruta.value) {
      errorMsg.value = e.message.includes('Sin conexión')
        ? 'Sin conexión y sin datos guardados'
        : e.message.includes('no encontrada')
          ? 'Ruta no encontrada'
          : 'Error al cargar la ruta'
    }
  } finally {
    cargando.value = false
  }
}

onMounted(async () => {
  if (!rutasStore.rutas.length) {
    await rutasStore.init()
    await rutasStore.cargarRutas()
  }
  await cargarDetalle()
})


// ── Checklist pre-viaje ───────────────────────────────────────────────────────
const checklistCompleto = computed(() =>
  ruta.value?.extra?.checklist_completo === true
)

// ── Bloqueo por hora programada ───────────────────────────────────────────────
/**
 * Si la ruta tiene hora_programada, calcula si todavía es demasiado temprano.
 * Retorna null si ya se puede iniciar, o un objeto { hora, minRestantes } si no.
 */
const bloqueoHora = computed(() => {
  const r = ruta.value
  if (!r?.hora_programada || !r?.fecha_programada) return null

  const [hh, mm]       = r.hora_programada.split(':').map(Number)
  const dtProgramado   = new Date(`${r.fecha_programada}T${String(hh).padStart(2,'0')}:${String(mm).padStart(2,'0')}:00`)
  const limite         = new Date(dtProgramado.getTime() - 30 * 60 * 1000)
  const ahora          = new Date()

  if (ahora < limite) {
    const diffMs  = dtProgramado - ahora
    const diffMin = Math.ceil(diffMs / 60000)
    const horas   = Math.floor(diffMin / 60)
    const minutos = diffMin % 60
    return {
      hora:        r.hora_programada,
      minRestantes: diffMin,
      texto:       horas > 0
        ? `Faltan ${horas}h ${minutos}min para las ${r.hora_programada}`
        : `Faltan ${minutos} min para las ${r.hora_programada}`,
    }
  }
  return null
})

// ── Helpers estáticos ─────────────────────────────────────────────────────────
const ESTADO_LABEL = {
  pendiente: 'Pendiente', activo: 'En curso',
  finalizado: 'Finalizada', cancelado: 'Cancelada', borrador: 'Borrador',
}
const ESTADO_BADGE = {
  pendiente:  'bg-indigo-50 text-indigo-600',
  activo:     'bg-green-50  text-green-600',
  finalizado: 'bg-gray-100  text-gray-500',
  cancelado:  'bg-red-50    text-red-500',
}
const PARADA_COLOR = {
  origen:  'bg-[#1D9E75]',
  parada:  'bg-[#378ADD]',
  destino: 'bg-[#E24B4A]',
}
const COMBUSTIBLE = {
  bencina: 'Bencina', diesel: 'Diésel', electrico: 'Eléctrico', hibrido: 'Híbrido',
}
</script>

<template>
  <div class="min-h-dvh bg-gray-50 flex flex-col">

    <!-- ── Toast ─────────────────────────────────────────────────────────── -->
    <Transition name="toast-slide">
      <div v-if="toast.visible"
           class="fixed left-4 right-4 z-[4000] rounded-2xl px-4 py-3 shadow-xl text-sm font-semibold flex items-center gap-2"
           style="top: max(1rem, calc(env(safe-area-inset-top, 0px) + 0.5rem))"
           :class="toast.ok ? 'bg-green-500 text-white' : 'bg-red-500 text-white'">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
        </svg>
        {{ toast.mensaje }}
      </div>
    </Transition>

    <!-- ── Skeleton carga inicial ──────────────────────────────────────────── -->
    <template v-if="cargando && !ruta">
      <div class="h-[68px] bg-white border-b border-gray-100 shrink-0"/>
      <div class="h-[220px] bg-gray-200 animate-pulse shrink-0"/>
      <div class="px-4 pt-4 flex flex-col gap-3">
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-3/4"/>
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-1/2"/>
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-2/3"/>
      </div>
    </template>

    <!-- ── Error ──────────────────────────────────────────────────────────── -->
    <template v-else-if="errorMsg && !ruta">
      <div class="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center text-gray-400">
        <svg class="w-14 h-14 text-gray-200" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        <p class="text-sm font-medium">{{ errorMsg }}</p>
        <div class="flex gap-3">
          <button @click="cargarDetalle" class="text-sm text-[var(--color-acento)] font-bold min-h-[44px] px-4">
            Reintentar
          </button>
          <button @click="router.back()" class="text-sm text-gray-400 min-h-[44px] px-4">
            Volver
          </button>
        </div>
      </div>
    </template>

    <!-- ── Vista principal ────────────────────────────────────────────────── -->
    <template v-else-if="ruta">

      <!-- Header fijo -->
      <header class="fixed top-0 left-0 right-0 z-[1001] bg-white border-b border-gray-100 flex items-center gap-3 px-4"
              style="padding-top:max(0.75rem,env(safe-area-inset-top)); padding-bottom:0.75rem">
        <button @click="router.back()"
                class="p-2 -ml-2 text-gray-500 min-h-[44px] min-w-[44px] flex items-center justify-center">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="flex-1 min-w-0">
          <p class="font-bold text-gray-800 text-sm truncate">{{ ruta.nombre }}</p>
          <p class="text-xs text-gray-400">{{ ruta.tipo === 'carga' ? 'Carga' : 'Personas' }}</p>
        </div>
        <span :class="['text-[10px] font-bold px-2.5 py-1 rounded-full shrink-0',
                       ESTADO_BADGE[ruta.estado] || 'bg-gray-100 text-gray-500']">
          {{ ruta.estado === 'activo' ? '● ' : '' }}{{ ESTADO_LABEL[ruta.estado] || ruta.estado }}
        </span>
      </header>

      <!-- Barra de tabs -->
      <div class="fixed left-0 right-0 z-[1000] bg-white border-b border-gray-100 px-4 py-2 flex gap-2"
           style="top:calc(56px + max(0.75rem,env(safe-area-inset-top)))">
        <button
          v-for="t in [
            { key:'ruta',      label:'Ruta',      icon:'ti-map-pin'   },
            { key:'detalles',  label:'Detalles',  icon:'ti-list'      },
            { key:'historial', label:'Historial', icon:'ti-history'   },
          ]"
          :key="t.key"
          @click="cambiarTab(t.key)"
          :class="['px-4 py-1.5 rounded-full text-xs font-semibold transition-all min-h-[34px]',
                   tab === t.key
                     ? 'text-white'
                     : 'text-gray-500 bg-gray-100 hover:bg-gray-200']"
          :style="tab === t.key ? 'background:var(--color-acento)' : ''"
        >
          <i :class="`ti ${t.icon} mr-1 text-xs`"/>{{ t.label }}
        </button>
      </div>

      <!-- Contenido scrollable -->
      <div
        class="flex-1 overflow-y-auto"
        style="
          margin-top: calc(106px + max(0.75rem, env(safe-area-inset-top, 0px)));
          padding-bottom: calc(var(--nav-total, 60px) + 70px);
        "
      >

        <!-- ═══ TAB: RUTA ═══════════════════════════════════════════════════ -->
        <div v-show="tab === 'ruta'">

          <!-- Mapa -->
          <MapaRuta
            :paradas="ruta.paradas"
            :polyline="ruta.polyline"
            altura="220px"
          />

          <!-- Chips de información -->
          <div class="flex gap-2 px-4 py-3 flex-wrap">
            <span v-if="ruta.distancia_km"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1.5">
              <i class="ti ti-road text-gray-400 text-xs"/>{{ ruta.distancia_km }} km
            </span>
            <span v-if="ruta.duracion_min"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1.5">
              <i class="ti ti-clock text-gray-400 text-xs"/>{{ formatDuracion(ruta.duracion_min) }}
            </span>
            <span v-if="ruta.fecha_programada"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1.5">
              <i class="ti ti-calendar text-gray-400 text-xs"/>{{ formatFechaRuta(ruta.fecha_programada) }}
              <span v-if="ruta.hora_programada" class="font-semibold text-indigo-600 ml-0.5">· {{ ruta.hora_programada }}</span>
            </span>
          </div>

          <!-- Lista paradas -->
          <div class="px-4 pb-4">
            <div class="bg-white rounded-2xl border border-gray-100 p-4">
              <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Recorrido</h3>

              <div v-for="(parada, i) in (ruta.paradas || []).slice().sort((a,b) => a.orden - b.orden)"
                   :key="parada.id"
                   class="flex gap-3">

                <!-- Conector vertical -->
                <div class="flex flex-col items-center">
                  <span :class="['w-3 h-3 rounded-full shrink-0 mt-0.5',
                                 PARADA_COLOR[parada.tipo] || 'bg-gray-400']"/>
                  <div v-if="i < (ruta.paradas || []).length - 1"
                       class="w-px flex-1 my-1 min-h-[18px]"
                       style="border-left:2px dashed #E5E7EB"/>
                </div>

                <!-- Info -->
                <div class="pb-3 min-w-0 flex-1">
                  <div class="flex items-start justify-between gap-2">
                    <p class="text-sm font-medium text-gray-800 leading-snug">{{ parada.nombre }}</p>
                    <span class="text-[10px] text-gray-400 shrink-0 capitalize">
                      {{ parada.tipo === 'origen'  ? 'Origen'
                       : parada.tipo === 'destino' ? 'Destino'
                       : `Parada ${parada.orden}` }}
                    </span>
                  </div>
                  <p v-if="parada.direccion" class="text-xs text-gray-400 truncate">{{ parada.direccion }}</p>
                  <p v-if="parada.tipo === 'origen' && ruta.fecha_programada"
                     class="text-xs text-gray-400">
                    Salida programada: {{ formatFechaRuta(ruta.fecha_programada) }}
                    <span v-if="ruta.hora_programada" class="font-semibold text-indigo-500 ml-0.5">{{ ruta.hora_programada }}</span>
                  </p>
                  <p v-if="parada.notas" class="text-xs text-gray-400 italic">{{ parada.notas }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══ TAB: DETALLES ════════════════════════════════════════════════ -->
        <div v-show="tab === 'detalles'" class="px-4 pt-4 flex flex-col gap-3 pb-4">

          <div class="bg-white rounded-2xl border border-gray-100 p-4 flex flex-col gap-3">

            <!-- Tipo -->
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-500">Tipo</span>
              <span :class="['text-xs font-bold px-3 py-1 rounded-full',
                             ruta.tipo === 'carga' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700']">
                {{ ruta.tipo === 'carga' ? 'Carga' : 'Personas' }}
              </span>
            </div>

            <!-- Vehículo -->
            <div v-if="ruta.vehiculo" class="flex items-start justify-between gap-4">
              <span class="text-sm text-gray-500 shrink-0">Vehículo</span>
              <div class="text-right">
                <p class="text-sm font-semibold text-gray-700">{{ ruta.vehiculo.patente }}</p>
                <p class="text-xs text-gray-400">{{ ruta.vehiculo.marca }} {{ ruta.vehiculo.modelo }}</p>
                <p class="text-xs text-gray-400">
                  {{ COMBUSTIBLE[ruta.vehiculo.tipo_combustible] || ruta.vehiculo.tipo_combustible }}
                </p>
              </div>
            </div>

            <!-- Conductor -->
            <div v-if="ruta.conductor" class="flex justify-between">
              <span class="text-sm text-gray-500">Conductor</span>
              <span class="text-sm font-medium text-gray-700">{{ ruta.conductor.nombre }}</span>
            </div>

            <div class="border-t border-gray-50"/>

            <!-- Fechas -->
            <div v-if="ruta.fecha_programada" class="flex justify-between">
              <span class="text-sm text-gray-500">Fecha programada</span>
              <span class="text-sm font-medium text-gray-700">{{ formatFechaRuta(ruta.fecha_programada) }}</span>
            </div>
            <div v-if="ruta.hora_programada" class="flex justify-between">
              <span class="text-sm text-gray-500">Hora programada</span>
              <span class="text-sm font-semibold text-indigo-600 flex items-center gap-1"><i class="ti ti-clock-hour-4 text-xs"/>{{ ruta.hora_programada }}</span>
            </div>
            <div v-if="ruta.fecha_inicio" class="flex justify-between">
              <span class="text-sm text-gray-500">Inicio real</span>
              <span class="text-sm font-medium text-gray-700">{{ formatFechaRuta(ruta.fecha_inicio) }}</span>
            </div>
            <div v-if="ruta.fecha_fin" class="flex justify-between">
              <span class="text-sm text-gray-500">Fin real</span>
              <span class="text-sm font-medium text-gray-700">{{ formatFechaRuta(ruta.fecha_fin) }}</span>
            </div>

            <!-- KM -->
            <template v-if="ruta.km_inicio || ruta.km_fin">
              <div class="border-t border-gray-50"/>
              <div v-if="ruta.km_inicio" class="flex justify-between">
                <span class="text-sm text-gray-500">KM inicio</span>
                <span class="text-sm font-medium text-gray-700">{{ ruta.km_inicio.toLocaleString('es-CL') }}</span>
              </div>
              <div v-if="ruta.km_fin" class="flex justify-between">
                <span class="text-sm text-gray-500">KM fin</span>
                <span class="text-sm font-medium text-gray-700">{{ ruta.km_fin.toLocaleString('es-CL') }}</span>
              </div>
              <div v-if="ruta.km_reales" class="flex justify-between font-semibold">
                <span class="text-sm text-gray-600">KM recorridos</span>
                <span class="text-sm text-gray-800">{{ ruta.km_reales.toLocaleString('es-CL') }} km</span>
              </div>
            </template>
          </div>

        </div>

        <!-- ═══ TAB: HISTORIAL ═══════════════════════════════════════════════ -->
        <div v-show="tab === 'historial'" class="px-4 pt-4 flex flex-col gap-3 pb-4">

          <!-- Spinner -->
          <div v-if="cargandoEventos" class="flex justify-center py-10">
            <div class="w-7 h-7 border-4 border-[var(--color-acento)] border-t-transparent rounded-full animate-spin"/>
          </div>

          <!-- Lista -->
          <div v-else class="bg-white rounded-2xl border border-gray-100 p-4">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Historial</h3>

            <div v-if="!eventos.length" class="flex flex-col items-center gap-2 py-8 text-gray-400">
              <i class="ti ti-notes text-3xl text-gray-200"/>
              <p class="text-sm">No hay eventos aún.</p>
            </div>

            <div v-for="e in eventos" :key="e.id" class="flex gap-3 mb-4 last:mb-0">
              <!-- Icono -->
              <div :class="['flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-sm',
                e.tipo === 'auto' ? 'bg-indigo-500' : 'bg-green-500']">
                <i :class="e.tipo === 'auto' ? 'ti ti-settings' : 'ti ti-message-circle'"/>
              </div>
              <!-- Contenido -->
              <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-800">{{ e.texto }}</p>
                <p class="text-xs text-gray-400 mt-0.5">
                  {{ e.autor || 'Sistema' }} · {{ formatTimestamp(e.created_at) }}
                </p>
              </div>
            </div>
          </div>

          <!-- Input nuevo comentario -->
          <div class="bg-white rounded-2xl border border-gray-100 p-4">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3"><i class="ti ti-message-plus mr-1"/>Agregar comentario</p>
            <div class="flex gap-2">
              <input v-model="nuevoComentario" type="text" placeholder="Escribe un comentario..."
                class="flex-1 border-2 border-gray-100 rounded-xl px-3 py-2.5 text-sm bg-gray-50
                       focus:border-[var(--color-acento)] focus:bg-white outline-none transition"
                @keydown.enter="enviarComentario"/>
              <button @click="enviarComentario"
                :disabled="!nuevoComentario.trim() || enviandoComentario"
                class="px-4 py-2.5 rounded-xl text-sm font-bold text-white disabled:opacity-50 min-h-[44px]"
                style="background:var(--color-acento)">
                <span v-if="enviandoComentario" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block"/>
                <span v-else><i class="ti ti-send"/></span>
              </button>
            </div>
          </div>
        </div>

      </div><!-- fin scrollable -->

      <!-- ── Botón de acción fijo ──────────────────────────────────────────── -->
      <div
        class="fixed left-0 right-0 px-4 pb-3 z-[500]"
        style="bottom: var(--nav-total, 60px)"
      >

        <!-- [pendiente] → Checklist o Iniciar ruta -->
        <template v-if="ruta.estado === 'pendiente'">
          <button
            v-if="!checklistCompleto"
            @click="router.push(`/rutas/${rutaId}/checklist`)"
            class="w-full py-4 rounded-2xl text-white font-bold text-sm flex items-center justify-center gap-2 min-h-[54px]"
            style="background:linear-gradient(135deg,#534AB7,#7C3AED);
                   box-shadow:0 4px 20px rgba(83,74,183,0.35)"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
            </svg>
            Completar checklist antes de iniciar
          </button>
          <!-- Bloqueado por anticipación de hora -->
          <div
            v-else-if="bloqueoHora"
            class="w-full rounded-2xl border-2 border-amber-300 bg-amber-50 px-4 py-3.5 flex flex-col items-center gap-1.5 min-h-[54px]"
          >
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-amber-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span class="text-sm font-bold text-amber-700">Ruta programada para las {{ bloqueoHora.hora }}</span>
            </div>
            <p class="text-xs text-amber-600 text-center">{{ bloqueoHora.texto }} — podrás iniciarla 30 min antes</p>
          </div>
          <!-- Listo para iniciar -->
          <button
            v-else
            @click="abrirIniciar"
            class="w-full py-4 rounded-2xl text-white font-bold text-sm flex items-center justify-center gap-2 min-h-[54px]"
            style="background:linear-gradient(135deg,#22c55e,#16a34a);
                   box-shadow:0 4px 16px rgba(34,197,94,.4)"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 3l14 9-14 9V3z"/>
            </svg>
            Iniciar ruta
          </button>
        </template>

        <!-- [activo] → Navegar + Finalizar -->
        <template v-else-if="ruta.estado === 'activo'">
          <button
            v-if="tieneCoordsNavegacion"
            @click="menuNavegar = true"
            class="w-full mb-4 py-4 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 min-h-[54px] text-gray-700 bg-white border-2 border-gray-200"
          >
            <svg class="w-5 h-5" style="color: var(--color-acento)" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
            </svg>
            Navegar con GPS
          </button>
          <button
            @click="abrirFinalizar"
            class="w-full py-4 rounded-2xl text-white font-bold text-sm flex items-center justify-center gap-2 min-h-[54px]"
            style="background:linear-gradient(135deg,var(--color-acento),#7C3AED);
                   box-shadow:0 4px 16px rgba(83,74,183,.4)"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Finalizar ruta
          </button>
        </template>

        <!-- [finalizado / cancelado] → Banner informativo -->
        <div
          v-else-if="ruta.estado === 'finalizado' || ruta.estado === 'cancelado'"
          class="flex items-center justify-center gap-2 py-3.5 text-sm text-gray-500 bg-white border border-gray-200 rounded-2xl"
        >
          <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Estado: {{ ESTADO_LABEL[ruta.estado] }}
          <template v-if="ruta.fecha_fin"> · {{ formatFechaRuta(ruta.fecha_fin) }}</template>
        </div>
      </div>

    </template><!-- fin vista principal -->

    <!-- ─────────────────────────────────────────────────────────────────────
         SHEET: Elegir app de navegación
    ───────────────────────────────────────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="menuNavegar" class="fixed inset-0 z-[2000]">
        <div class="absolute inset-0 bg-black/40" @click="menuNavegar = false"/>
        <div class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl px-6 pt-5 pb-10"
             style="padding-bottom: calc(2.5rem + env(safe-area-inset-bottom))">
          <div class="flex justify-center mb-4"><div class="w-10 h-1 rounded-full bg-gray-300"/></div>
          <h2 class="text-base font-bold text-gray-800 mb-1">Navegar con GPS</h2>
          <p class="text-sm text-gray-500 mb-4">Abre la ruta en tu app de mapas.</p>
          <button @click="navegarGoogleMaps"
            class="w-full py-3.5 mb-2 rounded-xl border border-gray-200 text-gray-800 font-semibold text-sm flex items-center justify-center gap-2">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="#4285F4"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/></svg>
            Google Maps
            <span class="text-[11px] text-gray-400 font-normal">(ruta completa)</span>
          </button>
          <button @click="navegarWaze"
            class="w-full py-3.5 rounded-xl border border-gray-200 text-gray-800 font-semibold text-sm flex items-center justify-center gap-2">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="#33CCFF"><circle cx="12" cy="12" r="10"/></svg>
            Waze
            <span class="text-[11px] text-gray-400 font-normal">(al destino)</span>
          </button>
        </div>
      </div>
    </Transition>

    <!-- ─────────────────────────────────────────────────────────────────────
         MODAL: Iniciar ruta
    ───────────────────────────────────────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="modalIniciar" class="fixed inset-0 z-[2000]">
        <div class="absolute inset-0 bg-black/40" @click="modalIniciar = false"/>

        <div
          class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl"
          style="padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px))"
        >
          <div class="flex justify-center pt-4 pb-2"
               @touchstart="onDragStart" @touchend="onDragEnd">
            <div class="w-10 h-1 bg-gray-200 rounded-full"/>
          </div>

          <div class="px-6 pb-4">
            <h3 class="text-lg font-bold text-gray-800 mb-0.5">Iniciar ruta</h3>
            <p class="text-sm text-gray-400 mb-5 truncate">{{ ruta?.nombre }}</p>

            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Odómetro actual
              <span class="text-gray-400 font-normal">(opcional)</span>
            </label>
            <div class="relative mb-5">
              <input
                v-model="kmInicio"
                type="number" inputmode="numeric" placeholder="Ej: 125000" min="0"
                class="w-full px-4 py-3 pr-12 border-2 border-gray-100 rounded-xl text-sm bg-gray-50
                       focus:border-green-400 focus:bg-white outline-none transition"
              />
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-gray-400 font-medium">km</span>
            </div>

            <p v-if="errorModal" class="text-sm text-red-500 mb-3">{{ errorModal }}</p>

            <div class="flex gap-3">
              <button @click="modalIniciar = false"
                      class="flex-1 py-3 rounded-xl text-sm text-gray-500 bg-gray-100 font-semibold min-h-[48px]">
                Cancelar
              </button>
              <button @click="confirmarIniciar" :disabled="procesando"
                      class="flex-[2] py-3 rounded-xl text-sm text-white font-bold bg-green-500
                             disabled:opacity-60 min-h-[48px] flex items-center justify-center gap-2">
                <span v-if="procesando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                {{ procesando ? 'Iniciando…' : 'Iniciar ▶' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ─────────────────────────────────────────────────────────────────────
         MODAL: Finalizar ruta
    ───────────────────────────────────────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="modalFinalizar" class="fixed inset-0 z-[2000]">
        <div class="absolute inset-0 bg-black/40" @click="modalFinalizar = false"/>

        <div
          class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl"
          style="max-height: min(65vh, 65dvh); padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px))"
        >
          <div class="flex justify-center pt-4 pb-2"
               @touchstart="onDragStart" @touchend="onDragEnd">
            <div class="w-10 h-1 bg-gray-200 rounded-full"/>
          </div>

          <div class="px-6 pb-4">
            <h3 class="text-lg font-bold text-gray-800 mb-0.5">Finalizar ruta</h3>
            <p class="text-sm text-gray-400 mb-5 truncate">{{ ruta?.nombre }}</p>

            <!-- Km final -->
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Odómetro final *
            </label>
            <div class="relative mb-4">
              <input
                v-model="kmFin"
                type="number" inputmode="numeric" placeholder="Ej: 126000" min="0"
                class="w-full px-4 py-3 pr-12 border-2 border-gray-100 rounded-xl text-sm bg-gray-50
                       focus:border-[var(--color-acento)] focus:bg-white outline-none transition"
              />
              <span class="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-gray-400 font-medium">km</span>
            </div>

            <p v-if="errorModal" class="text-sm text-red-500 mb-3">{{ errorModal }}</p>

            <div class="flex gap-3">
              <button @click="modalFinalizar = false"
                      class="flex-1 py-3 rounded-xl text-sm text-gray-500 bg-gray-100 font-semibold min-h-[48px]">
                Cancelar
              </button>
              <button @click="confirmarFinalizar" :disabled="procesando || (!kmFin && kmFin !== 0)"
                      class="flex-[2] py-3 rounded-xl text-sm text-white font-bold disabled:opacity-60
                             min-h-[48px] flex items-center justify-center gap-2"
                      style="background:var(--color-acento)">
                <span v-if="procesando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                {{ procesando ? 'Finalizando…' : 'Finalizar ✓' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <BottomNav />
  </div>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active { transition: opacity 0.28s ease; }
.sheet-enter-from,
.sheet-leave-to     { opacity: 0; }

.sheet-enter-active .absolute:last-child,
.sheet-leave-active .absolute:last-child { transition: transform 0.3s ease; }
.sheet-enter-from   .absolute:last-child,
.sheet-leave-to     .absolute:last-child { transform: translateY(100%); }

.toast-slide-enter-active,
.toast-slide-leave-active { transition: all 0.25s ease; }
.toast-slide-enter-from,
.toast-slide-leave-to     { opacity: 0; transform: translateY(-12px); }
</style>
