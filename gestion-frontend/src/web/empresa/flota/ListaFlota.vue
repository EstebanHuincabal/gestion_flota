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

// Columnas de módulos opcionales: solo se muestran si el plan incluye el permiso.
const verGps         = computed(() => tienePermiso('gps.ver'))
const verConductores = computed(() => tienePermiso('conductores.ver'))

// ── Datos ───────────────────────────────────────────────
const vehiculos    = ref([])
const conductores  = ref([])
const cargando     = ref(true)
const operando     = ref(false)
const error        = ref('')
const sinEmpresa   = ref(false)
const toast        = useToast()
const confirm      = ref({ visible: false, item: null, tipo: '' })

const COMBUSTIBLE_LABEL = { bencina: 'Bencina', diesel: 'Diésel', electrico: 'Eléctrico', hibrido: 'Híbrido' }

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

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  cargar()
}

const limpiarEmpresa = () => {
  setEmpresaActiva(null)
  empresaActiva.value   = null
  mostrarDropdown.value = false
  vehiculos.value = []
}

// ── Carga ───────────────────────────────────────────────
const cargar = async () => {
  // SUPERADMIN necesita una empresa seleccionada para listar sus vehículos.
  if (esSuperadmin.value && !empresaActiva.value) {
    vehiculos.value = []
    cargando.value  = false
    return
  }
  cargando.value   = true
  error.value      = ''
  sinEmpresa.value = false
  try {
    const [rV, rC] = await Promise.all([
      apiFetchEmpresa('/api/empresa/vehiculos/'),
      apiFetchEmpresa('/api/empresa/conductores/'),
    ])
    if (rV.status === 400) {
      const d = await rV.json()
      if (d.error === 'sin_empresa') { sinEmpresa.value = true; return }
    }
    if (!rV.ok) throw new Error('Error al cargar los vehículos')
    vehiculos.value   = await rV.json()
    conductores.value = rC.ok ? await rC.json() : []
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

// ── Permisos ────────────────────────────────────────────
const sinPermiso = (msg) =>
  window.dispatchEvent(new CustomEvent('permiso-denegado', { detail: msg }))

const irNuevoVehiculo = () => {
  if (!tienePermiso('vehiculos.crear')) return sinPermiso('No tienes permiso para agregar vehículos.')
  router.push(ruta('/vehiculos/nuevo'))
}
const irEditarVehiculo = (vehiculoId) => {
  if (!tienePermiso('vehiculos.editar')) return sinPermiso('No tienes permiso para editar vehículos.')
  router.push(ruta(`/vehiculos/${vehiculoId}/editar`))
}

// ── Asignar conductor ────────────────────────────────────
const modalAsignar  = ref(false)
const vehiculoSel   = ref(null)
const conductorSel  = ref(null)
const guardandoAsig = ref(false)

// Todos los conductores activos; los que ya tienen vehículo se marcan en el
// dropdown. Al elegir uno ocupado, se hace un traspaso (con aviso previo).
const conductoresDisponibles = computed(() =>
  conductores.value.filter(c => c.is_active)
)

// Conductor seleccionado (objeto) y detección de traspaso.
const conductorSelObj = computed(() =>
  conductores.value.find(c => c.id === conductorSel.value) || null
)
// Hay traspaso si el conductor elegido ya maneja OTRO vehículo distinto a este.
const traspasoConductor = computed(() => {
  const c = conductorSelObj.value
  if (!c?.vehiculo) return null
  if (c.vehiculo.id === vehiculoSel.value?.id) return null
  return c.vehiculo   // { id, patente, ... }
})

const abrirAsignar = (v) => {
  if (!tienePermiso('conductores.asignar')) return sinPermiso('No tienes permiso para asignar conductores.')
  vehiculoSel.value  = v
  conductorSel.value = v.conductor_asignado?.id ?? null
  modalAsignar.value = true
}

const guardarAsignacion = async () => {
  if (guardandoAsig.value) return
  guardandoAsig.value = true
  try {
    // Sin selección → desasignar el conductor actual del vehículo (si lo hay).
    if (!conductorSel.value) {
      const actualId = vehiculoSel.value?.conductor_asignado?.id
      if (actualId) {
        const res = await apiFetchEmpresa(`/api/empresa/conductores/${actualId}/desasignar/`, { method: 'POST' })
        if (!res.ok) { const d = await res.json().catch(() => ({})); toast.agregar(d.error || 'Error al desasignar', 'error'); return }
        toast.agregar('Conductor desasignado.', 'success')
      }
    } else {
      const res = await apiFetchEmpresa(`/api/empresa/conductores/${conductorSel.value}/asignar/`, {
        method: 'POST',
        body:   { vehiculo_id: vehiculoSel.value.id },
      })
      if (!res.ok) { const d = await res.json().catch(() => ({})); toast.agregar(d.error || 'Error al asignar conductor', 'error'); return }
      toast.agregar(traspasoConductor.value ? 'Vehículo traspasado correctamente.' : 'Conductor asignado correctamente.', 'success')
    }
    modalAsignar.value = false
    await cargar()
  } catch {
    toast.agregar('Error de conexión.', 'error')
  } finally {
    guardandoAsig.value = false
  }
}

// ── Activar / desactivar vehículo (con confirmación) ─────
const permisosPorTipo = {
  'desactivar-vehiculo': { permiso: 'vehiculos.editar', msg: 'No tienes permiso para desactivar vehículos.' },
  'activar-vehiculo':    { permiso: 'vehiculos.editar', msg: 'No tienes permiso para activar vehículos.'    },
}
const pedirConPermiso = (item, tipo) => {
  const cfg = permisosPorTipo[tipo]
  if (cfg && !tienePermiso(cfg.permiso)) return sinPermiso(cfg.msg)
  confirm.value = { visible: true, item, tipo }
}
const cancelar = () => { confirm.value = { visible: false, item: null, tipo: '' } }

const confirmar = async () => {
  if (operando.value) return
  const { item, tipo } = confirm.value
  cancelar()
  operando.value = true
  try {
    if (tipo === 'desactivar-vehiculo') {
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
  'desactivar-vehiculo': { titulo: 'Desactivar vehículo', peligroso: true,  labelOk: 'Desactivar' },
  'activar-vehiculo':    { titulo: 'Activar vehículo',    peligroso: false, labelOk: 'Activar'    },
}
const mensajeConfirm = () => {
  const { item, tipo } = confirm.value
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
          {{ esSuperadmin ? 'Vehículos por empresa' : 'Vehículos de tu empresa y su conductor asignado' }}
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
            <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa' }}</span>
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
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </span>
              <span class="option-nombre">Quitar selección</span>
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
          @click="irNuevoVehiculo"
          :disabled="(esSuperadmin && !empresaActiva) || operando"
          :title="esSuperadmin && !empresaActiva ? 'Selecciona una empresa para agregar un vehículo' : ''"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Nuevo vehículo
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

    <div v-else-if="esSuperadmin && !empresaActiva" class="empty">
      <p>Selecciona una empresa para ver sus vehículos.</p>
    </div>

    <div v-else-if="error" class="alert-error">{{ error }}</div>

    <div v-else-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando vehículos...</span>
    </div>

    <div v-else-if="vehiculos.length === 0" class="empty">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
      </svg>
      <p>No hay vehículos registrados.</p>
      <button class="btn-primary" @click="irNuevoVehiculo">Agregar primer vehículo</button>
    </div>

    <!-- ── Tabla de vehículos ── -->
    <div v-else class="tabla-wrap">
      <table class="tabla-vehiculos">
        <thead>
          <tr>
            <th>Patente</th>
            <th>Vehículo</th>
            <th>Año</th>
            <th>Combustible</th>
            <th>Estado</th>
            <th v-if="verConductores">Conductor</th>
            <th v-if="verGps">GPS</th>
            <th class="th-acciones">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in vehiculos" :key="v.id" :class="{ inactivo: !v.activo }">
            <td class="td-patente">
              <div class="patente-cell">
                <div class="veh-thumb">
                  <img v-if="v.foto_url" :src="v.foto_url" :alt="v.patente"/>
                  <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
                  </svg>
                </div>
                <span>{{ v.patente }}</span>
              </div>
            </td>
            <td>
              <span v-if="v.marca || v.modelo">{{ [v.marca, v.modelo].filter(Boolean).join(' ') }}</span>
              <span v-else class="texto-tenue">—</span>
            </td>
            <td>{{ v.anio || '—' }}</td>
            <td>{{ COMBUSTIBLE_LABEL[v.tipo_combustible] || v.tipo_combustible }}</td>
            <td>
              <span :class="['badge', v.activo ? 'badge-ok' : 'badge-off']">
                {{ v.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td v-if="verConductores">
              <span v-if="v.conductor_asignado" class="conductor-chip">
                {{ v.conductor_asignado.nombre }}
              </span>
              <span v-else class="texto-tenue">Sin conductor</span>
            </td>
            <td v-if="verGps">
              <span v-if="v.gps_asociado" class="gps-chip" :title="`${v.gps_asociado.modelo} · ${v.gps_asociado.imei}`">
                {{ v.gps_asociado.modelo }}
                <span class="gps-imei">{{ v.gps_asociado.imei }}</span>
              </span>
              <span v-else class="texto-tenue">Sin GPS</span>
            </td>
            <td class="td-acciones">
              <button v-if="verConductores" class="btn-accion" title="Asignar conductor" @click="abrirAsignar(v)" :disabled="!v.activo">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                </svg>
              </button>
              <button class="btn-accion" title="Editar" @click="irEditarVehiculo(v.id)">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </button>
              <button v-if="v.activo" class="btn-accion btn-peligro" title="Desactivar" @click="pedirConPermiso(v, 'desactivar-vehiculo')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
              <button v-else class="btn-accion btn-ok" title="Activar" @click="pedirConPermiso(v, 'activar-vehiculo')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Modal asignar conductor ── -->
    <div v-if="modalAsignar" class="modal-overlay" @click.self="modalAsignar = false">
      <div class="modal-card">
        <h2 class="modal-title">Asignar conductor</h2>
        <p class="modal-sub">Vehículo <strong>{{ vehiculoSel?.patente }}</strong></p>

        <label class="label">Conductor</label>
        <select v-model="conductorSel" class="input select">
          <option :value="null">— Sin conductor —</option>
          <option v-for="c in conductoresDisponibles" :key="c.id" :value="c.id">
            {{ c.nombre }}{{ c.vehiculo && c.vehiculo.id !== vehiculoSel?.id ? ` — maneja ${c.vehiculo.patente}` : '' }}
          </option>
        </select>
        <p v-if="!conductoresDisponibles.length" class="modal-hint">
          No hay conductores activos en esta empresa.
        </p>

        <!-- Aviso de traspaso: el conductor elegido ya maneja otro vehículo -->
        <div v-if="traspasoConductor" class="aviso-traspaso">
          <strong>{{ conductorSelObj.nombre }}</strong> maneja <strong>{{ traspasoConductor.patente }}</strong>.
          Al continuar, se le reasignará a <strong>{{ vehiculoSel?.patente }}</strong> y
          {{ traspasoConductor.patente }} quedará sin conductor.
        </div>

        <div class="modal-actions">
          <button class="btn-secondary" @click="modalAsignar = false" :disabled="guardandoAsig">Cancelar</button>
          <button class="btn-primary" @click="guardarAsignacion" :disabled="guardandoAsig">
            {{ guardandoAsig ? 'Guardando...' : (traspasoConductor ? 'Traspasar' : 'Guardar') }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.75rem; flex-wrap: wrap; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.1rem; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-primary svg { width: 16px; height: 16px; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Selector empresa */
.selector-wrap { position: relative; }
.selector-btn { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.55rem 0.875rem; background: #fff; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; font-family: inherit; max-width: 260px; }
.selector-btn.sin-sel { border-color: #FCD34D; background: #FFFBEB; color: #B45309; }
.selector-icono svg, .selector-chevron { width: 16px; height: 16px; flex-shrink: 0; }
.selector-texto { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.selector-dropdown { position: absolute; top: calc(100% + 6px); right: 0; width: 300px; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); z-index: 30; padding: 0.5rem; max-height: 360px; overflow-y: auto; }
.dropdown-search { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.6rem; border: 1px solid #E5E7EB; border-radius: 8px; margin-bottom: 0.5rem; }
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; }
.dropdown-input { border: none; outline: none; font-size: 0.8125rem; flex: 1; font-family: inherit; }
.dropdown-option { display: flex; align-items: center; gap: 0.6rem; width: 100%; padding: 0.5rem 0.6rem; border: none; background: none; cursor: pointer; border-radius: 8px; font-family: inherit; text-align: left; }
.dropdown-option:hover { background: #F5F3FF; }
.dropdown-option.selected { background: #EDE9FE; }
.option-avatar { width: 28px; height: 28px; border-radius: 7px; background: linear-gradient(135deg,#6366F1,#8B5CF6); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8125rem; flex-shrink: 0; }
.option-todos { background: #E5E7EB; color: #6B7280; }
.option-todos svg { width: 15px; height: 15px; }
.option-nombre { flex: 1; font-size: 0.8125rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.option-check { width: 16px; height: 16px; color: #7C3AED; }
.dropdown-empty { padding: 0.75rem; text-align: center; color: #9CA3AF; font-size: 0.8125rem; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 20; }

/* Tabla */
.tabla-wrap { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.tabla-vehiculos { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla-vehiculos thead th { text-align: left; padding: 0.75rem 1rem; font-weight: 600; color: #6B7280; font-size: 0.8125rem; background: #F9FAFB; border-bottom: 1px solid #E5E7EB; white-space: nowrap; }
.tabla-vehiculos tbody td { padding: 0.75rem 1rem; border-bottom: 1px solid #F3F4F6; color: #374151; }
.tabla-vehiculos tbody tr:last-child td { border-bottom: none; }
.tabla-vehiculos tbody tr.inactivo { opacity: 0.55; }
.td-patente { font-weight: 700; color: #1E1B4B; font-family: ui-monospace, monospace; }
.patente-cell { display: flex; align-items: center; gap: 0.625rem; }
.veh-thumb {
  flex-shrink: 0;
  width: 44px; height: 32px;
  border-radius: 7px;
  background: #F3F4F6;
  border: 1px solid #E5E7EB;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.veh-thumb img { width: 100%; height: 100%; object-fit: cover; }
.veh-thumb svg { width: 18px; height: 18px; color: #C7CDD6; }
.texto-tenue { color: #9CA3AF; }
.th-acciones, .td-acciones { text-align: right; white-space: nowrap; }

.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-ok  { background: #DCFCE7; color: #15803D; }
.badge-off { background: #FEE2E2; color: #B91C1C; }
.conductor-chip { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8125rem; font-weight: 500; background: #EDE9FE; color: #6D28D9; }
.gps-chip { display: inline-flex; align-items: baseline; gap: 0.35rem; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; background: #E0F2FE; color: #0369A1; }
.gps-imei { font-family: ui-monospace, monospace; font-size: 0.6875rem; font-weight: 400; color: #0C4A6E; opacity: 0.7; }

.btn-accion { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: 1px solid #E5E7EB; background: #fff; border-radius: 8px; cursor: pointer; color: #6B7280; margin-left: 0.35rem; transition: background 0.15s, color 0.15s, border-color 0.15s; }
.btn-accion svg { width: 16px; height: 16px; }
.btn-accion:hover { background: #F5F3FF; color: #6D28D9; border-color: #DDD6FE; }
.btn-accion:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-accion.btn-peligro:hover { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }
.btn-accion.btn-ok:hover { background: #ECFDF5; color: #16A34A; border-color: #BBF7D0; }

/* Estados */
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2.5rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; }
.empty, .sin-empresa { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; padding: 3rem 1rem; color: #9CA3AF; text-align: center; }
.empty svg, .sin-empresa svg { width: 48px; height: 48px; color: #D1D5DB; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; padding: 1rem; z-index: 60; }
.modal-card { background: #fff; border-radius: 16px; padding: 1.75rem; width: 100%; max-width: 420px; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.modal-sub { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.25rem; }
.label { display: block; font-size: 0.875rem; font-weight: 600; color: #374151; margin-bottom: 0.375rem; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; width: 100%; font-family: inherit; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.select { cursor: pointer; }
.modal-hint { font-size: 0.8125rem; color: #9CA3AF; margin: 0.5rem 0 0; }
.aviso-traspaso { margin-top: 0.75rem; padding: 0.65rem 0.85rem; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; font-size: 0.8125rem; color: #92400E; line-height: 1.4; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .tabla-wrap { overflow-x: auto; }
  .tabla-vehiculos { min-width: 760px; }
}
</style>
