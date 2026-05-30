<script setup>
import { ref, computed, onMounted } from 'vue'
import { Camera, CameraSource, CameraResultType } from '@capacitor/camera'
import { Preferences } from '@capacitor/preferences'
import { Capacitor } from '@capacitor/core'
import { Filesystem, Directory } from '@capacitor/filesystem'
import { useDocumentosStore, TIPOS_CONDUCTOR, TIPOS_VEHICULO } from '@/stores/documentos.js'
import { useAuthStore } from '@/stores/auth.js'
import BottomNav from '@/components/BottomNav.vue'

const store = useDocumentosStore()
const auth  = useAuthStore()

const vehiculo = computed(() => auth.usuario?.vehiculo_asignado || null)

// ── Pull to refresh ──────────────────────────────────────────────────────────
let startY       = 0
const refreshing = ref(false)
function onTouchStart(e) { startY = e.touches[0].clientY }
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await store.cargarDocumentos()
    refreshing.value = false
  }
}

// ── Helpers UI ───────────────────────────────────────────────────────────────
const ESTADOS = {
  vigente:         { label: 'Vigente',    color: '#085041', bg: '#E1F5EE' },
  por_vencer:      { label: 'Por vencer', color: '#B45309', bg: '#FEF3C7' },
  vencido:         { label: 'Vencido',    color: '#791F1F', bg: '#FCEBEB' },
  sin_vencimiento: { label: 'Sin venc.',  color: '#374151', bg: '#F3F4F6' },
}
function badgeEstado(estado) { return ESTADOS[estado] || { label: estado, color: '#555', bg: '#eee' } }
function formatFecha(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// ── Chips del header ─────────────────────────────────────────────────────────
const hayVencidos  = computed(() => store.documentos.some(d => d.estado === 'vencido'))
const hayPorVencer = computed(() => store.documentos.some(d => d.estado === 'por_vencer'))
const todoAlDia    = computed(() =>
  store.documentos.length > 0 && !hayVencidos.value && !hayPorVencer.value,
)

// ── Toast ────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', tipo: 'ok' })
let toastTimer = null
function mostrarToast(mensaje, tipo = 'ok') {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, tipo }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3500)
}

// ── Modal ────────────────────────────────────────────────────────────────────
const modalAbierto  = ref(false)
const tipoForzado   = ref(null)
const esDocVehiculo = ref(false)
const errorForm     = ref('')
const form = ref({ tipo: '', fechaEmision: '', fechaVencimiento: '', notas: '' })
const archivoBlob    = ref(null)
const archivoNombre  = ref('')
const archivoPreview = ref(null)
const esImagen       = ref(false)
const inputArchivo   = ref(null)

const TODOS_TIPOS = [...TIPOS_CONDUCTOR, ...TIPOS_VEHICULO]

const tipoActual = computed(() =>
  TODOS_TIPOS.find(t => t.value === (tipoForzado.value || form.value.tipo)),
)
const esRenovacion = computed(() => !!(form.value.tipo && store.docPorTipo[form.value.tipo]))

function abrirModal(tipo, esVehiculo = false) {
  tipoForzado.value    = tipo
  esDocVehiculo.value  = esVehiculo
  form.value           = { tipo: tipo || '', fechaEmision: '', fechaVencimiento: '', notas: '' }
  archivoBlob.value    = null
  archivoNombre.value  = ''
  archivoPreview.value = null
  esImagen.value       = false
  errorForm.value      = ''
  modalAbierto.value   = true
}
function cerrarModal() { modalAbierto.value = false }

// ── Manejo de archivo ────────────────────────────────────────────────────────
async function tomarFotoConCamara() {
  try {
    const foto = await Camera.getPhoto({ quality: 90, allowEditing: false, resultType: CameraResultType.DataUrl, source: CameraSource.Camera })
    _procesarDataUrl(foto.dataUrl)
  } catch {}
}
async function elegirDeGaleria() {
  try {
    const foto = await Camera.getPhoto({ quality: 90, allowEditing: false, resultType: CameraResultType.DataUrl, source: CameraSource.Photos })
    _procesarDataUrl(foto.dataUrl)
  } catch {}
}
function seleccionarArchivo() { inputArchivo.value?.click() }
function onArchivoSeleccionado(e) {
  const file = e.target.files?.[0]; if (!file) return
  if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
    mostrarToast('Solo se permiten archivos PDF o imágenes.', 'error')
    e.target.value = ''
    return
  }
  archivoBlob.value    = file
  archivoNombre.value  = file.name
  esImagen.value       = file.type.startsWith('image/')
  archivoPreview.value = esImagen.value ? URL.createObjectURL(file) : null
  e.target.value = ''
}
function _procesarDataUrl(dataUrl) {
  const b64   = dataUrl.split(',')[1]
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
  archivoBlob.value    = new Blob([bytes], { type: 'image/jpeg' })
  archivoNombre.value  = `documento_${Date.now()}.jpg`
  archivoPreview.value = dataUrl
  esImagen.value       = true
}
function quitarArchivo() {
  archivoBlob.value = null; archivoNombre.value = ''; archivoPreview.value = null; esImagen.value = false
}

// ── Enviar ───────────────────────────────────────────────────────────────────
async function enviarDocumento() {
  errorForm.value = ''
  if (!form.value.tipo) { errorForm.value = 'Selecciona el tipo de documento.'; return }
  if (form.value.fechaEmision && form.value.fechaVencimiento &&
      form.value.fechaEmision >= form.value.fechaVencimiento) {
    errorForm.value = 'La fecha de vencimiento debe ser posterior a la de emisión.'
    return
  }
  const notas = form.value.notas || ''
  if (notas && notas.trim() === '') { errorForm.value = 'Las notas no pueden contener solo espacios en blanco.'; return }
  if (notas.length > 50) { errorForm.value = 'Las notas no pueden superar 50 caracteres.'; return }
  const usuario = auth.usuario
  if (!usuario) { errorForm.value = 'Sesión no disponible.'; return }

  const fd = new FormData()
  fd.append('tipo',              form.value.tipo)
  fd.append('fecha_emision',     form.value.fechaEmision     || '')
  fd.append('fecha_vencimiento', form.value.fechaVencimiento || '')
  fd.append('notas',             form.value.notas            || '')

  if (esDocVehiculo.value) {
    if (!vehiculo.value?.id) { errorForm.value = 'Sin vehículo asignado.'; return }
    fd.append('entidad',     'vehiculo')
    fd.append('vehiculo_id', String(vehiculo.value.id))
  } else {
    fd.append('entidad',      'conductor')
    fd.append('conductor_id', String(usuario.id))
  }

  if (archivoBlob.value) fd.append('archivo', archivoBlob.value, archivoNombre.value)

  const docPrevio = store.docPorTipo[form.value.tipo]
  if (docPrevio) fd.append('version_anterior_id', String(docPrevio.id))

  const res = await store.subirDocumento(fd)
  if (res.success) {
    cerrarModal()
    mostrarToast(docPrevio ? 'Documento renovado correctamente' : 'Documento subido correctamente')
  } else {
    errorForm.value = res.error || 'Error al subir el documento.'
  }
}

// ── Ver documento (preview in-app) ──────────────────────────────────────────
const esNativo        = Capacitor.isNativePlatform()
const previsualizando = ref(null)
const previewAbierto  = ref(false)
const previewUrl      = ref(null)
const previewMime     = ref('')
const previewEsPdf    = ref(false)

const EXT_IMAGEN = new Set(['jpg','jpeg','png','gif','webp','bmp'])

function _blobToBase64(blob) {
  return new Promise(resolve => {
    const r = new FileReader()
    r.onloadend = () => resolve(r.result.split(',')[1])
    r.readAsDataURL(blob)
  })
}

function _mimeDesdeNombre(nombre) {
  const ext = (nombre || '').split('.').pop().toLowerCase()
  if (EXT_IMAGEN.has(ext)) return 'image/jpeg'
  if (ext === 'pdf')       return 'application/pdf'
  return ''
}

async function verDocumento(docId, nombreArchivo = '') {
  const doc = store.documentos.find(d => d.id === docId)
  if (doc && !doc.tiene_archivo) {
    mostrarToast('Este documento no tiene archivo adjunto.', 'error')
    return
  }
  previsualizando.value = docId
  try {
    const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const { value: token } = await Preferences.get({ key: 'access_token' })
    const res = await fetch(`${BASE_URL}/api/empresa/documentos/${docId}/descargar/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.status === 404) { mostrarToast('El archivo no se encontró en el servidor.', 'error'); return }
    if (!res.ok) throw new Error()
    const blob = await res.blob()

    // El backend puede devolver application/octet-stream; detectamos por nombre como fallback.
    let mime = blob.type || ''
    if (!mime || mime === 'application/octet-stream') mime = _mimeDesdeNombre(nombreArchivo)
    previewMime.value  = mime
    previewEsPdf.value = mime === 'application/pdf' || (!mime.startsWith('image/') && !!mime)

    if (esNativo) {
      const esImagen = mime.startsWith('image/')
      const ext  = esImagen ? 'jpg' : 'pdf'
      const path = `doc_preview_${docId}.${ext}`
      await Filesystem.writeFile({ path, data: await _blobToBase64(blob), directory: Directory.Cache })
      const { uri } = await Filesystem.getUri({ path, directory: Directory.Cache })
      previewUrl.value = Capacitor.convertFileSrc(uri)
    } else {
      previewUrl.value = URL.createObjectURL(blob)
    }
    previewAbierto.value = true
  } catch {
    mostrarToast('No se pudo abrir el documento', 'error')
  } finally {
    previsualizando.value = null
  }
}

function cerrarPreview() {
  previewAbierto.value = false
  previewEsPdf.value   = false
  if (previewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value  = null
  previewMime.value = ''
}

onMounted(() => store.cargarDocumentos())
</script>

<template>
  <div
    class="min-h-dvh bg-gray-50 pb-nav"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- Spinner pull-to-refresh -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="doc-header">
      <div class="doc-header-pattern" aria-hidden="true"/>
      <div class="doc-header-content">
        <div>
          <p class="doc-header-subtitle">Mis documentos</p>
          <h1 class="doc-header-title">Documentación</h1>
        </div>
        <div class="doc-chips">
          <span v-if="hayVencidos" class="doc-chip doc-chip--red">
            <i class="ti ti-alert-circle text-[10px]"/> Vencido
          </span>
          <span v-else-if="hayPorVencer" class="doc-chip doc-chip--yellow">
            <i class="ti ti-clock text-[10px]"/> Por vencer
          </span>
          <span v-else-if="todoAlDia" class="doc-chip doc-chip--green">
            <i class="ti ti-circle-check text-[10px]"/> Al día
          </span>
        </div>
      </div>
    </header>

    <!-- Skeleton -->
    <div v-if="store.cargando && !store.documentos.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 4" :key="i" class="h-28 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <div v-else class="px-4 mt-4 flex flex-col gap-5 mb-2">

      <!-- ══════════════════════════════════════════════════════════════════
           SECCIÓN 1: MI DOCUMENTACIÓN (conductor)
      ══════════════════════════════════════════════════════════════════════ -->
      <section>
        <p class="doc-section-label">Mi documentación</p>
        <div class="flex flex-col gap-3">
          <div
            v-for="tipo in TIPOS_CONDUCTOR"
            :key="tipo.value"
            class="bg-white rounded-2xl border border-gray-100 p-4"
            style="box-shadow: var(--shadow-sm)"
          >
            <!-- Cabecera de la tarjeta -->
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                   :style="`background: ${tipo.colorSuave}`">
                <i class="ti text-xl" :class="tipo.icono" :style="`color: ${tipo.color}`"/>
              </div>
              <p class="flex-1 text-sm font-bold text-gray-800">{{ tipo.label }}</p>
              <span v-if="store.docPorTipo[tipo.value]"
                class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5"
                :style="`color: ${badgeEstado(store.docPorTipo[tipo.value].estado).color}; background: ${badgeEstado(store.docPorTipo[tipo.value].estado).bg}`">
                {{ badgeEstado(store.docPorTipo[tipo.value].estado).label }}
              </span>
              <span v-else class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5 text-gray-500 bg-gray-100">
                Sin documento
              </span>
            </div>

            <!-- Doc existente -->
            <template v-if="store.docPorTipo[tipo.value]">
              <div class="flex gap-4 mb-3">
                <div v-if="store.docPorTipo[tipo.value].fecha_emision">
                  <p class="text-[10px] text-gray-400 mb-0.5">Emisión</p>
                  <p class="text-xs font-semibold text-gray-700">{{ formatFecha(store.docPorTipo[tipo.value].fecha_emision) }}</p>
                </div>
                <div v-if="store.docPorTipo[tipo.value].fecha_vencimiento">
                  <p class="text-[10px] text-gray-400 mb-0.5">Vencimiento</p>
                  <p class="text-xs font-semibold" :style="`color: ${badgeEstado(store.docPorTipo[tipo.value].estado).color}`">
                    {{ formatFecha(store.docPorTipo[tipo.value].fecha_vencimiento) }}
                  </p>
                </div>
              </div>
              <p v-if="store.docPorTipo[tipo.value].tiene_archivo"
                class="text-[11px] text-gray-400 mb-3 flex items-center gap-1 truncate">
                <i class="ti ti-paperclip shrink-0"/>
                {{ store.docPorTipo[tipo.value].nombre_archivo || 'Archivo adjunto' }}
              </p>
              <div class="flex gap-2">
                <button v-if="store.docPorTipo[tipo.value].tiene_archivo"
                  @click="verDocumento(store.docPorTipo[tipo.value].id, store.docPorTipo[tipo.value].nombre_archivo)"
                  :disabled="previsualizando === store.docPorTipo[tipo.value].id"
                  class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-gray-200
                         text-xs font-semibold text-gray-600 bg-gray-50 min-h-[44px] active:bg-gray-100 transition disabled:opacity-50">
                  <span v-if="previsualizando === store.docPorTipo[tipo.value].id"
                    class="w-3.5 h-3.5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"/>
                  <i v-else class="ti ti-eye"/> Ver
                </button>
                <button @click="abrirModal(tipo.value, false)"
                  class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border
                         text-xs font-semibold min-h-[44px] active:opacity-75 transition"
                  :style="`background: ${tipo.colorSuave}; border-color: ${tipo.color}40; color: ${tipo.color}`">
                  <i class="ti ti-refresh"/> Renovar
                </button>
              </div>
            </template>
            <template v-else>
              <p class="text-xs text-gray-400 mb-3">No se ha subido este documento aún.</p>
              <button @click="abrirModal(tipo.value, false)"
                class="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                       text-sm font-semibold min-h-[44px] active:opacity-75 transition"
                :style="`background: ${tipo.colorSuave}; color: ${tipo.color}`">
                <i class="ti ti-upload"/> Subir documento
              </button>
            </template>
          </div>
        </div>
      </section>

      <!-- ══════════════════════════════════════════════════════════════════
           SECCIÓN 2: DOCUMENTOS DEL VEHÍCULO
      ══════════════════════════════════════════════════════════════════════ -->
      <section>
        <p class="doc-section-label">
          Vehículo
          <span v-if="vehiculo" class="text-gray-600 normal-case font-bold ml-1">
            {{ vehiculo.patente }}
            <span class="font-normal text-gray-400">· {{ vehiculo.marca }} {{ vehiculo.modelo }}</span>
          </span>
        </p>

        <!-- Sin vehículo asignado -->
        <div v-if="!vehiculo"
          class="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-3"
          style="box-shadow: var(--shadow-sm)">
          <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center shrink-0">
            <i class="ti ti-car text-xl text-gray-400"/>
          </div>
          <div>
            <p class="text-sm font-semibold text-gray-700">Sin vehículo asignado</p>
            <p class="text-xs text-gray-400 mt-0.5">El administrador debe asignarte un vehículo para subir su documentación.</p>
          </div>
        </div>

        <!-- Tarjetas del vehículo -->
        <div v-else class="flex flex-col gap-3">
          <div
            v-for="tipo in TIPOS_VEHICULO"
            :key="tipo.value"
            class="bg-white rounded-2xl border border-gray-100 p-4"
            style="box-shadow: var(--shadow-sm)"
          >
            <!-- Cabecera -->
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                   :style="`background: ${tipo.colorSuave}`">
                <i class="ti text-xl" :class="tipo.icono" :style="`color: ${tipo.color}`"/>
              </div>
              <p class="flex-1 text-sm font-bold text-gray-800">{{ tipo.label }}</p>
              <span v-if="store.docPorTipo[tipo.value]"
                class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5"
                :style="`color: ${badgeEstado(store.docPorTipo[tipo.value].estado).color}; background: ${badgeEstado(store.docPorTipo[tipo.value].estado).bg}`">
                {{ badgeEstado(store.docPorTipo[tipo.value].estado).label }}
              </span>
              <span v-else class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5 text-gray-500 bg-gray-100">
                Sin documento
              </span>
            </div>

            <!-- Doc existente -->
            <template v-if="store.docPorTipo[tipo.value]">
              <div class="flex gap-4 mb-3">
                <div v-if="store.docPorTipo[tipo.value].fecha_emision">
                  <p class="text-[10px] text-gray-400 mb-0.5">Emisión</p>
                  <p class="text-xs font-semibold text-gray-700">{{ formatFecha(store.docPorTipo[tipo.value].fecha_emision) }}</p>
                </div>
                <div v-if="store.docPorTipo[tipo.value].fecha_vencimiento">
                  <p class="text-[10px] text-gray-400 mb-0.5">Vencimiento</p>
                  <p class="text-xs font-semibold" :style="`color: ${badgeEstado(store.docPorTipo[tipo.value].estado).color}`">
                    {{ formatFecha(store.docPorTipo[tipo.value].fecha_vencimiento) }}
                  </p>
                </div>
              </div>
              <p v-if="store.docPorTipo[tipo.value].tiene_archivo"
                class="text-[11px] text-gray-400 mb-3 flex items-center gap-1 truncate">
                <i class="ti ti-paperclip shrink-0"/>
                {{ store.docPorTipo[tipo.value].nombre_archivo || 'Archivo adjunto' }}
              </p>
              <div class="flex gap-2">
                <button v-if="store.docPorTipo[tipo.value].tiene_archivo"
                  @click="verDocumento(store.docPorTipo[tipo.value].id, store.docPorTipo[tipo.value].nombre_archivo)"
                  :disabled="previsualizando === store.docPorTipo[tipo.value].id"
                  class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-gray-200
                         text-xs font-semibold text-gray-600 bg-gray-50 min-h-[44px] active:bg-gray-100 transition disabled:opacity-50">
                  <span v-if="previsualizando === store.docPorTipo[tipo.value].id"
                    class="w-3.5 h-3.5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"/>
                  <i v-else class="ti ti-eye"/> Ver
                </button>
                <button @click="abrirModal(tipo.value, true)"
                  class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border
                         text-xs font-semibold min-h-[44px] active:opacity-75 transition"
                  :style="`background: ${tipo.colorSuave}; border-color: ${tipo.color}40; color: ${tipo.color}`">
                  <i class="ti ti-refresh"/> Renovar
                </button>
              </div>
            </template>
            <template v-else>
              <p class="text-xs text-gray-400 mb-3">No se ha subido este documento aún.</p>
              <button @click="abrirModal(tipo.value, true)"
                class="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                       text-sm font-semibold min-h-[44px] active:opacity-75 transition"
                :style="`background: ${tipo.colorSuave}; color: ${tipo.color}`">
                <i class="ti ti-upload"/> Subir documento
              </button>
            </template>
          </div>
        </div>
      </section>

      <!-- Error de carga -->
      <div v-if="store.error && !store.documentos.length"
        class="bg-red-50 rounded-2xl border border-red-100 p-4 flex items-center gap-3">
        <i class="ti ti-alert-circle text-red-400 text-xl shrink-0"/>
        <div class="flex-1">
          <p class="text-sm font-semibold text-red-700">Error al cargar</p>
          <p class="text-xs text-red-500">{{ store.error }}</p>
        </div>
        <button @click="store.cargarDocumentos()"
          class="text-xs text-red-600 font-semibold underline min-h-[44px] px-2 shrink-0">
          Reintentar
        </button>
      </div>

    </div>

    <BottomNav />

    <!-- Input archivo oculto -->
    <input ref="inputArchivo" type="file" accept=".pdf,image/*" class="hidden" @change="onArchivoSeleccionado"/>

    <!-- Toast -->
    <Transition name="toast">
      <div v-if="toast.visible"
        class="fixed left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl shadow-lg
               text-sm font-medium text-white flex items-center gap-2"
        :class="toast.tipo === 'error' ? 'bg-red-600' : 'bg-gray-800'"
        style="bottom: calc(90px + env(safe-area-inset-bottom))">
        <i :class="toast.tipo === 'error' ? 'ti ti-alert-circle' : 'ti ti-circle-check'"/>
        {{ toast.mensaje }}
      </div>
    </Transition>

    <!-- ════════════════════════════════════════════════════════════════════════
         MODAL: SUBIR / RENOVAR DOCUMENTO
    ════════════════════════════════════════════════════════════════════════════ -->
    <Transition name="sheet">
      <div v-if="modalAbierto" class="fixed inset-0 z-[60] flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/50" @click="cerrarModal"/>
        <div class="relative bg-white rounded-t-2xl scroll-hidden"
          style="max-height: min(88vh, 88dvh); padding-bottom: env(safe-area-inset-bottom, 0px)">

          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-white z-10">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>

          <div class="px-4 pb-6">
            <!-- Header modal -->
            <div class="flex items-center gap-3 mb-5">
              <div v-if="tipoActual" class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                   :style="`background: ${tipoActual.colorSuave}`">
                <i class="ti text-lg" :class="tipoActual.icono" :style="`color: ${tipoActual.color}`"/>
              </div>
              <div>
                <h2 class="text-base font-bold text-gray-800 leading-tight">
                  {{ esRenovacion ? 'Renovar' : 'Subir' }} documento
                </h2>
                <p v-if="tipoActual" class="text-xs text-gray-400">{{ tipoActual.label }}</p>
                <p v-if="esDocVehiculo && vehiculo" class="text-xs font-semibold mt-0.5"
                   :style="`color: ${tipoActual?.color}`">
                  {{ vehiculo.patente }} · {{ vehiculo.marca }} {{ vehiculo.modelo }}
                </p>
              </div>
            </div>

            <!-- Fechas -->
            <div class="flex gap-3 mb-4">
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">Fecha de emisión</label>
                <input v-model="form.fechaEmision" type="date"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                         focus:outline-none focus:border-[var(--color-acento)] transition bg-white"/>
              </div>
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">Fecha de vencimiento</label>
                <input v-model="form.fechaVencimiento" type="date"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                         focus:outline-none focus:border-[var(--color-acento)] transition bg-white"/>
              </div>
            </div>

            <!-- Notas -->
            <div class="mb-4">
              <label class="flex items-center justify-between text-xs font-semibold text-gray-600 mb-1">
                <span>Notas <span class="text-gray-400 font-normal">(opcional)</span></span>
                <span :class="(form.notas || '').length > 50 ? 'text-red-500' : 'text-gray-400'">
                  {{ (form.notas || '').length }}/50
                </span>
              </label>
              <textarea v-model="form.notas" placeholder="Ej: número de folio, compañía aseguradora..." rows="2"
                maxlength="60"
                :class="[(form.notas || '').trim() === '' && form.notas ? 'border-red-400' : (form.notas || '').length > 50 ? 'border-red-400' : 'border-gray-200']"
                class="w-full rounded-xl border px-3 py-2.5 text-sm
                       focus:outline-none focus:border-[var(--color-acento)] transition resize-none"/>
            </div>

            <!-- Archivo adjunto -->
            <div class="mb-5">
              <label class="block text-xs font-semibold text-gray-600 mb-2">
                Archivo adjunto <span class="text-gray-400">(opcional)</span>
              </label>

              <div v-if="archivoBlob" class="flex items-center gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100 mb-2">
                <img v-if="esImagen && archivoPreview" :src="archivoPreview"
                  class="w-14 h-14 object-cover rounded-xl border border-gray-200 shrink-0" alt=""/>
                <div v-else class="w-14 h-14 rounded-xl border border-gray-200 bg-white flex flex-col items-center justify-center gap-1 shrink-0">
                  <i class="ti ti-file-text text-xl text-gray-400"/>
                  <span class="text-[9px] text-gray-400 uppercase font-bold">PDF</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-semibold text-gray-700 truncate">{{ archivoNombre }}</p>
                  <p class="text-[10px] text-gray-400 mt-0.5">Listo para subir</p>
                </div>
                <button @click="quitarArchivo"
                  class="w-8 h-8 rounded-full bg-red-100 text-red-500 flex items-center justify-center shrink-0">
                  <i class="ti ti-x text-sm"/>
                </button>
              </div>

              <div v-if="!archivoBlob" class="grid grid-cols-3 gap-2">
                <button @click="tomarFotoConCamara"
                  class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200
                         text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-camera text-xl text-gray-400"/> Cámara
                </button>
                <button @click="elegirDeGaleria"
                  class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200
                         text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-photo text-xl text-gray-400"/> Galería
                </button>
                <button @click="seleccionarArchivo"
                  class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200
                         text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-file text-xl text-gray-400"/> Archivo
                </button>
              </div>
            </div>

            <p v-if="errorForm" class="text-xs text-red-600 mb-3 flex items-center gap-1.5">
              <i class="ti ti-alert-circle shrink-0"/> {{ errorForm }}
            </p>

            <button @click="enviarDocumento" :disabled="store.enviando" class="btn-primary">
              <span v-if="store.enviando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
              {{ store.enviando ? 'Subiendo...' : (esRenovacion ? 'Renovar documento' : 'Subir documento') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ════════════════════════════════════════════════════════════════════════
         PREVIEW FULL-SCREEN: imagen / PDF
    ════════════════════════════════════════════════════════════════════════════ -->
    <Transition name="sheet">
      <div v-if="previewAbierto" class="fixed inset-0 z-[60] bg-black flex flex-col">
        <!-- Barra superior -->
        <div class="flex items-center gap-3 shrink-0 bg-black/90 border-b border-white/10"
             :style="`padding: max(1rem, env(safe-area-inset-top)) 1rem 0.75rem`">
          <button @click="cerrarPreview"
            class="w-9 h-9 rounded-full bg-white/15 flex items-center justify-center text-white shrink-0">
            <i class="ti ti-arrow-left text-lg"/>
          </button>
          <span class="flex-1 text-white text-sm font-semibold">Vista previa</span>
        </div>
        <!-- Contenido -->
        <div class="flex-1 overflow-hidden bg-gray-950 flex items-center justify-center">
          <!-- Imagen -->
          <img v-if="previewMime.startsWith('image/')"
               :src="previewUrl"
               class="max-w-full max-h-full object-contain"
               alt="Documento"/>
          <!-- PDF en Android: WebView no tiene visor nativo de PDFs -->
          <div v-else-if="previewEsPdf && esNativo"
               class="flex flex-col items-center justify-center gap-4 px-8 py-12 text-center">
            <div class="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center">
              <i class="ti ti-file-text text-3xl text-white/60"/>
            </div>
            <div>
              <p class="text-white text-sm font-semibold mb-1">No se puede previsualizar el PDF</p>
              <p class="text-white/50 text-xs leading-relaxed">
                Android no incluye un visor de PDF integrado.<br>
                Descarga el archivo con otra aplicación para abrirlo.
              </p>
            </div>
          </div>
          <!-- PDF en web / iframe -->
          <iframe v-else
                  :src="previewUrl"
                  class="w-full h-full border-0"/>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.doc-header {
  position: relative; overflow: hidden;
  background: var(--gradient-hero);
  padding: max(1.25rem, env(safe-area-inset-top)) 1rem 1.25rem;
}
.doc-header-pattern {
  position: absolute; inset: 0;
  background-image: radial-gradient(circle at 90% 10%, rgba(255,255,255,0.1) 0%, transparent 50%);
}
.doc-header-content {
  position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem;
}
.doc-header-subtitle {
  font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.65);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;
}
.doc-header-title { font-size: 1.375rem; font-weight: 800; color: white; line-height: 1.15; }
.doc-chips { display: flex; flex-direction: column; align-items: flex-end; gap: 0.375rem; flex-shrink: 0; }
.doc-chip {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.6875rem; font-weight: 700;
  border-radius: 999px; padding: 0.2rem 0.625rem; line-height: 1.4;
}
.doc-chip--green  { background: rgba(255,255,255,0.18); color: white;   border: 1px solid rgba(255,255,255,0.3); }
.doc-chip--yellow { background: rgba(251,191,36,0.25);  color: #FDE68A; border: 1px solid rgba(251,191,36,0.4); }
.doc-chip--red    { background: rgba(239,68,68,0.25);   color: #FECACA; border: 1px solid rgba(239,68,68,0.4); }

.doc-section-label {
  font-size: 0.6875rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9CA3AF; margin-bottom: 0.625rem;
}

.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from,   .sheet-leave-to     { transform: translateY(100%); }
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from,   .toast-leave-to     { opacity: 0; transform: translate(-50%, 8px); }
</style>
