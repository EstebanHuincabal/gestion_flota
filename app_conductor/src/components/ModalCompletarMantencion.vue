<script setup>
/**
 * ModalCompletarMantencion.vue
 *
 * Bottom-sheet con formulario para que el conductor marque una mantención
 * como realizada, ingresando el costo final y opcionalmente una foto.
 *
 * Props:
 *   mantencion (Object) — mantención en estado en_proceso
 *
 * Emits:
 *   cerrar              — usuario cancela
 *   completada(result)  — completado exitosamente; result = { mantencion, gasto_id }
 */
import { ref, watch } from 'vue'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import { useModeracion } from '@/composables/useModeracion.js'

const props = defineProps({
  mantencion: { type: Object, required: true },
})
const emit = defineEmits(['cerrar', 'completada'])

const store      = useMantencionesStore()
const guardando  = ref(false)
const errores    = ref({})
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()

// ── Formulario ────────────────────────────────────────────────────────────────
const hoy = new Date().toISOString().split('T')[0]
const form = ref({
  costo_final:     '',
  fecha_realizada: hoy,
  notas:           '',
})

watch(() => form.value.notas, () => {
  if (avisoMod.value) limpiarMod()
})
const fotoFile    = ref(null)
const fotoPreview = ref(null)

// Formatear como CLP mientras se escribe
const costoDisplay = ref('')
function onCostoInput(e) {
  const raw = e.target.value.replace(/\D/g, '')
  costoDisplay.value = raw ? Number(raw).toLocaleString('es-CL') : ''
  form.value.costo_final = raw
}

function onFotoSeleccionada(e) {
  const file = e.target.files?.[0]
  if (!file) return
  fotoFile.value = file
  const reader = new FileReader()
  reader.onload = (ev) => { fotoPreview.value = ev.target.result }
  reader.readAsDataURL(file)
}

function quitarFoto() {
  fotoFile.value    = null
  fotoPreview.value = null
}

// ── Validar y enviar ──────────────────────────────────────────────────────────
async function confirmar() {
  errores.value = {}

  const costo = Number(form.value.costo_final)
  if (!costo || costo <= 0) {
    errores.value.costo = 'Ingresa el costo final (mayor a $0).'
    return
  }
  if (form.value.fecha_realizada > hoy) {
    errores.value.fecha = 'La fecha realizada no puede ser futura.'
    return
  }

  if (form.value.notas && form.value.notas.trim().length >= 3) {
    const ok = await moderar(form.value.notas)
    if (!ok) return
  }

  guardando.value = true
  try {
    const fd = new FormData()
    fd.append('costo_final',     form.value.costo_final)
    fd.append('fecha_realizada', form.value.fecha_realizada)
    if (form.value.notas) fd.append('notas', form.value.notas)
    if (fotoFile.value)   fd.append('foto_comprobante', fotoFile.value)

    const result = await store.completarMantencion(props.mantencion.id, fd)
    emit('completada', result)
  } catch (e) {
    errores.value.global = e?.message || 'Error al completar. Intenta nuevamente.'
  } finally {
    guardando.value = false
  }
}

function fmtPrecio(v) {
  if (!v) return null
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(v)
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('cerrar')">
      <div class="sheet">

        <!-- Agarradera -->
        <div class="handle-wrap" @click="$emit('cerrar')">
          <span class="handle"/>
        </div>

        <!-- Encabezado -->
        <div class="header">
          <div>
            <p class="titulo">Marcar como Realizada</p>
            <p class="subtitulo">🔧 {{ mantencion.tipo }}</p>
          </div>
          <button class="btn-cerrar" @click="$emit('cerrar')">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Presupuesto referencial -->
        <div v-if="mantencion.presupuesto" class="presup-ref">
          <svg class="w-4 h-4 text-blue-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>Presupuesto estimado: <strong>{{ fmtPrecio(mantencion.presupuesto) }}</strong></span>
        </div>

        <!-- Error global -->
        <div v-if="errores.global" class="error-global">{{ errores.global }}</div>

        <!-- Formulario -->
        <div class="form">

          <!-- Costo final -->
          <div class="campo">
            <label class="label">Costo final ($) <span class="req">*</span></label>
            <div class="input-prefix-wrap">
              <span class="input-prefix">$</span>
              <input
                :value="costoDisplay"
                @input="onCostoInput"
                class="input input-con-prefix"
                inputmode="numeric"
                placeholder="0"
                autocomplete="off"
              />
            </div>
            <p v-if="errores.costo" class="error-campo">{{ errores.costo }}</p>
          </div>

          <!-- Fecha realizada -->
          <div class="campo">
            <label class="label">Fecha realizada</label>
            <input
              v-model="form.fecha_realizada"
              type="date"
              class="input"
              :max="hoy"
            />
            <p v-if="errores.fecha" class="error-campo">{{ errores.fecha }}</p>
          </div>

          <!-- Foto comprobante -->
          <div class="campo">
            <label class="label">Foto del recibo <span class="label-opt">(opcional)</span></label>

            <div v-if="fotoPreview" class="foto-preview-wrap">
              <img :src="fotoPreview" alt="Vista previa" class="foto-preview"/>
              <button type="button" class="foto-quitar" @click="quitarFoto">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <label v-else class="foto-drop">
              <svg class="foto-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <span class="foto-texto">Toca para agregar foto</span>
              <input type="file" accept="image/*" capture="environment" @change="onFotoSeleccionada" class="hidden-input"/>
            </label>
          </div>

          <!-- Notas -->
          <div class="campo">
            <label class="label">Notas <span class="label-opt">(opcional)</span></label>
            <textarea
              v-model="form.notas"
              class="input textarea"
              rows="2"
              placeholder="Observaciones sobre el servicio..."
            />
            <div v-if="avisoMod" class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 mt-1">
              <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M5 19h14a2 2 0 001.732-1l-7-12a2 2 0 00-3.464 0L3.268 18A2 2 0 005 20z"/>
              </svg>
              <div>
                <p class="text-xs text-amber-700 font-semibold" style="margin:0">{{ avisoMod }}</p>
                <p v-if="sugerenciaMod" class="text-xs text-amber-600" style="margin:0.25rem 0 0">{{ sugerenciaMod }}</p>
              </div>
            </div>
          </div>

        </div><!-- /form -->

        <!-- Acciones -->
        <div class="acciones">
          <button class="btn-cancelar" :disabled="guardando" @click="$emit('cerrar')">
            Cancelar
          </button>
          <button class="btn-confirmar" :disabled="guardando" @click="confirmar">
            <span v-if="guardando" class="spinner"/>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
            </svg>
            {{ guardando ? 'Guardando…' : 'Marcar realizada' }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* Overlay */
.overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5); backdrop-filter: blur(3px);
  display: flex; align-items: flex-end; justify-content: center;
  z-index: 1100;
  animation: fadeIn 0.2s ease;
}

/* Sheet */
.sheet {
  background: #fff;
  border-radius: 1.25rem 1.25rem 0 0;
  width: 100%; max-width: 480px;
  padding: 0 1.25rem;
  padding-bottom: max(1.5rem, env(safe-area-inset-bottom) + 1rem);
  max-height: 92dvh;
  overflow-y: auto;
  animation: slideUp 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.handle-wrap { display: flex; justify-content: center; padding: 0.75rem 0 0.25rem; cursor: pointer; }
.handle { width: 2.5rem; height: 4px; background: #D1D5DB; border-radius: 999px; }

/* Encabezado */
.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1rem; }
.titulo { font-size: 1rem; font-weight: 700; color: #111827; }
.subtitulo { font-size: 0.8125rem; color: #6B7280; margin-top: 0.125rem; }
.btn-cerrar { width: 2.25rem; height: 2.25rem; border-radius: 50%; border: 1px solid #E5E7EB; background: #F9FAFB; display: flex; align-items: center; justify-content: center; color: #6B7280; cursor: pointer; flex-shrink: 0; }
.btn-cerrar svg { width: 16px; height: 16px; }

/* Presupuesto referencial */
.presup-ref { display: flex; align-items: center; gap: 0.5rem; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 0.75rem; padding: 0.625rem 0.875rem; font-size: 0.8125rem; color: #1D4ED8; margin-bottom: 1rem; }
.w-4 { width: 1rem; }
.h-4 { height: 1rem; }
.shrink-0 { flex-shrink: 0; }

/* Error global */
.error-global { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; font-size: 0.8125rem; padding: 0.625rem 0.875rem; border-radius: 0.75rem; margin-bottom: 1rem; }

/* Formulario */
.form { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.25rem; }
.campo { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.label-opt { font-weight: 400; color: #9CA3AF; }
.req { color: #EF4444; }

.input { padding: 0.7rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 0.75rem; font-size: 0.9375rem; width: 100%; outline: none; font-family: inherit; background: #fff; }
.input:focus { border-color: var(--color-acento, #4F46E5); box-shadow: 0 0 0 3px rgba(79,70,229,0.12); }

.input-prefix-wrap { position: relative; }
.input-prefix { position: absolute; left: 0.875rem; top: 50%; transform: translateY(-50%); font-size: 0.9375rem; font-weight: 600; color: #374151; pointer-events: none; }
.input-con-prefix { padding-left: 1.75rem; }

.textarea { resize: none; line-height: 1.5; }
.error-campo { font-size: 0.75rem; color: #EF4444; margin: 0; }

/* Foto */
.foto-drop { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; border: 2px dashed #D1D5DB; border-radius: 0.875rem; padding: 1.25rem; cursor: pointer; transition: border-color 0.15s; }
.foto-drop:hover { border-color: var(--color-acento, #4F46E5); }
.foto-icon { width: 2rem; height: 2rem; color: #9CA3AF; }
.foto-texto { font-size: 0.8125rem; color: #6B7280; }
.hidden-input { display: none; }
.foto-preview-wrap { position: relative; }
.foto-preview { width: 100%; max-height: 180px; object-fit: cover; border-radius: 0.875rem; border: 1px solid #E5E7EB; }
.foto-quitar { position: absolute; top: 0.5rem; right: 0.5rem; width: 1.75rem; height: 1.75rem; border-radius: 50%; background: rgba(0,0,0,0.55); border: none; color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.foto-quitar svg { width: 14px; height: 14px; }

/* Acciones */
.acciones { display: flex; gap: 0.75rem; }
.btn-cancelar { flex: 1; padding: 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 0.875rem; background: #fff; font-size: 0.9375rem; font-weight: 600; color: #374151; cursor: pointer; min-height: 48px; }
.btn-cancelar:disabled { opacity: 0.5; }
.btn-confirmar { flex: 2; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.875rem; border: none; border-radius: 0.875rem; background: linear-gradient(135deg, #059669, #047857); color: #fff; font-size: 0.9375rem; font-weight: 700; cursor: pointer; min-height: 48px; transition: opacity 0.15s; }
.btn-confirmar:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-confirmar:not(:disabled):active { opacity: 0.85; }
.w-5 { width: 1.25rem; }
.h-5 { height: 1.25rem; }
.spinner { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }

/* Animaciones */
@keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
@keyframes slideUp { from { transform: translateY(100%) } to { transform: translateY(0) } }
@keyframes spin    { to { transform: rotate(360deg) } }
</style>
