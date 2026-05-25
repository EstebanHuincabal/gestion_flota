<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSolicitudesStore } from '@/stores/solicitudes.js'
import { Camera, CameraSource, CameraResultType } from '@capacitor/camera'
import BottomNav from '@/components/BottomNav.vue'

const store = useSolicitudesStore()

// ── Pull to refresh ───────────────────────────────────────────────────────────
let startY       = 0
const refreshing = ref(false)

function onTouchStart(e) { startY = e.touches[0].clientY }
async function onTouchEnd(e) {
  const diff = e.changedTouches[0].clientY - startY
  if (diff > 80 && !refreshing.value && window.scrollY === 0) {
    refreshing.value = true
    await store.cargarSolicitudes()
    refreshing.value = false
  }
}

// ── Historial colapsable ──────────────────────────────────────────────────────
const _histAbierto = ref(false)
const historialAbierto = computed(() =>
  store.resueltas.length <= 3 ? true : _histAbierto.value,
)
function toggleHistorial() { _histAbierto.value = !_histAbierto.value }

// ── Toast ──────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', tipo: 'ok' })
let toastTimer = null
function mostrarToast(mensaje, tipo = 'ok') {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, tipo }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3500)
}

// ── Modal Nueva Solicitud ─────────────────────────────────────────────────────
const modalNueva       = ref(false)
const paso             = ref(1)
const tipoSeleccionado = ref(null)
const fotoDataUrl      = ref(null)
const fotoBase64       = ref(null)
const errorForm        = ref('')

const form = ref({
  titulo:      '',
  descripcion: '',
  prioridad:   'media',
})

const TIPOS = [
  { value: 'mantencion',  label: 'Mantención',  icono: 'ti-tool',           color: '#534AB7', colorSuave: '#EEEDFE', descripcion: 'Falla mecánica o revisión necesaria' },
  { value: 'combustible', label: 'Combustible', icono: 'ti-gas-station',    color: '#B45309', colorSuave: '#FEF3C7', descripcion: 'Solicitar recarga o reportar consumo' },
  { value: 'incidencia',  label: 'Incidencia',  icono: 'ti-alert-triangle', color: '#A32D2D', colorSuave: '#FCEBEB', descripcion: 'Accidente, multa u otro problema' },
  { value: 'documento',   label: 'Documento',   icono: 'ti-file-plus',      color: '#16A34A', colorSuave: '#DCFCE7', descripcion: 'Subir o renovar un documento' },
]

const tipoActual = computed(() => TIPOS.find(t => t.value === tipoSeleccionado.value))

function abrirNuevaSolicitud() {
  paso.value             = 1
  tipoSeleccionado.value = null
  fotoDataUrl.value      = null
  fotoBase64.value       = null
  errorForm.value        = ''
  form.value             = { titulo: '', descripcion: '', prioridad: 'media' }
  modalNueva.value       = true
}

function cerrarNueva() { modalNueva.value = false }

async function elegirTipo(tipo) {
  tipoSeleccionado.value = tipo.value

  // «Documento» → lanza cámara directamente y cierra el modal
  if (tipo.value === 'documento') {
    cerrarNueva()
    await flujoDocumento()
    return
  }

  // Pre-rellenos por tipo
  if (tipo.value === 'combustible') {
    form.value.titulo    = 'Solicitud de combustible'
    form.value.prioridad = 'media'
  } else if (tipo.value === 'incidencia') {
    form.value.prioridad = 'alta'
  } else {
    form.value.titulo    = ''
    form.value.prioridad = 'media'
  }

  paso.value = 2
}

// Captura de foto con Capacitor Camera
async function tomarFoto() {
  try {
    const foto = await Camera.getPhoto({
      quality:            80,
      allowEditing:       false,
      resultType:         CameraResultType.DataUrl,
      source:             CameraSource.Prompt,
      promptLabelHeader:  'Foto del problema',
      promptLabelPhoto:   'Elegir de la galería',
      promptLabelPicture: 'Tomar foto',
    })
    fotoDataUrl.value = foto.dataUrl
    fotoBase64.value  = foto.dataUrl.split(',')[1]
  } catch {
    // Usuario canceló
  }
}

function quitarFoto() {
  fotoDataUrl.value = null
  fotoBase64.value  = null
}

// Flujo especial para tipo "documento"
async function flujoDocumento() {
  try {
    const foto = await Camera.getPhoto({
      quality:            90,
      allowEditing:       false,
      resultType:         CameraResultType.DataUrl,
      source:             CameraSource.Prompt,
      promptLabelHeader:  'Capturar documento',
      promptLabelPhoto:   'Elegir de la galería',
      promptLabelPicture: 'Tomar foto del documento',
    })
    const b64   = foto.dataUrl.split(',')[1]
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
    const blob  = new Blob([bytes], { type: 'image/jpeg' })

    const datos = {
      tipo:        'documento',
      titulo:      'Documento adjunto',
      descripcion: 'Documento capturado desde la app',
      prioridad:   'media',
    }
    const res = await store.crearSolicitud(datos, blob)
    if (res.success) {
      mostrarToast(
        res.offline
          ? 'Sin conexión. Se enviará cuando vuelva la señal.'
          : 'Documento enviado correctamente',
        res.offline ? 'offline' : 'ok',
      )
    } else {
      mostrarToast('Error al enviar el documento', 'error')
    }
  } catch {
    // Usuario canceló
  }
}

// Enviar solicitud desde el formulario paso 2
async function enviarSolicitud() {
  errorForm.value = ''
  const t = tipoSeleccionado.value
  const f = form.value

  if (!f.titulo || f.titulo.length < 5) {
    errorForm.value = 'El título debe tener al menos 5 caracteres.'
    return
  }
  if (t !== 'combustible' && f.descripcion.length < 10) {
    errorForm.value = 'La descripción debe tener al menos 10 caracteres.'
    return
  }
  if (t === 'incidencia' && !fotoBase64.value) {
    errorForm.value = 'Para incidencias se requiere una foto.'
    return
  }

  let foto = null
  if (fotoBase64.value) {
    const bytes = Uint8Array.from(atob(fotoBase64.value), c => c.charCodeAt(0))
    foto        = new Blob([bytes], { type: 'image/jpeg' })
  }

  const datos = {
    tipo:        t,
    titulo:      f.titulo,
    descripcion: f.descripcion,
    prioridad:   f.prioridad,
  }

  const res = await store.crearSolicitud(datos, foto)

  if (res.success) {
    cerrarNueva()
    mostrarToast(
      res.offline
        ? 'Sin conexión. Se enviará cuando vuelva la señal.'
        : 'Solicitud enviada correctamente',
      res.offline ? 'offline' : 'ok',
    )
  } else {
    errorForm.value = res.error || 'Error al enviar la solicitud.'
  }
}

// ── Modal Detalle Solicitud ───────────────────────────────────────────────────
const modalDetalle     = ref(false)
const solicitudDetalle = ref(null)

function verDetalle(sol) {
  solicitudDetalle.value = sol
  modalDetalle.value     = true
}

// ── Helpers de UI ─────────────────────────────────────────────────────────────
const ESTADOS = {
  pendiente:   { label: 'Pendiente',   color: '#185FA5', bg: '#E6F1FB' },
  en_revision: { label: 'En revisión', color: '#B45309', bg: '#FEF3C7' },
  aprobado:    { label: 'Aprobado',    color: '#085041', bg: '#E1F5EE' },
  rechazado:   { label: 'Rechazado',   color: '#791F1F', bg: '#FCEBEB' },
}

function badgeEstado(estado) {
  return ESTADOS[estado] || { label: estado, color: '#555', bg: '#eee' }
}

function tipoInfo(tipo) {
  return TIPOS.find(t => t.value === tipo) || { icono: 'ti-help', color: '#888', colorSuave: '#eee', label: tipo }
}

function tiempoDesde(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr).getTime()
  const min  = Math.floor(diff / 60000)
  if (min < 60)  return `hace ${min} min`
  const h    = Math.floor(min / 60)
  if (h < 24)   return `hace ${h}h`
  const d    = Math.floor(h / 24)
  if (d < 30)   return `hace ${d} días`
  const m    = Math.floor(d / 30)
  return `hace ${m} mes${m > 1 ? 'es' : ''}`
}

function formatFecha(isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleDateString('es-CL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ── Inicialización ────────────────────────────────────────────────────────────
onMounted(async () => {
  await store.cargarSolicitudes()
  _histAbierto.value = store.resueltas.length <= 3
})
</script>

<template>
  <div
    class="min-h-dvh bg-gray-50 pb-nav"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- ── Spinner pull-to-refresh ─────────────────────────────────────────── -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <header class="bg-white px-4 pt-safe pb-4 border-b border-gray-100">
      <h1 class="text-xl font-bold text-gray-800">Solicitudes</h1>
    </header>

    <!-- ── Skeleton inicial ───────────────────────────────────────────────── -->
    <div v-if="store.cargando && !store.solicitudes.length" class="px-4 mt-4 flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="h-20 rounded-2xl bg-gray-200 animate-pulse"/>
    </div>

    <template v-else>
      <div class="px-4 mt-4 flex flex-col gap-5">

        <!-- ── Estado vacío ─────────────────────────────────────────────── -->
        <div
          v-if="!store.solicitudes.length"
          class="flex flex-col items-center gap-3 py-16 text-gray-400"
        >
          <i class="ti ti-clipboard-list text-6xl text-gray-200"/>
          <p class="text-base font-medium">No tienes solicitudes</p>
          <p class="text-sm text-center text-gray-400">
            Usa el botón + para reportar un problema<br>o hacer una solicitud
          </p>
        </div>

        <!-- ── Solicitudes en proceso ────────────────────────────────────── -->
        <section v-if="store.pendientes.length">
          <h2 class="text-sm font-bold text-gray-700 mb-2">
            En proceso
            <span class="text-gray-400 font-normal">({{ store.pendientes.length }})</span>
          </h2>

          <div class="flex flex-col gap-2">
            <button
              v-for="sol in store.pendientes"
              :key="sol.id"
              @click="verDetalle(sol)"
              class="w-full text-left bg-white rounded-2xl p-4 border border-gray-200
                     hover:border-gray-300 hover:shadow-sm transition active:bg-gray-50 min-h-[44px]"
            >
              <div class="flex items-start gap-3">
                <!-- Ícono tipo -->
                <div
                  class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                  :style="`background: ${tipoInfo(sol.tipo).colorSuave}`"
                >
                  <i
                    class="ti text-base"
                    :class="tipoInfo(sol.tipo).icono"
                    :style="`color: ${tipoInfo(sol.tipo).color}`"
                  />
                </div>

                <!-- Contenido -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-semibold text-gray-800 truncate">{{ sol.titulo }}</p>
                    <span
                      class="shrink-0 text-[10px] font-semibold rounded-full px-2 py-0.5"
                      :style="`color: ${badgeEstado(sol.estado).color}; background: ${badgeEstado(sol.estado).bg}`"
                    >
                      {{ badgeEstado(sol.estado).label }}
                    </span>
                  </div>
                  <p class="text-xs text-gray-400 mt-0.5">
                    {{ tipoInfo(sol.tipo).label }} · {{ tiempoDesde(sol.created_at) }}
                  </p>
                  <p v-if="sol.respuesta" class="text-xs text-gray-500 mt-1 italic truncate">
                    "{{ sol.respuesta }}"
                  </p>
                </div>
              </div>
            </button>
          </div>
        </section>

        <!-- ── Historial ─────────────────────────────────────────────────── -->
        <section v-if="store.resueltas.length">
          <button
            @click="toggleHistorial"
            class="flex items-center justify-between w-full text-sm font-bold text-gray-700 mb-2 min-h-[44px]"
          >
            <span>Historial</span>
            <svg
              class="w-4 h-4 text-gray-400 transition-transform"
              :class="{ 'rotate-180': historialAbierto }"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <Transition name="historial">
            <div v-if="historialAbierto" class="flex flex-col gap-1.5">
              <button
                v-for="sol in store.resueltas"
                :key="sol.id"
                @click="verDetalle(sol)"
                class="w-full text-left bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-100
                       flex items-center gap-3 min-h-[44px] active:bg-gray-100 transition"
              >
                <div
                  class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                  :style="`background: ${tipoInfo(sol.tipo).colorSuave}`"
                >
                  <i
                    class="ti text-xs"
                    :class="tipoInfo(sol.tipo).icono"
                    :style="`color: ${tipoInfo(sol.tipo).color}`"
                  />
                </div>
                <p class="flex-1 text-sm text-gray-600 truncate">{{ sol.titulo }}</p>
                <span
                  class="shrink-0 text-[10px] font-semibold rounded-full px-2 py-0.5"
                  :style="`color: ${badgeEstado(sol.estado).color}; background: ${badgeEstado(sol.estado).bg}`"
                >
                  {{ badgeEstado(sol.estado).label }}
                </span>
                <span class="text-[10px] text-gray-400 shrink-0">{{ tiempoDesde(sol.created_at) }}</span>
              </button>
            </div>
          </Transition>
        </section>

      </div>
    </template>

    <!-- ── FAB ───────────────────────────────────────────────────────────── -->
    <button
      @click="abrirNuevaSolicitud"
      class="fixed right-4 rounded-full px-5 py-3 shadow-lg flex items-center gap-2 text-white font-medium z-40"
      :style="`bottom: calc(72px + env(safe-area-inset-bottom)); background: var(--color-acento)`"
    >
      <i class="ti ti-plus text-lg"/>
      Nueva
    </button>

    <!-- ── BottomNav ──────────────────────────────────────────────────────── -->
    <BottomNav />

    <!-- ── Toast ─────────────────────────────────────────────────────────── -->
    <Transition name="toast">
      <div
        v-if="toast.visible"
        class="fixed left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl shadow-lg
               text-sm font-medium text-white flex items-center gap-2"
        :class="{
          'bg-gray-800':   toast.tipo === 'ok',
          'bg-orange-600': toast.tipo === 'offline',
          'bg-red-600':    toast.tipo === 'error',
        }"
        style="bottom: calc(90px + env(safe-area-inset-bottom))"
      >
        <i v-if="toast.tipo === 'ok'"      class="ti ti-circle-check"/>
        <i v-else-if="toast.tipo === 'offline'" class="ti ti-wifi-off"/>
        <i v-else                           class="ti ti-alert-circle"/>
        {{ toast.mensaje }}
      </div>
    </Transition>


    <!-- ═══════════════════════════════════════════════════════════════════════
         MODAL: NUEVA SOLICITUD
    ═══════════════════════════════════════════════════════════════════════════ -->
    <Transition name="sheet">
      <div v-if="modalNueva" class="fixed inset-0 z-50 flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/50" @click="cerrarNueva"/>

        <div
          class="relative bg-white rounded-t-2xl scroll-hidden"
          :style="paso === 1
            ? 'height: min(80vh, 80dvh); padding-bottom: env(safe-area-inset-bottom, 0px)'
            : 'max-height: min(85vh, 85dvh); padding-bottom: env(safe-area-inset-bottom, 0px)'"
        >
          <!-- Handle -->
          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-white z-10">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>

          <!-- ── Paso 1: elegir tipo ─────────────────────────────────────── -->
          <div v-if="paso === 1" class="px-4 pb-6">
            <h2 class="text-base font-bold text-gray-800 mb-5 text-center">Nueva solicitud</h2>

            <div class="grid grid-cols-2 gap-3 mb-6">
              <button
                v-for="tipo in TIPOS"
                :key="tipo.value"
                @click="elegirTipo(tipo)"
                class="rounded-2xl p-4 text-left border border-transparent transition active:scale-95 min-h-[44px]"
                :style="`background: ${tipo.colorSuave}`"
              >
                <i
                  class="ti text-2xl block mb-2"
                  :class="tipo.icono"
                  :style="`color: ${tipo.color}`"
                />
                <p class="text-sm font-bold" :style="`color: ${tipo.color}`">{{ tipo.label }}</p>
                <p class="text-xs mt-0.5 text-gray-500">{{ tipo.descripcion }}</p>
              </button>
            </div>

            <button
              @click="cerrarNueva"
              class="w-full py-3 rounded-xl text-sm font-medium text-gray-500 bg-gray-100 min-h-[44px]"
            >
              Cancelar
            </button>
          </div>

          <!-- ── Paso 2: formulario ─────────────────────────────────────── -->
          <div v-else class="px-4 pb-6">
            <!-- Header con volver -->
            <div class="flex items-center gap-3 mb-5">
              <button
                @click="paso = 1"
                class="p-2 -ml-1 text-gray-500 min-h-[44px] min-w-[44px] flex items-center justify-center"
              >
                <i class="ti ti-arrow-left text-lg"/>
              </button>
              <div class="flex items-center gap-2">
                <i
                  class="ti text-xl"
                  :class="tipoActual?.icono"
                  :style="`color: ${tipoActual?.color}`"
                />
                <h2 class="text-base font-bold text-gray-800">{{ tipoActual?.label }}</h2>
              </div>
            </div>

            <!-- Título -->
            <div class="mb-4">
              <label class="block text-xs font-semibold text-gray-600 mb-1">
                Título <span class="text-red-400">*</span>
              </label>
              <input
                v-model="form.titulo"
                type="text"
                placeholder="Describe brevemente el problema"
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                       focus:outline-none focus:border-[var(--color-acento)] transition"
                :disabled="tipoSeleccionado === 'combustible'"
              />
            </div>

            <!-- Descripción -->
            <div class="mb-4">
              <label class="block text-xs font-semibold text-gray-600 mb-1">
                Descripción
                <span v-if="tipoSeleccionado !== 'combustible'" class="text-red-400">*</span>
              </label>
              <textarea
                v-model="form.descripcion"
                placeholder="Más detalles sobre el problema..."
                rows="3"
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                       focus:outline-none focus:border-[var(--color-acento)] transition resize-none"
              />
            </div>

            <!-- Prioridad (no para combustible) -->
            <div v-if="tipoSeleccionado !== 'combustible'" class="mb-4">
              <label class="block text-xs font-semibold text-gray-600 mb-2">Prioridad</label>
              <div class="flex gap-2">
                <button
                  v-for="p in ['baja', 'media', 'alta']"
                  :key="p"
                  @click="form.prioridad = p"
                  class="flex-1 py-2 rounded-xl text-xs font-semibold border transition min-h-[44px]"
                  :class="form.prioridad === p
                    ? 'text-white border-transparent'
                    : 'bg-white text-gray-500 border-gray-200'"
                  :style="form.prioridad === p ? `background: var(--color-acento)` : ''"
                >
                  {{ p.charAt(0).toUpperCase() + p.slice(1) }}
                </button>
              </div>
            </div>

            <!-- Foto -->
            <div class="mb-5">
              <label class="block text-xs font-semibold text-gray-600 mb-2">
                Foto
                <span v-if="tipoSeleccionado === 'incidencia'" class="text-red-400">* (requerida)</span>
                <span v-else class="text-gray-400">(opcional)</span>
              </label>

              <div v-if="!fotoDataUrl" class="flex gap-2">
                <button
                  @click="tomarFoto"
                  class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl
                         border border-gray-200 text-sm text-gray-600 bg-white min-h-[44px] active:bg-gray-50"
                >
                  <i class="ti ti-camera"/>
                  Cámara / Galería
                </button>
              </div>

              <div v-else class="flex items-center gap-3">
                <img
                  :src="fotoDataUrl"
                  class="w-20 h-20 object-cover rounded-xl border border-gray-200"
                  alt="Vista previa"
                />
                <button
                  @click="quitarFoto"
                  class="w-8 h-8 rounded-full bg-red-100 text-red-500 flex items-center justify-center"
                >
                  <i class="ti ti-x text-sm"/>
                </button>
              </div>
            </div>

            <!-- Error formulario -->
            <p v-if="errorForm" class="text-xs text-red-600 mb-3 flex items-center gap-1">
              <i class="ti ti-alert-circle"/>
              {{ errorForm }}
            </p>

            <!-- Botón enviar -->
            <button
              @click="enviarSolicitud"
              :disabled="store.enviando"
              class="w-full py-3.5 rounded-xl text-white text-sm font-semibold
                     flex items-center justify-center gap-2 transition min-h-[44px]"
              :style="`background: ${store.enviando ? '#9ca3af' : 'var(--color-acento)'}`"
            >
              <span
                v-if="store.enviando"
                class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
              />
              {{ store.enviando ? 'Enviando...' : 'Enviar solicitud' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>


    <!-- ═══════════════════════════════════════════════════════════════════════
         MODAL: DETALLE SOLICITUD
    ═══════════════════════════════════════════════════════════════════════════ -->
    <Transition name="sheet">
      <div v-if="modalDetalle && solicitudDetalle" class="fixed inset-0 z-50 flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/50" @click="modalDetalle = false"/>

        <div
          class="relative bg-white rounded-t-2xl scroll-hidden"
          style="max-height: min(60vh, 60dvh); padding-bottom: env(safe-area-inset-bottom, 0px)"
        >
          <!-- Handle -->
          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-white z-10">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>

          <div class="px-4 pb-6">
            <!-- Tipo + Título -->
            <div class="flex items-center gap-3 mb-3">
              <div
                class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                :style="`background: ${tipoInfo(solicitudDetalle.tipo).colorSuave}`"
              >
                <i
                  class="ti text-xl"
                  :class="tipoInfo(solicitudDetalle.tipo).icono"
                  :style="`color: ${tipoInfo(solicitudDetalle.tipo).color}`"
                />
              </div>
              <div>
                <p class="text-base font-bold text-gray-800 leading-tight">{{ solicitudDetalle.titulo }}</p>
                <p class="text-xs text-gray-400">
                  {{ tipoInfo(solicitudDetalle.tipo).label }}
                  <template v-if="solicitudDetalle.prioridad && solicitudDetalle.prioridad !== 'media'">
                    · {{ solicitudDetalle.prioridad.charAt(0).toUpperCase() + solicitudDetalle.prioridad.slice(1) }} prioridad
                  </template>
                </p>
              </div>
            </div>

            <!-- Estado -->
            <div class="flex items-center gap-2 mb-3">
              <span class="text-xs text-gray-500">Estado:</span>
              <span
                class="text-[11px] font-semibold rounded-full px-2.5 py-0.5"
                :style="`color: ${badgeEstado(solicitudDetalle.estado).color}; background: ${badgeEstado(solicitudDetalle.estado).bg}`"
              >
                {{ badgeEstado(solicitudDetalle.estado).label }}
              </span>
            </div>

            <!-- Fecha -->
            <p class="text-xs text-gray-400 mb-3">
              Enviada: {{ tiempoDesde(solicitudDetalle.created_at) }}
              ({{ formatFecha(solicitudDetalle.created_at) }})
            </p>

            <!-- Descripción -->
            <div v-if="solicitudDetalle.descripcion" class="mb-3">
              <p class="text-xs font-semibold text-gray-600 mb-1">Descripción:</p>
              <p class="text-sm text-gray-700 italic">"{{ solicitudDetalle.descripcion }}"</p>
            </div>

            <!-- Foto -->
            <div v-if="solicitudDetalle.foto_url" class="mb-3">
              <img
                :src="solicitudDetalle.foto_url"
                class="w-20 h-20 object-cover rounded-xl border border-gray-200"
                alt="Foto adjunta"
              />
            </div>

            <!-- Respuesta del administrador -->
            <div class="mb-5">
              <p class="text-xs font-semibold text-gray-600 mb-1">Respuesta del administrador:</p>
              <div v-if="solicitudDetalle.respuesta">
                <p class="text-sm text-gray-700 italic">"{{ solicitudDetalle.respuesta }}"</p>
              </div>
              <div v-else class="flex items-center gap-2 text-gray-400">
                <i class="ti ti-clock text-base"/>
                <p class="text-xs">Esperando respuesta del administrador...</p>
              </div>
            </div>

            <!-- Cerrar -->
            <button
              @click="modalDetalle = false"
              class="w-full py-3 rounded-xl text-sm font-medium text-gray-600 bg-gray-100 min-h-[44px]"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.pt-safe {
  padding-top: max(1rem, env(safe-area-inset-top));
}
.pb-6 {
  padding-bottom: max(1.5rem, env(safe-area-inset-bottom));
}

/* Bottom sheet */
.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from,   .sheet-leave-to     { transform: translateY(100%); }

/* Historial colapsable */
.historial-enter-active, .historial-leave-active { transition: all 0.25s ease; }
.historial-enter-from,   .historial-leave-to     { opacity: 0; transform: translateY(-6px); }

/* Toast */
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from,   .toast-leave-to     { opacity: 0; transform: translate(-50%, 8px); }
</style>
