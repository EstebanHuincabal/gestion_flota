<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '@/services/api.js'
import BottomNav from '@/components/BottomNav.vue'
import { useModeracion } from '@/composables/useModeracion.js'

const router   = useRouter()
const avisos   = ref([])
const cargando = ref(true)
const error    = ref('')

// ── Aviso abierto (modal) ─────────────────────────────────────────────────────
const avisoAbierto = ref(null)
function abrir(a)  { avisoAbierto.value = a }
function cerrar()  { avisoAbierto.value = null }

// ── Form nuevo aviso ──────────────────────────────────────────────────────────
const mostrarForm = ref(false)
const enviando    = ref(false)
const form        = ref({ asunto: '', mensaje: '' })
const errForm     = ref({})
const exito       = ref(false)
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()

async function cargar() {
  cargando.value = true
  error.value    = ''
  try {
    avisos.value = await apiFetch('/api/conductor/avisos/')
  } catch {
    error.value = 'No se pudieron cargar los avisos.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

async function enviar() {
  errForm.value = {}
  exito.value   = false
  if (!form.value.asunto.trim())  { errForm.value.asunto  = 'El asunto es obligatorio.'; return }
  if (!form.value.mensaje.trim()) { errForm.value.mensaje = 'El mensaje es obligatorio.'; return }

  limpiarMod()
  const ok = await moderar(form.value.asunto + ' ' + form.value.mensaje)
  if (!ok) return

  enviando.value = true
  try {
    await apiFetch('/api/conductor/avisos/', {
      method: 'POST',
      body: JSON.stringify({ asunto: form.value.asunto.trim(), mensaje: form.value.mensaje.trim() }),
    })
    exito.value       = true
    form.value        = { asunto: '', mensaje: '' }
    mostrarForm.value = false
    await cargar()
  } catch (e) {
    error.value = e.message || 'Error al enviar el aviso.'
  } finally {
    enviando.value = false
  }
}

function formatFecha(iso) {
  return new Date(iso).toLocaleString('es-CL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function nombreRemitente(a) {
  // Si lo envió el conductor (él mismo), lo dice; si no, muestra el nombre de la empresa.
  return a.emisor_rol === 'CONDUCTOR' ? 'Tú' : (a.empresa_nombre || 'Empresa')
}
</script>

<template>
  <div class="av-page">
    <!-- Cabecera ─────────────────────────────────────────────────────────── -->
    <div class="av-header">
      <button class="av-back" @click="router.back()">
        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="av-title">Avisos</h1>
      <button class="av-compose-btn" @click="mostrarForm = !mostrarForm" title="Escribir al admin">
        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
      </button>
    </div>

    <!-- Aviso de éxito ───────────────────────────────────────────────────── -->
    <div v-if="exito" class="av-success">✓ Aviso enviado al administrador.</div>

    <!-- Form enviar aviso ────────────────────────────────────────────────── -->
    <Transition name="slide">
      <div v-if="mostrarForm" class="av-form-card">
        <p class="av-form-titulo">Escribir al administrador</p>
        <div class="av-field">
          <label class="av-label">Asunto</label>
          <input v-model="form.asunto" type="text" class="av-input" :class="errForm.asunto && 'av-input-err'"
            placeholder="Ej: Consulta sobre turno" maxlength="150" autocomplete="off"/>
          <p v-if="errForm.asunto" class="av-err">{{ errForm.asunto }}</p>
        </div>
        <div class="av-field">
          <label class="av-label">Mensaje</label>
          <textarea v-model="form.mensaje" class="av-input" :class="errForm.mensaje && 'av-input-err'"
            placeholder="Escribe tu mensaje…" rows="4" maxlength="2000" style="resize:none;"/>
          <p v-if="errForm.mensaje" class="av-err">{{ errForm.mensaje }}</p>
        </div>
        <div v-if="avisoMod" class="av-mod-aviso">
          <span class="av-mod-titulo">Lenguaje inapropiado</span>
          <span class="av-mod-texto">{{ avisoMod }}</span>
          <span v-if="sugerenciaMod" class="av-mod-sug">{{ sugerenciaMod }}</span>
        </div>
        <div class="av-form-btns">
          <button class="av-btn-cancel" @click="mostrarForm = false">Cancelar</button>
          <button class="av-btn-send" :disabled="enviando" @click="enviar">
            {{ enviando ? 'Enviando…' : 'Enviar' }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- Error ────────────────────────────────────────────────────────────── -->
    <div v-if="error" class="av-error">{{ error }}</div>

    <!-- Loading ──────────────────────────────────────────────────────────── -->
    <div v-if="cargando" class="av-loading">
      <div class="av-spinner"/>
    </div>

    <!-- Vacío ────────────────────────────────────────────────────────────── -->
    <div v-else-if="!avisos.length && !mostrarForm" class="av-empty">
      <p class="av-empty-icon">📭</p>
      <p class="av-empty-msg">No tienes avisos aún.</p>
      <p class="av-empty-sub">Cuando la empresa envíe un aviso aparecerá aquí.</p>
      <button class="av-btn-send mt-4" @click="mostrarForm = true">Escribir al administrador</button>
    </div>

    <!-- Lista ────────────────────────────────────────────────────────────── -->
    <div v-else class="av-list">
      <div v-for="a in avisos" :key="a.id" class="av-card" @click="abrir(a)">
        <div class="av-card-header">
          <span class="av-badge" :class="a.emisor_rol === 'CONDUCTOR' ? 'av-badge-cond' : 'av-badge-admin'">
            {{ nombreRemitente(a) }}
          </span>
          <span class="av-fecha">{{ formatFecha(a.fecha) }}</span>
        </div>
        <p class="av-asunto">{{ a.asunto }}</p>
        <!-- Vista previa recortada -->
        <p class="av-msg-preview">{{ a.mensaje }}</p>
        <span class="av-leer">Leer mensaje →</span>
      </div>
    </div>
  </div>
  <BottomNav />

  <!-- ── Modal de lectura ──────────────────────────────────────────────────── -->
  <Transition name="modal">
    <div v-if="avisoAbierto" class="av-overlay" @click.self="cerrar">
      <div class="av-modal">
        <!-- Handle -->
        <div class="av-modal-handle"/>

        <!-- Remitente + fecha -->
        <div class="av-modal-meta">
          <span class="av-badge" :class="avisoAbierto.emisor_rol === 'CONDUCTOR' ? 'av-badge-cond' : 'av-badge-admin'">
            {{ nombreRemitente(avisoAbierto) }}
          </span>
          <span class="av-fecha">{{ formatFecha(avisoAbierto.fecha) }}</span>
        </div>

        <!-- Asunto -->
        <h2 class="av-modal-asunto">{{ avisoAbierto.asunto }}</h2>

        <!-- Mensaje completo -->
        <p class="av-modal-msg">{{ avisoAbierto.mensaje }}</p>

        <button class="av-modal-close" @click="cerrar">Cerrar</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.av-page  { min-height:100dvh; background:#F9FAFB; padding-bottom:5rem; }

.av-header { display:flex; align-items:center; gap:.75rem; padding:max(1rem,env(safe-area-inset-top)) 1rem .75rem; background:#fff; border-bottom:1px solid #E5E7EB; position:sticky; top:0; z-index:10; }
.av-back   { background:none; border:none; padding:.35rem; border-radius:8px; cursor:pointer; color:#374151; }
.av-title  { flex:1; font-size:1.1rem; font-weight:700; color:#1E1B4B; }
.av-compose-btn { background:none; border:none; padding:.35rem; border-radius:8px; cursor:pointer; color:#6366F1; }

.av-success { background:#ECFDF5; color:#065F46; border-radius:10px; padding:.75rem 1rem; margin:1rem; font-size:.875rem; font-weight:600; }
.av-error   { background:#FEF2F2; color:#B91C1C; border-radius:10px; padding:.75rem 1rem; margin:1rem; font-size:.875rem; }

.av-form-card   { background:#fff; border-radius:14px; margin:1rem; padding:1.25rem; box-shadow:0 2px 8px rgba(0,0,0,.08); }
.av-form-titulo { font-size:.95rem; font-weight:700; color:#1E1B4B; margin-bottom:1rem; }
.av-field  { margin-bottom:.9rem; }
.av-label  { display:block; font-size:.75rem; font-weight:600; color:#374151; text-transform:uppercase; letter-spacing:.05em; margin-bottom:.35rem; }
.av-input  { width:100%; border:1.5px solid #D1D5DB; border-radius:10px; padding:.6rem .85rem; font-size:.875rem; font-family:inherit; box-sizing:border-box; }
.av-input:focus { outline:none; border-color:#6366F1; }
.av-input-err  { border-color:#EF4444 !important; }
.av-err    { font-size:.75rem; color:#EF4444; margin-top:.2rem; }
.av-form-btns  { display:flex; gap:.75rem; justify-content:flex-end; margin-top:.5rem; }
.av-btn-cancel { background:#F3F4F6; color:#374151; border:none; border-radius:10px; padding:.55rem 1rem; font-size:.875rem; font-weight:600; cursor:pointer; }
.av-btn-send   { background:#6366F1; color:#fff; border:none; border-radius:10px; padding:.55rem 1.1rem; font-size:.875rem; font-weight:600; cursor:pointer; }
.av-btn-send:disabled { opacity:.6; cursor:not-allowed; }
.mt-4 { margin-top:1rem; }

.av-loading { display:flex; justify-content:center; padding:3rem; }
.av-spinner { width:1.5rem; height:1.5rem; border:2px solid #E5E7EB; border-top-color:#6366F1; border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

.av-empty      { text-align:center; padding:3rem 1rem; }
.av-empty-icon { font-size:2.5rem; }
.av-empty-msg  { font-size:1rem; font-weight:700; color:#1E1B4B; margin:.5rem 0 .25rem; }
.av-empty-sub  { font-size:.875rem; color:#9CA3AF; }

/* Lista */
.av-list  { padding:1rem; display:flex; flex-direction:column; gap:.75rem; }
.av-card  { background:#fff; border-radius:12px; padding:1rem; box-shadow:0 1px 4px rgba(0,0,0,.06); cursor:pointer; transition:transform .1s; }
.av-card:active { transform:scale(.98); }
.av-card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:.4rem; }
.av-badge       { font-size:.7rem; font-weight:700; padding:.2rem .55rem; border-radius:20px; }
.av-badge-admin { background:#EFF6FF; color:#1D4ED8; }
.av-badge-cond  { background:#F0FDF4; color:#15803D; }
.av-fecha       { font-size:.7rem; color:#9CA3AF; }
.av-asunto      { font-size:.9rem; font-weight:700; color:#1E1B4B; margin-bottom:.3rem; }
/* Vista previa — recorta en 2 líneas */
.av-msg-preview {
  font-size:.85rem; color:#6B7280; line-height:1.5;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  margin-bottom:.4rem;
}
.av-leer { font-size:.75rem; color:#6366F1; font-weight:600; }

/* Modal */
.av-overlay {
  position:fixed; inset:0; z-index:100;
  background:rgba(0,0,0,.45);
  display:flex; align-items:flex-end;
  padding-bottom:env(safe-area-inset-bottom, 0px);
}
.av-modal {
  background:#fff;
  border-radius:20px 20px 0 0;
  padding:1.25rem 1.25rem calc(1.5rem + env(safe-area-inset-bottom, 0px));
  width:100%;
  max-height:80dvh;
  overflow-y:auto;
}
.av-modal-handle {
  width:2.5rem; height:4px; border-radius:2px;
  background:#D1D5DB; margin:0 auto 1rem;
}
.av-modal-meta   { display:flex; align-items:center; gap:.5rem; margin-bottom:.85rem; }
.av-modal-asunto { font-size:1.05rem; font-weight:700; color:#1E1B4B; margin-bottom:.75rem; line-height:1.35; }
.av-modal-msg    { font-size:.9rem; color:#374151; white-space:pre-wrap; line-height:1.65; margin-bottom:1.5rem; }
.av-modal-close  {
  width:100%; background:#F3F4F6; color:#374151;
  border:none; border-radius:12px; padding:.75rem;
  font-size:.9rem; font-weight:600; cursor:pointer;
}

/* Transiciones */
.slide-enter-active, .slide-leave-active { transition:all .2s ease; }
.slide-enter-from, .slide-leave-to { opacity:0; transform:translateY(-8px); }

.modal-enter-active, .modal-leave-active { transition:all .25s ease; }
.modal-enter-from, .modal-leave-to { opacity:0; }
.modal-enter-active .av-modal, .modal-leave-active .av-modal { transition:transform .25s ease; }
.modal-enter-from .av-modal, .modal-leave-to .av-modal { transform:translateY(100%); }

.av-mod-aviso {
  display:flex; flex-direction:column; gap:.2rem;
  background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px;
  padding:.6rem .85rem; margin-bottom:.75rem;
}
.av-mod-titulo { font-size:.7rem; font-weight:700; color:#92400E; text-transform:uppercase; letter-spacing:.04em; }
.av-mod-texto  { font-size:.8rem; color:#78350F; }
.av-mod-sug    { font-size:.75rem; color:#A16207; font-style:italic; }
</style>
