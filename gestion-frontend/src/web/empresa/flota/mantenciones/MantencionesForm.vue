<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetchEmpresa, getEmpresaActiva, setEmpresaActiva, useEmpresaNav } from '../../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../../utils/permisos.js'
import { useToast } from '../../../../utils/useToast.js'
import { apiFetch } from '../../../../utils/api.js'
import { validarFechaFutura } from '../../../../utils/validators.js'

const router  = useRouter()
const route   = useRoute()
const { ruta } = useEmpresaNav()
const toast = useToast()

const esNuevo   = computed(() => !route.params.id)
const tituloForm = computed(() => esNuevo.value ? 'Programar Mantención' : 'Editar Mantención')

const usuario = JSON.parse(localStorage.getItem('usuario') || 'null')
const esSuperadmin = usuario?.rol === 'SUPERADMIN'

const empresas        = ref([])
const empresaActiva   = ref(getEmpresaActiva())
const sinEmpresa      = computed(() => esSuperadmin && !empresaActiva.value)
const mostrarDropdown = ref(false)

const vehiculos   = ref([])
const cargando    = ref(false)
const guardando   = ref(false)
const errores     = ref({})
const errorGlobal = ref('')

// Sugerencias del backend
const sugerencias = ref({ talleres: [], presupuesto_por_tipo: {} })

const TIPOS_MANTENCION = [
  { key: 'aceite',             label: 'Cambio de aceite' },
  { key: 'frenos',             label: 'Revisión de frenos' },
  { key: 'neumaticos',         label: 'Cambio de neumáticos' },
  { key: 'filtro_aire',        label: 'Filtro de aire' },
  { key: 'filtro_combustible', label: 'Filtro de combustible' },
  { key: 'rtv',                label: 'Revisión técnica (RTV)' },
  { key: 'electrica',          label: 'Revisión eléctrica' },
  { key: 'otro',               label: 'Otro' },
]

const tipoSeleccionado = ref('')
const tipoOtro         = ref('')
const tipoMantencion   = computed(() => {
  if (tipoSeleccionado.value === 'otro') return tipoOtro.value
  return TIPOS_MANTENCION.find(t => t.key === tipoSeleccionado.value)?.label || ''
})

const form = ref({
  vehiculo_id:      null,
  taller_proveedor: '',
  presupuesto:      '',
  fecha_programada: '',
  estado:           'pendiente',
})

const ESTADOS = [
  { value: 'pendiente',  label: 'Pendiente' },
  { value: 'en_proceso', label: 'En Proceso' },
  { value: 'realizada',  label: 'Realizada' },
  { value: 'cancelada',  label: 'Cancelada' },
]

// Pre-llenar presupuesto cuando el tipo coincide con una regla del plan
watch(tipoMantencion, (tipo) => {
  if (!tipo) return
  const presupuesto = sugerencias.value.presupuesto_por_tipo[tipo]
  if (presupuesto && form.value.presupuesto === '') {
    form.value.presupuesto = presupuesto
  }
})

// Al cambiar vehículo, recargar presupuestos del plan asignado
watch(() => form.value.vehiculo_id, async (id) => {
  if (!id) return
  const res = await apiFetchEmpresa(`/api/empresa/mantenciones/sugerencias/?vehiculo_id=${id}`)
  if (res.ok) {
    const data = await res.json()
    sugerencias.value.presupuesto_por_tipo = data.presupuesto_por_tipo
  }
})

const cargarTipo = (valor) => {
  const match = TIPOS_MANTENCION.find(t => t.label === valor || t.key === valor)
  if (match && match.key !== 'otro') {
    tipoSeleccionado.value = match.key
  } else if (valor) {
    tipoSeleccionado.value = 'otro'
    tipoOtro.value = valor
  }
}

const cargarEmpresas = async () => {
  if (!esSuperadmin) return
  const res = await apiFetch('/api/clientes/empresas/')
  if (res.ok) empresas.value = await res.json()
}

const seleccionarEmpresa = async (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value = emp
  await cargarDatos()
}

const cargarDatos = async () => {
  if (sinEmpresa.value) return
  cargando.value = true
  try {
    const [resVeh, resSug] = await Promise.all([
      apiFetchEmpresa('/api/empresa/vehiculos/'),
      apiFetchEmpresa('/api/empresa/mantenciones/sugerencias/'),
    ])
    if (resVeh.ok) vehiculos.value = (await resVeh.json()).filter(v => v.activo)
    if (resSug.ok) {
      const sug = await resSug.json()
      sugerencias.value.talleres = sug.talleres
      sugerencias.value.presupuesto_por_tipo = sug.presupuesto_por_tipo
    }

    if (!esNuevo.value) {
      const resM = await apiFetchEmpresa(`/api/empresa/mantenciones/${route.params.id}/`)
      if (resM.ok) {
        const data = await resM.json()
        form.value = {
          vehiculo_id:      data.vehiculo_id,
          taller_proveedor: data.taller_proveedor || '',
          presupuesto:      data.presupuesto ?? '',
          fecha_programada: data.fecha_programada || '',
          estado:           data.estado || 'pendiente',
        }
        cargarTipo(data.tipo_mantencion || '')
      } else {
        errorGlobal.value = 'No se encontró la mantención.'
      }
    } else {
      const q = route.query
      if (q.vehiculo)    form.value.vehiculo_id    = Number(q.vehiculo)
      if (q.fecha)       form.value.fecha_programada = q.fecha
      if (q.presupuesto) form.value.presupuesto     = q.presupuesto
      if (q.tipo)        cargarTipo(q.tipo)
    }
  } finally {
    cargando.value = false
  }
}

const validarFechaInput = () => {
  if (!form.value.fecha_programada) return
  if (esNuevo.value) {
    const r = validarFechaFutura(form.value.fecha_programada)
    if (!r.valido) {
      errores.value = { ...errores.value, fecha_programada: [r.error] }
    } else {
      const { fecha_programada: _, ...rest } = errores.value
      errores.value = rest
    }
  }
}

const guardar = async () => {
  const permiso = esNuevo.value ? 'mantenciones.crear' : 'mantenciones.editar'
  if (!tienePermiso(permiso)) { toast.agregar('Sin permisos para esta acción', 'error'); return }

  errores.value     = {}
  errorGlobal.value = ''

  if (!form.value.vehiculo_id) {
    errores.value.vehiculo_id = ['Debes seleccionar un vehículo.']
    return
  }

  if (!tipoMantencion.value.trim()) {
    errores.value.tipo_mantencion = [tipoSeleccionado.value === 'otro' ? 'Describe el tipo de mantención.' : 'Selecciona un tipo de mantención.']
    return
  }

  if (!form.value.fecha_programada) {
    errores.value.fecha_programada = ['La fecha programada es obligatoria.']
    return
  }

  if (esNuevo.value && form.value.fecha_programada < new Date().toISOString().split('T')[0]) {
    errores.value.fecha_programada = ['La fecha programada no puede ser en el pasado.']
    return
  }

  if (form.value.presupuesto !== '' && Number(form.value.presupuesto) <= 0) {
    errores.value.presupuesto = ['El presupuesto debe ser mayor a 0.']
    return
  }

  const payload = {
    vehiculo_id:      form.value.vehiculo_id,
    tipo_mantencion:  tipoMantencion.value,
    taller_proveedor: form.value.taller_proveedor,
    presupuesto:      form.value.presupuesto !== '' ? form.value.presupuesto : null,
    fecha_programada: form.value.fecha_programada,
    estado:           form.value.estado,
  }

  guardando.value = true
  try {
    const url    = esNuevo.value ? '/api/empresa/mantenciones/' : `/api/empresa/mantenciones/${route.params.id}/`
    const method = esNuevo.value ? 'POST' : 'PUT'
    const res    = await apiFetchEmpresa(url, { method, body: payload })

    if (res.ok) {
      toast.agregar(esNuevo.value ? 'Mantención programada exitosamente' : 'Mantención actualizada', 'success')
      setTimeout(() => router.push(ruta('/mantenciones')), 600)
    } else {
      let data = null
      try { data = await res.json() } catch { /* respuesta no-JSON */ }

      if (!data) {
        errorGlobal.value = `Error del servidor (${res.status}). Intenta nuevamente.`
      } else if (data.error === 'sin_empresa') {
        errorGlobal.value = 'No hay empresa seleccionada. Selecciona una empresa antes de guardar.'
      } else if (data.error) {
        errorGlobal.value = data.error
      } else {
        errores.value = data
      }
    }
  } catch (e) {
    errorGlobal.value = 'Error de conexión. Verifica tu red e intenta nuevamente.'
  } finally {
    guardando.value = false
  }
}

onMounted(async () => {
  await cargarEmpresas()
  await cargarDatos()
})
</script>

<template>
  <div class="page">

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenciones</h1>
        <p class="page-subtitle">Gestiona el mantenimiento y costos de tu flota</p>
      </div>
    </div>

    <!-- Sub-navegación -->
    <div class="subnav">
      <router-link :to="ruta('/mantenciones')"            class="subnav-tab" active-class="subnav-tab-active" exact>Programados</router-link>
      <router-link :to="ruta('/mantenciones/calendario')" class="subnav-tab" active-class="subnav-tab-active">Calendario</router-link>
      <router-link :to="ruta('/mantenciones/historial')"  class="subnav-tab" active-class="subnav-tab-active">Historial</router-link>
      <router-link :to="ruta('/mantenciones/nueva')"      class="subnav-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        Programar
      </router-link>
    </div>

    <!-- Selector de empresa (solo SUPERADMIN) -->
    <div v-if="esSuperadmin" class="empresa-bar">
      <span class="empresa-label">Empresa:</span>
      <div class="empresa-dropdown">
        <button type="button" class="empresa-btn" @click.stop="mostrarDropdown = !mostrarDropdown">
          {{ empresaActiva ? empresaActiva.nombre : '— Seleccionar empresa —' }}
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:14px;height:14px;flex-shrink:0"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </button>
        <div v-if="mostrarDropdown" class="empresa-menu" @click.stop>
          <button
            v-for="emp in empresas" :key="emp.id"
            type="button"
            class="empresa-item"
            :class="{ 'empresa-item-active': empresaActiva?.id === emp.id }"
            @click="seleccionarEmpresa(emp); mostrarDropdown = false"
          >{{ emp.nombre }}</button>
        </div>
      </div>
    </div>

    <div v-if="cargando" class="loading"><div class="spinner"/>Cargando...</div>

    <template v-else-if="sinEmpresa">
      <div class="sin-empresa-msg">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:32px;height:32px;color:#9CA3AF;margin-bottom:0.5rem"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
        <p>Selecciona una empresa para continuar.</p>
      </div>
    </template>

    <template v-else>
      <!-- Botón volver -->
      <button class="btn-volver" @click="router.push(ruta('/mantenciones'))">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
        Volver a Programados
      </button>

      <!-- Banner pre-llenado desde alerta -->
      <div v-if="route.query.tipo" class="banner-alerta">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Formulario pre-llenado desde una alerta predictiva. Revisa y ajusta si es necesario.
      </div>

      <div class="form-card">
        <h2 class="form-titulo">{{ tituloForm }}</h2>

        <div v-if="errorGlobal" class="alert-error">{{ errorGlobal }}</div>

        <form @submit.prevent="guardar" class="form">
          <!-- Sección: Vehículo y tipo -->
          <div class="seccion-titulo">Información del mantenimiento</div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Vehículo <span class="req">*</span></label>
              <select v-model="form.vehiculo_id" class="input" required>
                <option :value="null">— Seleccionar vehículo —</option>
                <option v-for="v in vehiculos" :key="v.id" :value="v.id">
                  {{ v.patente }} — {{ v.marca }} {{ v.modelo }}
                </option>
              </select>
              <p v-if="errores.vehiculo_id" class="field-error">{{ errores.vehiculo_id[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">Estado</label>
              <select v-model="form.estado" class="input">
                <option v-for="e in ESTADOS" :key="e.value" :value="e.value">{{ e.label }}</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="label">Tipo de Mantención <span class="req">*</span></label>
            <select v-model="tipoSeleccionado" class="input">
              <option value="">— Seleccionar tipo —</option>
              <option v-for="t in TIPOS_MANTENCION" :key="t.key" :value="t.key">{{ t.label }}</option>
            </select>
            <input
              v-if="tipoSeleccionado === 'otro'"
              v-model="tipoOtro"
              class="input mt-1"
              placeholder="Describe el tipo de mantención..."
              autocomplete="off"
              maxlength="100"
            />
            <p v-if="errores.tipo_mantencion" class="field-error">{{ errores.tipo_mantencion[0] }}</p>
          </div>

          <!-- Sección: Programación -->
          <div class="seccion-titulo mt-2">Programación</div>

          <div class="form-group">
            <label class="label">Fecha programada <span class="req">*</span></label>
            <input v-model="form.fecha_programada" type="date" class="input"
              :class="{ 'input-error': errores.fecha_programada }"
              @change="validarFechaInput"/>
            <p v-if="errores.fecha_programada" class="field-error">{{ errores.fecha_programada[0] }}</p>
          </div>

          <!-- Sección: Taller y presupuesto -->
          <div class="seccion-titulo mt-2">Taller y presupuesto</div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Taller / Proveedor</label>
              <input
                v-model="form.taller_proveedor"
                class="input"
                list="talleres-list"
                placeholder="Ej: Taller Mecánico López..."
                autocomplete="off"
                maxlength="200"
              />
              <datalist id="talleres-list">
                <option v-for="t in sugerencias.talleres" :key="t" :value="t"/>
              </datalist>
            </div>
            <div class="form-group">
              <label class="label">Presupuesto estimado ($)</label>
              <input
                v-model="form.presupuesto"
                type="number"
                class="input"
                min="0"
                step="1"
                placeholder="Opcional"
              />
              <p v-if="errores.presupuesto" class="field-error">{{ errores.presupuesto[0] }}</p>
              <p v-else-if="sugerencias.presupuesto_por_tipo[tipoMantencion]" class="field-hint">
                Sugerido por el plan: ${{ Number(sugerencias.presupuesto_por_tipo[tipoMantencion]).toLocaleString('es-CL') }}
              </p>
            </div>
          </div>

          <!-- Acciones -->
          <div class="form-actions">
            <button type="button" class="btn-secondary" @click="router.push(ruta('/mantenciones'))">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="guardando">
              <span v-if="guardando" class="spinner-inline"/>
              {{ guardando ? 'Guardando...' : (esNuevo ? 'Programar Mantención' : 'Guardar Cambios') }}
            </button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background: #F9FAFB; min-height: 100vh; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.subnav { display: flex; align-items: center; gap: 0.25rem; border-bottom: 2px solid #E5E7EB; margin-bottom: 1.75rem; }
.subnav-tab { padding: 0.625rem 1rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; text-decoration: none; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: color 0.15s; }
.subnav-tab:hover { color: #4F46E5; }
.subnav-tab-active { color: #4F46E5; border-bottom-color: #4F46E5; font-weight: 600; }
.subnav-btn { margin-left: auto; display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.45rem 1rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; text-decoration: none; transition: opacity 0.15s; }
.subnav-btn:hover { opacity: 0.9; }
.subnav-btn svg { width: 15px; height: 15px; }

.btn-volver { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.45rem 0.875rem; background: none; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.8125rem; font-weight: 500; color: #6B7280; cursor: pointer; margin-bottom: 1.25rem; transition: all 0.15s; }
.btn-volver:hover { border-color: #4F46E5; color: #4F46E5; }
.btn-volver svg { width: 16px; height: 16px; }

.banner-alerta {
  display: flex; align-items: center; gap: 0.5rem;
  background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px;
  padding: 0.625rem 1rem; font-size: 0.8125rem; color: #1D4ED8;
  margin-bottom: 1.25rem;
}
.banner-alerta svg { width: 16px; height: 16px; flex-shrink: 0; }

.form-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); max-width: 720px; }
.form-titulo { font-size: 1.125rem; font-weight: 700; color: #111827; margin: 0 0 1.5rem; }

.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.875rem; margin-bottom: 1.25rem; }

.seccion-titulo { font-size: 0.8125rem; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.05em; padding-bottom: 0.5rem; border-bottom: 1px solid #E5E7EB; margin-bottom: 1rem; }
.seccion-hint { font-size: 0.8rem; color: #9CA3AF; margin: -0.5rem 0 1rem; }
.mt-1 { margin-top: 0.375rem; }
.mt-2 { margin-top: 1.5rem; }

.form { display: flex; flex-direction: column; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.req { color: #EF4444; }
.input { padding: 0.625rem 0.875rem; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; outline: none; width: 100%; background: #fff; }
.input:focus { border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }
.input.input-error { border-color: #EF4444; }
.textarea { resize: vertical; font-family: inherit; }
.field-error { font-size: 0.75rem; color: #EF4444; margin: 0; }
.field-hint { font-size: 0.75rem; color: #6B7280; margin: 0; }

.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.75rem; padding-top: 1.25rem; border-top: 1px solid #E5E7EB; }
.btn-secondary { padding: 0.625rem 1.25rem; background: #fff; border: 1px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; transition: background 0.15s; }
.btn-secondary:hover { background: #F9FAFB; }
.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.625rem 1.5rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.spinner-inline { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }

.loading { display: flex; flex-direction: column; align-items: center; padding: 4rem; color: #6B7280; }
.spinner { width: 28px; height: 28px; border: 3px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

.empresa-bar { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem; }
.empresa-label { font-size: 0.875rem; font-weight: 600; color: #374151; white-space: nowrap; }
.empresa-dropdown { position: relative; }
.empresa-btn { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.875rem; background: #fff; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; color: #374151; cursor: pointer; min-width: 220px; justify-content: space-between; }
.empresa-btn:hover { border-color: #4F46E5; }
.empresa-menu { position: absolute; top: calc(100% + 4px); left: 0; min-width: 220px; background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); z-index: 50; max-height: 280px; overflow-y: auto; }
.empresa-item { display: block; width: 100%; text-align: left; padding: 0.625rem 1rem; font-size: 0.875rem; color: #374151; background: none; border: none; cursor: pointer; }
.empresa-item:hover { background: #F3F4F6; }
.empresa-item-active { color: #4F46E5; font-weight: 600; background: #EEF2FF; }

.sin-empresa-msg { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 5rem 2rem; color: #9CA3AF; font-size: 0.9375rem; text-align: center; }
</style>
