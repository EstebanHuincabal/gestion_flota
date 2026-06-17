<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { getEmpresaActiva, EMPRESA_TODAS } from '../../utils/empresaActiva.js'
import { useToast } from '../../utils/useToast.js'
import { useModeracion } from '../../composables/useModeracion.js'
import AvisoModeracion from '../../components/AvisoModeracion.vue'

const toast = useToast()
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod } = useModeracion()
const esTodas = computed(() => getEmpresaActiva()?.id === EMPRESA_TODAS)

// ── Estado ────────────────────────────────────────────────────────────────────
const avisos           = ref([])
const conductores      = ref([])   // conductores de la empresa activa (usuario normal)
const conductoresForm  = ref([])   // conductores del empresa seleccionada en el form (superadmin)
const empresasList     = ref([])   // lista de empresas para el selector del form (superadmin)
const cargandoCond     = ref(false)
const cargando         = ref(true)
const enviando         = ref(false)
const error            = ref('')
const mostrarForm      = ref(false)

const form = ref({ destino: 'flota', destinatario_id: null, empresaId: '', asunto: '', mensaje: '' })
const errForm = ref({})

// ── Permisos ──────────────────────────────────────────────────────────────────
const planPermisos = computed(() => {
  try { return JSON.parse(sessionStorage.getItem('plan_permisos') || '[]') } catch { return [] }
})
const esSuperAdmin = computed(() => {
  try { return JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN' } catch { return false }
})
const puedeEnviar = computed(() => esSuperAdmin.value || planPermisos.value.includes('avisos.enviar'))

// Cuando el SUPERADMIN elige empresa en el form, cargar sus conductores
watch(() => form.value.empresaId, async (id) => {
  conductoresForm.value = []
  form.value.destinatario_id = null
  if (!id) return
  cargandoCond.value = true
  try {
    const res = await apiFetch(`/api/empresa/avisos/conductores/?empresa_id=${id}`)
    if (res.ok) conductoresForm.value = await res.json()
  } finally {
    cargandoCond.value = false
  }
})

// ── Carga de datos ────────────────────────────────────────────────────────────
async function cargar() {
  cargando.value = true
  try {
    const promesas = [apiFetch('/api/empresa/avisos/')]
    if (puedeEnviar.value && !esTodas.value)
      promesas.push(apiFetch('/api/empresa/avisos/conductores/'))
    else
      promesas.push(Promise.resolve(null))
    if (esSuperAdmin.value)
      promesas.push(apiFetch('/api/empresas/'))
    else
      promesas.push(Promise.resolve(null))

    const [resAv, resCond, resEmpresas] = await Promise.all(promesas)
    if (resAv.ok) avisos.value = await resAv.json()
    if (resCond?.ok) conductores.value = await resCond.json()
    if (resEmpresas?.ok) {
      const data = await resEmpresas.json()
      empresasList.value = (Array.isArray(data) ? data : []).filter(e => e.id !== EMPRESA_TODAS)
    }
  } catch {
    error.value = 'Error al cargar los avisos.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

function abrirForm() {
  if (mostrarForm.value) { mostrarForm.value = false; return }
  form.value = { destino: esTodas.value ? 'todas' : 'flota', destinatario_id: null, empresaId: '', asunto: '', mensaje: '' }
  errForm.value = {}
  mostrarForm.value = true
}

// Lista de conductores a mostrar en el form (según contexto)
const conductoresActivos = computed(() =>
  esTodas.value ? conductoresForm.value : conductores.value
)

// ── Enviar aviso ──────────────────────────────────────────────────────────────
async function enviar() {
  errForm.value = {}
  if (!form.value.asunto.trim())  { errForm.value.asunto  = 'El asunto es obligatorio.'; return }
  if (!form.value.mensaje.trim()) { errForm.value.mensaje = 'El mensaje es obligatorio.'; return }
  if (esTodas.value && form.value.destino !== 'todas' && !form.value.empresaId) {
    errForm.value.empresaId = 'Selecciona una empresa.'; return
  }
  if (form.value.destino === 'conductor' && !form.value.destinatario_id) {
    errForm.value.destinatario_id = 'Selecciona un conductor.'; return
  }

  const textoCompleto = `${form.value.asunto.trim()} ${form.value.mensaje.trim()}`
  const aprobado = await moderar(textoCompleto)
  if (!aprobado) return

  enviando.value = true
  try {
    const body = {
      destino:  form.value.destino,
      asunto:   form.value.asunto.trim(),
      mensaje:  form.value.mensaje.trim(),
      ...(esTodas.value && form.value.destino !== 'todas' ? { empresa_id: form.value.empresaId } : {}),
      ...(form.value.destino === 'conductor' ? { destinatario_id: form.value.destinatario_id } : {}),
    }
    const res  = await apiFetch('/api/empresa/avisos/', { method: 'POST', body })
    const data = await res.json()
    if (!res.ok) { error.value = data.error || 'Error al enviar el aviso.'; return }
    if (form.value.destino === 'todas') {
      toast.success(`Aviso enviado a ${data.empresas} empresa(s).`)
    } else {
      toast.success('Aviso enviado correctamente.')
      avisos.value.unshift(data)
    }
    mostrarForm.value = false
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    enviando.value = false
  }
}

// ── Filtros ───────────────────────────────────────────────────────────────────
const filtroDestino = ref('todos')
const filtroEmpresa = ref('')

const empresasEnBandeja = computed(() => {
  const map = new Map()
  for (const a of avisos.value) {
    // Los avisos globales (destino='todas') tienen empresa_nombre=null — excluirlos
    // del selector de empresa porque no pertenecen a una empresa concreta.
    if (a.empresa_nombre && a.destino !== 'todas' && !map.has(a.empresa_nombre))
      map.set(a.empresa_nombre, a.empresa_nombre)
  }
  return [...map.values()].sort()
})

const filtros = computed(() => {
  // Para los pills de tipo: si hay filtro de empresa, incluir siempre los 'todas'
  const base = filtroEmpresa.value
    ? avisos.value.filter(a => a.empresa_nombre === filtroEmpresa.value || a.destino === 'todas')
    : avisos.value
  const tipos = new Set(base.map(a => a.destino))
  const opciones = [{ key: 'todos', label: 'Todos' }]
  if (tipos.has('flota'))     opciones.push({ key: 'flota',     label: '👥 Flota' })
  if (tipos.has('conductor')) opciones.push({ key: 'conductor', label: '👤 Conductor' })
  if (tipos.has('admins'))    opciones.push({ key: 'admins',    label: '🏢 Admins' })
  if (tipos.has('todas'))     opciones.push({ key: 'todas',     label: '📢 Todas las empresas' })
  return opciones
})

const avisosFiltrados = computed(() => {
  let lista = avisos.value
  if (filtroEmpresa.value)
    // Los avisos globales (destino='todas') se muestran siempre, independientemente
    // del filtro de empresa, porque fueron enviados a TODAS incluyendo la empresa seleccionada.
    lista = lista.filter(a => a.empresa_nombre === filtroEmpresa.value || a.destino === 'todas')
  if (filtroDestino.value !== 'todos')
    lista = lista.filter(a => a.destino === filtroDestino.value)
  return lista
})

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatFecha(iso) {
  return new Date(iso).toLocaleString('es-CL', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
}

function iconoDestino(destino) {
  if (destino === 'flota')     return '👥'
  if (destino === 'conductor') return '👤'
  if (destino === 'admins')    return '🏢'
  if (destino === 'todas')     return '📢'
  if (destino === 'superadmin') return '🛠️'
  return '📢'
}

function labelDestino(destino) {
  if (destino === 'flota')     return 'Toda la flota'
  if (destino === 'conductor') return 'Conductor'
  if (destino === 'admins')    return 'Administradores'
  if (destino === 'todas')     return 'Todas las empresas'
  if (destino === 'superadmin') return 'Soporte (Superadmin)'
  return destino
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Avisos</h1>
        <p class="page-subtitle">Comunica novedades a tus conductores o recibe mensajes del equipo.</p>
      </div>
      <button v-if="puedeEnviar" class="btn-primary" @click="abrirForm">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 4v16m8-8H4"/>
        </svg>
        Nuevo aviso
      </button>
    </div>

    <!-- Form de redacción ─────────────────────────────────────────────────── -->
    <Transition name="slide-down">
      <div v-if="mostrarForm" class="compose-card">
        <h3 class="compose-title">Redactar aviso</h3>

        <div class="form-row">
          <!-- Destino -->
          <div class="form-group">
            <label class="label">Enviar a</label>
            <select v-model="form.destino" class="input select"
              @change="form.destinatario_id = null; form.empresaId = ''">
              <option value="flota">Toda la flota</option>
              <option value="conductor">Un conductor específico</option>
              <option v-if="esSuperAdmin" value="admins">Administradores de la empresa</option>
              <option v-if="!esSuperAdmin" value="superadmin">Soporte (Superadmin)</option>
              <option v-if="esSuperAdmin" value="todas">Todas las empresas</option>
            </select>
          </div>

          <!-- Empresa (SUPERADMIN en modo "Todas" enviando a flota/conductor) -->
          <div v-if="esTodas && form.destino !== 'todas'" class="form-group">
            <label class="label">Empresa</label>
            <select v-model="form.empresaId" class="input select"
              :class="errForm.empresaId && 'input-error'">
              <option value="" disabled>— Seleccionar empresa —</option>
              <option v-for="e in empresasList" :key="e.id" :value="e.id">{{ e.nombre }}</option>
            </select>
            <p v-if="errForm.empresaId" class="field-error">{{ errForm.empresaId }}</p>
          </div>
        </div>

        <!-- Conductor específico -->
        <div v-if="form.destino === 'conductor'" class="form-group">
          <label class="label">Conductor</label>
          <div v-if="esTodas && !form.empresaId" class="field-hint">Selecciona una empresa primero.</div>
          <template v-else>
            <div v-if="cargandoCond" class="field-hint">Cargando conductores…</div>
            <select v-else v-model="form.destinatario_id" class="input select"
              :class="errForm.destinatario_id && 'input-error'">
              <option :value="null" disabled>Seleccionar…</option>
              <option v-for="c in conductoresActivos" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
            <p v-if="errForm.destinatario_id" class="field-error">{{ errForm.destinatario_id }}</p>
          </template>
        </div>

        <!-- Asunto -->
        <div class="form-group">
          <label class="label">Asunto</label>
          <input v-model="form.asunto" type="text" class="input" :class="errForm.asunto && 'input-error'"
            placeholder="Ej: Cambio de turno mañana" maxlength="150" autocomplete="off"/>
          <p v-if="errForm.asunto" class="field-error">{{ errForm.asunto }}</p>
        </div>

        <!-- Mensaje -->
        <div class="form-group">
          <label class="label">Mensaje</label>
          <textarea v-model="form.mensaje" class="input" :class="errForm.mensaje && 'input-error'"
            placeholder="Escribe tu mensaje aquí…" rows="4" maxlength="2000" style="resize:vertical;"/>
          <p v-if="errForm.mensaje" class="field-error">{{ errForm.mensaje }}</p>
          <p class="char-count">{{ form.mensaje.length }} / 2000</p>
          <AvisoModeracion :aviso="avisoMod" :sugerencia="sugerenciaMod" />
        </div>

        <div class="compose-actions">
          <button class="btn-secondary" @click="mostrarForm = false" :disabled="enviando">Cancelar</button>
          <button class="btn-primary" @click="enviar" :disabled="enviando">
            <span v-if="enviando">Enviando…</span>
            <span v-else>
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
              </svg>
              Enviar
            </span>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Error ────────────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert-error">{{ error }}</div>

    <!-- Lista de avisos ───────────────────────────────────────────────────── -->
    <div v-if="cargando" class="loading-box">
      <div class="spinner"/><span>Cargando avisos…</span>
    </div>

    <template v-else>
      <!-- Filtros -->
      <div v-if="avisos.length" class="filtros-wrap">

        <!-- Selector empresa (solo en modo "Todas") -->
        <div v-if="esTodas && empresasEnBandeja.length > 1" class="filtro-empresa-wrap">
          <svg class="filtro-empresa-ico" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
          <select v-model="filtroEmpresa" class="filtro-empresa-select"
            @change="filtroDestino = 'todos'">
            <option value="">Todas las empresas</option>
            <option v-for="emp in empresasEnBandeja" :key="emp" :value="emp">{{ emp }}</option>
          </select>
        </div>

        <!-- Pills por destino -->
        <div v-if="filtros.length > 2" class="filtros-bar">
          <button
            v-for="f in filtros" :key="f.key"
            :class="['filtro-btn', filtroDestino === f.key && 'filtro-activo']"
            @click="filtroDestino = f.key">
            {{ f.label }}
            <span v-if="f.key !== 'todos'" class="filtro-count">
              {{ avisos.filter(a =>
                a.destino === f.key &&
                (!filtroEmpresa || a.empresa_nombre === filtroEmpresa || a.destino === 'todas')
              ).length }}
            </span>
          </button>
        </div>
      </div>

      <div v-if="!avisosFiltrados.length" class="empty-state">
        <p class="empty-icon">📭</p>
        <p v-if="filtroDestino !== 'todos'" class="empty-msg">Sin avisos con este filtro.</p>
        <p v-else class="empty-msg">No hay avisos aún.</p>
        <p v-if="puedeEnviar && filtroDestino === 'todos'" class="empty-sub">Usa el botón "Nuevo aviso" para comunicarte con tu flota.</p>
      </div>

      <div v-else class="avisos-list">
        <div v-for="a in avisosFiltrados" :key="a.id" class="aviso-card">
          <div class="aviso-header">
            <span class="aviso-destino">
              {{ iconoDestino(a.destino) }}
              <span v-if="a.destino === 'conductor'">{{ a.destinatario || 'Conductor' }}</span>
              <span v-else>{{ labelDestino(a.destino) }}</span>
            </span>
            <span class="aviso-fecha">{{ formatFecha(a.fecha) }}</span>
          </div>
          <p v-if="esTodas" class="aviso-empresa">🏢 {{ a.empresa_nombre || '—' }}</p>
          <p class="aviso-asunto">{{ a.asunto }}</p>
          <p class="aviso-mensaje">{{ a.mensaje }}</p>
          <p class="aviso-emisor">Enviado por <strong>{{ a.emisor }}</strong></p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 1.5rem; max-width: 860px; margin: 0 auto; }
.page-header { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap; }
.page-title  { font-size:1.5rem; font-weight:700; color:#1E1B4B; }
.page-subtitle { color:#6B7280; font-size:.875rem; margin-top:.25rem; }

.btn-primary  { display:flex; align-items:center; gap:.4rem; background:#6366F1; color:#fff; border:none; border-radius:10px; padding:.55rem 1.1rem; font-size:.875rem; font-weight:600; cursor:pointer; transition:background .15s; }
.btn-primary:hover:not(:disabled)  { background:#4F46E5; }
.btn-primary:disabled { opacity:.6; cursor:not-allowed; }
.btn-secondary { background:#F3F4F6; color:#374151; border:none; border-radius:10px; padding:.55rem 1.1rem; font-size:.875rem; font-weight:600; cursor:pointer; }
.btn-secondary:hover:not(:disabled) { background:#E5E7EB; }

/* Compose card */
.compose-card   { background:#fff; border:1px solid #E5E7EB; border-radius:14px; padding:1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.compose-title  { font-size:1rem; font-weight:700; color:#1E1B4B; margin-bottom:1rem; }
.compose-actions { display:flex; justify-content:flex-end; gap:.75rem; margin-top:1rem; }
.field-hint { font-size:.75rem; color:#6B7280; margin-top:.35rem; }
.aviso-empresa { font-size:.75rem; font-weight:600; color:#4F46E5; margin:.15rem 0 .35rem; }

.form-row   { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; }
.form-group { display:flex; flex-direction:column; gap:.35rem; margin-bottom:1rem; }
.label      { font-size:.8rem; font-weight:600; color:#374151; text-transform:uppercase; letter-spacing:.05em; }
.input      { border:1.5px solid #D1D5DB; border-radius:10px; padding:.6rem .85rem; font-size:.875rem; width:100%; box-sizing:border-box; font-family:inherit; transition:border-color .15s; }
.input:focus { outline:none; border-color:#6366F1; }
.input-error { border-color:#EF4444 !important; }
.select     { appearance:none; background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'%3E%3Cpath fill='none' stroke='%236B7280' stroke-width='2' d='M6 9l6 6 6-6'/%3E%3C/svg%3E") no-repeat right .75rem center; }
.field-error { font-size:.75rem; color:#EF4444; margin-top:.2rem; }
.char-count  { font-size:.75rem; color:#9CA3AF; text-align:right; margin-top:.2rem; }

/* Avisos list */
.loading-box { display:flex; align-items:center; gap:.75rem; padding:2rem; color:#6B7280; }
.spinner     { width:1.25rem; height:1.25rem; border:2px solid #E5E7EB; border-top-color:#6366F1; border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

.empty-state { text-align:center; padding:3rem 1rem; }
.empty-icon  { font-size:2.5rem; margin-bottom:.5rem; }
.empty-msg   { font-size:1rem; font-weight:600; color:#374151; }
.empty-sub   { font-size:.875rem; color:#9CA3AF; margin-top:.25rem; }

.avisos-list { display:flex; flex-direction:column; gap:.75rem; }
.aviso-card  { background:#fff; border:1px solid #E5E7EB; border-radius:12px; padding:1rem 1.25rem; box-shadow:0 1px 3px rgba(0,0,0,.05); }
.aviso-header  { display:flex; justify-content:space-between; align-items:center; margin-bottom:.5rem; }
.aviso-destino { display:flex; align-items:center; gap:.35rem; font-size:.8rem; font-weight:600; color:#6366F1; }
.aviso-fecha   { font-size:.75rem; color:#9CA3AF; }
.aviso-asunto  { font-size:.95rem; font-weight:700; color:#1E1B4B; margin-bottom:.35rem; }
.aviso-mensaje { font-size:.875rem; color:#374151; white-space:pre-wrap; line-height:1.55; margin-bottom:.5rem; }
.aviso-emisor  { font-size:.75rem; color:#9CA3AF; }

.alert-error { background:#FEF2F2; border:1px solid #FECACA; color:#B91C1C; border-radius:10px; padding:.75rem 1rem; margin-bottom:1rem; font-size:.875rem; }

/* Filtros */
.filtros-wrap { display:flex; flex-direction:column; gap:.6rem; margin-bottom:1rem; }
.filtros-bar  { display:flex; flex-wrap:wrap; gap:.5rem; }
.filtro-btn   { display:flex; align-items:center; gap:.35rem; border:1.5px solid #E5E7EB; background:#fff; border-radius:999px; padding:.35rem .9rem; font-size:.8rem; font-weight:600; color:#6B7280; cursor:pointer; transition:all .15s; }
.filtro-btn:hover { border-color:#6366F1; color:#6366F1; }
.filtro-activo { background:#EEF2FF; border-color:#6366F1; color:#4F46E5; }
.filtro-count  { background:#E5E7EB; color:#6B7280; border-radius:999px; padding:.05rem .45rem; font-size:.7rem; font-weight:700; }
.filtro-activo .filtro-count { background:#C7D2FE; color:#4F46E5; }

.filtro-empresa-wrap   { display:flex; align-items:center; gap:.5rem; }
.filtro-empresa-ico    { width:1rem; height:1rem; color:#6B7280; flex-shrink:0; }
.filtro-empresa-select { border:1.5px solid #E5E7EB; border-radius:10px; padding:.35rem .75rem; font-size:.825rem; font-weight:600; color:#374151; background:#fff; cursor:pointer; transition:border-color .15s; appearance:none; padding-right:1.75rem; background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24'%3E%3Cpath fill='none' stroke='%236B7280' stroke-width='2' d='M6 9l6 6 6-6'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right .5rem center; }
.filtro-empresa-select:focus { outline:none; border-color:#6366F1; }

/* Transición slide */
.slide-down-enter-active, .slide-down-leave-active { transition:all .25s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity:0; transform:translateY(-10px); }
</style>
