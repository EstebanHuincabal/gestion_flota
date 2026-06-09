<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../../utils/permisos.js'
import { useToast } from '../../../../utils/useToast.js'
import { usePaginacion } from '../../../../composables/usePaginacion.js'
import PaginacionTabla from '../../../../components/PaginacionTabla.vue'

const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = useToast()

const historial   = ref([])
const vehiculos   = ref([])
const resumen     = ref({ realizadas: 0, costo_mes: 0, costo_total: 0 })
const cargando    = ref(true)

const filtroVehiculo = ref('')
const filtroMes      = ref('')

const esSuperadmin     = JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN'
const empresaActiva    = ref(getEmpresaActiva())
const empresas         = ref([])
const cargandoEmpresas = ref(false)
const mostrarDropdown  = ref(false)
const busqueda         = ref('')
const sinEmpresa       = computed(() => esSuperadmin && !empresaActiva.value)
// Modo "Todas las empresas": vista de solo lectura con columna de empresa.
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)

const empresasFiltradas = computed(() => {
  if (!busqueda.value.trim()) return empresas.value
  const q = busqueda.value.toLowerCase()
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

const cargarEmpresas = async () => {
  if (!esSuperadmin) return
  cargandoEmpresas.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = conOpcionTodas(await res.json())
  } finally {
    cargandoEmpresas.value = false
  }
}

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  cargar()
}

const historialFiltrado = computed(() =>
  historial.value
    .filter(m => !filtroVehiculo.value || String(m.vehiculo_id) === filtroVehiculo.value)
    .filter(m => {
      if (!filtroMes.value) return true
      return m.fecha_realizada?.startsWith(filtroMes.value)
    })
)

const { pagina, totalPaginas, total, paginado, irA } = usePaginacion(historialFiltrado, 20)

const costoFiltrado = computed(() =>
  historialFiltrado.value.reduce((acc, m) => acc + Number(m.costo), 0)
)

const cargar = async () => {
  if (sinEmpresa.value) { cargando.value = false; return }
  cargando.value = true
  try {
    const [resList, resSum, resVeh] = await Promise.all([
      apiFetchEmpresa('/api/empresa/mantenciones/?estado=realizada'),
      apiFetchEmpresa('/api/empresa/mantenciones/resumen/'),
      apiFetchEmpresa('/api/empresa/vehiculos/'),
    ])
    if (resList.ok) historial.value = await resList.json()
    if (resSum.ok)  resumen.value   = await resSum.json()
    if (resVeh.ok)  vehiculos.value = await resVeh.json()
  } finally {
    cargando.value = false
  }
}

const irEditar = (m) => {
  if (!tienePermiso('mantenciones.editar')) { toast.agregar('Sin permisos', 'error'); return }
  router.push(ruta(`/mantenciones/${m.id}/editar`))
}

const formatFecha = (f) => f ? new Date(f + 'T12:00:00').toLocaleDateString('es-CL') : '—'

const diferenciaCosto = (m) => {
  if (!m.presupuesto) return null
  return Number(m.costo) - Number(m.presupuesto)
}

onMounted(async () => { await Promise.all([cargarEmpresas(), cargar()]) })
</script>

<template>
  <div class="page">

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenciones</h1>
        <p class="page-subtitle">Gestiona el mantenimiento y costos de tu flota</p>
      </div>
      <div v-if="esSuperadmin" class="selector-wrap">
        <button class="selector-btn" :class="{ 'sin-sel': !empresaActiva }" @click="mostrarDropdown = !mostrarDropdown">
          <span class="selector-icono"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg></span>
          <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa…' }}</span>
          <svg class="selector-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </button>
        <div v-if="mostrarDropdown" class="selector-dropdown">
          <div class="dropdown-search">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="busqueda" placeholder="Buscar empresa..." class="dropdown-input" autofocus/>
          </div>
          <div v-if="cargandoEmpresas" class="dropdown-empty">Cargando...</div>
          <div v-else-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</div>
          <button v-for="emp in empresasFiltradas" :key="emp.id" class="dropdown-option" :class="{ selected: empresaActiva?.id === emp.id }" @click="seleccionarEmpresa(emp)">
            <span class="option-avatar">{{ emp.nombre[0].toUpperCase() }}</span>
            <span class="option-nombre">{{ emp.nombre }}</span>
            <svg v-if="empresaActiva?.id === emp.id" class="option-check" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
          </button>
        </div>
        <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
      </div>
    </div>

    <!-- Sub-navegación -->
    <div class="subnav">
      <router-link :to="ruta('/mantenciones')"            class="subnav-tab" active-class="subnav-tab-active" exact>Programados</router-link>
      <router-link :to="ruta('/mantenciones/calendario')" class="subnav-tab" active-class="subnav-tab-active">Calendario</router-link>
      <router-link :to="ruta('/mantenciones/historial')"  class="subnav-tab" active-class="subnav-tab-active">Historial</router-link>
      <router-link :to="ruta('/mantenciones/nueva')"      class="subnav-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        Programar
      </router-link>
    </div>

    <div v-if="sinEmpresa" class="sin-empresa-box">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
      <p>Selecciona una empresa usando el selector de arriba a la derecha para ver su historial.</p>
    </div>
    <div v-else-if="cargando" class="loading"><div class="spinner"/>Cargando...</div>

    <template v-else>
      <!-- Stats -->
      <div class="stats-grid mb-6">
        <div class="stat-card stat-green">
          <h3>Total Realizadas</h3>
          <p class="stat-valor">{{ resumen.realizadas }}</p>
        </div>
        <div class="stat-card stat-orange">
          <h3>Gasto del Mes</h3>
          <p class="stat-valor-sm">${{ Number(resumen.costo_mes).toLocaleString('es-CL') }}</p>
        </div>
        <div class="stat-card stat-purple">
          <h3>Gasto Histórico</h3>
          <p class="stat-valor-sm">${{ Number(resumen.costo_total).toLocaleString('es-CL') }}</p>
        </div>
        <div class="stat-card stat-blue">
          <h3>Costo Filtrado</h3>
          <p class="stat-valor-sm">${{ costoFiltrado.toLocaleString('es-CL') }}</p>
        </div>
      </div>

      <!-- Filtros -->
      <div class="filtros mb-4">
        <select v-model="filtroVehiculo" class="input select-sm">
          <option value="">Todos los vehículos</option>
          <option v-for="v in vehiculos" :key="v.id" :value="String(v.id)">{{ v.patente }} — {{ v.marca }} {{ v.modelo }}</option>
        </select>
        <input v-model="filtroMes" type="month" class="input select-sm" title="Filtrar por mes de realización"/>
        <button v-if="filtroVehiculo || filtroMes" class="btn-clear" @click="filtroVehiculo = ''; filtroMes = ''">
          Limpiar filtros
        </button>
      </div>

      <!-- Tabla -->
      <div class="card">
        <table class="table">
          <thead>
            <tr>
              <th v-if="esTodas">Empresa</th>
              <th>Vehículo</th>
              <th>Tipo / Descripción</th>
              <th>Fecha Realizada</th>
              <th>KM Realizado</th>
              <th>Taller / Proveedor</th>
              <th>Presupuesto</th>
              <th>Costo Real</th>
              <th>Diferencia</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in paginado" :key="m.id">
              <td v-if="esTodas" class="font-medium">{{ m.empresa_nombre || '—' }}</td>
              <td>
                <strong>{{ m.vehiculo_patente }}</strong>
                <span class="text-xs text-muted block">{{ m.vehiculo_descripcion }}</span>
              </td>
              <td>
                <span class="font-medium">{{ m.tipo_mantencion }}</span>
                <span v-if="m.descripcion" class="text-xs text-muted block truncate max-w-xs">{{ m.descripcion }}</span>
              </td>
              <td>{{ formatFecha(m.fecha_realizada) }}</td>
              <td class="text-muted">
                <span v-if="m.kilometraje_realizado">{{ m.kilometraje_realizado.toLocaleString('es-CL') }} km</span>
                <span v-else>—</span>
              </td>
              <td class="text-muted">{{ m.taller_proveedor || '—' }}</td>
              <td class="text-muted">{{ m.presupuesto ? '$' + Number(m.presupuesto).toLocaleString('es-CL') : '—' }}</td>
              <td class="font-medium">${{ Number(m.costo).toLocaleString('es-CL') }}</td>
              <td>
                <template v-if="diferenciaCosto(m) !== null">
                  <span :class="['badge-dif', diferenciaCosto(m) > 0 ? 'dif-sobre' : 'dif-bajo']">
                    {{ diferenciaCosto(m) > 0 ? '+' : '' }}${{ Math.abs(diferenciaCosto(m)).toLocaleString('es-CL') }}
                  </span>
                </template>
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <button class="btn-icon" title="Editar" @click="irEditar(m)">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
              </td>
            </tr>
            <tr v-if="!historialFiltrado.length">
              <td colspan="9" class="empty-row">
                {{ filtroVehiculo || filtroMes ? 'Sin resultados para el filtro aplicado.' : 'No hay mantenciones realizadas aún.' }}
              </td>
            </tr>
          </tbody>
        </table>
        <PaginacionTabla
          :pagina="pagina"
          :total-paginas="totalPaginas"
          :total="total"
          :por-pagina="20"
          @update:pagina="irA"
        />

        <!-- Totales del filtro -->
        <div v-if="historialFiltrado.length" class="tabla-footer">
          <span>{{ historialFiltrado.length }} registro{{ historialFiltrado.length !== 1 ? 's' : '' }}</span>
          <span class="footer-total">Total costo: <strong>${{ costoFiltrado.toLocaleString('es-CL') }}</strong></span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background: #F9FAFB; min-height: 100vh; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.subnav { display: flex; align-items: center; gap: 0.25rem; border-bottom: 2px solid #E5E7EB; margin-bottom: 1.75rem; }
.subnav-tab { padding: 0.625rem 1rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; text-decoration: none; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: color 0.15s; }
.subnav-tab:hover { color: #4F46E5; }
.subnav-tab-active { color: #4F46E5; border-bottom-color: #4F46E5; font-weight: 600; }
.subnav-btn { margin-left: auto; display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.45rem 1rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; text-decoration: none; transition: opacity 0.15s; }
.subnav-btn:hover { opacity: 0.9; }
.subnav-btn svg { width: 15px; height: 15px; }

/* Stats */
.mb-6 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.stat-card { padding: 1.25rem; border-radius: 12px; color: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.06); }
.stat-card h3 { font-size: 0.75rem; font-weight: 600; opacity: 0.85; margin: 0 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-valor { font-size: 1.75rem; font-weight: 700; margin: 0; }
.stat-valor-sm { font-size: 1.25rem; font-weight: 700; margin: 0; }
.stat-green  { background: linear-gradient(135deg,#10B981,#059669); }
.stat-orange { background: linear-gradient(135deg,#F97316,#EA580C); }
.stat-purple { background: linear-gradient(135deg,#8B5CF6,#6D28D9); }
.stat-blue   { background: linear-gradient(135deg,#3B82F6,#2563EB); }

/* Filtros */
.filtros { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
.select-sm { padding: 0.45rem 0.75rem; font-size: 0.8125rem; max-width: 260px; }
.btn-clear { padding: 0.45rem 0.875rem; background: none; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.8rem; color: #6B7280; cursor: pointer; transition: all 0.15s; }
.btn-clear:hover { border-color: #EF4444; color: #EF4444; }

/* Tabla */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.table th { background: #F9FAFB; padding: 0.875rem 1rem; text-align: left; font-weight: 600; color: #4B5563; border-bottom: 1px solid #E5E7EB; white-space: nowrap; }
.table td { padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; color: #111827; vertical-align: middle; }
.font-medium { font-weight: 500; }
.text-xs { font-size: 0.75rem; }
.text-muted { color: #6B7280; }
.block { display: block; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.max-w-xs { max-width: 200px; }

.badge-dif { display: inline-flex; padding: 0.2rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
.dif-sobre { background: #FEE2E2; color: #991B1B; }
.dif-bajo  { background: #D1FAE5; color: #065F46; }

.btn-icon { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #E5E7EB; background: #fff; color: #6B7280; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; }
.btn-icon svg { width: 15px; height: 15px; }
.btn-icon:hover { border-color: #4F46E5; color: #4F46E5; }

.empty-row { text-align: center; color: #9CA3AF; padding: 3rem 1rem !important; }

.tabla-footer { display: flex; justify-content: space-between; align-items: center; padding: 0.875rem 1rem; background: #F9FAFB; border-top: 1px solid #E5E7EB; font-size: 0.8125rem; color: #6B7280; }
.footer-total { font-size: 0.875rem; color: #374151; }
.footer-total strong { color: #111827; }

.loading, .empty { display: flex; flex-direction: column; align-items: center; padding: 4rem; color: #6B7280; }
.spinner { width: 28px; height: 28px; border: 3px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

.input { padding: 0.625rem 0.875rem; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; outline: none; background: #fff; }
.input:focus { border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }
.sin-empresa-box { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 4rem 2rem; text-align: center; color: #9CA3AF; }
.sin-empresa-box svg { width: 48px; height: 48px; color: #D1D5DB; }
.sin-empresa-box p { font-size: 0.9375rem; max-width: 360px; line-height: 1.6; margin: 0; }
.selector-wrap { position: relative; }
.selector-btn { display: flex; align-items: center; gap: 0.5rem; padding: 0.55rem 0.875rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; font-family: inherit; white-space: nowrap; transition: border-color 0.15s; max-width: 260px; }
.selector-btn:hover { border-color: #7C3AED; }
.selector-btn.sin-sel { border-style: dashed; color: #9CA3AF; }
.selector-icono svg { width: 16px; height: 16px; color: #6B7280; flex-shrink: 0; }
.selector-texto { flex: 1; overflow: hidden; text-overflow: ellipsis; text-align: left; }
.selector-chevron { width: 14px; height: 14px; color: #9CA3AF; flex-shrink: 0; }
.selector-dropdown { position: absolute; top: calc(100% + 6px); right: 0; width: 280px; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); overflow: hidden; z-index: 200; max-height: 320px; display: flex; flex-direction: column; overflow-y: auto; }
.dropdown-search { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0; }
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; flex-shrink: 0; }
.dropdown-input { flex: 1; border: none; outline: none; font-size: 0.875rem; color: #111827; font-family: inherit; background: transparent; }
.dropdown-empty { padding: 1rem; font-size: 0.8125rem; color: #9CA3AF; text-align: center; }
.dropdown-option { display: flex; align-items: center; gap: 0.625rem; width: 100%; padding: 0.625rem 0.875rem; background: none; border: none; cursor: pointer; text-align: left; font-family: inherit; transition: background 0.12s; }
.dropdown-option:hover { background: #F5F3FF; }
.dropdown-option.selected { background: #EEF2FF; }
.option-avatar { flex-shrink: 0; width: 28px; height: 28px; background: linear-gradient(135deg,#4F46E5,#7C3AED); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: #fff; }
.option-nombre { flex: 1; font-size: 0.875rem; font-weight: 500; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.option-check { width: 16px; height: 16px; color: #4F46E5; flex-shrink: 0; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 199; }
</style>
