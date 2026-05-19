<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'

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
  nombre_completo: '',
  rut:      '',
  email:    '',
  password: '',
  rol:      'USUARIO',
  empresa_id: null,
})

const formatRut = (value) => {
  let cleaned = value.replace(/[^0-9kK]/g, '')
  if (cleaned.length < 2) return cleaned
  const body = cleaned.slice(0, -1)
  const dv   = cleaned.slice(-1).toUpperCase()
  return `${body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${dv}`
}
const onRutInput = (e) => { form.value.rut = formatRut(e.target.value) }

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
              placeholder="usuario@ejemplo.com" required autocomplete="off"/>
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
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; transition: border-color 0.15s; }
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; font-family: inherit; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

</style>
