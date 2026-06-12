<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from '@/services/api.js'
import BottomNav from '@/components/BottomNav.vue'
import { useModeracion } from '@/composables/useModeracion.js'

const vueRoute = useRoute()
const router   = useRouter()
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()

const rutaId = computed(() => Number(vueRoute.params.id))

// ── Estado general ─────────────────────────────────────────────────────────────
const items        = ref([])
const ruta         = ref(null)
const vehiculo     = ref(null)
const cargando     = ref(true)
const enviando     = ref(false)
const errorMsg     = ref('')

// ── Respuestas del conductor ───────────────────────────────────────────────────
// { item_id: { resultado: 'ok'|'falla'|null, observacion: '' } }
const respuestas = ref({})

watch(respuestas, () => {
  if (avisoMod.value) limpiarMod()
}, { deep: true })

// Cuál ítem tiene el selector inline abierto (solo uno a la vez)
const itemAbierto = ref(null)

// ── Firma digital ─────────────────────────────────────────────────────────────
const canvasRef  = ref(null)
const firmaB64   = ref('')
const dibujando  = ref(false)
let   lastX = 0, lastY = 0

// ── Toast ──────────────────────────────────────────────────────────────────────
const toast = ref({ visible: false, mensaje: '', ok: true })
let toastTimer = null

function mostrarToast(mensaje, ok = true) {
  clearTimeout(toastTimer)
  toast.value = { visible: true, mensaje, ok }
  toastTimer  = setTimeout(() => { toast.value.visible = false }, 3500)
}

// ── Agrupación de ítems ────────────────────────────────────────────────────────
const CATEGORIA_LABEL = {
  documentos: '📄 Documentos',
  mecanica:   '🔧 Mecánica',
  seguridad:  '🦺 Seguridad',
}

const grupos = computed(() => {
  const mapa = {}
  for (const item of items.value) {
    if (!mapa[item.categoria]) mapa[item.categoria] = []
    mapa[item.categoria].push(item)
  }
  return Object.entries(mapa).map(([cat, lista]) => ({
    cat,
    label: CATEGORIA_LABEL[cat] || cat,
    lista,
  }))
})

// ── Progreso ───────────────────────────────────────────────────────────────────
const totalObligatorios = computed(() =>
  items.value.filter(i => i.obligatorio).length
)
const completados = computed(() =>
  items.value.filter(i => i.obligatorio && respuestas.value[i.id]?.resultado).length
)
const progresoPct = computed(() =>
  totalObligatorios.value ? Math.round((completados.value / totalObligatorios.value) * 100) : 0
)
const pendientesCount = computed(() => totalObligatorios.value - completados.value)

// ── Validación del botón de envío ──────────────────────────────────────────────
const puedeEnviar = computed(() => pendientesCount.value === 0 && firmaB64.value)

const textoBtnEnviar = computed(() => {
  if (pendientesCount.value > 0)
    return `Completa todos los ítems (${pendientesCount.value} pendiente${pendientesCount.value > 1 ? 's' : ''})`
  if (!firmaB64.value)
    return 'Firma para continuar'
  return 'Enviar checklist'
})

// ── Carga inicial ──────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await apiFetch(`/api/conductor/checklist/${rutaId.value}/`)
    items.value    = data.items
    ruta.value     = data.ruta
    vehiculo.value = data.vehiculo

    // Inicializar respuestas
    const init = {}
    for (const item of data.items) {
      // Pre-cargar borrador si existe
      const guardado = data.respuestas_guardadas?.[item.id]
      if (guardado) {
        init[item.id] = { resultado: guardado.resultado, observacion: guardado.observacion || '' }
      } else if (item.pre_resultado) {
        // Documentos vigentes pre-marcados
        init[item.id] = { resultado: item.pre_resultado, observacion: '' }
      } else {
        init[item.id] = { resultado: null, observacion: '' }
      }
    }
    respuestas.value = init
  } catch (e) {
    errorMsg.value = e.message || 'Error al cargar el checklist'
  } finally {
    cargando.value = false
  }
})

// ── Manejo de ítems ────────────────────────────────────────────────────────────
function toggleItem(itemId) {
  const actual = respuestas.value[itemId]?.resultado
  if (actual) {
    // Ya marcado → devolver a pendiente
    respuestas.value[itemId] = { resultado: null, observacion: '' }
    itemAbierto.value = null
  } else {
    // Pendiente → abrir selector
    itemAbierto.value = itemAbierto.value === itemId ? null : itemId
  }
}

function marcarItem(itemId, resultado) {
  respuestas.value[itemId] = {
    resultado,
    observacion: respuestas.value[itemId]?.observacion || '',
  }
  if (resultado !== 'falla') {
    itemAbierto.value = null
  }
}

function claseItem(item) {
  const res = respuestas.value[item.id]?.resultado
  if (res === 'ok')    return 'item--ok'
  if (res === 'falla') return 'item--falla'
  return 'item--pendiente'
}

// ── Canvas de firma ────────────────────────────────────────────────────────────
function posCanvas(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const src  = e.touches ? e.touches[0] : e
  return {
    x: (src.clientX - rect.left) * (canvasRef.value.width  / rect.width),
    y: (src.clientY - rect.top)  * (canvasRef.value.height / rect.height),
  }
}

function iniciarTrazo(e) {
  e.preventDefault()
  dibujando.value = true
  const { x, y } = posCanvas(e)
  lastX = x; lastY = y
}

function continuarTrazo(e) {
  e.preventDefault()
  if (!dibujando.value) return
  const ctx = canvasRef.value.getContext('2d')
  const { x, y } = posCanvas(e)
  ctx.beginPath()
  ctx.moveTo(lastX, lastY)
  ctx.lineTo(x, y)
  ctx.strokeStyle = '#1a1a2e'
  ctx.lineWidth   = 2.2
  ctx.lineCap     = 'round'
  ctx.lineJoin    = 'round'
  ctx.stroke()
  lastX = x; lastY = y
}

function terminarTrazo(e) {
  e.preventDefault()
  dibujando.value = false
  firmaB64.value  = canvasRef.value.toDataURL('image/png')
}

function limpiarFirma() {
  const ctx = canvasRef.value.getContext('2d')
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  firmaB64.value = ''
}

// ── Envío ──────────────────────────────────────────────────────────────────────
async function enviarChecklist() {
  if (!puedeEnviar.value || enviando.value) return

  const obsTexto = Object.values(respuestas.value)
    .map(r => r.observacion || '')
    .filter(obs => obs.trim().length >= 3)
    .join(' ')
  if (obsTexto) {
    const ok = await moderar(obsTexto)
    if (!ok) return
  }

  enviando.value = true
  try {
    const data = await apiFetch(`/api/conductor/checklist/${rutaId.value}/`, {
      method: 'POST',
      body: JSON.stringify({
        respuestas: respuestas.value,
        firma_base64: firmaB64.value,
      }),
    })

    if (data.tiene_fallas) {
      mostrarToast('Checklist enviado con fallas. El admin fue notificado.', true)
    } else {
      mostrarToast('Todo en orden. Puedes iniciar la ruta. ✓', true)
    }
    setTimeout(() => router.push(`/rutas/${rutaId.value}`), 1800)
  } catch (e) {
    mostrarToast(e.message || 'Error al enviar el checklist', false)
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="min-h-dvh bg-gray-50 flex flex-col">

    <!-- ── Toast ────────────────────────────────────────────────────────────── -->
    <Transition name="toast-slide">
      <div v-if="toast.visible"
           class="fixed left-4 right-4 z-[4000] rounded-2xl px-4 py-3 shadow-xl text-sm font-semibold flex items-center gap-2"
           style="top: max(1rem, calc(env(safe-area-inset-top, 0px) + 0.5rem))"
           :class="toast.ok ? 'bg-green-500 text-white' : 'bg-red-500 text-white'">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
        </svg>
        {{ toast.mensaje }}
      </div>
    </Transition>

    <!-- ── Skeleton ──────────────────────────────────────────────────────────── -->
    <template v-if="cargando">
      <div class="h-[72px] bg-white border-b border-gray-100 shrink-0"/>
      <div class="px-4 pt-5 flex flex-col gap-3">
        <div v-for="n in 6" :key="n" class="h-16 bg-gray-200 rounded-2xl animate-pulse"/>
      </div>
    </template>

    <!-- ── Error ─────────────────────────────────────────────────────────────── -->
    <template v-else-if="errorMsg">
      <div class="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center text-gray-400">
        <p class="text-sm font-medium">{{ errorMsg }}</p>
        <button @click="router.back()" class="text-sm text-[var(--color-acento)] font-bold min-h-[44px] px-4">
          Volver
        </button>
      </div>
    </template>

    <!-- ── Contenido ─────────────────────────────────────────────────────────── -->
    <template v-else>

      <!-- Header fijo -->
      <header class="fixed top-0 left-0 right-0 z-[1001] bg-white border-b border-gray-100"
              style="padding-top:max(0.75rem,env(safe-area-inset-top))">
        <div class="flex items-center gap-3 px-4 pb-3">
          <button @click="router.back()"
                  class="p-2 -ml-2 text-gray-500 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          <div class="flex-1 min-w-0">
            <h1 class="text-base font-bold text-gray-900 leading-tight">Checklist pre-viaje</h1>
            <p class="text-xs text-gray-400 truncate">
              {{ ruta?.nombre }}
              <template v-if="vehiculo?.patente"> · {{ vehiculo.patente }}</template>
            </p>
          </div>
          <!-- Contador -->
          <span class="text-xs font-bold px-2.5 py-1 rounded-full"
                :class="pendientesCount === 0
                  ? 'bg-green-50 text-green-600'
                  : 'bg-[var(--color-acento-suave)] text-[var(--color-acento)]'">
            {{ completados }}/{{ totalObligatorios }}
          </span>
        </div>

        <!-- Barra de progreso -->
        <div class="h-1 bg-gray-100 mx-4 rounded-full overflow-hidden mb-0">
          <div class="h-full rounded-full transition-all duration-500"
               :style="`width:${progresoPct}%;
                        background:${progresoPct === 100
                          ? 'linear-gradient(90deg,#22c55e,#16a34a)'
                          : 'var(--gradient-primary)'}`"/>
        </div>
      </header>

      <!-- Espaciado del header fijo (aprox 82px) -->
      <div class="h-[82px] shrink-0"/>

      <!-- ── Lista de ítems ──────────────────────────────────────────────────── -->
      <div class="flex-1 px-4 pt-4 pb-[calc(var(--nav-total,64px)+160px)] flex flex-col gap-5">

        <section v-for="grupo in grupos" :key="grupo.cat">
          <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 px-1">
            {{ grupo.label }}
          </p>

          <div class="flex flex-col gap-2">
            <div v-for="item in grupo.lista" :key="item.id"
                 class="item-card"
                 :class="claseItem(item)"
                 @click="toggleItem(item.id)">

              <!-- Fila principal -->
              <div class="flex items-start gap-3 p-4">

                <!-- Círculo de estado -->
                <div class="item-circle shrink-0 mt-0.5">
                  <!-- Ok -->
                  <svg v-if="respuestas[item.id]?.resultado === 'ok'"
                       class="w-5 h-5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                  </svg>
                  <!-- Falla -->
                  <svg v-else-if="respuestas[item.id]?.resultado === 'falla'"
                       class="w-5 h-5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                  <!-- Pendiente -->
                  <div v-else class="w-2 h-2 rounded-full bg-gray-300"/>
                </div>

                <!-- Textos -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-semibold text-gray-800 leading-snug">{{ item.nombre }}</p>
                  <p v-if="item.fecha_vencimiento && item.estado_documento === 'vigente'"
                     class="text-xs text-green-600 font-medium mt-0.5">
                    Vence {{ item.fecha_vencimiento }}
                  </p>
                  <p v-else-if="item.estado_documento === 'por_vencer'"
                     class="text-xs text-amber-500 font-medium mt-0.5">
                    ⚠ Por vencer — {{ item.fecha_vencimiento }}
                  </p>
                  <p v-else-if="item.estado_documento === 'vencido'"
                     class="text-xs text-red-500 font-medium mt-0.5">
                    ✗ Vencido
                  </p>
                  <p v-else class="text-xs text-gray-400 mt-0.5">{{ item.descripcion }}</p>
                </div>

                <!-- Chevron / check -->
                <svg v-if="!respuestas[item.id]?.resultado"
                     class="w-4 h-4 text-gray-300 shrink-0 mt-1 transition-transform"
                     :class="itemAbierto === item.id ? 'rotate-90' : ''"
                     fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
                </svg>
              </div>

              <!-- Selector inline (solo si ítem abierto y sin respuesta) -->
              <Transition name="expand">
                <div v-if="itemAbierto === item.id && !respuestas[item.id]?.resultado"
                     class="px-4 pb-4 flex gap-2" @click.stop>
                  <button class="flex-1 py-2.5 rounded-xl text-sm font-bold border-2 border-green-500 text-green-600 bg-green-50 min-h-[44px]"
                          @click="marcarItem(item.id, 'ok')">
                    ✓ OK
                  </button>
                  <button class="flex-1 py-2.5 rounded-xl text-sm font-bold border-2 border-red-400 text-red-500 bg-red-50 min-h-[44px]"
                          @click="marcarItem(item.id, 'falla')">
                    ✗ Falla
                  </button>
                </div>
              </Transition>

              <!-- Textarea de observación (solo si es falla) -->
              <div v-if="respuestas[item.id]?.resultado === 'falla'"
                   class="px-4 pb-4" @click.stop>
                <textarea
                  v-model="respuestas[item.id].observacion"
                  placeholder="Describe la falla…"
                  rows="2"
                  class="w-full text-sm text-gray-700 placeholder-gray-300 bg-white border border-red-200 rounded-xl px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-red-300"
                />
              </div>

            </div>
          </div>
        </section>

        <!-- ── Firma digital ─────────────────────────────────────────────────── -->
        <section>
          <p class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 px-1">
            ✍ Firma del conductor
          </p>

          <div class="bg-white rounded-2xl border"
               :class="firmaB64 ? 'border-green-300' : 'border-gray-200'">
            <p class="text-xs text-gray-400 px-4 pt-3 pb-1">Firma dentro del recuadro para confirmar</p>
            <canvas
              ref="canvasRef"
              width="600"
              height="180"
              class="w-full touch-none rounded-b-2xl bg-gray-50 border-t border-dashed border-gray-200 cursor-crosshair"
              style="max-height: 140px"
              @touchstart="iniciarTrazo"
              @touchmove="continuarTrazo"
              @touchend="terminarTrazo"
              @mousedown="iniciarTrazo"
              @mousemove="continuarTrazo"
              @mouseup="terminarTrazo"
              @mouseleave="dibujando = false"
            />
            <div class="flex justify-between items-center px-4 py-2">
              <p v-if="firmaB64" class="text-xs font-semibold text-green-600">✓ Firma capturada</p>
              <p v-else class="text-xs text-gray-400">Sin firma</p>
              <button class="text-xs font-bold text-gray-400 min-h-[36px] px-3" @click="limpiarFirma">
                Limpiar
              </button>
            </div>
          </div>
        </section>

      </div><!-- fin scroll area -->

      <!-- ── Botón fijo de envío ─────────────────────────────────────────────── -->
      <div class="fixed left-0 right-0 px-4 pb-3 z-[500]"
           style="bottom: calc(var(--nav-total, 64px) + env(safe-area-inset-bottom, 0px))">
        <div v-if="avisoMod" class="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5 mb-2">
          <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M5 19h14a2 2 0 001.732-1l-7-12a2 2 0 00-3.464 0L3.268 18A2 2 0 005 20z"/>
          </svg>
          <div>
            <p class="text-xs font-semibold text-amber-700">{{ avisoMod }}</p>
            <p v-if="sugerenciaMod" class="text-xs text-amber-600 mt-0.5">{{ sugerenciaMod }}</p>
          </div>
        </div>
        <button
          @click="enviarChecklist"
          :disabled="!puedeEnviar || enviando"
          class="w-full py-4 rounded-2xl text-white font-bold text-sm flex items-center justify-center gap-2 min-h-[54px] transition-all duration-300"
          :style="puedeEnviar
            ? 'background:linear-gradient(135deg,#22c55e,#16a34a); box-shadow:0 4px 16px rgba(34,197,94,.4)'
            : 'background:#d1d5db; box-shadow:none; color:#9ca3af'">
          <svg v-if="enviando" class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8V4"/>
          </svg>
          <svg v-else-if="puedeEnviar" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
          {{ enviando ? 'Enviando…' : textoBtnEnviar }}
        </button>
      </div>

    </template><!-- fin contenido -->

    <BottomNav />
  </div>
</template>

<style scoped>
/* ── Ítem del checklist ────────────────────────────────────────────────────── */
.item-card {
  border-radius: 1rem;
  border-width: 1.5px;
  border-style: solid;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.item-card.item--pendiente {
  background: #fff;
  border-color: #e5e7eb;
}
.item-card.item--ok {
  background: #f0fdf4;
  border-color: #86efac;
}
.item-card.item--falla {
  background: #fff5f5;
  border-color: #fca5a5;
}

/* Círculo de estado */
.item-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}
.item--pendiente .item-circle { background: #f3f4f6; }
.item--ok        .item-circle { background: #22c55e; }
.item--falla     .item-circle { background: #ef4444; }

/* ── Transición selector inline ───────────────────────────────────────────── */
.expand-enter-active,
.expand-leave-active { transition: max-height 0.2s ease, opacity 0.2s ease; overflow: hidden; }
.expand-enter-from,
.expand-leave-to    { max-height: 0; opacity: 0; }
.expand-enter-to,
.expand-leave-from  { max-height: 120px; opacity: 1; }

/* ── Toast ────────────────────────────────────────────────────────────────── */
.toast-slide-enter-active,
.toast-slide-leave-active { transition: opacity 0.25s, transform 0.25s; }
.toast-slide-enter-from,
.toast-slide-leave-to    { opacity: 0; transform: translateY(-8px); }
</style>
