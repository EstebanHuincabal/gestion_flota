<template>
  <div class="relative inline-block" ref="contenedor">
    <button
      @click="togglePopover"
      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors"
      :class="claseChip"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <span>{{ textoChip }}</span>
    </button>

    <!-- Popover -->
    <Teleport to="body">
      <div
        v-if="popoverAbierto"
        class="fixed z-50 bg-white rounded-xl shadow-2xl border border-slate-200 w-72"
        :style="estiloPopover"
      >
        <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <span class="text-sm font-semibold text-slate-700">Documentos</span>
          <button @click="popoverAbierto = false" class="text-slate-400 hover:text-slate-600">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="cargando" class="py-6 flex justify-center">
          <svg class="animate-spin h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        </div>

        <div v-else-if="!docs.length" class="py-5 text-center text-sm text-slate-400">
          Sin documentos registrados
        </div>

        <ul v-else class="py-1 max-h-64 overflow-y-auto divide-y divide-slate-50">
          <li
            v-for="doc in docs"
            :key="doc.id"
            class="px-4 py-2.5 flex items-center justify-between gap-2"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-700 truncate">{{ doc.tipo_display }}</p>
              <p v-if="doc.fecha_vencimiento" class="text-xs text-slate-400">
                Vence: {{ formatFecha(doc.fecha_vencimiento) }}
              </p>
              <p v-else class="text-xs text-slate-400">Sin vencimiento</p>
            </div>
            <span class="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium" :class="claseEstado(doc.estado)">
              {{ labelEstado(doc.estado, doc.dias_para_vencer) }}
            </span>
          </li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const props = defineProps({
  entidad:     { type: String, required: true },   // 'vehiculo' | 'conductor'
  entidadId:   { type: [Number, String], required: true },
})

const docs            = ref([])
const cargando        = ref(false)
const popoverAbierto  = ref(false)
const estiloPopover   = ref({})
const contenedor      = ref(null)

async function cargar() {
  if (cargando.value || docs.value.length) return
  cargando.value = true
  try {
    const param  = props.entidad === 'vehiculo' ? 'vehiculo_id' : 'conductor_id'
    const res    = await apiFetch(`/api/empresa/documentos/?entidad=${props.entidad}&${param}=${props.entidadId}`)
    if (res.ok) {
      const json = await res.json()
      docs.value = json.documentos || []
    }
  } finally {
    cargando.value = false
  }
}

function posicionarPopover() {
  if (!contenedor.value) return
  const rect = contenedor.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const top = spaceBelow > 220 ? rect.bottom + 6 : rect.top - 226
  estiloPopover.value = {
    top:  `${top}px`,
    left: `${Math.min(rect.left, window.innerWidth - 290)}px`,
  }
}

function togglePopover() {
  if (!popoverAbierto.value) {
    cargar()
    posicionarPopover()
  }
  popoverAbierto.value = !popoverAbierto.value
}

function cerrarSiAfuera(e) {
  if (popoverAbierto.value && contenedor.value && !contenedor.value.contains(e.target)) {
    const popEl = document.querySelector('.fixed.z-50.bg-white.rounded-xl')
    if (!popEl || !popEl.contains(e.target)) {
      popoverAbierto.value = false
    }
  }
}

onMounted(() => document.addEventListener('mousedown', cerrarSiAfuera))
onUnmounted(() => document.removeEventListener('mousedown', cerrarSiAfuera))

// ── Computed ────────────────────────────────────────────
const vencidos   = computed(() => docs.value.filter(d => d.estado === 'vencido').length)
const porVencer  = computed(() => docs.value.filter(d => d.estado === 'por_vencer').length)

const claseChip = computed(() => {
  if (!docs.value.length && !cargando.value) return 'bg-slate-100 text-slate-500 hover:bg-slate-200'
  if (vencidos.value)  return 'bg-red-100 text-red-700 hover:bg-red-200'
  if (porVencer.value) return 'bg-amber-100 text-amber-700 hover:bg-amber-200'
  return 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
})

const textoChip = computed(() => {
  if (cargando.value)         return '...'
  if (!docs.value.length)     return 'Sin docs'
  if (vencidos.value)         return `${vencidos.value} vencido${vencidos.value > 1 ? 's' : ''}`
  if (porVencer.value)        return `${porVencer.value} por vencer`
  return 'Docs al día'
})

// ── Helpers ─────────────────────────────────────────────
function claseEstado(estado) {
  return {
    vencido:        'bg-red-100 text-red-700',
    por_vencer:     'bg-amber-100 text-amber-700',
    vigente:        'bg-emerald-100 text-emerald-700',
    sin_vencimiento:'bg-slate-100 text-slate-500',
  }[estado] || 'bg-slate-100 text-slate-500'
}

function labelEstado(estado, dias) {
  if (estado === 'vencido')   return `Vencido hace ${Math.abs(dias)}d`
  if (estado === 'por_vencer') return `Vence en ${dias}d`
  if (estado === 'vigente')   return 'Vigente'
  return 'Sin vencimiento'
}

function formatFecha(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
</script>
