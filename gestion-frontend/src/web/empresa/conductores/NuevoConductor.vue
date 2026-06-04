<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../utils/empresaActiva.js'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'
import { validarPassword, validarTelefono, validarNombre, validarRut, validarLicencia } from '../../../utils/validators.js'
import InputTelefono from '../../../components/InputTelefono.vue'

const router    = useRouter()
const { ruta }  = useEmpresaNav()
const toast     = useToast()
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})

const form = ref({
  nombre:           '',
  apellido_paterno: '',
  apellido_materno: '',
  rut:      '',
  email:    '',
  password: '',
  telefono: '',
  licencia: '',
  
  // Asignación
  vehiculo_id: null,
  crear_vehiculo: false,
  vehiculo_patente: '',
  vehiculo_marca: '',
  vehiculo_modelo: '',
})

const asignarVehiculo = ref(false)
const modoAsignacion = ref('existente') // 'existente' o 'nuevo'
const vehiculosLibres = ref([])

onMounted(async () => {
  try {
    const resVehiculos = await apiFetchEmpresa('/api/empresa/vehiculos/')
    if (resVehiculos.ok) {
      const todos = await resVehiculos.json()
      // Vehículos activos y sin conductor asignado (disponibles para asignar).
      vehiculosLibres.value = todos.filter(v => v.activo && !v.conductor_asignado)
    }
  } catch (err) {
    console.error("Error cargando datos auxiliares", err)
  }
})

const generarPassword  = ref(true)   // true = dejar vacío y mandar por correo

const nivelPassword = computed(() => {
  if (generarPassword.value || !form.value.password) return null
  const r = validarPassword(form.value.password)
  return r.nivel || null
})

const formatRut = (value) => {
  let cleaned = value.replace(/[^0-9kK]/g, '').slice(0, 9)
  if (cleaned.length < 2) return cleaned
  const body = cleaned.slice(0, -1)
  const dv   = cleaned.slice(-1).toUpperCase()
  return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${dv}`
}
// Verificación de RUT duplicado contra la BD (ambas tablas)
const rutVerificando = ref(false)
let _debounceRut = null

async function verificarRut() {
  const r = validarRut(form.value.rut)
  if (!r.valido) return
  rutVerificando.value = true
  try {
    const res = await apiFetch(`/api/verificar-rut/?rut=${encodeURIComponent(form.value.rut)}&tipo=usuario`)
    if (res.ok) {
      const data = await res.json()
      if (!data.disponible) {
        errores.value = { ...errores.value, rut: [data.mensaje || 'Este RUT ya está registrado.'] }
      }
    }
  } catch {} finally {
    rutVerificando.value = false
  }
}

const onRutInput = (e) => {
  const v = formatRut(e.target.value)
  form.value.rut = v
  e.target.value = v
  if (errores.value.rut) errores.value = { ...errores.value, rut: undefined }
  clearTimeout(_debounceRut)
  _debounceRut = setTimeout(verificarRut, 600)
}

const guardar = async () => {
  error.value   = ''
  errores.value = {}

  // Validar nombre y apellidos (los tres obligatorios)
  const nomR = validarNombre(form.value.nombre, 2, 30)
  if (!nomR.valido) { errores.value = { nombre: [nomR.error] }; return }
  const apPatR = validarNombre(form.value.apellido_paterno, 2, 30)
  if (!apPatR.valido) { errores.value = { apellido_paterno: [apPatR.error] }; return }
  const apMatR = validarNombre(form.value.apellido_materno, 2, 30)
  if (!apMatR.valido) { errores.value = { apellido_materno: [apMatR.error] }; return }

  // Validar contraseña solo si el admin la ingresó manualmente
  if (!generarPassword.value) {
    const pwdResult = validarPassword(form.value.password)
    if (!pwdResult.valido) {
      errores.value = { password: [pwdResult.error] }
      return
    }
  } else {
    form.value.password = ''   // vacío → backend genera y envía por correo
  }

  // Validar teléfono (obligatorio)
  const telResult = validarTelefono(form.value.telefono)
  if (!telResult.valido) {
    errores.value = { telefono: [telResult.error] }
    return
  }

  // Validar licencia (opcional, pero si se ingresa debe tener el formato correcto)
  const licResult = validarLicencia(form.value.licencia)
  if (!licResult.valido) {
    errores.value = { licencia: [licResult.error] }
    return
  }

  // Verificación final del RUT contra la BD antes de crear
  clearTimeout(_debounceRut)
  if (form.value.rut) {
    await verificarRut()
    if (errores.value.rut) return
  }

  guardando.value = true

  const payload = { ...form.value }
  if (!asignarVehiculo.value) {
    payload.vehiculo_id = null
    payload.crear_vehiculo = false
  } else {
    payload.crear_vehiculo = modoAsignacion.value === 'nuevo'
    if (payload.crear_vehiculo) {
        payload.vehiculo_id = null
    } else {
      payload.vehiculo_patente = ''
      payload.vehiculo_marca = ''
      payload.vehiculo_modelo = ''
    }
  }

  try {
    const res  = await apiFetchEmpresa('/api/empresa/conductores/', { 
      method: 'POST', 
      body: payload 
    })
    const data = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al crear el conductor'
      return
    }
    toast.success('Conductor creado exitosamente')
    router.push(ruta('/conductores'))
  } catch {
    error.value = 'Error de conexión con el servidor'
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="breadcrumb">
      <button class="btn-back" @click="router.push(ruta('/conductores'))">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        Volver a Conductores
      </button>
    </div>

    <h1 class="page-title">Nuevo Conductor</h1>
    <p class="page-subtitle">Completa los datos para registrar un conductor</p>

    <div class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>

      <form @submit.prevent="guardar" class="form">
        <div class="form-section">
          <h3 class="section-title">Datos Personales</h3>
          <div class="form-row">
            <div class="form-group">
              <label class="label">Nombre</label>
              <input v-model="form.nombre" type="text" class="input"
                :class="{ 'input-error': errores.nombre }"
                placeholder="Ej: Juan" required autocomplete="off" maxlength="30"/>
              <p v-if="errores.nombre" class="field-error">{{ errores.nombre[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">RUT</label>
              <div style="position:relative">
                <input :value="form.rut" @input="onRutInput" type="text" class="input"
                  :class="{ 'input-error': errores.rut }"
                  placeholder="12.345.678-9" maxlength="12" required autocomplete="off"/>
                <span v-if="rutVerificando" class="rut-spinner"/>
              </div>
              <p v-if="errores.rut" class="field-error">{{ errores.rut[0] }}</p>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="label">Apellido paterno</label>
              <input v-model="form.apellido_paterno" type="text" class="input"
                :class="{ 'input-error': errores.apellido_paterno }"
                placeholder="Ej: Pérez" required autocomplete="off" maxlength="30"/>
              <p v-if="errores.apellido_paterno" class="field-error">{{ errores.apellido_paterno[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">Apellido materno</label>
              <input v-model="form.apellido_materno" type="text" class="input"
                :class="{ 'input-error': errores.apellido_materno }"
                placeholder="Ej: González" required autocomplete="off" maxlength="30"/>
              <p v-if="errores.apellido_materno" class="field-error">{{ errores.apellido_materno[0] }}</p>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Email</label>
              <input v-model="form.email" type="email" class="input"
                :class="{ 'input-error': errores.email }"
                placeholder="conductor@ejemplo.com" required autocomplete="off" maxlength="50"/>
              <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">Contraseña</label>

              <!-- Toggle: generar automáticamente vs ingresar manualmente -->
              <label class="flex items-center gap-2 mb-2 cursor-pointer select-none">
                <input type="checkbox" v-model="generarPassword" class="rounded"/>
                <span class="text-sm text-gray-600">
                  Generar y enviar por correo al conductor
                </span>
              </label>

              <div v-if="!generarPassword">
                <input v-model="form.password" type="password" class="input"
                  :class="{ 'input-error': errores.password }"
                  placeholder="Mín. 8 chars, 1 mayúscula, 1 número" autocomplete="new-password"/>
                <p v-if="errores.password" class="field-error">{{ errores.password[0] }}</p>
              </div>
              <p v-else class="text-xs text-indigo-600 bg-indigo-50 rounded-lg px-3 py-2">
                Se generará una contraseña segura y se enviará al email del conductor al crear la cuenta.
              </p>

              <div v-if="!generarPassword && form.password && nivelPassword" class="pwd-strength">
                <div class="pwd-strength-bar">
                  <div class="pwd-strength-fill" :class="`pwd-strength-${nivelPassword}`"/>
                </div>
                <span class="pwd-strength-label" :class="`pwd-level-${nivelPassword}`">
                  {{ nivelPassword === 'debil' ? 'Débil' : nivelPassword === 'media' ? 'Media' : 'Fuerte' }}
                </span>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Teléfono</label>
              <InputTelefono v-model="form.telefono" :error="!!errores.telefono" />
              <p v-if="errores.telefono" class="field-error">{{ errores.telefono[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">N° Licencia <span class="opcional">(opcional)</span></label>
              <input v-model="form.licencia" type="text" class="input"
                :class="{ 'input-error': errores.licencia }"
                placeholder="Ej: ABC1234567890" autocomplete="off" maxlength="13"/>
              <p v-if="errores.licencia" class="field-error">{{ errores.licencia[0] }}</p>
            </div>
          </div>
        </div>

        <div class="form-section assignment-section">
          <div class="assignment-header">
            <h3 class="section-title">Asignación de Vehículo</h3>
            <label class="switch">
              <input type="checkbox" v-model="asignarVehiculo">
              <span class="slider round"></span>
            </label>
          </div>
          
          <div v-if="asignarVehiculo" class="assignment-content">
            <div class="tabs">
              <button type="button" class="tab" :class="{ active: modoAsignacion === 'existente' }" @click="modoAsignacion = 'existente'">
                Vehículo Existente
              </button>
              <button type="button" class="tab" :class="{ active: modoAsignacion === 'nuevo' }" @click="modoAsignacion = 'nuevo'">
                Nuevo Vehículo
              </button>
            </div>

            <!-- MODO EXISTENTE -->
            <div v-if="modoAsignacion === 'existente'" class="tab-panel">
              <div class="form-group">
                <label class="label">Seleccionar Vehículo</label>
                <select v-model="form.vehiculo_id" class="input select" :class="{ 'input-error': errores.vehiculo_id }">
                  <option :value="null">-- Selecciona un vehículo --</option>
                  <option v-for="v in vehiculosLibres" :key="v.id" :value="v.id">
                    {{ v.patente }} - {{ v.marca }} {{ v.modelo }}
                  </option>
                </select>
                <p v-if="errores.vehiculo_id" class="field-error">{{ errores.vehiculo_id[0] || errores.vehiculo_id }}</p>
              </div>
            </div>

            <!-- MODO NUEVO -->
            <div v-if="modoAsignacion === 'nuevo'" class="tab-panel">
              <div class="form-group">
                <label class="label">Patente</label>
                <input v-model="form.vehiculo_patente" type="text" class="input" maxlength="10" placeholder="ABCD12" :class="{ 'input-error': errores.vehiculo_patente }"/>
                <p v-if="errores.vehiculo_patente" class="field-error">{{ errores.vehiculo_patente[0] }}</p>
              </div>
              <div class="form-row mt-2">
                <div class="form-group">
                  <label class="label">Marca</label>
                  <input v-model="form.vehiculo_marca" type="text" class="input" placeholder="Ej: Toyota" maxlength="60"/>
                </div>
                <div class="form-group">
                  <label class="label">Modelo</label>
                  <input v-model="form.vehiculo_modelo" type="text" class="input" placeholder="Ej: Hilux" maxlength="60"/>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="errores.non_field_errors" class="field-error">{{ errores.non_field_errors[0] }}</p>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push(ruta('/conductores'))" :disabled="guardando">
            Cancelar
          </button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : 'Crear Conductor' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 720px; }
.breadcrumb { margin-bottom: 1.5rem; }
.btn-back { display: inline-flex; align-items: center; gap: 0.375rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; background: none; border: none; cursor: pointer; padding: 0; font-family: inherit; transition: color 0.15s; }
.btn-back:hover { color: #4F46E5; }
.btn-back svg { width: 16px; height: 16px; }
.page-title   { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.75rem; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem; }
.form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-section { padding-bottom: 0.5rem; }
.section-title { font-size: 1rem; font-weight: 700; color: #1E1B4B; margin: 0 0 1.25rem; border-bottom: 2px solid #F3F4F6; padding-bottom: 0.5rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.opcional { font-weight: 400; color: #9CA3AF; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236B7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 0.75rem center; background-size: 1rem; padding-right: 2.5rem; cursor: pointer; }
.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }
.rut-spinner {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  width: 16px; height: 16px;
  border: 2px solid #D1D5DB; border-top-color: #7C3AED;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; transition: border-color 0.15s; }
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; font-family: inherit; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }

.btn-link { background: none; border: none; color: #4F46E5; font-size: 0.75rem; font-weight: 600; cursor: pointer; padding: 0; text-align: left; margin-top: 0.25rem; text-decoration: underline; }
.btn-link:hover { color: #3730A3; }
.flex-col { display: flex; flex-direction: column; }
.gap-1 { gap: 0.25rem; }

/* Assignment Styles */
.assignment-section { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.25rem; margin-top: 0.5rem; }
.assignment-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.assignment-header .section-title { border: none; margin: 0; padding: 0; }
.assignment-content { margin-top: 1.25rem; }
.tabs { display: flex; gap: 0.5rem; background: #F3F4F6; padding: 0.25rem; border-radius: 8px; margin-bottom: 1.25rem; }
.tab { flex: 1; padding: 0.5rem; border: none; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; color: #6B7280; background: transparent; cursor: pointer; transition: all 0.2s; font-family: inherit; }
.tab.active { background: #fff; color: #4F46E5; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.tab-panel { animation: fadeIn 0.2s ease-out; }
.mt-2 { margin-top: 1rem; }

/* Switch Toggle */
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #D1D5DB; transition: .4s; }
.slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; }
input:checked + .slider { background-color: #4F46E5; }
input:focus + .slider { box-shadow: 0 0 1px #4F46E5; }
input:checked + .slider:before { transform: translateX(20px); }
.slider.round { border-radius: 34px; }
.slider.round:before { border-radius: 50%; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
@keyframes spin { to { transform: rotate(360deg); } }

.pwd-strength { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.375rem; }
.pwd-strength-bar { flex: 1; height: 4px; background: #E5E7EB; border-radius: 99px; overflow: hidden; }
.pwd-strength-fill { height: 100%; border-radius: 99px; transition: width 0.3s; }
.pwd-strength-debil  { width: 33%; background: #EF4444; }
.pwd-strength-media  { width: 66%; background: #F59E0B; }
.pwd-strength-fuerte { width: 100%; background: #10B981; }
.pwd-strength-label { font-size: 0.75rem; font-weight: 500; white-space: nowrap; }
.pwd-level-debil  { color: #EF4444; }
.pwd-level-media  { color: #F59E0B; }
.pwd-level-fuerte { color: #10B981; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-title { font-size: 1.25rem; }
  .form-row { grid-template-columns: 1fr !important; }
  /* Scroll horizontal con thumb visible */
  .tabla-wrap, .tabla-card, .sc-table-wrap, .card, .table-wrap {
    overflow-x: scroll !important;  /* scroll (no auto) → track siempre visible */
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: #A78BFA #EDE9FE;
  }
  .tabla-wrap::-webkit-scrollbar,
  .tabla-card::-webkit-scrollbar,
  .sc-table-wrap::-webkit-scrollbar,
  .card::-webkit-scrollbar,
  .table-wrap::-webkit-scrollbar { height: 8px; }
  .tabla-wrap::-webkit-scrollbar-track,
  .tabla-card::-webkit-scrollbar-track,
  .sc-table-wrap::-webkit-scrollbar-track,
  .card::-webkit-scrollbar-track,
  .table-wrap::-webkit-scrollbar-track { background: #EDE9FE; border-radius: 999px; }
  .tabla-wrap::-webkit-scrollbar-thumb,
  .tabla-card::-webkit-scrollbar-thumb,
  .sc-table-wrap::-webkit-scrollbar-thumb,
  .card::-webkit-scrollbar-thumb,
  .table-wrap::-webkit-scrollbar-thumb { background: #7C3AED; border-radius: 999px; min-width: 40px; }
  .tabla-wrap::-webkit-scrollbar-thumb:hover,
  .tabla-card::-webkit-scrollbar-thumb:hover,
  .sc-table-wrap::-webkit-scrollbar-thumb:hover,
  .card::-webkit-scrollbar-thumb:hover,
  .table-wrap::-webkit-scrollbar-thumb:hover { background: #6D28D9; }
  .tabla-wrap table, .tabla-card table, .sc-table-wrap table,
  .card table, .table-wrap table,
  .tabla, .table, .tabla-flotas, .tabla-vehiculos { min-width: 520px; }

}
</style>

