<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import { tienePermiso } from '../../utils/permisos.js'
import ConfirmModal from '../../components/ConfirmModal.vue'
import { usePaginacion } from '../../composables/usePaginacion.js'
import PaginacionTabla from '../../components/PaginacionTabla.vue'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const toast = useToast()

// ── Período ────────────────────────────────────────────────
const hoy     = new Date()
const mesSel  = ref(hoy.getMonth() + 1)
const anioSel = ref(hoy.getFullYear())
const meses   = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const anios   = Array.from({ length: 5 }, (_, i) => hoy.getFullYear() - i)

// ── Permisos ────────────────────────────────────────────────
const puedeCrear       = tienePermiso('finanzas.crear')
const puedeEditar      = tienePermiso('finanzas.editar')
const puedeEliminar    = tienePermiso('finanzas.eliminar')
const puedePresupuesto = tienePermiso('finanzas.presupuesto')
// Pestañas que muestran datos de OTROS módulos: solo si el plan los incluye.
const verMantencion    = tienePermiso('mantenciones.ver')
const verFlota         = tienePermiso('flotas.ver')
const router = useRouter()

// ── Tabs ────────────────────────────────────────────────────
const tabActivo = ref('resumen')
const tabs = computed(() => [
  { key: 'resumen',     label: 'Resumen' },
  { key: 'combustible', label: 'Combustible' },
  ...(verMantencion ? [{ key: 'mantencion', label: 'Mantención' }] : []),
  { key: 'multas',      label: 'Multas' },
  ...(verFlota ? [{ key: 'vehiculo', label: 'Por vehículo' }] : []),
  { key: 'servicio',    label: 'Pago de servicio' },
  ...(puedePresupuesto ? [{ key: 'presupuesto', label: 'Presupuesto' }] : []),
])

// ── Tiempo real ─────────────────────────────────────────────
const ultimaActualizacion = ref(null)
const tiempoLabel         = ref('')
let   intervalPolling     = null
let   intervalLabel       = null

function actualizarLabel() {
  if (!ultimaActualizacion.value) return
  const seg = Math.round((Date.now() - ultimaActualizacion.value) / 1000)
  tiempoLabel.value = seg < 60 ? `hace ${seg}s` : `hace ${Math.round(seg / 60)} min`
}

function onVisibilityChange() {
  if (!document.hidden && ultimaActualizacion.value) {
    if ((Date.now() - ultimaActualizacion.value) / 1000 >= 120) cargar()
  }
}

// ── Estado ─────────────────────────────────────────────────
const loading        = ref(false)
const gastos         = ref([])
const resumen        = ref(null)
const vehiculos      = ref([])
const conductores    = ref([])
const pagosServicio  = ref([])
const totalServicio  = ref(0)

// ── Modal gasto ────────────────────────────────────────────
const modalOpen   = ref(false)
const editandoId  = ref(null)
const guardando   = ref(false)
const form = ref({
  vehiculo_id:  '',
  conductor_id: '',
  categoria:    '',
  descripcion:  '',
  monto:        '',
  fecha:        hoy.toISOString().slice(0, 10),
  comprobante:  null,
})

// ── Confirm eliminar ────────────────────────────────────────
const confirmId  = ref(null)
const eliminando = ref(false)

// ── Tab vehículo seleccionado ───────────────────────────────
const vehiculoFiltro = ref('')

// ── Presupuesto ─────────────────────────────────────────────
const presupuestoForm  = ref({ monto: '' })
const guardandoPresup  = ref(false)
const presupuestoId    = ref(null)
const histPresupuesto  = ref([])

// ── Computed ────────────────────────────────────────────────
const categoriaTab = computed(() => {
  const map = { combustible: 'combustible', mantencion: 'mantencion', multas: ['multa', 'peaje'] }
  return map[tabActivo.value] || null
})

const gastosFiltrados = computed(() => {
  if (!categoriaTab.value) return gastos.value
  const cats = Array.isArray(categoriaTab.value) ? categoriaTab.value : [categoriaTab.value]
  return gastos.value.filter(g => cats.includes(g.categoria))
})

const gastosPorVehiculo = computed(() => {
  if (!vehiculoFiltro.value) return []
  const vid = parseInt(vehiculoFiltro.value)
  return gastos.value.filter(g => g.vehiculo_id === vid)
})

const { pagina: paginaGastos, totalPaginas: totalPaginasGastos, total: totalGastos, paginado: gastosFiltradosPaginados, irA: irAPaginaGastos } = usePaginacion(gastosFiltrados, 20)
const { pagina: paginaGastosVeh, totalPaginas: totalPaginasGastosVeh, total: totalGastosVeh, paginado: gastosPorVehiculoPaginados, irA: irAPaginaGastosVeh } = usePaginacion(gastosPorVehiculo, 20)

const breakdownVehiculo = computed(() => {
  const cats = {}
  for (const g of gastosPorVehiculo.value) {
    cats[g.categoria] = (cats[g.categoria] || 0) + g.monto
  }
  return Object.entries(cats).map(([cat, total]) => ({ cat, total }))
})

const presupuestoActual = computed(() => resumen.value?.presupuesto || null)

// ── Carga de datos ──────────────────────────────────────────
async function cargar() {
  loading.value = true
  try {
    const [gastosRes, vehRes, condRes] = await Promise.all([
      apiFetch(`/api/empresa/gastos/?mes=${mesSel.value}&anio=${anioSel.value}`),
      apiFetch('/api/empresa/vehiculos/'),
      apiFetch('/api/empresa/conductores/'),
    ])

    if (gastosRes.ok) {
      const data = await gastosRes.json()
      gastos.value         = data.gastos || []
      resumen.value        = data.resumen || null
      pagosServicio.value  = data.pagos_servicio || []
      totalServicio.value  = data.total_servicio || 0
      if (data.resumen?.presupuesto) {
        presupuestoId.value      = data.resumen.presupuesto.id
        presupuestoForm.value.monto = data.resumen.presupuesto.monto
      } else {
        presupuestoId.value         = null
        presupuestoForm.value.monto = ''
      }
    }

    if (vehRes.ok) {
      const d = await vehRes.json()
      vehiculos.value = Array.isArray(d) ? d : (d.vehiculos || d.results || [])
    }
    if (condRes.ok) {
      const d = await condRes.json()
      conductores.value = Array.isArray(d) ? d : (d.conductores || d.results || [])
    }

    await cargarHistPresupuesto()
  } catch {
    toast.error('Error al cargar los datos.')
  } finally {
    loading.value = false
    ultimaActualizacion.value = new Date()
    actualizarLabel()
    await nextTick()
    crearTendenciaChart()
    crearDonutCat()
  }
}

async function cargarHistPresupuesto() {
  const res = await apiFetch(`/api/empresa/presupuesto/?anio=${anioSel.value}`)
  if (res.ok) {
    histPresupuesto.value = await res.json()
  }
}

watch([mesSel, anioSel], cargar)

onMounted(() => {
  cargar()
  intervalPolling = setInterval(() => { if (!document.hidden) cargar() }, 120_000)
  intervalLabel   = setInterval(actualizarLabel, 10_000)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  clearInterval(intervalPolling)
  clearInterval(intervalLabel)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  if (tendenciaChart) tendenciaChart.destroy()
  if (donutCatChart)  donutCatChart.destroy()
})

// ── Formateo ────────────────────────────────────────────────
function clp(val) {
  if (val == null) return '—'
  return '$' + Number(val).toLocaleString('es-CL')
}

function fechaDisplay(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const COLORES_CAT = {
  combustible: '#F59E0B',
  mantencion:  '#3B82F6',
  multa:       '#EF4444',
  peaje:       '#8B5CF6',
  seguro:      '#10B981',
  otro:        '#6B7280',
}
const LABEL_CAT = {
  combustible: 'Combustible',
  mantencion:  'Mantención',
  multa:       'Multa',
  peaje:       'Peaje',
  seguro:      'Seguro',
  otro:        'Otro',
}

function colorCat(cat) { return COLORES_CAT[cat] || '#6B7280' }
function labelCat(cat)  { return LABEL_CAT[cat] || cat }

function pctPresup(val) {
  return presupuestoActual.value
    ? Math.min(100, Math.round(val / presupuestoActual.value.monto * 100))
    : 0
}

function colorPresup(pct) {
  if (pct > 100) return '#DC2626'
  if (pct > 80)  return '#F59E0B'
  return '#10B981'
}

// ── Modal ────────────────────────────────────────────────────
function abrirNuevo() {
  editandoId.value = null
  form.value = {
    vehiculo_id: '', conductor_id: '', categoria: '',
    descripcion: '', monto: '',
    fecha: hoy.toISOString().slice(0, 10), comprobante: null,
  }
  modalOpen.value = true
}

function abrirEditar(g) {
  editandoId.value = g.id
  form.value = {
    vehiculo_id:  g.vehiculo_id || '',
    conductor_id: g.conductor_id || '',
    categoria:    g.categoria,
    descripcion:  g.descripcion,
    monto:        g.monto,
    fecha:        g.fecha,
    comprobante:  null,
  }
  modalOpen.value = true
}

function onFile(e) {
  form.value.comprobante = e.target.files[0] || null
}

async function guardarGasto() {
  if (!form.value.vehiculo_id || !form.value.categoria || !form.value.monto || !form.value.fecha || !form.value.descripcion) {
    toast.error('Completa todos los campos requeridos.')
    return
  }
  if (Number(form.value.monto) <= 0) {
    toast.error('El monto debe ser mayor a 0.')
    return
  }

  guardando.value = true
  try {
    let body, headers = {}

    if (form.value.comprobante) {
      const fd = new FormData()
      fd.append('vehiculo_id',  form.value.vehiculo_id)
      if (form.value.conductor_id) fd.append('conductor_id', form.value.conductor_id)
      fd.append('categoria',   form.value.categoria)
      fd.append('descripcion', form.value.descripcion)
      fd.append('monto',       form.value.monto)
      fd.append('fecha',       form.value.fecha)
      fd.append('comprobante', form.value.comprobante)
      body = fd
    } else {
      body = {
        vehiculo_id:  form.value.vehiculo_id,
        conductor_id: form.value.conductor_id || null,
        categoria:    form.value.categoria,
        descripcion:  form.value.descripcion,
        monto:        form.value.monto,
        fecha:        form.value.fecha,
      }
    }

    const url    = editandoId.value ? `/api/empresa/gastos/${editandoId.value}/` : '/api/empresa/gastos/'
    const method = editandoId.value ? 'PUT' : 'POST'
    const res    = await apiFetch(url, { method, body })

    if (res.ok) {
      toast.success(editandoId.value ? 'Gasto actualizado.' : 'Gasto registrado.')
      modalOpen.value = false
      await cargar()
    } else {
      const err = await res.json()
      toast.error(err.error || 'Error al guardar el gasto.')
    }
  } catch {
    toast.error('Error de conexión.')
  } finally {
    guardando.value = false
  }
}

async function eliminarGasto() {
  if (!confirmId.value) return
  eliminando.value = true
  try {
    const res = await apiFetch(`/api/empresa/gastos/${confirmId.value}/`, { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      toast.success('Gasto eliminado.')
      confirmId.value = null
      await cargar()
    } else {
      const err = await res.json()
      toast.error(err.error || 'Error al eliminar.')
    }
  } catch {
    toast.error('Error de conexión.')
  } finally {
    eliminando.value = false
  }
}

// ── Presupuesto ─────────────────────────────────────────────
async function guardarPresupuesto() {
  if (!presupuestoForm.value.monto || Number(presupuestoForm.value.monto) <= 0) {
    toast.error('Ingresa un monto válido.')
    return
  }
  guardandoPresup.value = true
  try {
    const body = { mes: mesSel.value, anio: anioSel.value, monto: presupuestoForm.value.monto }
    const url = presupuestoId.value
      ? `/api/empresa/presupuesto/${presupuestoId.value}/`
      : '/api/empresa/presupuesto/'
    const method = presupuestoId.value ? 'PUT' : 'POST'
    const res = await apiFetch(url, { method, body })
    if (res.ok) {
      toast.success('Presupuesto guardado.')
      await cargar()
    } else {
      const err = await res.json()
      toast.error(err.error || 'Error al guardar.')
    }
  } catch {
    toast.error('Error de conexión.')
  } finally {
    guardandoPresup.value = false
  }
}

// ── Barras historial presupuesto ────────────────────────────
function alturaBarraPresup(monto, datos) {
  const max = Math.max(...datos.map(d => d.monto || 0), 1)
  return Math.round(monto / max * 100)
}

// ── Tendencia 6 meses ────────────────────────────────────────
const tendenciaCanvas = ref(null)
let tendenciaChart = null

// ── Doughnut categorías ──────────────────────────────────────
const donutCatCanvas = ref(null)
let donutCatChart = null

function clpTick(v) { return v >= 1_000_000 ? '$' + (v / 1_000_000).toFixed(1) + 'M' : v >= 1_000 ? '$' + Math.round(v / 1_000) + 'k' : '$' + v }

function crearTendenciaChart() {
  const tendencia = resumen.value?.tendencia_6meses
  if (!tendenciaCanvas.value || !tendencia?.length) return
  if (tendenciaChart) { tendenciaChart.destroy(); tendenciaChart = null }

  tendenciaChart = new Chart(tendenciaCanvas.value, {
    type: 'line',
    data: {
      labels: tendencia.map(t => t.label),
      datasets: [{
        label: 'Gastos',
        data: tendencia.map(t => t.total),
        borderColor: '#4F46E5',
        backgroundColor: 'rgba(79,70,229,0.07)',
        borderWidth: 2.5,
        pointBackgroundColor: '#4F46E5',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        tension: 0.35,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${clp(ctx.parsed.y)}` } },
      },
      scales: {
        x: { grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 }, color: '#9CA3AF' } },
        y: { grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 }, color: '#9CA3AF', callback: clpTick } },
      },
    },
  })
}

watch(tabActivo, async (nuevo) => {
  if (nuevo === 'resumen') {
    await nextTick()
    crearTendenciaChart()
    crearDonutCat()
  }
})

function crearDonutCat() {
  const pc = resumen.value?.por_categoria
  if (!donutCatCanvas.value || !pc) return
  if (donutCatChart) { donutCatChart.destroy(); donutCatChart = null }
  const COLORES = ['#3B82F6', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#94A3B8']
  const entradas = Object.entries(pc).filter(([, v]) => v > 0)
  donutCatChart = new Chart(donutCatCanvas.value, {
    type: 'doughnut',
    data: {
      labels: entradas.map(([k]) => labelCat(k)),
      datasets: [{
        data: entradas.map(([, v]) => v),
        backgroundColor: COLORES.slice(0, entradas.length),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } },
        tooltip: { callbacks: { label: (c) => ` ${labelCat(c.label)}: ${clp(c.parsed)}` } },
      },
    },
  })
}
watch(resumen, async () => { await nextTick(); crearDonutCat() }, { deep: true })

// ── Variación mes anterior ────────────────────────────────────
const variacion = computed(() => resumen.value?.variacion_mes_anterior || null)

function varBadgeStyle(pct) {
  if (pct == null) return {}
  return pct > 0
    ? { background: '#FEF2F2', color: '#DC2626' }
    : { background: '#ECFDF5', color: '#059669' }
}

// ── Alerta presupuesto ────────────────────────────────────────
const alertaPresup = computed(() => {
  if (!presupuestoActual.value) return null
  const pct = presupuestoActual.value.utilizado_pct
  if (pct >= 100) return { nivel: 'danger', pct, texto: `Has superado el presupuesto mensual (${pct}% ejecutado).` }
  if (pct >= 80)  return { nivel: 'warn',   pct, texto: `Llevas el ${pct}% del presupuesto mensual consumido.` }
  return null
})

// ── Gasto por conductor ───────────────────────────────────────
const porConductor = computed(() => resumen.value?.por_conductor || [])
</script>

<template>
  <div class="page">
    <!-- Encabezado -->
    <div class="header">
      <div>
        <h1 class="titulo">Finanzas</h1>
        <p class="subtitulo">Gestión de gastos operativos de tu flota</p>
      </div>
      <div class="header-actions">
        <!-- Selector período -->
        <div class="periodo">
          <select v-model="mesSel" class="sel">
            <option v-for="(m, i) in meses" :key="i" :value="i + 1">{{ m }}</option>
          </select>
          <select v-model="anioSel" class="sel">
            <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>
        <div class="refresh-bar">
          <span v-if="tiempoLabel" class="refresh-label">Actualizado {{ tiempoLabel }}</span>
          <button class="btn-refresh" @click="cargar" :disabled="loading" title="Actualizar datos">
            <svg :class="{ 'spin': loading }" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0
                   0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>
        <button v-if="puedeCrear" class="btn-nuevo" @click="abrirNuevo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          Registrar gasto
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <div class="spinner"></div>
      <span>Cargando datos...</span>
    </div>

    <template v-else>
      <!-- KPIs -->
      <div class="kpis" v-if="resumen">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ clp((resumen.total || 0) + (resumen.total_correctivos_mes || 0)) }}</span>
              <span v-if="variacion?.variacion_pct != null" class="var-badge" :style="varBadgeStyle(variacion.variacion_pct)">
                {{ variacion.variacion_pct > 0 ? '+' : '' }}{{ variacion.variacion_pct }}%
              </span>
            </div>
            <div class="kpi-label">Gasto total del mes</div>
            <p v-if="resumen.tiene_correctivos" class="aviso-correctivo">
              <i class="ti ti-alert-triangle"/>
              incluye {{ clp(resumen.total_correctivos_mes) }} en correctivos
              <button @click="router.push('/empresa/correctivos')">Ver →</button>
            </p>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon" style="background:#ECFDF5;color:#059669">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
          </div>
          <div>
            <div class="kpi-value">{{ resumen.costo_por_km != null ? clp(resumen.costo_por_km) + '/km' : '—' }}</div>
            <div class="kpi-label">Costo por km</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FEF3C7;color:#D97706">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/></svg>
          </div>
          <div>
            <div class="kpi-value">
              {{ resumen.por_vehiculo?.length > 0 ? clp(Math.max(...resumen.por_vehiculo.map(v => v.total))) : '—' }}
            </div>
            <div class="kpi-label">Vehículo más costoso</div>
          </div>
        </div>

        <div class="kpi-card" :class="{ 'kpi-warn': presupuestoActual && presupuestoActual.utilizado_pct > 80, 'kpi-danger': presupuestoActual && presupuestoActual.utilizado_pct > 100 }">
          <div class="kpi-icon" style="background:#F3F4F6;color:#6B7280">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
          </div>
          <div style="flex:1">
            <div class="kpi-value">
              <template v-if="presupuestoActual">{{ presupuestoActual.utilizado_pct }}%</template>
              <template v-else><span style="font-size:0.9rem;color:#6B7280">Sin presupuesto</span></template>
            </div>
            <div class="kpi-label">Presupuesto utilizado</div>
            <div v-if="presupuestoActual" class="presup-bar-wrap">
              <div class="presup-bar" :style="{ width: Math.min(100, presupuestoActual.utilizado_pct) + '%', background: colorPresup(presupuestoActual.utilizado_pct) }"></div>
            </div>
            <button v-else class="btn-definir" @click="tabActivo = 'presupuesto'">Definir →</button>
          </div>
        </div>

        <div class="kpi-card kpi-servicio" @click="tabActivo = 'servicio'" style="cursor:pointer">
          <div class="kpi-icon" style="background:#F0FDF4;color:#16A34A">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
          </div>
          <div>
            <div class="kpi-value" style="color:#16A34A">{{ clp(totalServicio) }}</div>
            <div class="kpi-label">Pago de servicio</div>
          </div>
        </div>
      </div>

      <!-- Alerta presupuesto -->
      <div v-if="alertaPresup" :class="['alerta-presup', alertaPresup.nivel]">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        </svg>
        <span>{{ alertaPresup.texto }}</span>
        <button v-if="puedePresupuesto" class="alerta-btn" @click="tabActivo = 'presupuesto'">Ver presupuesto →</button>
      </div>

      <!-- Tabs -->
      <div class="tabs-wrap">
        <button v-for="t in tabs" :key="t.key"
          :class="['tab-btn', tabActivo === t.key && 'tab-active']"
          @click="tabActivo = t.key">
          {{ t.label }}
        </button>
      </div>

      <!-- ═══ TAB RESUMEN ═══ -->
      <div v-if="tabActivo === 'resumen'" class="tab-content">
        <div class="grid-2">
          <!-- Distribución por categoría -->
          <div class="card">
            <div class="card-head"><h3 class="card-title">Distribución de gastos</h3></div>
            <div class="card-body">
              <div v-if="!resumen?.total" class="empty-msg">Sin gastos en este período.</div>
              <template v-else>
                <div v-for="(monto, cat) in resumen.por_categoria" :key="cat" class="cat-row">
                  <div class="cat-info">
                    <span class="cat-dot" :style="{ background: colorCat(cat) }"></span>
                    <span class="cat-label">{{ labelCat(cat) }}</span>
                  </div>
                  <div class="cat-bar-wrap">
                    <div class="cat-bar" :style="{ width: Math.round(monto / resumen.total * 100) + '%', background: colorCat(cat) }"></div>
                  </div>
                  <div class="cat-vals">
                    <span>{{ clp(monto) }}</span>
                    <span class="cat-pct">{{ Math.round(monto / resumen.total * 100) }}%</span>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Top vehículos (solo si el plan incluye flota) -->
          <div class="card" v-if="verFlota">
            <div class="card-head"><h3 class="card-title">Top vehículos por gasto</h3></div>
            <div v-if="!resumen?.por_vehiculo?.length" class="card-body">
              <p class="empty-msg">Sin datos.</p>
            </div>
            <table v-else class="tabla">
              <thead><tr><th>#</th><th>Patente</th><th>Total</th><th></th></tr></thead>
              <tbody>
                <tr v-for="(v, i) in resumen.por_vehiculo.slice(0, 5)" :key="v.vehiculo_id"
                    class="tabla-row" @click="tabActivo = 'vehiculo'; vehiculoFiltro = String(v.vehiculo_id)">
                  <td><span class="rank">{{ i + 1 }}</span></td>
                  <td class="font-medium">{{ v.patente }}</td>
                  <td>{{ clp(v.total) }}</td>
                  <td>
                    <div class="mini-bar-wrap">
                      <div class="mini-bar" :style="{ width: Math.round(v.total / resumen.por_vehiculo[0].total * 100) + '%' }"></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tendencia + Doughnut en grid -->
        <div class="grid-2 mt-4">
          <div class="card" v-if="resumen?.tendencia_6meses?.length">
            <div class="card-head"><h3 class="card-title">Tendencia de gastos — últimos 6 meses</h3></div>
            <div class="card-body">
              <div class="chart-tendencia">
                <canvas ref="tendenciaCanvas"></canvas>
              </div>
            </div>
          </div>
          <div class="card" v-if="resumen?.por_categoria && resumen?.total">
            <div class="card-head"><h3 class="card-title">Distribución por categoría</h3></div>
            <div class="card-body">
              <div style="height:220px">
                <canvas ref="donutCatCanvas"></canvas>
              </div>
            </div>
          </div>
        </div>

        <!-- Gasto por conductor -->
        <div v-if="porConductor.length" class="card mt-4">
          <div class="card-head"><h3 class="card-title">Gasto por conductor</h3></div>
          <table class="tabla">
            <thead>
              <tr><th>#</th><th>Conductor</th><th>Total</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in porConductor" :key="c.conductor_id || i">
                <td><span class="rank">{{ i + 1 }}</span></td>
                <td class="font-medium">{{ c.nombre || 'Sin conductor' }}</td>
                <td class="font-medium">{{ clp(c.total) }}</td>
                <td>
                  <div class="mini-bar-wrap">
                    <div class="mini-bar" :style="{ width: Math.round(c.total / porConductor[0].total * 100) + '%' }"></div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Últimos registros -->
        <div class="card mt-4">
          <div class="card-head">
            <h3 class="card-title">Últimos registros</h3>
            <button v-if="puedeCrear" class="btn-primary-sm" @click="abrirNuevo">+ Registrar</button>
          </div>
          <div v-if="!gastos.length" class="card-body"><p class="empty-msg">Sin gastos en este período.</p></div>
          <table v-else class="tabla">
            <thead>
              <tr><th>Fecha</th><th>Vehículo</th><th>Categoría</th><th>Descripción</th><th>Conductor</th><th>Monto</th><th>Comp.</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="g in gastos.slice(0, 10)" :key="g.id">
                <td>{{ fechaDisplay(g.fecha) }}</td>
                <td>{{ g.vehiculo || '—' }}</td>
                <td><span class="badge-cat" :style="{ background: colorCat(g.categoria) + '22', color: colorCat(g.categoria) }">{{ labelCat(g.categoria) }}</span></td>
                <td class="td-desc">{{ g.descripcion }}</td>
                <td>{{ g.conductor || '—' }}</td>
                <td class="font-medium">{{ clp(g.monto) }}</td>
                <td>
                  <a v-if="g.comprobante" :href="g.comprobante" target="_blank" class="btn-icon" title="Ver comprobante">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
                  </a>
                  <span v-else class="sin-comp">—</span>
                </td>
                <td>
                  <div class="acciones-row">
                    <button v-if="puedeEditar && !g.readonly" class="btn-icon" @click="abrirEditar(g)" title="Editar">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
                    </button>
                    <button v-if="puedeEliminar && !g.readonly" class="btn-icon btn-danger-icon" @click="confirmId = g.id" title="Eliminar">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                    <span v-if="g.readonly" class="badge-mant" title="Registrado desde Mantenciones">Mantención</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ═══ TABS POR CATEGORÍA ═══ -->
      <div v-else-if="['combustible', 'mantencion', 'multas'].includes(tabActivo)" class="tab-content">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">{{ tabs.find(t => t.key === tabActivo)?.label }}</h3>
            <div class="card-meta">
              <span class="total-cat">Total: {{ clp(gastosFiltrados.reduce((s, g) => s + g.monto, 0)) }}</span>
            </div>
          </div>
          <div v-if="!gastosFiltrados.length" class="card-body"><p class="empty-msg">Sin gastos en esta categoría para el período.</p></div>
          <table v-else class="tabla">
            <thead>
              <tr><th>Fecha</th><th>Vehículo</th><th>Descripción</th><th>Conductor</th><th>Monto</th><th>Comp.</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="g in gastosFiltradosPaginados" :key="g.id">
                <td>{{ fechaDisplay(g.fecha) }}</td>
                <td>{{ g.vehiculo || '—' }}</td>
                <td class="td-desc">{{ g.descripcion }}</td>
                <td>{{ g.conductor || '—' }}</td>
                <td class="font-medium">{{ clp(g.monto) }}</td>
                <td>
                  <a v-if="g.comprobante" :href="g.comprobante" target="_blank" class="btn-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
                  </a>
                  <span v-else>—</span>
                </td>
                <td>
                  <div class="acciones-row">
                    <button v-if="puedeEditar && !g.readonly" class="btn-icon" @click="abrirEditar(g)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
                    </button>
                    <button v-if="puedeEliminar && !g.readonly" class="btn-icon btn-danger-icon" @click="confirmId = g.id">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                    <span v-if="g.readonly" class="badge-mant" title="Registrado desde Mantenciones">Mantención</span>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="4" class="foot-label">Total</td>
                <td class="font-medium">{{ clp(gastosFiltrados.reduce((s, g) => s + g.monto, 0)) }}</td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          </table>
          <PaginacionTabla :pagina="paginaGastos" :total-paginas="totalPaginasGastos" :total="totalGastos"
            @update:pagina="irAPaginaGastos" />
        </div>
      </div>


      <!-- ═══ TAB POR VEHÍCULO ═══ -->
      <div v-else-if="tabActivo === 'vehiculo'" class="tab-content">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Por vehículo</h3>
            <select v-model="vehiculoFiltro" class="sel">
              <option value="">Selecciona un vehículo</option>
              <option v-for="v in vehiculos" :key="v.id" :value="String(v.id)">
                {{ v.patente }} — {{ v.marca }} {{ v.modelo }}
              </option>
            </select>
          </div>

          <div v-if="!vehiculoFiltro" class="card-body"><p class="empty-msg">Selecciona un vehículo para ver sus gastos.</p></div>

          <template v-else>
            <div class="card-body">
              <div class="breakdown-grid">
                <div v-for="item in breakdownVehiculo" :key="item.cat" class="breakdown-item">
                  <span class="cat-dot" :style="{ background: colorCat(item.cat) }"></span>
                  <span class="cat-label">{{ labelCat(item.cat) }}</span>
                  <span class="font-medium ml-auto">{{ clp(item.total) }}</span>
                </div>
                <div class="breakdown-total">
                  <span>Total</span>
                  <span class="font-medium ml-auto">{{ clp(gastosPorVehiculo.reduce((s, g) => s + g.monto, 0)) }}</span>
                </div>
              </div>
            </div>

            <!-- Historial barras (6 meses sin librería) -->
            <div v-if="resumen?.costo_por_km" class="kpi-inline">
              Costo por km del mes: <strong>{{ clp(resumen.costo_por_km) }}/km</strong>
            </div>

            <div v-if="!gastosPorVehiculo.length" class="card-body"><p class="empty-msg">Sin gastos para este vehículo en el período.</p></div>
            <template v-else>
              <table class="tabla">
                <thead><tr><th>Fecha</th><th>Categoría</th><th>Descripción</th><th>Conductor</th><th>Monto</th></tr></thead>
                <tbody>
                  <tr v-for="g in gastosPorVehiculoPaginados" :key="g.id">
                    <td>{{ fechaDisplay(g.fecha) }}</td>
                    <td><span class="badge-cat" :style="{ background: colorCat(g.categoria) + '22', color: colorCat(g.categoria) }">{{ labelCat(g.categoria) }}</span></td>
                    <td class="td-desc">{{ g.descripcion }}</td>
                    <td>{{ g.conductor || '—' }}</td>
                    <td class="font-medium">{{ clp(g.monto) }}</td>
                  </tr>
                </tbody>
              </table>
              <PaginacionTabla :pagina="paginaGastosVeh" :total-paginas="totalPaginasGastosVeh" :total="totalGastosVeh"
                @update:pagina="irAPaginaGastosVeh" />
            </template>
          </template>
        </div>
      </div>

      <!-- ═══ TAB PAGO DE SERVICIO ═══ -->
      <div v-else-if="tabActivo === 'servicio'" class="tab-content">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Pagos de servicio</h3>
            <div class="card-meta">
              <span class="total-cat">Total del período: {{ clp(totalServicio) }}</span>
            </div>
          </div>

          <div v-if="!pagosServicio.length" class="card-body">
            <p class="empty-msg">Sin pagos de servicio en este período.</p>
          </div>

          <table v-else class="tabla">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Plan</th>
                <th>Ciclo</th>
                <th>Método</th>
                <th>N° Orden</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in pagosServicio" :key="p.id">
                <td>{{ fechaDisplay(p.fecha) }}</td>
                <td class="font-medium">{{ p.plan }}</td>
                <td>
                  <span class="badge-ciclo" :class="p.ciclo === 'anual' ? 'anual' : 'mensual'">
                    {{ p.ciclo === 'anual' ? 'Anual' : 'Mensual' }}
                  </span>
                </td>
                <td>
                  <div class="metodo-cell">
                    <span class="metodo-icon">{{ p.via === 'manual' ? '🏦' : '💳' }}</span>
                    <span>{{ p.metodo }}</span>
                  </div>
                </td>
                <td class="orden-cell">{{ p.orden || '—' }}</td>
                <td class="font-medium servicio-monto">{{ clp(p.monto) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="5" class="foot-label">Total</td>
                <td class="font-medium">{{ clp(totalServicio) }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- ═══ TAB PRESUPUESTO ═══ -->
      <div v-else-if="tabActivo === 'presupuesto'" class="tab-content">
        <div class="grid-2">
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Presupuesto — {{ meses[mesSel - 1] }} {{ anioSel }}</h3>
            </div>
            <div class="card-body">
              <div class="field">
                <label class="label">Monto presupuestado (CLP)</label>
                <input v-model="presupuestoForm.monto" type="number" min="1" step="1000" class="input" placeholder="Ej: 5000000" />
              </div>

              <div v-if="presupuestoActual" class="presup-info">
                <div class="presup-row">
                  <span>Gastado</span>
                  <span class="font-medium">{{ clp(resumen?.total) }}</span>
                </div>
                <div class="presup-row">
                  <span>Presupuestado</span>
                  <span class="font-medium">{{ clp(presupuestoActual.monto) }}</span>
                </div>
                <div class="presup-row">
                  <span>Ejecución</span>
                  <span :style="{ color: colorPresup(presupuestoActual.utilizado_pct), fontWeight: 600 }">{{ presupuestoActual.utilizado_pct }}%</span>
                </div>
                <div class="presup-bar-wrap lg">
                  <div class="presup-bar" :style="{ width: Math.min(100, presupuestoActual.utilizado_pct) + '%', background: colorPresup(presupuestoActual.utilizado_pct) }"></div>
                </div>
              </div>

              <button class="btn-primary-sm mt-3" @click="guardarPresupuesto" :disabled="guardandoPresup">
                {{ guardandoPresup ? 'Guardando...' : (presupuestoId ? 'Actualizar presupuesto' : 'Definir presupuesto') }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </template>

    <!-- ═══ Modal gasto ═══ -->
    <Teleport to="body">
      <div v-if="modalOpen" class="overlay" @click.self="modalOpen = false">
        <div class="modal">
          <div class="modal-head">
            <h3>{{ editandoId ? 'Editar gasto' : 'Registrar gasto' }}</h3>
            <button class="btn-close" @click="modalOpen = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="field">
              <label class="label">Vehículo *</label>
              <select v-model="form.vehiculo_id" class="input">
                <option value="">Selecciona un vehículo</option>
                <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} — {{ v.marca }} {{ v.modelo }}</option>
              </select>
            </div>
            <div class="grid-2-modal">
              <div class="field">
                <label class="label">Categoría *</label>
                <select v-model="form.categoria" class="input">
                  <option value="">Selecciona</option>
                  <option value="combustible">Combustible</option>
                  <option value="mantencion">Mantención</option>
                  <option value="multa">Multa</option>
                  <option value="peaje">Peaje</option>
                  <option value="seguro">Seguro</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
              <div class="field">
                <label class="label">Fecha *</label>
                <input v-model="form.fecha" type="date" :max="new Date().toISOString().slice(0, 10)" class="input" />
              </div>
            </div>
            <div class="field">
              <label class="label">Descripción *</label>
              <input v-model="form.descripcion" type="text" class="input" placeholder="Descripción del gasto" maxlength="300" />
            </div>
            <div class="grid-2-modal">
              <div class="field">
                <label class="label">Monto (CLP) *</label>
                <input v-model="form.monto" type="number" min="1" step="100" class="input" placeholder="0" />
              </div>
              <div class="field">
                <label class="label">Conductor</label>
                <select v-model="form.conductor_id" class="input">
                  <option value="">Sin conductor</option>
                  <option v-for="c in conductores" :key="c.id" :value="c.id">{{ c.nombre || c.email }}</option>
                </select>
              </div>
            </div>
            <div class="field">
              <label class="label">Comprobante</label>
              <input type="file" accept="image/*,.pdf" @change="onFile" class="input-file" />
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn-cancel" @click="modalOpen = false">Cancelar</button>
            <button class="btn-primary-sm" @click="guardarGasto" :disabled="guardando">
              {{ guardando ? 'Guardando...' : (editandoId ? 'Actualizar' : 'Registrar') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ═══ Confirm eliminar ═══ -->
    <ConfirmModal
      v-if="confirmId"
      titulo="¿Eliminar gasto?"
      mensaje="Esta acción no se puede deshacer. El comprobante también será eliminado."
      labelOk="Eliminar"
      :peligroso="true"
      @confirmar="eliminarGasto"
      @cancelar="confirmId = null"
    />
  </div>
</template>

<style scoped>
.page { padding: 1.5rem 2rem; max-width: 1400px; }

.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap; }
.titulo { font-size: 1.5rem; font-weight: 800; color: #111827; margin: 0 0 0.2rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }

.periodo { display: flex; gap: 0.4rem; }
.sel { padding: 0.4rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.8rem; background: #fff; color: #374151; cursor: pointer; }

.btn-nuevo { display: flex; align-items: center; gap: 0.4rem; padding: 0.45rem 1rem; background: var(--color-accent, #4F46E5); color: #fff; border: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; }
.btn-nuevo svg { width: 15px; height: 15px; }
.refresh-bar  { display: flex; align-items: center; gap: 0.5rem; }
.refresh-label { font-size: 0.75rem; color: #9CA3AF; white-space: nowrap; }
.btn-refresh  { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; border: 1.5px solid #E5E7EB; background: #fff; color: #6B7280; cursor: pointer; transition: all 0.15s; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-accent, #4F46E5); color: var(--color-accent, #4F46E5); }
.btn-refresh:disabled { opacity: 0.5; cursor: default; }
.btn-refresh svg { width: 15px; height: 15px; }
.btn-export { display: flex; align-items: center; gap: 0.4rem; padding: 0.45rem 0.9rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.8rem; font-weight: 500; color: #374151; cursor: pointer; }
.btn-export svg { width: 14px; height: 14px; }
.btn-export:hover { border-color: var(--color-accent, #4F46E5); color: var(--color-accent, #4F46E5); }

.loading-wrap { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; padding: 3rem 0; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: var(--color-accent, #4F46E5); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* KPIs */
.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.1rem 1.25rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-card.kpi-warn { border-color: #FDE68A; background: #FFFBEB; }
.kpi-card.kpi-danger { border-color: #FECACA; background: #FEF2F2; }
.kpi-icon { width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.kpi-icon svg { width: 22px; height: 22px; }
.kpi-value { font-size: 1.35rem; font-weight: 700; color: #111827; line-height: 1.1; }
.kpi-label { font-size: 0.775rem; color: #6B7280; margin-top: 0.2rem; }
.aviso-correctivo { display: flex; align-items: center; gap: 0.3rem; font-size: 0.7rem; color: #DC2626; margin: 0.3rem 0 0; }
.aviso-correctivo button { font-size: 0.65rem; text-decoration: underline; background: none; border: none; cursor: pointer; color: #DC2626; padding: 0; }

.presup-bar-wrap { height: 4px; background: #F3F4F6; border-radius: 2px; margin-top: 0.4rem; overflow: hidden; }
.presup-bar-wrap.lg { height: 8px; border-radius: 4px; margin-top: 0.5rem; }
.presup-bar { height: 100%; border-radius: inherit; transition: width 0.4s; }
.btn-definir { font-size: 0.75rem; font-weight: 600; color: var(--color-accent, #4F46E5); background: none; border: none; cursor: pointer; padding: 0; margin-top: 0.3rem; }

/* Tabs */
.tabs-wrap { display: flex; gap: 0.2rem; background: #F3F4F6; border-radius: 10px; padding: 0.3rem; margin-bottom: 1.25rem; width: fit-content; flex-wrap: wrap; }
.tab-btn { padding: 0.35rem 0.85rem; border-radius: 7px; border: none; font-size: 0.825rem; font-weight: 600; color: #6B7280; background: transparent; cursor: pointer; transition: all 0.15s; }
.tab-active { background: #fff; color: var(--color-accent, #4F46E5); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }

/* Cards */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; gap: 0.75rem; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.card-body { padding: 1.25rem; }
.card-meta { font-size: 0.875rem; color: #6B7280; }
.total-cat { font-weight: 600; color: #111827; }
.mt-4 { margin-top: 1rem; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

/* Categorías */
.cat-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
.cat-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.cat-info { display: flex; align-items: center; gap: 0.5rem; width: 130px; flex-shrink: 0; }
.cat-label { font-size: 0.8rem; color: #374151; }
.cat-bar-wrap { flex: 1; height: 6px; background: #F3F4F6; border-radius: 3px; overflow: hidden; }
.cat-bar { height: 100%; border-radius: 3px; transition: width 0.4s; }
.cat-vals { display: flex; gap: 0.5rem; align-items: center; width: 130px; justify-content: flex-end; font-size: 0.8rem; }
.cat-pct { color: #9CA3AF; font-size: 0.75rem; }

/* Tablas */
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.tabla tr:last-child td { border-bottom: none; }
.tabla-row { cursor: pointer; }
.tabla-row:hover td { background: #FAFAFA; }
.tabla tfoot td { font-weight: 600; color: #111827; border-top: 1px solid #E5E7EB; background: #F9FAFB; }
.foot-label { color: #6B7280; }
.td-desc { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.font-medium { font-weight: 600; color: #111827; }
.rank { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: #EEF2FF; color: #4338CA; font-size: 0.7rem; font-weight: 700; }

.mini-bar-wrap { width: 80px; height: 5px; background: #F3F4F6; border-radius: 3px; overflow: hidden; }
.mini-bar { height: 100%; background: var(--color-accent, #4F46E5); border-radius: 3px; }

/* Badges */
.badge-cat { padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }

/* Botones acción */
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 7px; border: 1.5px solid #E5E7EB; background: #fff; color: #6B7280; cursor: pointer; }
.btn-icon svg { width: 14px; height: 14px; }
.btn-icon:hover { border-color: var(--color-accent, #4F46E5); color: var(--color-accent, #4F46E5); }
.btn-danger-icon:hover { border-color: #DC2626 !important; color: #DC2626 !important; }
.sin-comp { color: #9CA3AF; }
.acciones-row { display: flex; gap: 0.4rem; align-items: center; }
.badge-mant { font-size: 0.7rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 999px; background: #EEF2FF; color: #4338CA; white-space: nowrap; }

.btn-primary-sm { padding: 0.45rem 1rem; background: var(--color-accent, #4F46E5); color: #fff; border: none; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary-sm:hover { opacity: 0.9; }
.btn-primary-sm:disabled { opacity: 0.5; cursor: default; }
.mt-3 { margin-top: 0.75rem; display: block; }

/* Por vehículo */
.breakdown-grid { display: flex; flex-direction: column; gap: 0.6rem; }
.breakdown-item { display: flex; align-items: center; gap: 0.6rem; font-size: 0.875rem; }
.breakdown-total { display: flex; align-items: center; gap: 0.6rem; font-size: 0.875rem; font-weight: 700; border-top: 1px solid #E5E7EB; padding-top: 0.6rem; margin-top: 0.25rem; }
.ml-auto { margin-left: auto; }
.kpi-inline { padding: 0.75rem 1.25rem; background: #F9FAFB; font-size: 0.875rem; color: #374151; border-top: 1px solid #F3F4F6; }

/* Presupuesto */
.presup-info { background: #F9FAFB; border-radius: 10px; padding: 1rem; margin-top: 0.75rem; }
.presup-row { display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 0.5rem; color: #374151; }

/* Barras comparativas */
.barras-comparativas { display: flex; gap: 0.75rem; align-items: flex-end; height: 140px; position: relative; }
.barra-mes { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; flex: 1; height: 100%; }
.barra-col { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; width: 100%; height: 100%; }
.barra-bg { flex: 1; width: 100%; background: #F3F4F6; border-radius: 4px; display: flex; align-items: flex-end; overflow: hidden; }
.barra-fill { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.4s; }
.barra-fill.azul { background: var(--color-accent, #4F46E5); opacity: 0.7; }
.barra-label { font-size: 0.7rem; color: #9CA3AF; }
.barra-leyenda { display: flex; gap: 1rem; margin-top: 0.5rem; }
.leyenda-item { display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; color: #6B7280; }
.dot { width: 8px; height: 8px; border-radius: 2px; }
.dot.azul { background: var(--color-accent, #4F46E5); opacity: 0.7; }

/* Modal */
.overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.45); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; width: 100%; max-width: 540px; margin: 1rem; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; }
.modal-head h3 { font-size: 1.0625rem; font-weight: 700; color: #111827; margin: 0; }
.btn-close { background: none; border: none; font-size: 1rem; color: #9CA3AF; cursor: pointer; padding: 0.25rem; }
.modal-body { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 0.85rem; }
.modal-foot { padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6; display: flex; justify-content: flex-end; gap: 0.75rem; }

.field { display: flex; flex-direction: column; gap: 0.4rem; }
.label { font-size: 0.8rem; font-weight: 600; color: #374151; }
.input { padding: 0.55rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; color: #111827; background: #fff; font-family: inherit; width: 100%; box-sizing: border-box; }
.input:focus { outline: none; border-color: var(--color-accent, #4F46E5); }
.input-file { font-size: 0.8rem; color: #374151; }

.btn-cancel { padding: 0.45rem 1rem; background: #F3F4F6; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.8rem; font-weight: 600; color: #374151; cursor: pointer; }
.btn-cancel:hover { background: #E5E7EB; }

.grid-2-modal { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.empty-msg { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 1.5rem 0; }

.tab-content { animation: fade-in 0.15s ease; }
@keyframes fade-in { from { opacity: 0 } to { opacity: 1 } }

/* KPI variación */
.kpi-value-row { display: flex; align-items: baseline; gap: 0.5rem; }
.var-badge { font-size: 0.7rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 999px; }

/* Alerta presupuesto */
.alerta-presup { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.25rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1rem; }
.alerta-presup svg { width: 18px; height: 18px; flex-shrink: 0; }
.alerta-presup.warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; }
.alerta-presup.danger { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }
.alerta-presup span { flex: 1; }
.alerta-btn { font-size: 0.8rem; font-weight: 600; background: none; border: none; cursor: pointer; color: inherit; text-decoration: underline; white-space: nowrap; }

/* Tendencia chart */
.chart-tendencia { position: relative; height: 200px; }

/* Conductor */
.text-muted { color: #9CA3AF; }

/* Pago de servicio */
.kpi-servicio:hover { border-color: #86EFAC; background: #F0FDF4; }
.kpi-servicio { transition: border-color 0.15s, background 0.15s; }

.badge-ciclo { padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.badge-ciclo.mensual { background: #EEF2FF; color: #4338CA; }
.badge-ciclo.anual   { background: #F0FDF4; color: #15803D; }

.metodo-cell { display: flex; align-items: center; gap: 0.35rem; font-size: 0.875rem; }
.metodo-icon { font-size: 1rem; line-height: 1; }
.orden-cell  { font-size: 0.78rem; color: #9CA3AF; font-family: monospace; }
.servicio-monto { color: #16A34A !important; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .header { flex-direction: column; align-items: stretch; gap: 0.625rem; }
  .titulo { font-size: 1.25rem; }
  .header-actions { flex-direction: column; align-items: stretch; }
  .btn-nuevo { justify-content: center; }
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
