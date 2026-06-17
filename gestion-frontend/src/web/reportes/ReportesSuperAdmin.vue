<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const toast = useToast()

const cargando   = ref(false)
const datos      = ref(null)
const anioSel    = ref(new Date().getFullYear())
const anios      = [anioSel.value, anioSel.value - 1, anioSel.value - 2]
const planesCanvas = ref(null)
let   planesChart  = null

// ── Negocio SaaS ───────────────────────────────────────────────────────────
const saas = ref(null)
const saasCharts = {}
// Canvas de cada gráfico SaaS
const cIngresosMes = ref(null)
const cSubEstado   = ref(null)
const cSubPlan     = ref(null)
const cPagoEstado  = ref(null)
const cPagoMes     = ref(null)
const cCrecimiento = ref(null)
const cRegion      = ref(null)
const cTamano      = ref(null)
const cAdopcion    = ref(null)
const cLogins      = ref(null)
const cAltasBajas  = ref(null)
const cMovimientos = ref(null)

const PALETA = ['#4F46E5', '#7C3AED', '#059669', '#D97706', '#DC2626', '#0EA5E9', '#DB2777', '#65A30D']

function _mk(key, canvas, config) {
  if (!canvas) return
  if (saasCharts[key]) { saasCharts[key].destroy() }
  saasCharts[key] = new Chart(canvas, config)
}
const _ejeY = { beginAtZero: true, ticks: { precision: 0, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }
const _ejeX = { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF', maxRotation: 0, autoSkip: true } }
const _legBottom = { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }

// Ordenación
const ordenCampo = ref('costo_mantenciones_anio')
const ordenDesc  = ref(true)

const empresasOrdenadas = computed(() => {
  if (!datos.value?.empresas) return []
  return [...datos.value.empresas].sort((a, b) => {
    const va = a[ordenCampo.value]
    const vb = b[ordenCampo.value]
    if (va == null) return 1
    if (vb == null) return -1
    const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb
    return ordenDesc.value ? -cmp : cmp
  })
})

function toggleOrden(campo) {
  if (ordenCampo.value === campo) ordenDesc.value = !ordenDesc.value
  else { ordenCampo.value = campo; ordenDesc.value = true }
}

function flechaOrden(campo) {
  if (ordenCampo.value !== campo) return ''
  return ordenDesc.value ? ' ↓' : ' ↑'
}

// Formatters
function clp(val) {
  if (!val) return '$0'
  return '$' + Number(val).toLocaleString('es-CL')
}

const PLAN_COLORS = {
  basico:     { bg: '#EEF2FF', text: '#4338CA' },
  pro:        { bg: '#F5F3FF', text: '#7C3AED' },
  enterprise: { bg: '#FFF7ED', text: '#C2410C' },
}

function planStyle(plan) {
  return PLAN_COLORS[plan] || { bg: '#F3F4F6', text: '#6B7280' }
}

// Exportar CSV desde datos en memoria
function exportarCSV() {
  if (!datos.value?.empresas?.length) return
  const cabecera = [
    'Empresa', 'Plan', 'Vehículos', 'Conductores',
    `Mantenciones ${anioSel.value}`, `Costo mantenciones ${anioSel.value}`, 'Docs vencidos',
  ]
  const filas = empresasOrdenadas.value.map(e => [
    e.nombre, e.plan_display || e.plan || '—',
    e.vehiculos, e.conductores,
    e.mantenciones_anio, e.costo_mantenciones_anio, e.docs_vencidos,
  ])
  const csv = [cabecera, ...filas]
    .map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(';'))
    .join('\n')
  const contenido = 'sep=;\n' + csv
  const bom  = new Uint8Array([0xEF, 0xBB, 0xBF])
  const blob = new Blob([bom, new TextEncoder().encode(contenido)], { type: 'text/csv;charset=utf-8;' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `reporte_empresas_${anioSel.value}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function crearChartPlanes() {
  if (!planesCanvas.value || !datos.value?.empresas?.length) return
  if (planesChart) { planesChart.destroy(); planesChart = null }
  const conteo = {}
  for (const e of datos.value.empresas) {
    const p = e.plan_display || e.plan || 'Sin plan'
    conteo[p] = (conteo[p] || 0) + 1
  }
  const labels = Object.keys(conteo)
  const values = Object.values(conteo)
  planesChart = new Chart(planesCanvas.value, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: ['#4F46E5', '#7C3AED', '#C2410C', '#059669'], borderWidth: 0, hoverOffset: 6 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '65%',
      plugins: { legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 12, boxWidth: 10 } } },
    },
  })
}

// ── Render de todos los gráficos SaaS ───────────────────────────────────────
function renderSaas() {
  const s = saas.value
  if (!s) return

  // 1. Ingresos por mes (línea)
  _mk('ingMes', cIngresosMes.value, {
    type: 'line',
    data: { labels: s.ingresos.por_mes.labels, datasets: [{ data: s.ingresos.por_mes.data, label: 'Ingresos', borderColor: '#4F46E5', backgroundColor: 'rgba(79,70,229,0.1)', fill: true, tension: 0.35, pointRadius: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: _ejeY, x: _ejeX } },
  })
  // 2. Suscripciones por estado (dona)
  _mk('subEst', cSubEstado.value, {
    type: 'doughnut',
    data: { labels: Object.keys(s.suscripciones.por_estado), datasets: [{ data: Object.values(s.suscripciones.por_estado), backgroundColor: PALETA, borderWidth: 0, hoverOffset: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: _legBottom },
  })
  // 3. Ingreso potencial por plan (barra)
  _mk('subPlan', cSubPlan.value, {
    type: 'bar',
    data: { labels: Object.keys(s.suscripciones.ingreso_potencial), datasets: [{ data: Object.values(s.suscripciones.ingreso_potencial), backgroundColor: '#7C3AED', borderRadius: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: _ejeY, x: _ejeX } },
  })
  // 4. Pagos por estado (dona)
  _mk('pagoEst', cPagoEstado.value, {
    type: 'doughnut',
    data: { labels: Object.keys(s.pagos.por_estado), datasets: [{ data: Object.values(s.pagos.por_estado), backgroundColor: ['#9CA3AF', '#059669', '#DC2626', '#D97706', '#7C3AED'], borderWidth: 0, hoverOffset: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: _legBottom },
  })
  // 5. Pagos aprobados vs rechazados por mes (barra agrupada)
  _mk('pagoMes', cPagoMes.value, {
    type: 'bar',
    data: { labels: s.pagos.aprob_vs_rech.labels, datasets: [
      { label: 'Aprobados', data: s.pagos.aprob_vs_rech.aprobados, backgroundColor: '#059669', borderRadius: 4 },
      { label: 'Rechazados', data: s.pagos.aprob_vs_rech.rechazados, backgroundColor: '#DC2626', borderRadius: 4 },
    ] },
    options: { responsive: true, maintainAspectRatio: false, plugins: _legBottom, scales: { y: _ejeY, x: _ejeX } },
  })
  // 6. Crecimiento de empresas (línea acumulada)
  _mk('crec', cCrecimiento.value, {
    type: 'line',
    data: { labels: s.clientes.crecimiento.labels, datasets: [{ data: s.clientes.crecimiento.data, label: 'Empresas', borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.1)', fill: true, tension: 0.35, pointRadius: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: _ejeY, x: _ejeX } },
  })
  // 7. Empresas por región (barra)
  _mk('region', cRegion.value, {
    type: 'bar',
    data: { labels: Object.keys(s.clientes.por_region), datasets: [{ data: Object.values(s.clientes.por_region), backgroundColor: '#0EA5E9', borderRadius: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: _ejeY, x: { ..._ejeX, ticks: { font: { size: 9 }, color: '#9CA3AF', maxRotation: 35 } } } },
  })
  // 8. Empresas por tamaño de flota (dona)
  _mk('tamano', cTamano.value, {
    type: 'doughnut',
    data: { labels: Object.keys(s.clientes.por_tamano_flota).map(k => k + ' veh.'), datasets: [{ data: Object.values(s.clientes.por_tamano_flota), backgroundColor: PALETA, borderWidth: 0, hoverOffset: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: _legBottom },
  })
  // 9. Adopción de módulos (barra horizontal)
  _mk('adop', cAdopcion.value, {
    type: 'bar',
    data: { labels: Object.keys(s.adopcion.modulos), datasets: [{ data: Object.values(s.adopcion.modulos), backgroundColor: '#4F46E5', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.raw + '%' } } }, scales: { x: { ..._ejeX, max: 100, ticks: { callback: v => v + '%', font: { size: 10 }, color: '#9CA3AF' } }, y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#374151' } } } },
  })
  // 10. Logins por día (línea)
  _mk('logins', cLogins.value, {
    type: 'line',
    data: { labels: s.adopcion.logins_por_dia.labels, datasets: [{ data: s.adopcion.logins_por_dia.data, label: 'Logins', borderColor: '#DB2777', backgroundColor: 'rgba(219,39,119,0.08)', fill: true, tension: 0.3, pointRadius: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: _ejeY, x: { ..._ejeX, ticks: { font: { size: 8 }, color: '#9CA3AF', maxTicksLimit: 10 } } } },
  })
  // 11. Altas vs bajas de suscripciones (barra)
  _mk('altas', cAltasBajas.value, {
    type: 'bar',
    data: { labels: s.suscripciones.altas_vs_bajas.labels, datasets: [
      { label: 'Altas', data: s.suscripciones.altas_vs_bajas.altas, backgroundColor: '#059669', borderRadius: 4 },
      { label: 'Bajas', data: s.suscripciones.altas_vs_bajas.bajas, backgroundColor: '#DC2626', borderRadius: 4 },
    ] },
    options: { responsive: true, maintainAspectRatio: false, plugins: _legBottom, scales: { y: _ejeY, x: _ejeX } },
  })
  // 12. Movimientos de plan: upgrades vs downgrades (barra)
  _mk('mov', cMovimientos.value, {
    type: 'bar',
    data: { labels: s.adopcion.movimientos.labels, datasets: [
      { label: 'Upgrades', data: s.adopcion.movimientos.upgrades, backgroundColor: '#059669', borderRadius: 4 },
      { label: 'Downgrades', data: s.adopcion.movimientos.downgrades, backgroundColor: '#D97706', borderRadius: 4 },
    ] },
    options: { responsive: true, maintainAspectRatio: false, plugins: _legBottom, scales: { y: _ejeY, x: _ejeX } },
  })
}

// Renderiza TODOS los gráficos juntos. Se llama una sola vez tras cargar ambos
// conjuntos de datos, para evitar que un re-render del DOM (al insertar la
// sección SaaS) deje el canvas de "Distribución por plan" huérfano.
function renderTodo() {
  crearChartPlanes()
  renderSaas()
}

// Carga
async function cargar() {
  cargando.value = true
  try {
    const [rEmp, rSaas] = await Promise.all([
      apiFetch(`/api/admin/reportes/empresas/?anio=${anioSel.value}`),
      apiFetch('/api/admin/reportes/saas/'),
    ])
    if (rEmp.ok) datos.value = await rEmp.json()
    else toast.error('Error al cargar el reporte.')
    if (rSaas.ok) saas.value = await rSaas.json()
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
    await nextTick()   // el DOM ya tiene todas las secciones → render coherente
    renderTodo()
  }
}

onMounted(cargar)
onUnmounted(() => {
  if (planesChart) planesChart.destroy()
  Object.values(saasCharts).forEach(c => { try { c.destroy() } catch {} })
})
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div>
        <h1 class="titulo">Reportes</h1>
        <p class="subtitulo">Actividad operativa por empresa en el período seleccionado</p>
      </div>
      <div class="header-right">
        <select v-model="anioSel" class="sel" @change="cargar">
          <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-wrap">
      <div class="spinner"/><span>Cargando datos...</span>
    </div>

    <template v-else-if="datos">

      <!-- ═══════════════ NEGOCIO SaaS ═══════════════ -->
      <template v-if="saas">
        <h2 class="seccion-titulo">Negocio</h2>

        <!-- KPIs SaaS -->
        <div class="kpis-saas">
          <div class="kpi-mini"><span class="km-tag">Ingresos</span><span class="km-val">{{ clp(saas.ingresos.mrr) }}</span><span class="km-lbl">MRR (recurrente/mes)</span></div>
          <div class="kpi-mini"><span class="km-tag">Ingresos</span><span class="km-val">{{ clp(saas.ingresos.arpu) }}</span><span class="km-lbl">ARPU por empresa</span></div>
          <div class="kpi-mini"><span class="km-tag">Ingresos</span><span class="km-val">{{ clp(saas.ingresos.ingresos_mes) }}</span><span class="km-lbl">Cobrado este mes</span></div>
          <div class="kpi-mini"><span class="km-tag">Pagos</span><span class="km-val">{{ saas.pagos.tasa_exito }}%</span><span class="km-lbl">Tasa de éxito</span></div>
          <div class="kpi-mini"><span class="km-tag">Pagos</span><span class="km-val" :style="saas.pagos.monto_rechazado_mes > 0 ? 'color:#DC2626' : ''">{{ clp(saas.pagos.monto_rechazado_mes) }}</span><span class="km-lbl">Rechazado este mes</span></div>
          <div class="kpi-mini"><span class="km-tag">Suscripciones</span><span class="km-val" :style="saas.suscripciones.churn_mes > 0 ? 'color:#DC2626' : ''">{{ saas.suscripciones.churn_mes }}</span><span class="km-lbl">Churn este mes</span></div>
          <div class="kpi-mini"><span class="km-tag">Suscripciones</span><span class="km-val" :style="saas.suscripciones.por_vencer > 0 ? 'color:#D97706' : ''">{{ saas.suscripciones.por_vencer }}</span><span class="km-lbl">Por vencer (7 días)</span></div>
          <div class="kpi-mini"><span class="km-tag">Clientes</span><span class="km-val">{{ saas.clientes.activas }}<span class="km-sub">/{{ saas.clientes.total }}</span></span><span class="km-lbl">Empresas activas</span></div>
          <div class="kpi-mini"><span class="km-tag">Clientes</span><span class="km-val" :style="saas.clientes.sin_actividad > 0 ? 'color:#D97706' : ''">{{ saas.clientes.sin_actividad }}</span><span class="km-lbl">Sin actividad (30 días)</span></div>
          <div class="kpi-mini"><span class="km-tag">Adopción</span><span class="km-val" style="color:#059669">{{ saas.adopcion.upgrades_mes }}</span><span class="km-lbl">Upgrades este mes</span></div>
          <div class="kpi-mini"><span class="km-tag">Adopción</span><span class="km-val" :style="saas.adopcion.downgrades_mes > 0 ? 'color:#D97706' : ''">{{ saas.adopcion.downgrades_mes }}</span><span class="km-lbl">Downgrades este mes</span></div>
          <div class="kpi-mini"><span class="km-tag">Pagos</span><span class="km-val">{{ saas.pagos.cobro_automatico }}</span><span class="km-lbl">Con cobro automático</span></div>
        </div>

        <!-- Gráficos SaaS -->
        <div class="grid-charts">
          <div class="card"><div class="card-head"><h3 class="card-title">Ingresos cobrados por mes</h3></div><div class="chart-box"><canvas ref="cIngresosMes"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Crecimiento de empresas</h3></div><div class="chart-box"><canvas ref="cCrecimiento"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Suscripciones por estado</h3></div><div class="chart-box"><canvas ref="cSubEstado"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Ingreso potencial por plan</h3></div><div class="chart-box"><canvas ref="cSubPlan"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Pagos por estado</h3></div><div class="chart-box"><canvas ref="cPagoEstado"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Pagos aprobados vs rechazados</h3></div><div class="chart-box"><canvas ref="cPagoMes"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Altas vs bajas de suscripciones</h3></div><div class="chart-box"><canvas ref="cAltasBajas"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Movimientos de plan</h3></div><div class="chart-box"><canvas ref="cMovimientos"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Empresas por región</h3></div><div class="chart-box"><canvas ref="cRegion"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Empresas por tamaño de flota</h3></div><div class="chart-box"><canvas ref="cTamano"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Adopción de módulos</h3></div><div class="chart-box"><canvas ref="cAdopcion"/></div></div>
          <div class="card"><div class="card-head"><h3 class="card-title">Logins por día (30 días)</h3></div><div class="chart-box"><canvas ref="cLogins"/></div></div>
        </div>

        <h2 class="seccion-titulo">Operación por empresa</h2>
      </template>

      <!-- KPIs -->
      <div class="kpis">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div>
            <div class="kpi-value">{{ datos.total_empresas }}</div>
            <div class="kpi-label">Empresas activas</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#F0FDF4;color:#059669">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
            </svg>
          </div>
          <div>
            <div class="kpi-value">{{ datos.total_vehiculos }}</div>
            <div class="kpi-label">Total vehículos</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <div>
            <div class="kpi-value">{{ datos.total_mantenciones }}</div>
            <div class="kpi-label">Mantenciones {{ datos.anio }}</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FDF4FF;color:#7C3AED">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div>
            <div class="kpi-value">{{ clp(datos.total_costo) }}</div>
            <div class="kpi-label">Costo total mantenciones</div>
          </div>
        </div>
      </div>

      <!-- Dona distribución planes -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.25rem">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Distribución por plan</h3>
            <span class="sub-count">empresas activas</span>
          </div>
          <div style="padding:1.25rem;height:230px">
            <canvas ref="planesCanvas"/>
          </div>
        </div>
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Resumen {{ datos.anio }}</h3>
          </div>
          <div style="padding:1.25rem;display:flex;flex-direction:column;gap:1rem">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:0.875rem;color:#6B7280">Vehículos totales</span>
              <span style="font-size:1.25rem;font-weight:700;color:#111827">{{ datos.total_vehiculos }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:0.875rem;color:#6B7280">Mantenciones del año</span>
              <span style="font-size:1.25rem;font-weight:700;color:#111827">{{ datos.total_mantenciones }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:0.875rem;color:#6B7280">Costo total mantenciones</span>
              <span style="font-size:1.1rem;font-weight:700;color:#4F46E5">{{ clp(datos.total_costo) }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:0.875rem;color:#6B7280">Costo promedio / empresa</span>
              <span style="font-size:1rem;font-weight:600;color:#374151">
                {{ datos.total_empresas ? clp(Math.round(datos.total_costo / datos.total_empresas)) : '$0' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabla -->
      <div class="card">
        <div class="card-head">
          <h3 class="card-title">Actividad por empresa — {{ datos.anio }}</h3>
          <span class="sub-count">{{ datos.total_empresas }} empresa{{ datos.total_empresas !== 1 ? 's' : '' }}</span>
        </div>
        <div v-if="!datos.empresas.length" class="card-body">
          <p class="empty-msg">Sin empresas activas.</p>
        </div>
        <div v-else class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th class="sortable" @click="toggleOrden('nombre')">Empresa{{ flechaOrden('nombre') }}</th>
                <th>Plan</th>
                <th class="sortable" @click="toggleOrden('vehiculos')">Vehículos{{ flechaOrden('vehiculos') }}</th>
                <th class="sortable" @click="toggleOrden('conductores')">Conductores{{ flechaOrden('conductores') }}</th>
                <th class="sortable" @click="toggleOrden('mantenciones_anio')">Mantenciones{{ flechaOrden('mantenciones_anio') }}</th>
                <th class="sortable" @click="toggleOrden('costo_mantenciones_anio')">Costo mant.{{ flechaOrden('costo_mantenciones_anio') }}</th>
                <th class="sortable" @click="toggleOrden('docs_vencidos')">Docs vencidos{{ flechaOrden('docs_vencidos') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in empresasOrdenadas" :key="e.id">
                <td class="font-medium">{{ e.nombre }}</td>
                <td>
                  <span class="badge" :style="{ background: planStyle(e.plan).bg, color: planStyle(e.plan).text }">
                    {{ e.plan_display || '—' }}
                  </span>
                </td>
                <td>{{ e.vehiculos }}</td>
                <td>{{ e.conductores }}</td>
                <td>{{ e.mantenciones_anio }}</td>
                <td class="font-medium">{{ clp(e.costo_mantenciones_anio) }}</td>
                <td>
                  <span v-if="e.docs_vencidos" class="badge" style="background:#FEF2F2;color:#DC2626">
                    {{ e.docs_vencidos }}
                  </span>
                  <span v-else class="text-ok">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 1.5rem 2rem; max-width: 1400px; font-family: 'Inter', system-ui, sans-serif; }

.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; }
.titulo { font-size: 1.5rem; font-weight: 800; color: #111827; margin: 0 0 0.2rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-right { display: flex; align-items: center; gap: 0.75rem; }
.sel { padding: 0.45rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; background: #fff; color: #374151; cursor: pointer; }
.btn-export {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem; background: #fff; border: 1.5px solid #D1D5DB;
  border-radius: 8px; font-size: 0.875rem; font-weight: 600; color: #374151;
  cursor: pointer; transition: all 0.15s; white-space: nowrap; font-family: inherit;
}
.btn-export svg { width: 15px; height: 15px; }
.btn-export:hover:not(:disabled) { border-color: #4F46E5; color: #4F46E5; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

.loading-wrap { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; padding: 3rem 0; font-size: 0.875rem; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #4F46E5; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1rem 1.25rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-icon svg { width: 20px; height: 20px; }
.kpi-value { font-size: 1.4rem; font-weight: 800; color: #111827; line-height: 1.1; }
.kpi-label { font-size: 0.75rem; color: #9CA3AF; font-weight: 500; margin-top: 0.15rem; }

.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.card-body { padding: 1.25rem; }
.sub-count { font-size: 0.8rem; color: #9CA3AF; }
.empty-msg { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 1.5rem 0; }

.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; white-space: nowrap; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tr:hover td { background: #FAFAFA; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: #374151; }
.font-medium { font-weight: 600; color: #111827; }
.text-ok { color: #D1D5DB; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }

/* ── Negocio SaaS ── */
.seccion-titulo { font-size: 1.05rem; font-weight: 700; color: #1E1B4B; margin: 1.75rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #EDE9FE; }
.seccion-titulo:first-child { margin-top: 0; }

.kpis-saas { display: grid; grid-template-columns: repeat(auto-fill, minmax(155px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }
.kpi-mini { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 0.75rem 0.9rem; display: flex; flex-direction: column; gap: 0.15rem; }
.km-tag { font-size: 0.625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #A78BFA; }
.km-val { font-size: 1.25rem; font-weight: 800; color: #111827; line-height: 1.1; }
.km-sub { font-size: 0.875rem; font-weight: 600; color: #9CA3AF; }
.km-lbl { font-size: 0.75rem; color: #6B7280; }

.grid-charts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.chart-box { padding: 1rem 1.25rem 1.25rem; height: 240px; }
@media (max-width: 900px) { .grid-charts { grid-template-columns: 1fr; } }
</style>
