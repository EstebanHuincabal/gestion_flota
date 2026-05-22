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

onMounted(async () => {
  const res = await apiFetch('/api/configuracion/planes/')
  if (res.ok) planes.value = await res.json()
  cargando.value = false
})

const seleccionar = async (plan) => {
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

const permisosAgrupados = computed(() => {
  const grupos = {}
  for (const p of todosPermisos.value) {
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

const categoriaCompleta     = (cat) => cat.every(p => permisosPlan.value.includes(p.codigo))
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

const totalActivos = computed(() => permisosPlan.value.length)

const colorPlan = (nombre) => {
  if (!nombre) return '#6B7280'
  const n = nombre.toLowerCase()
  if (n === 'enterprise') return '#7C3AED'
  if (n === 'pro')        return '#0EA5E9'
  return '#059669'
}

const activosCat = (cat) => cat.filter(p => permisosPlan.value.includes(p.codigo)).length
</script>

<template>
  <div class="page">

    <div class="page-header">
      <h1 class="page-title">Permisos por Plan</h1>
      <p class="page-subtitle">Define qué acciones puede realizar cada plan de suscripción</p>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando planes...</span>
    </div>

    <div v-else class="split">

      <!-- ── Panel izquierdo: planes ── -->
      <aside class="panel-izq">
        <p class="lista-label">Planes disponibles</p>
        <div class="lista-planes">
          <button
            v-for="plan in planes"
            :key="plan.id"
            :class="['plan-item', { selected: planSel?.id === plan.id }]"
            @click="seleccionar(plan)"
          >
            <div class="plan-dot" :style="{ background: colorPlan(plan.nombre) }"/>
            <div class="plan-info">
              <p class="plan-nombre">{{ plan.nombre_display || plan.nombre }}</p>
              <p class="plan-sub">{{ plan.activo ? 'Activo' : 'Inactivo' }}</p>
            </div>
            <span class="plan-count" :style="{ color: colorPlan(plan.nombre) }">
              {{ plan._permisos_count !== undefined ? plan._permisos_count : '—' }}
            </span>
          </button>
          <p v-if="!planes.length" class="empty-list">No hay planes creados.</p>
        </div>
      </aside>

      <!-- ── Panel derecho: editor ── -->
      <section class="panel-der">

        <!-- Estado vacío -->
        <div v-if="!planSel" class="empty-editor">
          <div class="empty-icon-wrap">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          </div>
          <p class="empty-title">Selecciona un plan</p>
          <p class="empty-desc">Elige un plan de la izquierda para configurar sus permisos</p>
        </div>

        <template v-else>

          <!-- Header del plan -->
          <div class="editor-header">
            <div class="plan-avatar" :style="{ background: colorPlan(planSel.nombre) }">
              {{ (planSel.nombre_display || planSel.nombre || 'P')[0].toUpperCase() }}
            </div>
            <div class="editor-info">
              <p class="editor-nombre">Plan {{ planSel.nombre_display || planSel.nombre }}</p>
              <p class="editor-detalle">{{ planSel.descripcion || 'Sin descripción' }}</p>
            </div>
            <div class="editor-stat-pill">
              <span class="stat-activos">{{ totalActivos }}</span>
              <span class="stat-sep">/{{ todosPermisos.length }}</span>
              <span class="stat-text">permisos</span>
            </div>
          </div>

          <!-- Barra de acciones rápidas -->
          <div class="barra-acciones">
            <div class="acciones-btns">
              <button class="btn-sel-todos" @click="seleccionarTodos">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Seleccionar todos
              </button>
              <button class="btn-quitar-todos" @click="deseleccionarTodos">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Quitar todos
              </button>
            </div>
            <p class="barra-aviso">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              Afecta a todas las empresas con este plan
            </p>
          </div>

          <!-- Lista de categorías -->
          <div v-if="cargandoPerm" class="loading-perm">
            <div class="spinner"/> <span>Cargando permisos...</span>
          </div>
          <div v-else class="categorias-body">
            <div
              v-for="(permisosCat, cat) in permisosAgrupados"
              :key="cat"
              class="cat-section"
            >
              <!-- Cabecera de categoría -->
              <div class="cat-head">
                <label class="cat-toggle">
                  <input
                    type="checkbox"
                    :checked="categoriaCompleta(permisosCat)"
                    :indeterminate="categoriaIndeterminate(permisosCat)"
                    @change="toggleCategoria(permisosCat)"
                    class="sr-only"
                  />
                  <span :class="['cat-box', {
                    'cat-box--on':      categoriaCompleta(permisosCat),
                    'cat-box--partial': categoriaIndeterminate(permisosCat),
                  }]">
                    <svg v-if="categoriaCompleta(permisosCat)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                    </svg>
                    <svg v-else-if="categoriaIndeterminate(permisosCat)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M20 12H4"/>
                    </svg>
                  </span>
                </label>
                <span class="cat-nombre">{{ cat }}</span>
                <span :class="['cat-badge', {
                  'cat-badge--full':    categoriaCompleta(permisosCat),
                  'cat-badge--partial': categoriaIndeterminate(permisosCat),
                }]">
                  {{ activosCat(permisosCat) }} / {{ permisosCat.length }}
                </span>
              </div>

              <!-- Checklist de permisos -->
              <div class="perms-lista">
                <label v-for="p in permisosCat" :key="p.codigo" class="perm-row">
                  <input type="checkbox" :value="p.codigo" v-model="permisosPlan" class="sr-only" />
                  <span :class="['perm-box', { 'perm-box--on': permisosPlan.includes(p.codigo) }]">
                    <svg v-if="permisosPlan.includes(p.codigo)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                    </svg>
                  </span>
                  <span :class="['perm-nombre', { 'perm-nombre--on': permisosPlan.includes(p.codigo) }]">
                    {{ p.nombre }}
                  </span>
                </label>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="editor-footer">
            <button class="btn-cancelar" @click="cancelar">Cancelar</button>
            <button class="btn-guardar" @click="guardar" :disabled="guardando || cargandoPerm">
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

.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}

.page {
  padding: 2rem 2.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  height: calc(100vh - 64px);
  display: flex; flex-direction: column; overflow: hidden;
}

.page-header { margin-bottom: 1.25rem; flex-shrink: 0; }
.page-title   { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* ── Spinner ── */
.loading, .loading-perm {
  display: flex; align-items: center; gap: 0.75rem;
  color: #6B7280; font-size: 0.875rem; padding: 2rem 0;
}
.loading-perm { flex: 1; justify-content: center; }
.spinner {
  width: 22px; height: 22px; border: 2.5px solid #E5E7EB;
  border-top-color: #7C3AED; border-radius: 50%;
  animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Layout split ── */
.split {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1.25rem;
  flex: 1; min-height: 0;
}

/* ── Panel izquierdo ── */
.panel-izq {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  display: flex; flex-direction: column;
  overflow: hidden;
}

.lista-label {
  font-size: 0.6875rem; font-weight: 600; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.07em;
  padding: 0.875rem 1rem 0.5rem; flex-shrink: 0;
}

.lista-planes { flex: 1; overflow-y: auto; padding: 0 0.625rem 0.625rem; }

.plan-item {
  width: 100%; display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 0.625rem; border-radius: 10px;
  border: none; background: transparent;
  cursor: pointer; text-align: left;
  transition: background 0.12s;
}
.plan-item:hover { background: #F5F3FF; }
.plan-item.selected { background: #EEF2FF; }

.plan-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.plan-info { flex: 1; min-width: 0; }
.plan-nombre { font-size: 0.875rem; font-weight: 600; color: #111827; margin: 0 0 0.1rem; }
.plan-sub    { font-size: 0.6875rem; color: #9CA3AF; margin: 0; }
.plan-count  { font-size: 0.875rem; font-weight: 700; flex-shrink: 0; }

.empty-list { font-size: 0.8125rem; color: #9CA3AF; text-align: center; padding: 1.5rem 0; margin: 0; }

/* ── Panel derecho ── */
.panel-der {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  display: flex; flex-direction: column;
  overflow: hidden; min-height: 0;
}

/* Estado vacío */
.empty-editor {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.75rem;
}
.empty-icon-wrap {
  width: 64px; height: 64px; border-radius: 16px;
  background: #F5F3FF;
  display: flex; align-items: center; justify-content: center;
}
.empty-icon-wrap svg { width: 32px; height: 32px; color: #7C3AED; }
.empty-title { font-size: 1rem; font-weight: 600; color: #374151; margin: 0; }
.empty-desc  { font-size: 0.875rem; color: #9CA3AF; margin: 0; }

/* Header del plan */
.editor-header {
  display: flex; align-items: center; gap: 1rem;
  padding: 1.125rem 1.5rem;
  border-bottom: 1px solid #F3F4F6;
  flex-shrink: 0;
}
.plan-avatar {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 1.25rem; font-weight: 700;
}
.editor-info { flex: 1; min-width: 0; }
.editor-nombre  { font-size: 1rem; font-weight: 700; color: #111827; margin: 0 0 0.1rem; }
.editor-detalle { font-size: 0.8125rem; color: #6B7280; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.editor-stat-pill {
  display: flex; align-items: baseline; gap: 0.2rem;
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 100px; padding: 0.3rem 0.875rem;
  flex-shrink: 0;
}
.stat-activos { font-size: 1rem; font-weight: 700; color: #4F46E5; }
.stat-sep     { font-size: 0.875rem; font-weight: 500; color: #9CA3AF; }
.stat-text    { font-size: 0.75rem; color: #9CA3AF; margin-left: 0.25rem; }

/* Barra de acciones */
.barra-acciones {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: #FAFAFA;
  border-bottom: 1px solid #F3F4F6;
  flex-shrink: 0; gap: 1rem;
}
.acciones-btns { display: flex; gap: 0.5rem; }

.btn-sel-todos, .btn-quitar-todos {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.4rem 0.875rem; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 0.12s;
}
.btn-sel-todos svg, .btn-quitar-todos svg { width: 15px; height: 15px; }

.btn-sel-todos {
  border: 1px solid #C4B5FD; background: #EEF2FF; color: #4338CA;
}
.btn-sel-todos:hover { background: #DDD6FE; }

.btn-quitar-todos {
  border: 1px solid #E5E7EB; background: #fff; color: #6B7280;
}
.btn-quitar-todos:hover { background: #F3F4F6; }

.barra-aviso {
  display: flex; align-items: center; gap: 0.35rem;
  font-size: 0.75rem; color: #9CA3AF; margin: 0;
}
.barra-aviso svg { width: 14px; height: 14px; flex-shrink: 0; }

/* ── Categorías ── */
.categorias-body {
  flex: 1; overflow-y: auto; padding: 0.5rem 0;
}

.cat-section {
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #F3F4F6;
}
.cat-section:last-child { border-bottom: none; }

.cat-head {
  display: flex; align-items: center; gap: 0.75rem;
  margin-bottom: 0.625rem;
}

/* Checkbox visual personalizado */
.cat-toggle { cursor: pointer; flex-shrink: 0; display: flex; }
.cat-box {
  width: 20px; height: 20px; border-radius: 6px;
  border: 2px solid #D1D5DB; background: #fff;
  display: flex; align-items: center; justify-content: center;
  transition: border-color 0.12s, background 0.12s;
}
.cat-box svg { width: 12px; height: 12px; }
.cat-box--on      { border-color: #7C3AED; background: #7C3AED; color: #fff; }
.cat-box--partial { border-color: #7C3AED; background: #EDE9FE; color: #7C3AED; }
.cat-toggle:hover .cat-box { border-color: #7C3AED; }

.cat-nombre {
  font-size: 0.875rem; font-weight: 700; color: #111827;
  flex: 1; text-transform: capitalize;
}

.cat-badge {
  padding: 0.15rem 0.5rem; border-radius: 100px;
  font-size: 0.6875rem; font-weight: 600;
  background: #F3F4F6; color: #9CA3AF;
  flex-shrink: 0;
}
.cat-badge--full    { background: #EDE9FE; color: #7C3AED; }
.cat-badge--partial { background: #FEF3C7; color: #D97706; }

/* ── Checklist de permisos ── */
.perms-lista {
  display: flex; flex-direction: column;
  padding: 0.125rem 0 0 2.75rem;
}

.perm-row {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.425rem 0.625rem 0.425rem 0.375rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}
.perm-row:hover { background: #F5F3FF; }

.perm-box {
  width: 18px; height: 18px; border-radius: 5px;
  border: 2px solid #D1D5DB; background: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.1s, background 0.1s;
}
.perm-box svg { width: 11px; height: 11px; }
.perm-box--on { border-color: #7C3AED; background: #7C3AED; color: #fff; }
.perm-row:hover .perm-box:not(.perm-box--on) { border-color: #A78BFA; }

.perm-nombre {
  font-size: 0.875rem; color: #4B5563; line-height: 1.4;
}
.perm-nombre--on { color: #4C1D95; font-weight: 600; }

/* ── Footer ── */
.editor-footer {
  padding: 0.875rem 1.5rem;
  border-top: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: flex-end;
  gap: 0.625rem; flex-shrink: 0;
}

.btn-cancelar {
  padding: 0.5rem 1.125rem;
  border: 1px solid #E5E7EB; border-radius: 8px;
  background: #fff; color: #374151;
  font-size: 0.875rem; font-weight: 500;
  cursor: pointer; font-family: inherit;
  transition: background 0.12s;
}
.btn-cancelar:hover { background: #F9FAFB; }

.btn-guardar {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1.25rem;
  border: none; border-radius: 8px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; font-family: inherit;
  transition: opacity 0.12s;
}
.btn-guardar:hover:not(:disabled) { opacity: 0.9; }
.btn-guardar:disabled { opacity: 0.55; cursor: not-allowed; }

.spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite; flex-shrink: 0;
}
</style>
