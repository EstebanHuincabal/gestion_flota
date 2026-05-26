<script setup>
/**
 * HistorialMantenciones.vue
 *
 * Vista de historial de mantenciones realizadas del vehículo asignado.
 * Muestra las mantenciones en estado "realizada" con paginación y
 * posibilidad de ver el detalle (foto, costo, notas) en un bottom-sheet.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '@/services/api.js'

const router = useRouter()

// ── Estado ────────────────────────────────────────────────────────────────────
const historial  = ref([])
const vehiculo   = ref(null)
const total      = ref(0)
const cargando   = ref(false)
const cargandoMas = ref(false)
const error      = ref('')
const pagina     = ref(1)
const hasMore    = ref(false)
const PAGE_SIZE  = 20

// ── Detalle (bottom-sheet) ────────────────────────────────────────────────────
const detalleVisible = ref(false)
const detalleItem    = ref(null)

// ── Pull-to-refresh ───────────────────────────────────────────────────────────
let startY        = 0
const refreshing  = ref(false)
function onTouchStart(e) { startY = e.touches[0].clientY }
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await cargar(true)
    refreshing.value = false
  }
}

// ── Carga de datos ────────────────────────────────────────────────────────────
async function cargar(reiniciar = false) {
  if (reiniciar) {
    pagina.value   = 1
    historial.value = []
  }
  cargando.value = true
  error.value    = ''
  try {
    const data = await apiFetch(
      `/api/conductor/mantenciones/historial/?page=${pagina.value}&page_size=${PAGE_SIZE}`
    )
    if (reiniciar) {
      historial.value = data.historial || []
    } else {
      historial.value.push(...(data.historial || []))
    }
    total.value   = data.total   ?? 0
    hasMore.value = data.has_more ?? false
    vehiculo.value = data.vehiculo || null
  } catch (e) {
    error.value = e?.message || 'Error al cargar el historial.'
  } finally {
    cargando.value = false
  }
}

async function cargarMas() {
  if (!hasMore.value || cargandoMas.value) return
  cargandoMas.value = true
  pagina.value++
  try {
    const data = await apiFetch(
      `/api/conductor/mantenciones/historial/?page=${pagina.value}&page_size=${PAGE_SIZE}`
    )
    historial.value.push(...(data.historial || []))
    hasMore.value = data.has_more ?? false
  } catch {
    pagina.value--  // revertir si falla
  } finally {
    cargandoMas.value = false
  }
}

// ── Helpers de formato ────────────────────────────────────────────────────────
const fmtFecha = (iso) => {
  if (!iso) return '—'
  return new Date(iso + (iso.length === 10 ? 'T00:00' : '')).toLocaleDateString('es-CL', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

const fmtPrecio = (v) => {
  if (!v && v !== 0) return '—'
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(v)
}

const diffPresupuesto = (m) => {
  if (!m.presupuesto || !m.costo_real) return null
  return m.costo_real - m.presupuesto
}

// ── Detalle ───────────────────────────────────────────────────────────────────
function verDetalle(item) {
  detalleItem.value    = item
  detalleVisible.value = true
}

onMounted(() => cargar(true))
</script>

<template>
  <div
    class="min-h-dvh bg-gray-50 pb-safe-bottom"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <!-- Header con gradiente y botón volver -->
    <header class="hist-header">
      <div class="hist-header-pattern" aria-hidden="true"/>
      <div class="hist-header-inner">
        <button class="hist-back-btn" @click="router.back()" aria-label="Volver">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="flex-1 min-w-0">
          <p class="hist-subtitle">Vehículo</p>
          <h1 class="hist-title">Historial de mantenciones</h1>
          <p v-if="vehiculo" class="hist-vehicle">
            {{ vehiculo.patente }} · {{ vehiculo.marca }} {{ vehiculo.modelo }}
          </p>
        </div>
        <span v-if="total > 0" class="hist-badge">
          {{ total }}
        </span>
      </div>
    </header>

    <!-- Spinner pull-to-refresh -->
    <div v-if="refreshing" class="flex justify-center pt-3">
      <span class="w-5 h-5 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- Error -->
    <div v-if="error" class="mx-4 mt-4 bg-red-50 border border-red-200 rounded-2xl p-4 text-sm text-red-700">
      {{ error }}
    </div>

    <!-- Skeleton carga inicial -->
    <div v-if="cargando && !historial.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 4" :key="i" class="h-24 hist-skeleton"/>
    </div>

    <!-- Estado vacío -->
    <div
      v-else-if="!cargando && !historial.length && !error"
      class="flex flex-col items-center gap-3 py-20 text-gray-400 px-6"
    >
      <div class="hist-empty-icon">
        <svg class="w-8 h-8" style="color: var(--color-acento)" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
        </svg>
      </div>
      <p class="text-base font-semibold text-gray-600">Sin historial aún</p>
      <p class="text-sm text-center leading-relaxed">
        Aquí aparecerán las mantenciones realizadas<br>a tu vehículo.
      </p>
    </div>

    <!-- ── Timeline ────────────────────────────────────────────────────── -->
    <div v-else class="timeline-wrap pb-6">
      <div
        v-for="(m, idx) in historial"
        :key="m.id"
        class="timeline-item"
        @click="verDetalle(m)"
      >
        <!-- Eje del timeline -->
        <div class="timeline-axis">
          <div class="timeline-dot">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <div v-if="idx < historial.length - 1" class="timeline-line"/>
        </div>

        <!-- Tarjeta -->
        <div class="timeline-card">
          <!-- Fecha encabezado -->
          <p class="timeline-date">{{ fmtFecha(m.fecha_realizada) }}</p>

          <!-- Contenido principal -->
          <div class="flex items-start justify-between gap-3 mb-2">
            <p class="text-sm font-bold text-gray-800 leading-tight flex-1">{{ m.tipo }}</p>
            <p class="text-base font-extrabold text-gray-900 shrink-0">{{ fmtPrecio(m.costo_real) }}</p>
          </div>

          <!-- Chips inferiores -->
          <div class="flex items-center gap-2 flex-wrap">
            <span v-if="m.confirmado_conductor" class="tl-chip tl-chip--green">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              Completada por ti
            </span>
            <span v-else class="tl-chip tl-chip--gray">👤 Por administrador</span>

            <span v-if="m.taller" class="tl-chip tl-chip--gray">
              🏪 {{ m.taller }}
            </span>

            <span
              v-if="diffPresupuesto(m) !== null"
              :class="diffPresupuesto(m) > 0 ? 'tl-chip--red' : diffPresupuesto(m) < 0 ? 'tl-chip--green' : 'tl-chip--gray'"
              class="tl-chip"
            >
              {{ diffPresupuesto(m) > 0 ? '▲' : diffPresupuesto(m) < 0 ? '▼' : '=' }}
              {{ fmtPrecio(Math.abs(diffPresupuesto(m))) }}
            </span>
          </div>

          <!-- Foto miniatura -->
          <img
            v-if="m.foto_comprobante_url"
            :src="m.foto_comprobante_url"
            alt="Comprobante"
            class="w-full h-20 object-cover rounded-xl border border-gray-100 mt-3"
          />
        </div>
      </div>

      <!-- Cargar más -->
      <button
        v-if="hasMore"
        class="w-full mx-4 py-3 text-sm font-semibold text-[var(--color-acento)] bg-white border border-gray-200 rounded-2xl active:opacity-70 mt-1"
        style="max-width: calc(100% - 2rem)"
        :disabled="cargandoMas"
        @click="cargarMas"
      >
        <span v-if="cargandoMas" class="inline-flex items-center gap-2">
          <span class="w-4 h-4 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
          Cargando…
        </span>
        <span v-else>Ver más ({{ total - historial.length }} restantes)</span>
      </button>
    </div>

    <!-- ── Bottom-sheet detalle ───────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="detalleVisible && detalleItem" class="overlay-det" @click.self="detalleVisible = false">
        <div class="sheet-det">
          <!-- Agarradera -->
          <div class="handle-wrap" @click="detalleVisible = false">
            <span class="handle"/>
          </div>

          <!-- Encabezado -->
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="text-2xl">🔧</span>
              <p class="text-base font-bold text-gray-800">{{ detalleItem.tipo }}</p>
            </div>
            <button class="btn-cerrar-det" @click="detalleVisible = false">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <p v-if="detalleItem.descripcion" class="text-sm text-gray-500 italic mb-3">
            "{{ detalleItem.descripcion }}"
          </p>

          <!-- Grid info -->
          <div class="det-grid">
            <div class="det-item">
              <span class="det-label">Fecha realizada</span>
              <span class="det-val">{{ fmtFecha(detalleItem.fecha_realizada) }}</span>
            </div>
            <div v-if="detalleItem.taller" class="det-item">
              <span class="det-label">Taller / Mecánico</span>
              <span class="det-val">{{ detalleItem.taller }}</span>
            </div>
            <div v-if="detalleItem.presupuesto" class="det-item">
              <span class="det-label">Presupuesto estimado</span>
              <span class="det-val">{{ fmtPrecio(detalleItem.presupuesto) }}</span>
            </div>
            <div v-if="detalleItem.fecha_programada" class="det-item">
              <span class="det-label">Fecha programada</span>
              <span class="det-val">{{ fmtFecha(detalleItem.fecha_programada) }}</span>
            </div>
          </div>

          <!-- Costo final destacado -->
          <div v-if="detalleItem.costo_real" class="precio-box">
            <p class="precio-label">Costo final</p>
            <p class="precio-val">{{ fmtPrecio(detalleItem.costo_real) }}</p>
            <p v-if="diffPresupuesto(detalleItem) !== null" class="precio-diff">
              <span
                :class="diffPresupuesto(detalleItem) > 0
                  ? 'text-red-500'
                  : diffPresupuesto(detalleItem) < 0
                    ? 'text-green-600'
                    : 'text-gray-400'"
              >
                {{ diffPresupuesto(detalleItem) > 0 ? '▲' : diffPresupuesto(detalleItem) < 0 ? '▼' : '=' }}
                {{ diffPresupuesto(detalleItem) !== 0
                  ? fmtPrecio(Math.abs(diffPresupuesto(detalleItem))) + (diffPresupuesto(detalleItem) > 0 ? ' sobre' : ' bajo') + ' el presupuesto'
                  : 'Igual al presupuesto' }}
              </span>
            </p>
          </div>

          <!-- Foto comprobante -->
          <div v-if="detalleItem.foto_comprobante_url" class="mb-4">
            <p class="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide">📷 Comprobante</p>
            <img
              :src="detalleItem.foto_comprobante_url"
              alt="Comprobante"
              class="w-full max-h-52 object-cover rounded-2xl border border-gray-100"
            />
          </div>

          <!-- Quién completó -->
          <div
            v-if="detalleItem.confirmado_conductor"
            class="completado-banner completado-conductor"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
            <div>
              <p class="text-sm font-bold text-green-700">Completada por ti</p>
              <p v-if="detalleItem.fecha_confirmacion" class="text-xs text-green-600 mt-0.5">
                {{ fmtFecha(detalleItem.fecha_confirmacion) }}
              </p>
            </div>
          </div>
          <div v-else class="completado-banner completado-admin">
            <span class="text-base shrink-0">👤</span>
            <p class="text-sm text-gray-500">Completada por el administrador</p>
          </div>

        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ── Header historial ──────────────────────────────────────────────────── */
.hist-header {
  position: relative; overflow: hidden;
  background: var(--gradient-hero);
  padding: max(1rem, env(safe-area-inset-top)) 1rem 1rem;
}
.hist-header-pattern {
  position: absolute; inset: 0;
  background-image: radial-gradient(circle at 85% 20%, rgba(255,255,255,0.09) 0%, transparent 50%);
}
.hist-header-inner {
  position: relative;
  display: flex; align-items: center; gap: 0.75rem;
}
.hist-back-btn {
  width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%;
  background: rgba(255,255,255,0.18); border: none; color: white;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.hist-back-btn:active { background: rgba(255,255,255,0.30); }
.hist-subtitle {
  font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.65);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.1rem;
}
.hist-title {
  font-size: 1.125rem; font-weight: 800; color: white; line-height: 1.2;
}
.hist-vehicle {
  font-size: 0.6875rem; color: rgba(255,255,255,0.65); margin-top: 0.2rem;
}
.hist-badge {
  margin-left: auto; flex-shrink: 0;
  background: rgba(255,255,255,0.20); border: 1px solid rgba(255,255,255,0.3);
  color: white; font-size: 0.75rem; font-weight: 700;
  border-radius: 999px; padding: 0.2rem 0.75rem;
}

/* ── Skeleton ──────────────────────────────────────────────────────────── */
.hist-skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: 1rem;
}
@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Empty ─────────────────────────────────────────────────────────────── */
.hist-empty-icon {
  width: 72px; height: 72px; border-radius: 24px;
  background: var(--color-acento-suave);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 0.25rem;
}

/* ── Timeline ──────────────────────────────────────────────────────────── */
.timeline-wrap { padding: 1rem 1rem 0; }
.timeline-item {
  display: flex; gap: 0.75rem;
  cursor: pointer;
}
.timeline-item:active .timeline-card { opacity: 0.75; }

.timeline-axis {
  display: flex; flex-direction: column; align-items: center;
  flex-shrink: 0; padding-top: 0.25rem;
  width: 28px;
}
.timeline-dot {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--color-acento-suave);
  border: 2px solid var(--color-acento);
  display: flex; align-items: center; justify-content: center;
  color: var(--color-acento); flex-shrink: 0; z-index: 1;
}
.timeline-line {
  flex: 1; width: 2px;
  background: linear-gradient(to bottom, var(--color-acento) 0%, #E5E7EB 100%);
  opacity: 0.25;
  margin: 0.25rem 0;
  min-height: 1rem;
}

.timeline-card {
  flex: 1; min-width: 0;
  background: white; border-radius: 1rem;
  border: 1px solid #F3F4F6;
  box-shadow: var(--shadow-xs);
  padding: 0.875rem 1rem;
  margin-bottom: 0.875rem;
  transition: opacity 0.1s;
}
.timeline-date {
  font-size: 0.6875rem; font-weight: 600;
  color: var(--color-acento); margin-bottom: 0.4rem;
  text-transform: uppercase; letter-spacing: 0.04em;
}

/* Chips del timeline */
.tl-chip {
  display: inline-flex; align-items: center; gap: 0.2rem;
  font-size: 0.6875rem; font-weight: 600;
  border-radius: 999px; padding: 0.15rem 0.5rem;
}
.tl-chip--green { background: #ECFDF5; color: #059669; }
.tl-chip--gray  { background: #F3F4F6; color: #6B7280; }
.tl-chip--red   { background: #FEF2F2; color: #DC2626; }

/* Overlay detalle */
.overlay-det {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45); backdrop-filter: blur(3px);
  display: flex; align-items: flex-end; justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}
.sheet-det {
  background: #fff;
  border-radius: 1.25rem 1.25rem 0 0;
  width: 100%; max-width: 480px;
  padding: 0 1.25rem;
  padding-bottom: max(1.75rem, env(safe-area-inset-bottom) + 1rem);
  max-height: 88dvh;
  overflow-y: auto;
  animation: slideUp 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.handle-wrap { display: flex; justify-content: center; padding: 0.75rem 0 0.75rem; cursor: pointer; }
.handle { width: 2.5rem; height: 4px; background: #D1D5DB; border-radius: 999px; }

.btn-cerrar-det {
  width: 2.25rem; height: 2.25rem; border-radius: 50%;
  border: 1px solid #E5E7EB; background: #F9FAFB;
  display: flex; align-items: center; justify-content: center;
  color: #6B7280; cursor: pointer; flex-shrink: 0;
}
.btn-cerrar-det svg { width: 16px; height: 16px; }

/* Grid info */
.det-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; margin: 1rem 0; }
.det-item { display: flex; flex-direction: column; gap: 0.2rem; }
.det-label { font-size: 0.7rem; color: #9CA3AF; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.det-val { font-size: 0.8125rem; color: #111827; font-weight: 600; }

/* Costo */
.precio-box { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 1rem; padding: 1rem; text-align: center; margin-bottom: 1rem; }
.precio-label { font-size: 0.7rem; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.precio-val { font-size: 2rem; font-weight: 800; color: #111827; letter-spacing: -0.02em; }
.precio-diff { font-size: 0.75rem; margin-top: 0.375rem; }
.text-red-500   { color: #EF4444; }
.text-green-600 { color: #059669; }
.text-gray-400  { color: #9CA3AF; }

/* Banners */
.completado-banner { display: flex; align-items: flex-start; gap: 0.625rem; border-radius: 0.875rem; padding: 0.875rem 1rem; }
.completado-conductor { background: #ECFDF5; border: 1px solid #6EE7B7; }
.completado-admin { background: #F9FAFB; border: 1px solid #E5E7EB; }

@keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
@keyframes slideUp { from { transform: translateY(100%) } to { transform: translateY(0) } }
</style>
