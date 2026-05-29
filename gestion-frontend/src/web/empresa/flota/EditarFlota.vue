<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../utils/empresaActiva.js'

const router = useRouter()
const { ruta } = useEmpresaNav()
const route  = useRoute()
const id     = route.params.id
const cargando  = ref(true)
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})
const form      = ref({ nombre: '' })

const cargar = async () => {
  try {
    const res = await apiFetchEmpresa(`/api/empresa/flotas/${id}/`)
    if (!res.ok) throw new Error('Flota no encontrada')
    const data = await res.json()
    form.value.nombre = data.nombre
  } catch (e) { error.value = e.message }
  finally { cargando.value = false }
}

const guardar = async () => {
  error.value = ''
  errores.value = {}
  guardando.value = true
  try {
    const res  = await apiFetchEmpresa(`/api/empresa/flotas/${id}/`, { method: 'PUT', body: form.value })
    const data = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al guardar'
      return
    }
    router.push(ruta('/flota'))
  } catch { error.value = 'Error de conexión' }
  finally { guardando.value = false }
}

onMounted(cargar)
</script>

<template>
  <div class="page">
    <button class="btn-back" @click="router.push(ruta('/flota'))">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Volver a Flota
    </button>
    <h1 class="page-title">Editar Flota</h1>
    <p class="page-subtitle">Modifica el nombre de la flota</p>

    <div v-if="cargando" class="loading"><div class="spinner"/> <span>Cargando...</span></div>
    <div v-else class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>
      <form @submit.prevent="guardar" class="form">
        <div class="form-group">
          <label class="label">Nombre de la flota</label>
          <input v-model="form.nombre" type="text" class="input" :class="{ 'input-error': errores.nombre }" required maxlength="100"/>
          <p v-if="errores.nombre" class="field-error">{{ errores.nombre[0] }}</p>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push(ruta('/flota'))" :disabled="guardando">Cancelar</button>
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
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 500px; }
.btn-back { display: inline-flex; align-items: center; gap: 0.375rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; background: none; border: none; cursor: pointer; padding: 0; font-family: inherit; transition: color 0.15s; margin-bottom: 1.5rem; }
.btn-back:hover { color: #4F46E5; }
.btn-back svg { width: 16px; height: 16px; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.75rem; }
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem; }
.form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
