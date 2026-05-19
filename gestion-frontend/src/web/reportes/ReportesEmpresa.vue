<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const toast = useToast()

// ── Tabs
const tabActivo = ref('mantencion')

// ── Estado
const cargando        = ref(false)
const exportando      = ref(false)
const datosMantencion = ref(null)
const datosFlota      = ref(null)
const datosTco        = ref(null)
const datosConductores = ref(null)
const vehiculos       = ref([])

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

// ── Chart
const chartCanvas = ref(null)
let chartInstance = null

function crearChart() {
  if (!chartCanvas.value || !datosMantencion.value?.resumen?.por_mes?.length) return
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

watch(datosMantencion, async () => { await nextTick(); crearChart() }, { deep: true })

// ── Carga de datos
async function cargarVehiculos() {
  const res = await apiFetch('/api/empresa/vehiculos/')
  if (res.ok) vehiculos.value = await res.json()
}

async function cargarMantencion() {
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
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresa/reportes/conductores/')
    if (res.ok) datosConductores.value = await res.json()
    else toast.error('Error al cargar el reporte de conductores.')
  } catch { toast.error('Error de conexión.') }
  finally { cargando.value = false }
}

function exportarTco() {
  if (!datosTco.value?.vehiculos) return
  const rows = [
    ['Patente', 'Marca/Modelo', 'Flota', 'Conductor', 'KM', 'Gastos Operativos', 'Mantenciones', 'TCO Total', 'Costo/KM'],
    ...datosTco.value.vehiculos.map(v => [
      v.patente, `${v.marca} ${v.modelo}`, v.flota, v.conductor || '—',
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
watch(tabActivo, async (tab) => {
  if (tab === 'flota' && !datosFlota.value) await cargarFlota()
  if (tab === 'tco')   await cargarTco()
  if (tab === 'conductores') await cargarConductores()
})
watch([anioSel, mesSel], () => {
  if (tabActivo.value === 'tco') cargarTco()
})

// ── Lifecycle
onMounted(async () => {
  await Promise.all([cargarVehiculos(), cargarMantencion()])
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})

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

    <!-- Tabs -->
    <div class="tabs-wrap">
      <button :class="['tab-btn', tabActivo === 'mantencion' && 'tab-active']"
        @click="tabActivo = 'mantencion'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        Mantenciones
      </button>
      <button :class="['tab-btn', tabActivo === 'flota' && 'tab-active']"
        @click="tabActivo = 'flota'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
        </svg>
        Estado de Flota
      </button>
      <button :class="['tab-btn', tabActivo === 'tco' && 'tab-active']"
        @click="tabActivo = 'tco'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        Costo Total (TCO)
      </button>
      <button :class="['tab-btn', tabActivo === 'conductores' && 'tab-active']"
        @click="tabActivo = 'conductores'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        Conductores
      </button>
    </div>

    <!-- ── TAB MANTENCIONES ── -->
    <template v-if="tabActivo === 'mantencion'">
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
        <div class="filtro-spacer"/>
        <button class="btn-export" @click="exportar('mantencion')" :disabled="exportando">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          {{ exportando ? 'Exportando...' : 'Exportar CSV' }}
        </button>
      </div>

      <!-- Loading -->
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando datos...</span>
      </div>

      <template v-else-if="datosMantencion">
        <!-- KPIs -->
        <div class="kpis">
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ datosMantencion.resumen.total }}</div>
              <div class="kpi-label">Total mantenciones</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#F0FDF4;color:#059669">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ clp(datosMantencion.resumen.costo_total) }}</div>
              <div class="kpi-label">Costo total</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ clp(datosMantencion.resumen.costo_promedio) }}</div>
              <div class="kpi-label">Costo promedio</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#ECFDF5;color:#059669">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" style="color:#059669">{{ datosMantencion.resumen.por_estado.realizada }}</div>
              <div class="kpi-label">Realizadas</div>
            </div>
          </div>
        </div>

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
      </template>
    </template>

    <!-- ── TAB FLOTA ── -->
    <template v-else-if="tabActivo === 'flota'">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando datos...</span>
      </div>

      <template v-else-if="datosFlota">
        <!-- KPIs -->
        <div class="kpis mb-4" style="margin-top:1.25rem">
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ datosFlota.resumen.total }}</div>
              <div class="kpi-label">Vehículos activos</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FEF2F2;color:#DC2626">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" :style="datosFlota.resumen.con_docs_vencidos > 0 ? 'color:#DC2626' : ''">
                {{ datosFlota.resumen.con_docs_vencidos }}
              </div>
              <div class="kpi-label">Con docs vencidos</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" :style="datosFlota.resumen.sin_conductor > 0 ? 'color:#D97706' : ''">
                {{ datosFlota.resumen.sin_conductor }}
              </div>
              <div class="kpi-label">Sin conductor asignado</div>
            </div>
          </div>
          <div class="kpi-spacer"/>
          <button class="btn-export" @click="exportar('flota')" :disabled="exportando">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            {{ exportando ? 'Exportando...' : 'Exportar CSV' }}
          </button>
        </div>

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
                  <th class="sortable" @click="toggleOrden('flota')">Flota{{ flechaOrden('flota') }}</th>
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
                  <td>{{ v.flota }}</td>
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
    </template>

    <!-- ── TAB TCO ── -->
    <template v-else-if="tabActivo === 'tco'">
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
        <div class="filtro-spacer"/>
        <button class="btn-export" @click="exportarTco" :disabled="!datosTco">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Exportar CSV
        </button>
      </div>

      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando TCO...</span>
      </div>

      <template v-else-if="datosTco">
        <!-- KPIs TCO -->
        <div class="kpis">
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ datosTco.resumen.total_flota }}</div>
              <div class="kpi-label">Vehículos analizados</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FFF7ED;color:#EA580C">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ clp(datosTco.resumen.total_gastos) }}</div>
              <div class="kpi-label">Gastos operativos</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#F0FDF4;color:#059669">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ clp(datosTco.resumen.total_mant) }}</div>
              <div class="kpi-label">Costos mantención</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ clp(datosTco.resumen.costo_promedio) }}</div>
              <div class="kpi-label">TCO promedio / vehículo</div>
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
                  <th>Flota</th>
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
                  <td>{{ v.flota }}</td>
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
    </template>

    <!-- ── TAB CONDUCTORES ── -->
    <template v-else-if="tabActivo === 'conductores'">
      <div v-if="cargando" class="loading-wrap">
        <div class="spinner"/><span>Cargando conductores...</span>
      </div>

      <template v-else-if="datosConductores">
        <!-- KPIs Conductores -->
        <div class="kpis" style="margin-top:1.25rem">
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value">{{ datosConductores.resumen.total }}</div>
              <div class="kpi-label">Total conductores</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FEF2F2;color:#DC2626">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" :style="datosConductores.resumen.con_docs_vencidos > 0 ? 'color:#DC2626' : ''">
                {{ datosConductores.resumen.con_docs_vencidos }}
              </div>
              <div class="kpi-label">Con docs vencidos</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" :style="datosConductores.resumen.sin_vehiculo > 0 ? 'color:#D97706' : ''">
                {{ datosConductores.resumen.sin_vehiculo }}
              </div>
              <div class="kpi-label">Sin vehículo asignado</div>
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-icon" style="background:#F3F4F6;color:#6B7280">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <div>
              <div class="kpi-value" :style="datosConductores.resumen.sin_docs > 0 ? 'color:#6B7280' : ''">
                {{ datosConductores.resumen.sin_docs }}
              </div>
              <div class="kpi-label">Sin documentos</div>
            </div>
          </div>
          <div class="kpi-spacer"/>
          <button class="btn-export" @click="exportarConductores" :disabled="!datosConductores">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Exportar CSV
          </button>
        </div>

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
    </template>
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
.tab-btn svg { width: 16px; height: 16px; }
.tab-btn:hover { color: #4F46E5; background: #F5F3FF; }
.tab-active { color: #4F46E5 !important; border-bottom-color: #4F46E5 !important; }

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
</style>
