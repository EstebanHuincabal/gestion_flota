<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import { validarPassword, validarTelefono, validarNombre, validarRut } from '../../utils/validators.js'
import InputTelefono from '../../components/InputTelefono.vue'

const router  = useRouter()
const route   = useRoute()
const toast     = useToast()
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})
const empresas  = ref([])

// Detectar si venimos del flujo "crear empresa"
const desdeEmpresa    = computed(() => !!route.query.empresa_id)
const empresaFijada   = computed(() => ({
  id:     Number(route.query.empresa_id),
  nombre: route.query.empresa_nombre || '',
}))

const form = ref({
  nombre:           '',
  apellido_paterno: '',
  apellido_materno: '',
  telefono: '',
  rut:      '',
  email:    '',
  password: '',
  rol:      'USUARIO',
  empresa_id: null,
})

const nivelPassword = computed(() => {
  if (!form.value.password) return null
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

const cargarEmpresas = async () => {
  if (desdeEmpresa.value) {
    form.value.empresa_id = empresaFijada.value.id
  } else {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = (await res.json()).filter(e => e.estado === 'activa')
  }
}

const volver = () => router.push(desdeEmpresa.value ? '/empresas' : '/usuarios')

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

  // Validar teléfono (obligatorio)
  const telR = validarTelefono(form.value.telefono)
  if (!telR.valido) { errores.value = { telefono: [telR.error] }; return }

  // Validar contraseña
  const pwdResult = validarPassword(form.value.password)
  if (!pwdResult.valido) {
    errores.value = { password: [pwdResult.error] }
    return
  }

  // Verificación final del RUT contra la BD antes de crear
  clearTimeout(_debounceRut)
  if (form.value.rut) {
    await verificarRut()
    if (errores.value.rut) return
  }

  guardando.value = true
  try {
    const payload = { ...form.value }
    const res  = await apiFetch('/api/usuarios/crear/', { method: 'POST', body: payload })
    const data = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al crear el usuario'
      return
    }
    toast.success('Usuario creado exitosamente')
    router.push(desdeEmpresa.value ? '/empresas' : '/usuarios')
  } catch {
    error.value = 'Error de conexión con el servidor'
  } finally {
    guardando.value = false
  }
}

onMounted(cargarEmpresas)
</script>

<template>
  <div class="page">
    <div class="breadcrumb">
      <button class="btn-back" @click="volver">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        {{ desdeEmpresa ? 'Volver a Empresas' : 'Volver a Usuarios' }}
      </button>
    </div>

    <!-- Banner informativo cuando viene del flujo empresa -->
    <div v-if="desdeEmpresa" class="banner-empresa">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <span>
        Empresa <strong>{{ empresaFijada.nombre }}</strong> creada.
        Ahora registra su administrador.
      </span>
    </div>

    <h1 class="page-title">{{ desdeEmpresa ? 'Crear Administrador' : 'Nuevo Usuario' }}</h1>
    <p class="page-subtitle">
      {{ desdeEmpresa
        ? 'Este usuario quedará asignado como administrador de la empresa'
        : 'Completa los datos para registrar un nuevo usuario' }}
    </p>

    <div class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>

      <form @submit.prevent="guardar" class="form">

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
            <label class="label">Teléfono</label>
            <InputTelefono v-model="form.telefono" :error="!!errores.telefono" />
            <p v-if="errores.telefono" class="field-error">{{ errores.telefono[0] }}</p>
          </div>
          <div class="form-group">
            <label class="label">Email</label>
            <input v-model="form.email" type="email" class="input"
              :class="{ 'input-error': errores.email }"
              placeholder="usuario@ejemplo.com" required autocomplete="off" maxlength="50"/>
            <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label">Contraseña</label>
            <input v-model="form.password" type="password" class="input"
              :class="{ 'input-error': errores.password }"
              placeholder="Mín. 8 chars, 1 mayúscula, 1 número" required autocomplete="new-password"/>
            <p v-if="errores.password" class="field-error">{{ errores.password[0] }}</p>
            <div v-if="form.password && nivelPassword" class="pwd-strength">
              <div class="pwd-strength-bar">
                <div class="pwd-strength-fill" :class="`pwd-strength-${nivelPassword}`"/>
              </div>
              <span class="pwd-strength-label" :class="`pwd-level-${nivelPassword}`">
                {{ nivelPassword === 'debil' ? 'Débil' : nivelPassword === 'media' ? 'Media' : 'Fuerte' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Empresa fijada (flujo desde NuevaEmpresa) -->
        <div v-if="desdeEmpresa" class="form-group">
          <label class="label">Empresa</label>
          <div class="input-bloqueado">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
            {{ empresaFijada.nombre }}
            <span class="badge-fijo">Asignada automáticamente</span>
          </div>
        </div>

        <!-- Empresa selector (flujo normal) -->
        <div v-else class="form-group">
          <label class="label">Empresa</label>
          <select v-model="form.empresa_id" class="input select"
            :class="{ 'input-error': errores.empresa_id }" required>
            <option :value="null">— Seleccionar empresa —</option>
            <option v-for="e in empresas" :key="e.id" :value="e.id">{{ e.nombre }}</option>
          </select>
          <p v-if="errores.empresa_id" class="field-error">{{ errores.empresa_id[0] }}</p>
        </div>

        <!-- Selector de rol -->
        <div class="form-group">
          <label class="label">Rol</label>
          <select v-model="form.rol" class="input select">
            <option value="USUARIO">Usuario</option>
            <option value="CONDUCTOR">Conductor</option>
            <option value="SUPERADMIN">Super Administrador</option>
          </select>
        </div>

        <p v-if="errores.non_field_errors" class="field-error">{{ errores.non_field_errors[0] }}</p>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="volver" :disabled="guardando">
            Cancelar
          </button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : (desdeEmpresa ? 'Crear Administrador' : 'Crear Usuario') }}
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

.banner-empresa {
  display: flex; align-items: center; gap: 0.75rem;
  background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 10px;
  padding: 0.875rem 1rem; font-size: 0.875rem; color: #3730A3;
  margin-bottom: 1.25rem;
}
.banner-empresa svg { width: 18px; height: 18px; flex-shrink: 0; color: #4F46E5; }
.banner-empresa strong { font-weight: 700; }

.page-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.75rem; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem; }
.form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }

.input-bloqueado {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.65rem 0.875rem; border: 1.5px solid #E5E7EB; border-radius: 10px;
  font-size: 0.875rem; color: #374151; background: #F9FAFB; font-weight: 500;
}
.input-bloqueado svg { width: 16px; height: 16px; color: #7C3AED; flex-shrink: 0; }
.badge-fijo {
  margin-left: auto; font-size: 0.7rem; font-weight: 600;
  background: #EDE9FE; color: #5B21B6; padding: 0.2rem 0.5rem; border-radius: 999px;
}

.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.select { cursor: pointer; }
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
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; font-family: inherit; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
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
</style>
