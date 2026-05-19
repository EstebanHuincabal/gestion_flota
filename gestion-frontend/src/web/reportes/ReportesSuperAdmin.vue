<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'

const toast = useToast()

const cargando = ref(false)
const datos    = ref(null)
const anioSel  = ref(new Date().getFullYear())
const anios    = [anioSel.value, anioSel.value - 1, anioSel.value - 2]

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
    'Empresa', 'Plan', 'Flotas', 'Vehículos', 'Conductores',
    `Mantenciones ${anioSel.value}`, `Costo mantenciones ${anioSel.value}`, 'Docs vencidos',
  ]
  const filas = empresasOrdenadas.value.map(e => [
    e.nombre, e.plan_display || e.plan || '—',
    e.flotas, e.vehiculos, e.conductores,
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

// Carga
async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch(`/api/admin/reportes/empresas/?anio=${anioSel.value}`)
    if (res.ok) datos.value = await res.json()
    else toast.error('Error al cargar el reporte.')
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
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
        <button class="btn-export" @click="exportarCSV" :disabled="!datos?.empresas?.length">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Exportar CSV
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-wrap">
      <div class="spinner"/><span>Cargando datos...</span>
    </div>

    <template v-else-if="datos">
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
                <th class="sortable" @click="toggleOrden('flotas')">Flotas{{ flechaOrden('flotas') }}</th>
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
                <td>{{ e.flotas }}</td>
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
</style>
