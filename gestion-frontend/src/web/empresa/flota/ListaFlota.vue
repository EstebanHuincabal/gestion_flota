<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, safeJsonParse } from '../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva } from '../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../utils/permisos.js'
import ConfirmModal from '../../../components/ConfirmModal.vue'
import { useToast } from '../../../utils/useToast.js'

const router   = useRouter()
const { ruta } = useEmpresaNav()

const usuario      = computed(() => safeJsonParse(localStorage.getItem('usuario'), {}))
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')

// ── Datos ───────────────────────────────────────────────
const flotas          = ref([])
const todasLasFlotas  = ref([])
const cargando        = ref(true)
const operando        = ref(false)
const error           = ref('')
const sinEmpresa      = ref(false)
const abiertos        = ref({})
const toast = useToast()
const confirm         = ref({ visible: false, item: null, tipo: '', flotaCtx: null })

const COMBUSTIBLE_LABEL = { bencina: 'Bencina', diesel: 'Diésel', electrico: 'Eléctrico', hibrido: 'Híbrido' }
const colspan = computed(() => esSuperadmin.value ? 6 : 4)

// ── Selector de empresa (SUPERADMIN — actúa como filtro) ─
const empresas         = ref([])
const empresaActiva    = ref(getEmpresaActiva())
const cargandoEmpresas = ref(false)
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
    if (res.ok) {
      const data = await res.json()
      empresas.value = Array.isArray(data) ? data : []
    }
  } catch {} finally {
    cargandoEmpresas.value = false
  }
}

// ── Filtrado client-side (SUPERADMIN) ───────────────────
const aplicarFiltro = () => {
  flotas.value = empresaActiva.value
    ? todasLasFlotas.value.filter(f => f.empresa_id === empresaActiva.value.id)
    : todasLasFlotas.value
  flotas.value.forEach(f => { if (!(f.id in abiertos.value)) abiertos.value[f.id] = false })
}

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  aplicarFiltro()
}

const limpiarEmpresa = () => {
  setEmpresaActiva(null)
  empresaActiva.value   = null
  mostrarDropdown.value = false
  aplicarFiltro()
}

// ── Carga ───────────────────────────────────────────────
const cargar = async () => {
  cargando.value   = true
  error.value      = ''
  sinEmpresa.value = false
  try {
    if (esSuperadmin.value) {
      const res = await apiFetch('/api/admin/flotas/')
      if (!res.ok) throw new Error('Error al cargar flotas')
      todasLasFlotas.value = await res.json()
      aplicarFiltro()
    } else {
      const res = await apiFetchEmpresa('/api/empresa/flotas/')
      if (res.status === 400) {
        const d = await res.json()
        if (d.error === 'sin_empresa') { sinEmpresa.value = true; return }
      }
      if (!res.ok) throw new Error('Error al cargar flotas')
      flotas.value = await res.json()
      flotas.value.forEach(f => { if (!(f.id in abiertos.value)) abiertos.value[f.id] = false })
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// ── Contexto de empresa para acciones SUPERADMIN ────────
const ensureEmpresaCtx = (flota) => {
  if (esSuperadmin.value && flota?.empresa_id) {
    const ctx = { id: flota.empresa_id, nombre: flota.empresa_nombre }
    setEmpresaActiva(ctx)
    empresaActiva.value = ctx
  }
}

// ── Permisos ────────────────────────────────────────────
const sinPermiso = (msg) =>
  window.dispatchEvent(new CustomEvent('permiso-denegado', { detail: msg }))

const irNuevaFlota = () => {
  if (!tienePermiso('flotas.crear')) return sinPermiso('No tienes permiso para crear flotas.')
  router.push(ruta('/flota/nueva'))
}
const irNuevoVehiculo = (flota) => {
  if (!tienePermiso('vehiculos.crear')) return sinPermiso('No tienes permiso para agregar vehículos.')
  ensureEmpresaCtx(flota)
  router.push(ruta(`/flota/${flota.id}/nuevo-vehiculo`))
}
const irEditarFlota = (flota) => {
  if (!tienePermiso('flotas.editar')) return sinPermiso('No tienes permiso para editar flotas.')
  ensureEmpresaCtx(flota)
  router.push(ruta(`/flota/${flota.id}/editar`))
}
const irEditarVehiculo = (vehiculoId, flota) => {
  if (!tienePermiso('vehiculos.editar')) return sinPermiso('No tienes permiso para editar vehículos.')
  ensureEmpresaCtx(flota)
  router.push(ruta(`/vehiculos/${vehiculoId}/editar`))
}

// ── Acciones con confirmación ────────────────────────────
const pedir    = (item, tipo, flotaCtx = null) => { confirm.value = { visible: true, item, tipo, flotaCtx } }
const cancelar = () => { confirm.value = { visible: false, item: null, tipo: '', flotaCtx: null } }

const permisosPorTipo = {
  'eliminar-flota':      { permiso: 'flotas.eliminar',  msg: 'No tienes permiso para eliminar flotas.'       },
  'desactivar-vehiculo': { permiso: 'vehiculos.editar',  msg: 'No tienes permiso para desactivar vehículos.' },
  'activar-vehiculo':    { permiso: 'vehiculos.editar',  msg: 'No tienes permiso para activar vehículos.'    },
}
const pedirConPermiso = (item, tipo, flotaCtx = null) => {
  const cfg = permisosPorTipo[tipo]
  if (cfg && !tienePermiso(cfg.permiso)) return sinPermiso(cfg.msg)
  pedir(item, tipo, flotaCtx)
}

const confirmar = async () => {
  if (operando.value) return
  const { item, tipo, flotaCtx } = confirm.value
  cancelar()
  operando.value = true
  // Para SUPERADMIN: establecer empresa antes de la llamada API
  const ctx = flotaCtx || item
  ensureEmpresaCtx(ctx)
  try {
    if (tipo === 'eliminar-flota') {
      const res = await apiFetchEmpresa(`/api/empresa/flotas/${item.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Error al eliminar la flota')
      toast.agregar(`Flota "${item.nombre}" eliminada.`, 'success')
    } else if (tipo === 'desactivar-vehiculo') {
      const res = await apiFetchEmpresa(`/api/empresa/vehiculos/${item.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Error al desactivar el vehículo')
      toast.agregar(`Vehículo ${item.patente} desactivado.`, 'success')
    } else if (tipo === 'activar-vehiculo') {
      const res = await apiFetchEmpresa(`/api/empresa/vehiculos/${item.id}/`, { method: 'PUT', body: { activo: true } })
      if (!res.ok) throw new Error('Error al activar el vehículo')
      toast.agregar(`Vehículo ${item.patente} activado.`, 'success')
    }
    await cargar()
  } catch (e) {
    toast.agregar(e.message, 'error')
  } finally {
    operando.value = false
  }
}

const confirmConfig = {
  'eliminar-flota':      { titulo: 'Eliminar flota',      peligroso: true,  labelOk: 'Eliminar'   },
  'desactivar-vehiculo': { titulo: 'Desactivar vehículo', peligroso: true,  labelOk: 'Desactivar' },
  'activar-vehiculo':    { titulo: 'Activar vehículo',    peligroso: false, labelOk: 'Activar'    },
}
const mensajeConfirm = () => {
  const { item, tipo } = confirm.value
  if (tipo === 'eliminar-flota')      return `¿Eliminar la flota "${item?.nombre}"? Se eliminarán también sus vehículos.`
  if (tipo === 'desactivar-vehiculo') return `¿Desactivar el vehículo ${item?.patente}?`
  if (tipo === 'activar-vehiculo')    return `¿Activar el vehículo ${item?.patente}?`
  return ''
}

onMounted(async () => {
  await cargarEmpresas()
  await cargar()
})
</script>

<template>

  <ConfirmModal
    v-if="confirm.visible"
    :titulo="confirmConfig[confirm.tipo]?.titulo"
    :mensaje="mensajeConfirm()"
    :label-ok="confirmConfig[confirm.tipo]?.labelOk"
    :peligroso="confirmConfig[confirm.tipo]?.peligroso"
    @confirmar="confirmar"
    @cancelar="cancelar"
  />

  <div class="page">

    <!-- ── Encabezado ── -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Flota</h1>
        <p class="page-subtitle">
          {{ esSuperadmin ? 'Gestión global de flotas y vehículos' : 'Gestiona las flotas y vehículos de tu empresa' }}
        </p>
      </div>

      <div class="header-actions">

        <!-- Selector empresa (SUPERADMIN — actúa como filtro) -->
        <div v-if="esSuperadmin" class="selector-wrap">
          <button
            class="selector-btn"
            :class="{ 'sin-sel': !empresaActiva }"
            @click="mostrarDropdown = !mostrarDropdown"
          >
            <span class="selector-icono">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
              </svg>
            </span>
            <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Todas las empresas' }}</span>
            <svg class="selector-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <div v-if="mostrarDropdown" class="selector-dropdown">
            <div class="dropdown-search">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <input v-model="busqueda" placeholder="Buscar empresa..." class="dropdown-input" autofocus/>
            </div>

            <button v-if="empresaActiva" class="dropdown-option dropdown-todos" @click="limpiarEmpresa">
              <span class="option-avatar option-todos">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                </svg>
              </span>
              <span class="option-nombre">Todas las empresas</span>
            </button>

            <div v-if="cargandoEmpresas" class="dropdown-empty">Cargando...</div>
            <div v-else-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</div>
            <button
              v-for="emp in empresasFiltradas"
              :key="emp.id"
              class="dropdown-option"
              :class="{ selected: empresaActiva?.id === emp.id }"
              @click="seleccionarEmpresa(emp)"
            >
              <span class="option-avatar">{{ emp.nombre[0].toUpperCase() }}</span>
              <span class="option-nombre">{{ emp.nombre }}</span>
              <svg v-if="empresaActiva?.id === emp.id" class="option-check" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
            </button>
          </div>

          <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
        </div>

        <button
          class="btn-primary"
          @click="irNuevaFlota"
          :disabled="(esSuperadmin && !empresaActiva) || operando"
          :title="esSuperadmin && !empresaActiva ? 'Selecciona una empresa para crear una flota' : ''"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Nueva Flota
        </button>
      </div>
    </div>

    <!-- Estados vacíos / error -->
    <div v-if="sinEmpresa" class="sin-empresa">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
      </svg>
      <p>No tienes una empresa asignada.</p>
    </div>

    <div v-else-if="error" class="alert-error">{{ error }}</div>

    <div v-else-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando flotas...</span>
    </div>

    <div v-else-if="flotas.length === 0" class="empty">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
      </svg>
      <p>{{ empresaActiva ? `No hay flotas para ${empresaActiva.nombre}.` : 'No hay flotas creadas.' }}</p>
      <button v-if="!esSuperadmin || empresaActiva" class="btn-primary" @click="irNuevaFlota">Crear primera flota</button>
    </div>

    <!-- ── Tabla de flotas ── -->
    <div v-else class="tabla-wrap">
      <table class="tabla-flotas">
        <thead>
          <tr>
            <th class="th-expand"></th>
            <th>Flota</th>
            <th v-if="esSuperadmin">Empresa</th>
            <th v-if="esSuperadmin">Administrador</th>
            <th>Vehículos</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="flota in flotas" :key="flota.id">

            <!-- Fila principal de la flota -->
            <tr class="fila-flota" @click="abiertos[flota.id] = !abiertos[flota.id]">
              <td class="td-expand">
                <span class="icon-toggle" :class="{ open: abiertos[flota.id] }">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                  </svg>
                </span>
              </td>

              <td class="td-nombre">{{ flota.nombre }}</td>

              <td v-if="esSuperadmin" class="td-empresa">{{ flota.empresa_nombre }}</td>

              <td v-if="esSuperadmin" class="td-admin">
                <div v-if="flota.admin_nombre || flota.admin_email" class="admin-info">
                  <span class="admin-nombre">{{ flota.admin_nombre || '—' }}</span>
                  <span class="admin-email">{{ flota.admin_email }}</span>
                </div>
                <span v-else class="sin-admin">Sin administrador</span>
              </td>

              <td>
                <span class="badge-count">{{ flota.total_vehiculos }} veh.</span>
              </td>

              <td class="td-acciones" @click.stop>
                <button class="btn-agregar" @click="irNuevoVehiculo(flota)" title="Agregar vehículo">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                  <span>Agregar</span>
                </button>
                <button class="btn-accion btn-editar-flota" @click="irEditarFlota(flota)" title="Editar flota">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button class="btn-accion btn-eliminar-flota" @click="pedirConPermiso(flota, 'eliminar-flota')" title="Eliminar flota">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </td>
            </tr>

            <!-- Fila expandible con la sub-tabla de vehículos -->
            <tr v-if="abiertos[flota.id]" class="fila-vehiculos">
              <td :colspan="colspan" class="td-sub">
                <div v-if="!flota.vehiculos?.length" class="vehiculos-empty">
                  Sin vehículos —
                  <button class="link-btn" @click="irNuevoVehiculo(flota)">agregar uno</button>
                </div>
                <table v-else class="tabla-vehiculos">
                  <thead>
                    <tr>
                      <th>Patente</th>
                      <th>Marca / Modelo</th>
                      <th>Año</th>
                      <th>Combustible</th>
                      <th>KM</th>
                      <th>Estado</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="v in flota.vehiculos" :key="v.id" :class="{ inactivo: !v.activo }">
                      <td class="td-patente">{{ v.patente }}</td>
                      <td>{{ [v.marca, v.modelo].filter(Boolean).join(' ') || '—' }}</td>
                      <td>{{ v.anio || '—' }}</td>
                      <td>{{ COMBUSTIBLE_LABEL[v.tipo_combustible] || v.tipo_combustible }}</td>
                      <td>{{ v.km_actuales.toLocaleString('es-CL') }} km</td>
                      <td>
                        <span :class="['badge', v.activo ? 'badge-activo' : 'badge-inactivo']">
                          {{ v.activo ? 'Activo' : 'Inactivo' }}
                        </span>
                      </td>
                      <td class="td-acciones-v">
                        <button class="btn-accion btn-editar" @click="irEditarVehiculo(v.id, flota)" title="Editar">
                          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                          </svg>
                        </button>
                        <button v-if="v.activo" class="btn-accion btn-desactivar"
                          @click="pedirConPermiso(v, 'desactivar-vehiculo', flota)" title="Desactivar">
                          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                          </svg>
                        </button>
                        <button v-else class="btn-accion btn-activar"
                          @click="pedirConPermiso(v, 'activar-vehiculo', flota)" title="Activar">
                          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                          </svg>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>

          </template>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 1.75rem; gap: 1rem;
}
.page-title    { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }

/* ── Selector empresa ── */
.selector-wrap { position: relative; }
.selector-btn {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.875rem;
  background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px;
  font-size: 0.875rem; font-weight: 500; color: #374151;
  cursor: pointer; font-family: inherit; white-space: nowrap;
  transition: border-color 0.15s; max-width: 240px;
}
.selector-btn:hover { border-color: #7C3AED; }
.selector-btn.sin-sel { border-style: dashed; color: #9CA3AF; }
.selector-icono svg { width: 16px; height: 16px; color: #6B7280; flex-shrink: 0; }
.selector-texto { flex: 1; overflow: hidden; text-overflow: ellipsis; text-align: left; }
.selector-chevron { width: 14px; height: 14px; color: #9CA3AF; flex-shrink: 0; }

.selector-dropdown {
  position: absolute; top: calc(100% + 6px); right: 0;
  width: 280px; background: #fff;
  border: 1px solid #E5E7EB; border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  overflow: hidden; z-index: 200;
  max-height: 320px; display: flex; flex-direction: column; overflow-y: auto;
}
.dropdown-search {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; flex-shrink: 0; }
.dropdown-input { flex: 1; border: none; outline: none; font-size: 0.875rem; color: #111827; font-family: inherit; background: transparent; }
.dropdown-empty { padding: 1rem; font-size: 0.8125rem; color: #9CA3AF; text-align: center; }
.dropdown-option {
  display: flex; align-items: center; gap: 0.625rem;
  width: 100%; padding: 0.625rem 0.875rem;
  background: none; border: none; cursor: pointer;
  text-align: left; font-family: inherit; transition: background 0.12s;
}
.dropdown-option:hover   { background: #F5F3FF; }
.dropdown-option.selected { background: #EEF2FF; }
.dropdown-todos { border-bottom: 1px solid #F3F4F6; }
.option-avatar {
  flex-shrink: 0; width: 28px; height: 28px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; color: #fff;
}
.option-avatar.option-todos { background: #F3F4F6; }
.option-avatar.option-todos svg { width: 14px; height: 14px; color: #6B7280; }
.option-nombre { flex: 1; font-size: 0.875rem; font-weight: 500; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.option-check { width: 16px; height: 16px; color: #4F46E5; flex-shrink: 0; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 199; }

/* ── Botón ── */
.btn-primary {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff;
  font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px;
  cursor: pointer; transition: opacity 0.2s, transform 0.1s; font-family: inherit; white-space: nowrap;
}
.btn-primary:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-primary svg { width: 16px; height: 16px; }

/* ── Estados ── */
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; }
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
.sin-empresa { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 5rem 2rem; color: #9CA3AF; text-align: center; }
.sin-empresa svg { width: 56px; height: 56px; opacity: 0.35; }
.sin-empresa p { font-size: 1rem; margin: 0; color: #6B7280; }
.empty { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 4rem 2rem; color: #9CA3AF; text-align: center; }
.empty svg { width: 56px; height: 56px; opacity: 0.4; }
.empty p { font-size: 1rem; margin: 0; }

/* ── Tabla principal de flotas ── */
.tabla-wrap {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.tabla-flotas {
  width: 100%;
  border-collapse: collapse;
}

.tabla-flotas thead tr {
  background: #F9FAFB;
  border-bottom: 1px solid #E5E7EB;
}
.tabla-flotas th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}
.th-expand { width: 40px; }

.fila-flota {
  cursor: pointer;
  border-bottom: 1px solid #F3F4F6;
  transition: background 0.12s;
}
.fila-flota:hover { background: #F9FAFB; }
.fila-flota:last-of-type { border-bottom: none; }

.fila-flota td {
  padding: 0.85rem 1rem;
  font-size: 0.875rem;
  color: #374151;
  vertical-align: middle;
}

.td-expand { width: 40px; }
.icon-toggle {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  color: #9CA3AF;
  transition: transform 0.2s, color 0.2s;
}
.icon-toggle svg { width: 14px; height: 14px; }
.icon-toggle.open { transform: rotate(90deg); color: #4F46E5; }

.td-nombre { font-weight: 700; color: #111827; }

.td-empresa { color: #374151; font-size: 0.875rem; }

.td-admin .admin-info { display: flex; flex-direction: column; gap: 1px; }
.admin-nombre { font-size: 0.875rem; font-weight: 500; color: #111827; }
.admin-email  { font-size: 0.75rem; color: #9CA3AF; }
.sin-admin    { font-size: 0.8125rem; color: #D1D5DB; font-style: italic; }

.badge-count { background: #EEF2FF; color: #4338CA; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.625rem; border-radius: 999px; white-space: nowrap; }

.td-acciones { display: flex; align-items: center; gap: 0.5rem; }

/* ── Sub-tabla de vehículos ── */
.fila-vehiculos td { padding: 0; }
.td-sub { background: #F8FAFC; border-top: 1px solid #EEF2FF; }

.vehiculos-empty { padding: 1rem 1.5rem; font-size: 0.875rem; color: #9CA3AF; }
.link-btn { background: none; border: none; color: #4F46E5; font-weight: 600; cursor: pointer; font-family: inherit; font-size: inherit; padding: 0; }
.link-btn:hover { text-decoration: underline; }

.tabla-vehiculos { width: 100%; border-collapse: collapse; }
.tabla-vehiculos th {
  padding: 0.55rem 1rem;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: #F1F5F9;
  border-bottom: 1px solid #E5E7EB;
}
.tabla-vehiculos td { padding: 0.7rem 1rem; font-size: 0.8125rem; color: #374151; border-bottom: 1px solid #F1F5F9; }
.tabla-vehiculos tbody tr:last-child td { border-bottom: none; }
.tabla-vehiculos tbody tr.inactivo td { opacity: 0.45; }

.td-patente    { font-weight: 700; color: #111827; font-family: 'Courier New', monospace; }
.td-acciones-v { display: flex; gap: 0.4rem; align-items: center; }

/* ── Botones de acción ── */
.btn-agregar {
  display: flex; align-items: center; gap: 0.3rem;
  padding: 0.35rem 0.75rem; border: 1.5px solid #4F46E5; border-radius: 8px;
  background: #EEF2FF; color: #4F46E5; font-size: 0.8rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: background 0.15s; white-space: nowrap;
}
.btn-agregar:hover { background: #E0E7FF; }
.btn-agregar svg { width: 13px; height: 13px; }

.btn-accion {
  width: 30px; height: 30px; border: 1px solid #E5E7EB; border-radius: 7px;
  background: #fff; display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: border-color 0.15s, background 0.15s; flex-shrink: 0;
}
.btn-accion svg { width: 14px; height: 14px; }
.btn-editar-flota        { color: #6B7280; }
.btn-editar-flota:hover  { border-color: #6B7280; background: #F9FAFB; }
.btn-eliminar-flota      { color: #DC2626; }
.btn-eliminar-flota:hover { border-color: #DC2626; background: #FEF2F2; }
.btn-editar              { color: #4F46E5; }
.btn-editar:hover        { border-color: #4F46E5; background: #EEF2FF; }
.btn-desactivar          { color: #DC2626; }
.btn-desactivar:hover    { border-color: #DC2626; background: #FEF2F2; }
.btn-activar             { color: #059669; }
.btn-activar:hover       { border-color: #059669; background: #ECFDF5; }

.badge { display: inline-flex; align-items: center; padding: 0.2rem 0.625rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-activo   { background: #ECFDF5; color: #059669; }
.badge-inactivo { background: #F3F4F6; color: #9CA3AF; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
