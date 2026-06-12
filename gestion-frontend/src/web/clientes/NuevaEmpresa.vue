<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { validarTelefono, validarNombre, validarRut, validarEmail } from '../../utils/validators.js'
import InputTelefono from '../../components/InputTelefono.vue'
import { COMUNAS_POR_REGION } from '../../utils/comunasChile.js'
import { useModeracion } from '../../composables/useModeracion.js'
import AvisoModeracion from '../../components/AvisoModeracion.vue'

const router = useRouter()
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()
const guardando = ref(false)
const error = ref('')
const errores = ref({})
const planes = ref([])

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
  plan_id:  null,
  email:    '',
  telefono: '',
  direccion: '',
  comuna:   '',
  ciudad:   '',
  region:   '',
  pais:     'Chile',
})

watch([() => form.value.nombre, () => form.value.direccion], () => {
  if (avisoMod.value) limpiarMod()
})

const comunasDisponibles = computed(() => COMUNAS_POR_REGION[form.value.region] || [])

watch(() => form.value.region, () => {
  form.value.comuna = ''
  form.value.ciudad = ''
})

function onComunaChange() {
  if (form.value.comuna) form.value.ciudad = form.value.comuna
}

const aplicarFormatoRut = (val) => {
  if (!val) return ''
  val = val.replace(/[^0-9kK]/g, '').toUpperCase().slice(0, 9)
  if (val.length <= 1) return val
  const dv     = val.slice(-1)
  let cuerpo   = val.slice(0, -1)
  cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${dv}`
}

// Verificación de RUT duplicado contra la BD (ambas tablas)
const rutVerificando = ref(false)
let _debounceRut = null

async function verificarRut() {
  const r = validarRut(form.value.rut)
  if (!r.valido) return
  rutVerificando.value = true
  try {
    const res = await apiFetch(`/api/verificar-rut/?rut=${encodeURIComponent(form.value.rut)}&tipo=empresa`)
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

const formatRut = (e) => {
  const v = aplicarFormatoRut(e.target.value)
  form.value.rut = v
  e.target.value = v
  if (errores.value.rut) errores.value = { ...errores.value, rut: undefined }
  clearTimeout(_debounceRut)
  _debounceRut = setTimeout(verificarRut, 600)
}

onMounted(async () => {
  const res = await apiFetch('/api/configuracion/planes/')
  if (res.ok) planes.value = await res.json()
})

const guardar = async () => {
  error.value   = ''
  errores.value = {}

  const nombreResult = validarNombre(form.value.nombre, 2, 30)
  if (!nombreResult.valido) {
    errores.value = { nombre: [nombreResult.error] }
    return
  }

  // Validar email si se ingresó
  if (form.value.email) {
    const emailResult = validarEmail(form.value.email)
    if (!emailResult.valido) {
      errores.value = { email: [emailResult.error] }
      return
    }
  }

  // Validar teléfono si se ingresó
  if (form.value.telefono) {
    const telResult = validarTelefono(form.value.telefono)
    if (!telResult.valido) {
      errores.value = { telefono: [telResult.error] }
      return
    }
  }

  // Verificación final del RUT contra la BD antes de crear
  clearTimeout(_debounceRut)
  if (form.value.rut) {
    await verificarRut()
    if (errores.value.rut) return
  }

  const textoMod = [form.value.nombre, form.value.direccion].filter(Boolean).join(' ')
  if (textoMod.trim()) {
    const okMod = await moderar(textoMod)
    if (!okMod) return
  }

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
              placeholder="Ej: Transportes del Norte S.A." required autocomplete="off" maxlength="30"/>
            <p v-if="errores.nombre" class="field-error">{{ errores.nombre[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label" for="rut">RUT <span class="required">*</span></label>
            <div style="position:relative">
              <input id="rut" :value="form.rut" @input="formatRut" type="text" class="input"
                :class="{ 'input-error': errores.rut }"
                placeholder="Ej: 76.123.456-7" required autocomplete="off" maxlength="12"/>
              <span v-if="rutVerificando" class="rut-spinner"/>
            </div>
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

        <!-- ── Suscripción ── -->
        <h2 class="section-title">Suscripción</h2>

        <div class="form-group form-group--small">
          <label class="label" for="plan_id">Plan</label>
          <select id="plan_id" v-model="form.plan_id" class="input select">
            <option :value="null">Sin plan</option>
            <option v-for="p in planes" :key="p.id" :value="p.id">
              {{ p.nombre_display }} — {{ p.precio_display || 'A convenir' }}
            </option>
          </select>
        </div>

        <!-- ── Contacto ── -->
        <h2 class="section-title">Contacto</h2>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="email">Email de contacto</label>
            <input id="email" v-model="form.email" type="email" class="input"
              :class="{ 'input-error': errores.email }"
              placeholder="contacto@empresa.cl" autocomplete="off" maxlength="50"/>
            <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label" for="telefono">Teléfono</label>
            <InputTelefono v-model="form.telefono" :error="!!errores.telefono" />
            <p v-if="errores.telefono" class="field-error">{{ errores.telefono[0] }}</p>
          </div>
        </div>

        <!-- ── Ubicación ── -->
        <h2 class="section-title">Ubicación</h2>

        <div class="form-group">
          <label class="label" for="direccion">Dirección</label>
          <input id="direccion" v-model="form.direccion" type="text" class="input"
            placeholder="Av. Providencia 1234, Of. 5" autocomplete="off" maxlength="40"/>
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
              placeholder="Chile" autocomplete="off" maxlength="100"/>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label" for="ciudad">Ciudad</label>
            <select id="ciudad" v-model="form.ciudad" class="input select"
              :disabled="!form.region">
              <option value="">{{ form.region ? '— Selecciona ciudad —' : '— Elige región primero —' }}</option>
              <option v-for="c in comunasDisponibles" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>

          <div class="form-group">
            <label class="label" for="comuna">Comuna</label>
            <select id="comuna" v-model="form.comuna" class="input select"
              :disabled="!form.region" @change="onComunaChange">
              <option value="">{{ form.region ? '— Selecciona comuna —' : '— Elige región primero —' }}</option>
              <option v-for="c in comunasDisponibles" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </div>

        <!-- Acciones -->
        <AvisoModeracion :aviso="avisoMod" :sugerencia="sugerenciaMod" />
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

.rut-spinner {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  width: 16px; height: 16px;
  border: 2px solid #D1D5DB; border-top-color: #7C3AED;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-header { flex-direction: column; gap: 0.625rem; }
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
