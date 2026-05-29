<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../utils/empresaActiva.js'
import { useToast } from '../../../utils/useToast.js'
import { validarTelefono, validarNombre } from '../../../utils/validators.js'
import InputTelefono from '../../../components/InputTelefono.vue'

const router   = useRouter()
const { ruta } = useEmpresaNav()
const route  = useRoute()
const id     = route.params.id

const toast     = useToast()
const cargando  = ref(true)
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})

const form = ref({ nombre: '', apellido_paterno: '', apellido_materno: '', email: '', telefono: '', licencia: '' })

const cargar = async () => {
  try {
    const res = await apiFetchEmpresa(`/api/empresa/conductores/${id}/`)
    if (!res.ok) throw new Error('Conductor no encontrado')
    const c = await res.json()
    form.value.nombre           = c.primer_nombre || ''
    form.value.apellido_paterno = c.apellido_paterno || ''
    form.value.apellido_materno = c.apellido_materno || ''
    form.value.email            = c.email
    form.value.telefono         = c.telefono || ''
    form.value.licencia         = c.licencia  || ''
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
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

  // Validar teléfono (obligatorio)
  const telResult = validarTelefono(form.value.telefono)
  if (!telResult.valido) {
    errores.value = { telefono: [telResult.error] }
    return
  }

  guardando.value = true
  try {
    const res  = await apiFetchEmpresa(`/api/empresa/conductores/${id}/`, { method: 'PUT', body: { ...form.value } })
    const data = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al actualizar el conductor'
      return
    }
    toast.success('Conductor actualizado exitosamente')
    router.push(ruta('/conductores'))
  } catch {
    error.value = 'Error de conexión con el servidor'
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
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

    <h1 class="page-title">Editar Conductor</h1>
    <p class="page-subtitle">Modifica los datos del conductor</p>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando datos...</span>
    </div>

    <div v-else class="card">
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
            <label class="label">Email</label>
            <input v-model="form.email" type="email" class="input"
              :class="{ 'input-error': errores.email }"
              placeholder="conductor@ejemplo.com" required autocomplete="off" maxlength="50"/>
            <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
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
            <label class="label">N° Licencia <span class="opcional">(opcional)</span></label>
            <input v-model="form.licencia" type="text" class="input" placeholder="Ej: 123456789" autocomplete="off" maxlength="50"/>
          </div>
        </div>

        <p v-if="errores.non_field_errors" class="field-error">{{ errores.non_field_errors[0] }}</p>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push(ruta('/conductores'))" :disabled="guardando">
            Cancelar
          </button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : 'Guardar Cambios' }}
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
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem; }
.form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.opcional { font-weight: 400; color: #9CA3AF; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; transition: border-color 0.15s; }
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; font-family: inherit; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
