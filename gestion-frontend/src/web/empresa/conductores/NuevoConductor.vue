<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../utils/empresaActiva.js'

const router    = useRouter()
const { ruta }  = useEmpresaNav()
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})

const form = ref({
  nombre_completo: '',
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
  vehiculo_flota_id: null,
  vehiculo_flota_nuevo: ''
})

const asignarVehiculo = ref(false)
const modoAsignacion = ref('existente') // 'existente' o 'nuevo'
const flotas = ref([])
const vehiculosLibres = ref([])
const crearNuevaFlota = ref(false)

onMounted(async () => {
  try {
    const [resFlotas, resVehiculos] = await Promise.all([
      apiFetchEmpresa('/api/empresa/flotas/'),
      apiFetchEmpresa('/api/empresa/vehiculos/')
    ])
    if (resFlotas.ok) {
        flotas.value = await resFlotas.json()
        if (flotas.value.length === 0) {
            crearNuevaFlota.value = true
            form.value.vehiculo_flota_nuevo = "Flota Principal"
        }
    }
    if (resVehiculos.ok) {
      const todos = await resVehiculos.json()
      vehiculosLibres.value = todos.filter(v => v.activo) 
    }
  } catch (err) {
    console.error("Error cargando datos auxiliares", err)
  }
})

const formatRut = (value) => {
  let cleaned = value.replace(/[^0-9kK]/g, '')
  if (cleaned.length < 2) return cleaned
  const body = cleaned.slice(0, -1)
  const dv   = cleaned.slice(-1).toUpperCase()
  return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${dv}`
}
const onRutInput = (e) => { form.value.rut = formatRut(e.target.value) }

const guardar = async () => {
  error.value   = ''
  errores.value = {}
  guardando.value = true

  const payload = { ...form.value }
  if (!asignarVehiculo.value) {
    payload.vehiculo_id = null
    payload.crear_vehiculo = false
  } else {
    payload.crear_vehiculo = modoAsignacion.value === 'nuevo'
    if (payload.crear_vehiculo) {
        payload.vehiculo_id = null
        if (!crearNuevaFlota.value) {
            payload.vehiculo_flota_nuevo = ''
        }
    } else {
      payload.vehiculo_patente = ''
      payload.vehiculo_marca = ''
      payload.vehiculo_modelo = ''
      payload.vehiculo_flota_id = null
      payload.vehiculo_flota_nuevo = ''
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
              <label class="label">Nombre completo</label>
              <input v-model="form.nombre_completo" type="text" class="input"
                :class="{ 'input-error': errores.nombre_completo }"
                placeholder="Ej: Juan Pérez González" required autocomplete="off"/>
              <p v-if="errores.nombre_completo" class="field-error">{{ errores.nombre_completo[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">RUT</label>
              <input :value="form.rut" @input="onRutInput" type="text" class="input"
                :class="{ 'input-error': errores.rut }"
                placeholder="12.345.678-9" maxlength="12" required autocomplete="off"/>
              <p v-if="errores.rut" class="field-error">{{ errores.rut[0] }}</p>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Email</label>
              <input v-model="form.email" type="email" class="input"
                :class="{ 'input-error': errores.email }"
                placeholder="conductor@ejemplo.com" required autocomplete="off"/>
              <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
            </div>
            <div class="form-group">
              <label class="label">Contraseña</label>
              <input v-model="form.password" type="password" class="input"
                :class="{ 'input-error': errores.password }"
                placeholder="Mínimo 8 caracteres" required autocomplete="new-password"/>
              <p v-if="errores.password" class="field-error">{{ errores.password[0] }}</p>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="label">Teléfono <span class="opcional">(opcional)</span></label>
              <input v-model="form.telefono" type="text" class="input"
                placeholder="+56 9 1234 5678" autocomplete="off"/>
            </div>
            <div class="form-group">
              <label class="label">N° Licencia <span class="opcional">(opcional)</span></label>
              <input v-model="form.licencia" type="text" class="input"
                placeholder="Ej: 123456789" autocomplete="off"/>
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
              <div class="form-row">
                <div class="form-group">
                  <label class="label">Patente</label>
                  <input v-model="form.vehiculo_patente" type="text" class="input" maxlength="10" placeholder="ABCD12" :class="{ 'input-error': errores.vehiculo_patente }"/>
                  <p v-if="errores.vehiculo_patente" class="field-error">{{ errores.vehiculo_patente[0] }}</p>
                </div>
                <div class="form-group">
                  <label class="label">Flota</label>
                  <div class="flex-col gap-1">
                    <select v-if="!crearNuevaFlota" v-model="form.vehiculo_flota_id" class="input select" :class="{ 'input-error': errores.vehiculo_flota_id }">
                        <option :value="null">-- Selecciona Flota --</option>
                        <option v-for="f in flotas" :key="f.id" :value="f.id">{{ f.nombre }}</option>
                    </select>
                    <input v-else v-model="form.vehiculo_flota_nuevo" type="text" class="input" placeholder="Nombre de la nueva flota" :class="{ 'input-error': errores.vehiculo_flota_nuevo }"/>
                    
                    <button type="button" class="btn-link" @click="crearNuevaFlota = !crearNuevaFlota">
                        {{ crearNuevaFlota ? (flotas.length > 0 ? 'Seleccionar flota existente' : '') : '+ Crear nueva flota' }}
                    </button>
                  </div>
                  <p v-if="errores.vehiculo_flota_id" class="field-error">{{ errores.vehiculo_flota_id[0] }}</p>
                  <p v-if="errores.vehiculo_flota_nuevo" class="field-error">{{ errores.vehiculo_flota_nuevo[0] }}</p>
                </div>
              </div>
              <div class="form-row mt-2">
                <div class="form-group">
                  <label class="label">Marca</label>
                  <input v-model="form.vehiculo_marca" type="text" class="input" placeholder="Ej: Toyota"/>
                </div>
                <div class="form-group">
                  <label class="label">Modelo</label>
                  <input v-model="form.vehiculo_modelo" type="text" class="input" placeholder="Ej: Hilux"/>
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
</style>

