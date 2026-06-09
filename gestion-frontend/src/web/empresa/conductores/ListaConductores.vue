<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../utils/permisos.js'
import ConfirmModal from '../../../components/ConfirmModal.vue'
import { useToast } from '../../../utils/useToast.js'

const router     = useRouter()
const { ruta }   = useEmpresaNav()

const usuario      = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')

// Selector de empresa (solo SUPERADMIN)
const empresas         = ref([])
const empresaActiva    = ref(getEmpresaActiva())
const cargandoEmpresas = ref(false)
// Modo "Todas las empresas": vista de solo lectura (se ocultan acciones de escritura).
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)
const mostrarDropdown  = ref(false)
const busqueda         = ref('')

const empresasFiltradas = computed(() => {
  if (!busqueda.value.trim()) return empresas.value
  const q = busqueda.value.toLowerCase()
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

const cargarEmpresas = async () => {
  if (!esSuperadmin.value) return
  cargandoEmpresas.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = conOpcionTodas(await res.json())
  } finally { cargandoEmpresas.value = false }
}

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  cargar()
}

const conductores = ref([])
const vehiculos   = ref([])
const cargando    = ref(true)
const sinEmpresa  = ref(false)

const confirmState = ref({ visible: false, accion: null, conductor: null })
const toast = useToast()

// modal asignar vehículo
const modalAsignar   = ref(false)
const conductorActivo = ref(null)
const vehiculoSeleccionado = ref(null)
const guardandoAsig  = ref(false)

// Detección de traspaso: el vehículo elegido ya tiene OTRO conductor distinto al
// que estamos editando.
const traspasoVehiculo = computed(() => {
  const v = vehiculos.value.find(x => x.id === vehiculoSeleccionado.value)
  const ca = v?.conductor_asignado
  if (!ca) return null
  if (ca.id === conductorActivo.value?.id) return null
  return { patente: v.patente, conductor: ca.nombre }
})

const cargar = async () => {
  cargando.value   = true
  sinEmpresa.value = false
  const [rC, rV] = await Promise.all([
    apiFetchEmpresa('/api/empresa/conductores/'),
    apiFetchEmpresa('/api/empresa/vehiculos/'),
  ])
  if (rC.status === 400) { const d = await rC.json(); if (d.error === 'sin_empresa') { sinEmpresa.value = true; cargando.value = false; return } }
  if (rC.ok) conductores.value = await rC.json()
  if (rV.ok) vehiculos.value   = (await rV.json()).filter(v => v.activo)
  cargando.value = false
}

const abrirAsignar = (c) => {
  conductorActivo.value     = c
  vehiculoSeleccionado.value = c.vehiculo?.id ?? null
  modalAsignar.value = true
}

const guardarAsignacion = async () => {
  if (guardandoAsig.value) return
  if (!vehiculoSeleccionado.value) {
    await desasignar(conductorActivo.value, true)
    return
  }
  guardandoAsig.value = true
  const eraTraspaso = !!traspasoVehiculo.value
  try {
    const res  = await apiFetchEmpresa(`/api/empresa/conductores/${conductorActivo.value.id}/asignar/`, {
      method: 'POST',
      body:   { vehiculo_id: vehiculoSeleccionado.value },
    })
    const data = await res.json()
    if (res.ok) {
      modalAsignar.value = false
      await cargar()   // recarga conductores y vehículos (el traspaso afecta a otro conductor)
      toast.agregar(eraTraspaso ? 'Vehículo traspasado correctamente' : 'Vehículo asignado correctamente', 'success')
    } else {
      toast.agregar(data.error || 'Error al asignar vehículo', 'error')
    }
  } finally {
    guardandoAsig.value = false
  }
}

const desasignar = async (c, desdModal = false) => {
  const res = await apiFetchEmpresa(`/api/empresa/conductores/${c.id}/desasignar/`, { method: 'POST' })
  if (res.ok) {
    const data = await res.json()
    const idx  = conductores.value.findIndex(x => x.id === c.id)
    if (idx !== -1) conductores.value[idx] = data
    if (desdModal) modalAsignar.value = false
    toast.agregar('Asignación removida', 'success')
  }
}

const toggleActivo = (c) => {
  confirmState.value = {
    visible: true,
    accion: c.is_active ? 'desactivar' : 'activar',
    conductor: c
  }
}

const confirmarToggle = async () => {
  const c = confirmState.value.conductor
  confirmState.value.visible = false
  if (!c) return

  const res = c.is_active
    ? await apiFetchEmpresa(`/api/empresa/conductores/${c.id}/`, { method: 'DELETE' })
    : await apiFetchEmpresa(`/api/empresa/conductores/${c.id}/`, { method: 'PUT', body: { is_active: true } })

  if (res.ok) {
    await cargar()
    toast.agregar(`Conductor ${c.is_active ? 'desactivado' : 'activado'}`, 'success')
  }
}

const cancelarToggle = () => {
  confirmState.value.visible = false
}

// ── Verificación de permisos ─────────────────────────────
const sinPermiso = (msg) =>
  window.dispatchEvent(new CustomEvent('permiso-denegado', { detail: msg }))

const irNuevoConductor = () => {
  if (!tienePermiso('conductores.crear')) return sinPermiso('No tienes permiso para crear conductores.')
  router.push(ruta('/conductores/nuevo'))
}
const irEditarConductor = (id) => {
  if (!tienePermiso('conductores.editar')) return sinPermiso('No tienes permiso para editar conductores.')
  router.push(ruta(`/conductores/${id}/editar`))
}
const abrirAsignarConPermiso = (c) => {
  if (!tienePermiso('conductores.asignar')) return sinPermiso('No tienes permiso para asignar vehículos.')
  abrirAsignar(c)
}
const toggleActivoConPermiso = (c) => {
  if (!tienePermiso('conductores.editar')) return sinPermiso('No tienes permiso para activar/desactivar conductores.')
  toggleActivo(c)
}

onMounted(async () => {
  await cargarEmpresas()
  await cargar()
})
</script>

<template>
  <div class="page">
    <ConfirmModal
      v-if="confirmState.visible"
      :titulo="confirmState.accion === 'desactivar' ? 'Desactivar conductor' : 'Activar conductor'"
      :mensaje="`¿Quieres ${confirmState.accion} a ${confirmState.conductor?.nombre}?`"
      :labelOk="confirmState.accion === 'desactivar' ? 'Desactivar' : 'Activar'"
      :peligroso="confirmState.accion === 'desactivar'"
      @confirmar="confirmarToggle"
      @cancelar="cancelarToggle"
    />

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Conductores</h1>
        <p class="page-subtitle">Gestiona los conductores de la empresa</p>
      </div>

      <div class="header-actions">
        <!-- Selector empresa (solo SUPERADMIN) -->
        <div v-if="esSuperadmin" class="selector-wrap">
          <button
            class="selector-btn"
            :class="{ 'sin-seleccion': !empresaActiva }"
            @click="mostrarDropdown = !mostrarDropdown"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
            <span>{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="chevron">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <div v-if="mostrarDropdown" class="selector-dropdown">
            <input
              v-model="busqueda"
              class="dropdown-search"
              placeholder="Buscar empresa..."
              autofocus
            />
            <div v-if="cargandoEmpresas" class="dropdown-loading">Cargando...</div>
            <template v-else>
              <button
                v-for="emp in empresasFiltradas"
                :key="emp.id"
                class="dropdown-option"
                :class="{ selected: empresaActiva?.id === emp.id }"
                @click="seleccionarEmpresa(emp)"
              >
                <span class="option-avatar">{{ emp.nombre[0].toUpperCase() }}</span>
                <span>{{ emp.nombre }}</span>
                <svg v-if="empresaActiva?.id === emp.id" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="check-icon">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
              </button>
              <p v-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</p>
            </template>
          </div>
          <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
        </div>

        <button
          class="btn-primary"
          @click="irNuevoConductor"
          :disabled="esSuperadmin && !empresaActiva"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Nuevo Conductor
        </button>
      </div>
    </div>

    <!-- Sin empresa seleccionada -->
    <div v-if="sinEmpresa" class="sin-empresa">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
      </svg>
      <p>Selecciona una empresa en el selector de arriba para ver sus conductores.</p>
    </div>

    <!-- Cargando -->
    <div v-else-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando conductores...</span>
    </div>

    <!-- Sin conductores -->
    <div v-else-if="!sinEmpresa && !conductores.length" class="empty">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      <p>No hay conductores registrados</p>
      <button class="btn-primary" @click="irNuevoConductor">Agregar conductor</button>
    </div>

    <!-- Tabla -->
    <div v-else class="card">
      <table class="table">
        <thead>
          <tr>
            <th>Conductor</th>
            <th>Empresa</th>
            <th>RUT</th>
            <th>Teléfono</th>
            <th>Licencia</th>
            <th>Vehículo asignado</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in conductores" :key="c.id" :class="{ inactivo: !c.is_active }">
            <td>
              <div class="conductor-info">
                <div class="avatar">{{ (c.nombre || 'C')[0].toUpperCase() }}</div>
                <div>
                  <p class="nombre">{{ c.nombre }}</p>
                  <p class="email">{{ c.email }}</p>
                </div>
              </div>
            </td>
            <td>{{ c.empresa_nombre || '—' }}</td>
            <td class="mono">{{ c.rut || '—' }}</td>
            <td>{{ c.telefono || '—' }}</td>
            <td>{{ c.licencia || '—' }}</td>
            <td>
              <span v-if="c.vehiculo" class="badge badge-vehiculo">
                {{ c.vehiculo.patente }} · {{ c.vehiculo.descripcion }}
              </span>
              <span v-else class="sin-asignar">Sin vehículo</span>
            </td>
            <td>
              <span :class="['badge', c.is_active ? 'badge-activo' : 'badge-inactivo']">
                {{ c.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td>
              <div class="acciones">
                <button class="btn-icon" title="Ver Detalle" @click="router.push(ruta(`/conductores/${c.id}`))">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                  </svg>
                </button>
                <button class="btn-icon" title="Asignar vehículo" @click="abrirAsignarConPermiso(c)" :disabled="!c.is_active">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l1 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
                  </svg>
                </button>
                <button class="btn-icon" title="Editar" @click="irEditarConductor(c.id)">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button :class="['btn-icon', c.is_active ? 'danger' : 'success']"
                  :title="c.is_active ? 'Desactivar' : 'Activar'"
                  @click="toggleActivoConPermiso(c)">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path v-if="c.is_active" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal asignar vehículo -->
    <Teleport to="body">
      <div v-if="modalAsignar" class="overlay" @click.self="modalAsignar = false">
        <div class="modal">
          <h2 class="modal-title">Asignar vehículo</h2>
          <p class="modal-sub">{{ conductorActivo?.nombre }}</p>

          <div class="form-group">
            <label class="label">Vehículo</label>
            <select v-model="vehiculoSeleccionado" class="input select">
              <option :value="null">— Sin vehículo —</option>
              <option v-for="v in vehiculos" :key="v.id" :value="v.id">
                {{ v.patente }} · {{ v.marca }} {{ v.modelo }}{{ v.conductor_asignado && v.conductor_asignado.id !== conductorActivo?.id ? ` — lo maneja ${v.conductor_asignado.nombre}` : '' }}
              </option>
            </select>
          </div>

          <!-- Aviso de traspaso: el vehículo elegido ya tiene otro conductor -->
          <div v-if="traspasoVehiculo" class="aviso-traspaso">
            <strong>{{ traspasoVehiculo.patente }}</strong> lo maneja <strong>{{ traspasoVehiculo.conductor }}</strong>.
            Al continuar, se le quitará y pasará a <strong>{{ conductorActivo?.nombre }}</strong>.
          </div>

          <div class="modal-actions">
            <button class="btn-secondary" @click="modalAsignar = false" :disabled="guardandoAsig">Cancelar</button>
            <button class="btn-primary" @click="guardarAsignacion" :disabled="guardandoAsig">
              {{ guardandoAsig ? 'Guardando...' : (traspasoVehiculo ? 'Traspasar' : 'Guardar') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.75rem; flex-wrap: wrap; gap: 1rem; }
.page-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }

/* Selector empresa */
.selector-wrap { position: relative; z-index: 20; }
.selector-btn {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.875rem; border-radius: 10px; cursor: pointer;
  font-size: 0.875rem; font-weight: 500; font-family: inherit;
  background: #fff; color: #374151;
  border: 1.5px solid #D1D5DB; transition: border-color 0.15s;
  white-space: nowrap;
}
.selector-btn:hover { border-color: #7C3AED; color: #7C3AED; }
.selector-btn.sin-seleccion { border-style: dashed; color: #9CA3AF; }
.selector-btn svg:first-child { width: 16px; height: 16px; flex-shrink: 0; }
.chevron { width: 14px; height: 14px; flex-shrink: 0; }

.selector-dropdown {
  position: absolute; top: calc(100% + 6px); right: 0;
  width: 260px; background: #fff; border: 1px solid #E5E7EB;
  border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  overflow: hidden; z-index: 30;
}
.dropdown-search {
  width: 100%; padding: 0.625rem 0.875rem; border: none;
  border-bottom: 1px solid #F3F4F6; outline: none;
  font-size: 0.875rem; font-family: inherit; color: #111827;
}
.dropdown-loading { padding: 0.75rem 1rem; font-size: 0.875rem; color: #9CA3AF; }
.dropdown-option {
  display: flex; align-items: center; gap: 0.625rem;
  width: 100%; padding: 0.625rem 0.875rem; border: none;
  background: none; cursor: pointer; font-size: 0.875rem;
  color: #374151; font-family: inherit; text-align: left;
  transition: background 0.12s;
}
.dropdown-option:hover { background: #F5F3FF; color: #4F46E5; }
.dropdown-option.selected { background: #EDE9FE; color: #4F46E5; font-weight: 600; }
.option-avatar {
  width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg,#4F46E5,#7C3AED);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700;
}
.check-icon { width: 14px; height: 14px; margin-left: auto; color: #7C3AED; }
.dropdown-empty { padding: 0.75rem 1rem; font-size: 0.875rem; color: #9CA3AF; margin: 0; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 10; }

.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }

.sin-empresa { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 5rem 2rem; color: #9CA3AF; text-align: center; }
.sin-empresa svg { width: 56px; height: 56px; opacity: 0.4; }
.sin-empresa p { font-size: 1rem; margin: 0; color: #6B7280; }
.empty { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 4rem 0; color: #9CA3AF; }
.empty svg { width: 56px; height: 56px; }
.empty p { font-size: 0.95rem; margin: 0; }

.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }

.table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.table th { padding: 0.75rem 1rem; background: #F9FAFB; color: #6B7280; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; text-align: left; border-bottom: 1px solid #E5E7EB; }
.table td { padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; color: #374151; vertical-align: middle; }
.table tr:last-child td { border-bottom: none; }
.table tr.inactivo td { opacity: 0.5; }

.conductor-info { display: flex; align-items: center; gap: 0.75rem; }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 0.875rem; font-weight: 700; flex-shrink: 0; }
.nombre { font-weight: 600; color: #111827; margin: 0; font-size: 0.875rem; }
.email  { color: #6B7280; margin: 0; font-size: 0.75rem; }
.mono   { font-family: monospace; font-size: 0.8125rem; }
.sin-asignar { color: #9CA3AF; font-size: 0.8125rem; font-style: italic; }

.badge { display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-activo   { background: #D1FAE5; color: #065F46; }
.badge-inactivo { background: #F3F4F6; color: #6B7280; }
.badge-vehiculo { background: #EDE9FE; color: #5B21B6; }

.acciones { display: flex; gap: 0.375rem; }
.btn-icon { width: 32px; height: 32px; border-radius: 8px; border: 1.5px solid #E5E7EB; background: #fff; color: #6B7280; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; }
.btn-icon svg { width: 15px; height: 15px; }
.btn-icon:hover { border-color: #7C3AED; color: #7C3AED; background: #F5F3FF; }
.btn-icon.danger:hover  { border-color: #EF4444; color: #EF4444; background: #FEF2F2; }
.btn-icon.success:hover { border-color: #10B981; color: #10B981; background: #D1FAE5; }
.btn-icon:disabled { opacity: 0.35; cursor: not-allowed; }

.btn-primary {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 1.25rem; background: linear-gradient(135deg,#4F46E5,#7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px;
  cursor: pointer; font-family: inherit; transition: opacity 0.2s;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary svg { width: 16px; height: 16px; }

.btn-secondary {
  padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB;
  border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151;
  cursor: pointer; font-family: inherit; transition: border-color 0.15s;
}
.btn-secondary:hover { border-color: #9CA3AF; }

/* Modal */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 1.75rem; width: 100%; max-width: 420px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.modal-sub   { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.25rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
.aviso-traspaso { margin-top: 0.75rem; padding: 0.65rem 0.85rem; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; font-size: 0.8125rem; color: #92400E; line-height: 1.4; }

.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.select { cursor: pointer; }

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-header { flex-direction: column; align-items: stretch; }
  .page-title { font-size: 1.25rem; }
  .header-actions { flex-direction: column; align-items: stretch; }
  .selector-btn { width: 100%; }
  .btn-primary { justify-content: center; }

  /* Sin scroll: ocultar Empresa(2), RUT(3), Teléfono(4), Licencia(5).
     La info completa está en el detalle del conductor. */
  .card { overflow: visible; }
  .table { min-width: unset; width: 100%; } /* Empresa */ /* RUT */ /* Teléfono */ /* Licencia */

  /* Conductor: ocultar email debajo del nombre */
  .email { display: none; }

  /* Vehículo: texto más corto */
  .badge-vehiculo { font-size: 0.7rem; }

  .modal { width: calc(100vw - 2rem); max-width: 100%; }
  /* Scroll horizontal con thumb visible */
  .tabla-wrap, .tabla-card, .sc-table-wrap, .card, .table-wrap {
    overflow-x: scroll !important;  /* scroll (no auto) → track siempre visible */
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: #A78BFA #EDE9FE;
  }
  .tabla-wrap::-webkit-scrollbar,
  .tabla-card::-webkit-scrollbar,
  .sc-table-wrap::-webkit-scrollbar,
  .card::-webkit-scrollbar,
  .table-wrap::-webkit-scrollbar { height: 8px; }
  .tabla-wrap::-webkit-scrollbar-track,
  .tabla-card::-webkit-scrollbar-track,
  .sc-table-wrap::-webkit-scrollbar-track,
  .card::-webkit-scrollbar-track,
  .table-wrap::-webkit-scrollbar-track { background: #EDE9FE; border-radius: 999px; }
  .tabla-wrap::-webkit-scrollbar-thumb,
  .tabla-card::-webkit-scrollbar-thumb,
  .sc-table-wrap::-webkit-scrollbar-thumb,
  .card::-webkit-scrollbar-thumb,
  .table-wrap::-webkit-scrollbar-thumb { background: #7C3AED; border-radius: 999px; min-width: 40px; }
  .tabla-wrap::-webkit-scrollbar-thumb:hover,
  .tabla-card::-webkit-scrollbar-thumb:hover,
  .sc-table-wrap::-webkit-scrollbar-thumb:hover,
  .card::-webkit-scrollbar-thumb:hover,
  .table-wrap::-webkit-scrollbar-thumb:hover { background: #6D28D9; }
  .tabla-wrap table, .tabla-card table, .sc-table-wrap table,
  .card table, .table-wrap table,
  .tabla, .table, .tabla-flotas, .tabla-vehiculos { min-width: 520px; }

}
</style>
