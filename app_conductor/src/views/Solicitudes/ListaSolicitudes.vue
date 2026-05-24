<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'
import { apiFetch } from '@/services/api.js'
import { tiempoDesde } from '@/utils/formato.js'

const router = useRouter()

// ── Estado ─────────────────────────────────────────────────────────────────
const notificaciones  = ref([])
const cargando        = ref(false)
const errorMsg        = ref('')
const paginaActual    = ref(1)
const totalPaginas    = ref(1)
const cargandoMas     = ref(false)
const marcandoTodas   = ref(false)

const noLeidas = computed(() => notificaciones.value.filter(n => !n.leida).length)

// ── Carga de notificaciones ───────────────────────────────────────────────
async function cargarNotificaciones(pagina = 1, acumular = false) {
  if (pagina === 1) { cargando.value = true; errorMsg.value = '' }
  else               cargandoMas.value = true

  try {
    const data = await apiFetch(`/api/notificaciones/?page=${pagina}`)
    if (acumular) {
      notificaciones.value = [...notificaciones.value, ...data.results]
    } else {
      notificaciones.value = data.results
    }
    paginaActual.value = pagina
    totalPaginas.value = data.num_pages
  } catch (e) {
    if (!acumular) errorMsg.value = e.message === 'Sin conexión. Verifica tu red.'
      ? 'Sin conexión. No se pueden cargar las notificaciones.'
      : 'Error al cargar notificaciones.'
  } finally {
    cargando.value    = false
    cargandoMas.value = false
  }
}

async function cargarMas() {
  if (cargandoMas.value || paginaActual.value >= totalPaginas.value) return
  await cargarNotificaciones(paginaActual.value + 1, true)
}

// ── Marcar como leída (individual) ───────────────────────────────────────
async function marcarLeida(notif) {
  if (notif.leida) return
  notif.leida = true   // optimista
  try {
    await apiFetch('/api/notificaciones/leer/', {
      method: 'POST',
      body: JSON.stringify({ ids: [notif.id] }),
    })
  } catch {
    notif.leida = false  // revertir si falla
  }
}

// ── Marcar todas como leídas ─────────────────────────────────────────────
async function marcarTodas() {
  if (!noLeidas.value || marcandoTodas.value) return
  marcandoTodas.value = true
  // Optimista
  notificaciones.value.forEach(n => { n.leida = true })
  try {
    await apiFetch('/api/notificaciones/leer/', {
      method: 'POST',
      body: JSON.stringify({ todas: true }),
    })
  } catch {
    // Recargar si falla
    await cargarNotificaciones()
  } finally {
    marcandoTodas.value = false
  }
}

// ── Navegar si la notificación tiene url_accion ───────────────────────────
function abrirNotificacion(notif) {
  marcarLeida(notif)
  if (notif.url_accion && notif.url_accion.startsWith('/rutas/')) {
    const id = notif.url_accion.replace('/rutas/', '').replace('/', '')
    if (id && !isNaN(id)) router.push(`/rutas/${id}`)
  }
}

// ── Pull to refresh ───────────────────────────────────────────────────────
let startY = 0
let refreshing = ref(false)

function onTouchStart(e) { startY = e.touches[0].clientY }
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await cargarNotificaciones()
    refreshing.value = false
  }
}

// ── Íconos por tipo ───────────────────────────────────────────────────────
const TIPO_CONFIG = {
  actividad: {
    icon: 'actividad',
    clase: 'bg-blue-100 text-blue-600',
  },
  mantencion: {
    icon: 'mantencion',
    clase: 'bg-amber-100 text-amber-600',
  },
  documentos: {
    icon: 'documentos',
    clase: 'bg-purple-100 text-purple-600',
  },
  seguridad: {
    icon: 'seguridad',
    clase: 'bg-red-100 text-red-600',
  },
}

function tipoConfig(tipo) {
  return TIPO_CONFIG[tipo] || TIPO_CONFIG.actividad
}

onMounted(() => cargarNotificaciones())
</script>

<template>
  <div
    class="min-h-screen bg-gray-50 pb-24"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="bg-white px-4 pt-safe pb-4 border-b border-gray-100">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-bold text-gray-800">Notificaciones</h1>
          <!-- Badge no leídas -->
          <span
            v-if="noLeidas > 0"
            class="px-2 py-0.5 rounded-full text-xs font-bold text-white"
            style="background: var(--color-acento)"
          >
            {{ noLeidas > 99 ? '99+' : noLeidas }}
          </span>
        </div>

        <!-- Marcar todas como leídas -->
        <button
          v-if="noLeidas > 0"
          @click="marcarTodas"
          :disabled="marcandoTodas"
          class="flex items-center gap-1.5 text-xs font-semibold min-h-[44px] px-2 transition-colors disabled:opacity-50"
          style="color: var(--color-acento)"
        >
          <span v-if="marcandoTodas" class="w-3.5 h-3.5 border border-current border-t-transparent rounded-full animate-spin"/>
          <span>{{ marcandoTodas ? 'Marcando…' : 'Leer todas' }}</span>
        </button>
      </div>
    </header>

    <!-- ── Spinner pull-to-refresh ───────────────────────────────────────── -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Skeleton ───────────────────────────────────────────────────────── -->
    <div v-if="cargando && !notificaciones.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 5" :key="i" class="h-20 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <!-- ── Error ──────────────────────────────────────────────────────────── -->
    <div v-else-if="errorMsg && !notificaciones.length"
         class="flex flex-col items-center gap-3 py-16 px-8">
      <svg class="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <p class="text-sm text-gray-500 text-center">{{ errorMsg }}</p>
      <button
        @click="cargarNotificaciones()"
        class="px-5 py-2.5 rounded-xl text-sm font-semibold text-white min-h-[44px]"
        style="background: var(--color-acento)"
      >
        Reintentar
      </button>
    </div>

    <!-- ── Lista vacía ────────────────────────────────────────────────────── -->
    <div
      v-else-if="!cargando && !notificaciones.length"
      class="flex flex-col items-center gap-2 py-16 text-gray-400"
    >
      <svg class="w-14 h-14 text-gray-200" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
      </svg>
      <p class="text-sm font-medium">Sin notificaciones</p>
      <p class="text-xs text-gray-400">Todo en orden por ahora.</p>
    </div>

    <!-- ── Lista de notificaciones ────────────────────────────────────────── -->
    <div v-else class="px-4 mt-4 flex flex-col gap-2">
      <button
        v-for="notif in notificaciones"
        :key="notif.id"
        @click="abrirNotificacion(notif)"
        class="w-full text-left bg-white rounded-2xl shadow-sm p-4 flex items-start gap-3 transition-all active:scale-[0.98] min-h-[72px]"
        :class="{ 'ring-1 ring-[var(--color-acento)]/20': !notif.leida }"
      >
        <!-- Ícono tipo -->
        <div
          :class="['w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5', tipoConfig(notif.tipo).clase]"
        >
          <!-- Actividad -->
          <svg v-if="tipoConfig(notif.tipo).icon === 'actividad'" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          <!-- Mantención -->
          <svg v-else-if="tipoConfig(notif.tipo).icon === 'mantencion'" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <!-- Documentos -->
          <svg v-else-if="tipoConfig(notif.tipo).icon === 'documentos'" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <!-- Seguridad -->
          <svg v-else-if="tipoConfig(notif.tipo).icon === 'seguridad'" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
        </div>

        <!-- Contenido -->
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2">
            <p class="text-sm font-semibold text-gray-800 leading-snug truncate">
              {{ notif.titulo }}
            </p>
            <!-- Dot no leída -->
            <span
              v-if="!notif.leida"
              class="w-2 h-2 rounded-full shrink-0 mt-1"
              style="background: var(--color-acento)"
            />
          </div>
          <p class="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
            {{ notif.mensaje }}
          </p>
          <p class="text-[10px] text-gray-400 mt-1.5">
            {{ tiempoDesde(notif.fecha) }}
          </p>
        </div>
      </button>

      <!-- Cargar más -->
      <div v-if="paginaActual < totalPaginas" class="py-2">
        <button
          @click="cargarMas"
          :disabled="cargandoMas"
          class="w-full py-3 rounded-xl text-sm font-medium text-gray-500 bg-white shadow-sm min-h-[48px] flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <span v-if="cargandoMas" class="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"/>
          <span>{{ cargandoMas ? 'Cargando…' : 'Cargar más' }}</span>
        </button>
      </div>

    </div>

    <!-- ── Bottom nav ─────────────────────────────────────────────────────── -->
    <BottomNav />

  </div>
</template>

<style scoped>
.pt-safe {
  padding-top: max(1rem, env(safe-area-inset-top));
}

/* Limitar mensaje a 2 líneas */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
