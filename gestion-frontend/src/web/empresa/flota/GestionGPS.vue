<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch, safeJsonParse } from '../../../utils/api.js'
import { tienePermiso } from '../../../utils/permisos.js'
import { getEmpresaActiva, useEmpresaNav, EMPRESA_TODAS } from '../../../utils/empresaActiva.js'
import ConfirmModal from '../../../components/ConfirmModal.vue'
import SelectorEmpresa from '../../../components/SelectorEmpresa.vue'
import { usePaginacion } from '../../../composables/usePaginacion.js'
import PaginacionTabla from '../../../components/PaginacionTabla.vue'

const { ruta } = useEmpresaNav()

// ── Estado general ────────────────────────────────────────────────────────────
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
// Modo "Todas las empresas": vista de solo lectura (la gestión exige una empresa
// concreta, así que se ocultan las acciones y se muestra la columna Empresa).
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)

const MODELOS = [
  { value: 'emulador',  label: 'Emulador NMEA' },
  { value: 'teltonika', label: 'Teltonika' },
  { value: 'queclink',  label: 'Queclink' },
  { value: 'coban',     label: 'Coban' },
  { value: 'otro',      label: 'Otro' },
]

// Longitud del nombre libre del modelo cuando se elige la marca "Otro".
const MODELO_OTRO_MIN = 2
const MODELO_OTRO_MAX = 20

// Validación visible del "Nombre del modelo" (solo cuando la marca es "Otro").
const modeloOtroLen   = computed(() => (form.value?.modelo_otro || '').trim().length)
const modeloOtroError = computed(() => {
  if (form.value?.modelo !== 'otro') return ''
  const l = modeloOtroLen.value
  if (l === 0) return 'Ingresa el nombre del modelo.'
  if (l < MODELO_OTRO_MIN) return `Debe tener al menos ${MODELO_OTRO_MIN} caracteres.`
  if (l > MODELO_OTRO_MAX) return `No puede superar los ${MODELO_OTRO_MAX} caracteres.`
  return ''
})

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

async function cargarTodo() {
  cargando.value = true
  await Promise.all([cargarDispositivos(), cargarVehiculos()])
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
const modalForm      = ref(false)
const editandoId     = ref(null)
const form           = ref({ imei: '', modelo: 'emulador', modelo_otro: '', activo: true })
const guardando      = ref(false)
const empresaIdForm  = ref('')   // empresa elegida en el form cuando esTodas
const listaEmpresas  = ref([])

async function cargarListaEmpresas() {
  if (!esSuperadmin.value || listaEmpresas.value.length) return
  const res = await apiFetch('/api/empresas/')
  if (res.ok) listaEmpresas.value = await res.json()
}

function abrirCrear() {
  editandoId.value    = null
  empresaIdForm.value = ''
  form.value = { imei: '', modelo: 'emulador', modelo_otro: '', activo: true }
  if (esTodas.value) cargarListaEmpresas()
  modalForm.value = true
}

function abrirEditar(d) {
  editandoId.value = d.id
  form.value = { imei: d.imei, modelo: d.modelo, modelo_otro: d.modelo_otro || '', activo: d.activo }
  modalForm.value = true
}

async function guardar() {
  const imei = (form.value.imei || '').trim()
  if (imei.length < 1 || imei.length > 20) {
    toast('error', 'El IMEI es obligatorio y no puede superar los 20 caracteres.')
    return
  }
  if (esTodas.value && !editandoId.value && !empresaIdForm.value) {
    toast('error', 'Selecciona una empresa para registrar el dispositivo.')
    return
  }
  const modeloOtro = (form.value.modelo_otro || '').trim()
  if (form.value.modelo === 'otro' &&
      (modeloOtro.length < MODELO_OTRO_MIN || modeloOtro.length > MODELO_OTRO_MAX)) {
    toast('error', `El nombre del modelo debe tener entre ${MODELO_OTRO_MIN} y ${MODELO_OTRO_MAX} caracteres.`)
    return
  }
  guardando.value = true
  try {
    const url    = editandoId.value
      ? `/api/empresa/gps/dispositivos/${editandoId.value}/`
      : '/api/empresa/gps/dispositivos/'
    const method = editandoId.value ? 'PUT' : 'POST'
    const body   = { ...form.value, imei, modelo_otro: modeloOtro }
    if (esTodas.value && !editandoId.value) body.empresa_id = empresaIdForm.value
    const res = await apiFetch(url, { method, body })
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

// ── Regenerar clave (con confirmación) ──────────────────────────────────────
const confirmRegenerar = ref(false)

function pedirRegenerar(d) {
  objetivo.value = d
  confirmRegenerar.value = true
}

async function confirmarRegenerar() {
  const d = objetivo.value
  confirmRegenerar.value = false
  if (d) await regenerarClave(d)
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
const modalAsignar     = ref(false)
const asignarId        = ref(null)
const asignarEmpresaId = ref(null)
const asignarEmpresaNombre = ref('')
const vehiculoSel      = ref('')

const dispositivosFiltrados = computed(() => dispositivos.value)
const { pagina, totalPaginas, total, paginado, irA } = usePaginacion(dispositivosFiltrados, 20)

const vehiculosLibres = computed(() => {
  // Vehículos sin dispositivo_gps asignado. La lista de vehículos no trae ese
  // dato directo, así que excluimos los que ya aparecen asignados a un dispositivo.
  const ocupados = new Set(
    dispositivos.value.filter(d => d.vehiculo_id).map(d => d.vehiculo_id)
  )
  let libres = vehiculos.value.filter(v => !ocupados.has(v.id))
  // Modo "Todas": el dispositivo pertenece a una empresa concreta, así que solo
  // se pueden asignar vehículos de esa misma empresa.
  if (esTodas.value && asignarEmpresaId.value) {
    libres = libres.filter(v => v.empresa_id === asignarEmpresaId.value)
  }
  return libres
})

function abrirAsignar(d) {
  asignarId.value = d.id
  asignarEmpresaId.value = d.empresa_id ?? null
  asignarEmpresaNombre.value = d.empresa_nombre || ''
  vehiculoSel.value = ''
  modalAsignar.value = true
}

async function asignar() {
  if (!vehiculoSel.value) {
    toast('error', 'Selecciona un vehículo.')
    return
  }
  try {
    const url = `/api/empresa/gps/dispositivos/${asignarId.value}/asignar/`
      + (esTodas.value ? `?empresa_id=${asignarEmpresaId.value}` : '')
    const res = await apiFetch(url, {
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
    const url = `/api/empresa/gps/dispositivos/${d.id}/desasignar/`
      + (esTodas.value ? `?empresa_id=${d.empresa_id}` : '')
    const res = await apiFetch(url, { method: 'POST' })
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

</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-800">Gestión GPS</h1>
        <p class="text-sm text-gray-500">Dispositivos de rastreo de la flota.</p>
      </div>
      <div class="flex items-center gap-2">
        <router-link
          :to="ruta('/mapa')"
          class="px-4 py-2 text-sm font-semibold rounded-lg border border-indigo-200 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition"
        >
          Ver mapa de flota
        </router-link>
        <button
          v-if="puedeGestionar && !sinEmpresa"
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
    <!-- Skeleton -->
    <div v-if="cargando" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 rounded-lg animate-pulse"></div>
    </div>

    <!-- Lista de dispositivos -->
    <div v-else>
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
              <th v-if="esTodas" class="px-4 py-3 font-semibold">Empresa</th>
              <th class="px-4 py-3 font-semibold">IMEI</th>
              <th class="px-4 py-3 font-semibold">Modelo</th>
              <th class="px-4 py-3 font-semibold">Vehículo asignado</th>
              <th class="px-4 py-3 font-semibold">Estado</th>
              <th v-if="puedeGestionar" class="px-4 py-3 font-semibold text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in paginado" :key="d.id" class="border-b border-gray-50 hover:bg-gray-50/60">
              <td v-if="esTodas" class="px-4 py-3 text-gray-700 font-medium">{{ d.empresa_nombre || '—' }}</td>
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
                  <button @click="pedirRegenerar(d)" title="Generar una nueva clave de ingesta"
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
        <PaginacionTabla
          :pagina="pagina"
          :total-paginas="totalPaginas"
          :total="total"
          :por-pagina="20"
          @update:pagina="irA"
        />
      </div>
    </div>

    </template>

    <!-- Modal alta/edición -->
    <div v-if="modalForm" class="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" @click.self="modalForm = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-bold text-gray-800 mb-4">
          {{ editandoId ? 'Editar dispositivo' : 'Registrar dispositivo' }}
        </h2>

        <!-- Empresa (solo SUPERADMIN en modo "Todas", al crear) -->
        <template v-if="esTodas && !editandoId">
          <label class="block text-sm font-semibold text-gray-700 mb-1">Empresa *</label>
          <select v-model="empresaIdForm"
            class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none">
            <option value="" disabled>— Seleccionar empresa —</option>
            <option v-for="e in listaEmpresas.filter(x => x.id !== '__todas__')" :key="e.id" :value="e.id">{{ e.nombre }}</option>
          </select>
        </template>

        <label class="block text-sm font-semibold text-gray-700 mb-1">IMEI</label>
        <input v-model="form.imei" type="text" maxlength="20" inputmode="numeric"
          placeholder="350000000000001"
          class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none font-mono"/>

        <label class="block text-sm font-semibold text-gray-700 mb-1">Modelo</label>
        <select v-model="form.modelo"
          class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 outline-none">
          <option v-for="m in MODELOS" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>

        <!-- Nombre libre del modelo: solo cuando la marca es "Otro" -->
        <template v-if="form.modelo === 'otro'">
          <div class="flex items-center justify-between mb-1">
            <label class="block text-sm font-semibold text-gray-700">Nombre del modelo</label>
            <span class="text-xs" :class="modeloOtroLen > MODELO_OTRO_MAX ? 'text-red-500' : 'text-gray-400'">
              {{ modeloOtroLen }}/{{ MODELO_OTRO_MAX }}
            </span>
          </div>
          <input v-model="form.modelo_otro" type="text" :maxlength="MODELO_OTRO_MAX"
            placeholder="Ej. Sinotrack ST-901"
            class="w-full mb-1 px-3 py-2 text-sm border rounded-lg outline-none"
            :class="modeloOtroError ? 'border-red-400 focus:border-red-400' : 'border-gray-200 focus:border-indigo-400'"/>
          <p class="text-xs mb-4" :class="modeloOtroError ? 'text-red-500' : 'text-gray-400'">
            {{ modeloOtroError || `Entre ${MODELO_OTRO_MIN} y ${MODELO_OTRO_MAX} caracteres.` }}
          </p>
        </template>

        <label class="flex items-center gap-2 text-sm text-gray-700 mb-6">
          <input type="checkbox" v-model="form.activo"/> Dispositivo activo
        </label>

        <div class="flex justify-end gap-2">
          <button @click="modalForm = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">Cancelar</button>
          <button @click="guardar" :disabled="guardando || !!modeloOtroError"
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

        <!-- Empresa del dispositivo (solo SUPERADMIN en modo "Todas") -->
        <template v-if="esTodas">
          <label class="block text-sm font-semibold text-gray-700 mb-1">Empresa</label>
          <select disabled
            class="w-full mb-4 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-gray-50 text-gray-500">
            <option>{{ asignarEmpresaNombre || '—' }}</option>
          </select>
        </template>

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
    <ConfirmModal
      v-if="confirmRegenerar"
      titulo="Regenerar clave de ingesta"
      :mensaje="`Se generará una nueva clave para ${objetivo?.imei}. La clave anterior dejará de funcionar de inmediato y el dispositivo no podrá enviar posiciones hasta que cargues la nueva en él. ¿Continuar?`"
      label-ok="Regenerar"
      peligroso
      @confirmar="confirmarRegenerar"
      @cancelar="confirmRegenerar = false"
    />
  </div>
</template>
