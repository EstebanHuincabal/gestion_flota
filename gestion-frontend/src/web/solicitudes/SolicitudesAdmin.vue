<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { getEmpresaActiva, setEmpresaActiva, clearEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../utils/empresaActiva.js'
import { useModeracion } from '../../composables/useModeracion.js'
import AvisoModeracion from '../../components/AvisoModeracion.vue'

// ── Selector de empresa ──────────────────────────────────────────────────────
const empresas            = ref([])
const empresaSeleccionada = ref(null)
// Modo "Todas las empresas": solo lectura (sin aprobar/rechazar ni WebSocket).
const esTodas = computed(() => empresaSeleccionada.value?.id === EMPRESA_TODAS)
const busquedaEmpresa     = ref('')
const cargandoEmpresas    = ref(false)
const mostrarDropdown     = ref(false)

const empresasFiltradas = computed(() => {
  const q = busquedaEmpresa.value.toLowerCase().trim()
  if (!q) return empresas.value
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

async function cargarEmpresas() {
  cargandoEmpresas.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = conOpcionTodas(await res.json())
  } catch {
    empresas.value = []
  } finally {
    cargandoEmpresas.value = false
  }
}

function seleccionarEmpresa(emp) {
  empresaSeleccionada.value = emp
  busquedaEmpresa.value     = ''
  mostrarDropdown.value     = false
  setEmpresaActiva(emp)
}

function limpiarEmpresa() {
  empresaSeleccionada.value = null
  solicitudes.value = []
  resumen.value     = { pendientes: 0, en_revision: 0, aprobadas_hoy: 0, total_mes: 0 }
  total.value       = 0
  pages.value       = 1
  desconectarWS()
  clearEmpresaActiva()
}

// ── Estado principal ──────────────────────────────────────────────────────────
const solicitudes = ref([])
const resumen     = ref({ pendientes: 0, en_revision: 0, aprobadas_hoy: 0, total_mes: 0 })
const cargando    = ref(false)
const error       = ref('')
const total       = ref(0)
const page        = ref(1)
const pages       = ref(1)
const pageSize    = 15

// ── Filtros ───────────────────────────────────────────────────────────────────
const filtroEstado     = ref('')
const filtroTipo       = ref('')
const filtroBuscar     = ref('')
const filtroFechaDesde = ref('')
const filtroFechaHasta = ref('')

// ── Modales ───────────────────────────────────────────────────────────────────
const modalDetalle  = ref(null)
const modalRechazar = ref(null)
const motivoRechazo = ref('')
const errorRechazo  = ref('')
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()
const guardando     = ref(false)
const errorAccion   = ref('')


// ── Toast ─────────────────────────────────────────────────────────────────────
const toasts = ref([])
function toast(msg, tipo = 'ok') {
  const id = Date.now()
  toasts.value.push({ id, msg, tipo })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3500)
}

// ── Helpers de UI ─────────────────────────────────────────────────────────────
const estadoColor = {
  pendiente:   { bg: '#FEF3C7', text: '#92400E', label: 'Pendiente' },
  en_revision: { bg: '#DBEAFE', text: '#1E40AF', label: 'En revisión' },
  aprobado:    { bg: '#D1FAE5', text: '#065F46', label: 'Aprobado' },
  rechazado:   { bg: '#FEE2E2', text: '#991B1B', label: 'Rechazado' },
}
const prioridadColor = {
  alta:  { bg: '#FEE2E2', text: '#991B1B' },
  media: { bg: '#FEF3C7', text: '#92400E' },
  baja:  { bg: '#D1FAE5', text: '#065F46' },
}
const tipoIcon = {
  mantencion:  '🔧',
  combustible: '⛽',
  incidencia:  '⚠️',
  documento:   '📄',
}

function fmtFecha(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ── API helper — inyecta empresa_id ──────────────────────────────────────────
function apiEmpresa(path, options = {}) {
  if (!empresaSeleccionada.value) return Promise.reject(new Error('sin_empresa'))
  const sep = path.includes('?') ? '&' : '?'
  return apiFetch(`${path}${sep}empresa_id=${empresaSeleccionada.value.id}`, options)
}

// ── Carga de datos ────────────────────────────────────────────────────────────
async function cargar(resetPage = false) {
  if (!empresaSeleccionada.value) return
  if (resetPage) page.value = 1
  cargando.value = true
  error.value    = ''
  try {
    const params = new URLSearchParams({
      page:       page.value,
      page_size:  pageSize,
      empresa_id: empresaSeleccionada.value.id,
    })
    if (filtroEstado.value)     params.append('estado',      filtroEstado.value)
    if (filtroTipo.value)       params.append('tipo',        filtroTipo.value)
    if (filtroBuscar.value)     params.append('buscar',      filtroBuscar.value)
    if (filtroFechaDesde.value) params.append('fecha_desde', filtroFechaDesde.value)
    if (filtroFechaHasta.value) params.append('fecha_hasta', filtroFechaHasta.value)

    const res  = await apiFetch(`/api/empresa/solicitudes/?${params}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error al cargar solicitudes')

    solicitudes.value = data.solicitudes
    resumen.value     = data.resumen
    total.value       = data.total
    pages.value       = data.pages

    // Notificar al sidebar de Base.vue con el conteo actualizado
    window.dispatchEvent(new CustomEvent('solicitudes-admin-badge', {
      detail: data.resumen?.pendientes ?? 0,
    }))
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
let ws            = null
let wsEmpresaId   = null
let wsPingInterval = null

function conectarWS(empresaId) {
  if (ws && wsEmpresaId === empresaId) return
  desconectarWS()

  const token = localStorage.getItem('access_token')
  if (!token || !empresaId) return

  wsEmpresaId = empresaId
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/solicitudes/${empresaId}/?token=${token}`)

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.tipo === 'nueva_solicitud') {
        const nuevas = (resumen.value.pendientes || 0) + 1
        resumen.value.pendientes = nuevas
        toast(`Nueva solicitud de ${msg.solicitud?.conductor || 'un conductor'}: "${msg.solicitud?.titulo}"`, 'info')
        cargar()
        window.dispatchEvent(new CustomEvent('solicitudes-admin-badge', { detail: nuevas }))
      }
    } catch {}
  }

  ws.onclose = () => {
    clearInterval(wsPingInterval)
    if (ws?._manuallyClosed) return
    setTimeout(() => conectarWS(empresaId), 5000)
  }

  wsPingInterval = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
  }, 25000)
}

function desconectarWS() {
  clearInterval(wsPingInterval)
  if (ws) { ws._manuallyClosed = true; ws.close(); ws = null; wsEmpresaId = null }
}

// ── Acciones ──────────────────────────────────────────────────────────────────
async function marcarEnRevision(sol) {
  guardando.value   = true
  errorAccion.value = ''
  try {
    const res  = await apiEmpresa(`/api/empresa/solicitudes/${sol.id}/`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error')
    Object.assign(sol, data)
    if (modalDetalle.value?.id === sol.id) modalDetalle.value = { ...data }
    toast('Solicitud marcada "En revisión"', 'ok')
    await cargar()
  } catch (e) {
    errorAccion.value = e.message
  } finally {
    guardando.value = false
  }
}

async function aprobar(sol) {
  guardando.value   = true
  errorAccion.value = ''
  try {
    const res  = await apiEmpresa(`/api/empresa/solicitudes/${sol.id}/aprobar/`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuesta: '' }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error')
    if (modalDetalle.value?.id === sol.id) modalDetalle.value = { ...data.solicitud }
    toast('Solicitud aprobada ✓', 'ok')
    cerrarModalDetalle()
    await cargar()
  } catch (e) {
    errorAccion.value = e.message
  } finally {
    guardando.value = false
  }
}

function abrirModalRechazar(sol) {
  modalRechazar.value = sol
  motivoRechazo.value = ''
  errorRechazo.value  = ''
  limpiarMod()
}

async function confirmarRechazo() {
  if (motivoRechazo.value.trim().length < 10) {
    errorRechazo.value = 'El motivo debe tener al menos 10 caracteres.'
    return
  }
  const ok = await moderar(motivoRechazo.value)
  if (!ok) return
  guardando.value    = true
  errorRechazo.value = ''
  try {
    const res  = await apiEmpresa(`/api/empresa/solicitudes/${modalRechazar.value.id}/rechazar/`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuesta: motivoRechazo.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.respuesta || data.error || 'Error')
    if (modalDetalle.value?.id === modalRechazar.value.id) modalDetalle.value = { ...data.solicitud }
    toast('Solicitud rechazada', 'warn')
    modalRechazar.value = null
    cerrarModalDetalle()
    await cargar()
  } catch (e) {
    errorRechazo.value = e.message
  } finally {
    guardando.value = false
  }
}

async function verDetalle(sol) {
  errorAccion.value = ''
  try {
    const res  = await apiEmpresa(`/api/empresa/solicitudes/${sol.id}/`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error')
    modalDetalle.value = data
  } catch {
    modalDetalle.value = { ...sol }
  }
}

function cerrarModalDetalle() {
  modalDetalle.value = null
  errorAccion.value  = ''
}

// ── Watch empresa seleccionada ────────────────────────────────────────────────
watch(empresaSeleccionada, (nueva) => {
  if (nueva) {
    // Reset filtros al cambiar empresa
    filtroEstado.value     = ''
    filtroTipo.value       = ''
    filtroBuscar.value     = ''
    filtroFechaDesde.value = ''
    filtroFechaHasta.value = ''
    // En modo "Todas" no hay canal WebSocket único por empresa: solo carga.
    if (nueva.id === EMPRESA_TODAS) desconectarWS()
    else conectarWS(nueva.id)
    cargar(true)
  }
})

// Watch filtros
let debounce = null
watch([filtroEstado, filtroTipo, filtroFechaDesde, filtroFechaHasta], () => cargar(true))
watch(filtroBuscar, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => cargar(true), 400)
})

// ── Cerrar dropdown al hacer click fuera ──────────────────────────────────────
function handleClickOutside(e) {
  if (!e.target.closest('.sa-empresa-selector')) mostrarDropdown.value = false
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  cargarEmpresas()
  // Restaurar empresa activa seleccionada en otra vista
  const activa = getEmpresaActiva()
  if (activa) empresaSeleccionada.value = activa
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  desconectarWS()
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="sa-page">

    <!-- ── Encabezado ──────────────────────────────────────────────────────── -->
    <div class="sa-header">
      <div>
        <h1 class="sa-title">Solicitudes de Conductores</h1>
        <p class="sa-subtitle">Visualiza y gestiona solicitudes de cualquier empresa</p>
      </div>
      <button
        class="btn-refresh"
        @click="cargar()"
        :disabled="cargando || !empresaSeleccionada"
        title="Actualizar"
      >
        <svg :class="['icon-refresh', { spin: cargando }]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Actualizar
      </button>
    </div>

    <!-- ── Selector de empresa ─────────────────────────────────────────────── -->
    <div class="sa-empresa-selector-wrap">
      <label class="sa-empresa-label">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px;color:#6366F1">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        Empresa
      </label>

      <div class="sa-empresa-selector">
        <!-- Botón principal del selector -->
        <button
          class="sa-empresa-btn"
          @click.stop="mostrarDropdown = !mostrarDropdown"
          :class="{ 'sa-empresa-btn--active': empresaSeleccionada }"
        >
          <span v-if="empresaSeleccionada" class="sa-empresa-nombre">
            {{ empresaSeleccionada.nombre }}
          </span>
          <span v-else class="sa-empresa-placeholder">Selecciona una empresa…</span>
          <span v-if="empresaSeleccionada" class="sa-empresa-clear" @click.stop="limpiarEmpresa" title="Limpiar">✕</span>
          <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px;color:#9CA3AF;flex-shrink:0">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <!-- Dropdown -->
        <div v-if="mostrarDropdown" class="sa-dropdown">
          <div class="sa-dropdown-search">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:15px;height:15px;color:#9CA3AF;flex-shrink:0">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              v-model="busquedaEmpresa"
              type="text"
              placeholder="Buscar empresa…"
              class="sa-dropdown-input"
              @click.stop
            />
          </div>

          <div class="sa-dropdown-list">
            <div v-if="cargandoEmpresas" class="sa-dropdown-loading">
              <span class="spinner-sm"/>
              Cargando…
            </div>
            <div v-else-if="empresasFiltradas.length === 0" class="sa-dropdown-empty">
              Sin resultados
            </div>
            <button
              v-for="emp in empresasFiltradas"
              :key="emp.id"
              class="sa-dropdown-item"
              :class="{ 'sa-dropdown-item--selected': empresaSeleccionada?.id === emp.id }"
              @click="seleccionarEmpresa(emp)"
            >
              <span class="sa-empresa-avatar">{{ emp.nombre[0]?.toUpperCase() }}</span>
              <div class="sa-dropdown-item-info">
                <span class="sa-dropdown-item-nombre">{{ emp.nombre }}</span>
                <span class="sa-dropdown-item-rut">{{ emp.rut || '' }}</span>
              </div>
              <span v-if="empresaSeleccionada?.id === emp.id" style="color:#6366F1;font-size:0.875rem">✓</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Estado vacío: sin empresa ──────────────────────────────────────── -->
    <div v-if="!empresaSeleccionada" class="sa-empty-empresa">
      <div class="sa-empty-icon">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.25"
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
      </div>
      <h3>Selecciona una empresa</h3>
      <p>Elige una empresa del selector para ver sus solicitudes de conductores</p>
    </div>

    <!-- ── Contenido (solo si empresa seleccionada) ─────────────────────────── -->
    <template v-else>

      <!-- KPI Cards -->
      <div class="sc-kpis">
        <div class="kpi-card kpi-warn">
          <div class="kpi-value">{{ resumen.pendientes }}</div>
          <div class="kpi-label">Pendientes</div>
        </div>
        <div class="kpi-card kpi-info">
          <div class="kpi-value">{{ resumen.en_revision }}</div>
          <div class="kpi-label">En revisión</div>
        </div>
        <div class="kpi-card kpi-ok">
          <div class="kpi-value">{{ resumen.aprobadas_hoy }}</div>
          <div class="kpi-label">Aprobadas hoy</div>
        </div>
        <div class="kpi-card kpi-neutral">
          <div class="kpi-value">{{ resumen.total_mes }}</div>
          <div class="kpi-label">Total este mes</div>
        </div>
      </div>

      <!-- Filtros -->
      <div class="sc-filters">
        <input
          v-model="filtroBuscar"
          type="search"
          placeholder="Buscar por título…"
          class="filter-input filter-search"
        />
        <select v-model="filtroEstado" class="filter-input">
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendiente</option>
          <option value="en_revision">En revisión</option>
          <option value="aprobado">Aprobado</option>
          <option value="rechazado">Rechazado</option>
        </select>
        <select v-model="filtroTipo" class="filter-input">
          <option value="">Todos los tipos</option>
          <option value="mantencion">Mantención</option>
          <option value="combustible">Combustible</option>
          <option value="incidencia">Incidencia</option>
          <option value="documento">Documento</option>
        </select>
        <input v-model="filtroFechaDesde" type="date" class="filter-input" title="Desde" />
        <input v-model="filtroFechaHasta" type="date" class="filter-input" title="Hasta" />
      </div>

      <!-- Error global -->
      <div v-if="error" class="sc-error">{{ error }}</div>

      <!-- Tabla -->
      <div class="sc-table-wrap">
        <template v-if="cargando && solicitudes.length === 0">
          <div v-for="i in 5" :key="i" class="skeleton-row">
            <div class="skel skel-wide"/>
            <div class="skel skel-mid"/>
            <div class="skel skel-short"/>
            <div class="skel skel-short"/>
            <div class="skel skel-mid"/>
          </div>
        </template>

        <div v-else-if="!cargando && solicitudes.length === 0" class="sc-empty">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:48px;height:48px;color:#D1D5DB">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
          <p>No hay solicitudes con los filtros seleccionados</p>
        </div>

        <table v-else class="sc-table">
          <thead>
            <tr>
              <th v-if="esTodas">Empresa</th>
              <th>Conductor</th>
              <th>Tipo</th>
              <th>Título</th>
              <th>Prioridad</th>
              <th>Estado</th>
              <th>Vehículo</th>
              <th>Fecha</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sol in solicitudes" :key="sol.id" :class="{ 'row-pendiente': sol.estado === 'pendiente' }">
              <td v-if="esTodas" class="td-empresa">{{ sol.empresa_nombre || '—' }}</td>
              <td>
                <div class="conductor-cell">
                  <div class="conductor-avatar">{{ sol.conductor_iniciales || '?' }}</div>
                  <span>{{ sol.conductor_nombre || '—' }}</span>
                </div>
              </td>
              <td>
                <span class="tipo-badge">{{ tipoIcon[sol.tipo] }} {{ sol.tipo_display }}</span>
              </td>
              <td class="td-titulo">
                {{ sol.titulo }}
                <span v-if="sol.extra?.es_checklist" class="badge-checklist" title="Falla de checklist pre-viaje">CK</span>
              </td>
              <td>
                <span class="badge" :style="{ background: prioridadColor[sol.prioridad]?.bg, color: prioridadColor[sol.prioridad]?.text }">
                  {{ sol.prioridad_display }}
                </span>
              </td>
              <td>
                <span class="badge" :style="{ background: estadoColor[sol.estado]?.bg, color: estadoColor[sol.estado]?.text }">
                  {{ estadoColor[sol.estado]?.label || sol.estado }}
                </span>
              </td>
              <td class="td-vehiculo">{{ sol.vehiculo_patente || '—' }}</td>
              <td class="td-fecha">{{ fmtFecha(sol.created_at) }}</td>
              <td>
                <div class="action-btns">
                  <button class="btn-action btn-ver" @click="verDetalle(sol)" title="Ver detalle">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                  </button>
                  <template v-if="sol.estado === 'pendiente' || sol.estado === 'en_revision'">
                    <button class="btn-action btn-ok" @click="aprobar(sol)" title="Aprobar" :disabled="guardando">✓</button>
                    <button class="btn-action btn-nok" @click="abrirModalRechazar(sol)" title="Rechazar" :disabled="guardando">✕</button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div v-if="pages > 1" class="sc-pagination">
        <button :disabled="page <= 1" @click="page--; cargar()">‹ Anterior</button>
        <span>Página {{ page }} de {{ pages }} ({{ total }} solicitudes)</span>
        <button :disabled="page >= pages" @click="page++; cargar()">Siguiente ›</button>
      </div>
      <p v-else-if="total > 0 && !cargando" class="sc-total">{{ total }} solicitud{{ total !== 1 ? 'es' : '' }}</p>

    </template>

    <!-- ── Modal Detalle ────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="modalDetalle" class="overlay" @click.self="cerrarModalDetalle">
        <div class="modal modal-detalle">
          <div class="modal-header">
            <h2>{{ tipoIcon[modalDetalle.tipo] }} {{ modalDetalle.titulo }}</h2>
            <button class="modal-close" @click="cerrarModalDetalle">✕</button>
          </div>
          <div class="modal-body">
            <div class="detalle-badges">
              <span class="badge" :style="{ background: estadoColor[modalDetalle.estado]?.bg, color: estadoColor[modalDetalle.estado]?.text }">
                {{ estadoColor[modalDetalle.estado]?.label || modalDetalle.estado }}
              </span>
              <span class="badge" :style="{ background: prioridadColor[modalDetalle.prioridad]?.bg, color: prioridadColor[modalDetalle.prioridad]?.text }">
                Prioridad {{ modalDetalle.prioridad_display }}
              </span>
              <span class="badge tipo-badge">{{ modalDetalle.tipo_display }}</span>
            </div>
            <div class="detalle-grid">
              <div class="detalle-item">
                <span class="detalle-lbl">Conductor</span>
                <span>{{ modalDetalle.conductor_nombre || '—' }}</span>
              </div>
              <div class="detalle-item">
                <span class="detalle-lbl">Vehículo</span>
                <span>{{ modalDetalle.vehiculo_patente || '—' }}</span>
              </div>
              <div class="detalle-item">
                <span class="detalle-lbl">Fecha</span>
                <span>{{ fmtFecha(modalDetalle.created_at) }}</span>
              </div>
              <div class="detalle-item" v-if="modalDetalle.respondido_por_nombre">
                <span class="detalle-lbl">Respondido por</span>
                <span>{{ modalDetalle.respondido_por_nombre }} · {{ fmtFecha(modalDetalle.respondido_at) }}</span>
              </div>
            </div>
            <div class="detalle-seccion">
              <span class="detalle-lbl">Descripción</span>
              <p class="detalle-texto">{{ modalDetalle.descripcion || '—' }}</p>
            </div>
            <div v-if="modalDetalle.respuesta" class="detalle-seccion">
              <span class="detalle-lbl">Respuesta del equipo</span>
              <p class="detalle-texto">{{ modalDetalle.respuesta }}</p>
            </div>
            <div v-if="modalDetalle.foto_url" class="detalle-seccion">
              <span class="detalle-lbl">Foto adjunta</span>
              <a :href="modalDetalle.foto_url" target="_blank" rel="noopener">
                <img :src="modalDetalle.foto_url" class="detalle-foto" alt="Foto de la solicitud"/>
              </a>
            </div>
            <div v-if="errorAccion" class="error-inline">{{ errorAccion }}</div>
          </div>
          <div v-if="modalDetalle.estado === 'pendiente' || modalDetalle.estado === 'en_revision'" class="modal-footer">
            <button v-if="modalDetalle.estado === 'pendiente'" class="btn-secondary" @click="marcarEnRevision(modalDetalle)" :disabled="guardando">
              📋 Marcar en revisión
            </button>
            <button class="btn-ok-full" @click="aprobar(modalDetalle)" :disabled="guardando">✓ Aprobar</button>
            <button class="btn-nok-full" @click="abrirModalRechazar(modalDetalle)" :disabled="guardando">✕ Rechazar</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Modal Rechazo ────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="modalRechazar" class="overlay" @click.self="modalRechazar = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h2>Rechazar solicitud</h2>
            <button class="modal-close" @click="modalRechazar = null">✕</button>
          </div>
          <div class="modal-body">
            <p class="rechazo-info">Vas a rechazar: <strong>{{ modalRechazar.titulo }}</strong></p>
            <label class="form-label">Motivo del rechazo <span class="required">*</span></label>
            <textarea
              v-model="motivoRechazo"
              class="form-textarea"
              rows="4"
              placeholder="Explica el motivo del rechazo (mínimo 10 caracteres)…"
              :class="{ 'input-error': errorRechazo }"
            />
            <AvisoModeracion :aviso="avisoMod" :sugerencia="sugerenciaMod" />
            <p v-if="errorRechazo" class="error-field">{{ errorRechazo }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="modalRechazar = null">Cancelar</button>
            <button class="btn-nok-full" @click="confirmarRechazo" :disabled="guardando">
              {{ guardando ? 'Guardando…' : '✕ Confirmar rechazo' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Toasts ───────────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div class="toast-stack">
        <div v-for="t in toasts" :key="t.id" :class="['toast', `toast-${t.tipo}`]">{{ t.msg }}</div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.sa-page { padding: 1.75rem 2rem; display: flex; flex-direction: column; gap: 1.25rem; font-family: 'Inter', system-ui, sans-serif; }

/* Header */
.sa-header  { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.sa-title   { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0; }
.sa-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0.25rem 0 0; }

.btn-refresh {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #E5E7EB;
  background: #fff; color: #4F46E5; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s; font-family: inherit; white-space: nowrap;
}
.btn-refresh:hover:not(:disabled) { background: #EEF2FF; border-color: #A5B4FC; }
.btn-refresh:disabled { opacity: 0.4; cursor: not-allowed; }
.icon-refresh { width: 16px; height: 16px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Selector de empresa ── */
.sa-empresa-selector-wrap {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
}
.sa-empresa-label {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.8125rem; font-weight: 600; color: #374151;
  white-space: nowrap;
}
.sa-empresa-selector { position: relative; flex: 1; max-width: 420px; }

.sa-empresa-btn {
  width: 100%; display: flex; align-items: center; gap: 0.625rem;
  padding: 0.5625rem 0.875rem; border-radius: 9px;
  border: 1.5px solid #E5E7EB; background: #F9FAFB;
  font-size: 0.875rem; cursor: pointer; font-family: inherit;
  text-align: left; transition: border-color 0.15s, background 0.15s;
}
.sa-empresa-btn:hover { border-color: #A5B4FC; background: #fff; }
.sa-empresa-btn--active { border-color: #6366F1; background: #fff; }

.sa-empresa-nombre     { flex: 1; font-weight: 600; color: #1E1B4B; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sa-empresa-placeholder { flex: 1; color: #9CA3AF; }
.sa-empresa-clear {
  flex-shrink: 0; width: 18px; height: 18px; border-radius: 50%;
  background: #E5E7EB; color: #6B7280; font-size: 0.625rem;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: background 0.15s;
  border: none; padding: 0; font-family: inherit;
}
.sa-empresa-clear:hover { background: #FECACA; color: #DC2626; }

/* Dropdown */
.sa-dropdown {
  position: absolute; top: calc(100% + 6px); left: 0; right: 0;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  z-index: 500; overflow: hidden;
}
.sa-dropdown-search {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.625rem 0.75rem; border-bottom: 1px solid #F3F4F6;
}
.sa-dropdown-input {
  flex: 1; border: none; outline: none; font-size: 0.875rem;
  font-family: inherit; color: #374151; background: transparent;
}
.sa-dropdown-list { max-height: 280px; overflow-y: auto; }

.sa-dropdown-loading,
.sa-dropdown-empty {
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  padding: 1.25rem; font-size: 0.875rem; color: #9CA3AF;
}
.spinner-sm {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid #E5E7EB; border-top-color: #6366F1;
  animation: spin 0.7s linear infinite;
}
.sa-dropdown-item {
  width: 100%; display: flex; align-items: center; gap: 0.75rem;
  padding: 0.625rem 0.875rem; border: none; background: transparent;
  font-family: inherit; cursor: pointer; text-align: left;
  transition: background 0.1s;
}
.sa-dropdown-item:hover { background: #F9FAFB; }
.sa-dropdown-item--selected { background: #EEF2FF; }
.sa-empresa-avatar {
  width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.8125rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.sa-dropdown-item-info  { flex: 1; display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.sa-dropdown-item-nombre { font-size: 0.875rem; font-weight: 600; color: #1F2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sa-dropdown-item-rut    { font-size: 0.75rem; color: #9CA3AF; }

/* ── Empty estado sin empresa ── */
.sa-empty-empresa {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 1rem; padding: 4rem 2rem; background: #fff; border: 1px solid #E5E7EB;
  border-radius: 16px; text-align: center;
}
.sa-empty-icon {
  width: 72px; height: 72px; border-radius: 20px;
  background: #EEF2FF; display: flex; align-items: center; justify-content: center;
}
.sa-empty-icon svg { width: 36px; height: 36px; color: #6366F1; }
.sa-empty-empresa h3 { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0; }
.sa-empty-empresa p  { font-size: 0.875rem; color: #9CA3AF; margin: 0; max-width: 320px; }

/* ── KPIs ── */
.sc-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
@media (max-width: 900px) { .sc-kpis { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
  padding: 1rem 1.25rem; border-radius: 12px; border: 1px solid transparent;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.kpi-value { font-size: 2rem; font-weight: 800; line-height: 1.1; }
.kpi-label { font-size: 0.8125rem; font-weight: 500; opacity: 0.75; }
.kpi-warn    { background: #FEF3C7; border-color: #FDE68A; color: #92400E; }
.kpi-info    { background: #DBEAFE; border-color: #BFDBFE; color: #1E40AF; }
.kpi-ok      { background: #D1FAE5; border-color: #A7F3D0; color: #065F46; }
.kpi-neutral { background: #F3F4F6; border-color: #E5E7EB; color: #374151; }

/* Filtros */
.sc-filters { display: flex; flex-wrap: wrap; gap: 0.625rem; }
.filter-input {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; color: #374151; background: #fff;
  font-family: inherit; outline: none; transition: border-color 0.15s;
}
.filter-input:focus { border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
.filter-search { flex: 1; min-width: 180px; }

/* Error */
.sc-error { padding: 0.75rem 1rem; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; color: #991B1B; font-size: 0.875rem; }

/* Tabla */
.sc-table-wrap { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.sc-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.sc-table th {
  background: #F9FAFB; padding: 0.75rem 1rem; text-align: left;
  font-size: 0.75rem; font-weight: 600; color: #6B7280;
  text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #E5E7EB;
}
.sc-table td { padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; vertical-align: middle; color: #374151; }
.sc-table tr:last-child td { border-bottom: none; }
.sc-table tr:hover td { background: #F9FAFB; }
.row-pendiente td:first-child { border-left: 3px solid #F59E0B; }

.conductor-cell { display: flex; align-items: center; gap: 0.625rem; }
.conductor-avatar {
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.75rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.badge {
  display: inline-flex; align-items: center; padding: 0.2rem 0.6rem;
  border-radius: 9999px; font-size: 0.75rem; font-weight: 600; white-space: nowrap;
}
.tipo-badge { background: #EEF2FF; color: #4338CA; }
.td-titulo   { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.badge-checklist { display: inline-flex; align-items: center; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; font-weight: 700; background: #FEF3C7; color: #92400E; margin-left: 0.35rem; vertical-align: middle; }
.td-vehiculo { font-family: monospace; font-size: 0.8125rem; }
.td-fecha    { white-space: nowrap; font-size: 0.8125rem; color: #6B7280; }

.action-btns { display: flex; gap: 0.375rem; }
.btn-action {
  width: 30px; height: 30px; border-radius: 6px; border: 1px solid #E5E7EB;
  background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; transition: all 0.15s;
}
.btn-action svg { width: 16px; height: 16px; }
.btn-ver:hover  { background: #EEF2FF; border-color: #A5B4FC; color: #4F46E5; }
.btn-ok:hover   { background: #D1FAE5; border-color: #6EE7B7; }
.btn-nok:hover  { background: #FEE2E2; border-color: #FCA5A5; }

/* Skeleton */
.skeleton-row { display: flex; gap: 1rem; padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; }
.skel { height: 16px; border-radius: 6px; background: linear-gradient(90deg,#F3F4F6 25%,#E5E7EB 50%,#F3F4F6 75%); background-size: 200% 100%; animation: shimmer 1.2s infinite; }
.skel-wide { flex: 3; } .skel-mid { flex: 2; } .skel-short { flex: 1; }
@keyframes shimmer { to { background-position: -200% 0; } }

.sc-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 3rem 1rem; color: #9CA3AF; }

/* Paginación */
.sc-pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; }
.sc-pagination button { padding: 0.45rem 0.875rem; border: 1px solid #E5E7EB; border-radius: 8px; background: #fff; cursor: pointer; font-size: 0.875rem; color: #374151; }
.sc-pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.sc-pagination span { font-size: 0.875rem; color: #6B7280; }
.sc-total { text-align: center; font-size: 0.875rem; color: #6B7280; margin: 0; }

/* ── Modales ── */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 300; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.modal { background: #fff; border-radius: 16px; width: 100%; max-width: 680px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.25); }
.modal-sm { max-width: 460px; }
.modal-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #E5E7EB; gap: 1rem; }
.modal-header h2 { font-size: 1.0625rem; font-weight: 700; color: #1E1B4B; margin: 0; }
.modal-close { background: none; border: none; font-size: 1.125rem; cursor: pointer; color: #9CA3AF; line-height: 1; padding: 0.1rem; }
.modal-close:hover { color: #374151; }
.modal-body { flex: 1; overflow-y: auto; padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.detalle-badges  { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.detalle-grid    { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.detalle-item    { display: flex; flex-direction: column; gap: 0.25rem; }
.detalle-lbl     { font-size: 0.75rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.04em; }
.detalle-seccion { display: flex; flex-direction: column; gap: 0.5rem; }
.detalle-texto   { font-size: 0.875rem; color: #374151; line-height: 1.6; margin: 0; white-space: pre-wrap; }
.detalle-foto    { max-width: 100%; max-height: 300px; object-fit: contain; border-radius: 8px; border: 1px solid #E5E7EB; cursor: zoom-in; }
.error-inline { padding: 0.5rem 0.75rem; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; color: #991B1B; font-size: 0.8125rem; }
.modal-footer { padding: 1rem 1.5rem; border-top: 1px solid #E5E7EB; display: flex; gap: 0.625rem; justify-content: flex-end; flex-wrap: wrap; }
.btn-secondary { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #E5E7EB; background: #fff; color: #374151; font-size: 0.875rem; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s; }
.btn-secondary:hover { background: #F3F4F6; }
.btn-ok-full  { padding: 0.5rem 1rem; border-radius: 8px; border: none; background: #059669; color: #fff; font-size: 0.875rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-ok-full:hover { background: #047857; }
.btn-ok-full:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-nok-full { padding: 0.5rem 1rem; border-radius: 8px; border: none; background: #DC2626; color: #fff; font-size: 0.875rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-nok-full:hover { background: #B91C1C; }
.btn-nok-full:disabled { opacity: 0.5; cursor: not-allowed; }
.rechazo-info { font-size: 0.875rem; color: #374151; margin: 0; }
.form-label   { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.required     { color: #DC2626; }
.form-textarea { width: 100%; padding: 0.625rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; font-family: inherit; resize: vertical; outline: none; transition: border-color 0.15s; }
.form-textarea:focus { border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
.input-error  { border-color: #F87171 !important; }
.error-field  { font-size: 0.8125rem; color: #DC2626; margin: 0; }

/* Toasts */
.toast-stack { position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999; display: flex; flex-direction: column; gap: 0.5rem; }
.toast { padding: 0.75rem 1.125rem; border-radius: 10px; font-size: 0.875rem; font-weight: 500; max-width: 360px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); animation: slideIn 0.2s ease; }
.toast-ok   { background: #059669; color: #fff; }
.toast-warn { background: #D97706; color: #fff; }
.toast-info { background: #4F46E5; color: #fff; }
@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-header { flex-direction: column; gap: 0.625rem; }
  .page-title { font-size: 1.25rem; }
  .kpi-grid, .stats-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 0.625rem; }
  .filtros { flex-direction: column; gap: 0.5rem; }
  .filtros select, .filtros input { width: 100%; }
  .sc-table-wrap table, .tabla, .table { min-width: unset; width: 100%; }
  .toast-stack { right: 0.75rem; left: 0.75rem; bottom: 1rem; }
  .toast { max-width: 100%; }
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
