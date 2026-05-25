<script setup>
import { onMounted, ref } from 'vue'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import BottomNav from '@/components/BottomNav.vue'

const store = useMantencionesStore()

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

// ── Helpers UI ────────────────────────────────────────────────────────────────
const ESTADO = {
  pendiente:  { label: 'Pendiente',   color: '#185FA5', bg: '#E6F1FB' },
  en_proceso: { label: 'En proceso',  color: '#B45309', bg: '#FEF3C7' },
}
function badgeEstado(e) { return ESTADO[e] || { label: e, color: '#555', bg: '#eee' } }

function fmtFecha(iso) {
  if (!iso) return 'Sin fecha'
  return new Date(iso + 'T00:00').toLocaleDateString('es-CL', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

function fmtPresupuesto(v) {
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
          Contacta a tu administrador antes de iniciar cualquier ruta.
        </p>
      </div>
    </div>

    <!-- Skeleton carga -->
    <div v-if="store.cargando && !store.mantenciones.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 2" :key="i" class="h-28 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <template v-else>
      <div class="px-4 mt-4 flex flex-col gap-4">

        <!-- Estado vacío -->
        <div
          v-if="!store.mantenciones.length && !store.vehiculoEnMantencion"
          class="flex flex-col items-center gap-3 py-16 text-gray-400"
        >
          <i class="ti ti-tool text-6xl text-gray-200"/>
          <p class="text-base font-medium">Sin mantenciones activas</p>
          <p class="text-sm text-center">Tu vehículo no tiene mantenciones<br>pendientes ni en proceso.</p>
        </div>

        <!-- Lista de mantenciones -->
        <article
          v-for="m in store.mantenciones"
          :key="m.id"
          class="bg-white rounded-2xl border p-4 flex flex-col gap-3"
          :class="m.urgente ? 'border-orange-300 shadow-sm' : 'border-gray-200'"
        >

          <!-- Tipo + badge estado -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xl">🔧</span>
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

            <!-- Fecha -->
            <div>
              <p class="text-gray-400 font-medium mb-0.5">Fecha programada</p>
              <p class="text-gray-700 font-semibold">{{ fmtFecha(m.fecha_programada) }}</p>
              <p v-if="m.dias_restantes !== null" :class="colorDias(m.dias_restantes)" class="mt-0.5">
                {{ textoDias(m.dias_restantes) }}
              </p>
            </div>

            <!-- Taller -->
            <div v-if="m.taller">
              <p class="text-gray-400 font-medium mb-0.5">Taller / Mecánico</p>
              <p class="text-gray-700 font-semibold">{{ m.taller }}</p>
            </div>

            <!-- Presupuesto -->
            <div v-if="m.presupuesto">
              <p class="text-gray-400 font-medium mb-0.5">Presupuesto estimado</p>
              <p class="text-gray-700 font-semibold">{{ fmtPresupuesto(m.presupuesto) }}</p>
            </div>

          </div>

          <!-- Chip urgente -->
          <div v-if="m.urgente && m.dias_restantes !== null && m.dias_restantes >= 0"
            class="flex items-center gap-1.5 bg-orange-50 rounded-xl px-3 py-2"
          >
            <i class="ti ti-alert-triangle text-orange-500 text-sm"/>
            <p class="text-xs text-orange-600 font-medium">
              Mantención próxima — coordina con tu administrador
            </p>
          </div>
          <div v-else-if="m.dias_restantes !== null && m.dias_restantes < 0"
            class="flex items-center gap-1.5 bg-red-50 rounded-xl px-3 py-2"
          >
            <i class="ti ti-alert-circle text-red-500 text-sm"/>
            <p class="text-xs text-red-600 font-medium">
              Esta mantención está vencida — contacta a tu administrador
            </p>
          </div>

        </article>

      </div>
    </template>

    <BottomNav />
  </div>
</template>

<style scoped>
.pt-safe {
  padding-top: max(1rem, env(safe-area-inset-top));
}
</style>
