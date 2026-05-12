<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import AppToast from '../../components/AppToast.vue'

const toast = ref(null)
const planes = ref([])
const cargandoPlanes = ref(false)

const cargarPlanes = async () => {
  cargandoPlanes.value = true
  try {
    const res = await apiFetch('/api/configuracion/planes/')
    if (res.ok) planes.value = await res.json()
  } catch (e) {}
  cargandoPlanes.value = false
}

onMounted(() => {
  cargarPlanes()
})
</script>

<template>
  <AppToast ref="toast" />
  <div class="page p-8 max-w-7xl mx-auto">
    
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">Planes de Suscripción</h1>
      <p class="text-sm text-gray-500 mt-2">Configura los límites de capacidad para cada plan comercial.</p>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden min-h-[500px]">
      <div class="px-6 py-5 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Planes Disponibles</h2>
        </div>
        <button class="px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          + Añadir Plan
        </button>
      </div>

      <div class="p-6">
        <div v-if="cargandoPlanes" class="py-12 flex justify-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-if="planes.length === 0" class="col-span-full text-center py-12 text-gray-500">
            No hay planes registrados.
          </div>
          <div v-for="plan in planes" :key="plan.id" class="border border-gray-200 rounded-xl overflow-hidden hover:border-indigo-300 transition-colors bg-white">
            <div class="px-5 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
              <h3 class="font-bold text-gray-900 capitalize">{{ plan.nombre }}</h3>
              <button class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">Editar</button>
            </div>
            <div class="p-5 space-y-4">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Límite Flotas</span>
                <span class="font-semibold text-gray-900">{{ plan.max_flotas }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Límite Vehículos</span>
                <span class="font-semibold text-gray-900">{{ plan.max_vehiculos }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Límite Conductores</span>
                <span class="font-semibold text-gray-900">{{ plan.max_conductores }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>