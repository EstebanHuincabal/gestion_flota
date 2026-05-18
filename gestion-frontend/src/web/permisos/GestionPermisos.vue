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

// ── Carga inicial: solo la lista de planes ─────────────────────────────────
onMounted(async () => {
  const res = await apiFetch('/api/configuracion/planes/')
  if (res.ok) planes.value = await res.json()
  cargando.value = false
})

// ── Seleccionar plan ───────────────────────────────────────────────────────
const seleccionar = async (plan) => {
  planSel.value    = plan
  permisosPlan.value = []
  todosPermisos.value = []
  cargandoPerm.value = true

  const res = await apiFetch(`/api/configuracion/planes/${plan.id}/permisos/`)
  if (res.ok) {
    const data = await res.json()
    permisosPlan.value  = [...(data.permisos_plan  || [])]
    todosPermisos.value = data.todos_permisos || []
  }
  cargandoPerm.value = false
}

// ── Permisos agrupados por categoría ──────────────────────────────────────
const permisosAgrupados = computed(() => {
  const grupos = {}
  for (const p of todosPermisos.value) {
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

// ── Checkboxes por categoría ───────────────────────────────────────────────
const categoriaCompleta = (permisosCat) =>
  permisosCat.every(p => permisosPlan.value.includes(p.codigo))

const categoriaIndeterminate = (permisosCat) => {
  const alguno = permisosCat.some(p => permisosPlan.value.includes(p.codigo))
  return alguno && !categoriaCompleta(permisosCat)
}

const toggleCategoria = (permisosCat) => {
  const codigos = permisosCat.map(p => p.codigo)
  if (categoriaCompleta(permisosCat)) {
    permisosPlan.value = permisosPlan.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosPlan.value.includes(c))
    permisosPlan.value = [...permisosPlan.value, ...nuevos]
  }
}

const seleccionarTodos   = () => { permisosPlan.value = todosPermisos.value.map(p => p.codigo) }
const deseleccionarTodos = () => { permisosPlan.value = [] }

// ── Guardar ────────────────────────────────────────────────────────────────
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

const cancelar = () => {
  if (planSel.value) seleccionar(planSel.value)
}

const totalActivos = computed(() => permisosPlan.value.length)

// ── Color por plan ─────────────────────────────────────────────────────────
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

    <!-- Cabecera -->
    <div class="page-header">
      <h1 class="page-title">Permisos por Plan</h1>
      <p class="page-subtitle">Define qué acciones puede realizar cada plan de suscripción</p>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando planes...</span>
    </div>

    <div v-else class="split">

      <!-- ── Panel izquierdo: lista de planes ── -->
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
            <span class="plan-badge" :style="{ background: colorPlan(plan.nombre) + '20', color: colorPlan(plan.nombre) }">
              {{ plan._permisos_count !== undefined ? plan._permisos_count : '—' }} perms
            </span>
          </button>

          <p v-if="!planes.length" class="empty-list">No hay planes creados.</p>
        </div>
      </aside>

      <!-- ── Panel derecho: editor ── -->
      <section class="panel-der">

        <!-- Estado vacío -->
        <div v-if="!planSel" class="empty-editor">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <p>Selecciona un plan para configurar sus permisos</p>
        </div>

        <template v-else>

          <!-- 1. Header del plan -->
          <div class="editor-header">
            <div class="plan-avatar" :style="{ background: colorPlan(planSel.nombre) }">
              {{ (planSel.nombre_display || planSel.nombre || 'P')[0].toUpperCase() }}
            </div>
            <div class="editor-info">
              <p class="editor-nombre">Plan {{ planSel.nombre_display || planSel.nombre }}</p>
              <p class="editor-detalle">{{ planSel.descripcion || 'Sin descripción' }}</p>
            </div>
            <span class="editor-stat">{{ totalActivos }} / {{ todosPermisos.length }} permisos</span>
          </div>

          <!-- 2. Barra rápida -->
          <div class="barra-rapida">
            <div class="barra-rapida-acciones">
              <button class="btn-accion" @click="seleccionarTodos">Seleccionar todos</button>
              <button class="btn-accion btn-gris" @click="deseleccionarTodos">Quitar todos</button>
            </div>
            <p class="barra-hint">Los cambios se aplican a todas las empresas con este plan</p>
          </div>

          <!-- 3. Grid de permisos -->
          <div v-if="cargandoPerm" class="loading-perm">
            <div class="spinner"/> <span>Cargando permisos...</span>
          </div>
          <div v-else class="permisos-grid">
            <div
              v-for="(permisosCat, cat) in permisosAgrupados"
              :key="cat"
              class="cat-card"
            >
              <!-- Header de categoría -->
              <div class="cat-header">
                <label class="cat-label">
                  <input
                    type="checkbox"
                    :checked="categoriaCompleta(permisosCat)"
                    :indeterminate="categoriaIndeterminate(permisosCat)"
                    @change="toggleCategoria(permisosCat)"
                    class="cat-check"
                  />
                  <span class="cat-nombre">{{ cat }}</span>
                </label>
                <span :class="['cat-count', { completo: categoriaCompleta(permisosCat) }]">
                  {{ permisosCat.filter(p => permisosPlan.includes(p.codigo)).length }}/{{ permisosCat.length }}
                </span>
              </div>

              <!-- Lista de permisos individuales -->
              <div class="perm-lista">
                <label v-for="p in permisosCat" :key="p.codigo" class="perm-item">
                  <input
                    type="checkbox"
                    :value="p.codigo"
                    v-model="permisosPlan"
                    class="perm-check"
                  />
                  <span class="perm-nombre">{{ p.nombre }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- 4. Footer -->
          <div class="editor-footer">
            <span/>
            <div class="footer-acciones">
              <button class="btn-cancelar" @click="cancelar">Cancelar</button>
              <button class="btn-guardar" @click="guardar" :disabled="guardando || cargandoPerm">
                <span v-if="guardando" class="spinner-sm"/>
                {{ guardando ? 'Guardando...' : 'Guardar permisos' }}
              </button>
            </div>
          </div>

        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.page {
  padding: 2rem 2.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  height: calc(100vh - 64px); display: flex; flex-direction: column; overflow: hidden;
}

.page-header { margin-bottom: 1.25rem; flex-shrink: 0; }
.page-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

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

/* ── Layout ── */
.split {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 1rem;
  flex: 1; min-height: 0;
}

/* ── Panel izquierdo ── */
.panel-izq {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
  display: flex; flex-direction: column; overflow: hidden;
}

.lista-label {
  font-size: 0.6875rem; font-weight: 600; color: #9CA3AF;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 0.75rem 0.875rem 0.375rem; flex-shrink: 0;
}

.lista-planes { flex: 1; overflow-y: auto; padding: 0.25rem 0.5rem 0.5rem; }

.plan-item {
  width: 100%; display: flex; align-items: center; gap: 0.625rem;
  padding: 0.6rem 0.5rem; border-radius: 10px; border: none; background: transparent;
  cursor: pointer; text-align: left; transition: background 0.12s;
}
.plan-item:hover { background: #F5F3FF; }
.plan-item.selected { background: #EEF2FF; }

.plan-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.plan-info { flex: 1; min-width: 0; }
.plan-nombre { font-size: 0.875rem; font-weight: 600; color: #111827; margin: 0; }
.plan-sub    { font-size: 0.6875rem; color: #9CA3AF; margin: 0; }
.plan-badge  {
  padding: 0.15rem 0.5rem; border-radius: 100px;
  font-size: 0.6875rem; font-weight: 700; flex-shrink: 0; white-space: nowrap;
}

.empty-list { font-size: 0.8125rem; color: #9CA3AF; text-align: center; padding: 1.5rem 0; margin: 0; }

/* ── Panel derecho ── */
.panel-der {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 12px;
  display: flex; flex-direction: column; overflow: hidden; min-height: 0;
}

.empty-editor {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.75rem; color: #9CA3AF;
}
.empty-editor svg { width: 48px; height: 48px; }
.empty-editor p { font-size: 0.875rem; margin: 0; }

/* 1. Header */
.editor-header {
  display: flex; align-items: center; gap: 0.875rem;
  padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.plan-avatar {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 1.125rem; font-weight: 700;
}
.editor-info { flex: 1; min-width: 0; }
.editor-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.125rem; }
.editor-detalle { font-size: 0.8125rem; color: #6B7280; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.editor-stat {
  padding: 0.25rem 0.75rem; border-radius: 100px;
  background: #F3F4F6; color: #374151;
  font-size: 0.8125rem; font-weight: 600; flex-shrink: 0;
}

/* 2. Barra rápida */
.barra-rapida {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.625rem 1.25rem; border-bottom: 1px solid #F3F4F6;
  background: #fff; flex-shrink: 0; gap: 1rem;
}
.barra-rapida-acciones { display: flex; gap: 0.5rem; }
.btn-accion {
  padding: 0.35rem 0.875rem; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;
  border: 1px solid #C4B5FD; background: #EEF2FF; color: #4338CA;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-accion:hover { background: #DDD6FE; }
.btn-gris { background: #F9FAFB; border-color: #E5E7EB; color: #6B7280; }
.btn-gris:hover { background: #F3F4F6; }
.barra-hint { font-size: 0.75rem; color: #9CA3AF; margin: 0; }

/* 3. Grid de permisos */
.permisos-grid {
  flex: 1; overflow-y: auto; padding: 0.875rem 1rem;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 0.75rem;
  align-content: start;
}

.cat-card {
  border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden;
}

.cat-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.625rem 0.75rem; background: #F9FAFB;
  border-bottom: 1px solid #F3F4F6;
}
.cat-label {
  display: flex; align-items: center; gap: 0.375rem;
  flex: 1; cursor: pointer; min-width: 0;
}
.cat-check { cursor: pointer; accent-color: #7C3AED; flex-shrink: 0; }
.cat-nombre {
  font-size: 0.8125rem; font-weight: 600; color: #374151;
  text-transform: capitalize; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cat-count {
  font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.375rem;
  border-radius: 100px; background: #F3F4F6; color: #6B7280; flex-shrink: 0;
}
.cat-count.completo { background: #EEF2FF; color: #4338CA; }

.perm-lista { padding: 0.5rem 0.75rem; display: flex; flex-direction: column; gap: 0.25rem; }
.perm-item {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.8125rem; color: #374151; cursor: pointer;
}
.perm-check { accent-color: #7C3AED; cursor: pointer; flex-shrink: 0; }
.perm-nombre { line-height: 1.4; }

/* 4. Footer */
.editor-footer {
  padding: 0.75rem 1.25rem; border-top: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  flex-shrink: 0;
}
.footer-acciones { display: flex; gap: 0.625rem; }
.btn-cancelar {
  padding: 0.5rem 1rem; border: 1px solid #E5E7EB; border-radius: 8px;
  background: #fff; color: #374151; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-cancelar:hover { background: #F9FAFB; }
.btn-guardar {
  padding: 0.5rem 1.25rem; border: none; border-radius: 8px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600; cursor: pointer;
  font-family: inherit; transition: opacity 0.15s;
  display: flex; align-items: center; gap: 0.5rem;
}
.btn-guardar:hover:not(:disabled) { opacity: 0.9; }
.btn-guardar:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-sm {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
}
</style>
