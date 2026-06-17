<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { tienePermiso } from '../../utils/permisos.js'
import { useToast } from '../../utils/useToast.js'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const toast = useToast()

// (vista de página única — sin tabs)

// ── Estado
const cargando         = ref(false)
const exportando       = ref(false)
const datosMantencion  = ref(null)
const datosFlota       = ref(null)
const datosTco         = ref(null)
const datosConductores = ref(null)
const datosDocumentos  = ref(null)
const datosCombustible = ref(null)
const datosPpto        = ref(null)
const datosRutas       = ref(null)
const datosSolicitudes = ref(null)
const vehiculos        = ref([])

// Permisos por módulo: ocultan la sección completa (KPIs, skeletons y bloques)
// cuando el plan no tiene el permiso, sin dejar espacios vacíos.
const puedeMant  = computed(() => tienePermiso('mantenciones.ver'))
const puedeFlota = computed(() => tienePermiso('flotas.ver'))
const puedeFin   = computed(() => tienePermiso('finanzas.ver'))
const puedeCond  = computed(() => tienePermiso('conductores.ver'))
const puedeDocs  = computed(() => tienePermiso('documentos.ver'))
const puedeRutas = computed(() => tienePermiso('rutas.ver'))
const puedeSolic = computed(() => tienePermiso('solicitudes.ver'))

// ── Filtros mantenciones
const anioActual = new Date().getFullYear()
const anioSel    = ref(anioActual)
const mesSel     = ref(0)
const vehiculoSel = ref('')
const anios      = [anioActual, anioActual - 1, anioActual - 2]
const meses = [
  { value: 0, label: 'Todos los meses' },
  { value: 1,  label: 'Enero'      }, { value: 2,  label: 'Febrero'    },
  { value: 3,  label: 'Marzo'      }, { value: 4,  label: 'Abril'      },
  { value: 5,  label: 'Mayo'       }, { value: 6,  label: 'Junio'      },
  { value: 7,  label: 'Julio'      }, { value: 8,  label: 'Agosto'     },
  { value: 9,  label: 'Septiembre' }, { value: 10, label: 'Octubre'    },
  { value: 11, label: 'Noviembre'  }, { value: 12, label: 'Diciembre'  },
]

// ── Formatters
const NOMBRE_MES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
function labelMes(m) { return NOMBRE_MES[m - 1] || '' }
function clp(val) {
  if (!val) return '$0'
  return '$' + Number(val).toLocaleString('es-CL')
}
function fechaCorta(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const ESTADO = {
  pendiente:  { bg: '#F3F4F6', text: '#6B7280', label: 'Pendiente'   },
  en_proceso: { bg: '#EFF6FF', text: '#2563EB', label: 'En proceso'  },
  realizada:  { bg: '#ECFDF5', text: '#059669', label: 'Realizada'   },
  cancelada:  { bg: '#FEF2F2', text: '#DC2626', label: 'Cancelada'   },
}

// ── Charts (originales)
const chartCanvas      = ref(null)
const chartTcoCanvas   = ref(null)
const chartPptoCanvas  = ref(null)
const chartCombBar     = ref(null)
const chartCombLine    = ref(null)
let chartInstance      = null
let chartTcoInstance   = null
let chartPptoInstance  = null
let chartCombBarInst   = null
let chartCombLineInst  = null

// ── Charts (nuevos)
const chartDonaGastos  = ref(null)   // dona distribución gastos por categoría
const chartGastoMes    = ref(null)   // línea gasto total mensual
const chartRutasMes    = ref(null)   // barras rutas finalizadas vs canceladas
const chartRutasTipo   = ref(null)   // dona rutas por tipo
const chartSolicMes    = ref(null)   // barras solicitudes por tipo/mes
const chartSolicTipo   = ref(null)   // dona solicitudes por tipo
const chartPptoAcum    = ref(null)   // línea presupuesto acumulado vs gasto acumulado
let chartDonaGastosInst  = null
let chartGastoMesInst    = null
let chartRutasMesInst    = null
let chartRutasTipoInst   = null
let chartSolicMesInst    = null
let chartSolicTipoInst   = null
let chartPptoAcumInst    = null

function crearChart() {
  if (!chartCanvas.value || !datosMantencion.value?.resumen?.por_mes?.length) return
  if (!chartCanvas.value.offsetParent && chartCanvas.value.offsetHeight === 0) return
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }

  const pm     = datosMantencion.value.resumen.por_mes
  const labels = pm.map(m => `${labelMes(m.mes)} ${m.anio}`)
  const costos = pm.map(m => m.costo)
  const cantidades = pm.map(m => m.cantidad)

  chartInstance = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Costo total',
          data: costos,
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
          yAxisID: 'y',
        },
        {
          label: 'Cantidad',
          data: cantidades,
          borderColor: '#059669',
          backgroundColor: 'rgba(5,150,105,0.05)',
          borderWidth: 2,
          pointBackgroundColor: '#059669',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.35,
          fill: false,
          yAxisID: 'y2',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true, pointStyleWidth: 10, font: { size: 12 }, padding: 16 } },
        tooltip: {
          callbacks: {
            label: (ctx) => ctx.dataset.label === 'Costo total'
              ? ` Costo: ${clp(ctx.parsed.y)}`
              : ` Cantidad: ${ctx.parsed.y}`,
          },
        },
      },
      scales: {
        x:  { grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 }, color: '#6B7280' } },
        y:  { position: 'left',  grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 }, color: '#6B7280', callback: (v) => clp(v) } },
        y2: { position: 'right', grid: { drawOnChartArea: false }, ticks: { font: { size: 11 }, color: '#059669', stepSize: 1 }, title: { display: true, text: 'Cantidad', color: '#059669', font: { size: 11 } } },
      },
    },
  })
}

watch(datosMantencion, () => { setTimeout(crearChart, 80) }, { deep: true, flush: 'post' })

function crearChartTco() {
  if (!chartTcoCanvas.value || !datosTco.value?.vehiculos?.length) return
  if (!chartTcoCanvas.value.offsetParent && chartTcoCanvas.value.offsetHeight === 0) return
  if (chartTcoInstance) { chartTcoInstance.destroy(); chartTcoInstance = null }
  const top10   = datosTco.value.vehiculos.slice(0, 10)
  const labels  = top10.map(v => v.patente)
  const gastos  = top10.map(v => v.gastos_total)
  const mants   = top10.map(v => v.mantenciones_total)
  chartTcoInstance = new Chart(chartTcoCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Gastos op.',    data: gastos, backgroundColor: '#6366F1', borderRadius: 4, stack: 'tco' },
        { label: 'Mantenciones', data: mants,  backgroundColor: '#F59E0B', borderRadius: 4, stack: 'tco' },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true, padding: 12 } },
        tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${clp(c.parsed.x)}` } },
      },
      scales: {
        x: { stacked: true, ticks: { callback: (v) => clp(v), font: { size: 10 }, color: '#6B7280' }, grid: { color: '#F3F4F6' } },
        y: { stacked: true, ticks: { font: { size: 11 }, color: '#374151' }, grid: { display: false } },
      },
    },
  })
}
watch(datosTco, () => { setTimeout(crearChartTco, 80) }, { deep: true, flush: 'post' })

function crearChartPpto() {
  if (!chartPptoCanvas.value || !datosPpto.value?.meses?.length) return
  if (chartPptoCanvas.value.offsetHeight === 0) return
  if (chartPptoInstance) { chartPptoInstance.destroy(); chartPptoInstance = null }
  const meses   = datosPpto.value.meses
  const labels  = meses.map(m => m.mes_label)
  const ppto    = meses.map(m => m.presupuesto)
  const gasto   = meses.map(m => m.gasto_real)
  chartPptoInstance = new Chart(chartPptoCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Presupuesto', data: ppto,  backgroundColor: '#E5E7EB', borderRadius: 4, barPercentage: 0.6 },
        { label: 'Gasto real',  data: gasto, backgroundColor: '#4F46E5', borderRadius: 4, barPercentage: 0.6 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true, padding: 12 } },
        tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${clp(c.parsed.y)}` } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#6B7280' } },
        y: { ticks: { callback: (v) => clp(v), font: { size: 10 }, color: '#6B7280' }, grid: { color: '#F3F4F6' } },
      },
    },
  })
}
watch([datosMantencion, datosPpto], () => { setTimeout(crearChartPpto, 80) }, { deep: true, flush: 'post' })

function crearChartCombustible() {
  if (!datosCombustible.value) return
  if (chartCombBar.value && datosCombustible.value.por_vehiculo?.length) {
    if (chartCombBar.value.offsetHeight === 0) return
    if (chartCombBarInst) { chartCombBarInst.destroy(); chartCombBarInst = null }
    const top5 = datosCombustible.value.por_vehiculo.slice(0, 5)
    chartCombBarInst = new Chart(chartCombBar.value, {
      type: 'bar',
      data: {
        labels: top5.map(v => v.patente),
        datasets: [{ label: 'Gasto combustible', data: top5.map(v => v.gasto_total), backgroundColor: '#F59E0B', borderRadius: 4, barThickness: 28 }],
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${clp(c.parsed.x)}` } } },
        scales: {
          x: { ticks: { callback: (v) => clp(v), font: { size: 10 }, color: '#6B7280' }, grid: { color: '#F3F4F6' } },
          y: { ticks: { font: { size: 11 }, color: '#374151' }, grid: { display: false } },
        },
      },
    })
  }
  if (chartCombLine.value && datosCombustible.value.por_mes?.length) {
    if (chartCombLine.value.offsetHeight === 0) return
    if (chartCombLineInst) { chartCombLineInst.destroy(); chartCombLineInst = null }
    const meses = datosCombustible.value.por_mes
    chartCombLineInst = new Chart(chartCombLine.value, {
      type: 'line',
      data: {
        labels: meses.map(m => `${m.mes_label} ${String(m.anio).slice(2)}`),
        datasets: [{ label: 'Gasto combustible', data: meses.map(m => m.gasto), borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,0.07)', borderWidth: 2.5, pointRadius: 4, pointBackgroundColor: '#F59E0B', tension: 0.35, fill: true }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${clp(c.parsed.y)}` } } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#6B7280' } },
          y: { ticks: { callback: (v) => clp(v), font: { size: 10 }, color: '#6B7280' }, grid: { color: '#F3F4F6' } },
        },
      },
    })
  }
}
watch(datosCombustible, () => { setTimeout(crearChartCombustible, 80) }, { deep: true, flush: 'post' })

// ── Paleta de colores compartida
const PALETA_CATS = {
  combustible: '#F59E0B', mantencion: '#6366F1', multa: '#EF4444',
  peaje: '#8B5CF6', seguro: '#10B981', otro: '#9CA3AF',
}
const PALETA_TIPO_RUTA = { carga: '#6366F1', personas: '#10B981' }
const PALETA_SOLICITUDES = {
  mantencion: '#6366F1', combustible: '#F59E0B',
  incidencia: '#EF4444', documento: '#10B981',
}

// ── Funciones de gráficos nuevos
function crearChartDonaGastos() {
  if (!chartDonaGastos.value || !datosTco.value?.gastos_categoria) return
  if (chartDonaGastos.value.offsetHeight === 0) return
  if (chartDonaGastosInst) { chartDonaGastosInst.destroy(); chartDonaGastosInst = null }
  const cats  = Object.entries(datosTco.value.gastos_categoria).filter(([,v]) => v > 0)
  if (!cats.length) return
  chartDonaGastosInst = new Chart(chartDonaGastos.value, {
    type: 'doughnut',
    data: {
      labels: cats.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1)),
      datasets: [{ data: cats.map(([,v]) => v), backgroundColor: cats.map(([k]) => PALETA_CATS[k] || '#9CA3AF'), borderWidth: 2, borderColor: '#fff' }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '62%',
      plugins: {
        legend: { position: 'right', labels: { font: { size: 11 }, usePointStyle: true, padding: 12 } },
        tooltip: { callbacks: { label: (c) => ` ${c.label}: ${clp(c.parsed)}` } },
      },
    },
  })
}

function crearChartGastoMes() {
  if (!chartGastoMes.value || !datosPpto.value?.meses) return
  if (chartGastoMes.value.offsetHeight === 0) return
  if (chartGastoMesInst) { chartGastoMesInst.destroy(); chartGastoMesInst = null }
  const meses = datosPpto.value.meses
  chartGastoMesInst = new Chart(chartGastoMes.value, {
    type: 'line',
    data: {
      labels: meses.map(m => m.mes_label),
      datasets: [{ label: 'Gasto total', data: meses.map(m => m.gasto_real), borderColor: '#6366F1', backgroundColor: 'rgba(99,102,241,0.07)', borderWidth: 2.5, pointRadius: 4, tension: 0.35, fill: true }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${clp(c.parsed.y)}` } } },
      scales: {
        x: { grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 } } },
        y: { grid: { color: '#F3F4F6' }, ticks: { callback: (v) => clp(v), font: { size: 10 } } },
      },
    },
  })
}

function crearChartPptoAcum() {
  if (!chartPptoAcum.value || !datosPpto.value?.meses) return
  if (chartPptoAcum.value.offsetHeight === 0) return
  if (chartPptoAcumInst) { chartPptoAcumInst.destroy(); chartPptoAcumInst = null }
  const meses = datosPpto.value.meses
  let acumPpto = 0, acumGasto = 0
  const labAcumPpto = [], labAcumGasto = []
  meses.forEach(m => {
    acumPpto  += m.presupuesto; acumGasto += m.gasto_real
    labAcumPpto.push(acumPpto); labAcumGasto.push(acumGasto)
  })
  chartPptoAcumInst = new Chart(chartPptoAcum.value, {
    type: 'line',
    data: {
      labels: meses.map(m => m.mes_label),
      datasets: [
        { label: 'Presupuesto acumulado', data: labAcumPpto, borderColor: '#E5E7EB', backgroundColor: 'transparent', borderWidth: 2, borderDash: [5,4], pointRadius: 3, tension: 0 },
        { label: 'Gasto acumulado',       data: labAcumGasto, borderColor: '#4F46E5', backgroundColor: 'rgba(79,70,229,0.06)', borderWidth: 2.5, pointRadius: 4, tension: 0.2, fill: true },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true } }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${clp(c.parsed.y)}` } } },
      scales: {
        x: { grid: { color: '#F3F4F6' }, ticks: { font: { size: 11 } } },
        y: { grid: { color: '#F3F4F6' }, ticks: { callback: (v) => clp(v), font: { size: 10 } } },
      },
    },
  })
}

function crearChartRutasMes() {
  if (!chartRutasMes.value || !datosRutas.value?.por_mes) return
  if (chartRutasMes.value.offsetHeight === 0) return
  if (chartRutasMesInst) { chartRutasMesInst.destroy(); chartRutasMesInst = null }
  const meses = datosRutas.value.por_mes
  chartRutasMesInst = new Chart(chartRutasMes.value, {
    type: 'bar',
    data: {
      labels: meses.map(m => `${m.mes_label} ${String(m.anio).slice(2)}`),
      datasets: [
        { label: 'Finalizadas', data: meses.map(m => m.finalizadas), backgroundColor: '#10B981', borderRadius: 4, stack: 'rutas' },
        { label: 'Canceladas',  data: meses.map(m => m.canceladas),  backgroundColor: '#EF4444', borderRadius: 4, stack: 'rutas' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { stacked: true, grid: { color: '#F3F4F6' }, ticks: { stepSize: 1, font: { size: 10 } } },
      },
    },
  })
}

function crearChartRutasTipo() {
  if (!chartRutasTipo.value || !datosRutas.value?.resumen?.por_tipo) return
  if (chartRutasTipo.value.offsetHeight === 0) return
  if (chartRutasTipoInst) { chartRutasTipoInst.destroy(); chartRutasTipoInst = null }
  const tipos = Object.entries(datosRutas.value.resumen.por_tipo).filter(([,v]) => v > 0)
  if (!tipos.length) return
  chartRutasTipoInst = new Chart(chartRutasTipo.value, {
    type: 'doughnut',
    data: {
      labels: tipos.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1)),
      datasets: [{ data: tipos.map(([,v]) => v), backgroundColor: tipos.map(([k]) => PALETA_TIPO_RUTA[k] || '#9CA3AF'), borderWidth: 2, borderColor: '#fff' }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '62%',
      plugins: { legend: { position: 'right', labels: { font: { size: 11 }, usePointStyle: true } } },
    },
  })
}

function crearChartSolicMes() {
  if (!chartSolicMes.value || !datosSolicitudes.value?.por_mes) return
  if (chartSolicMes.value.offsetHeight === 0) return
  if (chartSolicMesInst) { chartSolicMesInst.destroy(); chartSolicMesInst = null }
  const meses = datosSolicitudes.value.por_mes
  const TIPOS = ['mantencion', 'combustible', 'incidencia', 'documento']
  const LABELS = { mantencion: 'Mantención', combustible: 'Combustible', incidencia: 'Incidencia', documento: 'Documento' }
  chartSolicMesInst = new Chart(chartSolicMes.value, {
    type: 'bar',
    data: {
      labels: meses.map(m => `${m.mes_label} ${String(m.anio).slice(2)}`),
      datasets: TIPOS.map(t => ({
        label: LABELS[t], data: meses.map(m => m[t] || 0),
        backgroundColor: PALETA_SOLICITUDES[t], borderRadius: 4, stack: 'solic',
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { stacked: true, grid: { color: '#F3F4F6' }, ticks: { stepSize: 1, font: { size: 10 } } },
      },
    },
  })
}

function crearChartSolicTipo() {
  if (!chartSolicTipo.value || !datosSolicitudes.value?.resumen?.por_tipo) return
  if (chartSolicTipo.value.offsetHeight === 0) return
  if (chartSolicTipoInst) { chartSolicTipoInst.destroy(); chartSolicTipoInst = null }
  const tipos = Object.entries(datosSolicitudes.value.resumen.por_tipo).filter(([,v]) => v > 0)
  if (!tipos.length) return
  const LABELS = { mantencion: 'Mantención', combustible: 'Combustible', incidencia: 'Incidencia', documento: 'Documento' }
  chartSolicTipoInst = new Chart(chartSolicTipo.value, {
    type: 'doughnut',
    data: {
      labels: tipos.map(([k]) => LABELS[k] || k),
      datasets: [{ data: tipos.map(([,v]) => v), backgroundColor: tipos.map(([k]) => PALETA_SOLICITUDES[k] || '#9CA3AF'), borderWidth: 2, borderColor: '#fff' }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '62%',
      plugins: { legend: { position: 'right', labels: { font: { size: 11 }, usePointStyle: true } } },
    },
  })
}

// ── Carga de datos
async function cargarVehiculos() {
  const res = await apiFetch('/api/empresa/vehiculos/')
  if (res.ok) vehiculos.value = await res.json()
}

async function cargarMantencion() {
  if (!tienePermiso('mantenciones.ver')) return
  cargando.value = true
  try {
    let url = `/api/empresa/reportes/mantencion/?anio=${anioSel.value}`
    if (mesSel.value)    url += `&mes=${mesSel.value}`
    if (vehiculoSel.value) url += `&vehiculo_id=${vehiculoSel.value}`
    const res = await apiFetch(url)
    if (res.ok) datosMantencion.value = await res.json()
    else toast.error('Error al cargar el reporte de mantenciones.')
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
  }
}

async function cargarFlota() {
  if (!tienePermiso('flotas.ver')) return
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/reportes/flota/')
    if (res.ok) datosFlota.value = await res.json()
    else toast.error('Error al cargar el reporte de flota.')
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
  }
}

// ── Exportar
async function exportar(tipo) {
  exportando.value = true
  try {
    let url = `/api/empresa/reportes/exportar/?tipo=${tipo}`
    if (tipo === 'mantencion') {
      url += `&anio=${anioSel.value}`
      if (mesSel.value)    url += `&mes=${mesSel.value}`
      if (vehiculoSel.value) url += `&vehiculo_id=${vehiculoSel.value}`
    }
    const res = await apiFetch(url)
    if (!res.ok) return toast.error('Error al exportar.')
    const blob = await res.blob()
    const a    = document.createElement('a')
    a.href     = URL.createObjectURL(blob)
    a.download = `reporte_${tipo}_${anioSel.value}.xlsx`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    toast.error('Error al exportar.')
  } finally {
    exportando.value = false
  }
}

// ── Ordenación tabla flota
const ordenCampo = ref('patente')
const ordenDesc  = ref(false)
const flotaOrdenada = computed(() => {
  if (!datosFlota.value?.vehiculos) return []
  return [...datosFlota.value.vehiculos].sort((a, b) => {
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
  else { ordenCampo.value = campo; ordenDesc.value = false }
}

function flechaOrden(campo) {
  if (ordenCampo.value !== campo) return ''
  return ordenDesc.value ? ' ↓' : ' ↑'
}

async function cargarTco() {
  if (!tienePermiso('finanzas.ver')) return
  cargando.value = true
  try {
    let url = `/api/empresa/reportes/tco/?anio=${anioSel.value}`
    if (mesSel.value) url += `&mes=${mesSel.value}`
    const res = await apiFetch(url)
    if (res.ok) datosTco.value = await res.json()
    else toast.error('Error al cargar el reporte TCO.')
  } catch { toast.error('Error de conexión.') }
  finally { cargando.value = false }
}

async function cargarConductores() {
  if (!tienePermiso('conductores.ver')) return
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/reportes/conductores/')
    if (res.ok) datosConductores.value = await res.json()
    else toast.error('Error al cargar el reporte de conductores.')
  } catch { toast.error('Error de conexión.') }
  finally { cargando.value = false }
}

async function cargarDocumentos() {
  if (!tienePermiso('documentos.ver')) return
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/reportes/documentos/')
    if (res.ok) datosDocumentos.value = await res.json()
    else toast.error('Error al cargar el reporte de documentos.')
  } catch { toast.error('Error de conexión.') }
  finally { cargando.value = false }
}

async function cargarCombustible() {
  if (!tienePermiso('finanzas.ver')) return
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/reportes/combustible/')
    if (res.ok) datosCombustible.value = await res.json()
    else toast.error('Error al cargar el reporte de combustible.')
  } catch { toast.error('Error de conexión.') }
  finally { cargando.value = false }
}

async function cargarPpto() {
  if (!tienePermiso('finanzas.ver')) return
  try {
    const res = await apiFetch('/api/empresa/reportes/presupuesto/')
    if (res.ok) datosPpto.value = await res.json()
  } catch { /* silencioso — se muestra en contexto de mantenciones */ }
}

async function cargarRutas() {
  if (!tienePermiso('rutas.ver')) return
  try {
    const res = await apiFetch('/api/empresa/reportes/rutas/')
    if (res.ok) datosRutas.value = await res.json()
  } catch { /* silencioso */ }
}

async function cargarSolicitudes() {
  if (!tienePermiso('solicitudes.ver')) return
  try {
    const res = await apiFetch('/api/empresa/reportes/solicitudes/')
    if (res.ok) datosSolicitudes.value = await res.json()
  } catch { /* silencioso */ }
}

function exportarTco() {
  if (!datosTco.value?.vehiculos) return
  const rows = [
    ['Patente', 'Marca/Modelo', 'Conductor', 'KM', 'Gastos Operativos', 'Mantenciones', 'TCO Total', 'Costo/KM'],
    ...datosTco.value.vehiculos.map(v => [
      v.patente, `${v.marca} ${v.modelo}`, v.conductor || '—',
      v.km_actuales || 0, v.gastos_total, v.mantenciones_total, v.tco_total,
      v.costo_por_km ?? '—',
    ]),
  ]
  const contenido = 'sep=;\n' + rows.map(r => r.join(';')).join('\n')
  const bom  = new Uint8Array([0xEF, 0xBB, 0xBF])
  const blob = new Blob([bom, new TextEncoder().encode(contenido)], { type: 'text/csv;charset=utf-8;' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `reporte_tco_${anioSel.value}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function exportarConductores() {
  if (!datosConductores.value?.conductores) return
  const rows = [
    ['Nombre', 'RUT', 'Vehículo Asignado', 'Docs Vigentes', 'Docs Por Vencer', 'Docs Vencidos', 'Estado Docs', 'Gastos Asociados'],
    ...datosConductores.value.conductores.map(c => [
      c.nombre, c.rut, c.vehiculo_asignado || '—',
      c.docs_vigentes, c.docs_por_vencer, c.docs_vencidos, c.estado_docs, c.gastos_total,
    ]),
  ]
  const contenido = 'sep=;\n' + rows.map(r => r.join(';')).join('\n')
  const bom  = new Uint8Array([0xEF, 0xBB, 0xBF])
  const blob = new Blob([bom, new TextEncoder().encode(contenido)], { type: 'text/csv;charset=utf-8;' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = 'reporte_conductores.csv'
  a.click()
}

// ── Ordenación TCO
const tcoOrdenCampo = ref('tco_total')
const tcoOrdenDesc  = ref(true)
const tcoOrdenada = computed(() => {
  if (!datosTco.value?.vehiculos) return []
  return [...datosTco.value.vehiculos].sort((a, b) => {
    const va = a[tcoOrdenCampo.value]; const vb = b[tcoOrdenCampo.value]
    const cmp = (va == null ? -1 : vb == null ? 1 : va < vb ? -1 : va > vb ? 1 : 0)
    return tcoOrdenDesc.value ? -cmp : cmp
  })
})

// ── Watchers
watch([anioSel, mesSel, vehiculoSel], cargarMantencion)
watch([anioSel, mesSel], cargarTco)

// Watches nuevos gráficos
watch(datosTco,         () => { setTimeout(crearChartDonaGastos, 80) }, { deep: true, flush: 'post' })
watch(datosPpto,        () => { setTimeout(crearChartGastoMes,   80); setTimeout(crearChartPptoAcum, 80) }, { deep: true, flush: 'post' })
watch(datosRutas,       () => { setTimeout(crearChartRutasMes,   80); setTimeout(crearChartRutasTipo, 80) }, { deep: true, flush: 'post' })
watch(datosSolicitudes, () => { setTimeout(crearChartSolicMes,   80); setTimeout(crearChartSolicTipo, 80) }, { deep: true, flush: 'post' })

// ── Lifecycle — carga todo de una vez (vista de página única)
onMounted(async () => {
  await Promise.all([
    cargarVehiculos(),
    cargarMantencion(),
    cargarPpto(),
    cargarFlota(),
    cargarTco(),
    cargarConductores(),
    cargarDocumentos(),
    cargarCombustible(),
    cargarRutas(),
    cargarSolicitudes(),
  ])
})

onUnmounted(() => {
  [
    chartInstance, chartTcoInstance, chartPptoInstance,
    chartCombBarInst, chartCombLineInst,
    chartDonaGastosInst, chartGastoMesInst, chartPptoAcumInst,
    chartRutasMesInst, chartRutasTipoInst,
    chartSolicMesInst, chartSolicTipoInst,
  ].forEach(c => { try { c?.destroy() } catch { /* noop */ } })
})

function diasSinMant(isoFecha) {
  if (!isoFecha) return null
  return Math.floor((Date.now() - new Date(isoFecha).getTime()) / 86400000)
}

// ── Max para barra de tipos
const maxCostoTipo = computed(() => {
  const tipos = datosMantencion.value?.resumen?.por_tipo || []
  return Math.max(1, ...tipos.map(t => t.costo))
})
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div>
        <h1 class="titulo">Reportes</h1>
        <p class="subtitulo">Análisis consolidado de mantenciones y estado de la flota</p>
      </div>
    </div>

    <!-- ── KPIs globales ─────────────────────────────────────────────────── -->
    <div class="kpis-globales">

      <!-- Mantenciones -->
      <template v-if="datosMantencion">
        <div class="kpi-g"><span class="kpi-tag">Mantenciones</span><span class="kpi-value">{{ datosMantencion.resumen.total }}</span><span class="kpi-label">Total mantenciones</span></div>
        <div class="kpi-g"><span class="kpi-tag">Mantenciones</span><span class="kpi-value">{{ clp(datosMantencion.resumen.costo_total) }}</span><span class="kpi-label">Costo total</span></div>
        <div class="kpi-g"><span class="kpi-tag">Mantenciones</span><span class="kpi-value">{{ clp(datosMantencion.resumen.costo_promedio) }}</span><span class="kpi-label">Costo promedio</span></div>
        <div class="kpi-g"><span class="kpi-tag">Mantenciones</span><span class="kpi-value" style="color:#059669">{{ datosMantencion.resumen.por_estado.realizada }}</span><span class="kpi-label">Realizadas</span></div>
      </template>
      <template v-else-if="puedeMant"><div v-for="i in 4" :key="'mant'+i" class="kpi-skeleton"></div></template>

      <!-- Flota -->
      <template v-if="datosFlota">
        <div class="kpi-g"><span class="kpi-tag">Flota</span><span class="kpi-value">{{ datosFlota.resumen.total }}</span><span class="kpi-label">Vehículos activos</span></div>
        <div class="kpi-g"><span class="kpi-tag">Flota</span><span class="kpi-value" :style="datosFlota.resumen.con_docs_vencidos > 0 ? 'color:#DC2626' : ''">{{ datosFlota.resumen.con_docs_vencidos }}</span><span class="kpi-label">Con docs vencidos</span></div>
        <div class="kpi-g"><span class="kpi-tag">Flota</span><span class="kpi-value" :style="datosFlota.resumen.sin_conductor > 0 ? 'color:#D97706' : ''">{{ datosFlota.resumen.sin_conductor }}</span><span class="kpi-label">Sin conductor</span></div>
      </template>
      <template v-else-if="puedeFlota"><div v-for="i in 3" :key="'flota'+i" class="kpi-skeleton"></div></template>

      <!-- TCO -->
      <template v-if="datosTco">
        <div class="kpi-g"><span class="kpi-tag">TCO</span><span class="kpi-value">{{ clp(datosTco.resumen.total_gastos) }}</span><span class="kpi-label">Gastos operativos</span></div>
        <div class="kpi-g"><span class="kpi-tag">TCO</span><span class="kpi-value">{{ clp(datosTco.resumen.total_mant) }}</span><span class="kpi-label">Costos mantención</span></div>
        <div class="kpi-g"><span class="kpi-tag">TCO</span><span class="kpi-value">{{ clp(datosTco.resumen.costo_promedio) }}</span><span class="kpi-label">TCO promedio/vehículo</span></div>
      </template>
      <template v-else-if="puedeFin"><div v-for="i in 3" :key="'tco'+i" class="kpi-skeleton"></div></template>

      <!-- Conductores -->
      <template v-if="datosConductores">
        <div class="kpi-g"><span class="kpi-tag">Conductores</span><span class="kpi-value">{{ datosConductores.resumen.total }}</span><span class="kpi-label">Total conductores</span></div>
        <div class="kpi-g"><span class="kpi-tag">Conductores</span><span class="kpi-value" :style="datosConductores.resumen.sin_vehiculo > 0 ? 'color:#D97706' : ''">{{ datosConductores.resumen.sin_vehiculo }}</span><span class="kpi-label">Sin vehículo</span></div>
      </template>
      <template v-else-if="puedeCond"><div v-for="i in 2" :key="'cond'+i" class="kpi-skeleton"></div></template>

      <!-- Documentos -->
      <template v-if="datosDocumentos">
        <div class="kpi-g"><span class="kpi-tag">Documentos</span><span class="kpi-value" style="color:#059669">{{ datosDocumentos.resumen.vigentes }}</span><span class="kpi-label">Vigentes</span></div>
        <div class="kpi-g"><span class="kpi-tag">Documentos</span><span class="kpi-value" :style="datosDocumentos.resumen.por_vencer > 0 ? 'color:#D97706' : ''">{{ datosDocumentos.resumen.por_vencer }}</span><span class="kpi-label">Por vencer (30 días)</span></div>
        <div class="kpi-g"><span class="kpi-tag">Documentos</span><span class="kpi-value" :style="datosDocumentos.resumen.vencidos > 0 ? 'color:#DC2626' : ''">{{ datosDocumentos.resumen.vencidos }}</span><span class="kpi-label">Vencidos</span></div>
      </template>
      <template v-else-if="puedeDocs"><div v-for="i in 3" :key="'doc'+i" class="kpi-skeleton"></div></template>

      <!-- Combustible -->
      <template v-if="datosCombustible">
        <div class="kpi-g"><span class="kpi-tag">Combustible</span><span class="kpi-value">{{ clp(datosCombustible.gasto_total) }}</span><span class="kpi-label">Gasto total</span></div>
        <div class="kpi-g"><span class="kpi-tag">Combustible</span><span class="kpi-value">{{ clp(datosCombustible.gasto_promedio_mes) }}</span><span class="kpi-label">Promedio mensual</span></div>
      </template>
      <template v-else-if="puedeFin"><div v-for="i in 2" :key="'comb'+i" class="kpi-skeleton"></div></template>

      <!-- Rutas -->
      <template v-if="datosRutas">
        <div class="kpi-g"><span class="kpi-tag">Rutas</span><span class="kpi-value">{{ datosRutas.resumen.total }}</span><span class="kpi-label">Total rutas</span></div>
        <div class="kpi-g"><span class="kpi-tag">Rutas</span><span class="kpi-value" style="color:#059669">{{ datosRutas.resumen.finalizadas }}</span><span class="kpi-label">Finalizadas</span></div>
        <div class="kpi-g"><span class="kpi-tag">Rutas</span><span class="kpi-value" :style="datosRutas.resumen.canceladas > 0 ? 'color:#EF4444' : ''">{{ datosRutas.resumen.canceladas }}</span><span class="kpi-label">Canceladas</span></div>
        <div class="kpi-g"><span class="kpi-tag">Rutas</span><span class="kpi-value" style="color:#6366F1">{{ datosRutas.resumen.activas }}</span><span class="kpi-label">En curso</span></div>
      </template>
      <template v-else-if="puedeRutas"><div v-for="i in 4" :key="'ruta'+i" class="kpi-skeleton"></div></template>

      <!-- Solicitudes -->
      <template v-if="datosSolicitudes">
        <div class="kpi-g"><span class="kpi-tag">Solicitudes</span><span class="kpi-value">{{ datosSolicitudes.resumen.total }}</span><span class="kpi-label">Total solicitudes</span></div>
        <div class="kpi-g"><span class="kpi-tag">Solicitudes</span><span class="kpi-value" style="color:#6366F1">{{ datosSolicitudes.resumen.por_tipo.mantencion }}</span><span class="kpi-label">Mantención</span></div>
        <div class="kpi-g"><span class="kpi-tag">Solicitudes</span><span class="kpi-value" :style="(datosSolicitudes.resumen.por_tipo.incidencia || 0) > 0 ? 'color:#EF4444' : ''">{{ datosSolicitudes.resumen.por_tipo.incidencia }}</span><span class="kpi-label">Incidencias</span></div>
      </template>
      <template v-else-if="puedeSolic"><div v-for="i in 3" :key="'solic'+i" class="kpi-skeleton"></div></template>

    </div>

    <!-- ── Mantenciones ── -->
    <div v-if="puedeMant" class="bloque-reporte">
      <!-- Filtros -->
      <div class="filtros-bar">
        <div class="filtro-group">
          <label class="filtro-label">Año</label>
          <select v-model="anioSel" class="sel">
            <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>
        <div class="filtro-group">
          <label class="filtro-label">Mes</label>
          <select v-model="mesSel" class="sel">
            <option v-for="m in meses" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
        <div class="filtro-group">
          <label class="filtro-label">Vehículo</label>
          <select v-model="vehiculoSel" class="sel">
            <option value="">Todos los vehículos</option>
            <option v-for="v in vehiculos" :key="v.id" :value="v.id">
              {{ v.patente }} — {{ v.marca }} {{ v.modelo }}
            </option>
          </select>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando datos...</span>
      </div>

      <template v-else-if="datosMantencion">
        <!-- Gráfico evolución + top tipos -->
        <div class="grid-2 mb-4">
          <!-- Gráfico -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Evolución de costos</h3>
            </div>
            <div class="card-body">
              <div v-if="!datosMantencion.resumen.por_mes.length" class="empty-msg">
                Sin datos de evolución para el período.
              </div>
              <div v-else class="chart-container">
                <canvas ref="chartCanvas"></canvas>
              </div>
            </div>
          </div>

          <!-- Top tipos -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Top tipos de mantención</h3>
              <div class="estados-mini">
                <span v-for="(val, key) in datosMantencion.resumen.por_estado" :key="key"
                  class="estado-chip"
                  :style="{ background: ESTADO[key]?.bg, color: ESTADO[key]?.text }">
                  {{ ESTADO[key]?.label }} · {{ val }}
                </span>
              </div>
            </div>
            <div class="card-body">
              <div v-if="!datosMantencion.resumen.por_tipo.length" class="empty-msg">
                Sin datos de tipos.
              </div>
              <div v-else class="tipos-list">
                <div v-for="t in datosMantencion.resumen.por_tipo" :key="t.tipo" class="tipo-row">
                  <div class="tipo-info">
                    <span class="tipo-nombre">{{ t.tipo }}</span>
                    <span class="tipo-cantidad">{{ t.cantidad }} vez{{ t.cantidad !== 1 ? 'ces' : '' }}</span>
                  </div>
                  <div class="tipo-barra-wrap">
                    <div class="tipo-barra"
                      :style="{ width: Math.round(t.costo / maxCostoTipo * 100) + '%' }"/>
                  </div>
                  <span class="tipo-costo">{{ clp(t.costo) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Presupuesto vs gasto real -->
        <div v-if="datosPpto" class="card" style="margin-bottom:1rem">
          <div class="card-head">
            <h3 class="card-title">Presupuesto vs Gasto real — {{ datosPpto.anio }}</h3>
            <span class="sub-count">por mes</span>
          </div>
          <div class="card-body">
            <div class="chart-container">
              <canvas ref="chartPptoCanvas"/>
            </div>
          </div>
        </div>

        <!-- Tabla detalle -->
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Detalle de mantenciones</h3>
            <span class="sub-count">{{ datosMantencion.detalle.length }} registro{{ datosMantencion.detalle.length !== 1 ? 's' : '' }}</span>
          </div>
          <div v-if="!datosMantencion.detalle.length" class="card-body">
            <p class="empty-msg">Sin mantenciones para el período seleccionado.</p>
          </div>
          <div v-else class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th>Vehículo</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>F. Programada</th>
                  <th>F. Realizada</th>
                  <th>Costo</th>
                  <th>Taller</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in datosMantencion.detalle" :key="m.id">
                  <td class="font-medium">{{ m.vehiculo }}</td>
                  <td>{{ m.tipo }}</td>
                  <td>
                    <span class="badge"
                      :style="{ background: ESTADO[m.estado]?.bg, color: ESTADO[m.estado]?.text }">
                      {{ ESTADO[m.estado]?.label || m.estado }}
                    </span>
                  </td>
                  <td>{{ fechaCorta(m.fecha_programada) }}</td>
                  <td>{{ fechaCorta(m.fecha_realizada) }}</td>
                  <td class="font-medium">{{ clp(m.costo) }}</td>
                  <td class="text-muted">{{ m.taller }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template><!-- /datosMantencion -->
      <div v-else-if="!cargando" class="loading-wrap"><span>Sin datos de mantenciones.</span></div>
    </div><!-- /mantenciones -->

    <!-- ── Flota ── -->
    <div v-if="puedeFlota" class="bloque-reporte">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando datos...</span>
      </div>

      <template v-else-if="datosFlota">
        <!-- Tabla flota -->
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Estado de la flota</h3>
            <span class="sub-count">{{ datosFlota.vehiculos.length }} vehículo{{ datosFlota.vehiculos.length !== 1 ? 's' : '' }}</span>
          </div>
          <div v-if="!datosFlota.vehiculos.length" class="card-body">
            <p class="empty-msg">No hay vehículos activos.</p>
          </div>
          <div v-else class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th class="sortable" @click="toggleOrden('patente')">Patente{{ flechaOrden('patente') }}</th>
                  <th>Vehículo</th>
                  <th class="sortable" @click="toggleOrden('km_actuales')">KM{{ flechaOrden('km_actuales') }}</th>
                  <th>Conductor</th>
                  <th>Documentos</th>
                  <th class="sortable" @click="toggleOrden('costo_total_mantenciones')">Costo mantenciones{{ flechaOrden('costo_total_mantenciones') }}</th>
                  <th>Última mantención</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in flotaOrdenada" :key="v.id">
                  <td class="font-medium">{{ v.patente }}</td>
                  <td>{{ v.marca }} {{ v.modelo }} <span class="text-muted">{{ v.anio }}</span></td>
                  <td>{{ v.km_actuales.toLocaleString('es-CL') }} km</td>
                  <td>
                    <span v-if="v.conductor">{{ v.conductor }}</span>
                    <span v-else class="badge" style="background:#FFFBEB;color:#D97706">Sin asignar</span>
                  </td>
                  <td>
                    <div class="docs-badges">
                      <span v-if="v.docs_vigentes" class="badge" style="background:#ECFDF5;color:#059669">
                        {{ v.docs_vigentes }} vigente{{ v.docs_vigentes !== 1 ? 's' : '' }}
                      </span>
                      <span v-if="v.docs_por_vencer" class="badge" style="background:#FFFBEB;color:#D97706">
                        {{ v.docs_por_vencer }} por vencer
                      </span>
                      <span v-if="v.docs_vencidos" class="badge" style="background:#FEF2F2;color:#DC2626">
                        {{ v.docs_vencidos }} vencido{{ v.docs_vencidos !== 1 ? 's' : '' }}
                      </span>
                      <span v-if="!v.docs_vigentes && !v.docs_por_vencer && !v.docs_vencidos" class="text-muted">—</span>
                    </div>
                  </td>
                  <td class="font-medium">{{ clp(v.costo_total_mantenciones) }}</td>
                  <td>{{ fechaCorta(v.ultima_mantencion) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- Estado inicial: no se ha cargado aún -->
      <div v-else-if="!cargando" class="loading-wrap">
        <span>Cargando estado de flota...</span>
      </div>
    </div><!-- /flota -->

    <!-- ── TCO ── -->
    <div v-if="puedeFin" class="bloque-reporte">
      <!-- Filtros TCO -->
      <div class="filtros-bar">
        <div class="filtro-group">
          <label class="filtro-label">Año</label>
          <select v-model="anioSel" class="sel">
            <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>
        <div class="filtro-group">
          <label class="filtro-label">Mes</label>
          <select v-model="mesSel" class="sel">
            <option v-for="m in meses" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
      </div>

      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando TCO...</span>
      </div>

      <template v-else-if="datosTco">
        <!-- Chart TCO comparativa -->
        <div v-if="datosTco.vehiculos.length" class="card" style="margin-bottom:1rem">
          <div class="card-head">
            <h3 class="card-title">Comparativa TCO por vehículo</h3>
            <span class="sub-count">top 10 · gastos + mantenciones</span>
          </div>
          <div class="card-body">
            <div :style="{ height: Math.max(200, datosTco.vehiculos.slice(0,10).length * 38) + 'px', position: 'relative' }">
              <canvas ref="chartTcoCanvas"/>
            </div>
          </div>
        </div>

        <!-- Tabla TCO -->
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Costo Total de Propiedad por Vehículo</h3>
            <span class="sub-count">{{ datosTco.vehiculos.length }} vehículo{{ datosTco.vehiculos.length !== 1 ? 's' : '' }}</span>
          </div>
          <div v-if="!datosTco.vehiculos.length" class="card-body">
            <p class="empty-msg">Sin datos para el período seleccionado.</p>
          </div>
          <div v-else class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th class="sortable" @click="tcoOrdenCampo = 'patente'; tcoOrdenDesc = !tcoOrdenDesc">Patente</th>
                  <th>Vehículo</th>
                  <th>Conductor</th>
                  <th class="sortable" @click="tcoOrdenCampo = 'km_actuales'; tcoOrdenDesc = !tcoOrdenDesc">KM</th>
                  <th class="sortable" @click="tcoOrdenCampo = 'gastos_total'; tcoOrdenDesc = !tcoOrdenDesc">Gastos Op.</th>
                  <th class="sortable" @click="tcoOrdenCampo = 'mantenciones_total'; tcoOrdenDesc = !tcoOrdenDesc">Mantenciones</th>
                  <th class="sortable" @click="tcoOrdenCampo = 'tco_total'; tcoOrdenDesc = !tcoOrdenDesc">TCO Total</th>
                  <th>Costo/KM</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in tcoOrdenada" :key="v.id">
                  <td class="font-medium">{{ v.patente }}</td>
                  <td>{{ v.marca }} {{ v.modelo }} <span class="text-muted">{{ v.anio }}</span></td>
                  <td>
                    <span v-if="v.conductor">{{ v.conductor }}</span>
                    <span v-else class="badge" style="background:#FFFBEB;color:#D97706">Sin asignar</span>
                  </td>
                  <td>{{ v.km_actuales ? v.km_actuales.toLocaleString('es-CL') + ' km' : '—' }}</td>
                  <td class="font-medium">{{ clp(v.gastos_total) }}</td>
                  <td class="font-medium">{{ clp(v.mantenciones_total) }}</td>
                  <td>
                    <span class="tco-total">{{ clp(v.tco_total) }}</span>
                  </td>
                  <td class="text-muted">{{ v.costo_por_km != null ? '$' + Number(v.costo_por_km).toFixed(0) + '/km' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <div v-else-if="!cargando" class="loading-wrap">
        <span>Cargando datos TCO...</span>
      </div>
    </div><!-- /tco -->

    <!-- ── Conductores ── -->
    <div v-if="puedeCond" class="bloque-reporte">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando conductores...</span>
      </div>

      <template v-else-if="datosConductores">
        <!-- Tabla conductores -->
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Estado documental de conductores</h3>
            <span class="sub-count">{{ datosConductores.conductores.length }} conductor{{ datosConductores.conductores.length !== 1 ? 'es' : '' }}</span>
          </div>
          <div v-if="!datosConductores.conductores.length" class="card-body">
            <p class="empty-msg">No hay conductores registrados.</p>
          </div>
          <div v-else class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>RUT</th>
                  <th>Vehículo asignado</th>
                  <th>Documentos</th>
                  <th>Estado docs</th>
                  <th>Gastos asociados</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in datosConductores.conductores" :key="c.id">
                  <td class="font-medium">{{ c.nombre }}</td>
                  <td class="text-muted">{{ c.rut || '—' }}</td>
                  <td>
                    <span v-if="c.vehiculo_asignado">{{ c.vehiculo_asignado }}</span>
                    <span v-else class="badge" style="background:#FFFBEB;color:#D97706">Sin asignar</span>
                  </td>
                  <td>
                    <div class="docs-badges">
                      <span v-if="c.docs_vigentes" class="badge" style="background:#ECFDF5;color:#059669">
                        {{ c.docs_vigentes }} vigente{{ c.docs_vigentes !== 1 ? 's' : '' }}
                      </span>
                      <span v-if="c.docs_por_vencer" class="badge" style="background:#FFFBEB;color:#D97706">
                        {{ c.docs_por_vencer }} por vencer
                      </span>
                      <span v-if="c.docs_vencidos" class="badge" style="background:#FEF2F2;color:#DC2626">
                        {{ c.docs_vencidos }} vencido{{ c.docs_vencidos !== 1 ? 's' : '' }}
                      </span>
                      <span v-if="!c.docs_vigentes && !c.docs_por_vencer && !c.docs_vencidos" class="text-muted">Sin docs</span>
                    </div>
                  </td>
                  <td>
                    <span v-if="c.estado_docs === 'vencido'" class="badge" style="background:#FEF2F2;color:#DC2626">Vencido</span>
                    <span v-else-if="c.estado_docs === 'por_vencer'" class="badge" style="background:#FFFBEB;color:#D97706">Por vencer</span>
                    <span v-else-if="c.estado_docs === 'vigente'" class="badge" style="background:#ECFDF5;color:#059669">Al día</span>
                    <span v-else class="badge" style="background:#F3F4F6;color:#6B7280">Sin docs</span>
                  </td>
                  <td class="font-medium">{{ clp(c.gastos_total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <div v-else-if="!cargando" class="loading-wrap">
        <span>Cargando datos de conductores...</span>
      </div>
    </div><!-- /conductores -->

    <!-- ── Documentos ── -->
    <div v-if="puedeDocs" class="bloque-reporte">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando documentos...</span>
      </div>

      <template v-else-if="datosDocumentos">
        <!-- (KPIs en el encabezado global) -->

        <div class="grid-2 mb-4">
          <!-- Estado documental por vehículo -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Documentos por vehículo</h3>
              <span class="sub-count">{{ datosDocumentos.por_vehiculo.length }} vehículos</span>
            </div>
            <div v-if="!datosDocumentos.por_vehiculo.length" class="card-body">
              <p class="empty-msg">Sin documentos registrados.</p>
            </div>
            <div v-else class="tabla-wrap" style="max-height:380px;overflow-y:auto">
              <table class="tabla">
                <thead>
                  <tr><th>Vehículo</th><th>Tipo</th><th>Vencimiento</th><th>Estado</th></tr>
                </thead>
                <tbody>
                  <template v-for="veh in datosDocumentos.por_vehiculo" :key="veh.vehiculo">
                    <tr v-for="(doc, di) in veh.documentos" :key="di">
                      <td v-if="di === 0" :rowspan="veh.documentos.length" class="font-medium" style="vertical-align:top;white-space:normal;min-width:120px">
                        {{ veh.vehiculo }}
                      </td>
                      <td>{{ doc.tipo_display }}</td>
                      <td>{{ doc.fecha_vencimiento ? doc.fecha_vencimiento.slice(8,10) + '/' + doc.fecha_vencimiento.slice(5,7) + '/' + doc.fecha_vencimiento.slice(0,4) : '—' }}</td>
                      <td>
                        <span class="badge"
                          :style="doc.estado === 'vigente' ? 'background:#ECFDF5;color:#059669' : doc.estado === 'por_vencer' ? 'background:#FFFBEB;color:#D97706' : 'background:#FEF2F2;color:#DC2626'">
                          {{ doc.estado === 'vigente' ? 'Vigente' : doc.estado === 'por_vencer' ? 'Por vencer' : 'Vencido' }}
                          <template v-if="doc.estado !== 'vigente'"> · {{ Math.abs(doc.dias) }}d</template>
                        </span>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Timeline próximos 60 días -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Próximos a vencer (60 días)</h3>
              <span class="sub-count">{{ datosDocumentos.proximos_vencer.length }} documentos</span>
            </div>
            <div v-if="!datosDocumentos.proximos_vencer.length" class="card-body">
              <p class="empty-msg">Sin vencimientos próximos.</p>
            </div>
            <div v-else style="max-height:380px;overflow-y:auto">
              <div v-for="(doc, i) in datosDocumentos.proximos_vencer" :key="i"
                style="display:flex;align-items:center;gap:0.75rem;padding:0.65rem 1.25rem;border-bottom:1px solid #F9FAFB">
                <span :style="{
                  minWidth: '48px', textAlign: 'center', fontWeight: 700, fontSize: '0.8rem',
                  padding: '0.2rem 0.5rem', borderRadius: '6px',
                  background: doc.dias < 0 ? '#FEF2F2' : doc.dias <= 15 ? '#FFFBEB' : '#ECFDF5',
                  color: doc.dias < 0 ? '#DC2626' : doc.dias <= 15 ? '#D97706' : '#059669',
                }">
                  {{ doc.dias < 0 ? Math.abs(doc.dias) + 'd' : doc.dias + 'd' }}
                </span>
                <div style="flex:1;min-width:0">
                  <div style="font-size:0.8125rem;font-weight:600;color:#111827">{{ doc.tipo_display }}</div>
                  <div style="font-size:0.75rem;color:#9CA3AF">{{ doc.vehiculo }}</div>
                </div>
                <span style="font-size:0.75rem;color:#6B7280">
                  {{ doc.fecha_vencimiento ? doc.fecha_vencimiento.slice(8,10) + '/' + doc.fecha_vencimiento.slice(5,7) : '' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else-if="!cargando" class="loading-wrap">
        <span>Cargando documentos...</span>
      </div>
    </div><!-- /documentos -->

    <!-- ── Combustible ── -->
    <div v-if="puedeFin" class="bloque-reporte">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando datos...</span>
      </div>

      <template v-else-if="datosCombustible">
        <!-- (KPIs en el encabezado global) -->

        <div class="grid-2 mb-4">
          <!-- Barras horizontales top 5 -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Top 5 vehículos por gasto</h3>
              <span class="sub-count">gasto total en combustible</span>
            </div>
            <div class="card-body">
              <div v-if="!datosCombustible.por_vehiculo.length" class="empty-msg">Sin datos de combustible.</div>
              <div v-else style="position:relative;height:220px">
                <canvas ref="chartCombBar"/>
              </div>
            </div>
          </div>

          <!-- Línea evolución mensual -->
          <div class="card">
            <div class="card-head">
              <h3 class="card-title">Evolución mensual</h3>
              <span class="sub-count">gasto en combustible · últimos 12 meses</span>
            </div>
            <div class="card-body">
              <div v-if="!datosCombustible.por_mes.length" class="empty-msg">Sin datos históricos.</div>
              <div v-else style="position:relative;height:220px">
                <canvas ref="chartCombLine"/>
              </div>
            </div>
          </div>
        </div>

        <!-- Nota eficiencia -->
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;padding:0.875rem 1rem;font-size:0.8125rem;color:#0369A1;display:flex;align-items:flex-start;gap:0.5rem;margin-bottom:1rem">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px;flex-shrink:0;margin-top:0.1rem">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>El cálculo de eficiencia (km/litro) no está disponible porque el sistema no registra el historial de kilómetros por período, solo el odómetro actual. Para calcular eficiencia, registra los km al momento de cada carga de combustible.</span>
        </div>
      </template>

      <div v-else-if="!cargando" class="loading-wrap">
        <span>Cargando datos de combustible...</span>
      </div>
    </div><!-- /combustible -->

    <!-- ── Gastos por categoría + Gasto mensual ── -->
    <div v-if="puedeFin" class="bloque-reporte">
      <div class="grid-2 mb-4">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Distribución de gastos por categoría</h3>
            <span class="sub-count">todos los vehículos</span>
          </div>
          <div class="card-body">
            <div v-if="!datosTco" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else-if="!datosTco.gastos_categoria || !Object.values(datosTco.gastos_categoria).some(v => v > 0)" class="empty-msg">Sin gastos registrados.</div>
            <div v-else style="position:relative;height:220px"><canvas ref="chartDonaGastos"/></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Gasto operativo mensual</h3>
            <span class="sub-count">año {{ anioSel }}</span>
          </div>
          <div class="card-body">
            <div v-if="!datosPpto" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else class="chart-container"><canvas ref="chartGastoMes"/></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <h3 class="card-title">Presupuesto acumulado vs Gasto acumulado</h3>
          <span class="sub-count">proyección anual — {{ anioSel }}</span>
        </div>
        <div class="card-body">
          <div v-if="!datosPpto" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
          <div v-else class="chart-container"><canvas ref="chartPptoAcum"/></div>
        </div>
      </div>
    </div><!-- /gastos-globales -->

    <!-- ── Semáforo de vehículos críticos ── -->
    <div v-if="puedeFin" class="bloque-reporte">
      <div class="card">
        <div class="card-head">
          <h3 class="card-title">Semáforo de vehículos críticos</h3>
          <span class="sub-count">atención requerida hoy</span>
        </div>
        <div v-if="!datosFlota" class="card-body loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
        <div v-else-if="!datosFlota.vehiculos.length" class="card-body"><p class="empty-msg">No hay vehículos activos.</p></div>
        <div v-else class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr><th>Patente</th><th>Vehículo</th><th>Conductor</th><th>Docs</th><th>Mantención</th><th>Días sin mant.</th></tr>
            </thead>
            <tbody>
              <tr v-for="v in datosFlota.vehiculos" :key="v.id"
                :class="['semaforo-row', v.docs_vencidos > 0 || !v.conductor ? 'semaforo-rojo' : v.docs_por_vencer > 0 ? 'semaforo-amarillo' : '']">
                <td class="font-medium">{{ v.patente }}</td>
                <td>{{ v.marca }} {{ v.modelo }}</td>
                <td>
                  <span v-if="v.conductor">{{ v.conductor }}</span>
                  <span v-else class="badge" style="background:#FEF2F2;color:#DC2626">Sin asignar</span>
                </td>
                <td>
                  <span v-if="v.docs_vencidos" class="badge" style="background:#FEF2F2;color:#DC2626">{{ v.docs_vencidos }} vencido{{ v.docs_vencidos !== 1 ? 's' : '' }}</span>
                  <span v-else-if="v.docs_por_vencer" class="badge" style="background:#FFFBEB;color:#D97706">{{ v.docs_por_vencer }} por vencer</span>
                  <span v-else class="badge" style="background:#ECFDF5;color:#059669">Al día</span>
                </td>
                <td>
                  <span v-if="v.costo_total_mantenciones === 0 && !v.ultima_mantencion" class="badge" style="background:#FEF2F2;color:#DC2626">Sin registro</span>
                  <span v-else class="badge" style="background:#ECFDF5;color:#059669">Registrada</span>
                </td>
                <td>
                  <span v-if="v.ultima_mantencion" :style="diasSinMant(v.ultima_mantencion) > 180 ? 'color:#DC2626;font-weight:600' : diasSinMant(v.ultima_mantencion) > 90 ? 'color:#D97706' : ''">
                    {{ diasSinMant(v.ultima_mantencion) }} días
                  </span>
                  <span v-else style="color:#DC2626;font-weight:600">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div><!-- /semaforo -->

    <!-- ── Rutas por mes + por tipo ── -->
    <div v-if="puedeRutas" class="bloque-reporte">
      <div class="grid-2 mb-4">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Rutas finalizadas vs canceladas</h3>
            <span class="sub-count">últimos 12 meses</span>
          </div>
          <div class="card-body">
            <div v-if="!datosRutas" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else-if="!datosRutas.por_mes.some(m => m.total > 0)" class="empty-msg">Sin rutas registradas.</div>
            <div v-else class="chart-container"><canvas ref="chartRutasMes"/></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Rutas por tipo</h3>
            <span class="sub-count">carga vs personas</span>
          </div>
          <div class="card-body">
            <div v-if="!datosRutas" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else-if="!Object.values(datosRutas.resumen.por_tipo || {}).some(v => v > 0)" class="empty-msg">Sin rutas registradas.</div>
            <div v-else style="position:relative;height:220px"><canvas ref="chartRutasTipo"/></div>
          </div>
        </div>
      </div>
    </div><!-- /rutas -->

    <!-- ── Solicitudes por mes + por tipo ── -->
    <div v-if="puedeSolic" class="bloque-reporte">
      <div class="grid-2 mb-4">
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Solicitudes de conductores por mes</h3>
            <span class="sub-count">últimos 12 meses</span>
          </div>
          <div class="card-body">
            <div v-if="!datosSolicitudes" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else-if="!datosSolicitudes.por_mes.some(m => m.total > 0)" class="empty-msg">Sin solicitudes registradas.</div>
            <div v-else class="chart-container"><canvas ref="chartSolicMes"/></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Solicitudes por tipo</h3>
            <span class="sub-count">distribución total</span>
          </div>
          <div class="card-body">
            <div v-if="!datosSolicitudes" class="loading-wrap"><div class="spinner"/><span>Cargando...</span></div>
            <div v-else-if="!datosSolicitudes.resumen.total" class="empty-msg">Sin solicitudes registradas.</div>
            <div v-else style="position:relative;height:220px"><canvas ref="chartSolicTipo"/></div>
          </div>
        </div>
      </div>
    </div><!-- /solicitudes -->

  </div>
</template>

<style scoped>
.page { padding: 1.5rem 2rem; max-width: 1400px; font-family: 'Inter', system-ui, sans-serif; }

.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.25rem; }
.titulo { font-size: 1.5rem; font-weight: 800; color: #111827; margin: 0 0 0.2rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* Tabs */
.tabs-wrap { display: flex; gap: 0.25rem; border-bottom: 2px solid #F3F4F6; margin-bottom: 1.5rem; }
.tab-btn {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.65rem 1.1rem; border: none; background: none;
  font-size: 0.875rem; font-weight: 600; color: #6B7280;
  cursor: pointer; border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all 0.15s; font-family: inherit; border-radius: 4px 4px 0 0;
}
/* KPIs globales al tope */
.kpis-globales {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 2rem;
}
.kpi-g {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 0.75rem 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.kpi-g .kpi-tag {
  font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9CA3AF; margin-bottom: 0.2rem;
}
.kpi-g .kpi-value {
  font-size: 1.3rem; font-weight: 800; color: #111827; line-height: 1.2;
}
.kpi-g .kpi-label {
  font-size: 0.72rem; color: #6B7280; font-weight: 500;
}
.kpi-skeleton {
  min-height: 72px; background: #F3F4F6; border-radius: 14px;
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .5 } }

/* Bloques de reporte */
.bloque-reporte {
  margin-bottom: 2.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #F3F4F6;
}
.bloque-reporte:first-of-type { border-top: none; padding-top: 0; }

/* Filtros */
.filtros-bar { display: flex; align-items: flex-end; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.filtro-group { display: flex; flex-direction: column; gap: 0.3rem; }
.filtro-label { font-size: 0.75rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.04em; }
.sel { padding: 0.45rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; background: #fff; color: #374151; cursor: pointer; }
.filtro-spacer { flex: 1; }
.btn-export {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem; background: #fff; border: 1.5px solid #D1D5DB;
  border-radius: 8px; font-size: 0.875rem; font-weight: 600; color: #374151;
  cursor: pointer; transition: all 0.15s; white-space: nowrap; font-family: inherit;
}
.btn-export svg { width: 15px; height: 15px; }
.btn-export:hover:not(:disabled) { border-color: #4F46E5; color: #4F46E5; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

/* Loading */
.loading-wrap { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; padding: 3rem 0; font-size: 0.875rem; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #4F46E5; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Semáforo */
.semaforo-rojo { background: #FEF2F2 !important; }
.semaforo-amarillo { background: #FFFBEB !important; }

/* KPIs */
.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1rem 1.25rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-icon svg { width: 20px; height: 20px; }
.kpi-value { font-size: 1.4rem; font-weight: 800; color: #111827; line-height: 1.1; }
.kpi-label { font-size: 0.75rem; color: #9CA3AF; font-weight: 500; margin-top: 0.15rem; }
.kpi-spacer { flex: 1; }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.mb-4 { margin-bottom: 1rem; }

/* Cards */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; flex-wrap: wrap; gap: 0.5rem; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.card-body { padding: 1.25rem; }
.sub-count { font-size: 0.8rem; color: #9CA3AF; }
.empty-msg { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 1.5rem 0; }

/* Chart */
.chart-container { position: relative; height: 240px; }

/* Top tipos */
.estados-mini { display: flex; flex-wrap: wrap; gap: 0.375rem; }
.estado-chip { font-size: 0.7rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 999px; }
.tipos-list { display: flex; flex-direction: column; gap: 0.875rem; }
.tipo-row { display: flex; align-items: center; gap: 0.75rem; }
.tipo-info { width: 180px; flex-shrink: 0; }
.tipo-nombre { display: block; font-size: 0.8125rem; font-weight: 600; color: #374151; }
.tipo-cantidad { font-size: 0.72rem; color: #9CA3AF; }
.tipo-barra-wrap { flex: 1; height: 7px; background: #F3F4F6; border-radius: 4px; overflow: hidden; }
.tipo-barra { height: 100%; background: linear-gradient(90deg, #4F46E5, #7C3AED); border-radius: 4px; transition: width 0.4s; }
.tipo-costo { font-size: 0.8125rem; font-weight: 700; color: #111827; width: 90px; text-align: right; }

/* Tabla */
.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; white-space: nowrap; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tr:hover td { background: #FAFAFA; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: #374151; }
.font-medium { font-weight: 600; color: #111827; }
.text-muted { color: #9CA3AF; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.docs-badges { display: flex; flex-wrap: wrap; gap: 0.3rem; }

/* TCO */
.tco-total { font-weight: 800; color: #4338CA; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .header { flex-direction: column; align-items: stretch; gap: 0.625rem; }
  .titulo { font-size: 1.25rem; }
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
