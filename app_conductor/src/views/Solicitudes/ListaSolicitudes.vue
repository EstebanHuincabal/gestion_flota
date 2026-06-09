<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSolicitudesStore } from '@/stores/solicitudes.js'
import { usePermisos } from '@/composables/usePermisos.js'
import { Camera, CameraSource, CameraResultType } from '@capacitor/camera'
import BottomNav from '@/components/BottomNav.vue'
import { agruparPorFecha } from '@/utils/formato.js'

const router = useRouter()
const store  = useSolicitudesStore()
const { cargando: cargandoPermisos } = usePermisos()

// ── Notificación tiempo real ──────────────────────────────────────────────────
// Cuando llega un evento WebSocket, mostramos un toast informativo
watch(() => store.actualizadaId, (id) => {
  if (!id) return
  const sol = store.solicitudes.find(s => s.id === id)
  if (!sol) return
  const msgs = {
    aprobado:  '✓ Tu solicitud fue aprobada',
    rechazado: '✗ Tu solicitud fue rechazada',
  }
  mostrarToast(msgs[sol.estado] || 'Tu solicitud fue actualizada',
    sol.estado === 'aprobado' ? 'ok' : 'error')
})

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

// ── Historial agrupado por fecha (siempre visible) ────────────────────────────
const historialAgrupado = computed(() =>
  agruparPorFecha(store.resueltas, sol => sol.respondido_at || sol.created_at),
)

// ── Toast ──────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', tipo: 'ok' })
let toastTimer = null
function mostrarToast(mensaje, tipo = 'ok') {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, tipo }
  // Los mensajes de modo offline necesitan más tiempo para leerse
  const duracion = tipo === 'offline' ? 6000 : 3500
  toastTimer = setTimeout(() => { toast.value.visible = false }, duracion)
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
  monto:       null,
  litros:      null,
  subtipo_incidencia: '',
})

const TIPOS = [
  { value: 'mantencion',  label: 'Mantención',  icono: 'ti-tool',           color: '#534AB7', colorSuave: '#EEEDFE', descripcion: 'Falla mecánica o revisión necesaria' },
  { value: 'combustible', label: 'Combustible', icono: 'ti-gas-station',    color: '#B45309', colorSuave: '#FEF3C7', descripcion: 'Solicitar recarga o reportar consumo' },
  { value: 'incidencia',  label: 'Incidencia',  icono: 'ti-alert-triangle', color: '#A32D2D', colorSuave: '#FCEBEB', descripcion: 'Parte o multa de tránsito' },
]

const tipoActual = computed(() => TIPOS.find(t => t.value === tipoSeleccionado.value))

// Comprueba si un tipo está habilitado por el plan de la empresa
function tipoHabilitado(tipo) {
  return store.esTipoPermitido(tipo.value)
}

function abrirNuevaSolicitud() {
  paso.value               = 1
  tipoSeleccionado.value   = null
  fotoDataUrl.value        = null
  fotoBase64.value         = null
  errorForm.value          = ''
  confirmarDuplicada.value = false
  form.value               = { titulo: '', descripcion: '', prioridad: 'media', monto: null, litros: null, subtipo_incidencia: '' }
  modalNueva.value         = true
}

function cerrarNueva() { modalNueva.value = false }

async function elegirTipo(tipo) {
  if (!tipoHabilitado(tipo)) return

  tipoSeleccionado.value = tipo.value

  if (tipo.value === 'combustible') {
    form.value.titulo    = 'Solicitud de combustible'
    form.value.prioridad = 'media'
  } else if (tipo.value === 'incidencia') {
    form.value.prioridad           = 'alta'
    form.value.subtipo_incidencia  = 'multa'
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
  } catch (e) {
    if (e?.message?.includes('denied') || e?.message?.includes('permission')) {
      mostrarToast('Permiso de cámara denegado. Actívalo en la configuración del dispositivo.', 'error')
    }
    // Si canceló, no hacer nada
  }
}

function quitarFoto() {
  fotoDataUrl.value = null
  fotoBase64.value  = null
}

// Enviar solicitud desde el formulario paso 2
async function enviarSolicitud(forzar = false) {
  errorForm.value = ''
  const t = tipoSeleccionado.value
  const f = form.value

  if (!f.titulo || f.titulo.length < 5) {
    errorForm.value = 'El título debe tener al menos 5 caracteres.'
    return
  }
  if (f.titulo.length > 200) {
    errorForm.value = 'El título no puede superar los 200 caracteres.'
    return
  }
  if (t !== 'combustible' && f.descripcion.length < 10) {
    errorForm.value = 'La descripción debe tener al menos 10 caracteres.'
    return
  }
  if (f.descripcion.length > 100) {
    errorForm.value = 'La descripción no puede superar los 100 caracteres.'
    return
  }
  if (t === 'incidencia') {
    if (!f.monto || f.monto <= 0) {
      errorForm.value = 'Debes ingresar el monto de la multa.'
      return
    }
    if (!fotoBase64.value) {
      errorForm.value = 'Para multas se requiere una foto del parte.'
      return
    }
  }
  if (t === 'combustible') {
    if (!f.monto || f.monto <= 0) {
      errorForm.value = 'Debes ingresar un monto válido.'
      return
    }
    if (!f.litros || f.litros <= 0) {
      errorForm.value = 'Debes ingresar los litros recargados.'
      return
    }
    if (!fotoBase64.value) {
      errorForm.value = 'Para recargas de combustible es obligatorio adjuntar el comprobante (foto).'
      return
    }
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
  if (t === 'combustible') {
    datos.monto = f.monto
    datos.litros = f.litros
  }
  if (t === 'incidencia') {
    datos.subtipo = 'multa'
    datos.monto   = f.monto
  }
  if (forzar) datos.forzar = 'true'

  const res = await store.crearSolicitud(datos, foto)

  if (res.success) {
    confirmarDuplicada.value = false
    cerrarNueva()
    mostrarToast(
      res.offline
        ? 'Sin conexión. Se enviará cuando vuelva la señal.'
        : 'Solicitud enviada correctamente',
      res.offline ? 'offline' : 'ok',
    )
  } else if (res.codigo === 'solicitud_duplicada') {
    // Ya hay una solicitud de mantención pendiente para este vehículo → confirmar.
    confirmarDuplicada.value = true
    errorForm.value = res.error || 'Ya tienes una solicitud pendiente para este vehículo.'
  } else {
    errorForm.value = res.error || 'Error al enviar la solicitud.'
  }
}

// Confirmación de solicitud duplicada
const confirmarDuplicada = ref(false)
function enviarDeTodasFormas() {
  confirmarDuplicada.value = false
  enviarSolicitud(true)
}

// ── Modal Detalle Solicitud ───────────────────────────────────────────────────
const modalDetalle     = ref(false)
const solicitudDetalle = ref(null)
const fotoAmpliadaUrl  = ref(null)

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
})

onUnmounted(() => {
  clearTimeout(toastTimer)
  store.detenerWs()
})
</script>

<template>
  <!-- Spinner mientras se verifican permisos del plan -->
  <div v-if="cargandoPermisos" class="min-h-dvh bg-gray-50 flex items-center justify-center">
    <span class="w-8 h-8 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
  </div>

  <div v-else
    class="min-h-dvh bg-gray-50 pb-nav"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >

    <!-- ── Spinner pull-to-refresh ─────────────────────────────────────────── -->
    <div v-if="refreshing" class="flex justify-center pt-4">
      <span class="w-6 h-6 border-2 border-gray-200 border-t-[var(--color-acento)] rounded-full animate-spin"/>
    </div>

    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <header class="sol-header">
      <div class="sol-header-pattern" aria-hidden="true"/>
      <div class="sol-header-content">
        <div>
          <p class="sol-header-subtitle">Mis solicitudes</p>
          <h1 class="sol-header-title">Centro de solicitudes</h1>
        </div>
        <!-- Resumen chips -->
        <div class="sol-summary-chips">
          <span v-if="store.pendientes.length" class="chip chip--accent">
            <i class="ti ti-clock text-xs mr-1"/>{{ store.pendientes.length }} activa{{ store.pendientes.length !== 1 ? 's' : '' }}
          </span>
          <span v-if="store.resueltas.length" class="chip chip--muted">
            <i class="ti ti-circle-check text-xs mr-1"/>{{ store.resueltas.length }} resuelta{{ store.resueltas.length !== 1 ? 's' : '' }}
          </span>
        </div>
      </div>
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
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center" style="background: var(--color-acento-suave)">
            <i class="ti ti-clipboard-list text-3xl" style="color: var(--color-acento)"/>
          </div>
          <p class="text-base font-semibold text-gray-600">Sin solicitudes aún</p>
          <p class="text-sm text-center text-gray-400">
            Toca el botón <strong>+ Nueva</strong> para reportar<br>un problema o hacer una solicitud
          </p>
        </div>

        <!-- ── Solicitudes en proceso ────────────────────────────────────── -->
        <section v-if="store.pendientes.length">
          <div class="flex items-center justify-between mb-2">
            <p class="sol-section-label"><i class="ti ti-loader mr-1.5"/>En proceso</p>
            <span class="chip chip--accent">{{ store.pendientes.length }}</span>
          </div>

          <div class="flex flex-col gap-2">
            <button
              v-for="sol in store.pendientes"
              :key="sol.id"
              @click="verDetalle(sol)"
              class="w-full text-left rounded-2xl p-4 border transition active:bg-gray-50 min-h-[44px]"
              :class="store.actualizadaId === sol.id
                ? 'bg-indigo-50 border-indigo-300 shadow-sm ring-2 ring-indigo-200'
                : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'"
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

        <!-- ── Historial (siempre visible, agrupado por fecha) ──────────────── -->
        <section v-if="store.resueltas.length">
          <p class="sol-section-label"><i class="ti ti-history mr-1.5"/>Historial</p>

          <div class="flex flex-col gap-3">
            <div v-for="grupo in historialAgrupado" :key="grupo.label">
              <p class="sol-subgroup-label">{{ grupo.label }}</p>
              <div class="flex flex-col gap-1.5">
                <button
                  v-for="sol in grupo.items"
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
            </div>
          </div>
        </section>

      </div>
    </template>

    <!-- ── FAB ───────────────────────────────────────────────────────────── -->
    <button
      @click="abrirNuevaSolicitud"
      class="fab-btn"
      :style="`bottom: calc(76px + env(safe-area-inset-bottom))`"
    >
      <i class="ti ti-plus" style="font-size:1.125rem"/>
      Nueva solicitud
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
      <div v-if="modalNueva" class="fixed inset-0 z-[60] flex flex-col justify-end">
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
                class="rounded-2xl p-4 text-left border transition relative min-h-[44px]"
                :class="tipoHabilitado(tipo)
                  ? 'border-transparent active:scale-95'
                  : 'border-transparent opacity-50 cursor-not-allowed'"
                :style="`background: ${tipoHabilitado(tipo) ? tipo.colorSuave : '#F3F4F6'}`"
                :disabled="!tipoHabilitado(tipo)"
              >
                <!-- Candado para tipos bloqueados por el plan -->
                <span
                  v-if="!tipoHabilitado(tipo)"
                  class="absolute top-2 right-2 w-5 h-5 rounded-full bg-gray-300 flex items-center justify-center"
                >
                  <i class="ti ti-lock text-[10px] text-gray-500"/>
                </span>

                <i
                  class="ti text-2xl block mb-2"
                  :class="tipo.icono"
                  :style="`color: ${tipoHabilitado(tipo) ? tipo.color : '#9CA3AF'}`"
                />
                <p
                  class="text-sm font-bold"
                  :style="`color: ${tipoHabilitado(tipo) ? tipo.color : '#9CA3AF'}`"
                >
                  {{ tipo.label }}
                </p>
                <p class="text-xs mt-0.5" :class="tipoHabilitado(tipo) ? 'text-gray-500' : 'text-gray-400'">
                  {{ tipoHabilitado(tipo) ? tipo.descripcion : 'No disponible en tu plan' }}
                </p>
              </button>
            </div>

            <!-- Aviso si hay tipos bloqueados -->
            <div
              v-if="store.tiposPermitidos !== null && store.tiposPermitidos.length < TIPOS.length"
              class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5 mb-4"
            >
              <i class="ti ti-info-circle text-amber-500 text-base shrink-0 mt-0.5"/>
              <p class="text-xs text-amber-700 leading-snug">
                Algunos tipos de solicitud no están disponibles en el plan de tu empresa.
                Contacta al administrador para más información.
              </p>
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
              <label class="flex items-center justify-between text-xs font-semibold text-gray-600 mb-1">
                <span>
                  Descripción
                  <span v-if="tipoSeleccionado !== 'combustible'" class="text-red-400">*</span>
                </span>
                <span :class="form.descripcion.length > 100 ? 'text-red-500' : 'text-gray-400'">
                  {{ form.descripcion.length }}/100
                </span>
              </label>
              <textarea
                v-model="form.descripcion"
                placeholder="Más detalles sobre el problema..."
                rows="3"
                maxlength="110"
                :class="form.descripcion.length > 100 ? 'border-red-400' : 'border-gray-200'"
                class="w-full rounded-xl border px-3 py-2.5 text-sm
                       focus:outline-none focus:border-[var(--color-acento)] transition resize-none"
              />
            </div>

            <!-- Incidencia: Monto de la multa -->
            <div v-if="tipoSeleccionado === 'incidencia'" class="mb-4">
              <label class="block text-xs font-semibold text-gray-600 mb-1">
                Monto de la multa ($) <span class="text-red-400">*</span>
              </label>
              <input
                v-model.number="form.monto"
                type="number"
                placeholder="Ej: 50000"
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                       focus:outline-none focus:border-[var(--color-acento)] transition"
              />
            </div>

            <!-- Combustible: Monto y Litros -->
            <div v-if="tipoSeleccionado === 'combustible'" class="flex gap-3 mb-4">
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">
                  Monto ($) <span class="text-red-400">*</span>
                </label>
                <input
                  v-model.number="form.monto"
                  type="number"
                  placeholder="Ej: 20000"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                         focus:outline-none focus:border-[var(--color-acento)] transition"
                />
              </div>
              <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-600 mb-1">
                  Litros <span class="text-red-400">*</span>
                </label>
                <input
                  v-model.number="form.litros"
                  type="number"
                  step="0.01"
                  placeholder="Ej: 15.5"
                  class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                         focus:outline-none focus:border-[var(--color-acento)] transition"
                />
              </div>
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
                <span v-if="tipoSeleccionado === 'incidencia' || tipoSeleccionado === 'combustible'" class="text-red-400">* (requerida)</span>
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

              <div v-else class="relative rounded-2xl overflow-hidden border border-gray-200 bg-gray-50">
                <img
                  :src="fotoDataUrl"
                  class="w-full max-h-48 object-contain"
                  alt="Vista previa"
                />
                <button
                  @click="quitarFoto"
                  class="absolute top-2 right-2 w-7 h-7 rounded-full bg-red-500/90 text-white flex items-center justify-center"
                >
                  <i class="ti ti-x text-xs"/>
                </button>
              </div>
            </div>

            <!-- Error formulario -->
            <p v-if="errorForm" class="text-xs text-red-600 mb-3 flex items-center gap-1">
              <i class="ti ti-alert-circle"/>
              {{ errorForm }}
            </p>

            <!-- Confirmación de solicitud duplicada -->
            <button
              v-if="confirmarDuplicada"
              @click="enviarDeTodasFormas"
              :disabled="store.enviando"
              class="w-full mb-2 py-3 rounded-xl text-amber-700 bg-amber-50 border border-amber-300 text-sm font-semibold min-h-[44px]"
            >
              Crear otra de todas formas
            </button>

            <!-- Botón enviar -->
            <button
              @click="enviarSolicitud()"
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
      <div v-if="modalDetalle && solicitudDetalle" class="fixed inset-0 z-[60] flex flex-col justify-end">
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
              <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Foto adjunta</p>
              <img
                :src="solicitudDetalle.foto_url"
                class="w-full rounded-2xl border border-gray-100 bg-gray-50 object-contain max-h-56 cursor-zoom-in"
                alt="Foto adjunta"
                @click="fotoAmpliadaUrl = solicitudDetalle.foto_url"
                @error="(e) => { e.target.style.display='none'; e.target.nextSibling && (e.target.nextSibling.style.display='block') }"
              />
              <p class="text-xs text-gray-400 text-center hidden">Foto no disponible</p>
              <p class="text-[10px] text-gray-400 mt-1 text-center">Toca para ampliar</p>
            </div>

            <!-- Respuesta del administrador -->
            <div class="mb-5">
              <p class="text-xs font-semibold text-gray-600 mb-1">Respuesta del administrador:</p>
              <div v-if="solicitudDetalle.respuesta">
                <p class="text-sm text-gray-700 italic">"{{ solicitudDetalle.respuesta }}"</p>
              </div>
              <div v-else-if="solicitudDetalle.estado === 'aprobado'" class="flex items-center gap-2 text-green-600">
                <i class="ti ti-circle-check text-base"/>
                <p class="text-xs font-semibold">Solicitud aprobada.</p>
              </div>
              <div v-else-if="solicitudDetalle.estado === 'rechazado'" class="flex items-center gap-2 text-red-500">
                <i class="ti ti-circle-x text-base"/>
                <p class="text-xs font-semibold">Solicitud rechazada.</p>
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

    <!-- ── Foto ampliada fullscreen ─────────────────────────────────────────── -->
    <Transition name="fade">
      <div
        v-if="fotoAmpliadaUrl"
        class="fixed inset-0 z-[70] bg-black/95 flex flex-col"
        @click="fotoAmpliadaUrl = null"
      >
        <div class="flex items-center gap-3 shrink-0 p-4"
             :style="`padding-top: max(1rem, env(safe-area-inset-top))`">
          <button class="w-9 h-9 rounded-full bg-white/15 flex items-center justify-center text-white shrink-0">
            <i class="ti ti-x text-lg"/>
          </button>
        </div>
        <div class="flex-1 flex items-center justify-center p-4">
          <img :src="fotoAmpliadaUrl" class="max-w-full max-h-full object-contain" alt="Foto ampliada"/>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* ── Header solicitudes ────────────────────────────────────────────────── */
.sol-header {
  position: relative;
  overflow: hidden;
  background: var(--gradient-hero);
  padding: max(1.25rem, env(safe-area-inset-top)) 1rem 1rem;
}
.sol-header-pattern {
  position: absolute; inset: 0;
  background-image: radial-gradient(circle at 90% 10%, rgba(255,255,255,0.1) 0%, transparent 50%);
}
.sol-header-content {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}
.sol-header-subtitle {
  font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.65);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;
}
.sol-header-title {
  font-size: 1.375rem; font-weight: 800; color: white; line-height: 1.15;
}
.sol-summary-chips {
  display: flex; flex-direction: column; align-items: flex-end; gap: 0.375rem;
  flex-shrink: 0;
}

/* ── Chips ─────────────────────────────────────────────────────────────── */
.chip {
  display: inline-flex; align-items: center; gap: 0.25rem;
  font-size: 0.6875rem; font-weight: 700;
  border-radius: 999px; padding: 0.2rem 0.625rem; line-height: 1.4;
}
.chip--accent {
  background: rgba(255,255,255,0.18); color: white; border: 1px solid rgba(255,255,255,0.3);
}
.chip--muted {
  background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.15);
}
/* Para usar fuera del header */
section .chip--accent {
  background: var(--color-acento-suave); color: var(--color-acento); border: none;
}

/* ── Sección label ─────────────────────────────────────────────────────── */
.sol-section-label {
  font-size: 0.6875rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9CA3AF; margin-bottom: 0.5rem;
}
.sol-subgroup-label {
  font-size: 0.6875rem; font-weight: 600;
  color: #B0B6C0; margin-bottom: 0.375rem;
}

/* ── FAB ───────────────────────────────────────────────────────────────── */
.fab-btn {
  position: fixed; right: 1rem;
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.8125rem 1.25rem;
  border-radius: 999px;
  background: var(--gradient-primary);
  box-shadow: var(--shadow-acento);
  color: white; font-size: 0.875rem; font-weight: 700;
  border: none; cursor: pointer; z-index: 40;
  -webkit-tap-highlight-color: transparent;
}
.fab-btn:active { opacity: 0.85; transform: scale(0.97); }

/* Bottom sheet */
.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from,   .sheet-leave-to     { transform: translateY(100%); }

/* Toast */
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from,   .toast-leave-to     { opacity: 0; transform: translate(-50%, 8px); }

/* Foto ampliada */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,   .fade-leave-to     { opacity: 0; }
</style>
