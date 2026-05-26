<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore }       from '@/stores/auth.js'
import { useRutasStore }      from '@/stores/rutas.js'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import { usePermisos } from '@/composables/usePermisos.js'
import BottomNav  from '@/components/BottomNav.vue'
import RutaCard   from '@/components/RutaCard.vue'
import { iniciales, tiempoDesde } from '@/utils/formato.js'

const router       = useRouter()
const auth         = useAuthStore()
const rutasStore   = useRutasStore()
const mantenStore  = useMantencionesStore()
const { cargando: cargandoPermisos } = usePermisos()

const historialAbierto = ref(true)

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
  await mantenStore.cargarMantenciones()
})
</script>

<template>
  <!-- Skeleton mientras se cargan los permisos -->
  <div v-if="cargandoPermisos" class="min-h-dvh bg-gray-50 flex items-center justify-center">
    <span class="w-8 h-8 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
  </div>

  <!-- Contenido normal (el watch redirige a /solicitudes si no hay módulo) -->
  <div v-else
    class="min-h-dvh bg-gray-50 pb-nav"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- ── Spinner pull-to-refresh ─────────────────────────────────────────── -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Banner: vehículo en mantención ───────────────────────────────────── -->
    <div
      v-if="mantenStore.vehiculoEnMantencion"
      class="alert-banner alert-banner--red mx-4 mt-3"
      @click="router.push('/mantencion')"
    >
      <span class="alert-icon">🔴</span>
      <div class="flex-1 min-w-0">
        <p class="alert-title">Vehículo fuera de servicio</p>
        <p class="alert-body">Tu vehículo está detenido por una mantención activa</p>
      </div>
      <svg class="w-4 h-4 shrink-0 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
      </svg>
    </div>

    <!-- ── Banner: mantención próxima (≤ 3 días) sin bloqueo ────────────────── -->
    <div
      v-else-if="mantenStore.hayUrgente"
      class="alert-banner alert-banner--amber mx-4 mt-3"
      @click="router.push('/mantencion')"
    >
      <span class="alert-icon">⚠️</span>
      <div class="flex-1 min-w-0">
        <p class="alert-title">Mantención próxima</p>
        <p class="alert-body">Tienes una mantención programada en los próximos días</p>
      </div>
      <svg class="w-4 h-4 shrink-0 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
      </svg>
    </div>

    <!-- ── Header con gradiente ──────────────────────────────────────────── -->
    <header class="header-hero">
      <!-- Capa de patrón sutil -->
      <div class="header-pattern" aria-hidden="true"/>

      <div class="header-content">
        <!-- Avatar + saludo -->
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <div class="avatar-circle">
            {{ iniciales(auth.usuario?.nombre) }}
          </div>
          <div class="min-w-0">
            <p class="text-white/70 text-xs leading-none mb-0.5">Bienvenido</p>
            <p class="text-white font-bold text-base leading-tight truncate">
              {{ auth.usuario?.nombre || auth.usuario?.email }}
            </p>
            <p v-if="auth.usuario?.vehiculo_asignado" class="text-white/60 text-[11px] mt-0.5 truncate">
              {{ auth.usuario.vehiculo_asignado.patente }} ·
              {{ auth.usuario.vehiculo_asignado.marca }}
              {{ auth.usuario.vehiculo_asignado.modelo }}
            </p>
          </div>
        </div>

        <!-- Botones derecha -->
        <div class="flex items-center gap-1 shrink-0">
          <!-- Sync -->
          <button
            @click="rutasStore.cargarRutas()"
            class="icon-btn-ghost"
            :class="{ 'animate-spin': rutasStore.cargando }"
            aria-label="Actualizar"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
          <!-- Notificaciones -->
          <button
            @click="router.push('/solicitudes')"
            class="icon-btn-ghost"
            aria-label="Solicitudes"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Stats row -->
      <div class="stats-row">
        <div class="stat-chip">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          <span>{{ rutasStore.rutasPendientes.length }} pendiente{{ rutasStore.rutasPendientes.length !== 1 ? 's' : '' }}</span>
        </div>
        <div v-if="rutasStore.rutaActiva" class="stat-chip stat-chip--green">
          <span class="pulse-dot"/>
          <span>Ruta en curso</span>
        </div>
        <div class="stat-chip stat-chip--muted">
          <span>Sync {{ tiempoDesde(rutasStore.ultimaSync) }}</span>
        </div>
      </div>
    </header>

    <!-- ── Banner offline ─────────────────────────────────────────────────── -->
    <Transition name="banner">
      <div
        v-if="!rutasStore.online"
        class="alert-banner alert-banner--orange mx-4 mt-3"
      >
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12h.01M8.464 15.536a5 5 0 01-.001-7.072m-2.827 9.9a9 9 0 010-12.728"/>
        </svg>
        <span class="alert-body">Sin conexión — mostrando datos guardados</span>
      </div>
    </Transition>

    <!-- ── Skeleton carga inicial ─────────────────────────────────────────── -->
    <div v-if="rutasStore.cargando && !rutasStore.rutas.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="skeleton h-28"/>
    </div>

    <template v-else>
      <div class="px-4 mt-4 flex flex-col gap-5">

        <!-- ── Ruta activa ───────────────────────────────────────────────── -->
        <section v-if="rutasStore.rutaActiva">
          <p class="section-title">En curso</p>
          <RutaCard
            :ruta="rutasStore.rutaActiva"
            variante="activa"
            @click="verRuta"
          />
        </section>

        <!-- ── Próximas rutas ────────────────────────────────────────────── -->
        <section>
          <div class="flex items-center justify-between mb-2">
            <p class="section-title" style="margin-bottom:0">Próximas rutas</p>
            <span v-if="rutasStore.rutasPendientes.length"
              class="text-[11px] font-bold text-[var(--color-acento)] bg-[var(--color-acento-suave)] rounded-full px-2.5 py-0.5"
            >{{ rutasStore.rutasPendientes.length }}</span>
          </div>

          <!-- Estado vacío -->
          <div
            v-if="!rutasStore.rutasPendientes.length"
            class="empty-state"
          >
            <div class="empty-icon-wrap">
              <svg class="w-8 h-8 text-[var(--color-acento)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
              </svg>
            </div>
            <p class="text-sm font-semibold text-gray-600">Sin rutas programadas</p>
            <p class="text-xs text-gray-400 text-center">Tu administrador asignará rutas aquí</p>
          </div>

          <div v-else class="flex flex-col gap-2.5">
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
            class="flex items-center justify-between w-full mb-2 min-h-[44px]"
          >
            <p class="section-title" style="margin-bottom:0">Historial</p>
            <svg
              class="w-4 h-4 text-gray-400 transition-transform duration-200"
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
                @click="verRuta"
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
/* ── Header héroe ──────────────────────────────────────────────────────── */
.header-hero {
  position: relative;
  overflow: hidden;
  background: var(--gradient-hero);
  padding: max(1.25rem, env(safe-area-inset-top)) 1rem 0.75rem;
}
.header-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.08) 0%, transparent 50%),
                    radial-gradient(circle at 20% 80%, rgba(255,255,255,0.05) 0%, transparent 40%);
}
.header-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.avatar-circle {
  width: 44px; height: 44px; flex-shrink: 0;
  border-radius: 50%;
  background: rgba(255,255,255,0.20);
  border: 2px solid rgba(255,255,255,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.875rem;
  font-weight: 700;
}
.icon-btn-ghost {
  width: 38px; height: 38px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.icon-btn-ghost:active { background: rgba(255,255,255,0.25); }

/* Stats row */
.stats-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.875rem;
  padding-bottom: 0.875rem;
  flex-wrap: wrap;
}
.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.9);
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 999px;
  padding: 0.25rem 0.625rem;
}
.stat-chip--green {
  background: rgba(34,197,94,0.25);
  border-color: rgba(34,197,94,0.4);
}
.stat-chip--muted {
  color: rgba(255,255,255,0.55);
  border-color: rgba(255,255,255,0.12);
  background: transparent;
}
.pulse-dot {
  display: inline-block;
  width: 6px; height: 6px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse-green 1.5s infinite;
}
@keyframes pulse-green {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(1.4); }
}

/* ── Alert banners ─────────────────────────────────────────────────────── */
.alert-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-radius: 1rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
}
.alert-banner:active { opacity: 0.8; }
.alert-banner--red    { background: #FFF1F1; border: 1px solid #FECACA; color: #B91C1C; }
.alert-banner--amber  { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; }
.alert-banner--orange { background: #FFF7ED; border: 1px solid #FED7AA; color: #9A3412; }
.alert-icon  { font-size: 1.25rem; flex-shrink: 0; }
.alert-title { font-size: 0.8125rem; font-weight: 700; line-height: 1.3; }
.alert-body  { font-size: 0.75rem; opacity: 0.8; }

/* ── Empty state ───────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2.5rem 1rem;
}
.empty-icon-wrap {
  width: 64px; height: 64px;
  border-radius: 20px;
  background: var(--color-acento-suave);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.25rem;
}

/* Títulos de sección */
.section-title {
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #9CA3AF;
  margin-bottom: 0.5rem;
}

/* Skeleton */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: 1rem;
}
@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Transición banner offline */
.banner-enter-active, .banner-leave-active { transition: all 0.3s ease; }
.banner-enter-from, .banner-leave-to       { opacity: 0; transform: translateY(-8px); }

/* Transición historial */
.historial-enter-active, .historial-leave-active { transition: all 0.25s ease; }
.historial-enter-from, .historial-leave-to       { opacity: 0; transform: translateY(-6px); }
</style>
