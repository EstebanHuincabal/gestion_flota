<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Notificaciones</h1>
      <div class="flex items-center space-x-3">
        <router-link
          :to="baseUrl + '/notificaciones/preferencias'"
          class="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          Preferencias
        </router-link>
        <button
          v-if="hayNoLeidas"
          @click="marcarTodas"
          class="text-sm text-gray-500 hover:text-gray-700 font-medium"
        >
          Marcar todas como leídas
        </button>
      </div>
    </div>

    <!-- Filtros -->
    <div class="flex flex-wrap gap-2 mb-6">
      <button
        v-for="f in filtros" :key="f.value"
        @click="filtroActivo = f.value; cargar()"
        :class="[
          filtroActivo === f.value
            ? 'bg-indigo-600 text-white'
            : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
          'px-3 py-1.5 rounded-full text-sm font-medium transition'
        ]"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- Lista -->
    <div class="bg-white shadow rounded-lg divide-y divide-gray-100">
      <div
        v-for="n in notificaciones" :key="n.id"
        @click="abrir(n)"
        :class="['flex items-start gap-4 p-4 cursor-pointer hover:bg-gray-50 transition', !n.leida && 'bg-indigo-50/40']"
      >
        <!-- Icono tipo -->
        <div :class="['flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center', iconoBg(n.tipo)]">
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconoPath(n.tipo)" />
          </svg>
        </div>

        <!-- Contenido -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <p :class="['text-sm font-medium text-gray-900 truncate', !n.leida && 'font-semibold']">
              {{ n.titulo }}
            </p>
            <span class="ml-3 flex-shrink-0 text-xs text-gray-400">{{ formatRelativo(n.fecha) }}</span>
          </div>
          <p class="text-sm text-gray-500 mt-0.5 line-clamp-2">{{ n.mensaje }}</p>
        </div>

        <!-- Dot no leída -->
        <div v-if="!n.leida" class="flex-shrink-0 mt-1.5 w-2 h-2 rounded-full bg-indigo-500"></div>
      </div>

      <div v-if="notificaciones.length === 0" class="p-8 text-center text-sm text-gray-500">
        No hay notificaciones para mostrar.
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="totalPaginas > 1" class="flex justify-center items-center gap-3 mt-6">
      <button
        :disabled="paginaActual === 1"
        @click="paginaActual--; cargar()"
        class="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
      >
        ← Anterior
      </button>
      <span class="text-sm text-gray-600">{{ paginaActual }} / {{ totalPaginas }}</span>
      <button
        :disabled="paginaActual === totalPaginas"
        @click="paginaActual++; cargar()"
        class="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
      >
        Siguiente →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()
const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const baseUrl = computed(() => usuario.rol === 'SUPERADMIN' ? '' : '/empresa')

const notificaciones = ref([])
const paginaActual   = ref(1)
const totalPaginas   = ref(1)
const filtroActivo   = ref('')

const filtros = [
  { value: '',             label: 'Todas' },
  { value: 'false',        label: 'No leídas', param: 'leida' },
  { value: 'mantencion_por_vencer', label: 'Mantenimiento', param: 'tipo' },
  { value: 'documento_por_vencer', label: 'Documentos', param: 'tipo' },
  { value: 'seguridad',    label: 'Seguridad', param: 'tipo' },
  { value: 'actividad',    label: 'Actividad', param: 'tipo' },
]

const hayNoLeidas = computed(() => notificaciones.value.some(n => !n.leida))

const cargar = async () => {
  let url = `/api/notificaciones/?page=${paginaActual.value}`
  const filtro = filtros.find(f => f.value === filtroActivo.value)
  if (filtro && filtro.param === 'leida') url += `&leida=${filtroActivo.value}`
  else if (filtro && filtro.param === 'tipo') url += `&tipo=${filtroActivo.value}`

  const res = await apiFetch(url)
  if (res.ok) {
    const data = await res.json()
    notificaciones.value = data.results
    totalPaginas.value   = data.num_pages
  }
}

const abrir = async (n) => {
  if (!n.leida) {
    await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: { ids: [n.id] } })
    n.leida = true
  }
  if (n.url_accion) router.push(n.url_accion)
}

const marcarTodas = async () => {
  await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: { todas: true } })
  notificaciones.value.forEach(n => (n.leida = true))
}

const iconoBg = (tipo) => {
  if (tipo.startsWith('mantencion')) return 'bg-yellow-500'
  if (tipo.startsWith('documento'))  return 'bg-blue-500'
  if (tipo === 'seguridad')          return 'bg-red-500'
  return 'bg-gray-500'
}

const iconoPath = (tipo) => {
  if (tipo.startsWith('mantencion'))
    return 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
  if (tipo.startsWith('documento'))
    return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  if (tipo === 'seguridad')
    return 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z'
  return 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9'
}

const formatRelativo = (fecha) => {
  const diff = Date.now() - new Date(fecha).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1)   return 'Ahora'
  if (min < 60)  return `Hace ${min}m`
  const h = Math.floor(min / 60)
  if (h < 24)    return `Hace ${h}h`
  const d = Math.floor(h / 24)
  return `Hace ${d}d`
}

onMounted(cargar)
</script>
