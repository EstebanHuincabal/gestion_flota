<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore }  from '@/stores/auth.js'
import { useRutasStore } from '@/stores/rutas.js'
import BottomNav  from '@/components/BottomNav.vue'
import RutaCard   from '@/components/RutaCard.vue'
import { iniciales, tiempoDesde } from '@/utils/formato.js'

const router     = useRouter()
const auth       = useAuthStore()
const rutasStore = useRutasStore()

const historialAbierto = ref(false)

// ── Pull to refresh ───────────────────────────────────────────────────────────
let startY    = 0
let refreshing = ref(false)

function onTouchStart(e) {
  startY = e.touches[0].clientY
}
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await rutasStore.cargarRutas()
    refreshing.value = false
  }
}

// ── Navegación ────────────────────────────────────────────────────────────────
function verRuta(id) {
  router.push(`/rutas/${id}`)
}

// ── Inicialización ────────────────────────────────────────────────────────────
onMounted(async () => {
  await rutasStore.init()
  await rutasStore.cargarRutas()
})
</script>

<template>
  <div
    class="min-h-screen bg-gray-50 pb-24"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- ── Spinner pull-to-refresh ─────────────────────────────────────────── -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <header class="bg-white px-4 pt-safe pb-4 border-b border-gray-100">
      <div class="flex items-center justify-between">
        <!-- Avatar + info -->
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
            style="background: var(--color-acento)"
          >
            {{ iniciales(auth.usuario?.nombre) }}
          </div>
          <div>
            <p class="text-xs text-gray-400 leading-tight">Hola,</p>
            <p class="text-sm font-bold text-gray-800 leading-tight">
              {{ auth.usuario?.nombre || auth.usuario?.email }}
            </p>
          </div>
        </div>

        <!-- Campana notificaciones -->
        <button
          @click="router.push('/solicitudes')"
          class="relative p-2 text-gray-400 hover:text-gray-600 min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
        </button>
      </div>

      <!-- Vehículo asignado -->
      <p v-if="auth.usuario?.vehiculo_asignado" class="text-xs text-gray-400 mt-1 ml-13">
        {{ auth.usuario.vehiculo_asignado.patente }} ·
        {{ auth.usuario.vehiculo_asignado.marca }}
        {{ auth.usuario.vehiculo_asignado.modelo }}
      </p>

      <!-- Última sync -->
      <div class="flex items-center justify-end gap-1 mt-2">
        <span class="text-[10px] text-gray-400">
          Actualizado {{ tiempoDesde(rutasStore.ultimaSync) }}
        </span>
        <button
          @click="rutasStore.cargarRutas()"
          class="p-1 text-gray-300 hover:text-gray-500 transition"
          :class="{ 'animate-spin': rutasStore.cargando }"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- ── Banner offline ─────────────────────────────────────────────────── -->
    <Transition name="banner">
      <div
        v-if="!rutasStore.online"
        class="mx-4 mt-3 flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-xl px-3 py-2.5"
      >
        <svg class="w-4 h-4 text-orange-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12h.01M8.464 15.536a5 5 0 01-.001-7.072m-2.827 9.9a9 9 0 010-12.728"/>
        </svg>
        <span class="text-xs font-medium text-orange-700">Sin conexión — mostrando datos guardados</span>
      </div>
    </Transition>

    <!-- ── Skeleton carga inicial ─────────────────────────────────────────── -->
    <div v-if="rutasStore.cargando && !rutasStore.rutas.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="h-28 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <template v-else>
      <div class="px-4 mt-4 flex flex-col gap-4">

        <!-- ── Ruta activa ───────────────────────────────────────────────── -->
        <section v-if="rutasStore.rutaActiva">
          <RutaCard
            :ruta="rutasStore.rutaActiva"
            variante="activa"
            @click="verRuta"
          />
        </section>

        <!-- ── Próximas rutas ────────────────────────────────────────────── -->
        <section>
          <h2 class="text-sm font-bold text-gray-700 mb-2">
            Próximas rutas
            <span v-if="rutasStore.rutasPendientes.length" class="text-gray-400 font-normal">
              ({{ rutasStore.rutasPendientes.length }})
            </span>
          </h2>

          <!-- Estado vacío -->
          <div
            v-if="!rutasStore.rutasPendientes.length"
            class="flex flex-col items-center gap-2 py-10 text-gray-400"
          >
            <svg class="w-12 h-12 text-gray-200" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
            </svg>
            <p class="text-sm">No tienes rutas programadas</p>
          </div>

          <div v-else class="flex flex-col gap-2">
            <RutaCard
              v-for="ruta in rutasStore.rutasPendientes"
              :key="ruta.id"
              :ruta="ruta"
              variante="pendiente"
              @click="verRuta"
            />
          </div>
        </section>

        <!-- ── Historial (colapsable) ────────────────────────────────────── -->
        <section v-if="rutasStore.rutasFinalizadas.length">
          <button
            @click="historialAbierto = !historialAbierto"
            class="flex items-center justify-between w-full text-sm font-bold text-gray-700 mb-2 min-h-[44px]"
          >
            <span>Historial</span>
            <svg
              class="w-4 h-4 text-gray-400 transition-transform"
              :class="{ 'rotate-180': historialAbierto }"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <Transition name="historial">
            <div v-if="historialAbierto" class="flex flex-col gap-2">
              <RutaCard
                v-for="ruta in rutasStore.rutasFinalizadas.slice(0, 5)"
                :key="ruta.id"
                :ruta="ruta"
                variante="finalizada"
              />
            </div>
          </Transition>
        </section>

      </div>
    </template>

    <!-- ── Bottom nav ─────────────────────────────────────────────────────── -->
    <BottomNav />

  </div>
</template>

<style scoped>
/* Safe area top para iPhone con notch */
.pt-safe {
  padding-top: max(1rem, env(safe-area-inset-top));
}
/* Margen avatar → vehículo */
.ml-13 { margin-left: 3.25rem; }

/* Transición banner offline */
.banner-enter-active, .banner-leave-active { transition: all 0.3s ease; }
.banner-enter-from, .banner-leave-to       { opacity: 0; transform: translateY(-8px); }

/* Transición historial */
.historial-enter-active, .historial-leave-active { transition: all 0.25s ease; }
.historial-enter-from, .historial-leave-to       { opacity: 0; transform: translateY(-6px); }
</style>
