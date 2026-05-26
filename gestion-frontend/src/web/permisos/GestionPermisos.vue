<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'

const toast = useToast()

const planes         = ref([])
const todosPermisos  = ref([])
const planSel        = ref(null)
const permisosPlan   = ref([])
const cargando       = ref(true)
const cargandoPerm   = ref(false)
const guardando      = ref(false)
const busqueda       = ref('')

// Etiquetas legibles por categoría
const LABELS = {
  Dashboard:    'Dashboard',
  conductores:  'Conductores',
  vehiculos:    'Vehículos',
  flotas:       'Flotas',
  mantenciones: 'Mantenciones',
  predictivo:   'Predictivo',
  rutas:        'Rutas',
  solicitudes:  'Solicitudes',
  finanzas:     'Finanzas',
  documentos:   'Documentos',
  usuarios:     'Usuarios',
}
const labelCat = (cat) => LABELS[cat] ?? cat

// ── Carga inicial ─────────────────────────────────────────────────────────────
onMounted(async () => {
  const res = await apiFetch('/api/configuracion/planes/')
  if (res.ok) planes.value = await res.json()
  cargando.value = false
})

const seleccionar = async (plan) => {
  busqueda.value      = ''
  planSel.value       = plan
  permisosPlan.value  = []
  todosPermisos.value = []
  cargandoPerm.value  = true

  const res = await apiFetch(`/api/configuracion/planes/${plan.id}/permisos/`)
  if (res.ok) {
    const data = await res.json()
    permisosPlan.value  = [...(data.permisos_plan  || [])]
    todosPermisos.value = data.todos_permisos || []
  }
  cargandoPerm.value = false
}

// ── Agrupados con filtro de búsqueda ──────────────────────────────────────────
const permisosAgrupados = computed(() => {
  const q = busqueda.value.toLowerCase().trim()
  const grupos = {}
  for (const p of todosPermisos.value) {
    const lbl    = labelCat(p.categoria).toLowerCase()
    const nombre = p.nombre.toLowerCase()
    if (q && !lbl.includes(q) && !nombre.includes(q) && !p.codigo.includes(q)) continue
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

// ── Helpers de estado ─────────────────────────────────────────────────────────
const categoriaCompleta      = (cat) => cat.every(p => permisosPlan.value.includes(p.codigo))
const categoriaIndeterminate = (cat) => cat.some(p => permisosPlan.value.includes(p.codigo)) && !categoriaCompleta(cat)

const toggleCategoria = (cat) => {
  const codigos = cat.map(p => p.codigo)
  if (categoriaCompleta(cat)) {
    permisosPlan.value = permisosPlan.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosPlan.value.includes(c))
    permisosPlan.value = [...permisosPlan.value, ...nuevos]
  }
}

const seleccionarTodos   = () => { permisosPlan.value = todosPermisos.value.map(p => p.codigo) }
const deseleccionarTodos = () => { permisosPlan.value = [] }
const totalActivos        = computed(() => permisosPlan.value.length)

// ── Guardar ───────────────────────────────────────────────────────────────────
const guardar = async () => {
  if (!planSel.value) return
  guardando.value = true
  try {
    const res = await apiFetch(`/api/configuracion/planes/${planSel.value.id}/permisos/`, {
      method: 'PUT',
      body:   { permisos: permisosPlan.value },
    })
    if (res.ok) {
      const idx = planes.value.findIndex(p => p.id === planSel.value.id)
      if (idx !== -1) planes.value[idx]._permisos_count = permisosPlan.value.length
      toast.success(`Permisos de "${planSel.value.nombre_display || planSel.value.nombre}" guardados.`)
    } else {
      toast.error('Error al guardar los permisos.')
    }
  } catch {
    toast.error('Error de conexión con el servidor.')
  } finally {
    guardando.value = false
  }
}

const cancelar = () => { if (planSel.value) seleccionar(planSel.value) }

const colorPlan = (nombre) => {
  if (!nombre) return '#6B7280'
  const n = nombre.toLowerCase()
  if (n === 'enterprise') return '#7C3AED'
  if (n === 'pro')        return '#0EA5E9'
  return '#059669'
}
</script>

<template>
  <div class="page">

    <!-- ── Encabezado ─────────────────────────────────────────────────────── -->
    <div class="page-header">
      <h1 class="page-title">Permisos por Plan</h1>
      <p class="page-subtitle">Define qué acciones puede realizar cada plan de suscripción</p>
    </div>

    <div v-if="cargando" class="loading-global">
      <div class="spinner"/> <span>Cargando planes...</span>
    </div>

    <div v-else class="split">

      <!-- ── Panel izquierdo: planes ─────────────────────────────────────── -->
      <aside class="panel-izq">
        <p class="lista-label">Planes</p>
        <div class="lista-planes">
          <button
            v-for="plan in planes"
            :key="plan.id"
            :class="['plan-item', { selected: planSel?.id === plan.id }]"
            @click="seleccionar(plan)"
          >
            <span class="plan-dot" :style="{ background: colorPlan(plan.nombre) }"/>
            <div class="plan-info">
              <p class="plan-nombre">{{ plan.nombre_display || plan.nombre }}</p>
              <p class="plan-sub">{{ plan.activo ? 'Activo' : 'Inactivo' }}</p>
            </div>
            <span v-if="plan._permisos_count !== undefined" class="plan-count"
                  :style="{ color: colorPlan(plan.nombre) }">
              {{ plan._permisos_count }}
            </span>
          </button>
          <p v-if="!planes.length" class="empty-list">No hay planes.</p>
        </div>
      </aside>

      <!-- ── Panel derecho: editor ───────────────────────────────────────── -->
      <section class="panel-der">

        <!-- Estado vacío -->
        <div v-if="!planSel" class="empty-editor">
          <div class="empty-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          </div>
          <p class="empty-title">Selecciona un plan</p>
          <p class="empty-desc">Elige un plan de la lista para ver y editar sus permisos</p>
        </div>

        <template v-else>

          <!-- Toolbar -->
          <div class="toolbar">
            <div class="toolbar-left">
              <span class="plan-dot-lg" :style="{ background: colorPlan(planSel.nombre) }"/>
              <span class="toolbar-plan-nombre">{{ planSel.nombre_display || planSel.nombre }}</span>
              <span class="toolbar-count">{{ totalActivos }} / {{ todosPermisos.length }} permisos</span>
            </div>
            <div class="toolbar-right">
              <!-- Buscador -->
              <div class="search-wrap">
                <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M21 21l-4.35-4.35M17 11A6 6 0 111 11a6 6 0 0116 0z"/>
                </svg>
                <input v-model="busqueda" type="text" placeholder="Buscar..." class="search-input"/>
                <button v-if="busqueda" class="search-clear" @click="busqueda = ''">×</button>
              </div>
              <button class="perm-btn-all" @click="seleccionarTodos">Todos</button>
              <button class="perm-btn-all perm-btn-none" @click="deseleccionarTodos">Ninguno</button>
            </div>
          </div>

          <!-- Cargando -->
          <div v-if="cargandoPerm" class="loading-perm">
            <div class="spinner"/> <span>Cargando permisos...</span>
          </div>

          <!-- Sin resultados -->
          <div v-else-if="!Object.keys(permisosAgrupados).length" class="no-results">
            Sin resultados para "<strong>{{ busqueda }}</strong>"
          </div>

          <!-- Grid de categorías — mismo patrón que Planes.vue -->
          <div v-else class="perm-grid">
            <div
              v-for="(permisosCat, cat) in permisosAgrupados"
              :key="cat"
              class="perm-cat-card"
            >
              <!-- Cabecera -->
              <div class="perm-cat-header">
                <label class="perm-cat-label">
                  <input
                    type="checkbox"
                    :checked="categoriaCompleta(permisosCat)"
                    :indeterminate="categoriaIndeterminate(permisosCat)"
                    @change="toggleCategoria(permisosCat)"
                    class="perm-check"
                  />
                  <span class="perm-cat-nombre">{{ labelCat(cat) }}</span>
                </label>
                <span :class="['perm-cat-count', { completo: categoriaCompleta(permisosCat) }]">
                  {{ permisosCat.filter(p => permisosPlan.includes(p.codigo)).length }}/{{ permisosCat.length }}
                </span>
              </div>

              <!-- Lista de permisos -->
              <div class="perm-lista">
                <label v-for="p in permisosCat" :key="p.codigo" class="perm-item">
                  <input type="checkbox" :value="p.codigo" v-model="permisosPlan" class="perm-check"/>
                  <span class="perm-nombre">{{ p.nombre }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="editor-footer">
            <button class="btn-cancel" @click="cancelar">Cancelar</button>
            <button class="btn-save" @click="guardar" :disabled="guardando || cargandoPerm">
              <span v-if="guardando" class="spinner-sm"/>
              {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
            </button>
          </div>

        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

/* ── Raíz ────────────────────────────────────────────────────────────────── */
.page {
  padding: 2rem 2.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  height: calc(100vh - 64px);
  display: flex; flex-direction: column; overflow: hidden;
}
.page-header   { margin-bottom: 1.25rem; flex-shrink: 0; }
.page-title    { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* ── Spinners ────────────────────────────────────────────────────────────── */
.loading-global, .loading-perm {
  display: flex; align-items: center; gap: 0.75rem;
  color: #6B7280; font-size: 0.875rem;
}
.loading-global { padding: 3rem 0; }
.loading-perm   { flex: 1; justify-content: center; }
.spinner {
  width: 22px; height: 22px;
  border: 2.5px solid #E5E7EB; border-top-color: #7C3AED;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
.spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Split ───────────────────────────────────────────────────────────────── */
.split {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 1.25rem;
  flex: 1; min-height: 0;
}

/* ── Panel izquierdo ─────────────────────────────────────────────────────── */
.panel-izq {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  display: flex; flex-direction: column; overflow: hidden;
}
.lista-label {
  font-size: 0.6875rem; font-weight: 700; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.07em;
  padding: 0.875rem 0.875rem 0.5rem; flex-shrink: 0;
}
.lista-planes { flex: 1; overflow-y: auto; padding: 0 0.5rem 0.5rem; }
.plan-item {
  width: 100%; display: flex; align-items: center; gap: 0.625rem;
  padding: 0.625rem 0.5rem; border-radius: 9px;
  border: none; background: transparent; cursor: pointer; text-align: left;
  transition: background 0.12s; margin-bottom: 2px;
}
.plan-item:hover    { background: #F5F3FF; }
.plan-item.selected { background: #EEF2FF; }
.plan-dot  { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.plan-info { flex: 1; min-width: 0; }
.plan-nombre {
  font-size: 0.875rem; font-weight: 600; color: #111827; margin: 0 0 0.1rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.plan-sub   { font-size: 0.6875rem; color: #9CA3AF; margin: 0; }
.plan-count { font-size: 0.8125rem; font-weight: 700; flex-shrink: 0; }
.empty-list { font-size: 0.8125rem; color: #9CA3AF; text-align: center; padding: 1.5rem 0; margin: 0; }

/* ── Panel derecho ───────────────────────────────────────────────────────── */
.panel-der {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  display: flex; flex-direction: column; overflow: hidden; min-height: 0;
}

/* Estado vacío */
.empty-editor {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.625rem;
}
.empty-icon {
  width: 64px; height: 64px; border-radius: 16px; background: #F5F3FF;
  display: flex; align-items: center; justify-content: center;
}
.empty-icon svg { width: 32px; height: 32px; color: #7C3AED; }
.empty-title { font-size: 1rem; font-weight: 600; color: #374151; margin: 0; }
.empty-desc  { font-size: 0.875rem; color: #9CA3AF; margin: 0; }

/* Toolbar */
.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.75rem; padding: 0.75rem 1rem;
  border-bottom: 1px solid #F3F4F6; flex-shrink: 0; flex-wrap: wrap;
}
.toolbar-left  { display: flex; align-items: center; gap: 0.5rem; }
.toolbar-right { display: flex; align-items: center; gap: 0.5rem; }
.plan-dot-lg { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.toolbar-plan-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; }
.toolbar-count {
  font-size: 0.75rem; color: #7C3AED; font-weight: 600;
  background: #EDE9FE; padding: 0.2rem 0.55rem; border-radius: 100px;
}

.search-wrap {
  display: flex; align-items: center;
  background: #fff; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 0 0.5rem; gap: 0.25rem;
}
.search-wrap:focus-within { border-color: #A78BFA; box-shadow: 0 0 0 3px #EDE9FE; }
.search-icon  { width: 14px; height: 14px; color: #9CA3AF; flex-shrink: 0; }
.search-input {
  border: none; outline: none; background: transparent;
  font-size: 0.8125rem; color: #111827; padding: 0.4rem 0; width: 130px;
  font-family: inherit;
}
.search-clear {
  border: none; background: transparent; cursor: pointer;
  color: #9CA3AF; font-size: 1.125rem; padding: 0; line-height: 1;
}

.perm-btn-all {
  font-size: 0.6875rem; font-weight: 600; padding: 0.2rem 0.625rem;
  border-radius: 6px; border: 1px solid #C4B5FD;
  background: #EEF2FF; color: #4338CA;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.perm-btn-all:hover { background: #DDD6FE; }
.perm-btn-none { background: #F9FAFB; border-color: #E5E7EB; color: #6B7280; }
.perm-btn-none:hover { background: #F3F4F6; }

/* Sin resultados */
.no-results {
  flex: 1; display: flex; align-items: center; justify-content: center;
  font-size: 0.9375rem; color: #9CA3AF; padding: 2rem;
}

/* ════════════════════════════════════════
   GRID DE PERMISOS — igual que Planes.vue
   ════════════════════════════════════════ */
.perm-grid {
  flex: 1; overflow-y: auto;
  padding: 1rem 1.125rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 0.75rem;
  align-content: start;
}

.perm-cat-card {
  border: 1px solid #E5E7EB; border-radius: 10px;
  /* sin overflow:hidden para que el texto nunca quede cortado */
}
.perm-cat-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 0.875rem; background: #F9FAFB;
  border-bottom: 1px solid #F3F4F6;
  border-radius: 10px 10px 0 0;
}
.perm-cat-label {
  display: flex; align-items: center; gap: 0.4rem;
  flex: 1; cursor: pointer; min-width: 0;
}
.perm-check { cursor: pointer; accent-color: #7C3AED; flex-shrink: 0; }
.perm-cat-nombre {
  font-size: 0.875rem; font-weight: 700; color: #111827;
}
.perm-cat-count {
  font-size: 0.6875rem; font-weight: 600; padding: 0.15rem 0.45rem;
  border-radius: 100px; background: #F3F4F6; color: #6B7280; flex-shrink: 0;
}
.perm-cat-count.completo { background: #EEF2FF; color: #4338CA; }

.perm-lista {
  padding: 0.5rem 0.875rem 0.75rem;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.perm-item {
  display: flex; align-items: flex-start; gap: 0.4rem;
  font-size: 0.8125rem; color: #374151; cursor: pointer;
  padding: 0.25rem 0.375rem; border-radius: 5px;
  transition: background 0.1s;
}
.perm-item:hover { background: #F5F3FF; }
.perm-nombre { line-height: 1.45; white-space: normal; word-break: break-word; }

/* ── Footer ─────────────────────────────────────────────────────────────── */
.editor-footer {
  padding: 0.875rem 1rem; border-top: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: flex-end;
  gap: 0.5rem; flex-shrink: 0;
}
.btn-cancel {
  padding: 0.55rem 1.25rem; border: 1.5px solid #E5E7EB;
  background: #fff; color: #374151; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer;
  transition: background 0.15s; font-family: inherit;
}
.btn-cancel:hover { background: #F9FAFB; }
.btn-save {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.55rem 1.5rem; border: none; border-radius: 8px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: opacity 0.15s;
}
.btn-save:disabled { opacity: 0.65; cursor: not-allowed; }
.btn-save:not(:disabled):hover { opacity: 0.9; }
</style>
