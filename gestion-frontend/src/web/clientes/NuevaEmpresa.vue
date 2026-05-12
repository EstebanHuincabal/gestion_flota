<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()
const guardando = ref(false)
const error = ref('')
const errores = ref({})

const REGIONES = [
  { value: 'arica_y_parinacota', label: 'Arica y Parinacota' },
  { value: 'tarapaca',           label: 'Tarapacá' },
  { value: 'antofagasta',        label: 'Antofagasta' },
  { value: 'atacama',            label: 'Atacama' },
  { value: 'coquimbo',           label: 'Coquimbo' },
  { value: 'valparaiso',         label: 'Valparaíso' },
  { value: 'metropolitana',      label: 'Metropolitana' },
  { value: 'ohiggins',           label: "O'Higgins" },
  { value: 'maule',              label: 'Maule' },
  { value: 'nuble',              label: 'Ñuble' },
  { value: 'biobio',             label: 'Biobío' },
  { value: 'la_araucania',       label: 'La Araucanía' },
  { value: 'los_rios',           label: 'Los Ríos' },
  { value: 'los_lagos',          label: 'Los Lagos' },
  { value: 'aysen',              label: 'Aysén' },
  { value: 'magallanes',         label: 'Magallanes' },
]

const form = ref({
  nombre:   '',
  rut:      '',
  estado:   'activa',
  email:    '',
  telefono: '',
  direccion: '',
  comuna:   '',
  ciudad:   '',
  region:   '',
  pais:     'Chile',
})

const aplicarFormatoRut = (val) => {
  if (!val) return ''
  val = val.replace(/[^0-9kK]/g, '').toUpperCase()
  if (val.length <= 1) return val
  const dv     = val.slice(-1)
  let cuerpo   = val.slice(0, -1)
  cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${dv}`
}

const formatRut = (e) => {
  form.value.rut = aplicarFormatoRut(e.target.value)
}

const guardar = async () => {
  error.value   = ''
  errores.value = {}
  guardando.value = true

  try {
    const res  = await apiFetch('/api/empresas/crear/', { method: 'POST', body: form.value })
    const data = await res.json()

    if (!res.ok) {
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al crear la empresa'
      return
    }

    router.push({ path: '/usuarios/nuevo', query: { empresa_id: data.id, empresa_nombre: data.nombre } })
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
      <button class="btn-back" @click="router.push('/empresas')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        Volver a Empresas
      </button>
    </div>

    <div class="page-header">
      <h1 class="page-title">Nueva Empresa</h1>
      <p class="page-subtitle">Completa los datos para registrar una nueva empresa</p>
    </div>

    <div class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>

      <form @submit.prevent="guardar" class="form">

        <!-- ── Datos básicos ── -->
        <h2 class="section-title">Datos básicos</h2>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="nombre">Nombre de la empresa <span class="required">*</span></label>
            <input id="nombre" v-model="form.nombre" type="text" class="input"
              :class="{ 'input-error': errores.nombre }"
              placeholder="Ej: Transportes del Norte S.A." required autocomplete="off"/>
            <p v-if="errores.nombre" class="field-error">{{ errores.nombre[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label" for="rut">RUT <span class="required">*</span></label>
            <input id="rut" :value="form.rut" @input="formatRut" type="text" class="input"
              :class="{ 'input-error': errores.rut }"
              placeholder="Ej: 76.123.456-7" required autocomplete="off"/>
            <p v-if="errores.rut" class="field-error">{{ errores.rut[0] }}</p>
          </div>
        </div>

        <div class="form-group form-group--small">
          <label class="label" for="estado">Estado</label>
          <select id="estado" v-model="form.estado" class="input select">
            <option value="activa">Activa</option>
            <option value="suspendida">Suspendida</option>
          </select>
        </div>

        <!-- ── Contacto ── -->
        <h2 class="section-title">Contacto</h2>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="email">Email de contacto</label>
            <input id="email" v-model="form.email" type="email" class="input"
              :class="{ 'input-error': errores.email }"
              placeholder="contacto@empresa.cl" autocomplete="off"/>
            <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label" for="telefono">Teléfono</label>
            <input id="telefono" v-model="form.telefono" type="text" class="input"
              placeholder="+56 9 1234 5678" autocomplete="off"/>
          </div>
        </div>

        <!-- ── Ubicación ── -->
        <h2 class="section-title">Ubicación</h2>

        <div class="form-group">
          <label class="label" for="direccion">Dirección</label>
          <input id="direccion" v-model="form.direccion" type="text" class="input"
            placeholder="Av. Providencia 1234, Of. 5" autocomplete="off"/>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="comuna">Comuna</label>
            <input id="comuna" v-model="form.comuna" type="text" class="input"
              placeholder="Providencia" autocomplete="off"/>
          </div>

          <div class="form-group">
            <label class="label" for="ciudad">Ciudad</label>
            <input id="ciudad" v-model="form.ciudad" type="text" class="input"
              placeholder="Santiago" autocomplete="off"/>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="region">Región</label>
            <select id="region" v-model="form.region" class="input select">
              <option value="">— Sin especificar —</option>
              <option v-for="r in REGIONES" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div class="form-group">
            <label class="label" for="pais">País</label>
            <input id="pais" v-model="form.pais" type="text" class="input"
              placeholder="Chile" autocomplete="off"/>
          </div>
        </div>

        <!-- Acciones -->
        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push('/empresas')" :disabled="guardando">
            Cancelar
          </button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : 'Crear Empresa' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.page {
  padding: 2rem 2.5rem;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  max-width: 720px;
}

.breadcrumb { margin-bottom: 1.5rem; }

.btn-back {
  display: inline-flex; align-items: center; gap: 0.375rem;
  font-size: 0.875rem; font-weight: 500; color: #6B7280;
  background: none; border: none; cursor: pointer; padding: 0;
  font-family: inherit; transition: color 0.15s;
}
.btn-back:hover { color: #4F46E5; }
.btn-back svg { width: 16px; height: 16px; }

.page-title {
  font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem;
}
.page-subtitle {
  font-size: 0.875rem; color: #6B7280; margin: 0 0 1.75rem;
}

.card {
  background: #fff; border: 1px solid #E5E7EB;
  border-radius: 14px; padding: 1.75rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.alert-error {
  background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626;
  padding: 0.75rem 1rem; border-radius: 10px;
  font-size: 0.875rem; margin-bottom: 1.5rem;
}

.form { display: flex; flex-direction: column; gap: 1rem; }

.section-title {
  font-size: 0.8125rem; font-weight: 700; color: #6B7280;
  text-transform: uppercase; letter-spacing: 0.05em;
  margin: 0.75rem 0 0; padding-bottom: 0.5rem;
  border-bottom: 1px solid #F3F4F6;
}

.form-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
}

.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.form-group--small { max-width: 220px; }

.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.required { color: #EF4444; }

.input {
  padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB;
  border-radius: 10px; font-size: 0.875rem; color: #111827;
  background: #fff; outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: inherit; width: 100%;
}
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.select { cursor: pointer; }

.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }

.form-actions {
  display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.75rem;
}

.btn-secondary {
  padding: 0.6rem 1.25rem; background: #fff;
  border: 1.5px solid #D1D5DB; border-radius: 10px;
  font-size: 0.875rem; font-weight: 600; color: #374151;
  cursor: pointer; font-family: inherit;
  transition: border-color 0.15s, color 0.15s;
}
.btn-secondary:hover { border-color: #9CA3AF; color: #111827; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600;
  border: none; border-radius: 10px; cursor: pointer;
  transition: opacity 0.2s; font-family: inherit;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner-inline {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
