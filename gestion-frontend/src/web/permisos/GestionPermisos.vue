<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const usuarios      = ref([])
const todosPermisos = ref([])
const usuarioSel    = ref(null)
const permisosUsuario = ref([])
const cargando      = ref(true)
const guardando     = ref(false)
const mensaje       = ref('')
const error         = ref('')
const busqueda      = ref('')

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
  usuarioSel.value   = u
  mensaje.value      = ''
  error.value        = ''
  permisosUsuario.value = [...(u.permisos || [])]
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

const categoriaCompleta = (permisosCat) =>
  permisosCat.every(p => permisosUsuario.value.includes(p.codigo))

const toggleCategoria = (permisosCat) => {
  const codigos = permisosCat.map(p => p.codigo)
  const todos   = categoriaCompleta(permisosCat)
  if (todos) {
    permisosUsuario.value = permisosUsuario.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosUsuario.value.includes(c))
    permisosUsuario.value = [...permisosUsuario.value, ...nuevos]
  }
}

const seleccionarTodos  = () => { permisosUsuario.value = todosPermisos.value.map(p => p.codigo) }
const deseleccionarTodos = () => { permisosUsuario.value = [] }

// ── Guardar ─────────────────────────────────────────────────────────────────
const guardar = async () => {
  if (!usuarioSel.value) return
  guardando.value = true
  mensaje.value   = ''
  error.value     = ''
  try {
    const res = await apiFetch(`/api/usuarios/${usuarioSel.value.id}/permisos/`, {
      method: 'PUT',
      body:   { permisos: permisosUsuario.value },
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.error || 'Error al guardar permisos.'
      return
    }
    // Actualizar el usuario en la lista local
    const idx = usuarios.value.findIndex(u => u.id === usuarioSel.value.id)
    if (idx !== -1) usuarios.value[idx].permisos = [...permisosUsuario.value]
    usuarioSel.value.permisos = [...permisosUsuario.value]
    mensaje.value = 'Permisos guardados correctamente.'
  } catch {
    error.value = 'Error de conexión con el servidor.'
  } finally {
    guardando.value = false
  }
}

const totalActivos = computed(() => permisosUsuario.value.length)
</script>

<template>
  <div class="page">

    <!-- Cabecera -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Gestión de Permisos</h1>
        <p class="page-subtitle">Configura los permisos de cada usuario de manera individual</p>
      </div>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando datos...</span>
    </div>

    <div v-else class="split">

      <!-- ── Panel izquierdo: lista de usuarios ── -->
      <aside class="panel-usuarios">
        <div class="search-wrap">
          <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <input v-model="busqueda" placeholder="Buscar usuario..." class="search-input"/>
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

      <!-- ── Panel derecho: editor de permisos ── -->
      <section class="panel-permisos">

        <div v-if="!usuarioSel" class="empty-editor">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <p>Selecciona un usuario para editar sus permisos</p>
        </div>

        <template v-else>
          <!-- Cabecera del editor -->
          <div class="editor-header">
            <div class="editor-user-info">
              <div class="editor-avatar">{{ (usuarioSel.nombre || usuarioSel.email)[0].toUpperCase() }}</div>
              <div>
                <p class="editor-nombre">{{ usuarioSel.nombre || usuarioSel.email }}</p>
                <p class="editor-detalle">{{ usuarioSel.email }} · {{ usuarioSel.empresa || 'Sin empresa' }}</p>
              </div>
            </div>
            <div class="editor-stats">
              <span class="stat-badge">{{ totalActivos }} / {{ todosPermisos.length }} permisos activos</span>
            </div>
          </div>

          <!-- Acciones rápidas -->
          <div class="acciones-rapidas">
            <button class="btn-accion" @click="seleccionarTodos">Seleccionar todos</button>
            <button class="btn-accion btn-accion-gris" @click="deseleccionarTodos">Deseleccionar todos</button>
          </div>

          <!-- Grilla de permisos por categoría -->
          <div class="permisos-grid">
            <div v-for="(permisosCat, cat) in permisosAgrupados" :key="cat" class="categoria-card">
              <label class="categoria-header">
                <input
                  type="checkbox"
                  :checked="categoriaCompleta(permisosCat)"
                  @change="toggleCategoria(permisosCat)"
                  class="cat-check"
                />
                <span class="cat-nombre">{{ cat }}</span>
                <span class="cat-count">
                  {{ permisosCat.filter(p => permisosUsuario.includes(p.codigo)).length }}/{{ permisosCat.length }}
                </span>
              </label>
              <div class="perm-list">
                <label v-for="p in permisosCat" :key="p.codigo" class="perm-item">
                  <input type="checkbox" :value="p.codigo" v-model="permisosUsuario" class="perm-check"/>
                  <span>{{ p.nombre }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Feedback y botón guardar -->
          <div class="editor-footer">
            <transition name="fade">
              <p v-if="mensaje" class="msg-ok">✓ {{ mensaje }}</p>
              <p v-else-if="error" class="msg-error">{{ error }}</p>
            </transition>
            <button class="btn-guardar" @click="guardar" :disabled="guardando">
              <span v-if="guardando" class="spinner-sm"/>
              {{ guardando ? 'Guardando...' : 'Guardar permisos' }}
            </button>
          </div>
        </template>

      </section>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.page-header { margin-bottom: 1.5rem; flex-shrink: 0; }
.page-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Layout split ── */
.split {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.25rem;
  flex: 1;
  min-height: 0;
}

/* ── Panel izquierdo ── */
.panel-usuarios {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.search-wrap {
  position: relative;
  padding: 0.875rem;
  border-bottom: 1px solid #F3F4F6;
}
.search-icon {
  position: absolute; left: 1.5rem; top: 50%; transform: translateY(-50%);
  width: 16px; height: 16px; color: #9CA3AF; pointer-events: none;
}
.search-input {
  width: 100%; padding: 0.55rem 0.75rem 0.55rem 2.25rem;
  border: 1.5px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; color: #111827; outline: none; font-family: inherit;
  transition: border-color 0.15s;
}
.search-input:focus { border-color: #7C3AED; }

.lista-count { font-size: 0.75rem; font-weight: 600; color: #9CA3AF; padding: 0.5rem 0.875rem 0.25rem; margin: 0; }

.lista-usuarios { flex: 1; overflow-y: auto; padding: 0.25rem 0.5rem 0.5rem; display: flex; flex-direction: column; gap: 2px; }

.usuario-item {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.625rem 0.75rem; border-radius: 10px; border: none;
  background: transparent; cursor: pointer; text-align: left; width: 100%;
  transition: background 0.15s;
}
.usuario-item:hover { background: #F9FAFB; }
.usuario-item.selected { background: #EDE9FE; }

.usuario-avatar {
  flex-shrink: 0; width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8125rem; font-weight: 700; color: #fff;
}
.usuario-info { flex: 1; min-width: 0; }
.usuario-nombre { font-size: 0.8125rem; font-weight: 600; color: #111827; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.usuario-empresa { font-size: 0.75rem; color: #6B7280; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.perm-badge {
  flex-shrink: 0; font-size: 0.6875rem; font-weight: 700;
  background: #EDE9FE; color: #5B21B6;
  padding: 0.15rem 0.45rem; border-radius: 999px;
}

.empty-list { text-align: center; color: #9CA3AF; font-size: 0.875rem; padding: 2rem 1rem; }

/* ── Panel derecho ── */
.panel-permisos {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.empty-editor {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 0.75rem; color: #D1D5DB;
}
.empty-editor svg { width: 56px; height: 56px; }
.empty-editor p { font-size: 0.9375rem; color: #9CA3AF; margin: 0; }

/* Cabecera editor */
.editor-header {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.editor-user-info { display: flex; align-items: center; gap: 0.875rem; }
.editor-avatar {
  flex-shrink: 0; width: 42px; height: 42px; border-radius: 50%;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700; color: #fff;
}
.editor-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.editor-detalle { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.stat-badge {
  font-size: 0.8125rem; font-weight: 600;
  background: #EDE9FE; color: #5B21B6;
  padding: 0.35rem 0.875rem; border-radius: 999px; white-space: nowrap;
}

/* Acciones rápidas */
.acciones-rapidas {
  display: flex; gap: 0.5rem;
  padding: 0.75rem 1.5rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.btn-accion {
  font-size: 0.75rem; font-weight: 600; padding: 0.3rem 0.75rem;
  border: 1.5px solid #7C3AED; border-radius: 6px; color: #7C3AED;
  background: #fff; cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-accion:hover { background: #EDE9FE; }
.btn-accion-gris { border-color: #D1D5DB; color: #6B7280; }
.btn-accion-gris:hover { background: #F9FAFB; }

/* Grilla de permisos */
.permisos-grid {
  flex: 1; overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  align-content: start;
}

.categoria-card {
  border: 1.5px solid #E5E7EB; border-radius: 12px; padding: 0.875rem 1rem;
  transition: border-color 0.15s;
}
.categoria-card:hover { border-color: #C4B5FD; }

.categoria-header {
  display: flex; align-items: center; gap: 0.5rem;
  cursor: pointer; margin-bottom: 0.625rem;
}
.cat-check { accent-color: #7C3AED; width: 15px; height: 15px; cursor: pointer; flex-shrink: 0; }
.cat-nombre { flex: 1; font-size: 0.8125rem; font-weight: 700; color: #1E1B4B; text-transform: capitalize; }
.cat-count { font-size: 0.7rem; font-weight: 600; color: #7C3AED; background: #EDE9FE; padding: 0.1rem 0.4rem; border-radius: 999px; }

.perm-list { display: flex; flex-direction: column; gap: 0.375rem; padding-left: 0.25rem; }
.perm-item { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.perm-item span { font-size: 0.8rem; color: #4B5563; }
.perm-check { accent-color: #7C3AED; width: 13px; height: 13px; cursor: pointer; }

/* Footer del editor */
.editor-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 1rem;
  padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6; flex-shrink: 0;
}

.msg-ok    { font-size: 0.875rem; font-weight: 500; color: #059669; margin: 0; }
.msg-error { font-size: 0.875rem; font-weight: 500; color: #DC2626; margin: 0; }

.btn-guardar {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 1.5rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; border: none; border-radius: 10px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
  font-family: inherit; transition: opacity 0.2s;
  box-shadow: 0 2px 8px rgba(79,70,229,0.3);
}
.btn-guardar:hover:not(:disabled) { opacity: 0.9; }
.btn-guardar:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
