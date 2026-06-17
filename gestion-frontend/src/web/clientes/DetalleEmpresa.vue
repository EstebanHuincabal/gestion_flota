<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const route = useRoute()
const router = useRouter()
const empresaId = route.params.id

const tabActiva = ref('informacion')
const tabs = [
  { id: 'informacion', label: 'Información' },
  { id: 'estadisticas', label: 'Estadísticas' },
  { id: 'usuarios', label: 'Usuarios y Conductores' },
  { id: 'actividad', label: 'Actividad' }
]

const loading = ref(true)
const error = ref('')
const data = ref(null)

const cargarDetalle = async () => {
  try {
    const res = await apiFetch(`/api/empresas/${empresaId}/`)
    if (!res.ok) throw new Error('Error al cargar detalle de la empresa')
    data.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(cargarDetalle)
</script>

<template>
  <div class="page p-8 max-w-7xl mx-auto">
    <!-- Header & Back Button -->
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button @click="router.push('/empresas')" class="p-2 bg-white border border-gray-200 rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-3">
            {{ data?.informacion?.nombre || 'Cargando...' }}
            <span v-if="data" :class="['px-2 py-0.5 text-xs font-semibold rounded-full', data.informacion.estado === 'activa' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-600']">
              {{ data.informacion.estado === 'activa' ? 'Activa' : 'Suspendida' }}
            </span>
          </h1>
          <p class="text-sm text-gray-500 mt-1">Detalle y métricas completas de la empresa</p>
        </div>
      </div>
      
      <button v-if="data" @click="router.push(`/empresas/${empresaId}/editar`)" class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 transition flex items-center gap-2">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        Editar Empresa
      </button>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="py-12 flex flex-col items-center justify-center text-gray-500">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
      Cargando información...
    </div>
    
    <div v-else-if="error" class="bg-red-50 text-red-600 p-4 rounded-lg border border-red-100 mb-6">
      {{ error }}
    </div>

    <template v-else>
      <!-- Tabs Navigation -->
      <div class="border-b border-gray-200 mb-6">
        <nav class="-mb-px flex gap-6" aria-label="Tabs">
          <button 
            v-for="tab in tabs" 
            :key="tab.id"
            @click="tabActiva = tab.id"
            :class="[
              tabActiva === tab.id 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200'
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- Tab Content: Información -->
      <div v-if="tabActiva === 'informacion'" class="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-200 bg-gray-50">
          <h3 class="text-base font-semibold leading-6 text-gray-900">Perfil de la Empresa</h3>
        </div>
        <div class="px-6 py-6 grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-4">
          <div>
            <dt class="text-sm font-medium text-gray-500">Nombre o Razón Social</dt>
            <dd class="mt-1 text-sm text-gray-900 font-semibold">{{ data.informacion.nombre }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">RUT</dt>
            <dd class="mt-1 text-sm text-gray-900 font-mono">{{ data.informacion.rut }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">Estado en Plataforma</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ data.informacion.estado === 'activa' ? 'Actualmente Operativa' : 'Suspendida' }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500">Fecha de Registro</dt>
            <dd class="mt-1 text-sm text-gray-900">{{ new Date(data.informacion.created_at).toLocaleDateString('es-CL', { year: 'numeric', month: 'long', day: 'numeric' }) }}</dd>
          </div>
          <template v-if="data.informacion.email || data.informacion.telefono">
            <div v-if="data.informacion.email">
              <dt class="text-sm font-medium text-gray-500">Email de Contacto</dt>
              <dd class="mt-1 text-sm text-gray-900">{{ data.informacion.email }}</dd>
            </div>
            <div v-if="data.informacion.telefono">
              <dt class="text-sm font-medium text-gray-500">Teléfono</dt>
              <dd class="mt-1 text-sm text-gray-900">{{ data.informacion.telefono }}</dd>
            </div>
          </template>
          <template v-if="data.informacion.direccion || data.informacion.region">
            <div v-if="data.informacion.direccion" class="md:col-span-2">
              <dt class="text-sm font-medium text-gray-500">Dirección</dt>
              <dd class="mt-1 text-sm text-gray-900">
                {{ data.informacion.direccion }}
                <span v-if="data.informacion.comuna">, {{ data.informacion.comuna }}</span>
                <span v-if="data.informacion.ciudad">, {{ data.informacion.ciudad }}</span>
              </dd>
            </div>
            <div v-if="data.informacion.region">
              <dt class="text-sm font-medium text-gray-500">Región</dt>
              <dd class="mt-1 text-sm text-gray-900">{{ data.informacion.region_display || data.informacion.region }}</dd>
            </div>
            <div v-if="data.informacion.pais">
              <dt class="text-sm font-medium text-gray-500">País</dt>
              <dd class="mt-1 text-sm text-gray-900">{{ data.informacion.pais }}</dd>
            </div>
          </template>
        </div>
      </div>

      <!-- Tab Content: Estadísticas -->
      <div v-if="tabActiva === 'estadisticas'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Vehículos Registrados</p>
              <p class="text-2xl font-bold text-gray-900">{{ data.estadisticas.vehiculos }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Conductores Activos</p>
              <p class="text-2xl font-bold text-gray-900">{{ data.estadisticas.conductores }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-orange-50 text-orange-600 rounded-lg">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Mantenciones (Histórico)</p>
              <p class="text-2xl font-bold text-gray-900">{{ data.estadisticas.mantenciones }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div class="flex items-center gap-4">
            <div class="p-3 bg-purple-50 text-purple-600 rounded-lg">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Documentos Cargados</p>
              <p class="text-2xl font-bold text-gray-900">{{ data.estadisticas.documentos }}</p>
            </div>
          </div>
        </div>

      </div>

      <!-- Tab Content: Usuarios -->
      <div v-if="tabActiva === 'usuarios'" class="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nombre</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">RUT</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Rol</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-if="data.usuarios.length === 0">
                <td colspan="5" class="px-6 py-12 text-center text-sm text-gray-500">No hay usuarios asignados a esta empresa.</td>
              </tr>
              <tr v-for="u in data.usuarios" :key="u.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ u.nombre }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">{{ u.rut }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ u.email }}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="[
                    'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                    u.rol === 'ADMIN' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                  ]">{{ u.rol }}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span v-if="u.is_active" class="text-green-600 font-medium">Activo</span>
                  <span v-else class="text-red-600 font-medium">Bloqueado</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab Content: Actividad -->
      <div v-if="tabActiva === 'actividad'" class="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden p-6">
        <h3 class="text-base font-semibold leading-6 text-gray-900 mb-6">Últimos accesos a la plataforma</h3>
        
        <div v-if="data.actividad.length === 0" class="text-center text-gray-500 py-8 text-sm">
          No se registran accesos recientes.
        </div>
        
        <div v-else class="flow-root">
          <ul role="list" class="-mb-8">
            <li v-for="(act, idx) in data.actividad" :key="idx">
              <div class="relative pb-8">
                <span v-if="idx !== data.actividad.length - 1" class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>
                <div class="relative flex space-x-3">
                  <div>
                    <span :class="[
                      act.rol === 'ADMIN' ? 'bg-purple-500' : 'bg-blue-500',
                      'h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white'
                    ]">
                      <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                    </span>
                  </div>
                  <div class="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                    <div>
                      <p class="text-sm text-gray-500">Inicio de sesión por <span class="font-medium text-gray-900">{{ act.usuario }}</span> ({{ act.rol }})</p>
                    </div>
                    <div class="whitespace-nowrap text-right text-sm text-gray-500">
                      <time :datetime="act.fecha">{{ new Date(act.fecha).toLocaleString('es-CL') }}</time>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

    </template>
  </div>
</template>