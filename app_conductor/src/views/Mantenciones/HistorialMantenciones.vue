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
    <!-- Header con botón volver -->
    <header class="bg-white border-b border-gray-100 px-4 pt-safe pb-3 sticky top-0 z-10">
      <div class="flex items-center gap-3">
        <button
          class="w-9 h-9 flex items-center justify-center rounded-xl bg-gray-100 text-gray-600 active:opacity-70"
          @click="router.back()"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="min-w-0">
          <h1 class="text-base font-bold text-gray-800 leading-tight">Historial de mantenciones</h1>
          <p v-if="vehiculo" class="text-xs text-gray-400 mt-0.5">
            {{ vehiculo.patente }} · {{ vehiculo.marca }} {{ vehiculo.modelo }}
          </p>
        </div>
        <!-- Contador total -->
        <span
          v-if="total > 0"
          class="ml-auto text-xs font-semibold bg-gray-100 text-gray-500 rounded-full px-2.5 py-1 shrink-0"
        >
          {{ total }} registro{{ total !== 1 ? 's' : '' }}
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
      <div v-for="i in 4" :key="i" class="h-24 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <!-- Estado vacío -->
    <div
      v-else-if="!cargando && !historial.length && !error"
      class="flex flex-col items-center gap-3 py-20 text-gray-400 px-6"
    >
      <svg class="w-14 h-14 text-gray-200" fill="none" stroke="currentColor" stroke-width="1.3" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <p class="text-base font-medium text-gray-500">Sin historial aún</p>
      <p class="text-sm text-center leading-relaxed">
        Aquí aparecerán las mantenciones realizadas<br>a tu vehículo.
      </p>
    </div>

    <!-- Lista -->
    <div v-else class="px-4 mt-4 flex flex-col gap-3 pb-6">
      <article
        v-for="m in historial"
        :key="m.id"
        class="bg-white rounded-2xl border border-gray-200 p-4 cursor-pointer active:opacity-75 shadow-sm"
        @click="verDetalle(m)"
      >
        <!-- Fila superior: tipo + fecha -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-xl shrink-0">🔧</span>
            <p class="text-sm font-bold text-gray-800 leading-tight truncate">{{ m.tipo }}</p>
          </div>
          <p class="text-xs text-gray-400 shrink-0 mt-0.5">{{ fmtFecha(m.fecha_realizada) }}</p>
        </div>

        <!-- Costo final + badge quién completó -->
        <div class="flex items-center justify-between gap-2">
          <div>
            <p class="text-xs text-gray-400 font-medium mb-0.5">Costo final</p>
            <p class="text-lg font-extrabold text-gray-900 leading-tight">{{ fmtPrecio(m.costo_real) }}</p>
          </div>
          <div class="flex flex-col items-end gap-1.5">
            <!-- Quién completó -->
            <span
              v-if="m.confirmado_conductor"
              class="inline-flex items-center gap-1 text-[10px] font-semibold bg-green-50 text-green-700 rounded-full px-2 py-0.5"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              Completada por ti
            </span>
            <span v-else class="inline-flex items-center gap-1 text-[10px] font-semibold bg-gray-100 text-gray-500 rounded-full px-2 py-0.5">
              👤 Por administrador
            </span>
            <!-- Diferencia vs presupuesto -->
            <span
              v-if="diffPresupuesto(m) !== null"
              :class="diffPresupuesto(m) > 0
                ? 'bg-red-50 text-red-600'
                : diffPresupuesto(m) < 0
                  ? 'bg-green-50 text-green-700'
                  : 'bg-gray-100 text-gray-500'"
              class="text-[10px] font-semibold rounded-full px-2 py-0.5"
            >
              {{ diffPresupuesto(m) > 0 ? '▲' : diffPresupuesto(m) < 0 ? '▼' : '=' }}
              {{ diffPresupuesto(m) > 0 ? '+' : '' }}{{ fmtPrecio(Math.abs(diffPresupuesto(m))) }}
              vs presupuesto
            </span>
          </div>
        </div>

        <!-- Miniatura foto + taller -->
        <div class="flex items-center gap-2 mt-3">
          <img
            v-if="m.foto_comprobante_url"
            :src="m.foto_comprobante_url"
            alt="Comprobante"
            class="w-12 h-12 object-cover rounded-xl border border-gray-100 shrink-0"
          />
          <div class="min-w-0">
            <p v-if="m.taller" class="text-xs text-gray-500 truncate">
              🏪 {{ m.taller }}
            </p>
            <p v-if="m.descripcion" class="text-xs text-gray-400 italic truncate mt-0.5">
              "{{ m.descripcion }}"
            </p>
          </div>
          <svg class="w-4 h-4 text-gray-300 ml-auto shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </div>
      </article>

      <!-- Cargar más -->
      <button
        v-if="hasMore"
        class="w-full py-3 text-sm font-semibold text-[var(--color-acento)] bg-white border border-gray-200 rounded-2xl active:opacity-70 mt-1"
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
.pt-safe  { padding-top: max(1rem, env(safe-area-inset-top)); }
.pb-safe-bottom { padding-bottom: max(1.5rem, env(safe-area-inset-bottom) + 1rem); }

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
