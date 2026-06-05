<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()
const route  = useRoute()

// ── Estado principal ────────────────────────────────────────────────────────
const solicitudes   = ref([])
const resumen       = ref({ pendientes: 0, en_revision: 0, aprobadas_hoy: 0, total_mes: 0 })
const cargando      = ref(false)
const error         = ref('')
const total         = ref(0)
const page          = ref(1)
const pages         = ref(1)
const pageSize      = 20

// ── Filtros ─────────────────────────────────────────────────────────────────
const filtroEstado     = ref('')
const filtroTipo       = ref('')
const filtroBuscar     = ref('')
const filtroFechaDesde = ref('')
const filtroFechaHasta = ref('')

// ── Modales ──────────────────────────────────────────────────────────────────
const modalDetalle    = ref(null)   // solicitud seleccionada
const modalRechazar   = ref(null)   // solicitud a rechazar
const modalProgramar  = ref(null)   // solicitud mantencion a programar
const motivoRechazo   = ref('')
const errorRechazo    = ref('')
const guardando       = ref(false)
const errorAccion     = ref('')

const programar = ref({ fecha: '', taller: '', presupuesto: '', suspender: false })

// ── Toast ────────────────────────────────────────────────────────────────────
const toasts = ref([])
function toast(msg, tipo = 'ok') {
  const id = Date.now()
  toasts.value.push({ id, msg, tipo })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3500)
}

// ── Helpers de UI ─────────────────────────────────────────────────────────
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

// ── Carga de datos ───────────────────────────────────────────────────────────
async function cargar(resetPage = false) {
  if (resetPage) page.value = 1
  cargando.value = true
  error.value    = ''
  try {
    const params = new URLSearchParams({ page: page.value, page_size: pageSize })
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
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// ── WebSocket para badge en tiempo real ──────────────────────────────────────
let ws = null
let wsPingInterval = null

function conectarWS() {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  const empresaId = usuario.empresa_id
  if (!empresaId) return

  const token = localStorage.getItem('access_token')
  if (!token) return

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const url   = `${proto}://${location.host}/ws/solicitudes/${empresaId}/?token=${token}`
  ws = new WebSocket(url)

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.tipo === 'nueva_solicitud') {
        resumen.value.pendientes = (resumen.value.pendientes || 0) + 1
        toast(`Nueva solicitud de ${msg.solicitud?.conductor || 'un conductor'}: "${msg.solicitud?.titulo}"`, 'info')
        cargar()
      }
    } catch {}
  }

  ws.onclose = () => {
    clearInterval(wsPingInterval)
    // Reconectar tras 5 s si no fue cierre intencional
    if (ws._manuallyClosed) return
    setTimeout(conectarWS, 5000)
  }

  wsPingInterval = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
  }, 25000)
}

function desconectarWS() {
  clearInterval(wsPingInterval)
  if (ws) { ws._manuallyClosed = true; ws.close() }
}

// ── Polling de conteo (fallback si WS no disponible) ─────────────────────────
let pollingConteo = null
async function refrescarConteo() {
  try {
    const res  = await apiFetch('/api/empresa/solicitudes/conteo/')
    if (!res.ok) return
    const data = await res.json()
    resumen.value.pendientes = data.pendientes ?? resumen.value.pendientes
  } catch {}
}

// ── Acciones sobre solicitudes ────────────────────────────────────────────────
async function marcarEnRevision(sol) {
  guardando.value = true
  errorAccion.value = ''
  try {
    const res  = await apiFetch(`/api/empresa/solicitudes/${sol.id}/`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({})
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

// Aprobar: si es mantencion abre modal de programación; si no, aprueba directo
function aprobar(sol) {
  if (sol.tipo === 'mantencion') {
    // Default es_correctivo=true: las solicitudes de conductor son fallas en terreno.
    programar.value      = { fecha: '', taller: '', presupuesto: '', suspender: false,
                             es_correctivo: true, monto: '', categoria_correctiva: '' }
    errorAccion.value    = ''
    modalProgramar.value = sol
    modalDetalle.value   = null   // cerrar modal detalle si estaba abierto
    return
  }
  _ejecutarAprobacion(sol, {})
}

async function confirmarProgramacion() {
  errorAccion.value = ''
  const p = programar.value

  if (p.es_correctivo) {
    // Correctivo → se registra el gasto directo: el monto es obligatorio.
    const montoNum = Number(String(p.monto).replace(/[.\s]/g, '').replace(',', '.'))
    if (!Number.isFinite(montoNum) || montoNum <= 0) {
      errorAccion.value = 'Ingresa el monto del gasto correctivo (mayor a 0).'
      return
    }
    const sol = modalProgramar.value
    await _ejecutarAprobacion(sol, {
      es_correctivo:        true,
      monto:                montoNum,
      categoria_correctiva: p.categoria_correctiva || undefined,
    })
    if (!errorAccion.value) modalProgramar.value = null
    return
  }

  // Programada → crea la mantención.
  const mantencionId = await _ejecutarAprobacion(modalProgramar.value, {
    es_correctivo:      false,
    fecha_programada:   p.fecha     || undefined,
    taller:             p.taller    || undefined,
    presupuesto:        p.presupuesto ? Number(p.presupuesto) : undefined,
    suspender_vehiculo: p.suspender,
  })
  modalProgramar.value = null

  // Redirigir al formulario de mantención creada automáticamente
  if (mantencionId) {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
    const base    = usuario.rol === 'SUPERADMIN' ? '' : '/empresa'
    router.push(`${base}/mantenciones/${mantencionId}/editar`)
  }
}

/**
 * Ejecuta la aprobación de una solicitud.
 * @returns {number|null} mantencion_id si se creó una mantención, null si no.
 */
async function _ejecutarAprobacion(sol, extra = {}) {
  guardando.value   = true
  errorAccion.value = ''
  try {
    const res  = await apiFetch(`/api/empresa/solicitudes/${sol.id}/aprobar/`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuesta: '', ...extra }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error')
    if (modalDetalle.value?.id === sol.id) modalDetalle.value = { ...data.solicitud }
    toast('Solicitud aprobada ✓', 'ok')
    cerrarModalDetalle()
    await cargar()
    return data.mantencion_id || null
  } catch (e) {
    errorAccion.value = e.message
    return null
  } finally {
    guardando.value = false
  }
}

function abrirModalRechazar(sol) {
  modalRechazar.value = sol
  motivoRechazo.value = ''
  errorRechazo.value  = ''
}

async function confirmarRechazo() {
  if (motivoRechazo.value.trim().length < 10) {
    errorRechazo.value = 'El motivo debe tener al menos 10 caracteres.'
    return
  }
  guardando.value = true
  errorRechazo.value = ''
  try {
    const res  = await apiFetch(`/api/empresa/solicitudes/${modalRechazar.value.id}/rechazar/`, {
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
  const id = typeof sol === 'object' ? sol.id : sol
  try {
    const res  = await apiFetch(`/api/empresa/solicitudes/${id}/`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error')
    modalDetalle.value = data
  } catch {
    if (typeof sol === 'object') modalDetalle.value = { ...sol }
  }
}

function cerrarModalDetalle() {
  modalDetalle.value = null
  errorAccion.value  = ''
}

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  cargar()
  conectarWS()
  pollingConteo = setInterval(refrescarConteo, 30_000)
  // Abrir el detalle si la URL apunta a una solicitud (desde notificación/email).
  // Soporta ?sol=ID (formato nuevo) y /solicitudes/:id (notificaciones antiguas).
  const solId = route.query.sol || route.params.id
  if (solId) verDetalle(Number(solId))
})

onUnmounted(() => {
  desconectarWS()
  clearInterval(pollingConteo)
})

// Abrir detalle si cambia la solicitud apuntada estando ya en la página.
watch(() => route.query.sol || route.params.id, (id) => { if (id) verDetalle(Number(id)) })

// Watch filtros con debounce
let debounce = null
watch([filtroEstado, filtroTipo, filtroFechaDesde, filtroFechaHasta], () => cargar(true))
watch(filtroBuscar, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => cargar(true), 400)
})
</script>

<template>
  <div class="sc-page">
    <!-- Título -->
    <div class="sc-header">
      <div>
        <h1 class="sc-title">Solicitudes de Conductores</h1>
        <p class="sc-subtitle">Gestiona las solicitudes enviadas desde la app móvil</p>
      </div>
      <button class="btn-refresh" @click="cargar()" :disabled="cargando" title="Actualizar">
        <svg :class="['icon-refresh', { spin: cargando }]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Actualizar
      </button>
    </div>

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
      <!-- Skeleton -->
      <template v-if="cargando && solicitudes.length === 0">
        <div v-for="i in 5" :key="i" class="skeleton-row">
          <div class="skel skel-wide"/>
          <div class="skel skel-mid"/>
          <div class="skel skel-short"/>
          <div class="skel skel-short"/>
          <div class="skel skel-mid"/>
        </div>
      </template>

      <!-- Empty -->
      <div v-else-if="!cargando && solicitudes.length === 0" class="sc-empty">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:48px;height:48px;color:#D1D5DB">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
        </svg>
        <p>No hay solicitudes con los filtros seleccionados</p>
      </div>

      <!-- Tabla de datos -->
      <table v-else class="sc-table">
        <thead>
          <tr>
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
            <td>
              <div class="conductor-cell">
                <div class="conductor-avatar">{{ sol.conductor_iniciales || '?' }}</div>
                <span>{{ sol.conductor_nombre || '—' }}</span>
              </div>
            </td>
            <td>
              <span class="tipo-badge">
                {{ tipoIcon[sol.tipo] }} {{ sol.tipo_display }}
              </span>
            </td>
            <td class="td-titulo">{{ sol.titulo }}</td>
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

    <!-- ── Modal Detalle ──────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="modalDetalle" class="overlay" @click.self="cerrarModalDetalle">
        <div class="modal modal-detalle">
          <div class="modal-header">
            <h2>
              {{ tipoIcon[modalDetalle.tipo] }}
              {{ modalDetalle.titulo }}
            </h2>
            <button class="modal-close" @click="cerrarModalDetalle">✕</button>
          </div>

          <div class="modal-body">
            <!-- Badges de estado/prioridad -->
            <div class="detalle-badges">
              <span class="badge"
                :style="{ background: estadoColor[modalDetalle.estado]?.bg, color: estadoColor[modalDetalle.estado]?.text }">
                {{ estadoColor[modalDetalle.estado]?.label || modalDetalle.estado }}
              </span>
              <span class="badge"
                :style="{ background: prioridadColor[modalDetalle.prioridad]?.bg, color: prioridadColor[modalDetalle.prioridad]?.text }">
                Prioridad {{ modalDetalle.prioridad_display }}
              </span>
              <span class="badge tipo-badge">{{ modalDetalle.tipo_display }}</span>
            </div>

            <!-- Grid de info -->
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
              <template v-if="modalDetalle.tipo === 'combustible' && modalDetalle.extra">
                <div class="detalle-item">
                  <span class="detalle-lbl">Monto</span>
                  <span>{{ modalDetalle.extra.monto ? '$' + modalDetalle.extra.monto.toLocaleString('es-CL') : '—' }}</span>
                </div>
                <div class="detalle-item">
                  <span class="detalle-lbl">Litros</span>
                  <span>{{ modalDetalle.extra.litros || '—' }} L</span>
                </div>
              </template>
              <template v-if="modalDetalle.tipo === 'incidencia' && modalDetalle.extra">
                <div class="detalle-item" v-if="modalDetalle.extra.subtipo">
                  <span class="detalle-lbl">Tipo de Incidencia</span>
                  <span class="capitalize">{{ modalDetalle.extra.subtipo.replace('_', ' ') }}</span>
                </div>
                <div class="detalle-item" v-if="modalDetalle.extra.subtipo === 'multa'">
                  <span class="detalle-lbl">Monto Multa</span>
                  <span>{{ modalDetalle.extra.monto ? '$' + modalDetalle.extra.monto.toLocaleString('es-CL') : '—' }}</span>
                </div>
              </template>
            </div>

            <!-- Checklist pre-viaje: detalle de ítems -->
            <div v-if="modalDetalle.checklist" class="detalle-seccion">
              <span class="detalle-lbl">
                Checklist pre-viaje
                <span :class="['chk-resumen', modalDetalle.checklist.tiene_fallas ? 'chk-fallas' : 'chk-ok']">
                  {{ modalDetalle.checklist.tiene_fallas ? 'Con fallas' : 'Todo en orden' }}
                </span>
              </span>
              <div class="chk-lista">
                <div v-for="it in modalDetalle.checklist.items" :key="it.id" class="chk-item">
                  <span :class="['chk-icono', 'chk-' + it.resultado]">
                    {{ it.resultado === 'ok' ? '✓' : it.resultado === 'falla' ? '✕' : '—' }}
                  </span>
                  <div class="chk-texto">
                    <span class="chk-nombre">{{ it.nombre }}</span>
                    <span v-if="it.observacion" class="chk-obs">{{ it.observacion }}</span>
                  </div>
                </div>
              </div>
              <p v-if="modalDetalle.checklist.firma" class="chk-firma">✍ Firmado por el conductor</p>
            </div>

            <!-- Descripción (no se repite para checklists) -->
            <div v-if="!modalDetalle.checklist" class="detalle-seccion">
              <span class="detalle-lbl">Descripción</span>
              <p class="detalle-texto">{{ modalDetalle.descripcion || '—' }}</p>
            </div>

            <!-- Respuesta (si existe) -->
            <div v-if="modalDetalle.respuesta" class="detalle-seccion">
              <span class="detalle-lbl">Respuesta del equipo</span>
              <p class="detalle-texto">{{ modalDetalle.respuesta }}</p>
            </div>

            <!-- Foto -->
            <div v-if="modalDetalle.foto_url" class="detalle-seccion">
              <span class="detalle-lbl">Foto adjunta</span>
              <a :href="modalDetalle.foto_url" target="_blank" rel="noopener">
                <img :src="modalDetalle.foto_url" class="detalle-foto" alt="Foto de la solicitud" />
              </a>
            </div>

            <!-- Error de acción -->
            <div v-if="errorAccion" class="error-inline">{{ errorAccion }}</div>
          </div>

          <!-- Footer con acciones -->
          <div v-if="modalDetalle.estado === 'pendiente' || modalDetalle.estado === 'en_revision'" class="modal-footer">
            <button
              v-if="modalDetalle.estado === 'pendiente'"
              class="btn-secondary"
              @click="marcarEnRevision(modalDetalle)"
              :disabled="guardando"
            >
              📋 Marcar en revisión
            </button>
            <button class="btn-ok-full" @click="aprobar(modalDetalle)" :disabled="guardando">
              ✓ Aprobar solicitud
            </button>
            <button class="btn-nok-full" @click="abrirModalRechazar(modalDetalle)" :disabled="guardando">
              ✕ Rechazar
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Modal Rechazo ──────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="modalRechazar" class="overlay" @click.self="modalRechazar = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h2>Rechazar solicitud</h2>
            <button class="modal-close" @click="modalRechazar = null">✕</button>
          </div>
          <div class="modal-body">
            <p class="rechazo-info">
              Vas a rechazar: <strong>{{ modalRechazar.titulo }}</strong>
            </p>
            <label class="form-label">Motivo del rechazo <span class="required">*</span></label>
            <textarea
              v-model="motivoRechazo"
              class="form-textarea"
              rows="4"
              placeholder="Explica el motivo del rechazo (mínimo 10 caracteres)…"
              :class="{ 'input-error': errorRechazo }"
            />
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

    <!-- ── Modal Programar Mantención ──────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="modalProgramar" class="overlay" @click.self="modalProgramar = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h2>🔧 Aprobar mantención</h2>
            <button class="modal-close" @click="modalProgramar = null">✕</button>
          </div>
          <div class="modal-body">
            <p class="rechazo-info">
              <strong>{{ modalProgramar.titulo }}</strong>
              <span v-if="modalProgramar.conductor_nombre" style="color:#6B7280">
                — {{ modalProgramar.conductor_nombre }}
              </span>
            </p>

            <!-- Clasificación del costo -->
            <div class="form-group">
              <label class="form-label">Tipo de mantención</label>
              <div class="seg-toggle">
                <button type="button"
                  :class="['seg-opt', { 'seg-active': programar.es_correctivo }]"
                  @click="programar.es_correctivo = true">
                  Correctivo (falla)
                </button>
                <button type="button"
                  :class="['seg-opt', { 'seg-active': !programar.es_correctivo }]"
                  @click="programar.es_correctivo = false">
                  Programada
                </button>
              </div>
              <p class="seg-hint">
                {{ programar.es_correctivo
                  ? 'La falla ya ocurrió: se registra el gasto directo en Correctivos (no se planifica).'
                  : 'Trabajo a ejecutar: se crea una mantención para programar.' }}
              </p>
            </div>

            <!-- CORRECTIVO → monto + categoría del gasto -->
            <template v-if="programar.es_correctivo">
              <div class="form-group">
                <label class="form-label">Monto del gasto ($) <span class="req">*</span></label>
                <input v-model="programar.monto" type="number" min="1" class="form-input" placeholder="0" />
              </div>
              <div class="form-group">
                <label class="form-label">Categoría correctiva <span class="opt-label">(opcional)</span></label>
                <select v-model="programar.categoria_correctiva" class="form-input">
                  <option value="">— Selecciona —</option>
                  <option value="falla_mecanica">Falla mecánica urgente</option>
                  <option value="repuesto_urgente">Repuesto no planificado</option>
                  <option value="accidente">Daño por accidente</option>
                  <option value="electrico">Falla eléctrica</option>
                  <option value="neumatico">Neumático de emergencia</option>
                  <option value="otro_correctivo">Otro correctivo</option>
                </select>
              </div>
            </template>

            <!-- PROGRAMADA → datos de la mantención a ejecutar -->
            <template v-else>
              <div class="form-group">
                <label class="form-label">
                  Fecha programada
                  <span class="opt-label">(opcional)</span>
                </label>
                <input v-model="programar.fecha" type="date" class="form-input" />
              </div>

              <div class="form-group">
                <label class="form-label">
                  Taller / Mecánico
                  <span class="opt-label">(opcional)</span>
                </label>
                <input
                  v-model="programar.taller"
                  type="text"
                  class="form-input"
                  placeholder="Ej: Taller Mecánico Rodríguez"
                />
              </div>

              <div class="form-group">
                <label class="form-label">
                  Presupuesto estimado
                  <span class="opt-label">(opcional)</span>
                </label>
                <input
                  v-model="programar.presupuesto"
                  type="number"
                  min="0"
                  step="1"
                  class="form-input"
                  placeholder="0"
                />
              </div>

              <label class="check-label">
                <input v-model="programar.suspender" type="checkbox" class="check-input" />
                <span>Suspender vehículo (marcarlo como en mantención)</span>
              </label>
            </template>

            <div v-if="errorAccion" class="error-inline">{{ errorAccion }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="modalProgramar = null" :disabled="guardando">
              Cancelar
            </button>
            <button class="btn-ok-full" @click="confirmarProgramacion" :disabled="guardando">
              {{ guardando ? 'Aprobando…' : '✓ Confirmar aprobación' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Toasts ─────────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div class="toast-stack">
        <div v-for="t in toasts" :key="t.id" :class="['toast', `toast-${t.tipo}`]">
          {{ t.msg }}
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.sc-page { padding: 1.75rem 2rem; display: flex; flex-direction: column; gap: 1.25rem; font-family: 'Inter', system-ui, sans-serif; }

/* Header */
.sc-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.sc-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0; }
.sc-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0.25rem 0 0; }

.btn-refresh {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #E5E7EB;
  background: #fff; color: #4F46E5; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s; font-family: inherit; white-space: nowrap;
}
.btn-refresh:hover { background: #EEF2FF; border-color: #A5B4FC; }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }
.icon-refresh { width: 16px; height: 16px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* KPIs */
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
  font-size: 0.75rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.04em;
  border-bottom: 1px solid #E5E7EB;
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

.td-titulo  { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-vehiculo { font-family: monospace; font-size: 0.8125rem; }
.td-fecha    { white-space: nowrap; font-size: 0.8125rem; color: #6B7280; }

/* Action btns */
.action-btns { display: flex; gap: 0.375rem; }
.btn-action {
  width: 30px; height: 30px; border-radius: 6px; border: 1px solid #E5E7EB;
  background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; transition: all 0.15s;
}
.btn-action svg { width: 16px; height: 16px; }
.btn-ver:hover  { background: #EEF2FF; border-color: #A5B4FC; color: #4F46E5; }
.btn-ok  { color: #065F46; }
.btn-ok:hover  { background: #D1FAE5; border-color: #6EE7B7; }
.btn-nok { color: #991B1B; }
.btn-nok:hover { background: #FEE2E2; border-color: #FCA5A5; }

/* Skeleton */
.skeleton-row { display: flex; gap: 1rem; padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; }
.skel { height: 16px; border-radius: 6px; background: linear-gradient(90deg,#F3F4F6 25%,#E5E7EB 50%,#F3F4F6 75%); background-size: 200% 100%; animation: shimmer 1.2s infinite; }
.skel-wide  { flex: 3; }
.skel-mid   { flex: 2; }
.skel-short { flex: 1; }
@keyframes shimmer { to { background-position: -200% 0; } }

/* Empty */
.sc-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 3rem 1rem; color: #9CA3AF; }

/* Paginación */
.sc-pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; }
.sc-pagination button { padding: 0.45rem 0.875rem; border: 1px solid #E5E7EB; border-radius: 8px; background: #fff; cursor: pointer; font-size: 0.875rem; color: #374151; }
.sc-pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.sc-pagination span { font-size: 0.875rem; color: #6B7280; }
.sc-total { text-align: center; font-size: 0.875rem; color: #6B7280; margin: 0; }

/* ── Modales ─────────────────────────────────────────────────────────────── */
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 300;
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.modal {
  background: #fff; border-radius: 16px; width: 100%; max-width: 680px;
  max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}
.modal-sm { max-width: 460px; }

.modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #E5E7EB; gap: 1rem;
}
.modal-header h2 { font-size: 1.0625rem; font-weight: 700; color: #1E1B4B; margin: 0; }
.modal-close { background: none; border: none; font-size: 1.125rem; cursor: pointer; color: #9CA3AF; line-height: 1; padding: 0.1rem; }
.modal-close:hover { color: #374151; }

.modal-body { flex: 1; overflow-y: auto; padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1rem; }

.detalle-badges { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.detalle-grid   { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.detalle-item   { display: flex; flex-direction: column; gap: 0.25rem; }
.detalle-lbl    { font-size: 0.75rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.04em; }
.detalle-seccion { display: flex; flex-direction: column; gap: 0.5rem; }
.detalle-texto  { font-size: 0.875rem; color: #374151; line-height: 1.6; margin: 0; white-space: pre-wrap; }
.detalle-foto   { max-width: 100%; max-height: 300px; object-fit: contain; border-radius: 8px; border: 1px solid #E5E7EB; cursor: zoom-in; }

.error-inline { padding: 0.5rem 0.75rem; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; color: #991B1B; font-size: 0.8125rem; }

.modal-footer { padding: 1rem 1.5rem; border-top: 1px solid #E5E7EB; display: flex; gap: 0.625rem; justify-content: flex-end; flex-wrap: wrap; }

.btn-secondary {
  padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #E5E7EB;
  background: #fff; color: #374151; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.btn-secondary:hover { background: #F3F4F6; }
.btn-ok-full {
  padding: 0.5rem 1rem; border-radius: 8px; border: none;
  background: #059669; color: #fff; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-ok-full:hover { background: #047857; }
.btn-ok-full:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-nok-full {
  padding: 0.5rem 1rem; border-radius: 8px; border: none;
  background: #DC2626; color: #fff; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-nok-full:hover { background: #B91C1C; }
.btn-nok-full:disabled { opacity: 0.5; cursor: not-allowed; }

/* Rechazo y formularios de modales */
.rechazo-info { font-size: 0.875rem; color: #374151; margin: 0; }
.form-label   { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.required     { color: #DC2626; }
.opt-label    { font-weight: 400; color: #9CA3AF; }
.form-group   { display: flex; flex-direction: column; gap: 0.375rem; }
.form-input {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit; outline: none; background: #fff;
  transition: border-color 0.15s; color: #374151; width: 100%;
}
.form-input:focus { border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
.check-label {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.875rem; color: #374151; cursor: pointer;
}
.check-input { width: 16px; height: 16px; accent-color: #4F46E5; cursor: pointer; }
.form-textarea {
  width: 100%; padding: 0.625rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit; resize: vertical; outline: none;
  transition: border-color 0.15s;
}
.form-textarea:focus { border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
.input-error  { border-color: #F87171 !important; }
.error-field  { font-size: 0.8125rem; color: #DC2626; margin: 0; }

/* Toasts */
.toast-stack  { position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999; display: flex; flex-direction: column; gap: 0.5rem; }
.toast {
  padding: 0.75rem 1.125rem; border-radius: 10px; font-size: 0.875rem; font-weight: 500;
  max-width: 360px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  animation: slideIn 0.2s ease;
}
.toast-ok   { background: #059669; color: #fff; }
.toast-warn { background: #D97706; color: #fff; }
.toast-info { background: #4F46E5; color: #fff; }
@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }

/* Toggle correctivo / programada */
.seg-toggle { display: flex; gap: 0.5rem; }
.seg-opt {
  flex: 1; padding: 0.55rem 0.5rem;
  border: 1.5px solid #E5E7EB; border-radius: 9px;
  background: #fff; color: #6B7280;
  font-size: 0.8125rem; font-weight: 600; cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.seg-opt:hover { border-color: #C7D2FE; }
.seg-active { border-color: #4F46E5; background: #EEF2FF; color: #4338CA; }
.seg-hint { font-size: 0.75rem; color: #9CA3AF; margin: 0.4rem 0 0; }

/* Checklist pre-viaje en el detalle */
.chk-resumen { margin-left: 0.5rem; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; }
.chk-ok     { background: #ECFDF5; color: #059669; }
.chk-fallas { background: #FEF2F2; color: #DC2626; }
.chk-lista  { margin-top: 0.6rem; display: flex; flex-direction: column; gap: 0.4rem; }
.chk-item   { display: flex; align-items: flex-start; gap: 0.6rem; }
.chk-icono  {
  flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.7rem; font-weight: 800;
}
.chk-item .chk-ok          { background: #ECFDF5; color: #059669; }
.chk-item .chk-falla       { background: #FEF2F2; color: #DC2626; }
.chk-item .chk-sin_revisar { background: #F3F4F6; color: #9CA3AF; }
.chk-texto  { display: flex; flex-direction: column; }
.chk-nombre { font-size: 0.8125rem; color: #374151; font-weight: 500; }
.chk-obs    { font-size: 0.75rem; color: #DC2626; }
.chk-firma  { font-size: 0.75rem; color: #6B7280; margin: 0.6rem 0 0; }
</style>
