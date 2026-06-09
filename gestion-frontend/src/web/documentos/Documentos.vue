<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { apiFetchEmpresa, getEmpresaActiva, setEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../utils/empresaActiva.js'
import { useToast } from '../../utils/useToast.js'
import { usePaginacion } from '../../composables/usePaginacion.js'
import PaginacionTabla from '../../components/PaginacionTabla.vue'

const toast = useToast()

// ── Empresa selector (SUPERADMIN)
const esSuperadmin     = JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN'
const empresaActiva    = ref(getEmpresaActiva())
// Modo "Todas las empresas": vista de solo lectura con columna de empresa.
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)
const empresas         = ref([])
const cargandoEmpresas = ref(false)
const mostrarDropdown  = ref(false)
const busqueda         = ref('')
const sinEmpresa       = computed(() => esSuperadmin && !empresaActiva.value)

const empresasFiltradas = computed(() => {
  if (!busqueda.value.trim()) return empresas.value
  const q = busqueda.value.toLowerCase()
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

async function cargarEmpresas() {
  if (!esSuperadmin) return
  cargandoEmpresas.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = conOpcionTodas(await res.json())
  } finally {
    cargandoEmpresas.value = false
  }
}

function seleccionarEmpresa(emp) {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  vehiculos.value       = []
  conductores.value     = []
  cargar()
  cargarAuxiliares()
}

// ── Estado global
const cargando   = ref(false)
const documentos = ref([])
const resumen    = ref(null)
const vehiculos  = ref([])
const conductores = ref([])

// ── Filtros
const filtroEntidad  = ref('')
const filtroEstado   = ref('')
const filtroTipo     = ref('')
const filtroBuscar   = ref('')
const filtroVehiculo = ref('')
const filtroCondutor = ref('')

// ── Modales
const modalSubir  = ref(false)
const modalDetalle = ref(null)   // doc seleccionado
const modalRenovar = ref(null)   // doc a renovar
const confirmEliminar = ref(null)

// ── Form de subida/edición
const editandoId        = ref(null)
const empresaDocForm    = ref('')   // empresa elegida en el form cuando esTodas
const guardando         = ref(false)
const form = ref({
  entidad: 'vehiculo',
  vehiculo_id: '',
  conductor_id: '',
  tipo: '',
  fecha_emision: '',
  fecha_vencimiento: '',
  archivo: null,
  notas: '',
})
const archivoPreview = ref(null)
const errForm = ref({})

// ── Form de renovación
const formRenovar = ref({ fecha_emision: '', fecha_vencimiento: '', notas: '', archivo: null })
const guardandoRenovar = ref(false)

// ── Constantes
const TIPOS_VEHICULO  = [
  { value: 'permiso_circulacion', label: 'Permiso de circulación' },
  { value: 'revision_tecnica',    label: 'Revisión técnica' },
  { value: 'seguro_soap',         label: 'Seguro SOAP' },
]
const TIPOS_CONDUCTOR = [
  { value: 'licencia',     label: 'Licencia de conducir' },
  { value: 'antecedentes', label: 'Antecedentes comerciales' },
]
const tiposDisponibles = computed(() =>
  form.value.entidad === 'vehiculo' ? TIPOS_VEHICULO : TIPOS_CONDUCTOR
)

const ESTADO = {
  vigente:          { bg: '#ECFDF5', text: '#059669', label: 'Vigente'     },
  por_vencer:       { bg: '#FFFBEB', text: '#D97706', label: 'Por vencer'  },
  vencido:          { bg: '#FEF2F2', text: '#DC2626', label: 'Vencido'     },
  sin_vencimiento:  { bg: '#F3F4F6', text: '#6B7280', label: 'Sin fecha'   },
}

// ── Formatters
function fechaCorta(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
function diasLabel(dias) {
  if (dias == null) return ''
  if (dias < 0)  return `Vencido hace ${Math.abs(dias)} día${Math.abs(dias) !== 1 ? 's' : ''}`
  if (dias === 0) return 'Vence hoy'
  return `Vence en ${dias} día${dias !== 1 ? 's' : ''}`
}

// ── Documentos filtrados
const docsFiltrados = computed(() => {
  let list = documentos.value
  if (filtroEntidad.value)  list = list.filter(d => d.entidad === filtroEntidad.value)
  if (filtroEstado.value)   list = list.filter(d => d.estado  === filtroEstado.value)
  if (filtroTipo.value)     list = list.filter(d => d.tipo    === filtroTipo.value)
  if (filtroVehiculo.value) list = list.filter(d => String(d.vehiculo_id) === filtroVehiculo.value)
  if (filtroCondutor.value) list = list.filter(d => String(d.conductor_id) === filtroCondutor.value)
  if (filtroBuscar.value) {
    const q = filtroBuscar.value.toLowerCase()
    list = list.filter(d =>
      d.tipo_display.toLowerCase().includes(q) ||
      (d.vehiculo_patente || '').toLowerCase().includes(q) ||
      (d.conductor_nombre || '').toLowerCase().includes(q) ||
      (d.nombre_archivo   || '').toLowerCase().includes(q)
    )
  }
  return list
})

const { pagina: paginaDocs, totalPaginas: totalPaginasDocs, total: totalDocs, paginado: docsPaginados, irA: irAPaginaDocs } = usePaginacion(docsFiltrados, 20)

// ── Carga
async function cargar() {
  if (sinEmpresa.value) { cargando.value = false; return }
  cargando.value = true
  try {
    const res = await apiFetchEmpresa('/api/empresa/documentos/')
    if (res.ok) {
      const data   = await res.json()
      documentos.value = data.documentos || []
      resumen.value    = data.resumen    || null
    } else {
      toast.error('Error al cargar documentos.')
    }
  } catch {
    toast.error('Error de conexión.')
  } finally {
    cargando.value = false
  }
}

async function cargarAuxiliares() {
  if (sinEmpresa.value) return
  const [vRes, cRes] = await Promise.all([
    apiFetchEmpresa('/api/empresa/vehiculos/'),
    apiFetchEmpresa('/api/empresa/conductores/'),
  ])
  if (vRes.ok) vehiculos.value   = await vRes.json()
  if (cRes.ok) conductores.value = await cRes.json()
}

// ── Subir / editar documento
function abrirNuevo() {
  editandoId.value   = null
  empresaDocForm.value = ''
  form.value = { entidad: 'vehiculo', vehiculo_id: '', conductor_id: '', tipo: '', fecha_emision: '', fecha_vencimiento: '', archivo: null, notas: '' }
  archivoPreview.value = null
  errForm.value = {}
  modalSubir.value = true
}

function abrirEditar(doc) {
  editandoId.value = doc.id
  form.value = {
    entidad:           doc.entidad,
    vehiculo_id:       doc.vehiculo_id  || '',
    conductor_id:      doc.conductor_id || '',
    tipo:              doc.tipo,
    fecha_emision:     doc.fecha_emision     || '',
    fecha_vencimiento: doc.fecha_vencimiento || '',
    archivo:           null,
    notas:             doc.notas || '',
  }
  archivoPreview.value = null
  errForm.value = {}
  modalDetalle.value = null
  modalSubir.value = true
}

function onArchivoChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
    toast.error('Solo se permiten archivos PDF o imágenes (JPG, PNG, etc.).')
    e.target.value = ''
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    toast.error('El archivo no debe superar 10 MB.')
    e.target.value = ''
    return
  }
  form.value.archivo = file
  if (file.type.startsWith('image/')) {
    archivoPreview.value = URL.createObjectURL(file)
  } else {
    archivoPreview.value = null
  }
}

watch(() => form.value.entidad, () => { form.value.tipo = '' })

function validarForm() {
  const err = {}
  if (esTodas.value && !editandoId.value && !empresaDocForm.value) err.empresaDoc = 'Selecciona una empresa.'
  if (!form.value.tipo) err.tipo = 'Selecciona un tipo.'
  if (form.value.entidad === 'vehiculo' && !form.value.vehiculo_id) err.vehiculo_id = 'Selecciona un vehículo.'
  if (form.value.entidad === 'conductor' && !form.value.conductor_id) err.conductor_id = 'Selecciona un conductor.'
  if (form.value.fecha_emision && form.value.fecha_vencimiento && form.value.fecha_emision >= form.value.fecha_vencimiento) {
    err.fecha_vencimiento = 'La fecha de vencimiento debe ser posterior a la de emisión.'
  }
  if (form.value.fecha_vencimiento && !form.value.fecha_emision) {
    // Fecha de vencimiento sin emisión es válida, no error
  }
  if (!editandoId.value && !form.value.archivo) {
    err.archivo = 'El archivo es obligatorio para nuevos documentos.'
  }
  const notas = form.value.notas
  if (notas && notas.trim() === '') {
    err.notas = 'Las notas no pueden contener solo espacios en blanco.'
  } else if (notas.length > 50) {
    err.notas = 'Las notas no pueden superar 50 caracteres.'
  }
  errForm.value = err
  return !Object.keys(err).length
}

async function guardarDocumento() {
  if (!validarForm()) return
  guardando.value = true
  try {
    const method = editandoId.value ? 'PUT' : 'POST'
    const url    = editandoId.value
      ? `/api/empresa/documentos/${editandoId.value}/`
      : '/api/empresa/documentos/'

    const empresaId = esTodas.value
      ? empresaDocForm.value
      : (esSuperadmin ? empresaActiva.value?.id : undefined)

    let body
    if (form.value.archivo) {
      const fd = new FormData()
      fd.append('entidad',           form.value.entidad)
      fd.append('tipo',              form.value.tipo)
      if (form.value.vehiculo_id)  fd.append('vehiculo_id',  form.value.vehiculo_id)
      if (form.value.conductor_id) fd.append('conductor_id', form.value.conductor_id)
      if (form.value.fecha_emision)     fd.append('fecha_emision',     form.value.fecha_emision)
      if (form.value.fecha_vencimiento) fd.append('fecha_vencimiento', form.value.fecha_vencimiento)
      fd.append('notas',   form.value.notas)
      fd.append('archivo', form.value.archivo)
      if (empresaId) fd.append('empresa_id', empresaId)
      body = fd
    } else {
      body = {
        entidad:           form.value.entidad,
        tipo:              form.value.tipo,
        vehiculo_id:       form.value.vehiculo_id  || undefined,
        conductor_id:      form.value.conductor_id || undefined,
        fecha_emision:     form.value.fecha_emision     || undefined,
        fecha_vencimiento: form.value.fecha_vencimiento || undefined,
        notas:             form.value.notas,
        ...(empresaId ? { empresa_id: empresaId } : {}),
      }
    }

    const res  = await apiFetch(url, { method, body })
    const data = await res.json()
    if (!res.ok) {
      toast.error(data.error || 'Error al guardar.')
      return
    }
    toast.success(editandoId.value ? 'Documento actualizado.' : 'Documento subido correctamente.')
    modalSubir.value = false
    await cargar()
  } catch {
    toast.error('Error de conexión.')
  } finally {
    guardando.value = false
  }
}

// ── Eliminar
async function eliminarDoc() {
  if (!confirmEliminar.value) return
  try {
    const res = await apiFetch(`/api/empresa/documentos/${confirmEliminar.value}/`, { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      toast.success('Documento eliminado.')
      confirmEliminar.value = null
      modalDetalle.value    = null
      await cargar()
    } else {
      const d = await res.json()
      toast.error(d.error || 'Error al eliminar.')
    }
  } catch {
    toast.error('Error de conexión.')
  }
}

// ── Descargar
async function descargar(docId) {
  const doc = documentos.value.find(d => d.id === docId)
  if (doc && !doc.tiene_archivo) {
    toast.error('Este documento no tiene archivo adjunto.')
    return
  }
  try {
    const res = await apiFetch(`/api/empresa/documentos/${docId}/descargar/`)
    if (res.status === 404) { toast.error('El archivo no se encontró en el servidor.'); return }
    if (!res.ok) { toast.error('No se pudo descargar el archivo.'); return }
    const blob = await res.blob()
    const cd   = res.headers.get('Content-Disposition') || ''
    const match = cd.match(/filename="?([^"]+)"?/)
    const nombre = match ? match[1] : `documento_${docId}`
    const a    = document.createElement('a')
    a.href     = URL.createObjectURL(blob)
    a.download = nombre
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    toast.error('Error de conexión al descargar.')
  }
}

// ── Renovar
function abrirRenovar(doc) {
  modalRenovar.value  = doc
  modalDetalle.value  = null
  formRenovar.value   = { fecha_emision: '', fecha_vencimiento: '', notas: '', archivo: null }
}

function onArchivoRenovarChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
    toast.error('Solo se permiten archivos PDF o imágenes (JPG, PNG, etc.).')
    e.target.value = ''
    return
  }
  if (file.size > 10 * 1024 * 1024) { toast.error('El archivo no debe superar 10 MB.'); e.target.value = ''; return }
  formRenovar.value.archivo = file
}

async function guardarRenovacion() {
  if (!formRenovar.value.archivo) { toast.error('El archivo es obligatorio.'); return }
  if (formRenovar.value.fecha_emision && formRenovar.value.fecha_vencimiento &&
      formRenovar.value.fecha_emision >= formRenovar.value.fecha_vencimiento) {
    toast.error('La fecha de vencimiento debe ser posterior a la de emisión.')
    return
  }
  const notasR = formRenovar.value.notas
  if (notasR && notasR.trim() === '') { toast.error('Las notas no pueden contener solo espacios en blanco.'); return }
  if (notasR.length > 50) { toast.error('Las notas no pueden superar 50 caracteres.'); return }
  guardandoRenovar.value = true
  try {
    const fd = new FormData()
    if (formRenovar.value.fecha_emision)     fd.append('fecha_emision',     formRenovar.value.fecha_emision)
    if (formRenovar.value.fecha_vencimiento) fd.append('fecha_vencimiento', formRenovar.value.fecha_vencimiento)
    fd.append('notas',   formRenovar.value.notas)
    fd.append('archivo', formRenovar.value.archivo)

    const res = await apiFetch(`/api/empresa/documentos/${modalRenovar.value.id}/renovar/`, { method: 'POST', body: fd })
    const data = await res.json()
    if (!res.ok) { toast.error(data.error || 'Error al renovar.'); return }
    toast.success('Documento renovado exitosamente.')
    modalRenovar.value = null
    await cargar()
  } catch {
    toast.error('Error de conexión.')
  } finally {
    guardandoRenovar.value = false
  }
}

// ── Filtro rápido desde tabla resumen
function filtrarPorVehiculo(vid) {
  filtroVehiculo.value = String(vid)
  filtroCondutor.value = ''
  filtroEntidad.value  = 'vehiculo'
}
function filtrarPorConductor(cid) {
  filtroCondutor.value = String(cid)
  filtroVehiculo.value = ''
  filtroEntidad.value  = 'conductor'
}
function limpiarFiltros() {
  filtroEntidad.value = filtroEstado.value = filtroTipo.value = ''
  filtroBuscar.value  = filtroVehiculo.value = filtroCondutor.value = ''
}

// ── Lifecycle
onMounted(async () => {
  await Promise.all([cargarEmpresas(), cargar(), cargarAuxiliares()])
})
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div>
        <h1 class="titulo">Gestión de documentos</h1>
        <p class="subtitulo">Repositorio de documentos de vehículos y conductores con alertas de vencimiento</p>
      </div>
      <button class="btn-nuevo" @click="abrirNuevo">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Subir documento
      </button>
    </div>

    <!-- Selector de empresa (solo SUPERADMIN) -->
    <div v-if="esSuperadmin" class="empresa-selector-wrap">
      <div class="empresa-selector" @click="mostrarDropdown = !mostrarDropdown">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        <span>{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
        <svg class="chevron" :class="mostrarDropdown && 'open'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </div>
      <div v-if="mostrarDropdown" class="empresa-dropdown">
        <input v-model="busqueda" class="empresa-search" placeholder="Buscar empresa…" @click.stop autofocus/>
        <div v-if="cargandoEmpresas" class="empresa-loading">Cargando...</div>
        <div v-else-if="!empresasFiltradas.length" class="empresa-empty">Sin resultados</div>
        <div v-else class="empresa-list">
          <div
            v-for="emp in empresasFiltradas" :key="emp.id"
            class="empresa-item"
            :class="empresaActiva?.id === emp.id && 'empresa-activa'"
            @click="seleccionarEmpresa(emp)">
            {{ emp.nombre }}
          </div>
        </div>
      </div>
    </div>

    <!-- Aviso sin empresa -->
    <div v-if="sinEmpresa" class="sin-empresa">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
      </svg>
      <p>Selecciona una empresa para ver sus documentos.</p>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-wrap">
      <div class="spinner"/><span>Cargando documentos...</span>
    </div>

    <template v-else-if="!sinEmpresa">
      <!-- KPIs -->
      <div class="kpis" v-if="resumen">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#EEF2FF;color:#4338CA">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <div><div class="kpi-value">{{ resumen.total }}</div><div class="kpi-label">Total</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#ECFDF5;color:#059669">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div><div class="kpi-value" style="color:#059669">{{ resumen.vigentes }}</div><div class="kpi-label">Vigentes</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FFFBEB;color:#D97706">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div><div class="kpi-value" style="color:#D97706">{{ resumen.por_vencer }}</div><div class="kpi-label">Por vencer (30 días)</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FEF2F2;color:#DC2626">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            </svg>
          </div>
          <div><div class="kpi-value" style="color:#DC2626">{{ resumen.vencidos }}</div><div class="kpi-label">Vencidos</div></div>
        </div>
      </div>

      <!-- Fila alertas + resumen por entidad -->
      <div v-if="resumen" class="grid-2 mb-4">
        <!-- Alertas activas -->
        <div class="card">
          <div class="card-head">
            <h3 class="card-title">Alertas activas</h3>
            <span v-if="resumen.alertas.length" class="badge-alerta">{{ resumen.alertas.length }}</span>
          </div>
          <div class="card-body p0">
            <div v-if="!resumen.alertas.length" class="empty-msg">Sin alertas activas.</div>
            <div v-else class="alertas-list">
              <div v-for="a in resumen.alertas" :key="a.id"
                class="alerta-row"
                :class="a.estado === 'vencido' ? 'alerta-vencido' : 'alerta-por-vencer'"
                @click="modalDetalle = documentos.find(d => d.id === a.id)">
                <div class="alerta-icono">
                  <svg v-if="documentos.find(d=>d.id===a.id)?.entidad === 'vehiculo'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                  </svg>
                  <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                  </svg>
                </div>
                <div class="alerta-info">
                  <div class="alerta-tipo">{{ a.tipo_display }}</div>
                  <div class="alerta-entidad">{{ a.entidad_nombre }}</div>
                </div>
                <div class="alerta-right">
                  <div class="alerta-fecha">{{ fechaCorta(a.fecha_vencimiento) }}</div>
                  <span class="chip-dias" :class="a.estado === 'vencido' ? 'chip-rojo' : 'chip-naranja'">
                    {{ diasLabel(a.dias_para_vencer) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Estado por vehículo + conductor -->
        <div class="col-resumen">
          <div class="card mb-2">
            <div class="card-head"><h3 class="card-title">Estado por vehículo</h3></div>
            <div class="card-body p0">
              <div v-if="!resumen.por_vehiculo.length" class="empty-msg">Sin vehículos con documentos.</div>
              <table v-else class="tabla-mini">
                <thead><tr><th>Patente</th><th>Docs</th><th>Estado</th></tr></thead>
                <tbody>
                  <tr v-for="v in resumen.por_vehiculo" :key="v.vehiculo_id"
                    class="row-click" @click="filtrarPorVehiculo(v.vehiculo_id)">
                    <td class="font-medium">{{ v.patente }}</td>
                    <td>{{ v.total }} / {{ v.esperados }}</td>
                    <td>
                      <span class="badge" :style="{ background: ESTADO[v.estado_peor]?.bg, color: ESTADO[v.estado_peor]?.text }">
                        {{ ESTADO[v.estado_peor]?.label }}
                        <span v-if="v.total < v.esperados" style="margin-left:4px">⚠ Falta {{ v.esperados - v.total }}</span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="card">
            <div class="card-head"><h3 class="card-title">Estado por conductor</h3></div>
            <div class="card-body p0">
              <div v-if="!resumen.por_conductor.length" class="empty-msg">Sin conductores con documentos.</div>
              <table v-else class="tabla-mini">
                <thead><tr><th>Conductor</th><th>Docs</th><th>Estado</th></tr></thead>
                <tbody>
                  <tr v-for="c in resumen.por_conductor" :key="c.conductor_id"
                    class="row-click" @click="filtrarPorConductor(c.conductor_id)">
                    <td class="font-medium">{{ c.nombre }}</td>
                    <td>{{ c.total }} / {{ c.esperados }}</td>
                    <td>
                      <span class="badge" :style="{ background: ESTADO[c.estado_peor]?.bg, color: ESTADO[c.estado_peor]?.text }">
                        {{ ESTADO[c.estado_peor]?.label }}
                        <span v-if="c.total < c.esperados" style="margin-left:4px">⚠ Falta {{ c.esperados - c.total }}</span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Filtros de la tabla principal -->
      <div class="filtros-bar">
        <select v-model="filtroEntidad" class="sel">
          <option value="">Todos los tipos</option>
          <option value="vehiculo">Vehículos</option>
          <option value="conductor">Conductores</option>
        </select>
        <select v-model="filtroEstado" class="sel">
          <option value="">Todos los estados</option>
          <option value="vigente">Vigente</option>
          <option value="por_vencer">Por vencer</option>
          <option value="vencido">Vencido</option>
        </select>
        <input v-model="filtroBuscar" class="input-buscar" placeholder="Buscar por tipo, patente o nombre…"/>
        <button v-if="filtroEntidad || filtroEstado || filtroBuscar || filtroVehiculo || filtroCondutor"
          class="btn-limpiar" @click="limpiarFiltros">✕ Limpiar filtros</button>
        <div class="filtro-spacer"/>
        <span class="total-label">{{ docsFiltrados.length }} documento{{ docsFiltrados.length !== 1 ? 's' : '' }}</span>
      </div>

      <!-- Tabla principal -->
      <div class="card">
        <div v-if="!docsFiltrados.length" class="card-body">
          <p class="empty-msg">Sin documentos para los filtros seleccionados.</p>
        </div>
        <div v-else class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th v-if="esTodas">Empresa</th>
                <th>Tipo</th>
                <th>Documento</th>
                <th>Asociado a</th>
                <th>Emisión</th>
                <th>Vencimiento</th>
                <th>Estado</th>
                <th>Archivo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in docsPaginados" :key="doc.id">
                <td v-if="esTodas" class="font-medium">{{ doc.empresa_nombre || '—' }}</td>
                <td>
                  <span class="badge" :style="doc.entidad === 'vehiculo'
                    ? 'background:#EEF2FF;color:#4338CA'
                    : 'background:#F5F3FF;color:#7C3AED'">
                    {{ doc.entidad === 'vehiculo' ? 'Vehículo' : 'Conductor' }}
                  </span>
                </td>
                <td class="font-medium">{{ doc.tipo_display }}</td>
                <td>{{ doc.vehiculo_patente || doc.conductor_nombre || '—' }}</td>
                <td>{{ fechaCorta(doc.fecha_emision) }}</td>
                <td>
                  <div>{{ fechaCorta(doc.fecha_vencimiento) }}</div>
                  <div v-if="doc.estado !== 'sin_vencimiento'" class="dias-mini"
                    :style="{ color: ESTADO[doc.estado]?.text }">
                    {{ diasLabel(doc.dias_para_vencer) }}
                  </div>
                </td>
                <td>
                  <span class="badge" :style="{ background: ESTADO[doc.estado]?.bg, color: ESTADO[doc.estado]?.text }">
                    {{ ESTADO[doc.estado]?.label }}
                  </span>
                </td>
                <td>
                  <button v-if="doc.tiene_archivo" class="btn-icon" title="Descargar" @click="descargar(doc.id)">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                  </button>
                  <span v-else class="text-muted">—</span>
                </td>
                <td>
                  <div class="acciones-row">
                    <button class="btn-icon" title="Ver detalle" @click="modalDetalle = doc">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
                    </button>
                    <button class="btn-icon" title="Editar" @click="abrirEditar(doc)">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <PaginacionTabla :pagina="paginaDocs" :total-paginas="totalPaginasDocs" :total="totalDocs"
            @update:pagina="irAPaginaDocs" />
        </div>
      </div>
    </template>

    <!-- ════════════════════ MODAL SUBIR/EDITAR ════════════════════ -->
    <Teleport to="body">
      <div v-if="modalSubir" class="overlay" @click.self="modalSubir = false">
        <div class="modal">
          <div class="modal-head">
            <h3>{{ editandoId ? 'Editar documento' : 'Subir documento' }}</h3>
            <button class="btn-close" @click="modalSubir = false">✕</button>
          </div>
          <div class="modal-body">
            <!-- Empresa (solo SUPERADMIN en modo "Todas", al crear) -->
            <div v-if="esTodas && !editandoId" class="field">
              <label class="label">Empresa *</label>
              <select v-model="empresaDocForm" class="input" :class="errForm.empresaDoc && 'input-error'">
                <option value="" disabled>— Seleccionar empresa —</option>
                <option v-for="e in empresas.filter(e => e.id !== '__todas__')" :key="e.id" :value="e.id">{{ e.nombre }}</option>
              </select>
              <p v-if="errForm.empresaDoc" class="field-err">{{ errForm.empresaDoc }}</p>
            </div>

            <!-- Entidad -->
            <div class="field">
              <label class="label">Entidad *</label>
              <div class="radio-group">
                <label class="radio-opt" :class="form.entidad === 'vehiculo' && 'radio-active'">
                  <input type="radio" v-model="form.entidad" value="vehiculo"/> Vehículo
                </label>
                <label class="radio-opt" :class="form.entidad === 'conductor' && 'radio-active'">
                  <input type="radio" v-model="form.entidad" value="conductor"/> Conductor
                </label>
              </div>
            </div>

            <!-- Vehículo o Conductor -->
            <div v-if="form.entidad === 'vehiculo'" class="field">
              <label class="label">Vehículo *</label>
              <select v-model="form.vehiculo_id" class="input" :class="errForm.vehiculo_id && 'input-error'" :disabled="!!editandoId">
                <option value="">— Seleccionar —</option>
                <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} — {{ v.marca }} {{ v.modelo }}</option>
              </select>
              <p v-if="errForm.vehiculo_id" class="field-err">{{ errForm.vehiculo_id }}</p>
            </div>
            <div v-else class="field">
              <label class="label">Conductor *</label>
              <select v-model="form.conductor_id" class="input" :class="errForm.conductor_id && 'input-error'" :disabled="!!editandoId">
                <option value="">— Seleccionar —</option>
                <option v-for="c in conductores" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
              <p v-if="errForm.conductor_id" class="field-err">{{ errForm.conductor_id }}</p>
            </div>

            <!-- Tipo -->
            <div class="field">
              <label class="label">Tipo de documento *</label>
              <select v-model="form.tipo" class="input" :class="errForm.tipo && 'input-error'" :disabled="!!editandoId">
                <option value="">— Seleccionar —</option>
                <option v-for="t in tiposDisponibles" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
              <p v-if="errForm.tipo" class="field-err">{{ errForm.tipo }}</p>
            </div>

            <!-- Fechas -->
            <div class="form-row">
              <div class="field">
                <label class="label">Fecha de emisión</label>
                <input v-model="form.fecha_emision" type="date" class="input"/>
              </div>
              <div class="field">
                <label class="label">Fecha de vencimiento</label>
                <input v-model="form.fecha_vencimiento" type="date" class="input" :class="errForm.fecha_vencimiento && 'input-error'"/>
                <p v-if="errForm.fecha_vencimiento" class="field-err">{{ errForm.fecha_vencimiento }}</p>
              </div>
            </div>

            <!-- Archivo -->
            <div class="field">
              <label class="label">Archivo{{ editandoId ? ' (opcional: reemplaza el actual)' : ' *' }}</label>
              <input type="file" class="input-file" accept=".pdf,image/*" @change="onArchivoChange"/>
              <p v-if="errForm.archivo" class="field-err">{{ errForm.archivo }}</p>
              <img v-if="archivoPreview" :src="archivoPreview" class="img-preview"/>
              <div v-else-if="form.archivo" class="pdf-preview">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                </svg>
                {{ form.archivo.name }}
              </div>
            </div>

            <!-- Notas -->
            <div class="field">
              <label class="label" style="display:flex;justify-content:space-between;align-items:center">
                <span>Notas</span>
                <span :style="form.notas.length > 50 ? 'color:#EF4444' : 'color:#9CA3AF'" style="font-size:0.75rem;font-weight:500">{{ form.notas.length }}/50</span>
              </label>
              <textarea v-model="form.notas" class="input textarea" :class="errForm.notas && 'input-error'" rows="2" placeholder="Opcional…" maxlength="60"/>
              <p v-if="errForm.notas" class="field-err">{{ errForm.notas }}</p>
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn-cancel" @click="modalSubir = false">Cancelar</button>
            <button class="btn-primary-sm" @click="guardarDocumento" :disabled="guardando">
              <span v-if="guardando" class="spin-sm"/>
              {{ guardando ? 'Guardando...' : (editandoId ? 'Actualizar' : 'Subir documento') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ════════════════════ MODAL DETALLE ════════════════════ -->
    <Teleport to="body">
      <div v-if="modalDetalle" class="overlay" @click.self="modalDetalle = null">
        <div class="modal">
          <div class="modal-head">
            <h3>{{ modalDetalle.tipo_display }}</h3>
            <button class="btn-close" @click="modalDetalle = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="detalle-grid">
              <div class="det-item"><span class="det-label">Entidad</span><span class="det-val">{{ modalDetalle.entidad === 'vehiculo' ? 'Vehículo' : 'Conductor' }}</span></div>
              <div class="det-item"><span class="det-label">Asociado a</span><span class="det-val">{{ modalDetalle.vehiculo_patente || modalDetalle.conductor_nombre || '—' }}</span></div>
              <div class="det-item"><span class="det-label">Emisión</span><span class="det-val">{{ fechaCorta(modalDetalle.fecha_emision) }}</span></div>
              <div class="det-item">
                <span class="det-label">Vencimiento</span>
                <span class="det-val" :style="{ color: ESTADO[modalDetalle.estado]?.text }">
                  {{ fechaCorta(modalDetalle.fecha_vencimiento) }}
                  <span v-if="modalDetalle.estado !== 'sin_vencimiento'"> · {{ diasLabel(modalDetalle.dias_para_vencer) }}</span>
                </span>
              </div>
              <div class="det-item"><span class="det-label">Estado</span>
                <span class="badge" :style="{ background: ESTADO[modalDetalle.estado]?.bg, color: ESTADO[modalDetalle.estado]?.text }">
                  {{ ESTADO[modalDetalle.estado]?.label }}
                </span>
              </div>
              <div class="det-item"><span class="det-label">Subido por</span><span class="det-val">{{ modalDetalle.subido_por_nombre || '—' }}</span></div>
              <div v-if="modalDetalle.notas" class="det-item full"><span class="det-label">Notas</span><span class="det-val">{{ modalDetalle.notas }}</span></div>
            </div>
          </div>
          <div class="modal-foot" style="justify-content:space-between">
            <button class="btn-danger-sm" @click="confirmEliminar = modalDetalle.id">Eliminar</button>
            <div style="display:flex;gap:0.5rem">
              <button v-if="modalDetalle.tiene_archivo" class="btn-cancel" @click="descargar(modalDetalle.id)">Descargar</button>
              <button class="btn-cancel" @click="abrirRenovar(modalDetalle)">Renovar</button>
              <button class="btn-primary-sm" @click="abrirEditar(modalDetalle)">Editar</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ════════════════════ MODAL RENOVAR ════════════════════ -->
    <Teleport to="body">
      <div v-if="modalRenovar" class="overlay" @click.self="modalRenovar = null">
        <div class="modal">
          <div class="modal-head">
            <h3>Renovar documento</h3>
            <button class="btn-close" @click="modalRenovar = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="banner-info">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              Esta renovación no elimina el documento anterior. Ambos quedarán en el historial.
            </div>
            <div class="field">
              <label class="label">Tipo</label>
              <div class="input input-locked">{{ modalRenovar.tipo_display }} — {{ modalRenovar.vehiculo_patente || modalRenovar.conductor_nombre }}</div>
            </div>
            <div class="form-row">
              <div class="field">
                <label class="label">Nueva fecha de emisión</label>
                <input v-model="formRenovar.fecha_emision" type="date" class="input"/>
              </div>
              <div class="field">
                <label class="label">Nueva fecha de vencimiento</label>
                <input v-model="formRenovar.fecha_vencimiento" type="date" class="input"/>
              </div>
            </div>
            <div class="field">
              <label class="label">Nuevo archivo *</label>
              <input type="file" class="input-file" accept=".pdf,image/*" @change="onArchivoRenovarChange"/>
            </div>
            <div class="field">
              <label class="label" style="display:flex;justify-content:space-between;align-items:center">
                <span>Notas</span>
                <span :style="formRenovar.notas.length > 50 ? 'color:#EF4444' : 'color:#9CA3AF'" style="font-size:0.75rem;font-weight:500">{{ formRenovar.notas.length }}/50</span>
              </label>
              <textarea v-model="formRenovar.notas" class="input textarea" rows="2" placeholder="Opcional…" maxlength="60"/>
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn-cancel" @click="modalRenovar = null">Cancelar</button>
            <button class="btn-primary-sm" @click="guardarRenovacion" :disabled="guardandoRenovar">
              <span v-if="guardandoRenovar" class="spin-sm"/>
              {{ guardandoRenovar ? 'Renovando...' : 'Confirmar renovación' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ════════════════════ CONFIRM ELIMINAR ════════════════════ -->
    <Teleport to="body">
      <div v-if="confirmEliminar" class="overlay" @click.self="confirmEliminar = null">
        <div class="modal modal-sm">
          <div class="modal-head"><h3>¿Eliminar documento?</h3></div>
          <div class="modal-body">
            <p style="color:#374151;font-size:0.875rem">Esta acción no se puede deshacer. El archivo adjunto también será eliminado.</p>
          </div>
          <div class="modal-foot">
            <button class="btn-cancel" @click="confirmEliminar = null">Cancelar</button>
            <button class="btn-danger-sm" @click="eliminarDoc">Eliminar</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { padding: 1.5rem 2rem; max-width: 1400px; font-family: 'Inter', system-ui, sans-serif; }
.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; gap: 1rem; }
.titulo { font-size: 1.5rem; font-weight: 800; color: #111827; margin: 0 0 0.2rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.btn-nuevo { display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1.1rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; border: none; border-radius: 9px; font-size: 0.875rem; font-weight: 600; cursor: pointer; font-family: inherit; white-space: nowrap; }
.btn-nuevo svg { width: 16px; height: 16px; }

.loading-wrap { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; padding: 3rem 0; font-size: 0.875rem; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #4F46E5; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

/* KPIs */
.kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px,1fr)); gap: 1rem; margin-bottom: 1.25rem; }
.kpi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1rem 1.25rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-icon svg { width: 20px; height: 20px; }
.kpi-value { font-size: 1.5rem; font-weight: 800; color: #111827; line-height: 1.1; }
.kpi-label { font-size: 0.75rem; color: #9CA3AF; font-weight: 500; margin-top: 0.15rem; }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.mb-4 { margin-bottom: 1rem; }
.mb-2 { margin-bottom: 0.75rem; }
.col-resumen { display: flex; flex-direction: column; gap: 0.75rem; }

/* Cards */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.card-body { padding: 1.25rem; }
.p0 { padding: 0; }
.empty-msg { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 1.5rem; }
.badge-alerta { background: #FEF2F2; color: #DC2626; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 999px; }

/* Alertas */
.alertas-list { max-height: 320px; overflow-y: auto; }
.alerta-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.25rem; border-bottom: 1px solid transparent; cursor: pointer; transition: opacity 0.15s; }
.alerta-row:last-child { border-bottom: none; }
.alerta-row:hover { opacity: 0.8; }
.alerta-vencido   { background: rgba(254,242,242,0.6); border-bottom-color: #FECACA20; }
.alerta-por-vencer { background: rgba(255,251,235,0.6); border-bottom-color: #FDE68A20; }
.alerta-icono { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #6B7280; }
.alerta-icono svg { width: 18px; height: 18px; }
.alerta-info { flex: 1; }
.alerta-tipo   { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.alerta-entidad { font-size: 0.75rem; color: #9CA3AF; }
.alerta-right { display: flex; flex-direction: column; align-items: flex-end; gap: 0.2rem; }
.alerta-fecha { font-size: 0.75rem; color: #6B7280; }
.chip-dias { font-size: 0.7rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 999px; white-space: nowrap; }
.chip-rojo   { background: #FEF2F2; color: #DC2626; }
.chip-naranja { background: #FFFBEB; color: #D97706; }

/* Tabla mini */
.tabla-mini { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.tabla-mini th { padding: 0.5rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.04em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla-mini td { padding: 0.6rem 1rem; border-bottom: 1px solid #F9FAFB; color: #374151; }
.tabla-mini tr:last-child td { border-bottom: none; }
.row-click { cursor: pointer; transition: background 0.1s; }
.row-click:hover td { background: #F9FAFB; }

/* Filtros */
.filtros-bar { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; flex-wrap: wrap; }
.sel { padding: 0.45rem 0.7rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; background: #fff; color: #374151; cursor: pointer; }
.input-buscar { padding: 0.45rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; width: 220px; outline: none; }
.input-buscar:focus { border-color: #7C3AED; }
.btn-limpiar { padding: 0.4rem 0.75rem; background: #F3F4F6; border: none; border-radius: 7px; font-size: 0.8rem; color: #6B7280; cursor: pointer; }
.filtro-spacer { flex: 1; }
.total-label { font-size: 0.8rem; color: #9CA3AF; }

/* Tabla principal */
.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; white-space: nowrap; }
.tabla th { padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }
.tabla td { padding: 0.75rem 1rem; color: #374151; border-bottom: 1px solid #F9FAFB; vertical-align: middle; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tr:hover td { background: #FAFAFA; }
.font-medium { font-weight: 600; color: #111827; }
.text-muted { color: #D1D5DB; }
.dias-mini { font-size: 0.72rem; margin-top: 0.15rem; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.acciones-row { display: flex; gap: 0.3rem; }
.btn-icon { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; border: 1.5px solid #E5E7EB; border-radius: 7px; background: #fff; color: #6B7280; cursor: pointer; transition: all 0.15s; }
.btn-icon svg { width: 15px; height: 15px; }
.btn-icon:hover { border-color: #4F46E5; color: #4F46E5; }

/* Modales */
.overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.modal { background: #fff; border-radius: 16px; width: 100%; max-width: 540px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-sm { max-width: 400px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; }
.modal-head h3 { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.btn-close { background: none; border: none; font-size: 1.1rem; color: #9CA3AF; cursor: pointer; padding: 0.2rem; }
.btn-close:hover { color: #374151; }
.modal-body { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 0.875rem; }
.modal-foot { display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem; padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6; }

/* Campos del modal */
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.label { font-size: 0.8rem; font-weight: 600; color: #374151; }
.input { padding: 0.55rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; width: 100%; outline: none; font-family: inherit; background: #fff; color: #111827; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input-error { border-color: #EF4444 !important; }
.input-locked { background: #F9FAFB; color: #6B7280; cursor: default; }
.textarea { resize: vertical; min-height: 64px; }
.input-file { padding: 0.45rem 0; border: none; font-size: 0.8125rem; color: #374151; }
.img-preview { max-height: 120px; border-radius: 8px; border: 1px solid #E5E7EB; margin-top: 0.5rem; }
.pdf-preview { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; font-size: 0.8125rem; color: #374151; }
.pdf-preview svg { width: 18px; height: 18px; color: #DC2626; }
.field-err { font-size: 0.78rem; color: #EF4444; margin: 0; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.radio-group { display: flex; gap: 0.75rem; }
.radio-opt { display: flex; align-items: center; gap: 0.4rem; padding: 0.45rem 0.875rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; color: #374151; cursor: pointer; transition: all 0.15s; }
.radio-opt input { display: none; }
.radio-active { border-color: #7C3AED; background: #F5F3FF; color: #7C3AED; font-weight: 600; }

/* Botones del modal */
.btn-cancel { padding: 0.5rem 1rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-cancel:hover { border-color: #9CA3AF; }
.btn-primary-sm { display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1.1rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; font-family: inherit; }
.btn-primary-sm:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-danger-sm { padding: 0.5rem 1rem; background: #FEF2F2; border: 1.5px solid #FECACA; border-radius: 8px; font-size: 0.875rem; font-weight: 600; color: #DC2626; cursor: pointer; font-family: inherit; }
.btn-danger-sm:hover { background: #FEE2E2; }
.spin-sm { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }

/* Detalle modal */
.detalle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.875rem; }
.det-item { display: flex; flex-direction: column; gap: 0.2rem; }
.det-item.full { grid-column: 1 / -1; }
.det-label { font-size: 0.72rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.04em; }
.det-val { font-size: 0.875rem; color: #374151; font-weight: 500; }

/* Selector de empresa */
.empresa-selector-wrap { position: relative; margin-bottom: 1.25rem; }
.empresa-selector { display: inline-flex; align-items: center; gap: 0.6rem; padding: 0.55rem 1rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 10px; cursor: pointer; font-size: 0.875rem; font-weight: 600; color: #374151; transition: border-color 0.15s; user-select: none; }
.empresa-selector:hover { border-color: #7C3AED; }
.empresa-selector svg:first-child { width: 17px; height: 17px; color: #7C3AED; flex-shrink: 0; }
.chevron { width: 15px; height: 15px; color: #9CA3AF; transition: transform 0.2s; }
.chevron.open { transform: rotate(180deg); }
.empresa-dropdown { position: absolute; top: calc(100% + 6px); left: 0; min-width: 300px; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); z-index: 200; overflow: hidden; }
.empresa-search { width: 100%; padding: 0.6rem 0.875rem; border: none; border-bottom: 1px solid #F3F4F6; font-size: 0.875rem; outline: none; color: #374151; }
.empresa-loading { padding: 1rem; text-align: center; font-size: 0.8125rem; color: #9CA3AF; }
.empresa-empty   { padding: 1rem; text-align: center; font-size: 0.8125rem; color: #9CA3AF; }
.empresa-list { max-height: 240px; overflow-y: auto; }
.empresa-item { padding: 0.6rem 0.875rem; font-size: 0.875rem; color: #374151; cursor: pointer; transition: background 0.1s; }
.empresa-item:hover { background: #F5F3FF; color: #7C3AED; }
.empresa-activa { background: #F5F3FF; color: #7C3AED; font-weight: 600; }
.sin-empresa { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 4rem 2rem; color: #9CA3AF; text-align: center; }
.sin-empresa svg { width: 40px; height: 40px; color: #D1D5DB; }
.sin-empresa p { font-size: 0.9375rem; margin: 0; }

/* Banner info */
.banner-info { display: flex; align-items: flex-start; gap: 0.6rem; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 0.75rem 1rem; font-size: 0.8125rem; color: #1E40AF; }
.banner-info svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 1px; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .header { flex-direction: column; align-items: stretch; gap: 0.625rem; }
  .titulo { font-size: 1.25rem; }
  .btn-nuevo { justify-content: center; }
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
