<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { validarTelefono, validarNombre, validarEmail } from '../../utils/validators.js'
import InputTelefono from '../../components/InputTelefono.vue'

const router = useRouter()
const route  = useRoute()
const id     = route.params.id

const cargando  = ref(true)
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})
const fechaRegistro  = ref('')
const planes         = ref([])
const planOriginalId = ref(null)
const usageData      = ref({ vehiculos: 0, conductores: 0, usuarios: 0 })

function clp(val) {
  if (val == null) return '—'
  const abs = Math.abs(Math.round(val))
  const fmt = '$' + abs.toLocaleString('es-CL')
  return val > 0 ? '+' + fmt : val < 0 ? '-' + fmt : fmt
}

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

const aplicarFormatoRut = (val) => {
  if (!val) return ''
  val = val.replace(/[^0-9kK]/g, '').toUpperCase().slice(0, 9)
  if (val.length <= 1) return val
  const dv   = val.slice(-1)
  let cuerpo = val.slice(0, -1)
  cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${dv}`
}

const formatRut = (e) => {
  const v = aplicarFormatoRut(e.target.value)
  form.value.rut = v
  e.target.value = v
}

const cargarEmpresa = async () => {
  try {
    const res = await apiFetch(`/api/empresas/${id}/`)
    if (!res.ok) throw new Error('Empresa no encontrada')
    const raw  = await res.json()
    const data = raw.informacion || raw
    form.value.nombre    = data.nombre    || ''
    form.value.rut       = aplicarFormatoRut(data.rut || '')
    form.value.estado    = data.estado    || 'activa'
    form.value.email     = data.email     || ''
    form.value.telefono  = data.telefono  || ''
    form.value.direccion = data.direccion || ''
    form.value.comuna    = data.comuna    || ''
    form.value.ciudad    = data.ciudad    || ''
    form.value.region    = data.region    || ''
    form.value.pais      = data.pais      || 'Chile'
    form.value.plan_id   = data.plan_id   || null
    planOriginalId.value = data.plan_id   || null
    usageData.value = {
      vehiculos:   data.cantidad_vehiculos   || 0,
      conductores: data.cantidad_conductores || 0,
      usuarios:    data.cantidad_usuarios    || (data.usuarios?.length ?? 0),
    }
    if (data.created_at) {
      fechaRegistro.value = new Date(data.created_at).toLocaleDateString('es-CL', {
        year: 'numeric', month: 'long', day: 'numeric'
      })
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

const guardar = async () => {
  error.value   = ''
  errores.value = {}

  const nombreR = validarNombre(form.value.nombre, 2, 30)
  if (!nombreR.valido) { errores.value = { nombre: [nombreR.error] }; return }

  if (form.value.email) {
    const emailR = validarEmail(form.value.email)
    if (!emailR.valido) { errores.value = { email: [emailR.error] }; return }
  }

  if (form.value.telefono) {
    const telR = validarTelefono(form.value.telefono)
    if (!telR.valido) { errores.value = { telefono: [telR.error] }; return }
  }

  guardando.value = true

  try {
    const { rut: _rut, ...body } = form.value
    const res  = await apiFetch(`/api/empresas/${id}/`, { method: 'PUT', body })
    const data = await res.json()

    if (!res.ok) {
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al actualizar la empresa'
      return
    }

    router.push('/empresas')
  } catch {
    error.value = 'Error de conexión con el servidor'
  } finally {
    guardando.value = false
  }
}

// ── Comparación en tiempo real al cambiar el plan ───────────────────────────
const planOriginalObj = computed(() => planes.value.find(p => p.id === planOriginalId.value) || null)
const planNuevoObj    = computed(() => planes.value.find(p => p.id === form.value.plan_id)  || null)

const comparacionPlan = computed(() => {
  if (!planes.value.length) return null
  if (form.value.plan_id === planOriginalId.value) return null   // sin cambio

  if (!form.value.plan_id) {
    return { tipo: 'quitar', advertencias: [], planAntes: planOriginalObj.value, planDespues: null }
  }
  if (!planOriginalId.value) {
    return { tipo: 'nuevo', advertencias: [], planAntes: null, planDespues: planNuevoObj.value }
  }
  if (!planOriginalObj.value || !planNuevoObj.value) return null

  const pAnt = planOriginalObj.value.precio_mensual || 0
  const pNvo = planNuevoObj.value.precio_mensual    || 0
  const tipo = pNvo > pAnt ? 'upgrade' : pNvo < pAnt ? 'downgrade' : 'lateral'

  const advertencias = []
  const uso = usageData.value
  const np  = planNuevoObj.value
  if (uso.vehiculos   > np.max_vehiculos)    advertencias.push(`Vehículos: tienes ${uso.vehiculos} (nuevo límite: ${np.max_vehiculos})`)
  if (uso.conductores > np.max_conductores)  advertencias.push(`Conductores: tienes ${uso.conductores} (nuevo límite: ${np.max_conductores})`)
  if (uso.usuarios    > np.max_usuarios)     advertencias.push(`Usuarios: tienes ${uso.usuarios} (nuevo límite: ${np.max_usuarios})`)

  return { tipo, advertencias, planAntes: planOriginalObj.value, planDespues: planNuevoObj.value }
})

onMounted(async () => {
  const [, planesRes] = await Promise.all([
    cargarEmpresa(),
    apiFetch('/api/configuracion/planes/'),
  ])
  if (planesRes.ok) planes.value = await planesRes.json()
})
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
      <div>
        <h1 class="page-title">Editar Empresa</h1>
        <p class="page-subtitle">
          Modifica los datos de la empresa
          <span v-if="fechaRegistro" class="fecha-registro">— Registrada el {{ fechaRegistro }}</span>
        </p>
      </div>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/>
      <span>Cargando datos...</span>
    </div>

    <div v-else class="card">
      <div v-if="error && !form.nombre" class="alert-error">{{ error }}</div>

      <form @submit.prevent="guardar" class="form">
        <div v-if="error && form.nombre" class="alert-error">{{ error }}</div>

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
            <label class="label" for="rut">RUT</label>
            <div class="input-readonly">
              <svg class="lock-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
              </svg>
              <span>{{ form.rut }}</span>
            </div>
            <p class="field-hint">El RUT no puede modificarse una vez registrado</p>
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

        <!-- ── Card comparación de plan ── -->
        <div v-if="comparacionPlan" class="plan-cambio" :class="'plan-cambio--' + comparacionPlan.tipo">
          <div class="pc-header">
            <span class="pc-icono">
              {{ comparacionPlan.tipo === 'upgrade'   ? '⬆️' :
                 comparacionPlan.tipo === 'downgrade' ? '⬇️' :
                 comparacionPlan.tipo === 'quitar'    ? '⚠️' : '✅' }}
            </span>
            <strong class="pc-titulo">
              {{ comparacionPlan.tipo === 'upgrade'   ? 'Cambio a plan superior'   :
                 comparacionPlan.tipo === 'downgrade' ? 'Cambio a plan inferior'   :
                 comparacionPlan.tipo === 'lateral'   ? 'Cambio de plan'           :
                 comparacionPlan.tipo === 'nuevo'     ? 'Asignando primer plan'    :
                                                       'Quitando plan asignado'    }}
            </strong>
          </div>

          <div class="pc-planes">
            <span class="pc-chip pc-chip--antes">{{ comparacionPlan.planAntes?.nombre_display || 'Sin plan' }}</span>
            <span class="pc-arrow">→</span>
            <span class="pc-chip pc-chip--despues">{{ comparacionPlan.planDespues?.nombre_display || 'Sin plan' }}</span>
            <span v-if="comparacionPlan.planAntes?.precio_mensual && comparacionPlan.planDespues?.precio_mensual"
                  class="pc-diff"
                  :class="comparacionPlan.tipo === 'upgrade' ? 'pc-diff--sube' : 'pc-diff--baja'">
              {{ clp(comparacionPlan.planDespues.precio_mensual - comparacionPlan.planAntes.precio_mensual) }}/mes
            </span>
          </div>

          <p class="pc-info">
            {{ comparacionPlan.tipo === 'upgrade'
                ? 'Nuevos límites y módulos disponibles de inmediato. El próximo cobro será al precio del nuevo plan.'
                : comparacionPlan.tipo === 'downgrade'
                ? 'Los límites se reducen de inmediato. El próximo cobro será al precio menor.'
                : comparacionPlan.tipo === 'nuevo'
                ? 'La empresa deberá pagar para activar el acceso al sistema.'
                : comparacionPlan.tipo === 'quitar'
                ? 'La empresa quedará sin plan y no podrá acceder al sistema.'
                : 'El plan se actualizará de inmediato.' }}
          </p>

          <div v-if="comparacionPlan.advertencias.length" class="pc-advertencias">
            <p class="pc-adv-titulo">⚠️ Uso actual supera el límite del nuevo plan:</p>
            <ul class="pc-adv-lista">
              <li v-for="adv in comparacionPlan.advertencias" :key="adv">{{ adv }}</li>
            </ul>
            <p class="pc-adv-nota">Los recursos existentes no se eliminarán, pero la empresa no podrá crear nuevos hasta reducir su uso.</p>
          </div>
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
              placeholder="Chile" autocomplete="off" maxlength="100"/>
          </div>
        </div>

        <!-- Acciones -->
        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push('/empresas')" :disabled="guardando">
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
.fecha-registro { color: #9CA3AF; }

.loading {
  display: flex; align-items: center; gap: 0.75rem;
  color: #6B7280; font-size: 0.875rem; padding: 2rem 0;
}
.spinner {
  width: 22px; height: 22px;
  border: 2.5px solid #E5E7EB; border-top-color: #7C3AED;
  border-radius: 50%; animation: spin 0.7s linear infinite;
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

.input-readonly {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.65rem 0.875rem; border: 1.5px solid #E5E7EB;
  border-radius: 10px; font-size: 0.875rem; color: #6B7280;
  background: #F9FAFB; font-family: 'Courier New', monospace;
  user-select: none;
}
.lock-icon { width: 14px; height: 14px; flex-shrink: 0; color: #9CA3AF; }
.field-hint { font-size: 0.75rem; color: #9CA3AF; margin: 0; }

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

/* ── Card comparación de plan ── */
.plan-cambio {
  border-radius: 10px; padding: 0.875rem 1rem;
  display: flex; flex-direction: column; gap: 0.5rem;
  border: 1.5px solid;
}
.plan-cambio--upgrade  { background: #F0FDF4; border-color: #86EFAC; }
.plan-cambio--downgrade { background: #FFFBEB; border-color: #FDE68A; }
.plan-cambio--lateral  { background: #EFF6FF; border-color: #BFDBFE; }
.plan-cambio--nuevo    { background: #EFF6FF; border-color: #BFDBFE; }
.plan-cambio--quitar   { background: #FEF2F2; border-color: #FECACA; }

.pc-header { display: flex; align-items: center; gap: 0.5rem; }
.pc-icono  { font-size: 1.05rem; line-height: 1; }
.pc-titulo { font-size: 0.8125rem; font-weight: 700; color: #111827; }

.pc-planes {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
}
.pc-chip {
  padding: 0.2rem 0.6rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 600;
}
.pc-chip--antes   { background: #E5E7EB; color: #374151; }
.pc-chip--despues { background: #4F46E5; color: #fff; }
.pc-arrow { color: #6B7280; font-size: 0.875rem; }
.pc-diff  { font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 999px; }
.pc-diff--sube { background: #D1FAE5; color: #065F46; }
.pc-diff--baja { background: #FEF3C7; color: #92400E; }

.pc-info { font-size: 0.8rem; color: #374151; margin: 0; line-height: 1.45; }

.pc-advertencias {
  background: rgba(0,0,0,0.04); border-radius: 8px;
  padding: 0.625rem 0.75rem; display: flex; flex-direction: column; gap: 0.35rem;
}
.pc-adv-titulo { font-size: 0.775rem; font-weight: 700; color: #92400E; margin: 0; }
.pc-adv-lista  { margin: 0; padding-left: 1.25rem; }
.pc-adv-lista li { font-size: 0.775rem; color: #374151; line-height: 1.5; }
.pc-adv-nota   { font-size: 0.725rem; color: #6B7280; margin: 0; font-style: italic; }

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
