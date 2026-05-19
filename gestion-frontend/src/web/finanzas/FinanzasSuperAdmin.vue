<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const toast = useToast()

const cargando       = ref(false)
const datos          = ref(null)
const historico      = ref([])
const mesesPeriodo   = ref(12)
const ordenMrr       = ref(false)
const chartCanvas    = ref(null)
let   chartInstance  = null

// ── Tiempo real ────────────────────────────────────────────
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

async function cargar() {
  cargando.value = true
  try {
    const [finRes, histRes] = await Promise.all([
      apiFetch('/api/admin/finanzas/'),
      apiFetch(`/api/admin/finanzas/historico/?meses=${mesesPeriodo.value}`),
    ])
    if (finRes.ok) datos.value = await finRes.json()
    else toast.error('Error al cargar datos financieros.')
    if (histRes.ok) historico.value = await histRes.json()
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
    ultimaActualizacion.value = new Date()
    actualizarLabel()
  }
}

function crearChart() {
  if (!chartCanvas.value || !historico.value.length) return
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }

  const labels = historico.value.map(h => `${labelMes(h.mes)} ${h.anio}`)
  const mrrData = historico.value.map(h => h.mrr)
  const nuevasData = historico.value.map(h => h.nuevas)

  chartInstance = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'MRR',
          data: mrrData,
          borderColor: '#4F46E5',
          backgroundColor: 'rgba(79, 70, 229, 0.08)',
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
          label: 'Nuevas suscripciones',
          data: nuevasData,
          borderColor: '#059669',
          backgroundColor: 'rgba(5, 150, 105, 0.06)',
          borderWidth: 2,
          pointBackgroundColor: '#059669',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.35,
          fill: true,
          yAxisID: 'y2',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { size: 12 }, padding: 16, usePointStyle: true, pointStyleWidth: 10 },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              if (ctx.dataset.label === 'MRR') return ` MRR: ${clp(ctx.parsed.y)}`
              return ` Nuevas: ${ctx.parsed.y}`
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: '#F3F4F6' },
          ticks: { font: { size: 11 }, color: '#6B7280' },
        },
        y: {
          position: 'left',
          grid: { color: '#F3F4F6' },
          ticks: { font: { size: 11 }, color: '#6B7280', callback: (v) => clp(v) },
        },
        y2: {
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { font: { size: 11 }, color: '#059669', stepSize: 1 },
          title: { display: true, text: 'Nuevas', color: '#059669', font: { size: 11 } },
        },
      },
    },
  })
}

watch(historico, async () => { await nextTick(); crearChart() }, { deep: true })

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
  if (chartInstance) chartInstance.destroy()
})

function clp(val) {
  if (val == null || val === 0) return '$0'
  return '$' + Number(val).toLocaleString('es-CL')
}

function pct(part, total) {
  if (!total) return 0
  return Math.round(part / total * 100)
}

const ESTADO_COLORES = {
  activa:     { bg: '#ECFDF5', text: '#059669' },
  suspendida: { bg: '#FEF2F2', text: '#DC2626' },
  trial:      { bg: '#EFF6FF', text: '#2563EB' },
  gracia:     { bg: '#FFFBEB', text: '#D97706' },
  cancelada:  { bg: '#F3F4F6', text: '#6B7280' },
}
const PLAN_COLORES = {
  basico:     { bg: '#EEF2FF', text: '#4338CA' },
  pro:        { bg: '#F5F3FF', text: '#7C3AED' },
  enterprise: { bg: '#FFF7ED', text: '#C2410C' },
}

function estadoStyle(estado) { return ESTADO_COLORES[estado] || { bg: '#F3F4F6', text: '#6B7280' } }
function planStyle(plan)     { return PLAN_COLORES[plan]     || { bg: '#F3F4F6', text: '#6B7280' } }

const empresasOrdenadas = computed(() => {
  if (!datos.value?.empresas_suscritas) return []
  return [...datos.value.empresas_suscritas].sort((a, b) =>
    ordenMrr.value ? a.mrr - b.mrr : b.mrr - a.mrr
  )
})

const NOMBRE_MES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
function labelMes(mes) { return NOMBRE_MES[mes - 1] || '' }
</script>

<template>
  <div class="page">
    <div class="header">
      <div>
        <h1 class="titulo">Finanzas SaaS</h1>
        <p class="subtitulo">Dashboard de ingresos de la plataforma</p>
      </div>
      <div class="header-right">
        <div class="refresh-bar">
          <span v-if="tiempoLabel" class="refresh-label">Actualizado {{ tiempoLabel }}</span>
          <button class="btn-refresh" @click="cargar" :disabled="cargando" title="Actualizar datos">
            <svg :class="{ 'spin': cargando }" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0
                   0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>
        <select v-model="mesesPeriodo" class="sel" @change="cargar">
          <option :value="3">Últimos 3 meses</option>
          <option :value="6">Últimos 6 meses</option>
          <option :value="12">Últimos 12 meses</option>
        </select>
      </div>
    </div>

    <div v-if="cargando" class="loading-wrap">
      <div class="spinner"></div>
      <span>Cargando datos financieros...</span>
    </div>

    <template v-else-if="datos">
      <!-- ── KPIs ── -->
      <div class="kpis">
        <div class="kpi-card">
          <div class="kpi-label">MRR</div>
          <div class="kpi-value">{{ clp(datos.mrr) }}</div>
          <div class="kpi-sub">Ingreso mensual recurrente</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">ARR</div>
          <div class="kpi-value">{{ clp(datos.arr) }}</div>
          <div class="kpi-sub">Ingreso anual proyectado</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Churn rate</div>
          <div class="kpi-value" :style="{ color: datos.churn_rate > 5 ? '#DC2626' : datos.churn_rate > 2 ? '#F59E0B' : '#059669' }">
            {{ datos.churn_rate }}%
          </div>
          <div class="kpi-sub">Cancelaciones / mes</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">LTV promedio</div>
          <div class="kpi-value">{{ datos.ltv_promedio > 0 ? clp(datos.ltv_promedio) : '—' }}</div>
          <div class="kpi-sub">Valor de vida del cliente</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Empresas activas</div>
          <div class="kpi-value" style="color:#059669">{{ datos.empresas_activas }}</div>
          <div class="kpi-sub">Con plan asignado</div>
        </div>
      </div>

      <!-- ── Fila media ── -->
      <div class="grid-2 mb-4">
        <!-- Ingresos por plan -->
        <div class="card">
          <div class="card-head"><h3 class="card-title">Ingresos por plan</h3></div>
          <div class="card-body">
            <div v-if="!datos.ingresos_por_plan?.length" class="empty-msg">Sin datos de planes.</div>
            <div v-else class="planes-list">
              <div v-for="p in datos.ingresos_por_plan" :key="p.plan" class="plan-row">
                <div class="plan-info">
                  <span class="badge" :style="{ background: planStyle(p.plan).bg, color: planStyle(p.plan).text }">
                    {{ p.plan.charAt(0).toUpperCase() + p.plan.slice(1) }}
                  </span>
                  <span class="plan-empresas">{{ p.empresas }} empresa{{ p.empresas !== 1 ? 's' : '' }}</span>
                </div>
                <div class="plan-barra-wrap">
                  <div class="plan-barra" :style="{ width: p.pct + '%', background: planStyle(p.plan).text }"></div>
                </div>
                <div class="plan-vals">
                  <span class="font-medium">{{ clp(p.mrr) }}</span>
                  <span class="pct-text">{{ p.pct }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Movimientos del mes -->
        <div class="card">
          <div class="card-head"><h3 class="card-title">Movimientos del mes</h3></div>
          <div class="card-body">
            <div v-if="datos.movimientos_mes" class="movs">
              <div class="mov-item" style="background:#F0FDF4;border-color:#BBF7D0">
                <div class="mov-top">
                  <span class="mov-label" style="color:#059669">Nuevas suscripciones</span>
                  <span class="mov-count" style="color:#059669">+{{ datos.movimientos_mes.nuevas_suscripciones.cantidad }}</span>
                </div>
                <div class="mov-mrr" style="color:#059669">
                  +{{ clp(datos.movimientos_mes.nuevas_suscripciones.mrr_ganado) }} MRR
                </div>
              </div>

              <div class="mov-item" style="background:#EFF6FF;border-color:#BFDBFE">
                <div class="mov-top">
                  <span class="mov-label" style="color:#2563EB">Upgrades</span>
                  <span class="mov-count" style="color:#2563EB">+{{ datos.movimientos_mes.upgrades.cantidad }}</span>
                </div>
                <div class="mov-mrr" style="color:#2563EB">
                  +{{ clp(datos.movimientos_mes.upgrades.mrr_expansion) }} expansión
                </div>
              </div>

              <div class="mov-item" style="background:#FEF2F2;border-color:#FECACA">
                <div class="mov-top">
                  <span class="mov-label" style="color:#DC2626">Cancelaciones</span>
                  <span class="mov-count" style="color:#DC2626">-{{ datos.movimientos_mes.cancelaciones.cantidad }}</span>
                </div>
                <div class="mov-mrr" style="color:#DC2626">
                  -{{ clp(datos.movimientos_mes.cancelaciones.mrr_perdido) }} MRR
                </div>
              </div>

              <div class="mov-item" style="background:#FFFBEB;border-color:#FDE68A">
                <div class="mov-top">
                  <span class="mov-label" style="color:#D97706">Pagos fallidos</span>
                  <span class="mov-count" style="color:#D97706">{{ datos.movimientos_mes.pagos_fallidos.cantidad }}</span>
                </div>
                <div class="mov-mrr" style="color:#D97706">Requieren atención</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Evolución MRR ── -->
      <div class="card mb-4">
        <div class="card-head">
          <h3 class="card-title">Evolución MRR — últimos {{ mesesPeriodo }} meses</h3>
        </div>
        <div class="card-body">
          <div v-if="!historico.length" class="empty-msg">Sin historial disponible.</div>
          <div v-else class="chart-container">
            <canvas ref="chartCanvas"></canvas>
          </div>
        </div>
      </div>

      <!-- ── Tabla empresas ── -->
      <div class="card">
        <div class="card-head">
          <h3 class="card-title">Empresas suscritas</h3>
          <span class="sub-count">{{ datos.empresas_suscritas?.length || 0 }} empresa{{ (datos.empresas_suscritas?.length || 0) !== 1 ? 's' : '' }}</span>
        </div>
        <div v-if="!datos.empresas_suscritas?.length" class="card-body">
          <p class="empty-msg">Sin empresas con plan asignado.</p>
        </div>
        <table v-else class="tabla">
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Plan</th>
              <th class="sortable" @click="ordenMrr = !ordenMrr">
                MRR <span>{{ ordenMrr ? '↑' : '↓' }}</span>
              </th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in empresasOrdenadas" :key="e.empresa_id">
              <td class="font-medium">{{ e.nombre }}</td>
              <td>
                <span class="badge" :style="{ background: planStyle(e.plan).bg, color: planStyle(e.plan).text }">
                  {{ e.plan.charAt(0).toUpperCase() + e.plan.slice(1) }}
                </span>
              </td>
              <td class="font-medium">{{ clp(e.mrr) }}</td>
              <td>
                <span class="badge" :style="{ background: estadoStyle(e.estado_suscripcion).bg, color: estadoStyle(e.estado_suscripcion).text }">
                  {{ e.estado_suscripcion.charAt(0).toUpperCase() + e.estado_suscripcion.slice(1) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 1.5rem 2rem; max-width: 1400px; }

.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; }
.titulo { font-size: 1.5rem; font-weight: 800; color: #111827; margin: 0 0 0.2rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-right { display: flex; align-items: center; gap: 0.75rem; }
.sel { padding: 0.4rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.8rem; background: #fff; color: #374151; cursor: pointer; }
.refresh-bar  { display: flex; align-items: center; gap: 0.5rem; }
.refresh-label { font-size: 0.75rem; color: #9CA3AF; white-space: nowrap; }
.btn-refresh  { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; border: 1.5px solid #E5E7EB; background: #fff; color: #6B7280; cursor: pointer; transition: all 0.15s; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-accent, #4F46E5); color: var(--color-accent, #4F46E5); }
.btn-refresh:disabled { opacity: 0.5; cursor: default; }
.btn-refresh svg { width: 15px; height: 15px; }
.spin { animation: spin 0.7s linear infinite; }

.loading-wrap { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; padding: 3rem 0; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: var(--color-accent, #4F46E5); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* KPIs */
.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.1rem 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-label { font-size: 0.75rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.35rem; }
.kpi-value { font-size: 1.5rem; font-weight: 800; color: #111827; line-height: 1.1; margin-bottom: 0.25rem; }
.kpi-sub { font-size: 0.72rem; color: #9CA3AF; }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.mb-4 { margin-bottom: 1rem; }

/* Cards */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.card-body { padding: 1.25rem; }
.mrr-max-label { font-size: 0.8rem; color: #9CA3AF; }
.sub-count { font-size: 0.8rem; color: #9CA3AF; }

.empty-msg { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 1.5rem 0; }

/* Ingresos por plan */
.planes-list { display: flex; flex-direction: column; gap: 1rem; }
.plan-row { display: flex; align-items: center; gap: 0.75rem; }
.plan-info { display: flex; align-items: center; gap: 0.5rem; width: 160px; flex-shrink: 0; }
.plan-empresas { font-size: 0.75rem; color: #9CA3AF; }
.plan-barra-wrap { flex: 1; height: 8px; background: #F3F4F6; border-radius: 4px; overflow: hidden; }
.plan-barra { height: 100%; border-radius: 4px; transition: width 0.4s; opacity: 0.85; }
.plan-vals { display: flex; gap: 0.5rem; align-items: center; width: 110px; justify-content: flex-end; }
.pct-text { font-size: 0.75rem; color: #9CA3AF; }
.font-medium { font-weight: 600; color: #111827; }

/* Movimientos */
.movs { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.mov-item { border: 1px solid; border-radius: 10px; padding: 0.75rem 1rem; }
.mov-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.2rem; }
.mov-label { font-size: 0.8rem; font-weight: 600; }
.mov-count { font-size: 1.1rem; font-weight: 800; }
.mov-mrr { font-size: 0.75rem; opacity: 0.8; }

/* Gráfico MRR */
.chart-container { position: relative; height: 260px; }
.mrr-max-label { font-size: 0.8rem; color: #9CA3AF; }

/* Tabla empresas */
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tr:hover td { background: #FAFAFA; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: #374151; }

.badge { padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
</style>
