<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Mantenimiento Predictivo</h1>

    <!-- Tabs -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex space-x-8">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="currentTab = tab.id"
          :class="[
            currentTab === tab.id
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
          ]"
        >
          {{ tab.name }}
        </button>
      </nav>
    </div>

    <!-- Tab 1: Alertas -->
    <div v-if="currentTab === 'alertas'">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-medium text-gray-900">Alertas de Mantenimiento</h2>
        <div class="flex space-x-4">
          <select v-model="alertasFiltroNivel" @change="fetchAlertas" class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="">Todos los niveles</option>
            <option value="por_vencer">Por Vencer</option>
            <option value="vencida">Vencida</option>
          </select>
          <select v-model="alertasFiltroEstado" @change="fetchAlertas" class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
            <option value="pendiente">Pendientes</option>
            <option value="atendida">Atendidas</option>
          </select>
        </div>
      </div>
      
      <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <ul class="divide-y divide-gray-200">
          <li v-for="alerta in alertas" :key="alerta.id" class="p-4 hover:bg-gray-50 flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center space-x-3">
                <span class="text-sm font-medium text-indigo-600">{{ alerta.vehiculo_patente }}</span>
                <span class="text-sm text-gray-500">- {{ alerta.tipo_mantencion }}</span>
                <span :class="[alerta.nivel === 'vencida' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800', 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full']">
                  {{ alerta.nivel === 'vencida' ? 'Vencida' : 'Por Vencer' }}
                </span>
              </div>
              <div class="mt-2 flex items-center text-sm text-gray-500">
                <span v-if="alerta.dias_restantes <= 0" class="text-red-600 font-medium mr-2">Vencida hace {{ Math.abs(alerta.dias_restantes) }} días</span>
                <span v-else class="text-yellow-600 font-medium mr-2">Vence en {{ alerta.dias_restantes }} días</span>
                | <span class="ml-2">Avance: {{ alerta.pct_avance }}%</span>
              </div>
              <!-- ProgressBar -->
              <div class="w-full bg-gray-200 rounded-full h-1.5 mt-2 max-w-md">
                <div :class="alerta.nivel === 'vencida' ? 'bg-red-600' : 'bg-yellow-400'" class="h-1.5 rounded-full" :style="{ width: Math.min(alerta.pct_avance, 100) + '%' }"></div>
              </div>
            </div>
            <div v-if="!alerta.atendida" class="ml-4 flex items-center gap-2">
              <button
                @click="router.push({ path: ruta('/mantenciones/nueva'), query: { vehiculo: alerta.vehiculo_id, tipo: alerta.tipo_mantencion, presupuesto: alerta.costo_estimado || '' } })"
                class="inline-flex items-center px-3 py-1.5 border border-indigo-300 text-xs font-medium rounded text-indigo-700 bg-white hover:bg-indigo-50 focus:outline-none"
                title="Abrir formulario pre-llenado"
              >
                Programar
              </button>
              <button @click="openAtenderModal(alerta)" class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none">
                Registrar
              </button>
            </div>
          </li>
          <li v-if="alertas.length === 0" class="p-4 text-center text-sm text-gray-500">
            No hay alertas para mostrar.
          </li>
        </ul>
      </div>
    </div>

    <!-- Tab 2: Planes -->
    <div v-if="currentTab === 'planes'">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-medium text-gray-900">Planes de Mantenimiento</h2>
        <button @click="currentTab = 'nuevo_plan'" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none">
          + Nuevo Plan
        </button>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div v-for="plan in planes" :key="plan.id" class="bg-white overflow-hidden shadow rounded-lg border border-gray-200">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900">{{ plan.nombre }}</h3>
            <p class="mt-1 max-w-2xl text-sm text-gray-500">{{ plan.descripcion || 'Sin descripción' }}</p>
            <div class="mt-4">
              <h4 class="text-sm font-medium text-gray-900 mb-2">Reglas ({{ plan.reglas.length }})</h4>
              <ul class="text-sm text-gray-500 space-y-1">
                <li v-for="regla in plan.reglas" :key="regla.id">
                  • {{ regla.tipo }}: cada {{ regla.intervalo_dias }} días (Alerta {{ regla.umbral_alerta_dias }} días antes)
                </li>
              </ul>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-4 sm:px-6 flex justify-between items-center">
            <span :class="plan.activo ? 'text-green-600' : 'text-gray-500'" class="text-sm font-medium">
              {{ plan.activo ? 'Activo' : 'Inactivo' }}
            </span>
            <button @click="eliminarPlan(plan.id)" class="text-red-600 hover:text-red-900 text-sm font-medium">Eliminar</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 3: Nuevo Plan -->
    <div v-if="currentTab === 'nuevo_plan'">
      <div class="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div class="md:grid md:grid-cols-3 md:gap-6">
          <div class="md:col-span-1">
            <h3 class="text-lg font-medium leading-6 text-gray-900">Crear Plan</h3>
            <p class="mt-1 text-sm text-gray-500">
              Un plan contiene varias reglas que se evaluarán automáticamente.
            </p>
          </div>
          <div class="mt-5 md:mt-0 md:col-span-2">
            <form @submit.prevent="guardarPlan">
              <div class="grid grid-cols-6 gap-6">
                <div class="col-span-6 sm:col-span-4">
                  <label class="block text-sm font-medium text-gray-700">Nombre del Plan</label>
                  <input type="text" v-model="nuevoPlan.nombre" required class="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md" />
                </div>
                <div class="col-span-6 sm:col-span-4">
                  <label class="block text-sm font-medium text-gray-700">Descripción</label>
                  <textarea v-model="nuevoPlan.descripcion" rows="3" class="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"></textarea>
                </div>
              </div>

              <div class="mt-8 border-t border-gray-200 pt-6">
                <div class="flex justify-between items-center mb-4">
                  <h4 class="text-md font-medium text-gray-900">Reglas del Plan</h4>
                  <button type="button" @click="agregarRegla" class="text-sm text-indigo-600 hover:text-indigo-900">+ Agregar Regla</button>
                </div>

                <div v-for="(regla, idx) in nuevoPlan.reglas" :key="idx" class="bg-gray-50 p-4 rounded-md mb-4 border border-gray-200 relative">
                  <button type="button" @click="nuevoPlan.reglas.splice(idx, 1)" class="absolute top-2 right-2 text-red-500 hover:text-red-700">&times;</button>
                  <div class="grid grid-cols-12 gap-4">
                    <div class="col-span-12 sm:col-span-4">
                      <label class="block text-xs font-medium text-gray-700">Tipo Mantención</label>
                      <input type="text" v-model="regla.tipo" placeholder="Ej: Aceite, Frenos" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                    </div>
                    <div class="col-span-6 sm:col-span-2">
                      <label class="block text-xs font-medium text-gray-700">Intervalo (días)</label>
                      <input type="number" v-model.number="regla.intervalo_dias" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                      <p class="text-[10px] text-gray-500 mt-1">{{ formatIntervaloHelper(regla.intervalo_dias) }}</p>
                    </div>
                    <div class="col-span-6 sm:col-span-2">
                      <label class="block text-xs font-medium text-gray-700">Umbral Alerta (días)</label>
                      <input type="number" v-model.number="regla.umbral_alerta_dias" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                    </div>
                    <div class="col-span-6 sm:col-span-2">
                      <label class="block text-xs font-medium text-gray-700">Prioridad</label>
                      <select v-model="regla.prioridad" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm">
                        <option value="baja">Baja</option>
                        <option value="media">Media</option>
                        <option value="alta">Alta</option>
                      </select>
                    </div>
                    <div class="col-span-6 sm:col-span-2">
                      <label class="block text-xs font-medium text-gray-700">Costo Est. ($)</label>
                      <input type="number" v-model.number="regla.costo_estimado" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                    </div>
                    <div class="col-span-12 sm:col-span-6 flex items-center space-x-4 mt-2">
                      <label class="flex items-center text-xs text-gray-700">
                        <input type="checkbox" v-model="regla.escalar_sin_respuesta" class="mr-2 h-4 w-4 text-indigo-600 rounded border-gray-300" />
                        Escalar si no se atiende (48h)
                      </label>
                      <label class="flex items-center text-xs text-gray-700">
                        <input type="checkbox" v-model="regla.bloquear_despacho" class="mr-2 h-4 w-4 text-indigo-600 rounded border-gray-300" />
                        Bloquear si vence
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <div class="mt-6 flex justify-end">
                <button type="button" @click="currentTab = 'planes'" class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none mr-3">
                  Cancelar
                </button>
                <button type="submit" :disabled="guardando" class="bg-indigo-600 border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none">
                  {{ guardando ? 'Guardando...' : 'Guardar Plan' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 4: Simulador -->
    <div v-if="currentTab === 'simulador'">
      <div class="bg-white shadow sm:rounded-lg mb-6">
        <div class="px-4 py-5 sm:p-6 grid grid-cols-1 gap-4 sm:grid-cols-3 items-end">
          <div>
            <label class="block text-sm font-medium text-gray-700">Seleccionar Vehículo</label>
            <select v-model="simuladorVehiculoId" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm focus:ring-indigo-500 focus:border-indigo-500">
              <option value="">Seleccione...</option>
              <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} - {{ v.marca }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Período (Meses)</label>
            <select v-model="simuladorMeses" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm focus:ring-indigo-500 focus:border-indigo-500">
              <option :value="3">3 Meses</option>
              <option :value="6">6 Meses</option>
              <option :value="12">12 Meses</option>
            </select>
          </div>
          <div>
            <button @click="ejecutarSimulacion" :disabled="!simuladorVehiculoId || simulando" class="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none disabled:bg-gray-400">
              {{ simulando ? 'Calculando...' : 'Proyectar' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="simulacionResultados" class="bg-white shadow overflow-hidden sm:rounded-md">
        <div class="px-4 py-5 border-b border-gray-200 sm:px-6 flex justify-between items-center">
          <h3 class="text-lg leading-6 font-medium text-gray-900">Proyección de Eventos</h3>
          <div class="text-right">
            <p class="text-sm text-gray-500">Total Eventos: <span class="font-semibold text-gray-900">{{ simulacionResultados.total_eventos }}</span></p>
            <p class="text-sm text-gray-500">Presupuesto Est.: <span class="font-semibold text-gray-900">${{ simulacionResultados.presupuesto_total.toLocaleString() }}</span></p>
          </div>
        </div>
        <ul class="divide-y divide-gray-200">
          <li v-for="(evento, idx) in simulacionResultados.eventos" :key="idx" class="px-4 py-4 sm:px-6 hover:bg-gray-50">
            <div class="flex items-center justify-between">
              <p class="text-sm font-medium text-indigo-600 truncate">{{ evento.tipo }}</p>
              <div class="ml-2 flex-shrink-0 flex">
                <p class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  {{ formatearFecha(evento.fecha) }}
                </p>
              </div>
            </div>
            <div class="mt-2 sm:flex sm:justify-between">
              <div class="sm:flex">
                <p class="flex items-center text-sm text-gray-500">
                  Costo Est.: ${{ evento.costo_estimado.toLocaleString() }}
                </p>
              </div>
            </div>
          </li>
          <li v-if="simulacionResultados.eventos.length === 0" class="p-4 text-center text-sm text-gray-500">
            No se proyectan eventos para este período.
          </li>
        </ul>
      </div>
    </div>

    <!-- Modal Atender Alerta -->
    <div v-if="modalAtenderOpen" class="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="modalAtenderOpen = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">Registrar Mantención Realizada</h3>
            <div class="mt-2">
              <p class="text-sm text-gray-500">Vas a cerrar la alerta para el vehículo {{ alertaActual?.vehiculo_patente }} ({{ alertaActual?.tipo_mantencion }}).</p>
              <div class="mt-4 space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700">Fecha de Realización</label>
                  <input type="date" v-model="fechaRealizada" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700">Costo Final ($)</label>
                  <input type="number" v-model.number="costoRealizado" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm sm:text-sm" />
                </div>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-6 sm:flex sm:flex-row-reverse">
            <button type="button" @click="atenderAlerta" :disabled="guardandoAtencion" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm disabled:bg-gray-400">
              {{ guardandoAtencion ? 'Guardando...' : 'Confirmar' }}
            </button>
            <button type="button" @click="modalAtenderOpen = false" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:w-auto sm:text-sm">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../utils/api.js'
import { useEmpresaNav } from '../../../utils/empresaActiva.js'

const router = useRouter()
const { ruta } = useEmpresaNav()

const tabs = [
  { id: 'alertas', name: 'Alertas' },
  { id: 'planes', name: 'Planes' },
  { id: 'nuevo_plan', name: 'Nuevo Plan' },
  { id: 'simulador', name: 'Simulador' }
]

const currentTab = ref('alertas')

// Alertas
const alertas = ref([])
const alertasFiltroNivel = ref('')
const alertasFiltroEstado = ref('pendiente')

const fetchAlertas = async () => {
  try {
    let url = '/api/empresa/alertas-mantenimiento/?'
    if (alertasFiltroNivel.value) url += `nivel=${alertasFiltroNivel.value}&`
    if (alertasFiltroEstado.value) url += `estado=${alertasFiltroEstado.value}&`
    const res = await apiFetch(url)
    if (res.ok) alertas.value = await res.json()
  } catch (err) {
    console.error(err)
  }
}

// Planes
const planes = ref([])
const fetchPlanes = async () => {
  try {
    const res = await apiFetch('/api/empresa/planes-mantenimiento/')
    if (res.ok) planes.value = await res.json()
  } catch (err) {
    console.error(err)
  }
}

const eliminarPlan = async (id) => {
  if (confirm('¿Estás seguro de eliminar este plan?')) {
    try {
      const res = await apiFetch(`/api/empresa/planes-mantenimiento/${id}/`, { method: 'DELETE' })
      if (res.ok) fetchPlanes()
    } catch (err) {
      console.error(err)
    }
  }
}

// Nuevo Plan
const guardando = ref(false)
const nuevoPlan = ref({
  nombre: '',
  descripcion: '',
  activo: true,
  reglas: [
    { tipo: '', intervalo_dias: 90, umbral_alerta_dias: 15, prioridad: 'media', costo_estimado: 0, escalar_sin_respuesta: false, bloquear_despacho: false, canal: 'email' }
  ]
})

const agregarRegla = () => {
  nuevoPlan.value.reglas.push({
    tipo: '', intervalo_dias: 90, umbral_alerta_dias: 15, prioridad: 'media', costo_estimado: 0, escalar_sin_respuesta: false, bloquear_despacho: false, canal: 'email'
  })
}

const guardarPlan = async () => {
  guardando.value = true
  try {
    const res = await apiFetch('/api/empresa/planes-mantenimiento/', {
      method: 'POST',
      body: nuevoPlan.value
    })
    if (res.ok) {
      nuevoPlan.value = {
        nombre: '', descripcion: '', activo: true, reglas: [{ tipo: '', intervalo_dias: 90, umbral_alerta_dias: 15, prioridad: 'media', costo_estimado: 0, escalar_sin_respuesta: false, bloquear_despacho: false, canal: 'email' }]
      }
      fetchPlanes()
      currentTab.value = 'planes'
    } else {
      alert('Error al guardar el plan')
    }
  } catch (err) {
    console.error(err)
    alert('Error al guardar el plan')
  } finally {
    guardando.value = false
  }
}

// Helper intervalo
const formatIntervaloHelper = (dias) => {
  if (!dias) return ''
  if (dias >= 365) return `Aprox ${Math.round(dias/365 * 10)/10} años`
  if (dias >= 30) return `Aprox ${Math.round(dias/30 * 10)/10} meses`
  return `${dias} días`
}

// Atender Alerta
const modalAtenderOpen = ref(false)
const alertaActual = ref(null)
const fechaRealizada = ref(new Date().toISOString().slice(0, 10))
const costoRealizado = ref(0)
const guardandoAtencion = ref(false)

const openAtenderModal = (alerta) => {
  alertaActual.value = alerta
  fechaRealizada.value = new Date().toISOString().slice(0, 10)
  costoRealizado.value = 0
  modalAtenderOpen.value = true
}

const atenderAlerta = async () => {
  guardandoAtencion.value = true
  try {
    const res = await apiFetch(`/api/empresa/alertas-mantenimiento/${alertaActual.value.id}/atender/`, {
      method: 'POST',
      body: {
        fecha_realizada: fechaRealizada.value,
        costo: costoRealizado.value
      }
    })
    if (res.ok) {
      modalAtenderOpen.value = false
      fetchAlertas()
    } else {
      alert('Error al registrar la atención')
    }
  } catch (err) {
    console.error(err)
    alert('Error al registrar la atención')
  } finally {
    guardandoAtencion.value = false
  }
}

// Simulador
const vehiculos = ref([])
const simuladorVehiculoId = ref('')
const simuladorMeses = ref(3)
const simulando = ref(false)
const simulacionResultados = ref(null)

const fetchVehiculos = async () => {
  try {
    const res = await apiFetch('/api/empresa/vehiculos/')
    if (res.ok) vehiculos.value = await res.json()
  } catch (err) {
    console.error(err)
  }
}

const ejecutarSimulacion = async () => {
  simulando.value = true
  simulacionResultados.value = null
  try {
    let url = `/api/empresa/simulador-vencimientos/?vehiculo_id=${simuladorVehiculoId.value}&meses=${simuladorMeses.value}`
    const res = await apiFetch(url)
    if (res.ok) {
      simulacionResultados.value = await res.json()
    } else {
      alert('Error al ejecutar la simulación')
    }
  } catch (err) {
    console.error(err)
    alert('Error al ejecutar la simulación')
  } finally {
    simulando.value = false
  }
}

const formatearFecha = (fechaStr) => {
  const [year, month, day] = fechaStr.split('-')
  return `${day}/${month}/${year}`
}

onMounted(() => {
  fetchAlertas()
  fetchPlanes()
  fetchVehiculos()
})
</script>
