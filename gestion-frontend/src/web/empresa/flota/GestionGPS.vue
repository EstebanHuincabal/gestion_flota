<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch, safeJsonParse } from '../../../utils/api.js'
import { tienePermiso } from '../../../utils/permisos.js'
import { getEmpresaActiva, useEmpresaNav } from '../../../utils/empresaActiva.js'
import ConfirmModal from '../../../components/ConfirmModal.vue'
import SelectorEmpresa from '../../../components/SelectorEmpresa.vue'

const { ruta } = useEmpresaNav()

// ── Estado general ────────────────────────────────────────────────────────────
const tab        = ref('dispositivos')   // 'dispositivos' | 'configuracion'
const cargando   = ref(true)
const dispositivos = ref([])
const vehiculos    = ref([])

const puedeGestionar = computed(() => tienePermiso('gps.gestionar'))

// SUPERADMIN debe elegir una empresa antes de operar (sistema unificado).
const esSuperadmin = computed(() => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  return usuario.rol === 'SUPERADMIN'
})
const empresaActiva = ref(getEmpresaActiva())
const sinEmpresa = computed(() => esSuperadmin.value && !empresaActiva.value)

const MODELOS = [
  { value: 'emulador',         label: 'Emulador NMEA' },
  { value: 'teltonika_fmb920', label: 'Teltonika FMB920' },
  { value: 'teltonika_fmc125', label: 'Teltonika FMC125' },
  { value: 'queclink_gl300',   label: 'Queclink GL300' },
  { value: 'coban_tk103',      label: 'Coban TK103' },
  { value: 'otro',             label: 'Otro' },
]

function toast(tipo, mensaje) {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { tipo, mensaje } }))
}

// ── Carga inicial ─────────────────────────────────────────────────────────────
async function cargarDispositivos() {
  try {
    const res = await apiFetch('/api/empresa/gps/dispositivos/')
    if (res.ok) {
      const data = await res.json()
      dispositivos.value = data.dispositivos || []
    }
  } catch { /* manejado por apiFetch */ }
}

async function cargarVehiculos() {
  try {
    const res = await apiFetch('/api/empresa/vehiculos/')
    if (res.ok) vehiculos.value = await res.json()
  } catch { /* noop */ }
}

async function cargarConfiguracion() {
  try {
    const res = await apiFetch('/api/empresa/gps/configuracion/')
    if (res.ok) {
      const data = await res.json()
      config.value = {
        servidor_ip:     data.servidor_ip || '',
        servidor_puerto: data.servidor_puerto ?? 5000,
        protocolo:       data.protocolo || 'tcp',
      }
    }
  } catch { /* noop */ }
}

async function cargarTodo() {
  cargando.value = true
  await Promise.all([cargarDispositivos(), cargarVehiculos(), cargarConfiguracion()])
  cargando.value = false
}

function onCambioEmpresa(empresa) {
  empresaActiva.value = empresa
  dispositivos.value = []
  vehiculos.value    = []
  if (empresa) cargarTodo()
}

onMounted(async () => {
  // Para SUPERADMIN sin empresa seleccionada, esperamos a que elija una.
  if (sinEmpresa.value) {
    cargando.value = false
    return
  }
  await cargarTodo()
})

// ── Modal alta / edición ──────────────────────────────────────────────────────
const modalForm   = ref(false)
const editandoId  = ref(null)
const form        = ref({ imei: '', modelo: 'emulador', activo: true })
const guardando   = ref(false)

function abrirCrear() {
  editandoId.value = null
  form.value = { imei: '', modelo: 'emulador', activo: true }
  modalForm.value = true
}

function abrirEditar(d) {
  editandoId.value = d.id
  form.value = { imei: d.imei, modelo: d.modelo, activo: d.activo }
  modalForm.value = true
}

async function guardar() {
  const imei = (form.value.imei || '').trim()
  if (imei.length < 10 || imei.length > 20) {
    toast('error', 'El IMEI debe tener entre 10 y 20 caracteres.')
    return
  }
  guardando.value = true
  try {
    const url    = editandoId.value
      ? `/api/empresa/gps/dispositivos/${editandoId.value}/`
      : '/api/empresa/gps/dispositivos/'
    const method = editandoId.value ? 'PUT' : 'POST'
    const res = await apiFetch(url, { method, body: { ...form.value, imei } })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo guardar el dispositivo.')
      guardando.value = false
      return
    }
    const data = await res.json().catch(() => ({}))
    const eraNuevo = !editandoId.value
    toast('exito', editandoId.value ? 'Dispositivo actualizado.' : 'Dispositivo registrado.')
    modalForm.value = false
    await cargarDispositivos()
    // Al crear, el backend devuelve la clave de ingesta una sola vez.
    if (eraNuevo && data.api_key) mostrarClave(imei, data.api_key)
  } catch {
    toast('error', 'Error de conexión al guardar.')
  } finally {
    guardando.value = false
  }
}

// ── Clave de ingesta del dispositivo ──────────────────────────────────────────
const claveModal = ref(false)
const claveImei  = ref('')
const claveValor = ref('')
const claveCopiada = ref(false)

function mostrarClave(imei, valor) {
  claveImei.value  = imei
  claveValor.value = valor
  claveCopiada.value = false
  claveModal.value = true
}

async function copiarClave() {
  try {
    await navigator.clipboard.writeText(claveValor.value)
    claveCopiada.value = true
    setTimeout(() => { claveCopiada.value = false }, 2000)
  } catch {
    toast('error', 'No se pudo copiar. Selecciona y copia manualmente.')
  }
}

async function regenerarClave(d) {
  try {
    const res = await apiFetch(`/api/empresa/gps/dispositivos/${d.id}/regenerar-clave/`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo regenerar la clave.')
      return
    }
    const data = await res.json()
    await cargarDispositivos()
    mostrarClave(d.imei, data.api_key)
  } catch {
    toast('error', 'Error de conexión al regenerar la clave.')
  }
}

// ── Activar / Desactivar ───────────────────────────────────────────────────────
// Los dispositivos no se eliminan; se desactivan (reversible). Un dispositivo
// inactivo deja de aceptar posiciones (la ingesta lo rechaza) pero conserva su
// historial y asignación.
const confirmDesactivar = ref(false)
const objetivo          = ref(null)

function pedirDesactivar(d) {
  objetivo.value = d
  confirmDesactivar.value = true
}

async function setActivo(d, activo) {
  try {
    const res = await apiFetch(`/api/empresa/gps/dispositivos/${d.id}/`, {
      method: 'PUT',
      body: { activo },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo actualizar el dispositivo.')
      return
    }
    toast('exito', activo ? 'Dispositivo activado.' : 'Dispositivo desactivado.')
    await cargarDispositivos()
  } catch {
    toast('error', 'Error de conexión.')
  }
}

async function desactivar() {
  const d = objetivo.value
  confirmDesactivar.value = false
  if (d) await setActivo(d, false)
}

// ── Asignar vehículo ──────────────────────────────────────────────────────────
const modalAsignar = ref(false)
const asignarId    = ref(null)
const vehiculoSel  = ref('')

const vehiculosLibres = computed(() => {
  // Vehículos sin dispositivo_gps asignado. La lista de vehículos no trae ese
  // dato directo, así que excluimos los que ya aparecen asignados a un dispositivo.
  const ocupados = new Set(
    dispositivos.value.filter(d => d.vehiculo_id).map(d => d.vehiculo_id)
  )
  return vehiculos.value.filter(v => !ocupados.has(v.id))
})

function abrirAsignar(d) {
  asignarId.value = d.id
  vehiculoSel.value = ''
  modalAsignar.value = true
}

async function asignar() {
  if (!vehiculoSel.value) {
    toast('error', 'Selecciona un vehículo.')
    return
  }
  try {
    const res = await apiFetch(`/api/empresa/gps/dispositivos/${asignarId.value}/asignar/`, {
      method: 'POST',
      body: { vehiculo_id: vehiculoSel.value },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo asignar.')
      return
    }
    const data = await res.json()
    toast('exito', `Vehículo ${data.vehiculo_patente} asignado.`)
    modalAsignar.value = false
    await cargarDispositivos()
  } catch {
    toast('error', 'Error de conexión al asignar.')
  }
}

// ── Desasignar ────────────────────────────────────────────────────────────────
const confirmDesasignar = ref(false)

function pedirDesasignar(d) {
  objetivo.value = d
  confirmDesasignar.value = true
}

async function desasignar() {
  const d = objetivo.value
  confirmDesasignar.value = false
  if (!d) return
  try {
    const res = await apiFetch(`/api/empresa/gps/dispositivos/${d.id}/desasignar/`, { method: 'POST' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo desasignar.')
      return
    }
    toast('exito', 'Vehículo desasignado.')
    await cargarDispositivos()
  } catch {
    toast('error', 'Error de conexión al desasignar.')
  }
}

// ── Configuración del servidor ────────────────────────────────────────────────
const config        = ref({ servidor_ip: '', servidor_puerto: 5000, protocolo: 'tcp' })
const guardandoConfig = ref(false)

async function guardarConfig() {
  guardandoConfig.value = true
  try {
    const res = await apiFetch('/api/empresa/gps/configuracion/', {
      method: 'PUT',
      body: { ...config.value, servidor_puerto: Number(config.value.servidor_puerto) },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      toast('error', err.error || 'No se pudo guardar la configuración.')
      return
    }
    toast('exito', 'Configuración guardada.')
  } catch {
    toast('error', 'Error de conexión al guardar.')
  } finally {
    guardandoConfig.value = false
  }
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-800">Gestión GPS</h1>
        <p class="text-sm text-gray-500">Dispositivos de rastreo y configuración del servidor.</p>
      </div>
      <div class="flex items-center gap-2">
        <router-link
          :to="ruta('/mapa')"
          class="px-4 py-2 text-sm font-semibold rounded-lg border border-indigo-200 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition"
        >
          Ver mapa de flota
        </router-link>
        <button
          v-if="puedeGestionar && tab === 'dispositivos' && !sinEmpresa"
          @click="abrirCrear"
          class="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition"
        >
          + Registrar dispositivo
        </button>
      </div>
    </div>

    <!-- Selector de empresa (solo SUPERADMIN) -->
    <SelectorEmpresa @cambio="onCambioEmpresa" />

    <!-- Estado vacío: SUPERADMIN sin empresa seleccionada -->
    <div v-if="sinEmpresa" class="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
      <p class="text-gray-500">Selecciona una empresa para gestionar sus dispositivos GPS.</p>
    </div>

    <template v-else>
    <!-- Tabs -->
    <div class="flex gap-1 mb-5 border-b border-gray-200">
      <button
        @click="tab = 'dispositivos'"
        :class="['px-4 py-2 text-sm font-medium -mb-px border-b-2 transition',
                 tab === 'dispositivos' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700']"
      >Dispositivos</button>
      <button
        @click="tab = 'configuracion'"
        :class="['px-4 py-2 text-sm font-medium -mb-px border-b-2 transition',
                 tab === 'configuracion' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-500 hover:text-gray-700']"
      >Configuración servidor</button>
    </div>

    <!-- Skeleton -->
    <div v-if="cargando" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 rounded-lg animate-pulse"></div>
    </div>

    <!-- Tab Dispositivos -->
    <div v-else-if="tab === 'dispositivos'">
      <div v-if="!dispositivos.length" class="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
        <p class="text-gray-500 mb-4">No hay dispositivos GPS registrados.</p>
        <button
          v-if="puedeGestionar"
          @click="abrirCrear"
          class="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
        >+ Registrar el primero</button>
      </div>

      <div v-else class="overflow-x-auto bg-white rounded-xl border border-gray-100 shadow-sm">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b border-gray-100 bg-gray-50">
              <th class="px-4 py-3 font-semibold">IMEI</th>
              <th class="px-4 py-3 font-semibold">Modelo</th>
              <th class="px-4 py-3 font-semibold">Vehículo asignado</th>
              <th class="px-4 py-3 font-semibold">Estado</th>
              <th v-if="puedeGestionar" class="px-4 py-3 font-semibold text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in dispositivos" :key="d.id" class="border-b border-gray-50 hover:bg-gray-50/60">
              <td class="px-4 py-3 font-mono text-gray-700">{{ d.imei }}</td>
              <td class="px-4 py-3 text-gray-600">{{ d.modelo_display }}</td>
              <td class="px-4 py-3">
                <span v-if="d.vehiculo_id" class="text-gray-700">
                  <span class="font-semibold">{{ d.vehiculo_patente }}</span>
                  <span class="text-gray-400"> · {{ d.vehiculo_nombre }}</span>
                </span>
                <span v-else class="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Sin asignar</span>
              </td>
              <td class="px-4 py-3">
                <span :class="['text-xs px-2 py-0.5 rounded-full font-medium',
                               d.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600']">
                  {{ d.activo ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td v-if="puedeGestionar" class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button v-if="!d.vehiculo_id" @click="abrirAsignar(d)"
                    class="px-2.5 py-1 text-xs rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100">Asignar</button>
                  <button v-else @click="pedirDesasignar(d)"
                    class="px-2.5 py-1 text-xs rounded-md bg-amber-50 text-amber-700 hover:bg-amber-100">Desasignar</button>
                  <button @click="abrirEditar(d)"
                    class="px-2.5 py-1 text-xs rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200">Editar</button>
                  <button @click="regenerarClave(d)" title="Generar una nueva clave de ingesta"
                    class="px-2.5 py-1 text-xs rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100">Clave</button>
                  <button v-if="d.activo" @click="pedirDesactivar(d)"
                    class="px-2.5 py-1 text-xs rounded-md bg-red-50 text-red-600 hover:bg-red-100">Desactivar</button>
                  <button v-else @click="setActivo(d, true)"
                    class="px-2.5 py-1 text-xs rounded-md bg-green-50 text-green-700 hover:bg-green-100">Activar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab Configuración -->
    <div v-else class="max-w-lg bg-white rounded-xl border border-gray-100 shadow-sm p-6">
      <p class="text-sm text-gray-500 mb-5">
        Esta IP y puerto deben configurarse en el dispositivo GPS físico. Durante el
        desarrollo con el emulador no es necesario.
      </p>

      <label class="block text-sm font-semibold text-gray-700 mb-1">IP del servidor</label>
      <input v-model="config.servidor_ip" type="text" placeholder="190.20.30.40"
        :disabled="!puedeGestionar"
        class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none disabled:bg-gray-50"/>

      <label class="block text-sm font-semibold text-gray-700 mb-1">Puerto</label>
      <input v-model="config.servidor_puerto" type="number" min="1" max="65535"
        :disabled="!puedeGestionar"
        class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none disabled:bg-gray-50"/>

      <label class="block text-sm font-semibold text-gray-700 mb-2">Protocolo</label>
      <div class="flex gap-4 mb-6">
        <label class="flex items-center gap-2 text-sm text-gray-700">
          <input type="radio" value="tcp" v-model="config.protocolo" :disabled="!puedeGestionar"/> TCP
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700">
          <input type="radio" value="udp" v-model="config.protocolo" :disabled="!puedeGestionar"/> UDP
        </label>
      </div>

      <button v-if="puedeGestionar" @click="guardarConfig" :disabled="guardandoConfig"
        class="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60">
        {{ guardandoConfig ? 'Guardando...' : 'Guardar configuración' }}
      </button>
    </div>

    </template>

    <!-- Modal alta/edición -->
    <div v-if="modalForm" class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" @click.self="modalForm = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-bold text-gray-800 mb-4">
          {{ editandoId ? 'Editar dispositivo' : 'Registrar dispositivo' }}
        </h2>

        <label class="block text-sm font-semibold text-gray-700 mb-1">IMEI</label>
        <input v-model="form.imei" type="text" maxlength="20" inputmode="numeric"
          placeholder="350000000000001"
          class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none font-mono"/>

        <label class="block text-sm font-semibold text-gray-700 mb-1">Modelo</label>
        <select v-model="form.modelo"
          class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none">
          <option v-for="m in MODELOS" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>

        <label class="flex items-center gap-2 text-sm text-gray-700 mb-6">
          <input type="checkbox" v-model="form.activo"/> Dispositivo activo
        </label>

        <div class="flex justify-end gap-2">
          <button @click="modalForm = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">Cancelar</button>
          <button @click="guardar" :disabled="guardando"
            class="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal asignar vehículo -->
    <div v-if="modalAsignar" class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" @click.self="modalAsignar = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-bold text-gray-800 mb-4">Asignar vehículo</h2>
        <label class="block text-sm font-semibold text-gray-700 mb-1">Vehículo</label>
        <select v-model="vehiculoSel"
          class="w-full mb-6 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none">
          <option value="" disabled>Selecciona un vehículo</option>
          <option v-for="v in vehiculosLibres" :key="v.id" :value="v.id">
            {{ v.patente }} · {{ v.marca }} {{ v.modelo }}
          </option>
        </select>
        <p v-if="!vehiculosLibres.length" class="text-xs text-amber-600 mb-4">
          No hay vehículos sin dispositivo GPS disponibles.
        </p>
        <div class="flex justify-end gap-2">
          <button @click="modalAsignar = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">Cancelar</button>
          <button @click="asignar" class="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">Asignar</button>
        </div>
      </div>
    </div>

    <!-- Modal de clave de ingesta (mostrada una sola vez) -->
    <div v-if="claveModal" class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" @click.self="claveModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div class="flex items-center gap-2 mb-2">
          <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1721 9z"/></svg>
          <h2 class="text-lg font-bold text-gray-800">Clave de ingesta</h2>
        </div>
        <p class="text-sm text-gray-500 mb-4">
          Esta es la clave del dispositivo <span class="font-mono font-semibold">{{ claveImei }}</span>.
          Cárgala en el dispositivo o gateway. <span class="text-amber-600 font-semibold">No se volverá a mostrar</span> — si la pierdes, puedes regenerarla.
        </p>

        <div class="flex items-center gap-2 mb-5">
          <code class="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs font-mono text-gray-800 break-all">{{ claveValor }}</code>
          <button @click="copiarClave"
            class="px-3 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shrink-0">
            {{ claveCopiada ? '✓ Copiada' : 'Copiar' }}
          </button>
        </div>

        <div class="flex justify-end">
          <button @click="claveModal = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">Listo</button>
        </div>
      </div>
    </div>

    <!-- Confirmaciones -->
    <ConfirmModal
      v-if="confirmDesactivar"
      titulo="Desactivar dispositivo"
      :mensaje="`¿Desactivar el dispositivo ${objetivo?.imei}? Dejará de recibir posiciones, pero conserva su historial y podrás reactivarlo cuando quieras.`"
      label-ok="Desactivar"
      peligroso
      @confirmar="desactivar"
      @cancelar="confirmDesactivar = false"
    />
    <ConfirmModal
      v-if="confirmDesasignar"
      titulo="Desasignar vehículo"
      :mensaje="`¿Quitar el vehículo asignado al dispositivo ${objetivo?.imei}?`"
      @confirmar="desasignar"
      @cancelar="confirmDesasignar = false"
    />
  </div>
</template>
