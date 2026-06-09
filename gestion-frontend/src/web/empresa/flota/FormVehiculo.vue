<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, EMPRESA_TODAS } from '../../../utils/empresaActiva.js'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'
import { validarPatente, validarAnioVehiculo, soloDescripcion } from '../../../utils/validators.js'

const props = defineProps({ modo: { type: String, default: 'nuevo' } })
const router = useRouter()
const route  = useRoute()
const { ruta } = useEmpresaNav()
const vehiculoId = route.params.id

const toast     = useToast()
const cargando  = ref(props.modo === 'editar')
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})

const esSuperadmin = computed(() => {
  try { return JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN' } catch { return false }
})
const esTodas       = computed(() => getEmpresaActiva()?.id === EMPRESA_TODAS)
const empresas      = ref([])
const empresaIdForm = ref('')

const form = ref({
  patente: '',
  marca: '',
  modelo: '',
  anio: '',
  tipo_combustible: 'bencina',
  km_actuales: 0,
})

// Foto del vehículo
const fotoFile    = ref(null)      // File nuevo elegido (si lo hay)
const fotoPreview = ref(null)      // URL para previsualizar (existente o nueva)

function onFotoChange(e) {
  const f = e.target.files?.[0]
  if (!f) return
  if (f.size > 8 * 1024 * 1024) { toast.error('La imagen no puede superar 8 MB.'); e.target.value = ''; return }
  if (!f.type.startsWith('image/')) { toast.error('El archivo debe ser una imagen.'); e.target.value = ''; return }
  fotoFile.value    = f
  fotoPreview.value = URL.createObjectURL(f)
}
function quitarFoto() {
  fotoFile.value    = null
  fotoPreview.value = null
}

const formatPatente = (v) => v.toUpperCase().replace(/[^A-Z0-9]/g, '')

const cargarVehiculo = async () => {
  try {
    const res = await apiFetchEmpresa(`/api/empresa/vehiculos/${vehiculoId}/`)
    if (!res.ok) throw new Error('Vehículo no encontrado')
    const v = await res.json()
    form.value = { patente: v.patente, marca: v.marca, modelo: v.modelo, anio: v.anio || '', tipo_combustible: v.tipo_combustible, km_actuales: v.km_actuales }
    fotoPreview.value = v.foto_url || null
  } catch (e) { error.value = e.message }
  finally { cargando.value = false }
}

const guardar = async () => {
  error.value = ''
  errores.value = {}

  // Validar patente
  const patenteResult = validarPatente(form.value.patente)
  if (!patenteResult.valido) {
    errores.value = { patente: [patenteResult.error] }
    return
  }

  // Validar año si se ingresó
  if (form.value.anio !== '' && form.value.anio !== null) {
    const anioResult = validarAnioVehiculo(form.value.anio)
    if (!anioResult.valido) {
      errores.value = { anio: [anioResult.error] }
      return
    }
  }

  if (esTodas.value && props.modo !== 'editar' && !empresaIdForm.value) {
    error.value = 'Selecciona una empresa para registrar el vehículo.'
    return
  }

  guardando.value = true
  try {
    const url     = props.modo === 'editar' ? `/api/empresa/vehiculos/${vehiculoId}/` : '/api/empresa/vehiculos/'
    const method  = props.modo === 'editar' ? 'PUT' : 'POST'

    // Con foto nueva → multipart; si no, JSON como siempre.
    let body
    if (fotoFile.value) {
      body = new FormData()
      body.append('patente',          form.value.patente)
      body.append('marca',            form.value.marca || '')
      body.append('modelo',           form.value.modelo || '')
      if (form.value.anio) body.append('anio', form.value.anio)
      body.append('tipo_combustible', form.value.tipo_combustible)
      body.append('km_actuales',      form.value.km_actuales)
      body.append('foto',             fotoFile.value, fotoFile.value.name)
      if (esTodas.value && props.modo !== 'editar') body.append('empresa_id', empresaIdForm.value)
    } else {
      body = { ...form.value, anio: form.value.anio || null }
      if (esTodas.value && props.modo !== 'editar') body.empresa_id = empresaIdForm.value
    }
    const res  = await apiFetchEmpresa(url, { method, body })
    const data    = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return  // el toast global ya lo notifica
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al guardar'
      return
    }
    toast.success(props.modo === 'editar' ? 'Vehículo actualizado exitosamente' : 'Vehículo registrado exitosamente')
    router.push(ruta('/flota'))
  } catch { error.value = 'Error de conexión' }
  finally { guardando.value = false }
}

onMounted(async () => {
  if (props.modo === 'editar') await cargarVehiculo()
  if (props.modo !== 'editar' && esSuperadmin.value) {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = await res.json()
  }
})
</script>

<template>
  <div class="page">
    <button class="btn-back" @click="router.push(ruta('/flota'))">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Volver a Flota
    </button>
    <h1 class="page-title">{{ modo === 'editar' ? 'Editar Vehículo' : 'Nuevo Vehículo' }}</h1>
    <p class="page-subtitle">{{ modo === 'editar' ? 'Modifica los datos del vehículo' : 'Registra un nuevo vehículo' }}</p>

    <div v-if="cargando" class="loading"><div class="spinner"/> <span>Cargando...</span></div>

    <div v-else class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>
      <form @submit.prevent="guardar" class="form">

        <!-- Selector de empresa (solo SUPERADMIN en modo "Todas", creación) -->
        <div v-if="esTodas && modo !== 'editar'" class="form-group" style="margin-bottom:1.25rem">
          <label class="label">Empresa</label>
          <select v-model="empresaIdForm" class="input select" required>
            <option value="" disabled>Seleccionar empresa…</option>
            <option v-for="e in empresas" :key="e.id" :value="e.id">{{ e.nombre }}</option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label">Patente</label>
            <input :value="form.patente" @input="form.patente = formatPatente($event.target.value)"
              type="text" class="input" :class="{ 'input-error': errores.patente }"
              placeholder="ABCD12" maxlength="8" required autocomplete="off"/>
            <p v-if="errores.patente" class="field-error">{{ errores.patente[0] }}</p>
          </div>
          <div class="form-group">
            <label class="label">Tipo de combustible</label>
            <select v-model="form.tipo_combustible" class="input select">
              <option value="bencina">Bencina</option>
              <option value="diesel">Diésel</option>
              <option value="electrico">Eléctrico</option>
              <option value="hibrido">Híbrido</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label">Marca</label>
            <input v-model="form.marca" @input="form.marca = soloDescripcion(form.marca)"
              type="text" class="input" placeholder="Ej: Toyota" autocomplete="off" maxlength="60"/>
          </div>
          <div class="form-group">
            <label class="label">Modelo</label>
            <input v-model="form.modelo" @input="form.modelo = soloDescripcion(form.modelo)"
              type="text" class="input" placeholder="Ej: Hilux 560" autocomplete="off" maxlength="60"/>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label">Año</label>
            <input v-model="form.anio" type="number" class="input"
              :class="{ 'input-error': errores.anio }"
              placeholder="2020" min="1950" :max="new Date().getFullYear() + 1"/>
            <p v-if="errores.anio" class="field-error">{{ errores.anio[0] }}</p>
          </div>
          <div class="form-group">
            <label class="label">KM actuales</label>
            <input v-model="form.km_actuales" type="number" class="input" :class="{ 'input-error': errores.km_actuales }" min="0" required/>
            <p v-if="errores.km_actuales" class="field-error">{{ errores.km_actuales[0] }}</p>
          </div>
        </div>

        <!-- Foto del vehículo -->
        <div class="form-group">
          <label class="label">Foto del vehículo <span class="label-opt">(opcional)</span></label>
          <div class="foto-row">
            <div class="foto-preview">
              <img v-if="fotoPreview" :src="fotoPreview" alt="Foto del vehículo"/>
              <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
              </svg>
            </div>
            <div class="foto-acciones">
              <label class="btn-foto">
                <input type="file" accept="image/*" class="hidden-input" @change="onFotoChange"/>
                {{ fotoPreview ? 'Cambiar foto' : 'Subir foto' }}
              </label>
              <button v-if="fotoPreview" type="button" class="btn-foto-quitar" @click="quitarFoto">Quitar</button>
              <p class="foto-hint">JPG o PNG · máx 8 MB. Ayuda a identificar el vehículo de un vistazo.</p>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push(ruta('/flota'))" :disabled="guardando">Cancelar</button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : (modo === 'editar' ? 'Guardar Cambios' : 'Agregar Vehículo') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 680px; }
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
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.select { cursor: pointer; }
.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }
.field-help  { font-size: 0.8125rem; color: #9CA3AF; margin: 0.25rem 0 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

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

/* ── Foto del vehículo ── */
.label-opt { font-weight: 400; color: #9CA3AF; font-size: 0.8em; }
.foto-row { display: flex; gap: 1rem; align-items: center; }
.foto-preview {
  flex-shrink: 0;
  width: 120px; height: 90px;
  border-radius: 10px;
  border: 1.5px dashed #D1D5DB;
  background: #F9FAFB;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.foto-preview img { width: 100%; height: 100%; object-fit: cover; }
.foto-preview svg { width: 34px; height: 34px; color: #D1D5DB; }
.foto-acciones { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-start; }
.hidden-input { display: none; }
.btn-foto {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: #EEF2FF; color: #4338CA;
  border: 1px solid #C7D2FE; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 600; cursor: pointer;
}
.btn-foto:hover { background: #E0E7FF; }
.btn-foto-quitar {
  padding: 0.35rem 0.75rem;
  background: none; border: none;
  color: #DC2626; font-size: 0.8125rem; font-weight: 500; cursor: pointer;
}
.btn-foto-quitar:hover { text-decoration: underline; }
.foto-hint { font-size: 0.75rem; color: #9CA3AF; margin: 0; max-width: 280px; }
</style>
