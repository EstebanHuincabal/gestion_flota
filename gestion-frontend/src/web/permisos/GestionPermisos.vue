<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()

const usuarios       = ref([])
const todosPermisos  = ref([])
const usuarioSel     = ref(null)
const permisosUsuario = ref([])
const planModulos    = ref([])
const planNombre     = ref('')
const cargando       = ref(true)
const cargandoPerm   = ref(false)
const guardando      = ref(false)
const mensaje        = ref('')
const errorMsg       = ref('')
const busqueda       = ref('')

// ── Mapeo categoría → módulo del plan ──────────────────────────────────────
const CATEGORIA_A_MODULO = {
  flotas:       'flotas',
  vehiculos:    'vehiculos',
  conductores:  'conductores',
  mantenciones: 'mantencion_correctiva',
  documentos:   'documentos',
  dashboard:    'dashboard',
  predictivo:   'mantencion_predictiva',
  gps:          'gps',
  reportes:     'reportes',
  usuarios:     null,
}

const PLAN_MINIMO = {
  flotas:                   'Básico',
  vehiculos:                'Básico',
  conductores:              'Básico',
  mantencion_correctiva:    'Básico',
  documentos:               'Básico',
  dashboard:                'Básico',
  mantencion_predictiva:    'Pro',
  notificaciones_avanzadas: 'Pro',
  gps:                      'Enterprise',
  geofencing:               'Enterprise',
  reportes:                 'Enterprise',
  exportacion:              'Enterprise',
  api_access:               'Enterprise',
}

const TODOS_MODULOS = [
  { key: 'flotas',                   label: 'Flotas'            },
  { key: 'vehiculos',                label: 'Vehículos'         },
  { key: 'conductores',              label: 'Conductores'       },
  { key: 'mantencion_correctiva',    label: 'Mantenciones'      },
  { key: 'documentos',               label: 'Documentos'        },
  { key: 'dashboard',                label: 'Dashboard'         },
  { key: 'mantencion_predictiva',    label: 'Predictivo'        },
  { key: 'notificaciones_avanzadas', label: 'Notif. avanzadas'  },
  { key: 'gps',                      label: 'GPS'               },
  { key: 'reportes',                 label: 'Reportes'          },
  { key: 'exportacion',              label: 'Exportación'       },
  { key: 'api_access',               label: 'API'               },
]

// ── Carga inicial ───────────────────────────────────────────────────────────
onMounted(async () => {
  const [resU, resP] = await Promise.all([
    apiFetch('/api/usuarios/?rol=USUARIO'),
    apiFetch('/api/permisos/'),
  ])
  if (resU.ok) usuarios.value      = await resU.json()
  if (resP.ok) todosPermisos.value = await resP.json()
  cargando.value = false
})

// ── Filtro de búsqueda ──────────────────────────────────────────────────────
const usuariosFiltrados = computed(() => {
  const q = busqueda.value.trim().toLowerCase()
  if (!q) return usuarios.value
  return usuarios.value.filter(u =>
    (u.nombre || '').toLowerCase().includes(q) ||
    u.email.toLowerCase().includes(q) ||
    (u.empresa || '').toLowerCase().includes(q)
  )
})

// ── Seleccionar usuario ─────────────────────────────────────────────────────
const seleccionar = async (u) => {
  usuarioSel.value    = u
  mensaje.value       = ''
  errorMsg.value      = ''
  permisosUsuario.value = []
  planModulos.value   = []
  planNombre.value    = ''
  cargandoPerm.value  = true

  const res = await apiFetch(`/api/usuarios/${u.id}/permisos/`)
  if (res.ok) {
    const data = await res.json()
    permisosUsuario.value = [...(data.permisos || [])]
    planModulos.value     = data.plan_modulos || []
    planNombre.value      = data.plan_nombre  || ''
  }
  cargandoPerm.value = false
}

// ── Permisos agrupados por categoría ───────────────────────────────────────
const permisosAgrupados = computed(() => {
  const grupos = {}
  for (const p of todosPermisos.value) {
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

// ── Módulos bloqueados ──────────────────────────────────────────────────────
const esBloqueado = (categoria) => {
  const modulo = CATEGORIA_A_MODULO[categoria]
  if (modulo === null || modulo === undefined) return false
  return !planModulos.value.includes(modulo)
}

const planMinimoParaCategoria = (categoria) => {
  const modulo = CATEGORIA_A_MODULO[categoria]
  if (!modulo) return null
  return PLAN_MINIMO[modulo] || null
}

// ── Checkboxes de categoría ─────────────────────────────────────────────────
const categoriaCompleta = (permisosCat) =>
  permisosCat.every(p => permisosUsuario.value.includes(p.codigo))

const categoriaIndeterminate = (permisosCat) => {
  const alguno = permisosCat.some(p => permisosUsuario.value.includes(p.codigo))
  return alguno && !categoriaCompleta(permisosCat)
}

const toggleCategoria = (permisosCat) => {
  const codigos = permisosCat.map(p => p.codigo)
  if (categoriaCompleta(permisosCat)) {
    permisosUsuario.value = permisosUsuario.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosUsuario.value.includes(c))
    permisosUsuario.value = [...permisosUsuario.value, ...nuevos]
  }
}

// Solo los códigos de categorías desbloqueadas
const permisosDesbloqueados = computed(() => {
  const lista = []
  for (const [cat, perms] of Object.entries(permisosAgrupados.value)) {
    if (!esBloqueado(cat)) lista.push(...perms.map(p => p.codigo))
  }
  return lista
})

const seleccionarTodos  = () => { permisosUsuario.value = [...permisosDesbloqueados.value] }
const deseleccionarTodos = () => { permisosUsuario.value = [] }

// ── Guardar ─────────────────────────────────────────────────────────────────
const guardar = async () => {
  if (!usuarioSel.value) return
  guardando.value = true
  mensaje.value   = ''
  errorMsg.value  = ''
  try {
    const permisosAGuardar = permisosUsuario.value.filter(c => permisosDesbloqueados.value.includes(c))
    const res = await apiFetch(`/api/usuarios/${usuarioSel.value.id}/permisos/`, {
      method: 'PUT',
      body:   { permisos: permisosAGuardar },
    })
    const data = await res.json()
    if (!res.ok) {
      errorMsg.value = data.error || 'Error al guardar permisos.'
      return
    }
    const idx = usuarios.value.findIndex(u => u.id === usuarioSel.value.id)
    if (idx !== -1) usuarios.value[idx].permisos = [...permisosAGuardar]
    usuarioSel.value.permisos = [...permisosAGuardar]
    mensaje.value = 'Permisos guardados correctamente.'
  } catch {
    errorMsg.value = 'Error de conexión con el servidor.'
  } finally {
    guardando.value = false
  }
}

const cancelar = () => {
  if (usuarioSel.value) seleccionar(usuarioSel.value)
}

const totalActivos = computed(() => permisosUsuario.value.length)
const bannerExpandido = ref(false)
</script>

<template>
  <div class="page">

    <!-- Cabecera -->
    <div class="page-header">
      <h1 class="page-title">Gestión de Permisos</h1>
      <p class="page-subtitle">Configura los permisos de cada usuario dentro de los módulos habilitados en su plan</p>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando datos...</span>
    </div>

    <div v-else class="split">

      <!-- ── Panel izquierdo: lista de usuarios ── -->
      <aside class="panel-izq">
        <div class="search-wrap">
          <svg class="search-ico" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <input v-model="busqueda" placeholder="Buscar..." class="search-input"/>
        </div>

        <p class="lista-count">{{ usuariosFiltrados.length }} usuario{{ usuariosFiltrados.length !== 1 ? 's' : '' }}</p>

        <div class="lista-usuarios">
          <button
            v-for="u in usuariosFiltrados"
            :key="u.id"
            :class="['usuario-item', { selected: usuarioSel?.id === u.id }]"
            @click="seleccionar(u)"
          >
            <div class="usuario-avatar">{{ (u.nombre || u.email)[0].toUpperCase() }}</div>
            <div class="usuario-info">
              <p class="usuario-nombre">{{ u.nombre || u.email }}</p>
              <p class="usuario-empresa">{{ u.empresa || 'Sin empresa' }}</p>
            </div>
            <span class="perm-badge">{{ (u.permisos || []).length }}</span>
          </button>

          <p v-if="!usuariosFiltrados.length" class="empty-list">Sin resultados.</p>
        </div>
      </aside>

      <!-- ── Panel derecho: editor ── -->
      <section class="panel-der">

        <!-- Estado vacío -->
        <div v-if="!usuarioSel" class="empty-editor">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <p>Selecciona un usuario para editar sus permisos</p>
        </div>

        <template v-else>

          <!-- 1. Header del usuario -->
          <div class="editor-header">
            <div class="editor-avatar">{{ (usuarioSel.nombre || usuarioSel.email)[0].toUpperCase() }}</div>
            <div class="editor-info">
              <p class="editor-nombre">{{ usuarioSel.nombre || usuarioSel.email }}</p>
              <p class="editor-detalle">{{ usuarioSel.email }} · {{ usuarioSel.empresa || 'Sin empresa' }}</p>
            </div>
            <span class="editor-stat">{{ totalActivos }} / {{ todosPermisos.length }} permisos</span>
          </div>

          <!-- 2. Banner de plan -->
          <div v-if="cargandoPerm" class="plan-banner-skeleton">Cargando plan...</div>
          <div v-else class="plan-banner">
            <div class="plan-banner-izq">
              <div class="plan-banner-top">
                <div class="plan-empresa-label">
                  Plan de <strong>{{ usuarioSel.empresa || 'Sin empresa' }}</strong>
                </div>
                <span class="plan-pill">{{ planNombre || 'Sin plan' }}</span>
                <button class="btn-toggle-banner" @click="bannerExpandido = !bannerExpandido">
                  {{ bannerExpandido ? '▴ ocultar' : '▾ ver módulos' }}
                </button>
              </div>
              <div v-if="bannerExpandido" class="modulos-lista">
                <template v-for="m in TODOS_MODULOS" :key="m.key">
                  <span v-if="planModulos.includes(m.key)" class="modulo-tag incluido">{{ m.label }}</span>
                  <span v-else class="modulo-tag excluido"><s>{{ m.label }}</s></span>
                </template>
              </div>
            </div>
            <button class="btn-ver-plan" @click="router.push('/planes')">Ver plan →</button>
          </div>

          <!-- 3. Barra rápida -->
          <div class="barra-rapida">
            <div class="barra-rapida-acciones">
              <button class="btn-accion" @click="seleccionarTodos">Seleccionar todos</button>
              <button class="btn-accion btn-gris" @click="deseleccionarTodos">Deseleccionar todos</button>
            </div>
            <div class="barra-rapida-leyenda">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="candado-ico">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
              </svg>
              <span>Los módulos bloqueados requieren un plan superior</span>
            </div>
          </div>

          <!-- 4. Grid de permisos -->
          <div v-if="cargandoPerm" class="loading-perm">Cargando permisos...</div>
          <div v-else class="permisos-grid">
            <div
              v-for="(permisosCat, cat) in permisosAgrupados"
              :key="cat"
              :class="['cat-card', { bloqueada: esBloqueado(cat) }]"
            >
              <!-- Header de categoría -->
              <div class="cat-header">
                <div class="cat-header-top">
                  <label class="cat-label">
                    <input
                      type="checkbox"
                      :checked="categoriaCompleta(permisosCat)"
                      :indeterminate="categoriaIndeterminate(permisosCat)"
                      :disabled="esBloqueado(cat)"
                      @change="toggleCategoria(permisosCat)"
                      class="cat-check"
                    />
                    <span class="cat-nombre">{{ cat }}</span>
                  </label>
                  <span :class="['cat-count', { completo: categoriaCompleta(permisosCat) }]">
                    {{ permisosCat.filter(p => permisosUsuario.includes(p.codigo)).length }}/{{ permisosCat.length }}
                  </span>
                </div>
                <span v-if="esBloqueado(cat)" class="bloqueo-badge">
                  Requiere {{ planMinimoParaCategoria(cat) }}
                </span>
              </div>

              <!-- Lista de permisos individuales -->
              <div class="perm-lista">
                <label
                  v-for="p in permisosCat"
                  :key="p.codigo"
                  class="perm-item"
                >
                  <input
                    type="checkbox"
                    :value="p.codigo"
                    v-model="permisosUsuario"
                    :disabled="esBloqueado(cat)"
                    class="perm-check"
                  />
                  <span class="perm-nombre">{{ p.nombre }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- 5. Footer -->
          <div class="editor-footer">
            <transition name="fade">
              <p v-if="mensaje" class="msg-ok">✓ {{ mensaje }}</p>
              <p v-else-if="errorMsg" class="msg-error">{{ errorMsg }}</p>
            </transition>
            <div class="footer-acciones">
              <button class="btn-cancelar" @click="cancelar">Cancelar</button>
              <button class="btn-guardar" @click="guardar" :disabled="guardando">
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

.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
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

.search-wrap {
  position: relative; padding: 0.75rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.search-ico {
  position: absolute; left: 1.25rem; top: 50%; transform: translateY(-50%);
  width: 15px; height: 15px; color: #9CA3AF;
}
.search-input {
  width: 100%; padding: 0.45rem 0.75rem 0.45rem 2rem;
  border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.8125rem; color: #111827; background: #F9FAFB;
  outline: none; font-family: inherit;
}
.search-input:focus { border-color: #7C3AED; background: #fff; }

.lista-count {
  font-size: 0.75rem; color: #9CA3AF; font-weight: 500;
  padding: 0.5rem 0.75rem 0.25rem; flex-shrink: 0;
}

.lista-usuarios { flex: 1; overflow-y: auto; padding: 0.25rem 0.5rem 0.5rem; }

.usuario-item {
  width: 100%; display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.5rem; border-radius: 8px; border: none; background: transparent;
  cursor: pointer; text-align: left; transition: background 0.12s;
}
.usuario-item:hover { background: #F5F3FF; }
.usuario-item.selected { background: #EEF2FF; }

.usuario-avatar {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700;
}
.usuario-info { flex: 1; min-width: 0; }
.usuario-nombre { font-size: 0.8125rem; font-weight: 600; color: #111827; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.usuario-empresa { font-size: 0.6875rem; color: #9CA3AF; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.perm-badge {
  padding: 0.125rem 0.375rem; border-radius: 100px;
  background: #EEF2FF; color: #4338CA;
  font-size: 0.6875rem; font-weight: 700; flex-shrink: 0;
}

.empty-list { font-size: 0.8125rem; color: #9CA3AF; text-align: center; padding: 1rem 0; margin: 0; }

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
.editor-avatar {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700;
}
.editor-info { flex: 1; min-width: 0; }
.editor-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.125rem; }
.editor-detalle { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.editor-stat {
  padding: 0.25rem 0.75rem; border-radius: 100px;
  background: #F3F4F6; color: #374151;
  font-size: 0.8125rem; font-weight: 600; flex-shrink: 0;
}

/* 2. Banner de plan */
.plan-banner-skeleton {
  padding: 0.75rem 1.25rem; font-size: 0.8125rem; color: #9CA3AF;
  border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.plan-banner {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
  padding: 0.625rem 1.25rem; border-bottom: 1px solid #F3F4F6;
  background: #FAFAFA; flex-shrink: 0;
}
.plan-banner-izq { display: flex; flex-direction: column; gap: 0.375rem; flex: 1; min-width: 0; }
.plan-banner-top { display: flex; align-items: center; gap: 0.625rem; flex-wrap: wrap; }
.plan-empresa-label { font-size: 0.75rem; color: #6B7280; }
.plan-pill {
  padding: 0.2rem 0.75rem; border-radius: 100px;
  background: #7C3AED; color: #fff;
  font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
}
.btn-toggle-banner {
  font-size: 0.6875rem; color: #6B7280; background: none; border: none;
  cursor: pointer; font-family: inherit; padding: 0; white-space: nowrap;
  transition: color 0.15s;
}
.btn-toggle-banner:hover { color: #4338CA; }
.modulos-lista { display: flex; flex-wrap: wrap; gap: 0.375rem; }
.modulo-tag {
  font-size: 0.6875rem; font-weight: 600; padding: 0.2rem 0.5rem;
  border-radius: 100px;
}
.modulo-tag.incluido { background: #DCFCE7; color: #15803D; }
.modulo-tag.excluido { background: #F3F4F6; color: #9CA3AF; }
.btn-ver-plan {
  padding: 0.3rem 0.75rem; border-radius: 6px; border: 1px solid #E5E7EB;
  background: #fff; color: #4338CA; font-size: 0.75rem; font-weight: 600;
  cursor: pointer; white-space: nowrap; flex-shrink: 0; font-family: inherit;
  transition: background 0.15s; align-self: flex-start;
}
.btn-ver-plan:hover { background: #EEF2FF; }

/* 3. Barra rápida */
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

.barra-rapida-leyenda {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.75rem; color: #9CA3AF;
}
.candado-ico { width: 13px; height: 13px; flex-shrink: 0; }

/* 4. Grid de permisos */
.loading-perm {
  flex: 1; padding: 1.5rem 1.25rem; font-size: 0.875rem; color: #9CA3AF;
  display: flex; align-items: center; justify-content: center;
}
.permisos-grid {
  flex: 1; overflow-y: auto; padding: 0.875rem 1rem;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 0.75rem;
  align-content: start;
}

.cat-card {
  border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden;
  transition: opacity 0.2s;
}
.cat-card.bloqueada { opacity: 0.5; pointer-events: none; }

.cat-header {
  display: flex; flex-direction: column; gap: 0.25rem;
  padding: 0.625rem 0.75rem; background: #F9FAFB;
  border-bottom: 1px solid #F3F4F6;
}
.cat-header-top {
  display: flex; align-items: center; gap: 0.5rem;
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

.bloqueo-badge {
  font-size: 0.625rem; font-weight: 700; padding: 0.125rem 0.375rem;
  border-radius: 100px; background: #FEF3C7; color: #92400E;
  white-space: nowrap; flex-shrink: 0;
}

.perm-lista { padding: 0.5rem 0.75rem; display: flex; flex-direction: column; gap: 0.25rem; }
.perm-item {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.8125rem; color: #374151; cursor: pointer;
}
.perm-check { accent-color: #7C3AED; cursor: pointer; flex-shrink: 0; }
.perm-nombre { line-height: 1.4; }

/* 5. Footer */
.editor-footer {
  padding: 0.75rem 1.25rem; border-top: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  flex-shrink: 0;
}
.footer-acciones { display: flex; gap: 0.625rem; }
.msg-ok    { font-size: 0.8125rem; color: #15803D; margin: 0; font-weight: 500; }
.msg-error { font-size: 0.8125rem; color: #DC2626; margin: 0; font-weight: 500; }
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

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
