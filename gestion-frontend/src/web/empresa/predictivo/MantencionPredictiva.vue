<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva } from '../../../utils/empresaActiva.js'
import { useToast } from '../../../utils/useToast.js'

const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = useToast()

const usuario      = JSON.parse(localStorage.getItem('usuario') || '{}')
const esSuperadmin = usuario.rol === 'SUPERADMIN'

// ── Selector de empresa (SUPERADMIN) ─────────────────────────────────────────
const empresas          = ref([])
const empresaActiva     = ref(getEmpresaActiva())
const mostrarDropdown   = ref(false)
const busqueda          = ref('')
const cargandoEmpresas  = ref(false)
const sinEmpresa        = computed(() => esSuperadmin && !empresaActiva.value)

const empresasFiltradas = computed(() => {
  if (!busqueda.value.trim()) return empresas.value
  const q = busqueda.value.toLowerCase()
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  cargarTodo()
}

const limpiarEmpresa = () => {
  setEmpresaActiva(null)
  empresaActiva.value   = null
  mostrarDropdown.value = false
  alertas.value = []
  planes.value  = []
}

const tabs = [
  { id: 'alertas',   name: 'Alertas'    },
  { id: 'planes',    name: 'Planes'     },
  { id: 'simulador', name: 'Simulador'  },
]
const currentTab = ref('alertas')

// ── Alertas ──────────────────────────────────────────────────────────────────
const alertas            = ref([])
const alertasFiltroNivel  = ref('')
const alertasFiltroEstado = ref('pendiente')
const cargandoAlertas    = ref(false)

const fetchAlertas = async () => {
  cargandoAlertas.value = true
  try {
    let url = '/api/empresa/alertas-mantenimiento/?'
    if (alertasFiltroNivel.value)  url += `nivel=${alertasFiltroNivel.value}&`
    if (alertasFiltroEstado.value) url += `estado=${alertasFiltroEstado.value}&`
    const res = await apiFetchEmpresa(url)
    if (res.ok) alertas.value = await res.json()
  } catch { /* silencioso */ }
  finally { cargandoAlertas.value = false }
}

// ── Modal atender alerta ──────────────────────────────────────────────────────
const modalAtenderOpen  = ref(false)
const alertaActual      = ref(null)
const fechaRealizada    = ref('')
const guardandoAtencion = ref(false)

const openAtenderModal = (alerta) => {
  alertaActual.value   = alerta
  fechaRealizada.value = new Date().toISOString().slice(0, 10)
  modalAtenderOpen.value = true
}

const atenderAlerta = async () => {
  guardandoAtencion.value = true
  try {
    const res = await apiFetchEmpresa(
      `/api/empresa/alertas-mantenimiento/${alertaActual.value.id}/atender/`,
      { method: 'POST', body: { fecha_realizada: fechaRealizada.value, costo: alertaActual.value.costo_estimado ?? 0 } }
    )
    if (res.ok) {
      toast.success('Alerta atendida y mantención registrada')
      modalAtenderOpen.value = false
      fetchAlertas()
    } else {
      const data = await res.json()
      toast.error(data.error || 'Error al registrar la atención')
    }
  } catch { toast.error('Error de conexión') }
  finally { guardandoAtencion.value = false }
}

// ── Planes ────────────────────────────────────────────────────────────────────
const planes          = ref([])
const cargandoPlanes  = ref(false)
const mostrarFormPlan = ref(false)
const planAEliminar   = ref(null)

const fetchPlanes = async () => {
  cargandoPlanes.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/planes-mantenimiento/')
    if (res.ok) planes.value = await res.json()
  } catch { /* silencioso */ }
  finally { cargandoPlanes.value = false }
}

const confirmarEliminar = (plan) => { planAEliminar.value = plan.id }

const eliminarPlan = async (plan) => {
  planAEliminar.value = null
  try {
    const res = await apiFetchEmpresa(`/api/empresa/planes-mantenimiento/${plan.id}/`, { method: 'DELETE' })
    if (res.ok) {
      toast.success(`Plan "${plan.nombre}" eliminado`)
      fetchPlanes()
    } else {
      toast.error('Error al eliminar el plan')
    }
  } catch { toast.error('Error de conexión') }
}

// ── Nuevo Plan ────────────────────────────────────────────────────────────────
const guardando = ref(false)

function defaultRegla() {
  return {
    tipo: '', intervalo_dias: 90, umbral_alerta_dias: 15,
    prioridad: 'media', costo_estimado: 0,
    escalar_sin_respuesta: false, bloquear_despacho: false, canal: 'email',
  }
}

const nuevoPlan = ref({ nombre: '', activo: true, reglas: [defaultRegla()] })

const agregarRegla = () => nuevoPlan.value.reglas.push(defaultRegla())

const resetFormPlan = () => {
  nuevoPlan.value = { nombre: '', activo: true, reglas: [defaultRegla()] }
  mostrarFormPlan.value = false
}

const guardarPlan = async () => {
  guardando.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/planes-mantenimiento/', {
      method: 'POST', body: nuevoPlan.value,
    })
    if (res.ok) {
      toast.success('Plan de mantenimiento creado exitosamente')
      resetFormPlan()
      fetchPlanes()
    } else {
      const data = await res.json()
      toast.error(data.error || data.nombre?.[0] || 'Error al guardar el plan')
    }
  } catch { toast.error('Error de conexión') }
  finally { guardando.value = false }
}

const formatIntervalo = (dias) => {
  if (!dias) return ''
  if (dias >= 365) return `≈ ${Math.round(dias / 365 * 10) / 10} años`
  if (dias >= 30)  return `≈ ${Math.round(dias / 30  * 10) / 10} meses`
  return `${dias} días`
}

// ── Simulador ─────────────────────────────────────────────────────────────────
const vehiculos           = ref([])
const simuladorVehiculoId = ref('')
const simuladorMeses      = ref(3)
const simulando           = ref(false)
const simulacionResultados = ref(null)

const fetchVehiculos = async () => {
  try {
    const res = await apiFetchEmpresa('/api/empresa/vehiculos/')
    if (res.ok) vehiculos.value = await res.json()
  } catch { /* silencioso */ }
}

const ejecutarSimulacion = async () => {
  simulando.value = true
  simulacionResultados.value = null
  try {
    const res = await apiFetchEmpresa(
      `/api/empresa/simulador-vencimientos/?vehiculo_id=${simuladorVehiculoId.value}&meses=${simuladorMeses.value}`
    )
    if (res.ok) {
      simulacionResultados.value = await res.json()
    } else {
      toast.error('Error al ejecutar la simulación')
    }
  } catch { toast.error('Error de conexión') }
  finally { simulando.value = false }
}

const formatFecha = (fechaStr) => {
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

const cargarTodo = () => {
  if (sinEmpresa.value) return
  fetchAlertas()
  fetchPlanes()
  fetchVehiculos()
}

onMounted(async () => {
  if (esSuperadmin) {
    cargandoEmpresas.value = true
    try {
      const res = await apiFetch('/api/empresas/')
      if (res.ok) empresas.value = (await res.json()).filter(e => e.estado === 'activa')
    } finally { cargandoEmpresas.value = false }
  }
  cargarTodo()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenimiento Predictivo</h1>
        <p class="page-subtitle">Alertas y planes de mantenimiento preventivo</p>
      </div>
      <div class="header-actions">

    <!-- Selector de empresa (SUPERADMIN) -->
    <div v-if="esSuperadmin" class="selector-wrap">
      <button class="selector-btn" :class="{ 'sin-sel': !empresaActiva }" @click="mostrarDropdown = !mostrarDropdown">
        <span class="selector-icono">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
        </span>
        <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
        <svg class="selector-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>
      <div v-if="mostrarDropdown" class="selector-dropdown">
        <div class="dropdown-search">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
          </svg>
          <input v-model="busqueda" placeholder="Buscar empresa..." class="dropdown-input" autofocus/>
        </div>
        <button v-if="empresaActiva" class="dropdown-option dropdown-todos" @click="limpiarEmpresa">
          <span class="option-nombre">— Quitar selección</span>
        </button>
        <div v-if="cargandoEmpresas" class="dropdown-empty">Cargando...</div>
        <div v-else-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</div>
        <button
          v-for="emp in empresasFiltradas" :key="emp.id"
          class="dropdown-option" :class="{ selected: empresaActiva?.id === emp.id }"
          @click="seleccionarEmpresa(emp)"
        >
          <span class="option-nombre">{{ emp.nombre }}</span>
          <svg v-if="empresaActiva?.id === emp.id" class="option-check" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
        </button>
      </div>
      <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
    </div>

      </div><!-- /header-actions -->
    </div><!-- /page-header -->

    <!-- Tabs -->
    <div v-if="!sinEmpresa" class="tabs-bar">
      <button
        v-for="tab in tabs" :key="tab.id"
        class="tab-btn" :class="{ active: currentTab === tab.id }"
        @click="currentTab = tab.id"
      >{{ tab.name }}</button>
    </div>

    <!-- ═══ TAB ALERTAS ═══════════════════════════════════════════════════════ -->
    <div v-if="!sinEmpresa && currentTab === 'alertas'">
      <div class="list-header">
        <h2 class="section-title">Alertas de Mantenimiento</h2>
        <div class="filters">
          <select v-model="alertasFiltroNivel" @change="fetchAlertas" class="input select">
            <option value="">Todos los niveles</option>
            <option value="por_vencer">Por Vencer</option>
            <option value="vencida">Vencida</option>
          </select>
          <select v-model="alertasFiltroEstado" @change="fetchAlertas" class="input select">
            <option value="pendiente">Pendientes</option>
            <option value="atendida">Atendidas</option>
          </select>
        </div>
      </div>

      <div v-if="cargandoAlertas" class="loading">
        <div class="spinner"/> Cargando alertas...
      </div>
      <div v-else class="card list-card">
        <div v-for="alerta in alertas" :key="alerta.id" class="alert-row">
          <div class="alert-main">
            <div class="alert-top">
              <span class="patente-tag">{{ alerta.vehiculo_patente }}</span>
              <span class="tipo-text">{{ alerta.tipo_mantencion }}</span>
              <span class="nivel-badge" :class="alerta.nivel === 'vencida' ? 'nivel-vencida' : 'nivel-por-vencer'">
                {{ alerta.nivel === 'vencida' ? 'Vencida' : 'Por Vencer' }}
              </span>
            </div>
            <div class="alert-meta">
              <span v-if="alerta.dias_restantes <= 0" class="dias-vencida">
                Vencida hace {{ Math.abs(alerta.dias_restantes) }} días
              </span>
              <span v-else class="dias-por-vencer">
                Vence en {{ alerta.dias_restantes }} días
              </span>
              <span class="pct-text">Avance: {{ alerta.pct_avance }}%</span>
            </div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :class="alerta.nivel === 'vencida' ? 'fill-red' : 'fill-yellow'"
                :style="{ width: Math.min(alerta.pct_avance, 100) + '%' }"
              />
            </div>
          </div>
          <div v-if="!alerta.atendida" class="alert-actions">
            <button
              class="btn-outline-sm"
              @click="router.push({ path: ruta('/mantenciones/nueva'), query: { vehiculo: alerta.vehiculo_id, tipo: alerta.tipo_mantencion, presupuesto: alerta.costo_estimado || '' } })"
            >Programar</button>
            <button class="btn-primary-sm" @click="openAtenderModal(alerta)">Registrar</button>
          </div>
        </div>
        <div v-if="alertas.length === 0" class="empty-msg">No hay alertas para mostrar.</div>
      </div>
    </div>

    <!-- ═══ TAB PLANES ════════════════════════════════════════════════════════ -->
    <div v-if="!sinEmpresa && currentTab === 'planes'">
      <div class="list-header">
        <h2 class="section-title">Planes de Mantenimiento</h2>
        <button class="btn-primary" @click="mostrarFormPlan = !mostrarFormPlan">
          {{ mostrarFormPlan ? '— Cancelar' : '+ Nuevo Plan' }}
        </button>
      </div>

      <!-- Formulario inline nuevo plan -->
      <Transition name="slide-down">
        <div v-if="mostrarFormPlan" class="card form-card">
          <h3 class="form-card-title">Crear Plan de Mantenimiento</h3>
          <form @submit.prevent="guardarPlan" class="form">
            <div class="form-group" style="max-width: 400px;">
              <label class="label">Nombre del Plan</label>
              <input v-model="nuevoPlan.nombre" type="text" class="input" placeholder="Ej: Plan semestral" required/>
            </div>

            <div class="reglas-header">
              <span class="label">Reglas del plan</span>
              <button type="button" class="btn-link" @click="agregarRegla">+ Agregar regla</button>
            </div>

            <div v-for="(regla, idx) in nuevoPlan.reglas" :key="idx" class="regla-card">
              <button
                v-if="nuevoPlan.reglas.length > 1"
                type="button" class="regla-remove"
                @click="nuevoPlan.reglas.splice(idx, 1)"
              >&times;</button>
              <div class="regla-grid">
                <div class="form-group">
                  <label class="label-xs">Tipo Mantención</label>
                  <select v-model="regla.tipo" required class="input select">
                    <option value="">— Seleccionar —</option>
                    <option value="aceite">Cambio de aceite</option>
                    <option value="frenos">Revisión de frenos</option>
                    <option value="neumaticos">Cambio de neumáticos</option>
                    <option value="filtro_aire">Filtro de aire</option>
                    <option value="filtro_combustible">Filtro de combustible</option>
                    <option value="rtv">Revisión técnica (RTV)</option>
                    <option value="electrica">Revisión eléctrica</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="label-xs">Intervalo (días)</label>
                  <input type="number" v-model.number="regla.intervalo_dias" required min="1" class="input"/>
                  <p class="hint">{{ formatIntervalo(regla.intervalo_dias) }}</p>
                </div>
                <div class="form-group">
                  <label class="label-xs">Umbral alerta (días antes)</label>
                  <input type="number" v-model.number="regla.umbral_alerta_dias" required min="1" class="input"/>
                </div>
                <div class="form-group">
                  <label class="label-xs">Prioridad</label>
                  <select v-model="regla.prioridad" class="input select">
                    <option value="baja">Baja</option>
                    <option value="media">Media</option>
                    <option value="alta">Alta</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="label-xs">Costo Est. ($)</label>
                  <input type="number" v-model.number="regla.costo_estimado" min="0" class="input"/>
                </div>
                <div class="form-group regla-checks">
                  <label class="check-label">
                    <input type="checkbox" v-model="regla.escalar_sin_respuesta" class="check"/>
                    Escalar si no se atiende (48h)
                  </label>
                  <label class="check-label">
                    <input type="checkbox" v-model="regla.bloquear_despacho" class="check"/>
                    Bloquear vehículo si vence
                  </label>
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="btn-secondary" @click="resetFormPlan">Cancelar</button>
              <button type="submit" class="btn-primary" :disabled="guardando">
                <span v-if="guardando" class="spinner-inline"/>
                {{ guardando ? 'Guardando...' : 'Guardar Plan' }}
              </button>
            </div>
          </form>
        </div>
      </Transition>

      <div v-if="cargandoPlanes" class="loading">
        <div class="spinner"/> Cargando planes...
      </div>
      <div v-else class="planes-grid">
        <div v-for="plan in planes" :key="plan.id" class="plan-card card">
          <div class="plan-header">
            <h3 class="plan-nombre">{{ plan.nombre }}</h3>
            <span class="plan-estado" :class="plan.activo ? 'estado-activo' : 'estado-inactivo'">
              {{ plan.activo ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <p class="plan-desc">{{ plan.descripcion || 'Sin descripción' }}</p>
          <div class="plan-reglas">
            <span class="reglas-titulo">{{ plan.reglas.length }} regla{{ plan.reglas.length !== 1 ? 's' : '' }}</span>
            <ul class="reglas-lista">
              <li v-for="r in plan.reglas" :key="r.id">
                <span class="regla-tipo-tag">{{ r.tipo }}</span>
                cada {{ r.intervalo_dias }} días · alerta {{ r.umbral_alerta_dias }} días antes
              </li>
            </ul>
          </div>
          <div class="plan-footer">
            <div v-if="planAEliminar === plan.id" class="confirm-delete">
              <span class="confirm-text">¿Confirmar eliminación?</span>
              <button class="btn-danger-sm" @click="eliminarPlan(plan)">Sí, eliminar</button>
              <button class="btn-outline-sm" @click="planAEliminar = null">Cancelar</button>
            </div>
            <button v-else class="btn-danger-sm" @click="confirmarEliminar(plan)">Eliminar</button>
          </div>
        </div>
        <div v-if="planes.length === 0 && !mostrarFormPlan" class="empty-card card">
          No hay planes de mantenimiento creados.
        </div>
      </div>
    </div>

    <!-- ═══ TAB SIMULADOR ════════════════════════════════════════════════════ -->
    <div v-if="!sinEmpresa && currentTab === 'simulador'">
      <div class="card sim-filtros">
        <div class="form-row-3">
          <div class="form-group">
            <label class="label">Vehículo</label>
            <select v-model="simuladorVehiculoId" class="input select">
              <option value="">— Seleccionar vehículo —</option>
              <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} — {{ v.marca }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="label">Período</label>
            <select v-model="simuladorMeses" class="input select">
              <option :value="3">3 Meses</option>
              <option :value="6">6 Meses</option>
              <option :value="12">12 Meses</option>
            </select>
          </div>
          <div class="form-group">
            <label class="label">&nbsp;</label>
            <button
              class="btn-primary"
              @click="ejecutarSimulacion"
              :disabled="!simuladorVehiculoId || simulando"
            >
              <span v-if="simulando" class="spinner-inline"/>
              {{ simulando ? 'Calculando...' : 'Proyectar' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="simulacionResultados" class="card">
        <div class="sim-resumen">
          <h3 class="section-title">Proyección de Eventos</h3>
          <div class="sim-stats">
            <span class="stat-item">Total: <strong>{{ simulacionResultados.total_eventos }}</strong></span>
            <span class="stat-sep">·</span>
            <span class="stat-item">Presupuesto estimado: <strong>${{ simulacionResultados.presupuesto_total.toLocaleString() }}</strong></span>
          </div>
        </div>
        <div class="sim-lista">
          <div v-for="(evento, idx) in simulacionResultados.eventos" :key="idx" class="sim-evento">
            <span class="sim-tipo">{{ evento.tipo }}</span>
            <span class="sim-fecha">{{ formatFecha(evento.fecha) }}</span>
            <span class="sim-costo">${{ evento.costo_estimado.toLocaleString() }}</span>
          </div>
          <div v-if="simulacionResultados.eventos.length === 0" class="empty-msg">
            No se proyectan eventos para este período.
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ MODAL ATENDER ALERTA ══════════════════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="modalAtenderOpen" class="modal-overlay" @click.self="modalAtenderOpen = false">
        <div class="modal-box">
          <h3 class="modal-title">Registrar Mantención Realizada</h3>
          <p class="modal-sub">
            Vehículo <strong>{{ alertaActual?.vehiculo_patente }}</strong>
            — {{ alertaActual?.tipo_mantencion }}
          </p>
          <div class="form modal-form">
            <div class="form-group">
              <label class="label">Fecha de Realización</label>
              <input type="date" v-model="fechaRealizada" class="input" required/>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-secondary" @click="modalAtenderOpen = false" :disabled="guardandoAtencion">
              Cancelar
            </button>
            <button class="btn-primary" @click="atenderAlerta" :disabled="guardandoAtencion">
              <span v-if="guardandoAtencion" class="spinner-inline"/>
              {{ guardandoAtencion ? 'Guardando...' : 'Confirmar' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background: #F9FAFB; min-height: 100vh; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.2rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }

/* Tabs */
.tabs-bar { display: flex; border-bottom: 2px solid #E5E7EB; margin-bottom: 1.75rem; }
.tab-btn { padding: 0.75rem 1.25rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-family: inherit; transition: color 0.15s, border-color 0.15s; white-space: nowrap; }
.tab-btn:hover { color: #374151; }
.tab-btn.active { color: #4F46E5; border-bottom-color: #4F46E5; font-weight: 600; }

/* Layout helpers */
.list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.section-title { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.filters { display: flex; gap: 0.625rem; flex-wrap: wrap; }
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.empty-msg { padding: 2.5rem; text-align: center; font-size: 0.875rem; color: #9CA3AF; }
.empty-card { padding: 2.5rem; text-align: center; font-size: 0.875rem; color: #9CA3AF; }

/* Cards */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 1rem; }
.list-card { padding: 0; overflow: hidden; }
.form-card { margin-bottom: 1.25rem; }
.form-card-title { font-size: 1rem; font-weight: 700; color: #1E1B4B; margin: 0 0 1.25rem; }

/* Alertas */
.alert-row { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; gap: 1.25rem; }
.alert-row:last-child { border-bottom: none; }
.alert-main { flex: 1; min-width: 0; }
.alert-top { display: flex; align-items: center; gap: 0.625rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.patente-tag { font-size: 0.8125rem; font-weight: 700; color: #4F46E5; background: #EEF2FF; padding: 0.2rem 0.5rem; border-radius: 6px; font-family: 'Courier New', monospace; letter-spacing: 0.04em; }
.tipo-text { font-size: 0.875rem; color: #374151; }
.nivel-badge { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 100px; }
.nivel-vencida { background: #FEE2E2; color: #B91C1C; }
.nivel-por-vencer { background: #FEF9C3; color: #92400E; }
.alert-meta { display: flex; align-items: center; gap: 1rem; font-size: 0.8125rem; margin-bottom: 0.35rem; flex-wrap: wrap; }
.dias-vencida { color: #DC2626; font-weight: 600; }
.dias-por-vencer { color: #D97706; font-weight: 600; }
.pct-text { color: #9CA3AF; }
.progress-track { height: 6px; background: #F3F4F6; border-radius: 100px; max-width: 300px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 100px; transition: width 0.3s; }
.fill-red { background: #EF4444; }
.fill-yellow { background: #F59E0B; }
.alert-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }

/* Planes */
.planes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; margin-top: 0; }
.plan-card { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 0; }
.plan-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.plan-nombre { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.plan-estado { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.625rem; border-radius: 100px; flex-shrink: 0; }
.estado-activo { background: #D1FAE5; color: #065F46; }
.estado-inactivo { background: #F3F4F6; color: #6B7280; }
.plan-desc { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.plan-reglas { background: #F9FAFB; border-radius: 10px; padding: 0.75rem 1rem; }
.reglas-titulo { font-size: 0.75rem; font-weight: 700; color: #374151; display: block; margin-bottom: 0.375rem; text-transform: uppercase; letter-spacing: 0.04em; }
.reglas-lista { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.3rem; }
.reglas-lista li { font-size: 0.8125rem; color: #4B5563; display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.regla-tipo-tag { font-weight: 600; color: #374151; }
.plan-footer { display: flex; justify-content: flex-end; align-items: center; border-top: 1px solid #F3F4F6; padding-top: 0.75rem; margin-top: auto; }
.confirm-delete { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.confirm-text { font-size: 0.8125rem; color: #374151; }

/* Form nuevo plan */
.form { display: flex; flex-direction: column; gap: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-row-3 { display: grid; grid-template-columns: 1fr 1fr auto; gap: 1rem; align-items: end; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.label-xs { font-size: 0.8rem; font-weight: 600; color: #374151; }
.opcional { font-weight: 400; color: #9CA3AF; font-size: 0.8125rem; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.select { cursor: pointer; }
.hint { font-size: 0.75rem; color: #9CA3AF; margin: 0; }
.reglas-header { display: flex; align-items: center; justify-content: space-between; }
.regla-card { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; position: relative; }
.regla-remove { position: absolute; top: 0.6rem; right: 0.75rem; background: none; border: none; font-size: 1.25rem; line-height: 1; color: #9CA3AF; cursor: pointer; padding: 0; }
.regla-remove:hover { color: #EF4444; }
.regla-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 0.75rem; align-items: start; }
.regla-checks { grid-column: 1 / -1; display: flex; gap: 1.5rem; flex-wrap: wrap; }
.check-label { display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; color: #374151; cursor: pointer; }
.check { accent-color: #7C3AED; width: 14px; height: 14px; flex-shrink: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-link { background: none; border: none; color: #7C3AED; font-size: 0.875rem; font-weight: 600; cursor: pointer; padding: 0; font-family: inherit; }
.btn-link:hover { color: #4F46E5; }

/* Simulador */
.sim-filtros { margin-bottom: 1rem; }
.sim-resumen { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.sim-stats { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.stat-item { font-size: 0.875rem; color: #6B7280; }
.stat-item strong { color: #111827; }
.stat-sep { color: #D1D5DB; }
.sim-lista { display: flex; flex-direction: column; }
.sim-evento { display: flex; align-items: center; gap: 1rem; padding: 0.875rem 0; border-bottom: 1px solid #F3F4F6; }
.sim-evento:last-child { border-bottom: none; }
.sim-tipo { flex: 1; font-size: 0.875rem; font-weight: 600; color: #4F46E5; }
.sim-fecha { font-size: 0.875rem; color: #374151; background: #F3F4F6; padding: 0.2rem 0.625rem; border-radius: 6px; }
.sim-costo { font-size: 0.875rem; color: #059669; font-weight: 600; min-width: 100px; text-align: right; }

/* Botones */
.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; transition: opacity 0.2s; white-space: nowrap; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; transition: border-color 0.15s; }
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-primary-sm { padding: 0.35rem 0.875rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.8125rem; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; font-family: inherit; white-space: nowrap; }
.btn-primary-sm:hover { opacity: 0.9; }
.btn-outline-sm { padding: 0.35rem 0.875rem; background: #fff; border: 1.5px solid #C7D2FE; color: #4338CA; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: inherit; white-space: nowrap; }
.btn-outline-sm:hover { background: #EEF2FF; }
.btn-danger-sm { padding: 0.35rem 0.875rem; background: #fff; border: 1.5px solid #FECACA; color: #DC2626; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: inherit; }
.btn-danger-sm:hover { background: #FEF2F2; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.modal-box { background: #fff; border-radius: 16px; padding: 1.75rem; width: 100%; max-width: 440px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.375rem; }
.modal-sub { font-size: 0.875rem; color: #6B7280; margin: 0; }
.modal-form { margin-top: 1.25rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }

/* Transición formulario */
.slide-down-enter-active,
.slide-down-leave-active { transition: all 0.2s ease; overflow: hidden; }
.slide-down-enter-from,
.slide-down-leave-to { opacity: 0; max-height: 0; }
.slide-down-enter-to,
.slide-down-leave-from { opacity: 1; max-height: 1000px; }

@keyframes spin { to { transform: rotate(360deg); } }

/* Selector empresa */
.selector-wrap { position: relative; display: inline-block; }
.selector-btn { display: inline-flex; align-items: center; gap: 0.625rem; padding: 0.55rem 0.875rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; font-family: inherit; min-width: 220px; transition: border-color 0.15s; }
.selector-btn:hover { border-color: #7C3AED; }
.selector-btn.sin-sel { border-style: dashed; color: #9CA3AF; }
.selector-icono svg { width: 16px; height: 16px; color: #6B7280; flex-shrink: 0; }
.selector-texto { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left; }
.selector-chevron { width: 14px; height: 14px; color: #9CA3AF; flex-shrink: 0; }
.selector-dropdown { position: absolute; top: calc(100% + 6px); left: 0; min-width: 260px; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); z-index: 200; overflow: hidden; }
.dropdown-search { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem; border-bottom: 1px solid #F3F4F6; }
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; flex-shrink: 0; }
.dropdown-input { flex: 1; border: none; outline: none; font-size: 0.875rem; color: #111827; font-family: inherit; background: transparent; }
.dropdown-empty { padding: 1rem; font-size: 0.8125rem; color: #9CA3AF; text-align: center; }
.dropdown-option { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.625rem 0.875rem; background: none; border: none; font-size: 0.875rem; color: #374151; cursor: pointer; font-family: inherit; text-align: left; }
.dropdown-option:hover { background: #F5F3FF; }
.dropdown-option.selected { background: #EEF2FF; }
.dropdown-todos { border-bottom: 1px solid #F3F4F6; color: #6B7280; font-style: italic; }
.option-nombre { flex: 1; }
.option-check { width: 15px; height: 15px; color: #7C3AED; flex-shrink: 0; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 199; }
</style>
