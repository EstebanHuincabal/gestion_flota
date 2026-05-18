<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Chart from 'chart.js/auto'
import { apiFetch } from '../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav } from '../utils/empresaActiva.js'
import { tienePermiso } from '../utils/permisos.js'
import { useTema } from '../utils/tema.js'

const { accentActual } = useTema()

const router = useRouter()
const { ruta } = useEmpresaNav()
const usuario = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')

const ACCESOS_EMPRESA = [
  {
    label: 'Flota', permiso: 'flotas.ver', path: '/flota', color: 'ac-purple',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>`,
  },
  {
    label: 'Conductores', permiso: 'conductores.ver', path: '/conductores', color: 'ac-blue',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
  {
    label: 'Mantenciones', permiso: 'mantenciones.ver', path: '/mantenciones', color: 'ac-amber',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
  {
    label: 'Documentos', permiso: 'documentos.ver', path: '/documentos', color: 'ac-slate',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`,
  },
  {
    label: 'Predictivo', permiso: 'mantenciones.ver', path: '/predictivo', color: 'ac-indigo',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 10V3L4 14h7v7l9-11h-7z"/>`,
  },
]

const accesosEmpresa = computed(() =>
  ACCESOS_EMPRESA.filter(a => tienePermiso(a.permiso))
)

const cargando         = ref(true)
const cargandoGraficos = ref(false)
const error            = ref('')

// SUPERADMIN: KPIs globales de plataforma
const kpisGlobal = ref({
  empresas_activas: 0, empresas_inactivas: 0,
  total_usuarios: 0,   total_conductores: 0,
  total_vehiculos: 0,  empresas_nuevas_mes: 0,
  usuarios_activos_hoy: 0,
})
const topEmpresas = ref([])

// USUARIO: KPIs de la empresa
const kpisEmpresa = ref({
  total_flotas: 0, total_vehiculos: 0, total_conductores: 0,
  mantenciones_pendientes: 0, docs_por_vencer: 0,
})

// Canvas refs — cada rol usa los suyos
const crecimientoCanvas  = ref(null)
const distribucionCanvas = ref(null)
const vehiculosCanvas    = ref(null)
const mantencionesCanvas = ref(null)

let crecimientoChart  = null
let distribucionChart = null
let vehiculosChart    = null
let mantencionesChart = null

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
      kpisGlobal.value  = data.kpis
      topEmpresas.value = data.charts.top_empresas
      pendiente = () => renderGraficosGlobal(data.charts)
    } else {
      const res = await apiFetchEmpresa(`/api/empresa/dashboard/?periodo=${periodoActivo.value}`)
      if (!res.ok) throw new Error('Error al cargar el dashboard')
      const data = await res.json()
      kpisEmpresa.value = data.kpis
      pendiente = () => renderGraficosEmpresa(data.charts)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
  // El finally ya puso cargando=false. Esperamos el próximo tick para
  // que Vue monte los <canvas> en el DOM antes de renderizar los gráficos.
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
      renderGraficosGlobal(data.charts)
    } else {
      const res = await apiFetchEmpresa(`/api/empresa/dashboard/?periodo=${p}`)
      if (!res.ok) return
      const data = await res.json()
      renderGraficosEmpresa(data.charts)
    }
  } finally {
    cargandoGraficos.value = false
  }
}

const cambiarPeriodo = (p) => {
  periodoActivo.value = p
  cargarGraficos(p)
}

const renderGraficosGlobal = (charts) => {
  if (crecimientoChart)  crecimientoChart.destroy()
  if (distribucionChart) distribucionChart.destroy()

  if (crecimientoCanvas.value) {
    const ac = accentActual()
    crecimientoChart = new Chart(crecimientoCanvas.value, {
      type: 'line',
      data: {
        labels: charts.crecimiento.labels,
        datasets: [{
          data: charts.crecimiento.data,
          borderColor: ac,
          backgroundColor: `color-mix(in oklch, ${ac} 12%, transparent)`,
          tension: 0.4, fill: true,
          pointRadius: 3, pointBackgroundColor: ac,
          pointHoverRadius: 5,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } },
          y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }
        }
      }
    })
  }

  if (distribucionCanvas.value) {
    const ac = accentActual()
    distribucionChart = new Chart(distribucionCanvas.value, {
      type: 'doughnut',
      data: {
        labels: charts.distribucion_flota.labels,
        datasets: [{
          data: charts.distribucion_flota.data,
          backgroundColor: [
            '#E5E7EB',
            ac,
            `color-mix(in oklch, ${ac} 60%, #10B981)`,
            `color-mix(in oklch, ${ac} 40%, #F59E0B)`,
          ],
          borderWidth: 0, hoverOffset: 6,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 12, boxWidth: 10 } } },
        cutout: '68%',
      }
    })
  }
}

const renderGraficosEmpresa = (charts) => {
  if (vehiculosChart)    vehiculosChart.destroy()
  if (mantencionesChart) mantencionesChart.destroy()

  if (vehiculosCanvas.value) {
    const ac = accentActual()
    vehiculosChart = new Chart(vehiculosCanvas.value, {
      type: 'bar',
      data: {
        labels: charts.vehiculos_por_flota.labels,
        datasets: [{
          data: charts.vehiculos_por_flota.data,
          backgroundColor: `color-mix(in oklch, ${ac} 80%, white)`,
          hoverBackgroundColor: ac,
          borderRadius: 6,
          barThickness: 32,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#9CA3AF', maxRotation: 30 } },
          y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }
        }
      }
    })
  }

  if (mantencionesCanvas.value) {
    mantencionesChart = new Chart(mantencionesCanvas.value, {
      type: 'line',
      data: {
        labels: charts.mantenciones.labels,
        datasets: [{
          data: charts.mantenciones.data,
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245,158,11,0.07)',
          tension: 0.4, fill: true,
          pointRadius: 3, pointBackgroundColor: '#F59E0B',
          pointHoverRadius: 5,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9CA3AF' } },
          y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 }, color: '#9CA3AF' }, grid: { color: '#F3F4F6' } }
        }
      }
    })
  }
}

onMounted(cargar)
</script>

<template>
  <div class="page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">
          {{ esSuperadmin ? 'Dashboard Global' : `Bienvenido, ${usuario.nombre?.split(' ')[0]}` }}
        </h1>
        <p class="page-subtitle">
          {{ esSuperadmin ? 'Métricas y estado general de la plataforma' : `${usuario.empresa} — Panel de gestión` }}
        </p>
      </div>
      <button class="btn-refresh" @click="cargar" :disabled="cargando">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Actualizar
      </button>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading">
      <div class="spinner"/>
      <span>Cargando métricas...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="alert-error">{{ error }}</div>

    <!-- ══════════════ SUPERADMIN ══════════════ -->
    <template v-else-if="esSuperadmin">

      <div class="kpis">
        <div class="kpi-card">
          <div class="kpi-icon bg-purple">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisGlobal.empresas_activas }}</span>
            <span class="kpi-label">Empresas activas</span>
            <span class="kpi-sub">{{ kpisGlobal.empresas_inactivas }} inactivas</span>
          </div>
          <span class="kpi-pct">{{ pctActivas }}%</span>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-indigo">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisGlobal.total_vehiculos }}</span>
            <span class="kpi-label">Vehículos totales</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-blue">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisGlobal.total_usuarios }}</span>
            <span class="kpi-label">Usuarios registrados</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-emerald">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M10 9V7m0 0H8m2 0h2M10 7a4 4 0 110 8 4 4 0 010-8zM21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisGlobal.total_conductores }}</span>
            <span class="kpi-label">Conductores</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-amber">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value text-amber">{{ kpisGlobal.empresas_nuevas_mes }}</span>
            <span class="kpi-label">Nuevas este mes</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-green">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value text-green">{{ kpisGlobal.usuarios_activos_hoy }}</span>
            <span class="kpi-label">Activos hoy</span>
          </div>
        </div>
      </div>

      <!-- Gráficos globales -->
      <div class="charts-row charts-global">
        <div class="card chart-grande">
          <div class="card-header">
            <div>
              <h2 class="card-title">Crecimiento de empresas</h2>
              <p class="card-subtitle">Altas por {{ periodoInfo.gran }} — {{ periodoInfo.titulo }}</p>
            </div>
            <div class="periodo-btns">
              <button
                v-for="p in PERIODOS" :key="p.key"
                :class="['periodo-btn', { active: periodoActivo === p.key }]"
                :disabled="cargandoGraficos"
                @click="cambiarPeriodo(p.key)">
                {{ p.label }}
              </button>
            </div>
          </div>
          <div class="chart-wrap" :class="{ 'chart-loading': cargandoGraficos }">
            <canvas ref="crecimientoCanvas"/>
          </div>
        </div>

        <div class="card chart-chico">
          <div class="card-header">
            <div>
              <h2 class="card-title">Distribución de flotas</h2>
              <p class="card-subtitle">Por tamaño de empresa</p>
            </div>
          </div>
          <div class="chart-wrap">
            <canvas ref="distribucionCanvas"/>
          </div>
        </div>
      </div>

      <!-- Fila inferior global -->
      <div class="bottom-row">
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">Top 5 empresas</h2>
              <p class="card-subtitle">Por cantidad de vehículos</p>
            </div>
            <button class="btn-link" @click="router.push('/empresas')">Ver todas →</button>
          </div>
          <table class="top-tabla">
            <thead>
              <tr><th>#</th><th>Empresa</th><th class="text-right">Vehículos</th></tr>
            </thead>
            <tbody>
              <tr v-if="topEmpresas.length === 0">
                <td colspan="3" class="empty">No hay empresas registradas.</td>
              </tr>
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
            <button class="acceso-card" @click="router.push('/empresas')">
              <div class="acceso-icon ac-purple">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
              </div>
              <span class="acceso-label">Empresas</span>
            </button>

            <button class="acceso-card" @click="router.push('/usuarios')">
              <div class="acceso-icon ac-blue">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
              </div>
              <span class="acceso-label">Usuarios</span>
            </button>

            <button class="acceso-card" @click="router.push('/logs')">
              <div class="acceso-icon ac-slate">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
                </svg>
              </div>
              <span class="acceso-label">Logs</span>
            </button>

            <button class="acceso-card" @click="router.push('/planes')">
              <div class="acceso-icon ac-indigo">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                </svg>
              </div>
              <span class="acceso-label">Planes</span>
            </button>
          </div>
        </div>
      </div>

    </template>

    <!-- ══════════════ USUARIO ══════════════ -->
    <template v-else>

      <div class="kpis">
        <div class="kpi-card">
          <div class="kpi-icon bg-indigo">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisEmpresa.total_flotas }}</span>
            <span class="kpi-label">Flotas</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-purple">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisEmpresa.total_vehiculos }}</span>
            <span class="kpi-label">Vehículos totales</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon bg-blue">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value">{{ kpisEmpresa.total_conductores }}</span>
            <span class="kpi-label">Conductores</span>
          </div>
        </div>

        <div class="kpi-card" :class="{ 'kpi-alert': kpisEmpresa.mantenciones_pendientes > 0 }">
          <div class="kpi-icon" :class="kpisEmpresa.mantenciones_pendientes > 0 ? 'bg-amber' : 'bg-slate'">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value" :class="{ 'text-amber': kpisEmpresa.mantenciones_pendientes > 0 }">
              {{ kpisEmpresa.mantenciones_pendientes }}
            </span>
            <span class="kpi-label">Mantenciones pendientes</span>
          </div>
        </div>

        <div class="kpi-card" :class="{ 'kpi-alert kpi-alert-red': kpisEmpresa.docs_por_vencer > 0 }">
          <div class="kpi-icon" :class="kpisEmpresa.docs_por_vencer > 0 ? 'bg-red' : 'bg-slate'">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value" :class="{ 'text-red': kpisEmpresa.docs_por_vencer > 0 }">
              {{ kpisEmpresa.docs_por_vencer }}
            </span>
            <span class="kpi-label">Docs. por vencer (30d)</span>
          </div>
        </div>
      </div>

      <!-- Gráficos empresa -->
      <div class="charts-row">
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">Vehículos por flota</h2>
              <p class="card-subtitle">Distribución actual</p>
            </div>
          </div>
          <div class="chart-wrap">
            <canvas ref="vehiculosCanvas"/>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">Mantenciones programadas</h2>
              <p class="card-subtitle">Por {{ periodoInfo.gran }} — {{ periodoInfo.titulo }}</p>
            </div>
            <div class="periodo-btns">
              <button
                v-for="p in PERIODOS" :key="p.key"
                :class="['periodo-btn', { active: periodoActivo === p.key }]"
                :disabled="cargandoGraficos"
                @click="cambiarPeriodo(p.key)">
                {{ p.label }}
              </button>
            </div>
          </div>
          <div class="chart-wrap" :class="{ 'chart-loading': cargandoGraficos }">
            <canvas ref="mantencionesCanvas"/>
          </div>
        </div>
      </div>

      <!-- Accesos rápidos empresa -->
      <div>
        <h2 class="section-title">Accesos rápidos</h2>
        <div v-if="accesosEmpresa.length" class="accesos accesos-auto">
          <button
            v-for="a in accesosEmpresa"
            :key="a.path"
            class="acceso-card"
            @click="router.push(ruta(a.path))"
          >
            <div :class="['acceso-icon', a.color]">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="a.icon"/>
            </div>
            <span class="acceso-label">{{ a.label }}</span>
          </button>
        </div>
        <p v-else class="accesos-vacio">Tu plan actual no tiene módulos habilitados.</p>
      </div>

    </template>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 1.75rem; gap: 1rem;
}
.page-title    { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.btn-refresh {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 1rem; background: #fff;
  border: 1px solid #E5E7EB; border-radius: 10px;
  font-size: 0.875rem; font-weight: 500; color: #374151;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.btn-refresh:hover:not(:disabled) { border-color: var(--color-accent, #6366F1); color: var(--color-accent, #4F46E5); }
.btn-refresh:disabled { opacity: 0.5; cursor: default; }
.btn-refresh svg { width: 15px; height: 15px; }

.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 3rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: var(--color-accent, #7C3AED); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.875rem 1rem; border-radius: 10px; font-size: 0.875rem; }

/* ── KPIs ─────────────────────────────── */
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem; margin-bottom: 1.5rem;
}
.kpi-card {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  padding: 1.2rem 1.25rem; display: flex; align-items: center; gap: 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04); position: relative;
  transition: box-shadow 0.15s;
}
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.kpi-alert      { border-color: #FDE68A; background: #FFFBEB; }
.kpi-alert-red  { border-color: #FECACA !important; background: #FEF2F2 !important; }

.kpi-icon { width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.kpi-icon svg { width: 22px; height: 22px; }
.bg-purple  { background: #EDE9FE; color: #6D28D9; }
.bg-indigo  { background: #EEF2FF; color: #4338CA; }
.bg-blue    { background: #EFF6FF; color: #2563EB; }
.bg-emerald { background: #ECFDF5; color: #059669; }
.bg-amber   { background: #FFFBEB; color: #D97706; }
.bg-green   { background: #F0FDF4; color: #16A34A; }
.bg-red     { background: #FEF2F2; color: #DC2626; }
.bg-slate   { background: #F1F5F9; color: #64748B; }

.kpi-data  { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.kpi-value { font-size: 1.75rem; font-weight: 700; color: #111827; line-height: 1; }
.kpi-label { font-size: 0.8rem; color: #6B7280; margin-top: 0.2rem; }
.kpi-sub   { font-size: 0.75rem; color: #9CA3AF; margin-top: 0.1rem; }

.text-amber { color: #D97706; }
.text-green { color: #16A34A; }
.text-red   { color: #DC2626; }

.kpi-pct {
  position: absolute; top: 0.75rem; right: 0.75rem;
  font-size: 0.7rem; font-weight: 700; color: #059669;
  background: #ECFDF5; border-radius: 999px; padding: 0.15rem 0.5rem;
}

/* ── Cards ────────────────────────────── */
.card {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04); overflow: hidden;
}
.card-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; gap: 1rem;
}
.card-title    { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.2rem; }
.card-subtitle { font-size: 0.8rem; color: #9CA3AF; margin: 0; }
.btn-link {
  font-size: 0.8125rem; font-weight: 600; color: var(--color-accent, #4F46E5);
  background: none; border: none; cursor: pointer; padding: 0; white-space: nowrap;
  font-family: inherit;
}
.btn-link:hover { text-decoration: underline; }

/* ── Períodos ─────────────────────────── */
.periodo-btns {
  display: flex; gap: 0.2rem;
  background: #F3F4F6; border-radius: 8px; padding: 0.25rem; flex-shrink: 0;
}
.periodo-btn {
  padding: 0.275rem 0.65rem; border-radius: 6px; border: none;
  font-size: 0.75rem; font-weight: 600; color: #6B7280;
  background: transparent; cursor: pointer; font-family: inherit;
  transition: all 0.15s; white-space: nowrap;
}
.periodo-btn.active { background: #fff; color: var(--color-accent, #4F46E5); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.periodo-btn:hover:not(.active):not(:disabled) { color: #374151; }
.periodo-btn:disabled { opacity: 0.5; cursor: default; }

/* ── Charts ───────────────────────────── */
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
.charts-global { grid-template-columns: 2fr 1fr; }
@media (max-width: 960px) { .charts-row, .charts-global { grid-template-columns: 1fr; } }

.chart-wrap { padding: 1.25rem 1.5rem; height: 240px; }
.chart-loading { opacity: 0.45; transition: opacity 0.2s; }

/* ── Fila inferior SUPERADMIN ─────────── */
.bottom-row { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .bottom-row { grid-template-columns: 1fr; } }

.section-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }

.top-tabla { width: 100%; border-collapse: collapse; }
.top-tabla th {
  padding: 0.65rem 1.5rem; text-align: left;
  font-size: 0.7rem; font-weight: 600; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.05em;
  background: #F9FAFB; border-bottom: 1px solid #F3F4F6;
}
.top-tabla td { padding: 0.8rem 1.5rem; font-size: 0.875rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.top-tabla tr:last-child td { border-bottom: none; }
.top-tabla tr:hover td { background: #FAFAFA; }
.rank {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: #EEF2FF; color: #4338CA; font-size: 0.7rem; font-weight: 700;
}
.empresa-nombre { font-weight: 500; color: #111827; }
.text-right { text-align: right; }
.font-semibold { font-weight: 600; color: #111827; }
.empty { text-align: center; color: #9CA3AF; padding: 2rem !important; }

/* ── Accesos rápidos ──────────────────── */
.accesos { display: grid; gap: 0.75rem; }
.accesos-2x2  { grid-template-columns: 1fr 1fr; }
.accesos-auto { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
.accesos-vacio { font-size: 0.875rem; color: #9CA3AF; padding: 1rem 0; margin: 0; }

.acceso-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.6rem;
  padding: 1.25rem 0.75rem;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.acceso-card:hover { border-color: var(--color-accent, #6366F1); box-shadow: 0 4px 12px rgba(99,102,241,0.12); transform: translateY(-1px); }

.acceso-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.acceso-icon svg { width: 22px; height: 22px; }
.ac-purple { background: #EDE9FE; color: #6D28D9; }
.ac-blue   { background: #EFF6FF; color: #2563EB; }
.ac-amber  { background: #FFFBEB; color: #D97706; }
.ac-slate  { background: #F1F5F9; color: #475569; }
.ac-indigo { background: #EEF2FF; color: #4338CA; }

.acceso-label { font-size: 0.8125rem; font-weight: 600; color: #374151; }
</style>
