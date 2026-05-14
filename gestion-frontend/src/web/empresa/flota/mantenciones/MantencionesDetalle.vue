<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../../utils/permisos.js'
import { useToast } from '../../../../utils/useToast.js'

const route  = useRoute()
const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = useToast()

const id         = route.params.id
const mantencion = ref(null)
const cargando   = ref(true)
const error404   = ref(false)

const mostrarFormCompletar = ref(false)
const formCompletar        = ref({ fecha_realizada: '', costo: '' })
const erroresCompletar     = ref({})
const guardando            = ref(false)

const cargar = async () => {
  cargando.value = true
  const res = await apiFetchEmpresa(`/api/empresa/mantenciones/${id}/`)
  if (res.ok) {
    mantencion.value = await res.json()
  } else if (res.status === 404) {
    error404.value = true
  }
  cargando.value = false
}

const formatFecha = (f) => f ? new Date(f + 'T12:00:00').toLocaleDateString('es-CL') : '—'
const formatMonto = (v) => (v !== null && v !== undefined && v !== '') ? '$' + Number(v).toLocaleString('es-CL') : '—'

const ESTADOS_ORDEN  = ['pendiente', 'en_proceso', 'realizada']
const LABELS_ESTADO  = { pendiente: 'Pendiente', en_proceso: 'En Proceso', realizada: 'Realizada' }

const estadoActual  = computed(() => mantencion.value?.estado)
const estadoIndex   = computed(() => ESTADOS_ORDEN.indexOf(estadoActual.value))
const cancelada     = computed(() => estadoActual.value === 'cancelada')

const badgeClase = (estado) => ({
  pendiente:  'badge-warning',
  en_proceso: 'badge-info',
  realizada:  'badge-success',
  cancelada:  'badge-gray',
}[estado] || 'badge-warning')

const marcarEnProceso = async () => {
  const res = await apiFetchEmpresa(`/api/empresa/mantenciones/${id}/`, {
    method: 'PUT',
    body: { estado: 'en_proceso' },
  })
  if (res.ok) {
    toast.agregar('Mantención marcada en proceso', 'success')
    await cargar()
  } else {
    toast.agregar('Error al actualizar', 'error')
  }
}

const abrirCompletar = () => {
  formCompletar.value = {
    fecha_realizada: new Date().toISOString().split('T')[0],
    costo: mantencion.value?.presupuesto || '',
  }
  erroresCompletar.value = {}
  mostrarFormCompletar.value = true
}

const confirmarCompletar = async () => {
  erroresCompletar.value = {}
  const hoy    = new Date().toISOString().split('T')[0]
  const fechaR = formCompletar.value.fecha_realizada
  const fechaP = mantencion.value?.fecha_programada

  if (!fechaR) {
    erroresCompletar.value.fecha = 'La fecha realizada es obligatoria.'
    return
  }
  if (fechaR > hoy) {
    erroresCompletar.value.fecha = 'No puede ser una fecha futura.'
    return
  }
  if (fechaP && fechaR < fechaP) {
    erroresCompletar.value.fecha = `No puede ser anterior a la programada (${formatFecha(fechaP)}).`
    return
  }
  if (!formCompletar.value.costo || Number(formCompletar.value.costo) <= 0) {
    erroresCompletar.value.costo = 'El costo real debe ser mayor a 0.'
    return
  }

  guardando.value = true
  const res = await apiFetchEmpresa(`/api/empresa/mantenciones/${id}/`, {
    method: 'PUT',
    body: { estado: 'realizada', ...formCompletar.value },
  })
  guardando.value = false
  if (res.ok) {
    mostrarFormCompletar.value = false
    toast.agregar('Mantención completada correctamente', 'success')
    await cargar()
  } else {
    const data = await res.json().catch(() => null)
    toast.agregar(data?.error || 'Error al completar', 'error')
  }
}

onMounted(cargar)
</script>

<template>
  <div class="page">

    <div v-if="cargando" class="loading"><div class="spinner"/>Cargando...</div>

    <div v-else-if="error404" class="error-box">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="error-icon">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p>Mantención no encontrada.</p>
      <button class="btn btn-outline mt-2" @click="router.push(ruta('/mantenciones'))">← Volver a la lista</button>
    </div>

    <template v-else-if="mantencion">
      <!-- Encabezado -->
      <div class="page-header">
        <div class="title-wrap">
          <button class="btn-back" @click="router.push(ruta('/mantenciones'))" title="Volver">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          <div>
            <div class="title-row">
              <h1 class="page-title">{{ mantencion.tipo_mantencion }}</h1>
              <span :class="['badge', badgeClase(mantencion.estado)]">{{ mantencion.estado_display }}</span>
            </div>
            <p class="page-subtitle">{{ mantencion.vehiculo_patente }} · {{ mantencion.vehiculo_descripcion }}</p>
          </div>
        </div>

        <div class="header-acciones" v-if="tienePermiso('mantenciones.editar')">
          <button
            v-if="mantencion.estado === 'pendiente'"
            class="btn-accion btn-accion-blue"
            @click="marcarEnProceso"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            En proceso
          </button>
          <button
            v-if="['pendiente', 'en_proceso'].includes(mantencion.estado)"
            class="btn-accion btn-accion-green"
            @click="abrirCompletar"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Completar
          </button>
          <button
            v-if="!cancelada && mantencion.estado !== 'realizada'"
            class="btn-accion btn-accion-neutral"
            @click="router.push(ruta(`/mantenciones/${id}/editar`))"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
            Editar
          </button>
        </div>
      </div>

      <!-- Timeline de estado (no se muestra si está cancelada) -->
      <div v-if="!cancelada" class="timeline-wrap">
        <div
          v-for="(step, i) in ESTADOS_ORDEN"
          :key="step"
          class="timeline-step"
          :class="{
            'step-done':    i < estadoIndex,
            'step-current': i === estadoIndex,
            'step-pending': i > estadoIndex,
          }"
        >
          <div class="step-connector-left"  v-if="i > 0"/>
          <div class="step-dot">
            <svg v-if="i < estadoIndex" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="step-connector-right" v-if="i < ESTADOS_ORDEN.length - 1"/>
          <span class="step-label">{{ LABELS_ESTADO[step] }}</span>
        </div>

        <!-- Badge cancelada fuera del flujo -->
      </div>
      <div v-else class="cancelada-notice">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
        </svg>
        Esta mantención fue cancelada y no puede modificarse.
      </div>

      <!-- Grilla de información -->
      <div class="info-grid">
        <!-- Programación -->
        <div class="card info-card">
          <h2 class="info-card-titulo">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
            Programación
          </h2>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">Tipo</span>
              <span class="info-valor">{{ mantencion.tipo_mantencion }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Fecha programada</span>
              <span class="info-valor">{{ formatFecha(mantencion.fecha_programada) }}</span>
            </div>
            <div class="info-row" v-if="mantencion.taller_proveedor">
              <span class="info-label">Taller / Proveedor</span>
              <span class="info-valor">{{ mantencion.taller_proveedor }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Presupuesto</span>
              <span class="info-valor presupuesto">{{ formatMonto(mantencion.presupuesto) }}</span>
            </div>
            <div class="info-row" v-if="mantencion.descripcion">
              <span class="info-label">Descripción</span>
              <span class="info-valor">{{ mantencion.descripcion }}</span>
            </div>
          </div>
        </div>

        <!-- Ejecución (solo si tiene datos de realización) -->
        <div class="card info-card" v-if="mantencion.estado === 'realizada'">
          <h2 class="info-card-titulo">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Ejecución
          </h2>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">Fecha realizada</span>
              <span class="info-valor">{{ formatFecha(mantencion.fecha_realizada) }}</span>
            </div>
            <div class="info-row" v-if="mantencion.kilometraje_realizado">
              <span class="info-label">Kilometraje</span>
              <span class="info-valor">{{ Number(mantencion.kilometraje_realizado).toLocaleString('es-CL') }} km</span>
            </div>
            <div class="info-row">
              <span class="info-label">Costo real</span>
              <span class="info-valor costo-real">{{ formatMonto(mantencion.costo) }}</span>
            </div>
            <div class="info-row" v-if="mantencion.presupuesto && mantencion.costo">
              <span class="info-label">Diferencia</span>
              <span
                class="info-valor"
                :class="Number(mantencion.costo) > Number(mantencion.presupuesto) ? 'diff-over' : 'diff-under'"
              >
                {{ Number(mantencion.costo) > Number(mantencion.presupuesto) ? '+' : '' }}
                ${{ (Number(mantencion.costo) - Number(mantencion.presupuesto)).toLocaleString('es-CL') }}
              </span>
            </div>
          </div>
        </div>

        <!-- Vehículo -->
        <div class="card info-card">
          <h2 class="info-card-titulo">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l1 1h5m0-1h6m0 0l1-1V9.5l-3-3H9"/>
            </svg>
            Vehículo
          </h2>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">Patente</span>
              <span class="info-valor mono">{{ mantencion.vehiculo_patente }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Descripción</span>
              <span class="info-valor">{{ mantencion.vehiculo_descripcion }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Formulario inline para completar -->
      <transition name="slide-down">
        <div v-if="mostrarFormCompletar" class="card completar-card">
          <h2 class="section-title">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Registrar como completada
          </h2>

          <div class="completar-grid">
            <div class="form-group">
              <label class="label">Fecha realizada <span class="req">*</span></label>
              <input
                type="date"
                v-model="formCompletar.fecha_realizada"
                class="input"
                :max="new Date().toISOString().split('T')[0]"
              />
              <p v-if="erroresCompletar.fecha" class="field-error">{{ erroresCompletar.fecha }}</p>
            </div>

            <div class="form-group">
              <label class="label">Costo real (CLP) <span class="req">*</span></label>
              <input
                type="number"
                v-model="formCompletar.costo"
                class="input"
                min="1"
                placeholder="Ej: 85000"
              />
              <p v-if="mantencion.presupuesto" class="field-hint">
                Presupuesto estimado: {{ formatMonto(mantencion.presupuesto) }}
              </p>
              <p v-if="erroresCompletar.costo" class="field-error">{{ erroresCompletar.costo }}</p>
            </div>
          </div>

          <div class="completar-footer">
            <button class="btn-secondary" @click="mostrarFormCompletar = false" :disabled="guardando">
              Cancelar
            </button>
            <button class="btn-primary" @click="confirmarCompletar" :disabled="guardando">
              <span v-if="guardando">Guardando…</span>
              <span v-else>Confirmar</span>
            </button>
          </div>
        </div>
      </transition>
    </template>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

/* ── Página ──────────────────────────────────────────── */
.page {
  padding:     2rem 2.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  background:  #F9FAFB;
  min-height:  100vh;
}

/* ── Encabezado ──────────────────────────────────────── */
.page-header {
  display:         flex;
  align-items:     flex-start;
  justify-content: space-between;
  gap:             1rem;
  margin-bottom:   1.75rem;
  flex-wrap:       wrap;
}

.title-wrap {
  display:     flex;
  align-items: flex-start;
  gap:         1rem;
}

.btn-back {
  width:           40px;
  height:          40px;
  flex-shrink:     0;
  border-radius:   10px;
  border:          1px solid #E5E7EB;
  background:      #fff;
  color:           #4B5563;
  display:         flex;
  align-items:     center;
  justify-content: center;
  cursor:          pointer;
  transition:      all 0.2s;
  margin-top:      2px;
}
.btn-back:hover { background: #F3F4F6; color: #111827; border-color: #D1D5DB; }
.btn-back svg   { width: 20px; height: 20px; }

.title-row {
  display:     flex;
  align-items: center;
  gap:         0.75rem;
  flex-wrap:   wrap;
}

.page-title    { font-size: 1.75rem; font-weight: 700; color: #111827; margin: 0; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0.2rem 0 0; }

/* ── Botones de acción del header ────────────────────── */
.header-acciones {
  display:     flex;
  align-items: center;
  gap:         0.5rem;
  flex-wrap:   wrap;
  flex-shrink: 0;
}

.btn-accion {
  display:       inline-flex;
  align-items:   center;
  gap:           0.4rem;
  padding:       0.6rem 1.25rem;
  border-radius: 10px;
  font-size:     0.875rem;
  font-weight:   600;
  cursor:        pointer;
  transition:    all 0.15s;
  border:        1.5px solid transparent;
  font-family:   inherit;
}
.btn-accion svg { width: 16px; height: 16px; }

.btn-accion-blue    { background: #EEF2FF; color: #4F46E5; border-color: #C7D2FE; }
.btn-accion-blue:hover { background: #E0E7FF; border-color: #A5B4FC; }

.btn-accion-green   { background: linear-gradient(135deg, #10B981, #059669); color: #fff; }
.btn-accion-green:hover { opacity: 0.9; }

.btn-accion-neutral { background: #fff; color: #374151; border-color: #D1D5DB; }
.btn-accion-neutral:hover { background: #F9FAFB; border-color: #9CA3AF; }

/* ── Timeline ────────────────────────────────────────── */
.timeline-wrap {
  display:         flex;
  align-items:     flex-start;
  padding:         1.5rem 2rem;
  background:      #fff;
  border:          1px solid #E5E7EB;
  border-radius:   16px;
  box-shadow:      0 4px 6px -1px rgba(0,0,0,0.05);
  margin-bottom:   1.5rem;
}

.timeline-step {
  display:        flex;
  flex-direction: column;
  align-items:    center;
  position:       relative;
  flex:           1;
}

.step-connector-left,
.step-connector-right {
  position:   absolute;
  top:        15px;
  height:     2px;
  width:      50%;
  background: #E5E7EB;
}
.step-connector-left  { left: 0; }
.step-connector-right { right: 0; }

.step-done .step-connector-left,
.step-done .step-connector-right,
.step-current .step-connector-left {
  background: #10B981;
}

.step-dot {
  width:           30px;
  height:          30px;
  border-radius:   50%;
  border:          2px solid #D1D5DB;
  background:      #fff;
  display:         flex;
  align-items:     center;
  justify-content: center;
  z-index:         1;
  transition:      all 0.2s;
}
.step-dot svg { width: 14px; height: 14px; color: #fff; }

.step-done    .step-dot { background: #10B981; border-color: #10B981; }
.step-current .step-dot { background: #4F46E5; border-color: #4F46E5; width: 34px; height: 34px; box-shadow: 0 0 0 4px rgba(79,70,229,0.15); }
.step-pending .step-dot { background: #F9FAFB; border-color: #D1D5DB; }

.step-label {
  margin-top:  0.5rem;
  font-size:   0.8rem;
  color:       #9CA3AF;
  font-weight: 500;
  text-align:  center;
}
.step-done    .step-label { color: #059669; font-weight: 600; }
.step-current .step-label { color: #4F46E5; font-weight: 700; font-size: 0.85rem; }

/* ── Cancelada ───────────────────────────────────────── */
.cancelada-notice {
  display:       flex;
  align-items:   center;
  gap:           0.75rem;
  padding:       1rem 1.25rem;
  background:    #FEF2F2;
  border:        1px solid #FECACA;
  border-radius: 12px;
  color:         #B91C1C;
  font-size:     0.875rem;
  font-weight:   500;
  margin-bottom: 1.5rem;
}
.cancelada-notice svg { width: 20px; height: 20px; flex-shrink: 0; }

/* ── Grilla de tarjetas ──────────────────────────────── */
.info-grid {
  display:               grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap:                   1.25rem;
  margin-bottom:         1.5rem;
}

.card {
  background:    #fff;
  border:        1px solid #E5E7EB;
  border-radius: 16px;
  padding:       1.5rem;
  box-shadow:    0 4px 6px -1px rgba(0,0,0,0.05);
}

/* ── Contenido de las tarjetas ───────────────────────── */
.info-card-titulo {
  display:        flex;
  align-items:    center;
  gap:            0.5rem;
  font-size:      0.9375rem;
  font-weight:    700;
  color:          #111827;
  margin:         0 0 1.25rem;
  padding-bottom: 0.875rem;
  border-bottom:  1px solid #F3F4F6;
}
.info-card-titulo svg { width: 18px; height: 18px; color: #6B7280; }

.info-rows { display: flex; flex-direction: column; gap: 0.875rem; }

.info-row {
  display:         flex;
  justify-content: space-between;
  align-items:     baseline;
  gap:             1rem;
}

.info-label {
  font-size:   0.8125rem;
  color:       #6B7280;
  font-weight: 500;
  flex-shrink: 0;
}

.info-valor {
  font-size:   0.875rem;
  color:       #111827;
  font-weight: 600;
  text-align:  right;
}

.info-valor.presupuesto { color: #4F46E5; }
.info-valor.costo-real  { color: #059669; }
.info-valor.diff-over   { color: #DC2626; }
.info-valor.diff-under  { color: #059669; }
.info-valor.mono        { font-family: monospace; font-size: 1rem; letter-spacing: 1px; }

/* ── Formulario completar ────────────────────────────── */
.completar-card {
  border-color: #A7F3D0;
  background:   #F0FDF4;
}

.section-title {
  display:        flex;
  align-items:    center;
  gap:            0.5rem;
  font-size:      1rem;
  font-weight:    700;
  color:          #065F46;
  margin:         0 0 1.25rem;
  padding-bottom: 0.875rem;
  border-bottom:  1px solid #D1FAE5;
}
.section-title svg { width: 18px; height: 18px; }

.completar-grid {
  display:               grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap:                   1rem;
  margin-bottom:         1.5rem;
}

.form-group { display: flex; flex-direction: column; gap: 0.375rem; }

.label {
  font-size:   0.875rem;
  font-weight: 600;
  color:       #374151;
}
.req { color: #EF4444; }

.input {
  padding:       0.65rem 0.875rem;
  border:        1.5px solid #D1D5DB;
  border-radius: 10px;
  font-size:     0.875rem;
  color:         #111827;
  background:    #fff;
  outline:       none;
  width:         100%;
  font-family:   inherit;
  transition:    border-color 0.15s, box-shadow 0.15s;
}
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }

.field-hint  { font-size: 0.75rem; color: #6B7280; margin: 0.15rem 0 0; }
.field-error { font-size: 0.75rem; color: #EF4444; font-weight: 500; margin: 0.15rem 0 0; }

.completar-footer {
  display:         flex;
  justify-content: flex-end;
  gap:             0.75rem;
}

/* ── Botones del formulario (alineados al proyecto) ──── */
.btn-primary {
  display:       inline-flex;
  align-items:   center;
  gap:           0.5rem;
  padding:       0.6rem 1.25rem;
  background:    linear-gradient(135deg, #4F46E5, #7C3AED);
  color:         #fff;
  font-size:     0.875rem;
  font-weight:   600;
  border:        none;
  border-radius: 10px;
  cursor:        pointer;
  font-family:   inherit;
  transition:    opacity 0.2s;
}
.btn-primary:hover    { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  display:       inline-flex;
  align-items:   center;
  gap:           0.5rem;
  padding:       0.6rem 1.25rem;
  background:    #fff;
  border:        1.5px solid #D1D5DB;
  border-radius: 10px;
  font-size:     0.875rem;
  font-weight:   600;
  color:         #374151;
  cursor:        pointer;
  font-family:   inherit;
  transition:    border-color 0.15s;
}
.btn-secondary:hover    { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Badges ──────────────────────────────────────────── */
.badge {
  display:       inline-flex;
  align-items:   center;
  padding:       0.25rem 0.75rem;
  border-radius: 999px;
  font-size:     0.75rem;
  font-weight:   600;
}
.badge-warning { background: #FEF3C7; color: #92400E; }
.badge-info    { background: #DBEAFE; color: #1E40AF; }
.badge-success { background: #D1FAE5; color: #065F46; }
.badge-gray    { background: #F3F4F6; color: #6B7280; }

/* ── Loading / Error ─────────────────────────────────── */
.loading {
  display:         flex;
  align-items:     center;
  justify-content: center;
  gap:             0.75rem;
  padding:         4rem;
  color:           #6B7280;
}
.spinner {
  width:            30px;
  height:           30px;
  border:           3px solid #E5E7EB;
  border-top-color: #7C3AED;
  border-radius:    50%;
  animation:        spin 0.8s linear infinite;
}

.error-box {
  display:         flex;
  flex-direction:  column;
  align-items:     center;
  justify-content: center;
  gap:             0.75rem;
  padding:         4rem;
  color:           #6B7280;
  text-align:      center;
}
.error-icon { width: 64px; height: 64px; color: #D1D5DB; }

/* ── Transición ──────────────────────────────────────── */
.slide-down-enter-active,
.slide-down-leave-active { transition: all 0.25s ease; }
.slide-down-enter-from   { opacity: 0; transform: translateY(-8px); }
.slide-down-leave-to     { opacity: 0; transform: translateY(-8px); }

@keyframes spin    { to { transform: rotate(360deg); } }
@keyframes fadeIn  { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 640px) {
  .page            { padding: 1.25rem 1rem; }
  .page-header     { flex-direction: column; }
  .header-acciones { width: 100%; }
  .btn-accion      { flex: 1; justify-content: center; }
  .info-grid       { grid-template-columns: 1fr; }
}
</style>
