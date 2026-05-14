<template>
  <div class="p-8 max-w-2xl">
    <div class="flex items-center gap-3 mb-6">
      <router-link :to="baseUrl + '/notificaciones'" class="text-gray-400 hover:text-gray-600">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
      </router-link>
      <h1 class="text-2xl font-bold text-gray-900">Preferencias de notificación</h1>
    </div>

    <div class="bg-white shadow rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Evento</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">In-App</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="cat in categorias" :key="cat.key">
            <td class="px-6 py-4">
              <p class="text-sm font-medium text-gray-900">{{ cat.label }}</p>
              <p class="text-xs text-gray-500">{{ cat.desc }}</p>
            </td>
            <td class="px-6 py-4 text-center">
              <input
                type="checkbox"
                :checked="prefs.inapp.includes(cat.key)"
                @change="toggle('inapp', cat.key)"
                class="h-4 w-4 text-indigo-600 border-gray-300 rounded cursor-pointer"
              />
            </td>
            <td class="px-6 py-4 text-center">
              <input
                type="checkbox"
                :checked="prefs.email.includes(cat.key)"
                @change="toggle('email', cat.key)"
                class="h-4 w-4 text-indigo-600 border-gray-300 rounded cursor-pointer"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-6 flex justify-end gap-3">
      <router-link :to="baseUrl + '/notificaciones'"
        class="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
        Cancelar
      </router-link>
      <button
        @click="guardar"
        :disabled="guardando"
        class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-60"
      >
        {{ guardando ? 'Guardando...' : 'Guardar preferencias' }}
      </button>
    </div>

    <p v-if="guardado" class="mt-3 text-sm text-green-600 text-right">✓ Preferencias guardadas</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const baseUrl = computed(() => usuario.rol === 'SUPERADMIN' ? '' : '/empresa')

const categorias = [
  { key: 'mantencion', label: 'Mantenimiento',      desc: 'Alertas de mantenimiento predictivo por vencer o vencidas' },
  { key: 'documentos', label: 'Documentos',         desc: 'Documentos de vehículos y conductores próximos a vencer' },
  { key: 'seguridad',  label: 'Seguridad',          desc: 'Cambios de contraseña, bloqueos y modificaciones de permisos' },
  { key: 'actividad',  label: 'Actividad operacional', desc: 'Asignaciones de conductor, nuevos vehículos y más' },
]

const prefs    = ref({ inapp: [], email: [], push_token: '' })
const guardando = ref(false)
const guardado  = ref(false)

const toggle = (canal, categoria) => {
  const lista = prefs.value[canal]
  const idx   = lista.indexOf(categoria)
  if (idx === -1) lista.push(categoria)
  else lista.splice(idx, 1)
}

const guardar = async () => {
  guardando.value = true
  guardado.value  = false
  const res = await apiFetch('/api/notificaciones/preferencias/', {
    method: 'PUT',
    body: prefs.value
  })
  if (res.ok) {
    prefs.value = await res.json()
    guardado.value = true
    setTimeout(() => (guardado.value = false), 3000)
  }
  guardando.value = false
}

onMounted(async () => {
  const res = await apiFetch('/api/notificaciones/preferencias/')
  if (res.ok) prefs.value = await res.json()
})
</script>
