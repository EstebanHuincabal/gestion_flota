<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import BottomNav from '@/components/BottomNav.vue'
import ModalDetalleMantencion from '@/components/ModalDetalleMantencion.vue'

const store  = useMantencionesStore()
const router = useRouter()

// ── Pull to refresh ───────────────────────────────────────────────────────────
let startY       = 0
const refreshing = ref(false)
function onTouchStart(e) { startY = e.touches[0].clientY }
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await store.cargarMantenciones()
    refreshing.value = false
  }
}

// ── Modal de detalle ──────────────────────────────────────────────────────────
const modalVisible    = ref(false)
const detalleActual   = ref(null)
const cargandoDetalle = ref(false)

async function abrirDetalle(mantencion) {
  detalleActual.value   = { ...mantencion }
  modalVisible.value    = true
  cargandoDetalle.value = true
  try {
    const completo = await store.obtenerDetalle(mantencion.id)
    detalleActual.value = completo
  } catch {
    // Si falla, nos quedamos con los datos parciales
  } finally {
    cargandoDetalle.value = false
  }
}

function cerrarDetalle() {
  modalVisible.value  = false
  detalleActual.value = null
}

// ── Toasts ────────────────────────────────────────────────────────────────────
const toastMsg     = ref('')
const toastVisible = ref(false)
let toastTimer = null

function mostrarToast(msg) {
  toastMsg.value     = msg
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 3500)
}

// ── Callbacks del modal ───────────────────────────────────────────────────────

function onIniciada(mantencionActualizada) {
  mostrarToast('🔧 Mantención iniciada. Tu vehículo está en mantención.')
  store.cargarMantenciones()
}

function onCompletada(result) {
  mostrarToast('✅ Mantención registrada y costo enviado a finanzas.')
  store.cargarMantenciones()
}

// ── Lista de mantenciones activas (pendiente + en_proceso) ────────────────────
const mantencionesActivas = computed(() =>
  store.mantenciones.filter(m => m.estado === 'pendiente' || m.estado === 'en_proceso')
)

// ── Helpers UI ────────────────────────────────────────────────────────────────
const ESTADO = {
  pendiente:  { label: 'Pendiente',   color: '#185FA5', bg: '#E6F1FB' },
  en_proceso: { label: 'En proceso',  color: '#B45309', bg: '#FEF3C7' },
  realizada:  { label: 'Realizada',   color: '#065F46', bg: '#D1FAE5' },
}
function badgeEstado(e) { return ESTADO[e] || { label: e, color: '#555', bg: '#eee' } }

function fmtFecha(iso) {
  if (!iso) return 'Sin fecha'
  return new Date(iso + 'T00:00').toLocaleDateString('es-CL', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

function fmtPrecio(v) {
  if (!v) return null
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(v)
}

function colorDias(dias) {
  if (dias === null) return 'text-gray-400'
  if (dias <= 0)  return 'text-red-600 font-bold'
  if (dias <= 3)  return 'text-orange-600 font-semibold'
  if (dias <= 7)  return 'text-amber-600'
  return 'text-gray-500'
}

function textoDias(dias) {
  if (dias === null)  return ''
  if (dias < 0)  return `Vencida hace ${Math.abs(dias)} días`
  if (dias === 0) return 'Hoy'
  if (dias === 1) return 'Mañana'
  return `En ${dias} días`
}

// Etiqueta de acción según estado (para el indicador clickable)
function labelAccion(estado) {
  if (estado === 'pendiente')  return '▶ Toca para iniciar'
  if (estado === 'en_proceso') return '✓ Toca para marcar realizada'
  return 'Ver detalles'
}
function colorAccion(estado) {
  if (estado === 'pendiente')  return '#2563EB'
  if (estado === 'en_proceso') return '#059669'
  return '#9CA3AF'
}

onMounted(() => store.cargarMantenciones())
</script>

<template>
  <div
    class="min-h-dvh bg-gray-50 pb-nav"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- Spinner pull-to-refresh -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- Toast de acción exitosa -->
    <Transition name="toast">
      <div
        v-if="toastVisible"
        class="fixed top-safe-toast left-4 right-4 z-[200] flex items-center gap-3
               bg-gray-900 text-white rounded-2xl px-4 py-3 shadow-lg"
      >
        <p class="text-sm font-semibold">{{ toastMsg }}</p>
      </div>
    </Transition>

    <!-- Header -->
    <header class="bg-white px-4 pt-safe pb-4 border-b border-gray-100">
      <h1 class="text-xl font-bold text-gray-800">Mantención</h1>
      <p v-if="store.vehiculo" class="text-xs text-gray-400 mt-0.5">
        {{ store.vehiculo.patente }} · {{ store.vehiculo.marca }} {{ store.vehiculo.modelo }}
      </p>
    </header>

    <!-- Vehículo en mantención — alerta bloqueante -->
    <div
      v-if="store.vehiculoEnMantencion"
      class="mx-4 mt-4 flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl p-4"
    >
      <span class="text-2xl">🔴</span>
      <div>
        <p class="text-sm font-bold text-red-700">Vehículo fuera de servicio</p>
        <p class="text-xs text-red-500 mt-0.5">
          Tu vehículo está detenido por una mantención activa.
          Finaliza la mantención antes de iniciar cualquier ruta.
        </p>
      </div>
    </div>

    <!-- Skeleton carga -->
    <div v-if="store.cargando && !store.mantenciones.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 2" :key="i" class="h-28 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <template v-else>
      <div class="px-4 mt-4 flex flex-col gap-4">

        <!-- ══ SECCIÓN: Mantenciones activas ══════════════════════════════════ -->

        <!-- Estado vacío -->
        <div
          v-if="!mantencionesActivas.length && !store.vehiculoEnMantencion"
          class="flex flex-col items-center gap-3 py-16 text-gray-400"
        >
          <svg class="w-14 h-14 text-gray-200" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <p class="text-base font-medium">Sin mantenciones activas</p>
          <p class="text-sm text-center">Tu vehículo no tiene mantenciones<br>pendientes ni en proceso.</p>
        </div>

        <!-- Lista -->
        <div v-if="mantencionesActivas.length" class="flex flex-col gap-3">
          <article
            v-for="m in mantencionesActivas"
            :key="m.id"
            class="bg-white rounded-2xl border p-4 flex flex-col gap-3 cursor-pointer active:opacity-75"
            :class="m.urgente ? 'border-orange-300 shadow-sm' : (m.estado === 'en_proceso' ? 'border-amber-300' : 'border-gray-200')"
            @click="abrirDetalle(m)"
          >
            <!-- Tipo + badge estado -->
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="text-xl">{{ m.estado === 'en_proceso' ? '🔩' : '🔧' }}</span>
                <p class="text-sm font-bold text-gray-800 leading-tight">{{ m.tipo }}</p>
              </div>
              <span
                class="shrink-0 text-[10px] font-semibold rounded-full px-2.5 py-0.5"
                :style="`color: ${badgeEstado(m.estado).color}; background: ${badgeEstado(m.estado).bg}`"
              >
                {{ badgeEstado(m.estado).label }}
              </span>
            </div>

            <!-- Descripción -->
            <p v-if="m.descripcion" class="text-xs text-gray-500 italic leading-relaxed">
              "{{ m.descripcion }}"
            </p>

            <!-- Grid de detalles -->
            <div class="grid grid-cols-2 gap-y-2 gap-x-3 text-xs">
              <div>
                <p class="text-gray-400 font-medium mb-0.5">Fecha programada</p>
                <p class="text-gray-700 font-semibold">{{ fmtFecha(m.fecha_programada) }}</p>
                <p v-if="m.dias_restantes !== null" :class="colorDias(m.dias_restantes)" class="mt-0.5">
                  {{ textoDias(m.dias_restantes) }}
                </p>
              </div>
              <div v-if="m.taller">
                <p class="text-gray-400 font-medium mb-0.5">Taller / Mecánico</p>
                <p class="text-gray-700 font-semibold">{{ m.taller }}</p>
              </div>
              <div v-if="m.presupuesto">
                <p class="text-gray-400 font-medium mb-0.5">Presupuesto estimado</p>
                <p class="text-gray-700 font-semibold">{{ fmtPrecio(m.presupuesto) }}</p>
              </div>
            </div>

            <!-- Chip urgente / vencida -->
            <div v-if="m.urgente && m.dias_restantes !== null && m.dias_restantes >= 0"
              class="flex items-center gap-1.5 bg-orange-50 rounded-xl px-3 py-2"
            >
              <svg class="w-4 h-4 text-orange-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
              <p class="text-xs text-orange-600 font-medium">
                Mantención próxima — coordina con tu administrador
              </p>
            </div>
            <div v-else-if="m.dias_restantes !== null && m.dias_restantes < 0"
              class="flex items-center gap-1.5 bg-red-50 rounded-xl px-3 py-2"
            >
              <svg class="w-4 h-4 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p class="text-xs text-red-600 font-medium">
                Esta mantención está vencida — contacta a tu administrador
              </p>
            </div>

            <!-- CTA indicador -->
            <div class="flex items-center justify-end gap-1">
              <span class="text-xs font-semibold" :style="`color: ${colorAccion(m.estado)}`">
                {{ labelAccion(m.estado) }}
              </span>
              <svg class="w-4 h-4" :style="`color: ${colorAccion(m.estado)}`" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </article>
        </div>

      </div>
    </template>

    <!-- Botón historial -->
    <div class="px-4 pb-2 mt-2">
      <button
        class="w-full flex items-center justify-between gap-3 bg-white border border-gray-200 rounded-2xl px-4 py-3.5 active:opacity-70 shadow-sm"
        @click="router.push('/mantencion/historial')"
      >
        <div class="flex items-center gap-3">
          <span class="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
            </svg>
          </span>
          <div class="text-left">
            <p class="text-sm font-semibold text-gray-800">Historial de mantenciones</p>
            <p class="text-xs text-gray-400 mt-0.5">Ver todas las realizadas en este vehículo</p>
          </div>
        </div>
        <svg class="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
        </svg>
      </button>
    </div>

    <!-- Modal de detalle + acciones -->
    <ModalDetalleMantencion
      v-if="modalVisible && detalleActual"
      :mantencion="detalleActual"
      :cargando="cargandoDetalle"
      @cerrar="cerrarDetalle"
      @iniciada="onIniciada"
      @completada="onCompletada"
    />

    <BottomNav />
  </div>
</template>

<style scoped>
.pt-safe {
  padding-top: max(1rem, env(safe-area-inset-top));
}
.top-safe-toast {
  top: max(1rem, calc(env(safe-area-inset-top) + 0.5rem));
}

/* Toast */
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to       { opacity: 0; transform: translateY(-8px); }
</style>
