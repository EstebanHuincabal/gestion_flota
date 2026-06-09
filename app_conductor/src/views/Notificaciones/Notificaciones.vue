<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '@/services/api.js'
import BottomNav from '@/components/BottomNav.vue'
import { agruparPorFecha } from '@/utils/formato.js'

const router = useRouter()

const notificaciones = ref([])
const cargando       = ref(true)
const cargandoMas    = ref(false)
const error          = ref('')
const pagina         = ref(1)
const totalPaginas   = ref(1)

const notificacionesAgrupadas = computed(() =>
  agruparPorFecha(notificaciones.value, n => n.fecha),
)

const hayNoLeidas = computed(() => notificaciones.value.some(n => !n.leida))

async function cargar() {
  cargando.value = true
  error.value    = ''
  try {
    const data = await apiFetch('/api/notificaciones/?page=1')
    notificaciones.value = data.results || []
    pagina.value       = 1
    totalPaginas.value = data.num_pages || 1
  } catch {
    error.value = 'No se pudieron cargar las notificaciones.'
  } finally {
    cargando.value = false
  }
}

async function cargarMas() {
  if (pagina.value >= totalPaginas.value) return
  cargandoMas.value = true
  try {
    const data = await apiFetch(`/api/notificaciones/?page=${pagina.value + 1}`)
    notificaciones.value.push(...(data.results || []))
    pagina.value       += 1
    totalPaginas.value  = data.num_pages || 1
  } catch {
    // Silencioso: el botón "Cargar más" sigue disponible para reintentar
  } finally {
    cargandoMas.value = false
  }
}

async function marcarTodas() {
  try {
    await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: JSON.stringify({ todas: true }) })
    notificaciones.value.forEach(n => { n.leida = true })
  } catch {
    // Silencioso
  }
}

// ── Notificación abierta (modal con el mensaje completo) ─────────────────────
const notifAbierta = ref(null)
function cerrar() { notifAbierta.value = null }

async function abrir(n) {
  if (!n.leida) {
    n.leida = true
    try {
      await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: JSON.stringify({ ids: [n.id] }) })
    } catch {
      // Silencioso: ya se marcó como leída en pantalla
    }
  }
  if (n.url_accion) {
    router.push(n.url_accion)
  } else {
    notifAbierta.value = n
  }
}

// ── Helpers de UI ─────────────────────────────────────────────────────────────
const TIPOS_INFO = {
  actividad:               { icono: 'ti-bell',           color: '#6366F1', colorSuave: '#EEF2FF' },
  mantencion_por_vencer:   { icono: 'ti-tool',            color: '#B45309', colorSuave: '#FEF3C7' },
  mantencion_vencida:      { icono: 'ti-tool',            color: '#B91C1C', colorSuave: '#FEE2E2' },
  documento_por_vencer:    { icono: 'ti-file-text',       color: '#B45309', colorSuave: '#FEF3C7' },
  documento_vencido:       { icono: 'ti-file-text',       color: '#B91C1C', colorSuave: '#FEE2E2' },
  seguridad:               { icono: 'ti-shield-check',    color: '#085041', colorSuave: '#E1F5EE' },
  limite_plan:             { icono: 'ti-alert-circle',    color: '#B45309', colorSuave: '#FEF3C7' },
  recordatorio_ruta:       { icono: 'ti-clock',           color: '#534AB7', colorSuave: '#EEEDFE' },
  recordatorio_checklist:  { icono: 'ti-clipboard-check', color: '#534AB7', colorSuave: '#EEEDFE' },
  recordatorio_finalizar:  { icono: 'ti-flag',            color: '#534AB7', colorSuave: '#EEEDFE' },
  recordatorio_vispera:    { icono: 'ti-calendar-event',  color: '#534AB7', colorSuave: '#EEEDFE' },
  recordatorio_documentos: { icono: 'ti-file-text',       color: '#B45309', colorSuave: '#FEF3C7' },
  checklist_completado:    { icono: 'ti-circle-check',    color: '#085041', colorSuave: '#E1F5EE' },
  checklist_enviado:       { icono: 'ti-alert-triangle',  color: '#A32D2D', colorSuave: '#FCEBEB' },
}
const DEFAULT_TIPO_INFO = { icono: 'ti-bell', color: '#6366F1', colorSuave: '#EEF2FF' }

function tipoInfo(tipo) {
  return TIPOS_INFO[tipo] || DEFAULT_TIPO_INFO
}

function tiempoDesde(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr).getTime()
  const min  = Math.floor(diff / 60000)
  if (min < 1)  return 'Ahora'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24)   return `hace ${h}h`
  const d = Math.floor(h / 24)
  if (d < 30)   return `hace ${d} días`
  const m = Math.floor(d / 30)
  return `hace ${m} mes${m > 1 ? 'es' : ''}`
}

function formatFecha(isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleString('es-CL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(cargar)
</script>

<template>
  <div class="not-page">
    <!-- Cabecera ─────────────────────────────────────────────────────────── -->
    <div class="not-header">
      <button class="not-back" @click="router.back()">
        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="not-title">Notificaciones</h1>
      <button v-if="hayNoLeidas" class="not-marcar-btn" @click="marcarTodas">
        Marcar todas
      </button>
    </div>

    <!-- Error ────────────────────────────────────────────────────────────── -->
    <div v-if="error" class="not-error">{{ error }}</div>

    <!-- Loading ──────────────────────────────────────────────────────────── -->
    <div v-if="cargando" class="not-loading">
      <div class="not-spinner"/>
    </div>

    <!-- Vacío ────────────────────────────────────────────────────────────── -->
    <div v-else-if="!notificaciones.length" class="not-empty">
      <p class="not-empty-icon">🔔</p>
      <p class="not-empty-msg">Sin notificaciones</p>
      <p class="not-empty-sub">Aquí aparecerán tus avisos de rutas, mantenciones y solicitudes.</p>
    </div>

    <!-- Lista ────────────────────────────────────────────────────────────── -->
    <div v-else class="not-list">
      <div v-for="grupo in notificacionesAgrupadas" :key="grupo.label" class="not-group">
        <p class="not-group-label">{{ grupo.label }}</p>
        <div class="flex flex-col gap-2">
          <button
            v-for="n in grupo.items"
            :key="n.id"
            class="not-card"
            :class="{ 'not-card--no-leida': !n.leida }"
            @click="abrir(n)"
          >
            <div class="not-card-icon" :style="`background: ${tipoInfo(n.tipo).colorSuave}`">
              <i class="ti text-base" :class="tipoInfo(n.tipo).icono" :style="`color: ${tipoInfo(n.tipo).color}`"/>
            </div>
            <div class="not-card-body">
              <div class="not-card-header">
                <p class="not-card-titulo" :class="{ 'not-card-titulo--no-leida': !n.leida }">{{ n.titulo }}</p>
                <span class="not-fecha">{{ tiempoDesde(n.fecha) }}</span>
              </div>
              <p class="not-card-msg">{{ n.mensaje }}</p>
            </div>
            <span v-if="!n.leida" class="not-dot"/>
          </button>
        </div>
      </div>

      <!-- Cargar más ─────────────────────────────────────────────────────── -->
      <button
        v-if="pagina < totalPaginas"
        class="not-cargar-mas"
        :disabled="cargandoMas"
        @click="cargarMas"
      >
        {{ cargandoMas ? 'Cargando…' : 'Cargar más' }}
      </button>
    </div>
  </div>
  <BottomNav />

  <!-- ── Modal de lectura ──────────────────────────────────────────────────── -->
  <Transition name="modal">
    <div v-if="notifAbierta" class="not-overlay" @click.self="cerrar">
      <div class="not-modal">
        <div class="not-modal-handle"/>
        <div class="not-modal-meta">
          <div class="not-card-icon" :style="`background: ${tipoInfo(notifAbierta.tipo).colorSuave}`">
            <i class="ti text-base" :class="tipoInfo(notifAbierta.tipo).icono" :style="`color: ${tipoInfo(notifAbierta.tipo).color}`"/>
          </div>
          <span class="not-fecha">{{ formatFecha(notifAbierta.fecha) }}</span>
        </div>
        <h2 class="not-modal-titulo">{{ notifAbierta.titulo }}</h2>
        <p class="not-modal-msg">{{ notifAbierta.mensaje }}</p>
        <button class="not-modal-close" @click="cerrar">Cerrar</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.not-page { min-height:100dvh; background:#F9FAFB; padding-bottom:5rem; }

.not-header { display:flex; align-items:center; gap:.75rem; padding:max(1rem,env(safe-area-inset-top)) 1rem .75rem; background:#fff; border-bottom:1px solid #E5E7EB; position:sticky; top:0; z-index:10; }
.not-back   { background:none; border:none; padding:.35rem; border-radius:8px; cursor:pointer; color:#374151; }
.not-title  { flex:1; font-size:1.1rem; font-weight:700; color:#1E1B4B; }
.not-marcar-btn { background:none; border:none; padding:.35rem .5rem; font-size:.8rem; font-weight:600; color:#6366F1; cursor:pointer; }

.not-error  { background:#FEF2F2; color:#B91C1C; border-radius:10px; padding:.75rem 1rem; margin:1rem; font-size:.875rem; }

.not-loading { display:flex; justify-content:center; padding:3rem; }
.not-spinner { width:1.5rem; height:1.5rem; border:2px solid #E5E7EB; border-top-color:#6366F1; border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

.not-empty      { text-align:center; padding:3rem 1rem; }
.not-empty-icon { font-size:2.5rem; }
.not-empty-msg  { font-size:1rem; font-weight:700; color:#1E1B4B; margin:.5rem 0 .25rem; }
.not-empty-sub  { font-size:.875rem; color:#9CA3AF; }

/* Lista */
.not-list { padding:1rem; display:flex; flex-direction:column; gap:1rem; }
.not-group-label { font-size:.6875rem; font-weight:600; color:#B0B6C0; margin-bottom:.375rem; }
.not-card {
  display:flex; align-items:flex-start; gap:.75rem;
  background:#fff; border-radius:12px; padding:.85rem;
  box-shadow:0 1px 4px rgba(0,0,0,.06);
  border:none; text-align:left; width:100%; cursor:pointer;
  transition:transform .1s;
  -webkit-tap-highlight-color: transparent;
}
.not-card:active { transform:scale(.98); }
.not-card--no-leida { background:#EEF2FF; }

.not-card-icon { flex-shrink:0; width:2.25rem; height:2.25rem; border-radius:.65rem; display:flex; align-items:center; justify-content:center; }
.not-card-body { flex:1; min-width:0; }
.not-card-header { display:flex; justify-content:space-between; align-items:flex-start; gap:.5rem; margin-bottom:.2rem; }
.not-card-titulo { font-size:.875rem; font-weight:600; color:#374151; }
.not-card-titulo--no-leida { font-weight:700; color:#1E1B4B; }
.not-fecha  { font-size:.7rem; color:#9CA3AF; flex-shrink:0; white-space:nowrap; }
.not-card-msg {
  font-size:.8125rem; color:#6B7280; line-height:1.45;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.not-dot { flex-shrink:0; width:.5rem; height:.5rem; border-radius:50%; background:#6366F1; margin-top:.4rem; }

.not-cargar-mas {
  margin-top:.25rem; background:#fff; border:1px solid #E5E7EB; border-radius:10px;
  padding:.65rem; font-size:.8125rem; font-weight:600; color:#6366F1; cursor:pointer;
}
.not-cargar-mas:disabled { opacity:.6; cursor:not-allowed; }

/* Modal */
.not-overlay {
  position:fixed; inset:0; z-index:100;
  background:rgba(0,0,0,.45);
  display:flex; align-items:flex-end;
  padding-bottom:env(safe-area-inset-bottom, 0px);
}
.not-modal {
  background:#fff;
  border-radius:20px 20px 0 0;
  padding:1.25rem 1.25rem calc(1.5rem + env(safe-area-inset-bottom, 0px));
  width:100%;
  max-height:80dvh;
  overflow-y:auto;
}
.not-modal-handle { width:2.5rem; height:4px; border-radius:2px; background:#D1D5DB; margin:0 auto 1rem; }
.not-modal-meta   { display:flex; align-items:center; justify-content:space-between; margin-bottom:.85rem; }
.not-modal-titulo { font-size:1.05rem; font-weight:700; color:#1E1B4B; margin-bottom:.75rem; line-height:1.35; }
.not-modal-msg    { font-size:.9rem; color:#374151; white-space:pre-wrap; line-height:1.65; margin-bottom:1.5rem; }
.not-modal-close  {
  width:100%; background:#F3F4F6; color:#374151;
  border:none; border-radius:12px; padding:.75rem;
  font-size:.9rem; font-weight:600; cursor:pointer;
}

/* Transiciones */
.modal-enter-active, .modal-leave-active { transition:all .25s ease; }
.modal-enter-from, .modal-leave-to { opacity:0; }
.modal-enter-active .not-modal, .modal-leave-active .not-modal { transition:transform .25s ease; }
.modal-enter-from .not-modal, .modal-leave-to .not-modal { transform:translateY(100%); }
</style>
