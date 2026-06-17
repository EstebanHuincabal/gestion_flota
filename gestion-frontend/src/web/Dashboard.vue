<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Chart from 'chart.js/auto'
import { apiFetch, safeJsonParse } from '../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav } from '../utils/empresaActiva.js'
import { tienePermiso } from '../utils/permisos.js'
import { useTema } from '../utils/tema.js'

const { accentActual } = useTema()
const router = useRouter()
const { ruta } = useEmpresaNav()
const usuario = computed(() => safeJsonParse(localStorage.getItem('usuario'), {}))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')

const ACCESOS_EMPRESA = [
  { label: 'Flota',        permiso: 'flotas.ver',      path: '/flota',       color: 'ac-purple',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>` },
  { label: 'Conductores',  permiso: 'conductores.ver', path: '/conductores', color: 'ac-blue',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>` },
  { label: 'Mantenciones', permiso: 'mantenciones.ver', path: '/mantenciones', color: 'ac-amber',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/>` },
  { label: 'Documentos',   permiso: 'documentos.ver',  path: '/documentos',  color: 'ac-slate',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>` },
  { label: 'Predictivo',   permiso: 'mantenciones.ver', path: '/predictivo',  color: 'ac-indigo',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 10V3L4 14h7v7l9-11h-7z"/>` },
]
const accesosEmpresa = computed(() => ACCESOS_EMPRESA.filter(a => tienePermiso(a.permiso)))

// Permisos de dashboard por categoría. Arrancan en false (fail-closed): cada
// sección solo se muestra cuando el backend confirma el permiso del módulo.
const permisosDash = ref({ flota: false, mantenimiento: false, finanzas: false, documentos: false, rutas: false, conductores: false })
const sinAcceso    = ref(false)

const cargando         = ref(true)
const cargandoGraficos = ref(false)
const error            = ref('')

// SUPERADMIN data
const kpisGlobal    = ref({ empresas_activas: 0, empresas_inactivas: 0, total_usuarios: 0, total_conductores: 0, total_vehiculos: 0, empresas_nuevas_mes: 0, usuarios_activos_hoy: 0, mrr_actual: 0, mrr_variacion: null })
const topEmpresas   = ref([])
const sinActividad  = ref([])
const empresasAlertas = ref([])

// EMPRESA data
const kpisEmpresa    = ref({ total_vehiculos: 0, total_conductores: 0, mantenciones_pendientes: 0, docs_por_vencer: 0 })
const widgetsEmpresa = ref({ proximas_7_dias: [], gasto_vs_presupuesto: null, top_vehiculos_costo: [] })
const hayConductoresKm = ref(false)

// ── Canvas refs ──────────────────────────────────────────────
// Superadmin (existentes)
const crecimientoCanvas  = ref(null)
const distribucionCanvas = ref(null)
const planesCanvas       = ref(null)
const combustibleCanvas  = ref(null)
const topEmpresasCanvas  = ref(null)
// Superadmin (nuevos S1-S5)
const mrrHistCanvas      = ref(null)
const usuariosNuevosCanvas = ref(null)
const marcasGlobalCanvas = ref(null)
const activosCanvas      = ref(null)

// Empresa (existentes)
const mantencionesCanvas = ref(null)
const flotaCanvas        = ref(null)
const gastosCanvas       = ref(null)
const rutasCanvas        = ref(null)
const conductoresCanvas  = ref(null)
// Empresa (nuevos E1-E7)
const gastos12mCanvas    = ref(null)
const marcasFlotaCanvas  = ref(null)
const mantEstadoCanvas   = ref(null)
const alertasTipoCanvas  = ref(null)
const docsEstadoCanvas   = ref(null)
const kmMesCanvas        = ref(null)

// ── Chart instances ──────────────────────────────────────────
let crecimientoChart = null; let distribucionChart = null; let planesChart = null
let combustibleChart = null; let topEmpresasChart = null
let mrrHistChart = null; let usuariosNuevosChart = null; let marcasGlobalChart = null; let activosChart = null
let vehiculosChart = null; let mantencionesChart = null; let flotaChart = null
let gastosChart = null; let rutasChart = null; let conductoresChart = null
let gastos12mChart = null; let marcasFlotaChart = null; let mantEstadoChart = null
let alertasTipoChart = null; let docsEstadoChart = null; let kmMesChart = null

const pctActivas = computed(() => {
  const total = kpisGlobal.value.empresas_activas + kpisGlobal.value.empresas_inactivas
  return total ? Math.round((kpisGlobal.value.empresas_activas / total) * 100) : 0
})

const PERIODOS = [
  { key: '7d',  label: '7D',  gran: 'día',    titulo: 'últimos 7 días'   },
  { key: '30d', label: '1M',  gran: 'día',    titulo: 'últimos 30 días'  },
  { key: '3m',  label: '3M',  gran: 'semana', titulo: 'últimos 3 meses'  },
  { key: '6m',  label: '6M',  gran: 'semana', titulo: 'últimos 6 meses'  },
  { key: '12m', label: '1A',  gran: 'mes',    titulo: 'últimos 12 meses' },
]
const periodoActivo = ref('12m')
const periodoInfo   = computed(() => PERIODOS.find(p => p.key === periodoActivo.value) || PERIODOS[4])

const cargar = async () => {
  cargando.value = true
  error.value    = ''
  let pendiente  = null
  try {
    if (esSuperadmin.value) {
      const res = await apiFetch(`/api/dashboard/?periodo=${periodoActivo.value}`)
      if (!res.ok) throw new Error('Error al cargar el dashboard')
      const data = await res.json()
      if (data.kpis)   kpisGlobal.value    = data.kpis
      if (data.charts) topEmpresas.value   = data.charts.top_empresas || []
      sinActividad.value    = data.sin_actividad  || []
      empresasAlertas.value = data.empresas_alertas || []
      if (data.charts) pendiente = () => renderGraficosGlobal(data.charts)
    } else {
      const res = await apiFetchEmpresa(`/api/empresa/dashboard/?periodo=${periodoActivo.value}`)
      if (!res.ok) throw new Error('Error al cargar el dashboard')
      const data = await res.json()
      sinAcceso.value = !!data.sin_acceso
      if (data.permisos_dashboard) permisosDash.value = data.permisos_dashboard
      if (data.kpis)    kpisEmpresa.value    = { ...kpisEmpresa.value, ...data.kpis }
      if (data.widgets) widgetsEmpresa.value = data.widgets
      if (data.charts)  pendiente = () => renderGraficosEmpresa(data.charts)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
  if (pendiente) {
    await nextTick()
    pendiente()
  }
}

const cargarGraficos = async (p) => {
  cargandoGraficos.value = true
  try {
    if (esSuperadmin.value) {
      const res = await apiFetch(`/api/dashboard/?periodo=${p}`)
      if (!res.ok) return
      const data = await res.json()
      if (data.charts) renderGraficosGlobal(data.charts)
    } else {
      const res = await apiFetchEmpresa(`/api/empresa/dashboard/?periodo=${p}`)
      if (!res.ok) return
      const data = await res.json()
      if (data.charts) renderGraficosEmpresa(data.charts)
    }
  } finally {
    cargandoGraficos.value = false
  }
}

const cambiarPeriodo = (p) => { periodoActivo.value = p; cargarGraficos(p) }

// ── Render superadmin ────────────────────────────────────────
const renderGraficosGlobal = (charts) => {
  ;[crecimientoChart, distribucionChart, planesChart, combustibleChart, topEmpresasChart,
    mrrHistChart, usuariosNuevosChart, marcasGlobalChart, activosChart
  ].forEach(c => { try { c?.destroy() } catch {} })

  const ac = accentActual()

  if (crecimientoCanvas.value) {
    crecimientoChart = new Chart(crecimientoCanvas.value, {
      type: 'line',
      data: { labels: charts.crecimiento.labels, datasets: [{ data: charts.crecimiento.data, borderColor: ac, backgroundColor: `color-mix(in oklch, ${ac} 12%, transparent)`, tension: 0.4, fill: true, pointRadius: 3, pointBackgroundColor: ac, pointHoverRadius: 5 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }
  if (distribucionCanvas.value) {
    distribucionChart = new Chart(distribucionCanvas.value, {
      type: 'doughnut',
      data: { labels: charts.distribucion_flota.labels, datasets: [{ data: charts.distribucion_flota.data, backgroundColor: ['#E5E7EB', ac, `color-mix(in oklch, ${ac} 60%, #10B981)`, `color-mix(in oklch, ${ac} 40%, #F59E0B)`], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 12, boxWidth: 10 } } }, cutout: '68%' }
    })
  }
  if (planesCanvas.value && charts.distribucion_planes?.length) {
    planesChart = new Chart(planesCanvas.value, {
      type: 'doughnut',
      data: { labels: charts.distribucion_planes.map(p => p.plan), datasets: [{ data: charts.distribucion_planes.map(p => p.empresas), backgroundColor: ['#4F46E5','#10B981','#F59E0B','#EF4444'], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }, cutout: '65%' }
    })
  }
  if (combustibleCanvas.value && charts.distribucion_combustible?.length) {
    combustibleChart = new Chart(combustibleCanvas.value, {
      type: 'doughnut',
      data: { labels: charts.distribucion_combustible.map(c => c.label), datasets: [{ data: charts.distribucion_combustible.map(c => c.total), backgroundColor: ['#3B82F6','#10B981','#F59E0B','#8B5CF6','#64748B'], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }, cutout: '65%' }
    })
  }
  if (topEmpresasCanvas.value && charts.top_empresas_bar?.length) {
    topEmpresasChart = new Chart(topEmpresasCanvas.value, {
      type: 'bar',
      data: { labels: charts.top_empresas_bar.map(e => e.nombre), datasets: [{ data: charts.top_empresas_bar.map(e => e.vehiculos), backgroundColor: `color-mix(in oklch, ${ac} 65%, white)`, hoverBackgroundColor: ac, borderRadius: 5, barThickness: 18 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }, y: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#374151' } } } }
    })
  }

  // S1: MRR histórico
  if (mrrHistCanvas.value && charts.mrr_historico?.data?.length) {
    const d = charts.mrr_historico
    // Proyección lineal de 3 meses (regresión simple sobre últimos 6 puntos)
    const ultimos = d.data.slice(-6)
    const n = ultimos.length
    const sx = ultimos.reduce((s,_,i) => s+i, 0), sy = ultimos.reduce((s,v) => s+v, 0)
    const sxy = ultimos.reduce((s,v,i) => s+i*v, 0), sx2 = ultimos.reduce((s,_,i) => s+i*i, 0)
    const slope = (n*sxy - sx*sy) / (n*sx2 - sx*sx || 1)
    const intercept = (sy - slope*sx) / n
    const proyLabels = ['', '', ''].map((_, i) => `+${i+1}m`)
    const proyData = Array(d.data.length).fill(null).concat(
      [0,1,2].map(i => Math.max(0, Math.round(intercept + slope*(n+i))))
    )
    mrrHistChart = new Chart(mrrHistCanvas.value, {
      type: 'line',
      data: {
        labels: [...d.labels, ...proyLabels],
        datasets: [
          { label: 'MRR real', data: [...d.data, null, null, null], borderColor: '#4F46E5', backgroundColor: 'rgba(79,70,229,0.08)', tension: 0.4, fill: true, pointRadius: 3, pointBackgroundColor: '#4F46E5', pointHoverRadius: 5 },
          { label: 'Proyección', data: proyData, borderColor: 'rgba(79,70,229,0.4)', borderDash: [6,4], backgroundColor: 'transparent', tension: 0.4, pointRadius: 3, pointBackgroundColor: 'rgba(79,70,229,0.4)', pointHoverRadius: 5 },
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { font: { size: 10 }, color: '#9CA3AF', callback: v => `$${(v/1000).toFixed(0)}k` }, grid: { color: '#F3F4F6' } } } }
    })
  }

  // S2: Usuarios nuevos por mes
  if (usuariosNuevosCanvas.value && charts.usuarios_nuevos?.data?.length) {
    const d = charts.usuarios_nuevos
    usuariosNuevosChart = new Chart(usuariosNuevosCanvas.value, {
      type: 'bar',
      data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: `color-mix(in oklch, ${ac} 70%, white)`, hoverBackgroundColor: ac, borderRadius: 5, barThickness: 18 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }

  // S4: Marcas globales
  if (marcasGlobalCanvas.value && charts.top_marcas_global?.length) {
    marcasGlobalChart = new Chart(marcasGlobalCanvas.value, {
      type: 'bar',
      data: { labels: charts.top_marcas_global.map(m => m.marca), datasets: [{ data: charts.top_marcas_global.map(m => m.total), backgroundColor: '#10B981', hoverBackgroundColor: '#059669', borderRadius: 5, barThickness: 16 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }, y: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#374151' } } } }
    })
  }

  // S5: Usuarios activos 30 días
  if (activosCanvas.value && charts.activos_30d?.data?.length) {
    const d = charts.activos_30d
    activosChart = new Chart(activosCanvas.value, {
      type: 'line',
      data: { labels: d.labels, datasets: [{ data: d.data, borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,0.07)', tension: 0.3, fill: true, pointRadius: 0, pointHoverRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 9 }, color: '#9CA3AF', maxTicksLimit: 10 } }, y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }
}

// ── Render empresa ───────────────────────────────────────────
const renderGraficosEmpresa = (charts) => {
  ;[vehiculosChart, mantencionesChart, flotaChart, gastosChart, rutasChart, conductoresChart,
    gastos12mChart, marcasFlotaChart, mantEstadoChart, alertasTipoChart,
    docsEstadoChart, kmMesChart
  ].forEach(c => { try { c?.destroy() } catch {} })

  const ac = accentActual()

  // Flota
  if (flotaCanvas.value && charts.estado_flota) {
    const ef = charts.estado_flota
    flotaChart = new Chart(flotaCanvas.value, {
      type: 'doughnut',
      data: { labels: ['Sin alertas', 'Docs por vencer', 'Mantenciones pendientes'], datasets: [{ data: [ef.sin_alerta, ef.docs_vencer, ef.mant_pendiente], backgroundColor: ['#059669','#F59E0B','#3B82F6'], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 12, boxWidth: 10 } } } }
    })
  }
  if (marcasFlotaCanvas.value && charts.marcas_flota?.length) {
    marcasFlotaChart = new Chart(marcasFlotaCanvas.value, {
      type: 'bar',
      data: { labels: charts.marcas_flota.map(m => m.marca), datasets: [{ data: charts.marcas_flota.map(m => m.total), backgroundColor: `color-mix(in oklch, ${ac} 55%, white)`, hoverBackgroundColor: ac, borderRadius: 5, barThickness: 18 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }, y: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#374151' } } } }
    })
  }

  // Mantenimiento
  if (mantencionesCanvas.value && charts.mantenciones) {
    mantencionesChart = new Chart(mantencionesCanvas.value, {
      type: 'line',
      data: { labels: charts.mantenciones.labels, datasets: [{ data: charts.mantenciones.data, borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,0.07)', tension: 0.4, fill: true, pointRadius: 3, pointBackgroundColor: '#F59E0B', pointHoverRadius: 5 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }
  if (mantEstadoCanvas.value && charts.mant_por_estado) {
    const ms = charts.mant_por_estado
    mantEstadoChart = new Chart(mantEstadoCanvas.value, {
      type: 'doughnut',
      data: { labels: ['Pendiente','En proceso','Completada','Cancelada'], datasets: [{ data: [ms.pendiente,ms.en_proceso,ms.completada,ms.cancelada], backgroundColor: ['#F59E0B','#3B82F6','#059669','#9CA3AF'], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } } }
    })
  }
  if (alertasTipoCanvas.value && charts.alertas_por_tipo?.length) {
    alertasTipoChart = new Chart(alertasTipoCanvas.value, {
      type: 'bar',
      data: { labels: charts.alertas_por_tipo.map(a => a.tipo), datasets: [{ data: charts.alertas_por_tipo.map(a => a.total), backgroundColor: '#EF4444', hoverBackgroundColor: '#DC2626', borderRadius: 5, barThickness: 18 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }, y: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#374151' } } } }
    })
  }

  // Finanzas
  if (gastosCanvas.value && charts.gastos_6m) {
    const COLORES_CAT = { combustible: '#3B82F6', mantencion: '#F59E0B', seguro: '#10B981', multa: '#EF4444', otro: '#94A3B8' }
    const LABELS_CAT  = { combustible: 'Combustible', mantencion: 'Mantención', seguro: 'Seguro', multa: 'Multa', otro: 'Otro' }
    gastosChart = new Chart(gastosCanvas.value, {
      type: 'bar',
      data: { labels: charts.gastos_6m.labels, datasets: Object.entries(charts.gastos_6m.datasets).map(([cat, data]) => ({ label: LABELS_CAT[cat], data, backgroundColor: COLORES_CAT[cat], stack: 'gastos', borderRadius: 0 })) },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }, scales: { x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { stacked: true, beginAtZero: true, ticks: { font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }
  if (gastos12mCanvas.value && charts.gastos_12m?.data?.length) {
    gastos12mChart = new Chart(gastos12mCanvas.value, {
      type: 'line',
      data: { labels: charts.gastos_12m.labels, datasets: [{ data: charts.gastos_12m.data, borderColor: '#4F46E5', backgroundColor: 'rgba(79,70,229,0.06)', tension: 0.4, fill: true, pointRadius: 3, pointBackgroundColor: '#4F46E5', pointHoverRadius: 5 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { font: { size: 10 }, color: '#9CA3AF', callback: v => `$${(v/1000).toFixed(0)}k` }, grid: { color: '#F3F4F6' } } } }
    })
  }

  // Documentos
  if (docsEstadoCanvas.value && charts.docs_por_estado) {
    const de = charts.docs_por_estado
    docsEstadoChart = new Chart(docsEstadoCanvas.value, {
      type: 'doughnut',
      data: { labels: ['Vigentes','Por vencer','Vencidos'], datasets: [{ data: [de.vigentes, de.por_vencer, de.vencidos], backgroundColor: ['#059669','#F59E0B','#EF4444'], borderWidth: 0, hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } } }
    })
  }

  // Rutas
  if (rutasCanvas.value && charts.rutas_6m) {
    rutasChart = new Chart(rutasCanvas.value, {
      type: 'bar',
      data: { labels: charts.rutas_6m.labels, datasets: [{ label: 'Finalizadas', data: charts.rutas_6m.finalizadas, backgroundColor: '#059669', borderRadius: 4, barThickness: 20 }, { label: 'Canceladas', data: charts.rutas_6m.canceladas, backgroundColor: '#EF4444', borderRadius: 4, barThickness: 20 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10, boxWidth: 10 } } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } } } }
    })
  }
  if (kmMesCanvas.value && charts.km_por_mes?.data?.length) {
    kmMesChart = new Chart(kmMesCanvas.value, {
      type: 'bar',
      data: { labels: charts.km_por_mes.labels, datasets: [{ data: charts.km_por_mes.data, backgroundColor: `color-mix(in oklch, #10B981 70%, white)`, hoverBackgroundColor: '#10B981', borderRadius: 5, barThickness: 20 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } }, y: { beginAtZero: true, ticks: { font: { size: 10 }, color: '#9CA3AF', callback: v => `${v.toFixed(0)} km` }, grid: { color: '#F3F4F6' } } } }
    })
  }


  // Conductores
  hayConductoresKm.value = (charts.top_conductores_km?.length || 0) > 0
  if (conductoresCanvas.value && charts.top_conductores_km?.length) {
    conductoresChart = new Chart(conductoresCanvas.value, {
      type: 'bar',
      data: { labels: charts.top_conductores_km.map(c => c.nombre), datasets: [{ data: charts.top_conductores_km.map(c => c.km), backgroundColor: `color-mix(in oklch, ${ac} 70%, white)`, hoverBackgroundColor: ac, borderRadius: 6, barThickness: 22 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }, y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#374151' } } } }
    })
  }
}

onMounted(cargar)

onUnmounted(() => {
  ;[crecimientoChart, distribucionChart, planesChart, combustibleChart, topEmpresasChart,
    mrrHistChart, usuariosNuevosChart, marcasGlobalChart, activosChart,
    vehiculosChart, mantencionesChart, flotaChart, gastosChart, rutasChart, conductoresChart,
    gastos12mChart, marcasFlotaChart, mantEstadoChart, alertasTipoChart,
    docsEstadoChart, kmMesChart
  ].forEach(c => { try { c?.destroy() } catch {} })
})
</script>

<template>
  <div class="page">

    <div class="page-header">
      <div>
        <h1 class="page-title">{{ esSuperadmin ? 'Dashboard Global' : `Bienvenido, ${usuario.nombre?.split(' ')[0]}` }}</h1>
        <p class="page-subtitle">{{ esSuperadmin ? 'Métricas y estado general de la plataforma' : `${usuario.empresa} — Panel de gestión` }}</p>
      </div>
      <button class="btn-refresh" @click="cargar" :disabled="cargando">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        Actualizar
      </button>
    </div>

    <div v-if="cargando" class="loading"><div class="spinner"/><span>Cargando métricas...</span></div>
    <div v-else-if="error" class="alert-error">{{ error }}</div>

    <!-- ══════════════ SUPERADMIN ══════════════ -->
    <template v-else-if="esSuperadmin">

      <div class="kpis">
        <div class="kpi-card">
          <div class="kpi-icon bg-purple"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg></div>
          <div class="kpi-data"><span class="kpi-value">{{ kpisGlobal.empresas_activas }}</span><span class="kpi-label">Empresas activas</span><span class="kpi-sub">{{ kpisGlobal.empresas_inactivas }} inactivas</span></div>
          <span class="kpi-pct">{{ pctActivas }}%</span>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-indigo"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/></svg></div>
          <div class="kpi-data"><span class="kpi-value">{{ kpisGlobal.total_vehiculos }}</span><span class="kpi-label">Vehículos totales</span></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-blue"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value">{{ kpisGlobal.total_usuarios }}</span><span class="kpi-label">Usuarios registrados</span></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-emerald"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M10 9V7m0 0H8m2 0h2M10 7a4 4 0 110 8 4 4 0 010-8zM21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value">{{ kpisGlobal.total_conductores }}</span><span class="kpi-label">Conductores</span></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-indigo"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 13v-1m-2.599-1c.52.598 1.49 1 2.599 1 1.657 0 3-.895 3-2m-6 0H6"/></svg></div>
          <div class="kpi-data">
            <span class="kpi-value">${{ kpisGlobal.mrr_actual?.toLocaleString('es-CL') }}</span>
            <span class="kpi-label">MRR</span>
            <span v-if="kpisGlobal.mrr_variacion !== null" class="kpi-sub" :style="{ color: kpisGlobal.mrr_variacion >= 0 ? '#059669' : '#DC2626' }">{{ kpisGlobal.mrr_variacion >= 0 ? '+' : '' }}{{ kpisGlobal.mrr_variacion }}% vs mes ant.</span>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-amber"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value text-amber">{{ kpisGlobal.empresas_nuevas_mes }}</span><span class="kpi-label">Nuevas este mes</span></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon bg-green"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value text-green">{{ kpisGlobal.usuarios_activos_hoy }}</span><span class="kpi-label">Activos hoy</span></div>
        </div>
      </div>

      <!-- Crecimiento + Distribución flotas -->
      <div class="charts-row charts-global">
        <div class="card chart-grande">
          <div class="card-header">
            <div><h2 class="card-title">Crecimiento de empresas</h2><p class="card-subtitle">Altas por {{ periodoInfo.gran }} — {{ periodoInfo.titulo }}</p></div>
            <div class="periodo-btns">
              <button v-for="p in PERIODOS" :key="p.key" :class="['periodo-btn', { active: periodoActivo === p.key }]" :disabled="cargandoGraficos" @click="cambiarPeriodo(p.key)">{{ p.label }}</button>
            </div>
          </div>
          <div class="chart-wrap" :class="{ 'chart-loading': cargandoGraficos }"><canvas ref="crecimientoCanvas"/></div>
        </div>
        <div class="card chart-chico">
          <div class="card-header"><div><h2 class="card-title">Distribución de flotas</h2><p class="card-subtitle">Por tamaño de empresa</p></div></div>
          <div class="chart-wrap"><canvas ref="distribucionCanvas"/></div>
        </div>
      </div>

      <!-- S1: MRR histórico (fila completa) -->
      <div class="charts-row" style="grid-template-columns:1fr;margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header">
            <div><h2 class="card-title">Evolución del MRR</h2><p class="card-subtitle">Últimos 12 meses + proyección 3 meses</p></div>
            <button class="btn-link" @click="router.push('/finanzas')">Ver finanzas →</button>
          </div>
          <div class="chart-wrap" style="height:260px"><canvas ref="mrrHistCanvas"/></div>
        </div>
      </div>

      <!-- S2: Usuarios nuevos + S4: Marcas globales -->
      <div class="charts-row" style="margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Nuevos usuarios por mes</h2><p class="card-subtitle">Usuarios y conductores registrados — 12 meses</p></div></div>
          <div class="chart-wrap" style="height:240px"><canvas ref="usuariosNuevosCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Top marcas de vehículos</h2><p class="card-subtitle">Distribución en toda la plataforma</p></div></div>
          <div class="chart-wrap" style="height:240px"><canvas ref="marcasGlobalCanvas"/></div>
        </div>
      </div>

      <!-- Fila inferior: top 5 + accesos -->
      <div class="bottom-row">
        <div class="card">
          <div class="card-header">
            <div><h2 class="card-title">Top 5 empresas</h2><p class="card-subtitle">Por cantidad de vehículos</p></div>
            <button class="btn-link" @click="router.push('/empresas')">Ver todas →</button>
          </div>
          <table class="top-tabla">
            <thead><tr><th>#</th><th>Empresa</th><th class="text-right">Vehículos</th></tr></thead>
            <tbody>
              <tr v-if="topEmpresas.length === 0"><td colspan="3" class="empty">No hay empresas registradas.</td></tr>
              <tr v-for="(e, i) in topEmpresas" :key="i">
                <td><span class="rank">{{ i + 1 }}</span></td>
                <td class="empresa-nombre">{{ e.nombre }}</td>
                <td class="text-right font-semibold">{{ e.vehiculos }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <h2 class="section-title">Accesos rápidos</h2>
          <div class="accesos accesos-2x2">
            <button class="acceso-card" @click="router.push('/empresas')"><div class="acceso-icon ac-purple"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg></div><span class="acceso-label">Empresas</span></button>
            <button class="acceso-card" @click="router.push('/usuarios')"><div class="acceso-icon ac-blue"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg></div><span class="acceso-label">Usuarios</span></button>
            <button class="acceso-card" @click="router.push('/logs')"><div class="acceso-icon ac-slate"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg></div><span class="acceso-label">Logs</span></button>
            <button class="acceso-card" @click="router.push('/planes')"><div class="acceso-icon ac-indigo"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg></div><span class="acceso-label">Planes</span></button>
          </div>
        </div>
      </div>

      <!-- Planes + Sin actividad -->
      <div class="bottom-row" style="margin-top:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Distribución de planes</h2><p class="card-subtitle">Empresas activas por plan</p></div></div>
          <div class="chart-wrap"><canvas ref="planesCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Sin actividad (30 días)</h2><p class="card-subtitle">Sin mantenciones recientes</p></div></div>
          <div v-if="!sinActividad.length" class="empty" style="padding:1.5rem;text-align:center">Todas las empresas tienen actividad reciente</div>
          <table v-else class="top-tabla">
            <tbody>
              <tr v-for="e in sinActividad" :key="e.id" style="cursor:pointer" @click="router.push(`/empresas/${e.id}`)">
                <td><div style="display:flex;align-items:center;gap:0.5rem"><span style="width:8px;height:8px;border-radius:50%;background:#F59E0B;flex-shrink:0;display:inline-block"/>{{ e.nombre }}</div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Top 10 empresas + Combustible -->
      <div class="charts-row charts-global" style="margin-top:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Top 10 empresas por flota</h2><p class="card-subtitle">Cantidad de vehículos por empresa</p></div><button class="btn-link" @click="router.push('/empresas')">Ver todas →</button></div>
          <div class="chart-wrap" style="height:280px"><canvas ref="topEmpresasCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Tipos de combustible</h2><p class="card-subtitle">Distribución de toda la flota</p></div></div>
          <div class="chart-wrap" style="height:280px"><canvas ref="combustibleCanvas"/></div>
        </div>
      </div>

      <!-- S3: Empresas con más alertas + S5: Usuarios activos -->
      <div class="charts-row" style="margin-top:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Empresas con más alertas vencidas</h2><p class="card-subtitle">Mantenimiento predictivo vencido</p></div></div>
          <div v-if="!empresasAlertas.length" class="empty" style="padding:1.5rem;text-align:center">Sin alertas vencidas en la plataforma</div>
          <table v-else class="top-tabla">
            <thead><tr><th>#</th><th>Empresa</th><th class="text-right">Alertas</th></tr></thead>
            <tbody>
              <tr v-for="(e, i) in empresasAlertas" :key="i">
                <td><span class="rank rank-red">{{ i + 1 }}</span></td>
                <td class="empresa-nombre">{{ e.nombre }}</td>
                <td class="text-right"><span class="badge-alerta">{{ e.alertas }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Usuarios activos — últimos 30 días</h2><p class="card-subtitle">Logins por día</p></div></div>
          <div class="chart-wrap" style="height:240px"><canvas ref="activosCanvas"/></div>
        </div>
      </div>

    </template>

    <!-- ══════════════ EMPRESA ══════════════ -->
    <template v-else>

      <!-- Sin ningún permiso de dashboard -->
      <div v-if="sinAcceso" class="sin-acceso-card">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        <p class="sin-acceso-titulo">Sin acceso al dashboard</p>
        <p class="sin-acceso-desc">Tu plan no incluye permisos para ver indicadores. Contacta al administrador para activarlos.</p>
      </div>

      <template v-else>

      <div v-if="accesosEmpresa.length" class="accesos accesos-top">
        <button v-for="a in accesosEmpresa" :key="a.path" class="acceso-top-btn" @click="router.push(ruta(a.path))">
          <div :class="['acceso-top-icon', a.color]"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="a.icon"/></div>
          <span class="acceso-label">{{ a.label }}</span>
        </button>
      </div>

      <!-- KPIs empresa (según permisos) -->
      <div class="kpis">
        <template v-if="permisosDash.flota">
          <div class="kpi-card">
            <div class="kpi-icon bg-purple"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/></svg></div>
            <div class="kpi-data"><span class="kpi-value">{{ kpisEmpresa.total_vehiculos }}</span><span class="kpi-label">Vehículos totales</span></div>
          </div>
        </template>
        <div v-if="permisosDash.conductores" class="kpi-card">
          <div class="kpi-icon bg-blue"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value">{{ kpisEmpresa.total_conductores }}</span><span class="kpi-label">Conductores</span></div>
        </div>
        <div v-if="permisosDash.mantenimiento" class="kpi-card" :class="{ 'kpi-alert': kpisEmpresa.mantenciones_pendientes > 0 }">
          <div class="kpi-icon" :class="kpisEmpresa.mantenciones_pendientes > 0 ? 'bg-amber' : 'bg-slate'"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value" :class="{ 'text-amber': kpisEmpresa.mantenciones_pendientes > 0 }">{{ kpisEmpresa.mantenciones_pendientes }}</span><span class="kpi-label">Mantenciones pendientes</span></div>
        </div>
        <div v-if="permisosDash.documentos" class="kpi-card" :class="{ 'kpi-alert kpi-alert-red': kpisEmpresa.docs_por_vencer > 0 }">
          <div class="kpi-icon" :class="kpisEmpresa.docs_por_vencer > 0 ? 'bg-red' : 'bg-slate'"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>
          <div class="kpi-data"><span class="kpi-value" :class="{ 'text-red': kpisEmpresa.docs_por_vencer > 0 }">{{ kpisEmpresa.docs_por_vencer }}</span><span class="kpi-label">Docs. por vencer (30d)</span></div>
        </div>
      </div>

      <!-- FLOTA: estado de la flota -->
      <div v-if="permisosDash.flota" class="charts-row" style="margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Estado de la flota</h2><p class="card-subtitle">Vehículos con y sin alertas activas</p></div></div>
          <div class="chart-wrap"><canvas ref="flotaCanvas"/></div>
        </div>
      </div>

      <!-- FLOTA: marcas | MANTENIMIENTO: mantenciones programadas -->
      <div v-if="permisosDash.flota || permisosDash.mantenimiento" class="charts-row" style="margin-bottom:1.25rem">
        <div v-if="permisosDash.flota" class="card">
          <div class="card-header"><div><h2 class="card-title">Marcas en la flota</h2><p class="card-subtitle">Top 8 marcas por cantidad de vehículos</p></div></div>
          <div class="chart-wrap" style="height:240px"><canvas ref="marcasFlotaCanvas"/></div>
        </div>
        <div v-if="permisosDash.mantenimiento" class="card">
          <div class="card-header">
            <div><h2 class="card-title">Mantenciones programadas</h2><p class="card-subtitle">Por {{ periodoInfo.gran }} — {{ periodoInfo.titulo }}</p></div>
            <div class="periodo-btns">
              <button v-for="p in PERIODOS" :key="p.key" :class="['periodo-btn', { active: periodoActivo === p.key }]" :disabled="cargandoGraficos" @click="cambiarPeriodo(p.key)">{{ p.label }}</button>
            </div>
          </div>
          <div class="chart-wrap" :class="{ 'chart-loading': cargandoGraficos }"><canvas ref="mantencionesCanvas"/></div>
        </div>
      </div>

      <!-- MANTENIMIENTO: estado + alertas tipo -->
      <div v-if="permisosDash.mantenimiento" class="charts-row" style="margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Mantenciones por estado</h2><p class="card-subtitle">Snapshot actual</p></div></div>
          <div class="chart-wrap"><canvas ref="mantEstadoCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Alertas predictivas vencidas</h2><p class="card-subtitle">Por tipo de mantenimiento</p></div><button class="btn-link" @click="router.push(ruta('/predictivo'))">Ver predictivo →</button></div>
          <div class="chart-wrap" style="height:240px"><canvas ref="alertasTipoCanvas"/></div>
        </div>
      </div>

      <!-- MANTENIMIENTO: predictivo progress -->
      <div v-if="permisosDash.mantenimiento" class="charts-row" style="margin-bottom:1.25rem;grid-template-columns:1fr 1fr">
        <div class="card" style="display:flex;flex-direction:column">
          <div class="card-header"><div><h2 class="card-title">Mantenimiento predictivo</h2><p class="card-subtitle">Cumplimiento de planes activos</p></div></div>
          <div style="padding:1.5rem;flex:1;display:flex;flex-direction:column;justify-content:center">
            <template v-if="widgetsEmpresa.predictivo && widgetsEmpresa.predictivo.total > 0">
              <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.5rem">
                <span style="font-size:2rem;font-weight:800;color:#111827">{{ widgetsEmpresa.predictivo.pct }}%</span>
                <span style="font-size:0.8125rem;color:#6B7280">al día</span>
              </div>
              <div style="height:10px;background:#F3F4F6;border-radius:999px;overflow:hidden;margin-bottom:1rem">
                <div :style="{ width: widgetsEmpresa.predictivo.pct + '%', height: '100%', background: widgetsEmpresa.predictivo.pct >= 80 ? '#059669' : widgetsEmpresa.predictivo.pct >= 50 ? '#F59E0B' : '#EF4444', borderRadius: '999px', transition: 'width 0.6s ease' }"/>
              </div>
              <div style="display:flex;gap:1.25rem">
                <div style="display:flex;align-items:center;gap:0.4rem"><span style="width:10px;height:10px;border-radius:50%;background:#059669;flex-shrink:0"/><span style="font-size:0.8125rem;color:#374151">Al día: {{ widgetsEmpresa.predictivo.al_dia }}</span></div>
                <div style="display:flex;align-items:center;gap:0.4rem"><span style="width:10px;height:10px;border-radius:50%;background:#EF4444;flex-shrink:0"/><span style="font-size:0.8125rem;color:#374151">Vencidas: {{ widgetsEmpresa.predictivo.vencidas }}</span></div>
              </div>
            </template>
            <div v-else style="color:#9CA3AF;font-size:0.875rem;text-align:center;padding:1rem 0">Sin planes de mantenimiento predictivo configurados</div>
          </div>
        </div>
        <div class="card widget-card">
          <div class="card-header"><h2 class="card-title">Próximos 7 días</h2><button class="btn-link" @click="router.push(ruta('/mantenciones'))">Ver todas →</button></div>
          <div v-if="!widgetsEmpresa.proximas_7_dias?.length" class="empty" style="padding:1rem 1.25rem;font-size:0.8125rem;color:#9CA3AF">Sin mantenciones en los próximos 7 días</div>
          <ul v-else class="proximas-list">
            <li v-for="m in widgetsEmpresa.proximas_7_dias" :key="m.id" class="proxima-item">
              <div class="proxima-fecha">{{ m.fecha?.slice(8,10) }}/{{ m.fecha?.slice(5,7) }}</div>
              <div class="proxima-info"><div class="proxima-tipo">{{ m.tipo }}</div><div class="proxima-vehiculo">{{ m.vehiculo }}</div></div>
              <span class="proxima-estado" :class="m.estado === 'en_proceso' ? 'estado-proceso' : 'estado-pendiente'">{{ m.estado === 'en_proceso' ? 'En proceso' : 'Pendiente' }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- FINANZAS: gastos 6M stacked + gastos 12M línea -->
      <div v-if="permisosDash.finanzas" class="charts-row" style="margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Gastos por categoría</h2><p class="card-subtitle">Últimos 6 meses — desglose por tipo</p></div></div>
          <div class="chart-wrap" style="height:260px"><canvas ref="gastosCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Tendencia de gasto total</h2><p class="card-subtitle">Evolución mensual — últimos 12 meses</p></div><button class="btn-link" @click="router.push(ruta('/finanzas'))">Ver finanzas →</button></div>
          <div class="chart-wrap" style="height:260px"><canvas ref="gastos12mCanvas"/></div>
        </div>
      </div>

      <!-- DOCUMENTOS: dona estado -->
      <div v-if="permisosDash.documentos" class="charts-row" style="margin-bottom:1.25rem;grid-template-columns:1fr 1fr">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Documentos por estado</h2><p class="card-subtitle">Vigentes, por vencer y vencidos</p></div><button class="btn-link" @click="router.push(ruta('/documentos'))">Ver documentos →</button></div>
          <div class="chart-wrap"><canvas ref="docsEstadoCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Información de documentos</h2><p class="card-subtitle">Estado documental de la flota</p></div></div>
          <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem">
            <div class="doc-stat-row">
              <span class="doc-dot" style="background:#059669"/>
              <span class="doc-label">Vigentes (más de 30 días)</span>
            </div>
            <div class="doc-stat-row">
              <span class="doc-dot" style="background:#F59E0B"/>
              <span class="doc-label">Por vencer (próximos 30 días)</span>
            </div>
            <div class="doc-stat-row">
              <span class="doc-dot" style="background:#EF4444"/>
              <span class="doc-label">Vencidos</span>
            </div>
            <p style="font-size:0.8rem;color:#9CA3AF;margin:0.5rem 0 0">Mantén los documentos al día para evitar infracciones.</p>
          </div>
        </div>
      </div>

      <!-- RUTAS: finalizadas/canceladas + km por mes -->
      <div v-if="permisosDash.rutas" class="charts-row" style="margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Rutas completadas vs canceladas</h2><p class="card-subtitle">Últimos 6 meses</p></div><button class="btn-link" @click="router.push(ruta('/rutas'))">Ver rutas →</button></div>
          <div class="chart-wrap" style="height:260px"><canvas ref="rutasCanvas"/></div>
        </div>
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Kilómetros recorridos</h2><p class="card-subtitle">Rutas finalizadas — últimos 6 meses</p></div></div>
          <div class="chart-wrap" style="height:260px"><canvas ref="kmMesCanvas"/></div>
        </div>
      </div>

      <!-- CONDUCTORES: top km -->
      <div v-if="permisosDash.conductores" class="charts-row" style="grid-template-columns:1fr;margin-bottom:1.25rem">
        <div class="card">
          <div class="card-header"><div><h2 class="card-title">Top conductores por km recorridos</h2><p class="card-subtitle">Rutas finalizadas — km acumulados</p></div><button class="btn-link" @click="router.push(ruta('/conductores'))">Ver conductores →</button></div>
          <div class="chart-wrap" style="height:200px"><canvas ref="conductoresCanvas"/></div>
          <div v-if="!hayConductoresKm" class="empty" style="padding:1.5rem">Sin rutas finalizadas con conductor asignado</div>
        </div>
      </div>

      <!-- Widgets inferiores: gasto mes + top vehículos -->
      <div v-if="permisosDash.finanzas" class="widgets-row">
        <div class="card widget-card">
          <div class="card-header"><h2 class="card-title">Gasto del mes</h2><button class="btn-link" @click="router.push(ruta('/finanzas'))">Ver finanzas →</button></div>
          <div style="padding:0 1.25rem 1.25rem">
            <div v-if="widgetsEmpresa.gasto_vs_presupuesto" class="gasto-presupuesto">
              <div class="gasto-cifra">${{ widgetsEmpresa.gasto_vs_presupuesto.gasto?.toLocaleString('es-CL') }}<span v-if="widgetsEmpresa.gasto_vs_presupuesto.presupuesto" class="gasto-de"> / ${{ widgetsEmpresa.gasto_vs_presupuesto.presupuesto.toLocaleString('es-CL') }}</span></div>
              <div v-if="widgetsEmpresa.gasto_vs_presupuesto.presupuesto" class="presup-barra-wrap">
                <div class="presup-barra"><div class="presup-barra-fill" :style="{ width: Math.min(widgetsEmpresa.gasto_vs_presupuesto.pct, 100) + '%', background: widgetsEmpresa.gasto_vs_presupuesto.pct >= 90 ? '#EF4444' : widgetsEmpresa.gasto_vs_presupuesto.pct >= 70 ? '#F59E0B' : '#4F46E5' }"/></div>
                <span class="presup-pct" :style="{ color: widgetsEmpresa.gasto_vs_presupuesto.pct >= 90 ? '#EF4444' : widgetsEmpresa.gasto_vs_presupuesto.pct >= 70 ? '#D97706' : '#374151' }">{{ widgetsEmpresa.gasto_vs_presupuesto.pct }}%</span>
              </div>
              <div v-else class="presup-sin">Sin presupuesto definido este mes</div>
            </div>
            <div v-else class="empty-widget">Sin datos de gastos</div>
          </div>
        </div>
        <div class="card widget-card">
          <div class="card-header"><h2 class="card-title">Top costo este mes</h2><button class="btn-link" @click="router.push(ruta('/reportes'))">Ver reporte →</button></div>
          <div v-if="!widgetsEmpresa.top_vehiculos_costo?.length" class="empty" style="padding:1rem 1.25rem;font-size:0.8125rem;color:#9CA3AF">Sin datos de gastos este mes</div>
          <ul v-else class="top-veh-list">
            <li v-for="(v, i) in widgetsEmpresa.top_vehiculos_costo" :key="v.vehiculo_id" class="top-veh-item">
              <span class="top-veh-rank">{{ i + 1 }}</span>
              <div class="top-veh-info"><div class="top-veh-patente">{{ v.patente }}</div><div class="top-veh-label">{{ v.label }}</div></div>
              <span class="top-veh-monto">${{ v.total.toLocaleString('es-CL') }}</span>
            </li>
          </ul>
        </div>
      </div>

      </template><!-- fin v-else sin-acceso -->

    </template>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }
.sin-acceso-card { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 4rem 2rem; background: #fff; border: 1px solid #E5E7EB; border-radius: 16px; margin-top: 1rem; }
.sin-acceso-card svg { width: 48px; height: 48px; color: #9CA3AF; }
.sin-acceso-titulo { font-size: 1.125rem; font-weight: 700; color: #374151; margin: 0; }
.sin-acceso-desc { font-size: 0.875rem; color: #9CA3AF; margin: 0; text-align: center; max-width: 360px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.75rem; gap: 1rem; }
.page-title    { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.btn-refresh { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; transition: all 0.15s; font-family: inherit; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-accent, #6366F1); color: var(--color-accent, #4F46E5); }
.btn-refresh:disabled { opacity: 0.5; cursor: default; }
.btn-refresh svg { width: 15px; height: 15px; }
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 3rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: var(--color-accent, #7C3AED); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.875rem 1rem; border-radius: 10px; font-size: 0.875rem; }
.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.2rem 1.25rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04); position: relative; transition: box-shadow 0.15s; }
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.kpi-alert     { border-color: #FDE68A; background: #FFFBEB; }
.kpi-alert-red { border-color: #FECACA !important; background: #FEF2F2 !important; }
.kpi-icon { width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.kpi-icon svg { width: 22px; height: 22px; }
.bg-purple  { background: #EDE9FE; color: #6D28D9; } .bg-indigo { background: #EEF2FF; color: #4338CA; }
.bg-blue    { background: #EFF6FF; color: #2563EB; } .bg-emerald { background: #ECFDF5; color: #059669; }
.bg-amber   { background: #FFFBEB; color: #D97706; } .bg-green  { background: #F0FDF4; color: #16A34A; }
.bg-red     { background: #FEF2F2; color: #DC2626; } .bg-slate  { background: #F1F5F9; color: #64748B; }
.kpi-data  { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.kpi-value { font-size: 1.75rem; font-weight: 700; color: #111827; line-height: 1; }
.kpi-label { font-size: 0.8rem; color: #6B7280; margin-top: 0.2rem; }
.kpi-sub   { font-size: 0.75rem; color: #9CA3AF; margin-top: 0.1rem; }
.text-amber { color: #D97706; } .text-green { color: #16A34A; } .text-red { color: #DC2626; }
.kpi-pct { position: absolute; top: 0.75rem; right: 0.75rem; font-size: 0.7rem; font-weight: 700; color: #059669; background: #ECFDF5; border-radius: 999px; padding: 0.15rem 0.5rem; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); overflow: hidden; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; gap: 1rem; }
.card-title    { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.2rem; }
.card-subtitle { font-size: 0.8rem; color: #9CA3AF; margin: 0; }
.btn-link { font-size: 0.8125rem; font-weight: 600; color: var(--color-accent, #4F46E5); background: none; border: none; cursor: pointer; padding: 0; white-space: nowrap; font-family: inherit; }
.btn-link:hover { text-decoration: underline; }
.periodo-btns { display: flex; gap: 0.2rem; background: #F3F4F6; border-radius: 8px; padding: 0.25rem; flex-shrink: 0; }
.periodo-btn { padding: 0.275rem 0.65rem; border-radius: 6px; border: none; font-size: 0.75rem; font-weight: 600; color: #6B7280; background: transparent; cursor: pointer; font-family: inherit; transition: all 0.15s; white-space: nowrap; }
.periodo-btn.active { background: #fff; color: var(--color-accent, #4F46E5); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.periodo-btn:hover:not(.active):not(:disabled) { color: #374151; }
.periodo-btn:disabled { opacity: 0.5; cursor: default; }
/* auto-fit: una fila con un solo card ocupa todo el ancho (sin hueco); con dos
   cards se reparten en dos columnas. Evita filas descuadradas cuando los permisos
   dejan un único gráfico en la fila. */
.charts-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.charts-global { grid-template-columns: 2fr 1fr; }
@media (max-width: 960px) { .charts-row, .charts-global { grid-template-columns: 1fr; } }
.chart-wrap { padding: 1.25rem 1.5rem; height: 240px; }
.chart-loading { opacity: 0.45; transition: opacity 0.2s; }
.bottom-row { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .bottom-row { grid-template-columns: 1fr; } }
.section-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.top-tabla { width: 100%; border-collapse: collapse; }
.top-tabla th { padding: 0.65rem 1.5rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.top-tabla td { padding: 0.8rem 1.5rem; font-size: 0.875rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.top-tabla tr:last-child td { border-bottom: none; }
.top-tabla tr:hover td { background: #FAFAFA; }
.rank { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: #EEF2FF; color: #4338CA; font-size: 0.7rem; font-weight: 700; }
.rank-red { background: #FEF2F2; color: #DC2626; }
.badge-alerta { display: inline-flex; align-items: center; justify-content: center; padding: 0.15rem 0.625rem; border-radius: 999px; background: #FEF2F2; color: #DC2626; font-size: 0.75rem; font-weight: 700; }
.empresa-nombre { font-weight: 500; color: #111827; }
.text-right { text-align: right; } .font-semibold { font-weight: 600; color: #111827; }
.empty { text-align: center; color: #9CA3AF; padding: 2rem !important; }
.accesos { display: grid; gap: 0.75rem; }
.accesos-2x2 { grid-template-columns: 1fr 1fr; }
.accesos-top { display: flex; gap: 0.625rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.acceso-top-btn { display: flex; align-items: center; gap: 0.625rem; padding: 0.55rem 1rem 0.55rem 0.65rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 10px; cursor: pointer; font-family: inherit; transition: all 0.15s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.acceso-top-btn:hover { border-color: var(--color-accent, #6366F1); box-shadow: 0 3px 8px rgba(99,102,241,0.12); transform: translateY(-1px); }
.acceso-top-icon { width: 28px; height: 28px; border-radius: 7px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.acceso-top-icon svg { width: 15px; height: 15px; }
.acceso-label { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.acceso-card { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; padding: 1.25rem 0.75rem; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; cursor: pointer; transition: all 0.15s; font-family: inherit; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.acceso-card:hover { border-color: var(--color-accent, #6366F1); box-shadow: 0 4px 12px rgba(99,102,241,0.12); transform: translateY(-1px); }
.acceso-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.acceso-icon svg { width: 22px; height: 22px; }
.ac-purple { background: #EDE9FE; color: #6D28D9; } .ac-blue  { background: #EFF6FF; color: #2563EB; }
.ac-amber  { background: #FFFBEB; color: #D97706; } .ac-slate { background: #F1F5F9; color: #475569; }
.ac-indigo { background: #EEF2FF; color: #4338CA; }
.widgets-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.25rem; margin-top: 0.5rem; }
@media (max-width: 900px) { .widgets-row { grid-template-columns: 1fr; } }
.widget-card { min-height: 180px; }
.gasto-presupuesto { display: flex; flex-direction: column; gap: 0.6rem; }
.gasto-cifra { font-size: 1.5rem; font-weight: 800; color: #111827; }
.gasto-de { font-size: 0.9rem; font-weight: 500; color: #9CA3AF; }
.presup-barra-wrap { display: flex; align-items: center; gap: 0.75rem; }
.presup-barra { flex: 1; height: 8px; background: #F3F4F6; border-radius: 999px; overflow: hidden; }
.presup-barra-fill { height: 100%; border-radius: 999px; transition: width 0.6s ease; }
.presup-pct { font-size: 0.8125rem; font-weight: 700; min-width: 36px; text-align: right; }
.presup-sin { font-size: 0.8rem; color: #9CA3AF; }
.empty-widget { font-size: 0.8125rem; color: #9CA3AF; }
.proximas-list { list-style: none; margin: 0; padding: 0; }
.proxima-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 1.25rem; border-bottom: 1px solid #F9FAFB; }
.proxima-item:last-child { border-bottom: none; }
.proxima-fecha { font-size: 0.75rem; font-weight: 700; color: #4F46E5; min-width: 32px; text-align: center; background: #EEF2FF; border-radius: 6px; padding: 0.25rem 0.35rem; }
.proxima-info { flex: 1; min-width: 0; }
.proxima-tipo { font-size: 0.8125rem; font-weight: 600; color: #111827; }
.proxima-vehiculo { font-size: 0.75rem; color: #9CA3AF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.proxima-estado { font-size: 0.7rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 999px; white-space: nowrap; }
.estado-proceso { background: #EFF6FF; color: #2563EB; }
.estado-pendiente { background: #FFF7ED; color: #C2410C; }
.top-veh-list { list-style: none; margin: 0; padding: 0; }
.top-veh-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.65rem 1.25rem; border-bottom: 1px solid #F9FAFB; }
.top-veh-item:last-child { border-bottom: none; }
.top-veh-rank { width: 22px; height: 22px; border-radius: 50%; background: #EEF2FF; color: #4F46E5; font-size: 0.72rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.top-veh-info { flex: 1; min-width: 0; }
.top-veh-patente { font-size: 0.8125rem; font-weight: 700; color: #111827; }
.top-veh-label { font-size: 0.75rem; color: #9CA3AF; }
.top-veh-monto { font-size: 0.8125rem; font-weight: 700; color: #374151; white-space: nowrap; }
.doc-stat-row { display: flex; align-items: center; gap: 0.75rem; }
.doc-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-header { flex-direction: column; gap: 0.625rem; }
  .page-header > div { min-width: 0; }
  .page-title { font-size: 1.25rem; }
  .kpis { grid-template-columns: repeat(2, 1fr); gap: 0.625rem; }
  .kpi-card { padding: 0.875rem 1rem; gap: 0.625rem; }
  .kpi-value { font-size: 1.375rem; }
  .kpi-icon { width: 38px; height: 38px; }
  .kpi-icon svg { width: 18px; height: 18px; }
  .charts-row, .charts-global, .bottom-row, .widgets-row { grid-template-columns: 1fr !important; }
  .chart-wrap { height: 200px !important; padding: 0.75rem 1rem; }
  .card-header { padding: 1rem; flex-wrap: wrap; }
  .periodo-btns { width: 100%; justify-content: flex-start; }
  .accesos-2x2 { grid-template-columns: repeat(2, 1fr); }
  .accesos-top { gap: 0.4rem; }
  .acceso-top-btn { padding: 0.45rem 0.75rem 0.45rem 0.5rem; font-size: 0.8rem; }
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
.doc-label { font-size: 0.875rem; color: #374151; }
</style>
