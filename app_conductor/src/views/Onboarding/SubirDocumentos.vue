<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Preferences } from '@capacitor/preferences'
import { Camera, CameraSource, CameraResultType } from '@capacitor/camera'
import { useDocumentosStore, TIPOS_CONDUCTOR, TIPOS_VEHICULO } from '@/stores/documentos.js'
import { useAuthStore } from '@/stores/auth.js'
import { getModulos } from '@/services/permisos.js'
import { validarFechaVigente, validarLicencia } from '@/utils/validators.js'

const store  = useDocumentosStore()
const auth   = useAuthStore()
const router = useRouter()

const vehiculo = computed(() => auth.usuario?.vehiculo_asignado || null)
const TODOS_TIPOS = [...TIPOS_CONDUCTOR, ...TIPOS_VEHICULO]

// ── Paso de licencia obligatorio si aún no la tiene ─────────────────────────
const requiereLicencia   = computed(() => !!auth.usuario?.requiere_licencia)
const licenciaForm       = ref({ numero: '', error: '' })
const guardandoLicencia  = ref(false)
const licenciaCompletada = ref(false)

async function guardarLicencia() {
  licenciaForm.value.error = ''
  const num = licenciaForm.value.numero.trim().toUpperCase()
  const val = validarLicencia(num)
  if (!val.valido) {
    licenciaForm.value.error = val.error
    return
  }
  guardandoLicencia.value = true
  try {
    const { apiFetch } = await import('@/services/api.js')
    await apiFetch('/api/conductor/perfil/', {
      method: 'PATCH',
      body: JSON.stringify({ licencia: num }),
    })
    // Actualizar usuario en Preferences y store
    const u = { ...auth.usuario, requiere_licencia: false }
    auth.usuario = u
    await Preferences.set({ key: 'usuario', value: JSON.stringify(u) })
    licenciaCompletada.value = true
  } catch (e) {
    licenciaForm.value.error = 'No se pudo guardar. Intenta de nuevo.'
  } finally {
    guardandoLicencia.value = false
  }
}

// ── Navegar al terminar el onboarding ────────────────────────────────────────
const errorContinuar  = ref('')
const guardandoContinuar = ref(false)

async function continuar() {
  errorContinuar.value = ''

  // Todos los documentos son obligatorios: los del conductor siempre y los del
  // vehículo cuando hay uno asignado.
  const requeridos = [...TIPOS_CONDUCTOR, ...(vehiculo.value ? TIPOS_VEHICULO : [])]
  const faltantes  = requeridos.filter(t => !store.docPorTipo[t.value])
  if (faltantes.length) {
    errorContinuar.value = `Faltan documentos por subir: ${faltantes.map(t => t.label).join(', ')}.`
    return
  }

  guardandoContinuar.value = true
  try {
    await _completarYRedirigir()
  } finally {
    guardandoContinuar.value = false
  }
}

// Marca el onboarding como completado (primer_login = false) y entra a la app.
async function _completarYRedirigir() {
  try {
    const { apiFetch } = await import('@/services/api.js')
    await apiFetch('/api/conductor/perfil/', {
      method: 'PATCH',
      body: JSON.stringify({ completar_onboarding: true }),
    })
  } catch {
    // fail-silent: si falla el API igual dejamos pasar, el guard se actualiza localmente
  }
  const u = { ...auth.usuario, primer_login: false }
  auth.usuario = u
  await Preferences.set({ key: 'usuario', value: JSON.stringify(u) })

  let modulos = []
  try {
    const { value } = await Preferences.get({ key: 'plan_modulos' })
    const parsed = JSON.parse(value || '[]')
    modulos = Array.isArray(parsed) ? parsed : []
  } catch {}
  if (modulos.includes('rutas'))        return router.replace({ name: 'rutas' })
  if (modulos.includes('solicitudes'))  return router.replace({ name: 'solicitudes' })
  if (modulos.includes('mantenciones')) return router.replace({ name: 'mantencion' })
  if (modulos.includes('documentos'))   return router.replace({ name: 'documentos' })
  router.replace({ name: 'ajustes' })   // siempre disponible
}

// ── Helpers UI ───────────────────────────────────────────────────────────────
const ESTADOS = {
  vigente:         { label: 'Vigente',    color: '#085041', bg: '#E1F5EE' },
  por_vencer:      { label: 'Por vencer', color: '#B45309', bg: '#FEF3C7' },
  vencido:         { label: 'Vencido',    color: '#791F1F', bg: '#FCEBEB' },
  sin_vencimiento: { label: 'Sin venc.',  color: '#374151', bg: '#F3F4F6' },
}
function badgeEstado(e) { return ESTADOS[e] || { label: e, color: '#555', bg: '#eee' } }
function formatFecha(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// ── Toast ────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', tipo: 'ok' })
let toastTimer = null
function mostrarToast(mensaje, tipo = 'ok') {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, tipo }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3000)
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

const tipoActual = computed(() =>
  TODOS_TIPOS.find(t => t.value === (tipoForzado.value || form.value.tipo)),
)

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

async function tomarFotoConCamara() {
  try {
    const foto = await Camera.getPhoto({ quality: 90, allowEditing: false, resultType: CameraResultType.DataUrl, source: CameraSource.Camera })
    _procesarDataUrl(foto.dataUrl)
  } catch (e) {
    if (e?.message?.includes('denied') || e?.message?.includes('permission') || e?.message?.includes('User cancelled')) {
      mostrarToast('Permiso de cámara denegado. Actívalo en la configuración del dispositivo.', 'error')
    }
  }
}
async function elegirDeGaleria() {
  try {
    const foto = await Camera.getPhoto({ quality: 90, allowEditing: false, resultType: CameraResultType.DataUrl, source: CameraSource.Photos })
    _procesarDataUrl(foto.dataUrl)
  } catch (e) {
    if (e?.message?.includes('denied') || e?.message?.includes('permission') || e?.message?.includes('User cancelled')) {
      mostrarToast('Permiso de galería denegado. Actívalo en la configuración del dispositivo.', 'error')
    }
  }
}
function seleccionarArchivo() { inputArchivo.value?.click() }
const MAX_ARCHIVO_MB = 10
function onArchivoSeleccionado(e) {
  const file = e.target.files?.[0]; if (!file) return
  if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
    mostrarToast('Solo se permiten archivos PDF o imágenes.', 'error')
    e.target.value = ''
    return
  }
  if (file.size > MAX_ARCHIVO_MB * 1024 * 1024) {
    mostrarToast(`El archivo no puede superar ${MAX_ARCHIVO_MB} MB.`, 'error')
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

async function enviarDocumento() {
  errorForm.value = ''
  if (!form.value.tipo) { errorForm.value = 'Selecciona el tipo de documento.'; return }
  const usuario = auth.usuario
  if (!usuario) { errorForm.value = 'Sesión no disponible.'; return }

  // Validar que fecha de vencimiento no sea anterior a la de emisión
  if (form.value.fechaEmision && form.value.fechaVencimiento) {
    if (form.value.fechaVencimiento < form.value.fechaEmision) {
      errorForm.value = 'La fecha de vencimiento no puede ser anterior a la fecha de emisión.'
      return
    }
  }

  // Validar fecha de vencimiento >= hoy
  if (form.value.fechaVencimiento) {
    const r = validarFechaVigente(form.value.fechaVencimiento)
    if (!r.valido) { errorForm.value = r.error; return }
  }

  const notas = form.value.notas || ''
  if (notas && notas.trim() === '') { errorForm.value = 'Las notas no pueden contener solo espacios en blanco.'; return }
  if (notas.length > 50) { errorForm.value = 'Las notas no pueden superar 50 caracteres.'; return }

  // El archivo adjunto es obligatorio (foto o PDF del documento).
  if (!archivoBlob.value) { errorForm.value = 'Debes adjuntar el archivo del documento (foto o PDF).'; return }

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
    mostrarToast('Documento subido correctamente')
  } else {
    errorForm.value = res.error || 'Error al subir el documento.'
  }
}

onMounted(async () => {
  // Si el plan no incluye el módulo de documentos, no se solicitan: se completa
  // el onboarding automáticamente y se entra a la app.
  const modulos = await getModulos()
  if (!modulos.includes('documentos')) {
    await _completarYRedirigir()
    return
  }
  store.cargarDocumentos()
})
</script>

<template>
  <div class="min-h-dvh bg-gray-50 flex flex-col">

    <!-- ── Paso 0: N° de licencia obligatorio ────────────────────────────────── -->
    <div v-if="requiereLicencia && !licenciaCompletada"
      class="min-h-dvh flex flex-col items-center justify-center px-6 pb-8"
      style="background: var(--gradient-hero)">
      <div class="w-full max-w-sm">
        <div class="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center mb-5 mx-auto">
          <i class="ti ti-id text-3xl text-white"/>
        </div>
        <h1 class="text-white text-2xl font-bold text-center mb-2">Número de licencia</h1>
        <p class="text-white/70 text-sm text-center mb-8">
          Antes de continuar necesitamos tu número de licencia de conducir.
        </p>
        <div class="bg-white rounded-2xl p-5 shadow-xl">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">N° de licencia</label>
          <input v-model="licenciaForm.numero" type="text" placeholder="Ej: ABC1234567890" maxlength="13"
            class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm font-mono uppercase focus:outline-none focus:border-[var(--color-acento)]"
            :class="licenciaForm.error ? 'border-red-300' : ''"
            @keyup.enter="guardarLicencia"/>
          <p v-if="licenciaForm.error" class="text-xs text-red-500 mt-1">{{ licenciaForm.error }}</p>
          <button @click="guardarLicencia" :disabled="guardandoLicencia"
            class="w-full mt-4 py-3 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2"
            style="background: var(--color-acento)">
            <span v-if="guardandoLicencia" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"/>
            <span v-else>Guardar y continuar <i class="ti ti-arrow-right"/></span>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Documentos (solo si la licencia ya está completa) ─────────────────── -->
    <template v-if="!requiereLicencia || licenciaCompletada">

    <!-- ── Banner de onboarding ──────────────────────────────────────────────── -->
    <header class="ob-header">
      <div class="ob-header-pattern" aria-hidden="true"/>
      <div class="ob-header-content">
        <div class="ob-step-badge">Paso 1 · Perfil</div>
        <h1 class="ob-title">Completa tu documentación</h1>
        <p class="ob-subtitle">
          Sube tu licencia y los documentos de tu vehículo para que el equipo pueda verificar tu perfil.
        </p>
      </div>
    </header>

    <!-- ── Contenido ──────────────────────────────────────────────────────────── -->
    <div class="flex-1 px-4 py-4 flex flex-col gap-5">

      <div v-if="store.cargando && !store.documentos.length" class="flex flex-col gap-3">
        <div v-for="i in 4" :key="i" class="h-24 rounded-2xl bg-gray-200 animate-pulse"/>
      </div>

      <template v-else>

        <!-- Sección conductor -->
        <section>
          <p class="ob-section-label">Mi documentación</p>
          <div class="flex flex-col gap-3">
            <div v-for="tipo in TIPOS_CONDUCTOR" :key="tipo.value"
              class="bg-white rounded-2xl border border-gray-100 p-4" style="box-shadow: var(--shadow-sm)">
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
                <span v-else class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5 text-amber-700 bg-amber-50">
                  Pendiente
                </span>
              </div>
              <div v-if="store.docPorTipo[tipo.value]" class="flex gap-4 mb-3">
                <div v-if="store.docPorTipo[tipo.value].fecha_vencimiento">
                  <p class="text-[10px] text-gray-400 mb-0.5">Vencimiento</p>
                  <p class="text-xs font-semibold" :style="`color: ${badgeEstado(store.docPorTipo[tipo.value].estado).color}`">
                    {{ formatFecha(store.docPorTipo[tipo.value].fecha_vencimiento) }}
                  </p>
                </div>
              </div>
              <button @click="abrirModal(tipo.value, false)"
                class="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl border
                       text-sm font-semibold min-h-[44px] active:opacity-75 transition"
                :style="store.docPorTipo[tipo.value]
                  ? `background: ${tipo.colorSuave}; border-color: ${tipo.color}40; color: ${tipo.color}`
                  : `background: ${tipo.colorSuave}; color: ${tipo.color}`">
                <i :class="store.docPorTipo[tipo.value] ? 'ti ti-refresh' : 'ti ti-upload'"/>
                {{ store.docPorTipo[tipo.value] ? 'Actualizar' : 'Subir' }}
              </button>
            </div>
          </div>
        </section>

        <!-- Sección vehículo -->
        <section>
          <p class="ob-section-label">
            Vehículo
            <span v-if="vehiculo" class="text-gray-600 normal-case font-bold ml-1">
              {{ vehiculo.patente }}
            </span>
          </p>

          <div v-if="!vehiculo"
            class="bg-white rounded-2xl border border-gray-100 p-4 flex items-center gap-3"
            style="box-shadow: var(--shadow-sm)">
            <i class="ti ti-car text-xl text-gray-300 shrink-0"/>
            <p class="text-xs text-gray-400">Sin vehículo asignado — el administrador debe asignarte uno.</p>
          </div>

          <div v-else class="flex flex-col gap-3">
            <div v-for="tipo in TIPOS_VEHICULO" :key="tipo.value"
              class="bg-white rounded-2xl border border-gray-100 p-4" style="box-shadow: var(--shadow-sm)">
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
                <span v-else class="shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-0.5 text-amber-700 bg-amber-50">
                  Pendiente
                </span>
              </div>
              <button @click="abrirModal(tipo.value, true)"
                class="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl border
                       text-sm font-semibold min-h-[44px] active:opacity-75 transition"
                :style="store.docPorTipo[tipo.value]
                  ? `background: ${tipo.colorSuave}; border-color: ${tipo.color}40; color: ${tipo.color}`
                  : `background: ${tipo.colorSuave}; color: ${tipo.color}`">
                <i :class="store.docPorTipo[tipo.value] ? 'ti ti-refresh' : 'ti ti-upload'"/>
                {{ store.docPorTipo[tipo.value] ? 'Actualizar' : 'Subir' }}
              </button>
            </div>
          </div>
        </section>

      </template>
    </div>

    <!-- ── Pie con botón Continuar ──────────────────────────────────────────── -->
    <div class="px-4 pb-6 pt-3 bg-white border-t border-gray-100"
         style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom))">
      <!-- Error si intenta continuar sin licencia -->
      <p v-if="errorContinuar" class="text-xs text-red-500 text-center mb-2 font-medium">
        <i class="ti ti-alert-circle mr-1"/>{{ errorContinuar }}
      </p>

      <button @click="continuar" :disabled="guardandoContinuar" class="btn-primary">
        <span v-if="guardandoContinuar" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin mr-2"/>
        <span v-else>Finalizar registro <i class="ti ti-check ml-1"/></span>
      </button>
      <p class="text-center text-xs text-gray-400 mt-3">
        Debes subir <strong>todos los documentos</strong> para finalizar tu registro.
      </p>
    </div>

    <!-- Input archivo oculto -->
    <input ref="inputArchivo" type="file" accept=".pdf,image/*" class="hidden" @change="onArchivoSeleccionado"/>

    <!-- Toast -->
    <Transition name="toast">
      <div v-if="toast.visible"
        class="fixed left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl shadow-lg
               text-sm font-medium text-white flex items-center gap-2"
        :class="toast.tipo === 'error' ? 'bg-red-600' : 'bg-gray-800'"
        style="bottom: calc(1.5rem + env(safe-area-inset-bottom))">
        <i :class="toast.tipo === 'error' ? 'ti ti-alert-circle' : 'ti ti-circle-check'"/>
        {{ toast.mensaje }}
      </div>
    </Transition>

    <!-- ════════════════════════════════════════════════════════════════════════
         MODAL: SUBIR DOCUMENTO
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
            <div class="flex items-center gap-3 mb-5">
              <div v-if="tipoActual" class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                   :style="`background: ${tipoActual.colorSuave}`">
                <i class="ti text-lg" :class="tipoActual.icono" :style="`color: ${tipoActual.color}`"/>
              </div>
              <div>
                <h2 class="text-base font-bold text-gray-800 leading-tight">
                  {{ store.docPorTipo[form.tipo] ? 'Actualizar' : 'Subir' }} documento
                </h2>
                <p v-if="tipoActual" class="text-xs text-gray-400">{{ tipoActual.label }}</p>
                <p v-if="esDocVehiculo && vehiculo" class="text-xs font-semibold mt-0.5"
                   :style="`color: ${tipoActual?.color}`">
                  {{ vehiculo.patente }} · {{ vehiculo.marca }} {{ vehiculo.modelo }}
                </p>
              </div>
            </div>

            <div class="flex gap-3 mb-4">
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">Fecha de emisión</label>
                <input v-model="form.fechaEmision" type="date"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:border-[var(--color-acento)] transition bg-white"/>
              </div>
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">Fecha de vencimiento</label>
                <input v-model="form.fechaVencimiento" type="date"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:border-[var(--color-acento)] transition bg-white"/>
              </div>
            </div>

            <div class="mb-4">
              <label class="flex items-center justify-between text-xs font-semibold text-gray-600 mb-1">
                <span>Notas <span class="text-gray-400 font-normal">(opcional)</span></span>
                <span :class="(form.notas || '').length > 50 ? 'text-red-500' : 'text-gray-400'">
                  {{ (form.notas || '').length }}/50
                </span>
              </label>
              <textarea v-model="form.notas" placeholder="Ej: número de folio, compañía aseguradora..." rows="2" maxlength="60"
                :class="[(form.notas || '').trim() === '' && form.notas ? 'border-red-400' : (form.notas || '').length > 50 ? 'border-red-400' : 'border-gray-200']"
                class="w-full rounded-xl border px-3 py-2.5 text-sm focus:outline-none focus:border-[var(--color-acento)] transition resize-none"/>
            </div>

            <div class="mb-5">
              <label class="block text-xs font-semibold text-gray-600 mb-2">Archivo adjunto <span class="text-red-500">*</span></label>
              <div v-if="archivoBlob" class="flex items-center gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100 mb-2">
                <img v-if="esImagen && archivoPreview" :src="archivoPreview" class="w-14 h-14 object-cover rounded-xl border border-gray-200 shrink-0" alt=""/>
                <div v-else class="w-14 h-14 rounded-xl border border-gray-200 bg-white flex flex-col items-center justify-center gap-1 shrink-0">
                  <i class="ti ti-file-text text-xl text-gray-400"/>
                  <span class="text-[9px] text-gray-400 uppercase font-bold">PDF</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-semibold text-gray-700 truncate">{{ archivoNombre }}</p>
                </div>
                <button @click="quitarArchivo" class="w-8 h-8 rounded-full bg-red-100 text-red-500 flex items-center justify-center shrink-0">
                  <i class="ti ti-x text-sm"/>
                </button>
              </div>
              <div v-if="!archivoBlob" class="grid grid-cols-3 gap-2">
                <button @click="tomarFotoConCamara" class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200 text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-camera text-xl text-gray-400"/> Cámara
                </button>
                <button @click="elegirDeGaleria" class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200 text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-photo text-xl text-gray-400"/> Galería
                </button>
                <button @click="seleccionarArchivo" class="flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl border border-gray-200 text-[11px] font-semibold text-gray-600 bg-white min-h-[60px] active:bg-gray-50 transition">
                  <i class="ti ti-file text-xl text-gray-400"/> Archivo
                </button>
              </div>
            </div>

            <p v-if="errorForm" class="text-xs text-red-600 mb-3 flex items-center gap-1.5">
              <i class="ti ti-alert-circle shrink-0"/> {{ errorForm }}
            </p>

            <button @click="enviarDocumento" :disabled="store.enviando" class="btn-primary">
              <span v-if="store.enviando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
              {{ store.enviando ? 'Subiendo...' : (store.docPorTipo[form.tipo] ? 'Actualizar documento' : 'Subir documento') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    </template><!-- fin v-if licencia completa -->

  </div>
</template>

<style scoped>
.ob-header {
  position: relative; overflow: hidden;
  background: var(--gradient-hero);
  padding: max(2rem, env(safe-area-inset-top, 2rem)) 1.25rem 1.5rem;
}
.ob-header-pattern {
  position: absolute; inset: 0;
  background-image: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.12) 0%, transparent 55%);
}
.ob-header-content { position: relative; }
.ob-step-badge {
  display: inline-block; font-size: 0.6875rem; font-weight: 700;
  color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.2); border-radius: 999px;
  padding: 0.2rem 0.75rem; margin-bottom: 0.6rem;
}
.ob-title { font-size: 1.5rem; font-weight: 800; color: white; line-height: 1.2; margin-bottom: 0.5rem; }
.ob-subtitle { font-size: 0.8125rem; color: rgba(255,255,255,0.75); line-height: 1.5; }
.ob-section-label {
  font-size: 0.6875rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9CA3AF; margin-bottom: 0.625rem;
}

.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from,   .sheet-leave-to     { transform: translateY(100%); }
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from,   .toast-leave-to     { opacity: 0; transform: translate(-50%, 8px); }
</style>
