<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiFetch } from '../../utils/api.js'

// ── Paleta de colores por tipo ─────────────────────────────────────────────
const PALETA = {
  // Rutas
  indigo: { chip: 'bg-indigo-100 text-indigo-700 border border-indigo-200', dot: 'bg-indigo-500', badge: 'bg-indigo-500 text-white', panel: 'bg-indigo-50 border-indigo-200', icono: '🗺️' },
  green:  { chip: 'bg-green-100 text-green-700 border border-green-200',   dot: 'bg-green-500',  badge: 'bg-green-500 text-white',  panel: 'bg-green-50 border-green-200',  icono: '▶️' },
  slate:  { chip: 'bg-slate-100 text-slate-600 border border-slate-200',   dot: 'bg-slate-400',  badge: 'bg-slate-400 text-white',  panel: 'bg-slate-50 border-slate-200',  icono: '✅' },
  // Mantenciones
  orange: { chip: 'bg-orange-100 text-orange-700 border border-orange-200', dot: 'bg-orange-500', badge: 'bg-orange-500 text-white', panel: 'bg-orange-50 border-orange-200', icono: '🔧' },
  amber:  { chip: 'bg-amber-100 text-amber-700 border border-amber-200',   dot: 'bg-amber-500',  badge: 'bg-amber-500 text-white',  panel: 'bg-amber-50 border-amber-200',  icono: '⚙️' },
  blue:   { chip: 'bg-blue-100 text-blue-700 border border-blue-200',      dot: 'bg-blue-500',   badge: 'bg-blue-500 text-white',   panel: 'bg-blue-50 border-blue-200',    icono: '✔️' },
  yellow: { chip: 'bg-yellow-100 text-yellow-700 border border-yellow-200', dot: 'bg-yellow-400', badge: 'bg-yellow-400 text-white', panel: 'bg-yellow-50 border-yellow-200', icono: '📅' },
  // Documentos
  red:    { chip: 'bg-red-100 text-red-700 border border-red-200',         dot: 'bg-red-500',    badge: 'bg-red-500 text-white',    panel: 'bg-red-50 border-red-200',      icono: '📄' },
  // Solicitudes
  purple: { chip: 'bg-purple-100 text-purple-700 border border-purple-200', dot: 'bg-purple-500', badge: 'bg-purple-500 text-white', panel: 'bg-purple-50 border-purple-200', icono: '💬' },
  violet: { chip: 'bg-violet-100 text-violet-700 border border-violet-200', dot: 'bg-violet-500', badge: 'bg-violet-500 text-white', panel: 'bg-violet-50 border-violet-200', icono: '💬' },
  teal:   { chip: 'bg-teal-100 text-teal-700 border border-teal-200',      dot: 'bg-teal-500',   badge: 'bg-teal-500 text-white',   panel: 'bg-teal-50 border-teal-200',    icono: '💬' },
  gray:   { chip: 'bg-gray-100 text-gray-500 border border-gray-200',      dot: 'bg-gray-400',   badge: 'bg-gray-400 text-white',   panel: 'bg-gray-50 border-gray-200',    icono: '—' },
}
const pal = (color) => PALETA[color] ?? PALETA.gray

// ── Filtros ────────────────────────────────────────────────────────────────
const FILTROS = [
  { tipo: 'ruta',                label: 'Rutas',         color: 'indigo' },
  { tipo: 'mantencion',          label: 'Mantenciones',  color: 'orange' },
  { tipo: 'mantencion_predictiva', label: 'Predictivo',  color: 'amber'  },
  { tipo: 'documento',           label: 'Documentos',    color: 'red'    },
  { tipo: 'solicitud',           label: 'Solicitudes',   color: 'purple' },
]
const filtrosActivos = ref(new Set(FILTROS.map(f => f.tipo)))
const toggleFiltro = (tipo) => {
  const s = new Set(filtrosActivos.value)
  s.has(tipo) ? s.delete(tipo) : s.add(tipo)
  filtrosActivos.value = s
}

// ── Estado del calendario ──────────────────────────────────────────────────
const hoy = new Date()
const mesActual = ref(hoy.getMonth())      // 0–11
const anioActual = ref(hoy.getFullYear())

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

function irMes(delta) {
  let m = mesActual.value + delta
  let a = anioActual.value
  if (m < 0)  { m = 11; a-- }
  if (m > 11) { m = 0;  a++ }
  mesActual.value  = m
  anioActual.value = a
}
function irHoy() {
  mesActual.value  = hoy.getMonth()
  anioActual.value = hoy.getFullYear()
}

// ── Carga de eventos ───────────────────────────────────────────────────────
const todos = ref([])
const cargando = ref(false)

async function cargar() {
  cargando.value = true
  const desde = new Date(anioActual.value, mesActual.value, 1)
  const hasta = new Date(anioActual.value, mesActual.value + 1, 0)
  const fmt = (d) => d.toISOString().split('T')[0]

  // Extender margen para documentos que vencen próximamente
  const desdeExt = new Date(desde); desdeExt.setDate(desdeExt.getDate() - 30)
  const hastaExt = new Date(hasta); hastaExt.setDate(hastaExt.getDate() + 60)

  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  const esSuperadmin = usuario.rol === 'SUPERADMIN'
  const empresaId = esSuperadmin
    ? JSON.parse(sessionStorage.getItem('empresaActiva') || 'null')?.id
    : null

  let url = `/api/empresa/calendario/?desde=${fmt(desdeExt)}&hasta=${fmt(hastaExt)}`
  if (empresaId) url += `&empresa_id=${empresaId}`

  try {
    const res = await apiFetch(url)
    if (res.ok) todos.value = await res.json()
  } catch {}
  cargando.value = false
}

// ── Días del mes en el grid ────────────────────────────────────────────────
const diasGrid = computed(() => {
  const primero = new Date(anioActual.value, mesActual.value, 1)
  // lunes = 0, domingo = 6
  let dow = primero.getDay() - 1
  if (dow < 0) dow = 6

  const dias = []
  // Días del mes anterior para completar primera semana
  for (let i = dow - 1; i >= 0; i--) {
    const d = new Date(anioActual.value, mesActual.value, -i)
    dias.push({ fecha: fmt(d), otroMes: true })
  }
  // Días del mes actual
  const ultimo = new Date(anioActual.value, mesActual.value + 1, 0).getDate()
  for (let d = 1; d <= ultimo; d++) {
    const fecha = new Date(anioActual.value, mesActual.value, d)
    dias.push({ fecha: fmt(fecha), otroMes: false })
  }
  // Completar hasta múltiplo de 7
  while (dias.length % 7 !== 0) {
    const extra = new Date(anioActual.value, mesActual.value + 1, dias.length - (dow + ultimo) + 1)
    dias.push({ fecha: fmt(extra), otroMes: true })
  }
  return dias
})

function fmt(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

// Eventos filtrados por tipos activos
const eventosFiltrados = computed(() =>
  todos.value.filter(e => filtrosActivos.value.has(e.tipo))
)

// Mapa fecha → eventos (solo para el mes visible + margen docs)
const eventosPorFecha = computed(() => {
  const map = {}
  for (const e of eventosFiltrados.value) {
    if (!map[e.fecha]) map[e.fecha] = []
    map[e.fecha].push(e)
  }
  return map
})

// ── Día seleccionado ───────────────────────────────────────────────────────
const diaSeleccionado = ref(null)
const eventosDia = computed(() =>
  diaSeleccionado.value ? (eventosPorFecha.value[diaSeleccionado.value] || []) : []
)

function seleccionarDia(fecha) {
  diaSeleccionado.value = diaSeleccionado.value === fecha ? null : fecha
}

// Formatear fecha legible
function fmtFechaLegible(isoStr) {
  const [y, m, d] = isoStr.split('-').map(Number)
  return `${d} de ${MESES[m-1]} ${y}`
}

function esHoy(fecha) {
  return fecha === fmt(hoy)
}

// ── Watcher mes/año ────────────────────────────────────────────────────────
watch([mesActual, anioActual], () => {
  diaSeleccionado.value = null
  cargar()
})

onMounted(cargar)

// ── Navegación a la URL del evento ────────────────────────────────────────
import { useRouter } from 'vue-router'
const router = useRouter()
const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const prefijo = usuario.rol === 'USUARIO' ? '/empresa' : ''

function irA(url) {
  router.push(prefijo + url)
}

// ── Etiquetas de tipo ──────────────────────────────────────────────────────
const TIPO_LABEL = {
  ruta:                  'Ruta',
  mantencion:            'Mantención',
  mantencion_predictiva: 'Predictivo',
  documento:             'Documento',
  solicitud:             'Solicitud',
}
</script>

<template>
  <div class="px-6 py-6 max-w-[1400px] mx-auto">

    <!-- ── Cabecera ───────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Calendario global</h1>
        <p class="text-sm text-gray-500 mt-0.5">Rutas, mantenciones, documentos y solicitudes en una sola vista</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="irHoy"
          class="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition">
          Hoy
        </button>
        <button @click="irMes(-1)"
          class="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition text-gray-500">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <span class="min-w-[160px] text-center text-base font-semibold text-gray-800">
          {{ MESES[mesActual] }} {{ anioActual }}
        </span>
        <button @click="irMes(1)"
          class="w-8 h-8 flex items-center justify-center rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition text-gray-500">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- ── Filtros de tipo ────────────────────────────────────────────────── -->
    <div class="flex flex-wrap gap-2 mb-5">
      <button
        v-for="f in FILTROS"
        :key="f.tipo"
        @click="toggleFiltro(f.tipo)"
        :class="[
          'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition select-none',
          filtrosActivos.has(f.tipo)
            ? pal(f.color).chip
            : 'bg-white border-gray-200 text-gray-400 opacity-60'
        ]"
      >
        <span :class="['w-2 h-2 rounded-full', pal(f.color).dot]"/>
        {{ f.label }}
        <span class="ml-0.5 text-xs opacity-70 font-normal">
          {{ todos.filter(e => e.tipo === f.tipo).length }}
        </span>
      </button>
      <span v-if="cargando" class="flex items-center gap-1.5 text-sm text-gray-400 ml-2">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        Cargando…
      </span>
    </div>

    <!-- ── Layout principal: Calendario + Panel lateral ──────────────────── -->
    <div class="flex gap-5 items-start">

      <!-- Calendario -->
      <div class="flex-1 min-w-0 bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">

        <!-- Días de semana -->
        <div class="grid grid-cols-7 border-b border-gray-100">
          <div v-for="d in DIAS_SEMANA" :key="d"
            class="py-2 text-center text-xs font-semibold text-gray-400 uppercase tracking-wider">
            {{ d }}
          </div>
        </div>

        <!-- Grid de días -->
        <div class="grid grid-cols-7 divide-x divide-y divide-gray-100">
          <div
            v-for="dia in diasGrid"
            :key="dia.fecha"
            @click="seleccionarDia(dia.fecha)"
            :class="[
              'min-h-[110px] p-1.5 cursor-pointer transition-colors',
              dia.otroMes ? 'bg-gray-50/50' : 'bg-white hover:bg-indigo-50/30',
              diaSeleccionado === dia.fecha ? 'ring-2 ring-inset ring-indigo-400 bg-indigo-50/40' : '',
            ]"
          >
            <!-- Número del día -->
            <div class="flex justify-end mb-1">
              <span :class="[
                'w-7 h-7 flex items-center justify-center text-sm font-medium rounded-full',
                esHoy(dia.fecha) ? 'bg-indigo-600 text-white font-bold' :
                dia.otroMes ? 'text-gray-300' : 'text-gray-700',
              ]">
                {{ Number(dia.fecha.split('-')[2]) }}
              </span>
            </div>

            <!-- Chips de eventos -->
            <div class="space-y-0.5">
              <template v-for="(ev, idx) in (eventosPorFecha[dia.fecha] || [])" :key="ev.id">
                <div
                  v-if="idx < 3"
                  :class="['rounded px-1.5 py-0.5 text-[11px] font-medium truncate leading-tight', pal(ev.color).chip]"
                  :title="ev.titulo + ' · ' + ev.subtitulo"
                >
                  {{ pal(ev.color).icono }} {{ ev.titulo }}
                </div>
              </template>
              <div
                v-if="(eventosPorFecha[dia.fecha] || []).length > 3"
                class="text-[11px] text-gray-400 font-medium px-1 leading-tight"
              >
                +{{ (eventosPorFecha[dia.fecha] || []).length - 3 }} más
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel lateral del día seleccionado -->
      <Transition name="panel-slide">
        <div
          v-if="diaSeleccionado"
          class="w-80 shrink-0 bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden"
        >
          <!-- Cabecera del panel -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <div>
              <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">
                {{ ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'][new Date(diaSeleccionado + 'T12:00').getDay()] }}
              </p>
              <p class="text-base font-bold text-gray-900">{{ fmtFechaLegible(diaSeleccionado) }}</p>
            </div>
            <button @click="diaSeleccionado = null"
              class="w-7 h-7 flex items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Lista de eventos del día -->
          <div class="divide-y divide-gray-50 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div v-if="eventosDia.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">
              Sin eventos para este día
            </div>

            <div
              v-for="ev in eventosDia"
              :key="ev.id"
              @click="irA(ev.url)"
              :class="['flex gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition group']"
            >
              <!-- Dot + icono -->
              <div class="flex flex-col items-center pt-0.5 gap-1 shrink-0">
                <span :class="['w-2.5 h-2.5 rounded-full mt-0.5', pal(ev.color).dot]"/>
              </div>

              <!-- Contenido -->
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-1 mb-0.5">
                  <p class="text-sm font-semibold text-gray-800 leading-tight truncate">{{ ev.titulo }}</p>
                  <span v-if="ev.hora" class="text-xs text-gray-400 shrink-0 mt-0.5">{{ ev.hora }}</span>
                </div>
                <p class="text-xs text-gray-500 leading-snug truncate">{{ ev.subtitulo }}</p>
                <div class="flex items-center gap-1.5 mt-1.5">
                  <span :class="['text-[11px] font-medium px-1.5 py-0.5 rounded-full', pal(ev.color).chip]">
                    {{ TIPO_LABEL[ev.tipo] ?? ev.tipo }}
                  </span>
                </div>
              </div>

              <!-- Flecha hover -->
              <svg class="w-4 h-4 text-gray-300 shrink-0 mt-1 group-hover:text-gray-500 transition"
                fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </div>

          <!-- Footer con resumen -->
          <div class="px-4 py-3 border-t border-gray-100 bg-gray-50">
            <div class="flex flex-wrap gap-2">
              <template v-for="f in FILTROS" :key="f.tipo">
                <span
                  v-if="eventosDia.filter(e => e.tipo === f.tipo).length > 0"
                  :class="['text-[11px] px-2 py-0.5 rounded-full font-medium', pal(f.color).chip]"
                >
                  {{ eventosDia.filter(e => e.tipo === f.tipo).length }} {{ f.label.toLowerCase() }}
                </span>
              </template>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Placeholder cuando no hay día seleccionado -->
      <div v-if="!diaSeleccionado" class="w-80 shrink-0 hidden lg:flex flex-col items-center justify-center py-16 bg-white border border-dashed border-gray-200 rounded-2xl text-center">
        <svg class="w-10 h-10 text-gray-300 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"/>
        </svg>
        <p class="text-sm font-medium text-gray-400">Selecciona un día</p>
        <p class="text-xs text-gray-300 mt-1">para ver sus eventos</p>
      </div>

    </div>

    <!-- ── Leyenda inferior ───────────────────────────────────────────────── -->
    <div class="mt-5 flex flex-wrap gap-4 text-xs text-gray-500">
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-indigo-500"/> Ruta pendiente</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-green-500"/> Ruta activa</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-slate-400"/> Ruta finalizada</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-orange-500"/> Mantención</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500"/> Predictivo</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-red-500"/> Doc. vencido / próximo</div>
      <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-purple-500"/> Solicitud</div>
    </div>

  </div>
</template>

<style scoped>
.panel-slide-enter-active { transition: all 0.2s ease; }
.panel-slide-leave-active { transition: all 0.15s ease; }
.panel-slide-enter-from  { opacity: 0; transform: translateX(12px); }
.panel-slide-leave-to    { opacity: 0; transform: translateX(12px); }
</style>
