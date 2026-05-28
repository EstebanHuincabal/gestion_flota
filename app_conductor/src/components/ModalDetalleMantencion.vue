<script setup>
/**
 * ModalDetalleMantencion.vue
 *
 * Bottom-sheet modal con el detalle completo de una mantención.
 * Acciones disponibles según estado:
 *
 *  • pendiente  → "Iniciar mantención"  (pendiente → en_proceso)
 *  • en_proceso → "Marcar como realizada" → abre ModalCompletarMantencion
 *  • realizada  → solo info (precio, foto, quién completó)
 *
 * Props:
 *   mantencion (Object)  — datos del ítem (del store o endpoint detalle)
 *   cargando   (Boolean) — spinner mientras se carga el detalle completo
 *
 * Emits:
 *   cerrar          — usuario cierra el modal
 *   iniciada(m)     — conductor inició; m = mantención actualizada
 *   completada(res) — conductor completó; res = { mantencion, gasto_id }
 */
import { ref, computed } from 'vue'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import ModalCompletarMantencion from './ModalCompletarMantencion.vue'

const props = defineProps({
  mantencion: { type: Object, required: true },
  cargando:   { type: Boolean, default: false },
})
const emit = defineEmits(['cerrar', 'iniciada', 'completada'])

const store          = useMantencionesStore()
const iniciando      = ref(false)
const mostrarIniciar = ref(false)
const errorAccion    = ref('')
const mostrarCompletar = ref(false)
const fotoAmpliada   = ref(null)

// ── Helpers ────────────────────────────────────────────────────────────────

const ESTADO_MAP = {
  pendiente:  { label: 'Pendiente',  color: '#185FA5', bg: '#E6F1FB' },
  en_proceso: { label: 'En proceso', color: '#B45309', bg: '#FEF3C7' },
  realizada:  { label: 'Realizada',  color: '#065F46', bg: '#D1FAE5' },
}

const badge = computed(() =>
  ESTADO_MAP[props.mantencion?.estado] || { label: props.mantencion?.estado, color: '#555', bg: '#eee' }
)

const fmtFecha = (iso) => {
  if (!iso) return '—'
  return new Date(iso + (iso.length === 10 ? 'T00:00' : '')).toLocaleDateString('es-CL', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

const fmtPrecio = (v) => {
  if (!v) return null
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(v)
}

// ── Iniciar mantención: pendiente → en_proceso ─────────────────────────────

async function ejecutarIniciar() {
  iniciando.value      = true
  errorAccion.value    = ''
  mostrarIniciar.value = false
  try {
    const mantencionActualizada = await store.iniciarMantencion(props.mantencion.id)
    emit('iniciada', mantencionActualizada)
    setTimeout(() => emit('cerrar'), 600)
  } catch (e) {
    errorAccion.value = e?.message || 'Error al iniciar. Intenta nuevamente.'
  } finally {
    iniciando.value = false
  }
}

// ── Completar mantención: en_proceso → realizada ───────────────────────────

function onCompletada(result) {
  mostrarCompletar.value = false
  emit('completada', result)
  emit('cerrar')
}
</script>

<template>
  <!-- Overlay principal -->
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('cerrar')">

      <!-- Bottom-sheet -->
      <div class="sheet">

        <!-- Agarradera -->
        <div class="handle-wrap" @click="$emit('cerrar')">
          <span class="handle"/>
        </div>

        <!-- Cargando detalle -->
        <div v-if="cargando" class="loading-state">
          <span class="spinner"/>
          <p class="text-sm text-gray-400">Cargando detalle…</p>
        </div>

        <template v-else>
          <!-- ── Encabezado ── -->
          <div class="header-row">
            <div class="flex items-center gap-2 flex-1 min-w-0">
              <span class="text-2xl shrink-0">🔧</span>
              <div class="min-w-0">
                <p class="tipo">{{ mantencion.tipo }}</p>
                <span
                  class="badge-estado"
                  :style="`color:${badge.color}; background:${badge.bg}`"
                >{{ badge.label }}</span>
              </div>
            </div>
            <button class="btn-cerrar" @click="$emit('cerrar')">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- ── Descripción ── -->
          <p v-if="mantencion.descripcion" class="descripcion">
            "{{ mantencion.descripcion }}"
          </p>

          <!-- ── Grid de info ── -->
          <div class="info-grid">
            <div v-if="mantencion.fecha_programada" class="info-item">
              <span class="info-label">Fecha programada</span>
              <span class="info-valor">{{ fmtFecha(mantencion.fecha_programada) }}</span>
            </div>
            <div v-if="mantencion.fecha_realizada" class="info-item">
              <span class="info-label">Fecha realizada</span>
              <span class="info-valor">{{ fmtFecha(mantencion.fecha_realizada) }}</span>
            </div>
            <div v-if="mantencion.taller" class="info-item">
              <span class="info-label">Taller / Mecánico</span>
              <span class="info-valor">{{ mantencion.taller }}</span>
            </div>
            <div v-if="mantencion.presupuesto" class="info-item">
              <span class="info-label">Presupuesto estimado</span>
              <span class="info-valor">{{ fmtPrecio(mantencion.presupuesto) }}</span>
            </div>
          </div>

          <!-- ═══════════════════════════════════════════════════════════════
               ESTADO: realizada — info del resultado
               ═══════════════════════════════════════════════════════════════ -->
          <template v-if="mantencion.estado === 'realizada'">
            <div class="divider"/>

            <!-- Foto comprobante -->
            <div v-if="mantencion.foto_comprobante_url" class="foto-wrap">
              <p class="seccion-titulo">📷 Comprobante</p>
              <img
                :src="mantencion.foto_comprobante_url"
                alt="Comprobante de mantención"
                class="foto-comprobante"
                @click="fotoAmpliada = mantencion.foto_comprobante_url"
              />
              <p class="foto-hint">Toca para ampliar</p>
            </div>

            <!-- Costo final -->
            <div v-if="mantencion.costo_real" class="precio-final-wrap">
              <p class="precio-label">Costo final</p>
              <p class="precio-valor">{{ fmtPrecio(mantencion.costo_real) }}</p>
              <p v-if="mantencion.presupuesto" class="precio-diff">
                <template v-if="mantencion.costo_real > mantencion.presupuesto">
                  <span class="text-red-500">▲ {{ fmtPrecio(mantencion.costo_real - mantencion.presupuesto) }} sobre el presupuesto</span>
                </template>
                <template v-else-if="mantencion.costo_real < mantencion.presupuesto">
                  <span class="text-green-600">▼ {{ fmtPrecio(mantencion.presupuesto - mantencion.costo_real) }} bajo el presupuesto</span>
                </template>
                <template v-else>
                  <span class="text-gray-500">Igual al presupuesto estimado</span>
                </template>
              </p>
            </div>

            <!-- Banner: completada por el conductor -->
            <div v-if="mantencion.confirmado_conductor" class="completed-banner">
              <svg class="icon-ok" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              <div>
                <p class="completed-title">Marcada como realizada por ti</p>
                <p v-if="mantencion.fecha_confirmacion" class="completed-sub">
                  {{ fmtFecha(mantencion.fecha_confirmacion) }}
                </p>
              </div>
            </div>

            <!-- Banner: completada por el administrador -->
            <div v-else class="admin-banner">
              <span class="admin-icon">👤</span>
              <p class="admin-texto">Marcada como realizada por el administrador</p>
            </div>
          </template>

          <!-- ═══════════════════════════════════════════════════════════════
               ESTADO: pendiente — botón "Iniciar mantención"
               ═══════════════════════════════════════════════════════════════ -->
          <template v-else-if="mantencion.estado === 'pendiente'">

            <!-- Alertas de urgencia -->
            <div v-if="mantencion.urgente && mantencion.dias_restantes !== null && mantencion.dias_restantes >= 0"
              class="alerta-chip alerta-naranja"
            >
              ⚠️ Mantención próxima — coordina con tu administrador
            </div>
            <div v-else-if="mantencion.dias_restantes !== null && mantencion.dias_restantes < 0"
              class="alerta-chip alerta-roja"
            >
              🔴 Mantención vencida — contacta a tu administrador
            </div>

            <div class="divider"/>

            <!-- Error -->
            <p v-if="errorAccion" class="error-accion">{{ errorAccion }}</p>

            <!-- CTA: Iniciar -->
            <div class="cta-wrap">
              <p class="cta-hint">
                Al iniciar, el vehículo quedará marcado en mantención y no podrá asignarse a rutas.
              </p>
              <button
                class="btn-accion btn-iniciar"
                :disabled="iniciando"
                @click="mostrarIniciar = true"
              >
                <span v-if="iniciando" class="spinner-btn"/>
                <svg v-else class="icon-btn" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                {{ iniciando ? 'Iniciando…' : 'Iniciar mantención' }}
              </button>
            </div>
          </template>

          <!-- ═══════════════════════════════════════════════════════════════
               ESTADO: en_proceso — botón "Marcar como realizada"
               ═══════════════════════════════════════════════════════════════ -->
          <template v-else-if="mantencion.estado === 'en_proceso'">

            <div class="divider"/>

            <!-- Banner informativo -->
            <div class="en-proceso-banner">
              <svg class="icon-proceso" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p class="proceso-texto">Mantención en curso. Cuando termines, regístrala con el costo final.</p>
            </div>

            <!-- Error -->
            <p v-if="errorAccion" class="error-accion">{{ errorAccion }}</p>

            <!-- CTA: Completar -->
            <div class="cta-wrap">
              <button
                class="btn-accion btn-completar"
                @click="mostrarCompletar = true"
              >
                <svg class="icon-btn" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
                Marcar como realizada
              </button>
            </div>
          </template>

        </template><!-- /v-else (no cargando) -->
      </div><!-- /sheet -->

    </div><!-- /overlay -->

    <!-- ── Mini-confirm: Iniciar mantención ── -->
    <div v-if="mostrarIniciar" class="overlay overlay-front" @click.self="mostrarIniciar = false">
      <div class="mini-modal">
        <p class="mini-titulo">¿Iniciar mantención?</p>
        <p class="mini-cuerpo">
          Tu vehículo quedará marcado como <strong>en mantención</strong> y no podrá asignarse a rutas hasta que registres la finalización.
        </p>
        <div class="mini-actions">
          <button class="btn-mini-cancel" @click="mostrarIniciar = false">Cancelar</button>
          <button class="btn-mini-ok" @click="ejecutarIniciar">
            Sí, iniciar
          </button>
        </div>
      </div>
    </div>

    <!-- ── Modal para completar (en_proceso → realizada) ── -->
    <ModalCompletarMantencion
      v-if="mostrarCompletar"
      :mantencion="mantencion"
      @cerrar="mostrarCompletar = false"
      @completada="onCompletada"
    />

  </Teleport>

  <!-- ── Foto ampliada fullscreen ────────────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="fade-foto">
      <div
        v-if="fotoAmpliada"
        class="overlay"
        style="z-index: 1100; background: rgba(0,0,0,0.95); align-items: center; justify-content: center; flex-direction: column;"
        @click="fotoAmpliada = null"
      >
        <div style="position:absolute; top:0; left:0; right:0; display:flex; align-items:center; padding: max(1rem, env(safe-area-inset-top)) 1rem 0.75rem;">
          <button style="width:2.25rem;height:2.25rem;border-radius:50%;background:rgba(255,255,255,0.15);border:none;color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <img :src="fotoAmpliada" alt="Foto completa"
          style="max-width:100%; max-height:100%; object-fit:contain; padding:4rem 1rem 1rem;"
          @click.stop
        />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ── Overlay ──────────────────────────────────────────────────────────── */
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  backdrop-filter: blur(3px);
  display: flex; align-items: flex-end; justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}
.overlay-front { z-index: 1050; align-items: center; }

/* ── Bottom-sheet ─────────────────────────────────────────────────────── */
.sheet {
  background: #fff;
  border-radius: 1.25rem 1.25rem 0 0;
  width: 100%; max-width: 480px;
  padding: 0 1.25rem 2rem;
  padding-bottom: max(2rem, env(safe-area-inset-bottom) + 1.5rem);
  max-height: 90dvh;
  overflow-y: auto;
  animation: slideUp 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.handle-wrap { display: flex; justify-content: center; padding: 0.75rem 0 0.25rem; cursor: pointer; }
.handle { width: 2.5rem; height: 4px; background: #D1D5DB; border-radius: 999px; }

/* ── Encabezado ───────────────────────────────────────────────────────── */
.header-row { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.75rem; }
.tipo { font-size: 1rem; font-weight: 700; color: #111827; line-height: 1.3; }
.badge-estado { display: inline-block; font-size: 0.7rem; font-weight: 600; border-radius: 999px; padding: 0.2rem 0.6rem; margin-top: 0.25rem; }
.btn-cerrar { flex-shrink: 0; width: 2.25rem; height: 2.25rem; border-radius: 50%; border: 1px solid #E5E7EB; background: #F9FAFB; display: flex; align-items: center; justify-content: center; color: #6B7280; cursor: pointer; }
.btn-cerrar svg { width: 16px; height: 16px; }

/* ── Utilidades de layout ─────────────────────────────────────────────── */
.flex { display: flex; }
.items-center { align-items: center; }
.gap-2 { gap: 0.5rem; }
.flex-1 { flex: 1; }
.min-w-0 { min-width: 0; }
.shrink-0 { flex-shrink: 0; }
.text-2xl { font-size: 1.5rem; }

/* ── Descripción ──────────────────────────────────────────────────────── */
.descripcion { font-size: 0.8125rem; color: #6B7280; font-style: italic; line-height: 1.5; margin-bottom: 1rem; }

/* ── Grid info ────────────────────────────────────────────────────────── */
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem 1rem; margin-bottom: 0.75rem; }
.info-item { display: flex; flex-direction: column; gap: 0.2rem; }
.info-label { font-size: 0.7rem; color: #9CA3AF; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.info-valor { font-size: 0.8125rem; color: #111827; font-weight: 600; }

/* ── Divider ──────────────────────────────────────────────────────────── */
.divider { height: 1px; background: #F3F4F6; margin: 0.75rem 0; }

/* ── Foto comprobante ─────────────────────────────────────────────────── */
.foto-wrap { margin-bottom: 1rem; }
.seccion-titulo { font-size: 0.8125rem; font-weight: 700; color: #374151; margin-bottom: 0.5rem; }
.foto-comprobante { width: 100%; max-height: 280px; object-fit: contain; background: #F9FAFB; border-radius: 0.875rem; border: 1px solid #E5E7EB; cursor: zoom-in; }
.foto-hint { font-size: 0.7rem; color: #9CA3AF; text-align: center; margin-top: 0.375rem; }

/* ── Precio final ─────────────────────────────────────────────────────── */
.precio-final-wrap { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 1rem; padding: 1rem; text-align: center; margin-bottom: 1rem; }
.precio-label { font-size: 0.75rem; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.precio-valor { font-size: 2rem; font-weight: 800; color: #111827; letter-spacing: -0.02em; }
.precio-diff { font-size: 0.75rem; margin-top: 0.375rem; }
.text-red-500 { color: #EF4444; }
.text-green-600 { color: #059669; }
.text-gray-500 { color: #6B7280; }

/* ── Banner completado por conductor ──────────────────────────────────── */
.completed-banner {
  display: flex; align-items: flex-start; gap: 0.625rem;
  background: #ECFDF5; border: 1px solid #6EE7B7;
  border-radius: 0.875rem; padding: 0.875rem 1rem; margin-bottom: 0.75rem;
}
.icon-ok { width: 1.25rem; height: 1.25rem; color: #059669; flex-shrink: 0; }
.completed-title { font-size: 0.875rem; font-weight: 700; color: #065F46; }
.completed-sub   { font-size: 0.75rem; color: #059669; margin-top: 0.125rem; }

/* ── Banner completado por admin ──────────────────────────────────────── */
.admin-banner {
  display: flex; align-items: center; gap: 0.5rem;
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 0.875rem; padding: 0.75rem 1rem; margin-bottom: 0.75rem;
}
.admin-icon { font-size: 1.1rem; flex-shrink: 0; }
.admin-texto { font-size: 0.8125rem; color: #6B7280; }

/* ── Alerta urgencia ──────────────────────────────────────────────────── */
.alerta-chip { font-size: 0.8125rem; font-weight: 600; border-radius: 0.875rem; padding: 0.75rem 1rem; margin-top: 0.75rem; }
.alerta-naranja { background: #FFF7ED; color: #9A3412; }
.alerta-roja    { background: #FEF2F2; color: #991B1B; }

/* ── En proceso: banner info ──────────────────────────────────────────── */
.en-proceso-banner {
  display: flex; align-items: flex-start; gap: 0.625rem;
  background: #FFFBEB; border: 1px solid #FDE68A;
  border-radius: 0.875rem; padding: 0.75rem 1rem; margin-bottom: 0.75rem;
}
.icon-proceso { width: 1.125rem; height: 1.125rem; color: #D97706; flex-shrink: 0; margin-top: 0.125rem; }
.proceso-texto { font-size: 0.8125rem; color: #92400E; line-height: 1.4; }

/* ── Error acción ─────────────────────────────────────────────────────── */
.error-accion { font-size: 0.8125rem; color: #991B1B; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 0.75rem; padding: 0.625rem 0.875rem; margin-bottom: 0.75rem; }

/* ── CTAs ─────────────────────────────────────────────────────────────── */
.cta-wrap { margin-top: 0.25rem; }
.cta-hint { font-size: 0.75rem; color: #6B7280; line-height: 1.5; margin-bottom: 0.875rem; text-align: center; }

.btn-accion {
  width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  padding: 0.9rem 1.5rem;
  color: #fff; font-size: 0.9375rem; font-weight: 700;
  border: none; border-radius: 1rem; cursor: pointer;
  transition: opacity 0.15s; min-height: 48px;
}
.btn-accion:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-accion:not(:disabled):active { opacity: 0.85; }

.btn-iniciar  { background: linear-gradient(135deg, #2563EB, #1D4ED8); }
.btn-completar { background: linear-gradient(135deg, #059669, #047857); }

.icon-btn { width: 1.25rem; height: 1.25rem; }
.spinner-btn { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }

/* ── Loading state ────────────────────────────────────────────────────── */
.loading-state { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; padding: 2rem; }
.spinner { width: 28px; height: 28px; border: 3px solid #E5E7EB; border-top-color: var(--color-acento, #4F46E5); border-radius: 50%; animation: spin 0.8s linear infinite; }
.text-sm    { font-size: 0.875rem; }
.text-gray-400 { color: #9CA3AF; }

/* ── Mini-modal ───────────────────────────────────────────────────────── */
.mini-modal { background: #fff; border-radius: 1rem; padding: 1.5rem; width: calc(100% - 2rem); max-width: 360px; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
.mini-titulo { font-size: 1rem; font-weight: 700; color: #111827; margin-bottom: 0.625rem; }
.mini-cuerpo { font-size: 0.875rem; color: #6B7280; line-height: 1.5; margin-bottom: 1.25rem; }
.mini-actions { display: flex; gap: 0.625rem; justify-content: flex-end; }
.btn-mini-cancel { padding: 0.6rem 1.1rem; border: 1px solid #D1D5DB; border-radius: 0.625rem; background: #fff; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; }
.btn-mini-ok { padding: 0.6rem 1.25rem; border: none; border-radius: 0.625rem; background: linear-gradient(135deg,#2563EB,#1D4ED8); color: #fff; font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-mini-ok:hover { opacity: 0.9; }

/* ── Animaciones ──────────────────────────────────────────────────────── */
@keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
@keyframes slideUp { from { transform: translateY(100%) } to { transform: translateY(0) } }
@keyframes spin    { to { transform: rotate(360deg) } }

.fade-foto-enter-active, .fade-foto-leave-active { transition: opacity 0.2s ease; }
.fade-foto-enter-from,   .fade-foto-leave-to     { opacity: 0; }
</style>
