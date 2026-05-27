<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva } from '../../../utils/empresaActiva.js'
import { useToast } from '../../../utils/useToast.js'

const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = useToast()

const usuario      = JSON.parse(localStorage.getItem('usuario') || '{}')
const esSuperadmin = usuario.rol === 'SUPERADMIN'

// ── Selector de empresa (SUPERADMIN) ──────────────────────────
const empresas         = ref([])
const empresaActiva    = ref(getEmpresaActiva())
const mostrarDropdown  = ref(false)
const busqueda         = ref('')
const cargandoEmpresas = ref(false)
const sinEmpresa       = computed(() => esSuperadmin && !empresaActiva.value)
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
  resumen.value = null; alertas.value = []; planes.value = []; asignaciones.value = []
}

// ── Tabs ──────────────────────────────────────────────────────
const tabs = [
  { id: 'planes',       name: 'Planes'       },
  { id: 'asignaciones', name: 'Asignaciones' },
  { id: 'alertas',      name: 'Alertas'      },
  { id: 'simulador',    name: 'Simulador'    },
]
const currentTab = ref('alertas')

// ── KPIs ──────────────────────────────────────────────────────
const resumen         = ref(null)
const cargandoResumen = ref(false)

const fetchResumen = async () => {
  cargandoResumen.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/predictivo/resumen/')
    if (res.ok) resumen.value = await res.json()
  } catch {} finally { cargandoResumen.value = false }
}

// ── Alertas ───────────────────────────────────────────────────
const alertas             = ref([])
const alertasFiltroNivel  = ref('')
const alertasFiltroEstado = ref('pendiente')
const cargandoAlertas     = ref(false)
const generando           = ref(false)

const fetchAlertas = async () => {
  cargandoAlertas.value = true
  try {
    let url = '/api/empresa/alertas-mantenimiento/?'
    if (alertasFiltroNivel.value)  url += `nivel=${alertasFiltroNivel.value}&`
    if (alertasFiltroEstado.value) url += `estado=${alertasFiltroEstado.value}&`
    const res = await apiFetchEmpresa(url)
    if (res.ok) alertas.value = await res.json()
  } catch {} finally { cargandoAlertas.value = false }
}

const generarAlertas = async () => {
  generando.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/predictivo/generar-alertas/', { method: 'POST', body: {} })
    if (res.ok) {
      const d = await res.json()
      toast.success(`Evaluación completada: ${d.alertas_creadas} nuevas, ${d.alertas_actualizadas} actualizadas`)
      fetchAlertas(); fetchResumen()
    } else { toast.error('Error al generar alertas') }
  } catch { toast.error('Error de conexión') } finally { generando.value = false }
}


// ── Modal atender ─────────────────────────────────────────────
const modalAtenderOpen  = ref(false)
const alertaActual      = ref(null)
const fechaRealizada    = ref('')
const costoRealizado    = ref(0)
const guardandoAtencion = ref(false)

const openAtenderModal = (alerta) => {
  alertaActual.value    = alerta
  fechaRealizada.value  = new Date().toISOString().slice(0, 10)
  costoRealizado.value  = alerta.costo_estimado ?? 0
  modalAtenderOpen.value = true
}

const atenderAlerta = async () => {
  guardandoAtencion.value = true
  try {
    const res = await apiFetchEmpresa(
      `/api/empresa/alertas-mantenimiento/${alertaActual.value.id}/atender/`,
      { method: 'POST', body: { fecha_realizada: fechaRealizada.value, costo: costoRealizado.value } }
    )
    if (res.ok) {
      toast.success('Alerta atendida y mantención registrada')
      modalAtenderOpen.value = false
      fetchAlertas(); fetchResumen()
    } else {
      const d = await res.json()
      toast.error(d.error || 'Error al registrar')
    }
  } catch { toast.error('Error de conexión') } finally { guardandoAtencion.value = false }
}

// ── Planes ────────────────────────────────────────────────────
const planes          = ref([])
const cargandoPlanes  = ref(false)
const mostrarFormPlan = ref(false)
const planEditando    = ref(null)
const planAEliminar   = ref(null)
const guardando       = ref(false)

const fetchPlanes = async () => {
  cargandoPlanes.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/planes-mantenimiento/')
    if (res.ok) planes.value = await res.json()
  } catch {} finally { cargandoPlanes.value = false }
}

function defaultRegla() {
  return { tipo: '', intervalo_dias: 90, umbral_alerta_dias: 15, prioridad: 'media', costo_estimado: 0, escalar_sin_respuesta: false, bloquear_despacho: false, canal: 'email' }
}

const nuevoPlan = ref({ nombre: '', descripcion: '', activo: true, reglas: [defaultRegla()] })

const abrirNuevoPlan = () => {
  planEditando.value  = null
  nuevoPlan.value     = { nombre: '', descripcion: '', activo: true, reglas: [defaultRegla()] }
  mostrarFormPlan.value = true
}

const abrirEditarPlan = (plan) => {
  planEditando.value = plan.id
  nuevoPlan.value    = {
    nombre:      plan.nombre,
    descripcion: plan.descripcion || '',
    activo:      plan.activo,
    reglas:      plan.reglas.map(r => ({ ...r })),
  }
  mostrarFormPlan.value = true
}

const resetFormPlan = () => { mostrarFormPlan.value = false; planEditando.value = null }

const guardarPlan = async () => {
  guardando.value = true
  try {
    const url    = planEditando.value ? `/api/empresa/planes-mantenimiento/${planEditando.value}/` : '/api/empresa/planes-mantenimiento/'
    const method = planEditando.value ? 'PUT' : 'POST'
    const res    = await apiFetchEmpresa(url, { method, body: nuevoPlan.value })
    if (res.ok) {
      toast.success(planEditando.value ? 'Plan actualizado' : 'Plan creado')
      resetFormPlan(); fetchPlanes()
    } else {
      const d = await res.json()
      toast.error(d.error || d.nombre?.[0] || 'Error al guardar')
    }
  } catch { toast.error('Error de conexión') } finally { guardando.value = false }
}

const eliminarPlan = async (plan) => {
  planAEliminar.value = null
  try {
    const res = await apiFetchEmpresa(`/api/empresa/planes-mantenimiento/${plan.id}/`, { method: 'DELETE' })
    if (res.ok) { toast.success(`Plan "${plan.nombre}" eliminado`); fetchPlanes() }
    else toast.error('Error al eliminar')
  } catch { toast.error('Error de conexión') }
}

const alertasPorVehiculo = computed(() => {
  const map = {}
  alertas.value.forEach(a => {
    if (!a.atendida) {
      if (!map[a.vehiculo_patente]) map[a.vehiculo_patente] = { pendientes: 0, vencidas: 0 }
      map[a.vehiculo_patente].pendientes++
      if (a.nivel === 'vencida') map[a.vehiculo_patente].vencidas++
    }
  })
  return map
})

const formatIntervalo = (dias) => {
  if (!dias) return ''
  if (dias >= 365) return `≈ ${Math.round(dias / 365 * 10) / 10} años`
  if (dias >= 30)  return `≈ ${Math.round(dias / 30  * 10) / 10} meses`
  return `${dias} días`
}

// ── Asignaciones ──────────────────────────────────────────────
const asignaciones    = ref([])
const cargandoAsig    = ref(false)
const vehiculos       = ref([])
const guardandoAsig   = ref(false)

// Nuevo flujo: seleccionar plan → checkboxes de vehículos
const asigPlanId      = ref('')
const asigSeleccion   = ref(new Set()) // vehiculo IDs marcados

// Vehículos ya asignados al plan seleccionado (para saber qué borrar)
// El serializer devuelve 'plan' y 'vehiculo' como IDs directos (FK)
const asigPrevios = computed(() => {
  if (!asigPlanId.value) return {}
  const map = {}
  asignaciones.value
    .filter(a => String(a.plan) === String(asigPlanId.value))
    .forEach(a => { map[a.vehiculo] = a.id })
  return map
})

// Cuando cambia el plan, pre-marcar vehículos que ya lo tienen
const onCambiarPlan = () => {
  asigSeleccion.value = new Set(
    Object.keys(asigPrevios.value).map(Number)
  )
}

const toggleVehiculo = (id) => {
  const s = new Set(asigSeleccion.value)
  s.has(id) ? s.delete(id) : s.add(id)
  asigSeleccion.value = s
}

const seleccionarTodos = () => {
  asigSeleccion.value = new Set(vehiculos.value.map(v => v.id))
}
const deseleccionarTodos = () => {
  asigSeleccion.value = new Set()
}

const fetchAsignaciones = async () => {
  cargandoAsig.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/vehiculo-planes/')
    if (res.ok) asignaciones.value = await res.json()
  } catch {} finally { cargandoAsig.value = false }
}

const fetchVehiculos = async () => {
  try {
    const res = await apiFetchEmpresa('/api/empresa/vehiculos/')
    if (res.ok) vehiculos.value = await res.json()
  } catch {}
}

const guardarAsignaciones = async () => {
  if (!asigPlanId.value) { toast.error('Selecciona un plan'); return }
  guardandoAsig.value = true

  const prevMap    = asigPrevios.value           // { vehiculo_id: asignacion_id }
  const prevIds    = new Set(Object.keys(prevMap).map(Number))
  const nuevosIds  = [...asigSeleccion.value].filter(id => !prevIds.has(id))
  const borrarIds  = [...prevIds].filter(id => !asigSeleccion.value.has(id))

  try {
    // Crear nuevas asignaciones
    await Promise.all(nuevosIds.map(vehiculo_id =>
      apiFetchEmpresa('/api/empresa/vehiculo-planes/', {
        method: 'POST', body: { vehiculo_id, plan_id: Number(asigPlanId.value) }
      })
    ))
    // Eliminar asignaciones desmarcadas
    await Promise.all(borrarIds.map(vid =>
      apiFetchEmpresa(`/api/empresa/vehiculo-planes/${prevMap[vid]}/`, { method: 'DELETE' })
    ))

    const agregados = nuevosIds.length
    const eliminados = borrarIds.length
    const msg = [
      agregados  ? `${agregados} vehículo(s) asignado(s)`   : '',
      eliminados ? `${eliminados} vehículo(s) desasignado(s)` : '',
    ].filter(Boolean).join(', ')

    toast.success(msg || 'Sin cambios')
    await fetchAsignaciones()
    fetchResumen()
    if (agregados) generarAlertas()
    onCambiarPlan() // sincronizar estado visual
  } catch {
    toast.error('Error al guardar asignaciones')
  } finally {
    guardandoAsig.value = false
  }
}

const eliminarAsignacion = async (asig) => {
  try {
    const res = await apiFetchEmpresa(`/api/empresa/vehiculo-planes/${asig.id}/`, { method: 'DELETE' })
    if (res.ok) {
      toast.success('Asignación eliminada')
      await fetchAsignaciones()
      fetchResumen()
      onCambiarPlan()
    } else toast.error('Error al eliminar')
  } catch { toast.error('Error de conexión') }
}

// ── Simulador ─────────────────────────────────────────────────
const simuladorVehiculoId  = ref('')
const simuladorMeses       = ref(3)
const simulando            = ref(false)
const simulacionResultados = ref(null)

const ejecutarSimulacion = async () => {
  simulando.value = true
  simulacionResultados.value = null
  try {
    const res = await apiFetchEmpresa(
      `/api/empresa/simulador-vencimientos/?vehiculo_id=${simuladorVehiculoId.value}&meses=${simuladorMeses.value}`
    )
    if (res.ok) simulacionResultados.value = await res.json()
    else toast.error('Error al ejecutar la simulación')
  } catch { toast.error('Error de conexión') } finally { simulando.value = false }
}

const formatFecha = (f) => { const [y,m,d] = f.split('-'); return `${d}/${m}/${y}` }
const clp = (v) => v != null ? '$' + Number(v).toLocaleString('es-CL') : '—'

const TIPOS_MANTENCION_MAP = {
  aceite: 'Cambio de aceite',
  frenos: 'Revisión de frenos',
  neumaticos: 'Cambio de neumáticos',
  filtro_aire: 'Filtro de aire',
  filtro_combustible: 'Filtro de combustible',
  rtv: 'Revisión técnica (RTV)',
  electrica: 'Revisión eléctrica',
  otro: 'Otro'
}
const formatTipoMantencion = (t) => TIPOS_MANTENCION_MAP[t] || t

// ── Lifecycle ─────────────────────────────────────────────────
const cargarTodo = () => {
  if (sinEmpresa.value) return
  fetchResumen(); fetchAlertas(); fetchPlanes(); fetchAsignaciones(); fetchVehiculos()
}

// Escuchar notificaciones WS para actualizar en tiempo real
// cuando el cron genera nuevas alertas predictivas
const TIPOS_PREDICTIVO = new Set([
  'mantencion_por_vencer',
  'mantencion_vencida',
  'actividad',        // algunas notificaciones de alertas usan este tipo
])

const onWsNotificacion = (e) => {
  const tipo = e.detail?.tipo
  if (TIPOS_PREDICTIVO.has(tipo)) {
    fetchAlertas()
    fetchResumen()
  }
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
  window.addEventListener('ws:notificacion', onWsNotificacion)
})

onUnmounted(() => {
  window.removeEventListener('ws:notificacion', onWsNotificacion)
})
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenimiento Predictivo</h1>
        <p class="page-subtitle">Alertas, planes y asignaciones de mantenimiento preventivo</p>
      </div>
      <div class="header-actions">
        <!-- Selector empresa SUPERADMIN -->
        <div v-if="esSuperadmin" class="selector-wrap">
          <button class="selector-btn" :class="{ 'sin-sel': !empresaActiva }" @click="mostrarDropdown = !mostrarDropdown">
            <span class="selector-icono"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg></span>
            <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
            <svg class="selector-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </button>
          <div v-if="mostrarDropdown" class="selector-dropdown">
            <div class="dropdown-search">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/></svg>
              <input v-model="busqueda" placeholder="Buscar empresa..." class="dropdown-input" autofocus/>
            </div>
            <button v-if="empresaActiva" class="dropdown-option dropdown-todos" @click="limpiarEmpresa">— Quitar selección</button>
            <div v-if="cargandoEmpresas" class="dropdown-empty">Cargando...</div>
            <div v-else-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</div>
            <button v-for="emp in empresasFiltradas" :key="emp.id" class="dropdown-option" :class="{ selected: empresaActiva?.id === emp.id }" @click="seleccionarEmpresa(emp)">
              <span>{{ emp.nombre }}</span>
              <svg v-if="empresaActiva?.id === emp.id" style="width:14px;height:14px;color:#7C3AED" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            </button>
          </div>
          <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
        </div>
      </div>
    </div>

    <template v-if="!sinEmpresa">
      <!-- KPIs globales -->
      <div v-if="resumen" class="kpis-row">
        <div class="kpi" :class="resumen.alertas_vencidas > 0 ? 'kpi-red' : ''">
          <div class="kpi-val">{{ resumen.alertas_vencidas }}</div>
          <div class="kpi-lbl">Vencidas</div>
        </div>
        <div class="kpi" :class="resumen.alertas_por_vencer > 0 ? 'kpi-yellow' : ''">
          <div class="kpi-val">{{ resumen.alertas_por_vencer }}</div>
          <div class="kpi-lbl">Por vencer</div>
        </div>
        <div class="kpi">
          <div class="kpi-val">{{ resumen.atendidas_mes }}</div>
          <div class="kpi-lbl">Atendidas este mes</div>
        </div>
        <div class="kpi">
          <div class="kpi-val">{{ resumen.vehiculos_con_alerta }}</div>
          <div class="kpi-lbl">Vehículos con alerta</div>
        </div>
        <div class="kpi">
          <div class="kpi-val">{{ resumen.vehiculos_asignados }}</div>
          <div class="kpi-lbl">Vehículos con plan</div>
        </div>
        <div class="kpi">
          <div class="kpi-val">{{ resumen.planes_activos }}</div>
          <div class="kpi-lbl">Planes activos</div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs-bar">
        <button v-for="tab in tabs" :key="tab.id" class="tab-btn" :class="{ active: currentTab === tab.id }" @click="currentTab = tab.id">
          {{ tab.name }}
          <span v-if="tab.id === 'alertas' && resumen?.alertas_pendientes" class="tab-badge">{{ resumen.alertas_pendientes }}</span>
        </button>
      </div>

      <!-- ═══ TAB ALERTAS ═══ -->
      <div v-if="currentTab === 'alertas'">
        <div class="list-header">
          <h2 class="section-title">Alertas de mantenimiento</h2>
          <div class="filters">
            <select v-model="alertasFiltroNivel" @change="fetchAlertas" class="input select">
              <option value="">Todos los niveles</option>
              <option value="por_vencer">Por vencer</option>
              <option value="vencida">Vencida</option>
            </select>
            <select v-model="alertasFiltroEstado" @change="fetchAlertas" class="input select">
              <option value="pendiente">Pendientes</option>
              <option value="atendida">Atendidas</option>
              <option value="">Todas</option>
            </select>
<button class="btn-secondary" @click="generarAlertas" :disabled="generando">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              {{ generando ? 'Evaluando...' : 'Evaluar ahora' }}
            </button>
          </div>
        </div>

        <div v-if="cargandoAlertas" class="loading"><div class="spinner"/> Cargando alertas...</div>
        <div v-else class="card list-card">
          <div v-for="alerta in alertas" :key="alerta.id" class="alert-row">
            <div class="alert-main">
              <div class="alert-top">
                <span class="patente-tag">{{ alerta.vehiculo_patente }}</span>
                <span class="tipo-text">{{ formatTipoMantencion(alerta.tipo_mantencion) }}</span>
                <span class="nivel-badge" :class="alerta.nivel === 'vencida' ? 'nivel-vencida' : 'nivel-por-vencer'">
                  {{ alerta.nivel === 'vencida' ? 'Vencida' : 'Por vencer' }}
                </span>
                <span v-if="alerta.atendida" class="nivel-badge nivel-atendida">✓ Atendida</span>
              </div>
              <div class="alert-meta">
                <span v-if="alerta.dias_restantes <= 0" class="dias-vencida">Vencida hace {{ Math.abs(alerta.dias_restantes) }} días</span>
                <span v-else class="dias-por-vencer">Vence en {{ alerta.dias_restantes }} días</span>
                <span class="pct-text">Avance: {{ alerta.pct_avance }}%</span>
                <span v-if="alerta.atendida && alerta.fecha_atencion" class="pct-text">
                  Atendida: {{ new Date(alerta.fecha_atencion).toLocaleDateString('es-CL') }}
                </span>
              </div>
              <div class="progress-track">
                <div class="progress-fill" :class="alerta.nivel === 'vencida' ? 'fill-red' : 'fill-yellow'" :style="{ width: Math.min(alerta.pct_avance, 100) + '%' }"/>
              </div>
            </div>
            <div v-if="!alerta.atendida" class="alert-actions">
              <button class="btn-outline-sm" @click="router.push({ path: ruta('/mantenciones/nueva'), query: { vehiculo: alerta.vehiculo_id, tipo: alerta.tipo_mantencion, presupuesto: alerta.costo_estimado || '' } })">Programar</button>
              <button class="btn-primary-sm" @click="openAtenderModal(alerta)">Registrar</button>
            </div>
          </div>
          <div v-if="!alertas.length" class="empty-msg">No hay alertas para mostrar.</div>
        </div>
      </div>

      <!-- ═══ TAB PLANES ═══ -->
      <div v-if="currentTab === 'planes'">
        <div class="list-header">
          <h2 class="section-title">Planes de mantenimiento</h2>
          <button class="btn-primary" @click="abrirNuevoPlan">+ Nuevo plan</button>
        </div>

        <Transition name="slide-down">
          <div v-if="mostrarFormPlan" class="card form-card">
            <h3 class="form-card-title">{{ planEditando ? 'Editar Plan' : 'Crear Plan de Mantenimiento' }}</h3>
            <form @submit.prevent="guardarPlan" class="form">
              <div class="form-row">
                <div class="form-group">
                  <label class="label">Nombre del plan *</label>
                  <input v-model="nuevoPlan.nombre" type="text" class="input" placeholder="Ej: Plan semestral" required/>
                </div>
                <div class="form-group">
                  <label class="label">Descripción</label>
                  <input v-model="nuevoPlan.descripcion" type="text" class="input" placeholder="Opcional"/>
                </div>
              </div>

              <div class="reglas-header">
                <span class="label">Reglas del plan</span>
                <button type="button" class="btn-link" @click="nuevoPlan.reglas.push(defaultRegla())">+ Agregar regla</button>
              </div>

              <div v-for="(regla, idx) in nuevoPlan.reglas" :key="idx" class="regla-card">
                <button v-if="nuevoPlan.reglas.length > 1" type="button" class="regla-remove" @click="nuevoPlan.reglas.splice(idx, 1)">&times;</button>
                <div class="regla-grid">
                  <div class="form-group">
                    <label class="label-xs">Tipo mantención</label>
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
                    <label class="label-xs">Alerta (días antes)</label>
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
                    <label class="label-xs">Costo est. ($)</label>
                    <input type="number" v-model.number="regla.costo_estimado" min="0" class="input"/>
                  </div>
                  <div class="form-group regla-checks">
                    <label class="check-label"><input type="checkbox" v-model="regla.escalar_sin_respuesta" class="check"/> Escalar si no se atiende (48h)</label>
                    <label class="check-label"><input type="checkbox" v-model="regla.bloquear_despacho" class="check"/> Bloquear vehículo si vence</label>
                  </div>
                </div>
              </div>

              <div class="form-actions">
                <button type="button" class="btn-secondary" @click="resetFormPlan">Cancelar</button>
                <button type="submit" class="btn-primary" :disabled="guardando">
                  <span v-if="guardando" class="spinner-inline"/>
                  {{ guardando ? 'Guardando...' : (planEditando ? 'Actualizar plan' : 'Guardar plan') }}
                </button>
              </div>
            </form>
          </div>
        </Transition>

        <div v-if="cargandoPlanes" class="loading"><div class="spinner"/> Cargando planes...</div>
        <div v-else class="planes-grid">
          <div v-for="plan in planes" :key="plan.id" class="plan-card card">
            <div class="plan-header">
              <h3 class="plan-nombre">{{ plan.nombre }}</h3>
              <span class="plan-estado" :class="plan.activo ? 'estado-activo' : 'estado-inactivo'">{{ plan.activo ? 'Activo' : 'Inactivo' }}</span>
            </div>
            <p class="plan-desc">{{ plan.descripcion || 'Sin descripción' }}</p>
            <div class="plan-reglas">
              <span class="reglas-titulo">{{ plan.reglas.length }} regla{{ plan.reglas.length !== 1 ? 's' : '' }}</span>
              <ul class="reglas-lista">
                <li v-for="r in plan.reglas" :key="r.id">
                  <span class="regla-tipo-tag">{{ formatTipoMantencion(r.tipo) }}</span>
                  cada {{ r.intervalo_dias }} días · alerta {{ r.umbral_alerta_dias }} días antes
                  <span v-if="r.costo_estimado > 0" class="regla-costo">· {{ clp(r.costo_estimado) }}</span>
                </li>
              </ul>
            </div>
            <div class="plan-footer">
              <div v-if="planAEliminar === plan.id" class="confirm-delete">
                <span class="confirm-text">¿Eliminar?</span>
                <button class="btn-danger-sm" @click="eliminarPlan(plan)">Sí</button>
                <button class="btn-outline-sm" @click="planAEliminar = null">No</button>
              </div>
              <template v-else>
                <button class="btn-outline-sm" @click="abrirEditarPlan(plan)">Editar</button>
                <button class="btn-danger-sm" @click="planAEliminar = plan.id">Eliminar</button>
              </template>
            </div>
          </div>
          <div v-if="!planes.length && !mostrarFormPlan" class="onboarding-card card">
            <h3 class="onboarding-title">Configura el mantenimiento predictivo</h3>
            <p class="onboarding-desc">Sigue estos 3 pasos para que el sistema genere alertas automáticas antes de que tus vehículos necesiten mantención.</p>
            <div class="onboarding-steps">
              <div class="onboarding-step onboarding-step-active">
                <div class="step-num">1</div>
                <div class="step-info">
                  <strong>Crear un plan</strong>
                  <span>Define qué mantenciones hacer y cada cuántos días</span>
                </div>
              </div>
              <div class="onboarding-step">
                <div class="step-num step-num-pending">2</div>
                <div class="step-info">
                  <strong>Asignar a vehículos</strong>
                  <span>Aplica el plan a uno o más vehículos de tu flota</span>
                </div>
              </div>
              <div class="onboarding-step">
                <div class="step-num step-num-pending">3</div>
                <div class="step-info">
                  <strong>Recibir alertas automáticas</strong>
                  <span>El sistema avisará cuando se acerque cada mantención</span>
                </div>
              </div>
            </div>
            <button class="btn-primary" @click="abrirNuevoPlan">Crear primer plan</button>
          </div>
        </div>
      </div>

      <!-- ═══ TAB ASIGNACIONES ═══ -->
      <div v-if="currentTab === 'asignaciones'">

        <div class="asig-layout">

          <!-- ── Panel izquierdo: selección ─────────────────── -->
          <div class="asig-panel-left">
            <div class="card form-card">
              <h3 class="form-card-title">Asignar plan a vehículos</h3>

              <!-- 1. Selector de plan -->
              <div class="form-group mb-4">
                <label class="label">Plan de mantenimiento</label>
                <select v-model="asigPlanId" class="input select" @change="onCambiarPlan">
                  <option value="">— Selecciona un plan —</option>
                  <option v-for="p in planes" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
              </div>

              <!-- 2. Lista de vehículos con checkboxes -->
              <template v-if="asigPlanId">
                <div class="asig-vehiculos-header">
                  <span class="label" style="margin:0">
                    Vehículos
                    <span class="asig-count">{{ asigSeleccion.size }} / {{ vehiculos.length }}</span>
                  </span>
                  <div class="asig-quick-actions">
                    <button class="btn-link" @click="seleccionarTodos">Todos</button>
                    <span style="color:#D1D5DB">·</span>
                    <button class="btn-link" @click="deseleccionarTodos">Ninguno</button>
                  </div>
                </div>

                <div class="asig-vehiculos-list">
                  <label
                    v-for="v in vehiculos" :key="v.id"
                    :class="['asig-vehiculo-item', asigSeleccion.has(v.id) && 'asig-vehiculo-checked']"
                  >
                    <input
                      type="checkbox"
                      :checked="asigSeleccion.has(v.id)"
                      @change="toggleVehiculo(v.id)"
                      class="asig-checkbox"
                    />
                    <span class="asig-patente">{{ v.patente }}</span>
                    <span class="asig-vehiculo-info">{{ v.marca }} {{ v.modelo }}</span>
                    <span v-if="asigPrevios[v.id]" class="asig-badge-mini">asignado</span>
                  </label>
                  <div v-if="!vehiculos.length" class="empty-msg">No hay vehículos registrados.</div>
                </div>

                <button
                  class="btn-primary w-full mt-4"
                  @click="guardarAsignaciones"
                  :disabled="guardandoAsig"
                >
                  <span v-if="guardandoAsig" class="spinner-inline"/>
                  {{ guardandoAsig ? 'Guardando...' : 'Guardar asignaciones' }}
                </button>
              </template>

              <div v-else class="asig-placeholder">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                <p>Selecciona un plan para ver y editar qué vehículos lo tienen asignado.</p>
              </div>
            </div>
          </div>

          <!-- ── Panel derecho: resumen de asignaciones ──────── -->
          <div class="asig-panel-right">
            <div class="list-header" style="margin-bottom:0.75rem">
              <h2 class="section-title">Asignaciones actuales</h2>
            </div>
            <div v-if="cargandoAsig" class="loading"><div class="spinner"/> Cargando...</div>
            <div v-else-if="asignaciones.length" class="card list-card">
              <table class="tabla">
                <thead>
                  <tr>
                    <th>Vehículo</th>
                    <th>Plan</th>
                    <th>Alertas</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="asig in asignaciones" :key="asig.id">
                    <td class="font-med">{{ asig.vehiculo_patente }}</td>
                    <td>{{ asig.plan_nombre }}</td>
                    <td>
                      <span v-if="alertasPorVehiculo[asig.vehiculo_patente]?.vencidas" class="asig-badge asig-badge-red">
                        {{ alertasPorVehiculo[asig.vehiculo_patente].vencidas }} vencida{{ alertasPorVehiculo[asig.vehiculo_patente].vencidas !== 1 ? 's' : '' }}
                      </span>
                      <span v-else-if="alertasPorVehiculo[asig.vehiculo_patente]?.pendientes" class="asig-badge asig-badge-yellow">
                        {{ alertasPorVehiculo[asig.vehiculo_patente].pendientes }} por vencer
                      </span>
                      <span v-else class="asig-badge asig-badge-green">OK</span>
                    </td>
                    <td>
                      <button class="btn-danger-sm" @click="eliminarAsignacion(asig)">Quitar</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="card list-card">
              <div class="empty-msg">Aún no hay asignaciones.</div>
            </div>
          </div>

        </div>
      </div>

      <!-- ═══ TAB SIMULADOR ═══ -->
      <div v-if="currentTab === 'simulador'">
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
                <option :value="3">3 meses</option>
                <option :value="6">6 meses</option>
                <option :value="12">12 meses</option>
              </select>
            </div>
            <div class="form-group">
              <label class="label">&nbsp;</label>
              <button class="btn-primary" @click="ejecutarSimulacion" :disabled="!simuladorVehiculoId || simulando">
                <span v-if="simulando" class="spinner-inline"/>
                {{ simulando ? 'Calculando...' : 'Proyectar' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="simulacionResultados" class="card">
          <div class="sim-resumen">
            <h3 class="section-title">Proyección de eventos</h3>
            <div class="sim-stats">
              <span class="stat-item">Total: <strong>{{ simulacionResultados.total_eventos }}</strong></span>
              <span class="stat-sep">·</span>
              <span class="stat-item">Presupuesto estimado: <strong>{{ clp(simulacionResultados.presupuesto_total) }}</strong></span>
            </div>
          </div>
          <div class="sim-lista">
            <div v-for="(evento, idx) in simulacionResultados.eventos" :key="idx" class="sim-evento">
              <span class="sim-tipo">{{ formatTipoMantencion(evento.tipo) }}</span>
              <span class="sim-fecha">{{ formatFecha(evento.fecha) }}</span>
              <span class="sim-costo">{{ clp(evento.costo_estimado) }}</span>
            </div>
            <div v-if="!simulacionResultados.eventos.length" class="empty-msg">No se proyectan eventos para este período.</div>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══ MODAL ATENDER ALERTA ═══ -->
    <Teleport to="body">
      <div v-if="modalAtenderOpen" class="modal-overlay" @click.self="modalAtenderOpen = false">
        <div class="modal-box">
          <h3 class="modal-title">Registrar mantención realizada</h3>
          <p class="modal-sub">Vehículo <strong>{{ alertaActual?.vehiculo_patente }}</strong> — {{ formatTipoMantencion(alertaActual?.tipo_mantencion) }}</p>
          <div class="form modal-form">
            <div class="form-group">
              <label class="label">Fecha de realización</label>
              <input type="date" v-model="fechaRealizada" class="input" required/>
            </div>
            <div class="form-group">
              <label class="label">Costo real (CLP)</label>
              <input type="number" v-model.number="costoRealizado" class="input" min="0" placeholder="0"/>
              <p class="hint">Estimado: {{ clp(alertaActual?.costo_estimado) }}</p>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-secondary" @click="modalAtenderOpen = false" :disabled="guardandoAtencion">Cancelar</button>
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
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.2rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; }

/* KPIs */
.kpis-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.kpi { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 0.875rem 1.25rem; flex: 1; min-width: 110px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-red { border-color: #FECACA; background: #FEF2F2; }
.kpi-yellow { border-color: #FDE68A; background: #FFFBEB; }
.kpi-val { font-size: 1.75rem; font-weight: 800; color: #111827; line-height: 1; }
.kpi-red .kpi-val { color: #DC2626; }
.kpi-yellow .kpi-val { color: #D97706; }
.kpi-lbl { font-size: 0.75rem; color: #9CA3AF; margin-top: 0.25rem; }

/* Tabs */
.tabs-bar { display: flex; border-bottom: 2px solid #E5E7EB; margin-bottom: 1.5rem; }
.tab-btn { display: flex; align-items: center; gap: 0.375rem; padding: 0.75rem 1.25rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-family: inherit; transition: color 0.15s, border-color 0.15s; }
.tab-btn:hover { color: #374151; }
.tab-btn.active { color: #4F46E5; border-bottom-color: #4F46E5; font-weight: 600; }
.tab-badge { background: #EF4444; color: #fff; font-size: 0.65rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 999px; }

/* Layout */
.list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.section-title { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.filters { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
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
.alert-top { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.patente-tag { font-size: 0.8125rem; font-weight: 700; color: #4F46E5; background: #EEF2FF; padding: 0.2rem 0.5rem; border-radius: 6px; font-family: monospace; }
.tipo-text { font-size: 0.875rem; color: #374151; }
.nivel-badge { font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 999px; }
.nivel-vencida { background: #FEE2E2; color: #B91C1C; }
.nivel-por-vencer { background: #FEF9C3; color: #92400E; }
.nivel-atendida { background: #D1FAE5; color: #065F46; }
.alert-meta { display: flex; align-items: center; gap: 1rem; font-size: 0.8125rem; margin-bottom: 0.35rem; flex-wrap: wrap; }
.dias-vencida { color: #DC2626; font-weight: 600; }
.dias-por-vencer { color: #D97706; font-weight: 600; }
.pct-text { color: #9CA3AF; }
.progress-track { height: 6px; background: #F3F4F6; border-radius: 999px; max-width: 300px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 999px; transition: width 0.3s; }
.fill-red { background: #EF4444; }
.fill-yellow { background: #F59E0B; }
.alert-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }

/* Planes */
.planes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
.plan-card { display: flex; flex-direction: column; gap: 0.75rem; }
.plan-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.plan-nombre { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.plan-estado { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.625rem; border-radius: 999px; flex-shrink: 0; }
.estado-activo { background: #D1FAE5; color: #065F46; }
.estado-inactivo { background: #F3F4F6; color: #6B7280; }
.plan-desc { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.plan-reglas { background: #F9FAFB; border-radius: 10px; padding: 0.75rem 1rem; }
.reglas-titulo { font-size: 0.75rem; font-weight: 700; color: #374151; display: block; margin-bottom: 0.375rem; text-transform: uppercase; letter-spacing: 0.04em; }
.reglas-lista { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.3rem; }
.reglas-lista li { font-size: 0.8125rem; color: #4B5563; display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.regla-tipo-tag { font-weight: 600; color: #374151; }
.regla-costo { color: #059669; font-weight: 600; }
.plan-footer { display: flex; justify-content: flex-end; align-items: center; gap: 0.5rem; border-top: 1px solid #F3F4F6; padding-top: 0.75rem; margin-top: auto; }
.confirm-delete { display: flex; align-items: center; gap: 0.5rem; }
.confirm-text { font-size: 0.8125rem; color: #374151; }

/* Formulario plan */
.form { display: flex; flex-direction: column; gap: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-row-3 { display: grid; grid-template-columns: 1fr 1fr auto; gap: 1rem; align-items: end; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.label-xs { font-size: 0.8rem; font-weight: 600; color: #374151; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; font-family: inherit; width: 100%; transition: border-color 0.15s; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.select { cursor: pointer; }
.hint { font-size: 0.75rem; color: #9CA3AF; margin: 0.2rem 0 0; }
.reglas-header { display: flex; align-items: center; justify-content: space-between; }
.regla-card { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem; position: relative; }
.regla-remove { position: absolute; top: 0.6rem; right: 0.75rem; background: none; border: none; font-size: 1.25rem; color: #9CA3AF; cursor: pointer; padding: 0; }
.regla-remove:hover { color: #EF4444; }
.regla-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 0.75rem; align-items: start; }
.regla-checks { grid-column: 1 / -1; display: flex; gap: 1.5rem; flex-wrap: wrap; }
.check-label { display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; color: #374151; cursor: pointer; }
.check { accent-color: #7C3AED; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

/* Asignaciones */
.asig-form { display: grid; grid-template-columns: 1fr 1fr auto; gap: 1rem; align-items: end; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.tabla tr:last-child td { border-bottom: none; }
.font-med { font-weight: 600; color: #111827; }
.text-m { color: #6B7280; }

/* Simulador */
.sim-filtros { margin-bottom: 1rem; }
.sim-resumen { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.sim-stats { display: flex; align-items: center; gap: 0.75rem; }
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
.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; white-space: nowrap; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-secondary { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.6rem 1.1rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.45rem 0.875rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-outline svg { width: 14px; height: 14px; }
.btn-outline:hover:not(:disabled) { border-color: #4F46E5; color: #4F46E5; }
.btn-outline:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-primary-sm { padding: 0.35rem 0.875rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.8125rem; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; font-family: inherit; }
.btn-outline-sm { padding: 0.35rem 0.875rem; background: #fff; border: 1.5px solid #C7D2FE; color: #4338CA; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: inherit; }
.btn-outline-sm:hover { background: #EEF2FF; }
.btn-danger-sm { padding: 0.35rem 0.875rem; background: #fff; border: 1.5px solid #FECACA; color: #DC2626; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: inherit; }
.btn-danger-sm:hover { background: #FEF2F2; }
.btn-link { background: none; border: none; color: #7C3AED; font-size: 0.875rem; font-weight: 600; cursor: pointer; padding: 0; font-family: inherit; }

.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.modal-box { background: #fff; border-radius: 16px; padding: 1.75rem; width: 100%; max-width: 440px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.375rem; }
.modal-sub { font-size: 0.875rem; color: #6B7280; margin: 0; }
.modal-form { margin-top: 1.25rem; display: flex; flex-direction: column; gap: 0.875rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }

/* Transición */
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.2s ease; overflow: hidden; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; max-height: 0; }
.slide-down-enter-to, .slide-down-leave-from { opacity: 1; max-height: 1200px; }

/* Selector empresa */
.selector-wrap { position: relative; }
.selector-btn { display: inline-flex; align-items: center; gap: 0.625rem; padding: 0.55rem 0.875rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; font-family: inherit; min-width: 220px; }
.selector-btn.sin-sel { border-style: dashed; color: #9CA3AF; }
.selector-icono svg { width: 16px; height: 16px; color: #6B7280; }
.selector-texto { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left; }
.selector-chevron { width: 14px; height: 14px; color: #9CA3AF; }
.selector-dropdown { position: absolute; top: calc(100% + 6px); left: 0; min-width: 260px; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); z-index: 200; overflow: hidden; }
.dropdown-search { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem; border-bottom: 1px solid #F3F4F6; }
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; }
.dropdown-input { flex: 1; border: none; outline: none; font-size: 0.875rem; color: #111827; font-family: inherit; background: transparent; }
.dropdown-empty { padding: 1rem; font-size: 0.8125rem; color: #9CA3AF; text-align: center; }
.dropdown-option { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.625rem 0.875rem; background: none; border: none; font-size: 0.875rem; color: #374151; cursor: pointer; font-family: inherit; }
.dropdown-option:hover { background: #F5F3FF; }
.dropdown-option.selected { background: #EEF2FF; }
.dropdown-todos { border-bottom: 1px solid #F3F4F6; color: #6B7280; font-style: italic; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 199; }

/* Onboarding */
.onboarding-card { text-align: center; padding: 2.5rem 2rem; }
.onboarding-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.5rem; }
.onboarding-desc { font-size: 0.875rem; color: #6B7280; margin: 0 0 2rem; }
.onboarding-steps { display: flex; flex-direction: column; gap: 1rem; max-width: 420px; margin: 0 auto 2rem; text-align: left; }
.onboarding-step { display: flex; align-items: flex-start; gap: 1rem; }
.step-num { width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.step-num-pending { background: #E5E7EB; color: #9CA3AF; }
.step-info { display: flex; flex-direction: column; gap: 0.15rem; padding-top: 0.35rem; }
.step-info strong { font-size: 0.875rem; color: #111827; }
.step-info span { font-size: 0.8125rem; color: #6B7280; }

/* Badges de estado en asignaciones */
.asig-badge { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 999px; white-space: nowrap; }
.asig-badge-red { background: #FEE2E2; color: #B91C1C; }
.asig-badge-yellow { background: #FEF9C3; color: #92400E; }
.asig-badge-green { background: #D1FAE5; color: #065F46; }

/* ── Nuevo layout asignaciones ── */
.asig-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 1.5rem;
  align-items: flex-start;
}
@media (max-width: 900px) {
  .asig-layout { grid-template-columns: 1fr; }
}

.asig-vehiculos-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.625rem;
}
.asig-count {
  display: inline-block; font-size: 0.75rem; font-weight: 600;
  background: #EEF2FF; color: #4F46E5;
  padding: 0.1rem 0.5rem; border-radius: 999px; margin-left: 0.5rem;
}
.asig-quick-actions { display: flex; align-items: center; gap: 0.4rem; }

.asig-vehiculos-list {
  display: flex; flex-direction: column; gap: 4px;
  max-height: 360px; overflow-y: auto;
  border: 1.5px solid #E5E7EB; border-radius: 10px; padding: 6px;
  background: #FAFAFA;
}
.asig-vehiculo-item {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.5rem 0.75rem; border-radius: 8px;
  cursor: pointer; transition: background 0.12s; user-select: none;
}
.asig-vehiculo-item:hover { background: #F3F4F6; }
.asig-vehiculo-checked { background: #EEF2FF !important; }
.asig-checkbox { width: 16px; height: 16px; accent-color: #4F46E5; flex-shrink: 0; cursor: pointer; }
.asig-patente { font-weight: 700; font-size: 0.875rem; color: #111827; min-width: 72px; }
.asig-vehiculo-info { flex: 1; font-size: 0.8125rem; color: #6B7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.asig-badge-mini {
  font-size: 0.7rem; font-weight: 600; padding: 0.1rem 0.45rem;
  border-radius: 999px; background: #D1FAE5; color: #065F46; white-space: nowrap;
}

.asig-placeholder {
  display: flex; flex-direction: column; align-items: center; gap: 0.75rem;
  padding: 2rem 1rem; color: #9CA3AF; text-align: center;
}
.asig-placeholder svg { width: 40px; height: 40px; opacity: 0.4; }
.asig-placeholder p { font-size: 0.875rem; margin: 0; line-height: 1.5; }

.asig-panel-left .form-card { margin-bottom: 0; }
.mb-4 { margin-bottom: 1rem; }
.mt-4 { margin-top: 1rem; }
.w-full { width: 100%; }
</style>
