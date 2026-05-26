<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRutasStore } from '@/stores/rutas.js'
import { apiFetch }      from '@/services/api.js'
import BottomNav  from '@/components/BottomNav.vue'
import MapaRuta   from '@/components/MapaRuta.vue'
import { formatCLP, formatDuracion, formatFechaRuta } from '@/utils/formato.js'

const vueRoute   = useRoute()
const router     = useRouter()
const rutasStore = useRutasStore()

const rutaId  = computed(() => Number(vueRoute.params.id))
const ruta    = ref(null)
const cargando = ref(true)
const errorMsg = ref('')

// ── Tabs ─────────────────────────────────────────────────────────────────────
const tab = ref('ruta') // 'ruta' | 'costos' | 'detalles'

// ── Modales ───────────────────────────────────────────────────────────────────
const modalIniciar   = ref(false)
const modalFinalizar = ref(false)
const kmInicio       = ref('')
const kmFin          = ref('')
const combustibleReal = ref('')
const peajesReal      = ref('')
const notasModal      = ref('')
const procesando      = ref(false)
const errorModal      = ref('')

// ── Toast ─────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', ok: true })
let   toastTimer = null

function mostrarToast(mensaje, ok = true) {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, ok }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3000)
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
  errorModal.value = ''
  kmInicio.value   = ruta.value?.vehiculo?.km_actuales?.toString() || ''
  modalIniciar.value = true
}

function abrirFinalizar() {
  errorModal.value    = ''
  kmFin.value         = ''
  combustibleReal.value = ruta.value?.costo_combustible_est?.toString() || ''
  peajesReal.value      = ruta.value?.costo_peajes_est?.toString()      || ''
  notasModal.value      = ''
  modalFinalizar.value  = true
}

async function confirmarIniciar() {
  procesando.value  = true
  errorModal.value  = ''
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
  // Validaciones
  if (Number(combustibleReal.value) < 0 || Number(peajesReal.value) < 0) {
    errorModal.value = 'Los costos no pueden ser negativos'
    return
  }

  procesando.value = true
  errorModal.value = ''
  try {
    await rutasStore.finalizarRuta(rutaId.value, {
      costo_combustible_real: combustibleReal.value ? Number(combustibleReal.value) : undefined,
      costo_peajes_real:      peajesReal.value      ? Number(peajesReal.value)      : undefined,
      notas:                  notasModal.value       || undefined,
    })
    modalFinalizar.value = false
    mostrarToast('Ruta finalizada. Se registraron los gastos.')
    setTimeout(() => router.push('/rutas'), 1600)
  } catch (e) {
    errorModal.value = e.message
  } finally {
    procesando.value = false
  }
}

// ── Carga del detalle ─────────────────────────────────────────────────────────
async function cargarDetalle() {
  // Mostrar cache del store de inmediato si existe
  const cached = rutasStore.rutas.find(r => r.id === rutaId.value)
  if (cached && !ruta.value) ruta.value = cached

  try {
    const data = await apiFetch(`/api/conductor/rutas/${rutaId.value}/`)
    ruta.value = data
    // Actualizar cache en el store
    const idx = rutasStore.rutas.findIndex(r => r.id === rutaId.value)
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

// ── Recorrido combinado (paradas + peajes intercalados) ───────────────────────
function distPuntoSegmento(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay
  if (!dx && !dy) return Math.hypot(px - ax, py - ay)
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

const recorridoCombinado = computed(() => {
  if (!ruta.value) return []
  const paradas = [...(ruta.value.paradas || [])].sort((a, b) => a.orden - b.orden)
  const peajes  = (ruta.value.peajes_ruta || []).filter(p => p.latitud != null)

  if (!peajes.length) return paradas.map(p => ({ ...p, _es: 'parada' }))

  const result = []
  for (let i = 0; i < paradas.length; i++) {
    result.push({ ...paradas[i], _es: 'parada' })

    if (i < paradas.length - 1 && paradas[i].latitud && paradas[i + 1].latitud) {
      const enSegmento = peajes.filter(peaje => {
        let minSeg = 0, minDist = Infinity
        for (let s = 0; s < paradas.length - 1; s++) {
          if (!paradas[s].latitud || !paradas[s + 1].latitud) continue
          const d = distPuntoSegmento(
            peaje.latitud, peaje.longitud,
            paradas[s].latitud, paradas[s].longitud,
            paradas[s + 1].latitud, paradas[s + 1].longitud,
          )
          if (d < minDist) { minDist = d; minSeg = s }
        }
        return minSeg === i
      })
      enSegmento.forEach(p => result.push({ ...p, _es: 'peaje' }))
    }
  }
  return result
})

// ── Costos comparativos ───────────────────────────────────────────────────────
const difCombustible = computed(() => {
  if (ruta.value?.costo_combustible_real == null) return null
  return ruta.value.costo_combustible_real - (ruta.value.costo_combustible_est || 0)
})
const difPeajes = computed(() => {
  if (ruta.value?.costo_peajes_real == null) return null
  return ruta.value.costo_peajes_real - (ruta.value.costo_peajes_est || 0)
})
const difTotal = computed(() => {
  if (ruta.value?.costo_total_real == null) return null
  return ruta.value.costo_total_real - (ruta.value.costo_total_est || 0)
})

function claseDif(dif) {
  if (dif == null) return 'text-gray-300'
  if (dif < 0)    return 'text-green-600'
  if (dif > 0)    return 'text-red-500'
  return 'text-gray-400'
}
function formatDif(dif) {
  if (dif == null || dif === 0) return '—'
  return (dif > 0 ? '+' : '-') + formatCLP(Math.abs(dif))
}

// ── Estimaciones de combustible ───────────────────────────────────────────────
const litrosEst = computed(() => {
  const km = ruta.value?.distancia_km
  const c  = ruta.value?.vehiculo?.consumo_l_100km
  if (!km || !c) return null
  return ((km * c) / 100).toFixed(1)
})
const precioLitroEst = computed(() => {
  if (!litrosEst.value || !ruta.value?.costo_combustible_est) return null
  return Math.round(ruta.value.costo_combustible_est / parseFloat(litrosEst.value))
})

// ── Checklist pre-viaje ───────────────────────────────────────────────────────
const checklistCompleto = computed(() =>
  ruta.value?.extra?.checklist_completo === true
)

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

    <!-- ── Toast (safe-area-aware para notch / Dynamic Island) ───────────── -->
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

    <!-- ── Skeleton carga inicial ─────────────────────────────────────────── -->
    <template v-if="cargando && !ruta">
      <div class="h-[68px] bg-white border-b border-gray-100 shrink-0"/>
      <div class="h-[220px] bg-gray-200 animate-pulse shrink-0"/>
      <div class="px-4 pt-4 flex flex-col gap-3">
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-3/4"/>
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-1/2"/>
        <div class="h-3.5 bg-gray-200 rounded-full animate-pulse w-2/3"/>
      </div>
    </template>

    <!-- ── Error ─────────────────────────────────────────────────────────── -->
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

    <!-- ── Vista principal ───────────────────────────────────────────────── -->
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

      <!-- Barra de tabs (fija debajo del header) -->
      <div class="fixed left-0 right-0 z-[1000] bg-white border-b border-gray-100 px-4 py-2 flex gap-2"
           style="top:calc(56px + max(0.75rem,env(safe-area-inset-top)))">
        <button
          v-for="t in [
            { key:'ruta',     label:'Ruta'     },
            { key:'costos',   label:'Costos'   },
            { key:'detalles', label:'Detalles' },
          ]"
          :key="t.key"
          @click="tab = t.key"
          :class="['px-4 py-1.5 rounded-full text-xs font-semibold transition-all min-h-[34px]',
                   tab === t.key
                     ? 'text-white'
                     : 'text-gray-500 bg-gray-100 hover:bg-gray-200']"
          :style="tab === t.key ? 'background:var(--color-acento)' : ''"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- Contenido scrollable (offset = header + tabs) -->
      <!-- pb = nav(60px) + botón(54px) + padding(16px) + safe-area-bottom -->
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
            :peajes="ruta.peajes_ruta || []"
            altura="220px"
          />

          <!-- Chips de información -->
          <div class="flex gap-2 px-4 py-3 flex-wrap">
            <span v-if="ruta.distancia_km"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1">
              🗺 {{ ruta.distancia_km }} km
            </span>
            <span v-if="ruta.duracion_min"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1">
              ⏱ {{ formatDuracion(ruta.duracion_min) }}
            </span>
            <span v-if="ruta.fecha_programada"
                  class="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 flex items-center gap-1">
              📅 {{ formatFechaRuta(ruta.fecha_programada) }}
            </span>
          </div>

          <!-- Lista recorrido (paradas + peajes intercalados) -->
          <div class="px-4 pb-4">
            <div class="bg-white rounded-2xl border border-gray-100 p-4">
              <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Recorrido</h3>

              <div v-for="(item, i) in recorridoCombinado"
                   :key="`${item._es}-${item.id}`"
                   class="flex gap-3">

                <!-- Conector vertical -->
                <div class="flex flex-col items-center">
                  <!-- Punto parada -->
                  <span v-if="item._es === 'parada'"
                        :class="['w-3 h-3 rounded-full shrink-0 mt-0.5',
                                 PARADA_COLOR[item.tipo] || 'bg-gray-400']"/>
                  <!-- Rombo peaje -->
                  <span v-else
                        class="w-3 h-3 shrink-0 mt-0.5 rotate-45 rounded-sm"
                        style="background:#EF9F27"/>
                  <!-- Línea punteada -->
                  <div v-if="i < recorridoCombinado.length - 1"
                       class="w-px flex-1 my-1 min-h-[18px]"
                       style="border-left:2px dashed #E5E7EB"/>
                </div>

                <!-- Info del item -->
                <div class="pb-3 min-w-0 flex-1">
                  <div class="flex items-start justify-between gap-2">
                    <p class="text-sm font-medium text-gray-800 leading-snug">{{ item.nombre }}</p>
                    <!-- Badge tipo parada -->
                    <span v-if="item._es === 'parada'"
                          class="text-[10px] text-gray-400 shrink-0 capitalize">
                      {{ item.tipo === 'origen'  ? 'Origen'
                       : item.tipo === 'destino' ? 'Destino'
                       : `Parada ${item.orden - 1}` }}
                    </span>
                    <!-- Badge peaje -->
                    <span v-else class="text-[10px] font-semibold text-orange-500 shrink-0">
                      Peaje
                    </span>
                  </div>

                  <!-- Detalles parada -->
                  <template v-if="item._es === 'parada'">
                    <p v-if="item.direccion" class="text-xs text-gray-400 truncate">{{ item.direccion }}</p>
                    <p v-if="item.tipo === 'origen' && ruta.fecha_programada"
                       class="text-xs text-gray-400">
                      Salida programada: {{ formatFechaRuta(ruta.fecha_programada) }}
                    </p>
                    <p v-if="item.notas" class="text-xs text-gray-400 italic">{{ item.notas }}</p>
                  </template>

                  <!-- Detalles peaje -->
                  <p v-else class="text-xs text-gray-500">
                    {{ item.ruta }} · {{ formatCLP(item.tarifa) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══ TAB: COSTOS ══════════════════════════════════════════════════ -->
        <div v-show="tab === 'costos'" class="px-4 pt-4 flex flex-col gap-3">

          <!-- Estimado vs. Real -->
          <div class="bg-white rounded-2xl border border-gray-100 p-4">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
              {{ ruta.estado === 'finalizado' ? 'Estimado vs. Real' : 'Costos estimados' }}
            </h3>

            <!-- Cabecera (solo si finalizado) -->
            <div v-if="ruta.estado === 'finalizado'"
                 class="grid grid-cols-4 text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-2">
              <span/>
              <span class="text-right">Estimado</span>
              <span class="text-right">Real</span>
              <span class="text-right">Dif.</span>
            </div>

            <!-- Filas -->
            <template v-for="row in [
              { label:'Combustible', est:ruta.costo_combustible_est, real:ruta.costo_combustible_real, dif:difCombustible, bold:false },
              { label:'Peajes',      est:ruta.costo_peajes_est,      real:ruta.costo_peajes_real,      dif:difPeajes,      bold:false },
            ]" :key="row.label">
              <div :class="['py-2 border-b border-gray-50',
                            ruta.estado === 'finalizado' ? 'grid grid-cols-4 items-center' : 'flex justify-between']">
                <span class="text-sm text-gray-500">{{ row.label }}</span>
                <span class="text-sm font-medium text-gray-700 text-right">{{ formatCLP(row.est) }}</span>
                <template v-if="ruta.estado === 'finalizado'">
                  <span class="text-sm font-medium text-gray-700 text-right">{{ formatCLP(row.real) }}</span>
                  <span :class="['text-xs font-bold text-right', claseDif(row.dif)]">{{ formatDif(row.dif) }}</span>
                </template>
              </div>
            </template>

            <!-- Total -->
            <div :class="['pt-2 mt-1',
                          ruta.estado === 'finalizado' ? 'grid grid-cols-4 items-center' : 'flex justify-between']">
              <span class="text-sm font-bold text-gray-700">Total</span>
              <span class="text-sm font-bold text-gray-800 text-right">{{ formatCLP(ruta.costo_total_est) }}</span>
              <template v-if="ruta.estado === 'finalizado'">
                <span class="text-sm font-bold text-gray-800 text-right">{{ formatCLP(ruta.costo_total_real) }}</span>
                <span :class="['text-sm font-bold text-right', claseDif(difTotal)]">{{ formatDif(difTotal) }}</span>
              </template>
            </div>
          </div>

          <!-- Desglose de peajes -->
          <div v-if="ruta.peajes_ruta?.length" class="bg-white rounded-2xl border border-gray-100 p-4">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Peajes en ruta</h3>
            <div v-for="peaje in ruta.peajes_ruta" :key="peaje.id"
                 class="flex justify-between items-center py-2 border-b border-gray-50 last:border-0 text-sm">
              <div>
                <p class="font-medium text-gray-700">{{ peaje.nombre }}</p>
                <p class="text-xs text-gray-400">{{ peaje.ruta }}</p>
              </div>
              <span class="font-semibold text-gray-700 shrink-0">{{ formatCLP(peaje.tarifa) }}</span>
            </div>
            <div class="flex justify-between text-sm font-bold border-t border-gray-100 pt-2 mt-1">
              <span class="text-gray-600">Total peajes</span>
              <span class="text-gray-800">
                {{ formatCLP(ruta.peajes_ruta.reduce((s, p) => s + p.tarifa, 0)) }}
              </span>
            </div>
          </div>

          <!-- Datos de combustible -->
          <div v-if="ruta.distancia_km || ruta.vehiculo?.consumo_l_100km"
               class="bg-white rounded-2xl border border-gray-100 p-4">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Datos de combustible</h3>
            <div class="flex flex-col gap-2">
              <div v-if="ruta.distancia_km" class="flex justify-between text-sm">
                <span class="text-gray-500">Distancia</span>
                <span class="font-medium text-gray-700">{{ ruta.distancia_km }} km</span>
              </div>
              <div v-if="ruta.vehiculo?.consumo_l_100km" class="flex justify-between text-sm">
                <span class="text-gray-500">Consumo est.</span>
                <span class="font-medium text-gray-700">{{ ruta.vehiculo.consumo_l_100km }} L/100km</span>
              </div>
              <div v-if="litrosEst" class="flex justify-between text-sm">
                <span class="text-gray-500">Litros est.</span>
                <span class="font-medium text-gray-700">{{ litrosEst }} L</span>
              </div>
              <div v-if="precioLitroEst" class="flex justify-between text-sm">
                <span class="text-gray-500">Precio/litro</span>
                <span class="font-medium text-gray-700">
                  {{ formatCLP(precioLitroEst) }}
                  <span v-if="ruta.vehiculo?.tipo_combustible" class="text-gray-400 font-normal">
                    ({{ COMBUSTIBLE[ruta.vehiculo.tipo_combustible] || ruta.vehiculo.tipo_combustible }})
                  </span>
                </span>
              </div>
              <div v-if="ruta.costo_combustible_est"
                   class="flex justify-between text-sm font-semibold border-t border-gray-100 pt-2">
                <span class="text-gray-600">Total est.</span>
                <span class="text-gray-800">{{ formatCLP(ruta.costo_combustible_est) }}</span>
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
                <p class="text-xs text-gray-400">
                  {{ ruta.vehiculo.marca }} {{ ruta.vehiculo.modelo }}
                </p>
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
                <span class="text-sm font-medium text-gray-700">
                  {{ ruta.km_inicio.toLocaleString('es-CL') }}
                </span>
              </div>
              <div v-if="ruta.km_fin" class="flex justify-between">
                <span class="text-sm text-gray-500">KM fin</span>
                <span class="text-sm font-medium text-gray-700">
                  {{ ruta.km_fin.toLocaleString('es-CL') }}
                </span>
              </div>
              <div v-if="ruta.km_reales" class="flex justify-between font-semibold">
                <span class="text-sm text-gray-600">KM recorridos</span>
                <span class="text-sm text-gray-800">{{ ruta.km_reales.toLocaleString('es-CL') }} km</span>
              </div>
            </template>
          </div>

          <!-- Notas -->
          <div v-if="ruta.notas" class="bg-white rounded-2xl border border-gray-100 p-4">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Notas</h3>
            <p class="text-sm text-gray-600 leading-relaxed">{{ ruta.notas }}</p>
          </div>
        </div>

      </div><!-- fin scrollable -->

      <!-- ── Botón de acción fijo ──────────────────────────────────────────── -->
      <!-- bottom = nav total (60px + safe-area-bottom) + 4px margen -->
      <div
        class="fixed left-0 right-0 px-4 pb-3 z-[500]"
        style="bottom: var(--nav-total, 60px)"
      >

        <!-- [pendiente] → Checklist o Iniciar ruta -->
        <template v-if="ruta.estado === 'pendiente'">
          <!-- Sin checklist: ir al checklist primero -->
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
          <!-- Con checklist: iniciar ruta normalmente -->
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

        <!-- [activo] → Finalizar ruta -->
        <button
          v-else-if="ruta.estado === 'activo'"
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
         MODAL: Iniciar ruta
    ───────────────────────────────────────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="modalIniciar" class="fixed inset-0 z-[2000]">
        <div class="absolute inset-0 bg-black/40" @click="modalIniciar = false"/>

        <div
          class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl"
          style="padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px))"
        >

          <!-- Handle arrastrable -->
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
          class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl scroll-hidden"
          style="max-height: min(72vh, 72dvh); padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0px))"
        >

          <div class="flex justify-center pt-4 pb-2"
               @touchstart="onDragStart" @touchend="onDragEnd">
            <div class="w-10 h-1 bg-gray-200 rounded-full"/>
          </div>

          <div class="px-6 pb-4">
            <h3 class="text-lg font-bold text-gray-800 mb-0.5">Finalizar ruta</h3>
            <p class="text-sm text-gray-400 mb-5 truncate">{{ ruta?.nombre }}</p>

            <!-- Costo combustible real -->
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Costo combustible real</label>
            <div class="relative mb-3">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
              <input
                v-model="combustibleReal"
                type="number" inputmode="numeric" min="0"
                class="w-full pl-8 pr-4 py-3 border-2 border-gray-100 rounded-xl text-sm bg-gray-50
                       focus:border-[var(--color-acento)] focus:bg-white outline-none transition"
              />
            </div>

            <!-- Costo peajes real -->
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Costo peajes real</label>
            <div class="relative mb-3">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
              <input
                v-model="peajesReal"
                type="number" inputmode="numeric" min="0"
                class="w-full pl-8 pr-4 py-3 border-2 border-gray-100 rounded-xl text-sm bg-gray-50
                       focus:border-[var(--color-acento)] focus:bg-white outline-none transition"
              />
            </div>

            <!-- Notas -->
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Notas <span class="text-gray-400 font-normal">(opcional)</span>
            </label>
            <textarea
              v-model="notasModal"
              rows="2"
              placeholder="Observaciones de la ruta…"
              class="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm bg-gray-50
                     focus:border-[var(--color-acento)] focus:bg-white outline-none transition resize-none mb-3"
            />

            <!-- Aviso gastos -->
            <div class="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5 mb-4">
              <span class="text-amber-500 mt-0.5">⚠</span>
              <p class="text-xs text-amber-700 leading-relaxed">
                Se crearán gastos operativos automáticamente al confirmar.
              </p>
            </div>

            <p v-if="errorModal" class="text-sm text-red-500 mb-3">{{ errorModal }}</p>

            <div class="flex gap-3">
              <button @click="modalFinalizar = false"
                      class="flex-1 py-3 rounded-xl text-sm text-gray-500 bg-gray-100 font-semibold min-h-[48px]">
                Cancelar
              </button>
              <button @click="confirmarFinalizar" :disabled="procesando"
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
/* Bottom sheet */
.sheet-enter-active,
.sheet-leave-active { transition: opacity 0.28s ease; }
.sheet-enter-from,
.sheet-leave-to     { opacity: 0; }

.sheet-enter-active .absolute:last-child,
.sheet-leave-active .absolute:last-child { transition: transform 0.3s ease; }
.sheet-enter-from   .absolute:last-child,
.sheet-leave-to     .absolute:last-child { transform: translateY(100%); }

/* Toast */
.toast-slide-enter-active,
.toast-slide-leave-active { transition: all 0.25s ease; }
.toast-slide-enter-from,
.toast-slide-leave-to     { opacity: 0; transform: translateY(-12px); }
</style>
