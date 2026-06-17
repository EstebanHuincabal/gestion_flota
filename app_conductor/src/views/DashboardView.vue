<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { apiFetch } from '../utils/api.js'

const auth    = useAuthStore()
const rutas   = ref([])
const cargando = ref(true)

onMounted(async () => {
  try {
    // Ejemplo: cargar rutas asignadas al conductor
    // const res = await apiFetch('/api/conductor/rutas/')
    // if (res.ok) rutas.value = await res.json()
  } finally {
    cargando.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">

    <!-- Header -->
    <header class="bg-white border-b border-gray-100 px-4 pt-safe pb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center">
          <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
          </svg>
        </div>
        <div>
          <p class="text-xs text-gray-400 leading-tight">Bienvenido</p>
          <p class="text-sm font-semibold text-gray-800 leading-tight">{{ auth.nombreVisible }}</p>
        </div>
      </div>
      <button @click="auth.logout()" class="p-2 text-gray-400 hover:text-red-500 transition">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
        </svg>
      </button>
    </header>

    <!-- Contenido -->
    <main class="flex-1 p-4">
      <!-- Módulos disponibles (se irán completando) -->
      <div class="grid grid-cols-2 gap-3 mt-2">

        <div class="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm flex flex-col items-center gap-2 text-center opacity-50">
          <div class="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
            </svg>
          </div>
          <span class="text-xs font-semibold text-gray-700">Mis Rutas</span>
          <span class="text-[10px] text-gray-400">Próximamente</span>
        </div>

        <div class="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm flex flex-col items-center gap-2 text-center opacity-50">
          <div class="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
          </div>
          <span class="text-xs font-semibold text-gray-700">Documentos</span>
          <span class="text-[10px] text-gray-400">Próximamente</span>
        </div>

        <div class="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm flex flex-col items-center gap-2 text-center opacity-50">
          <div class="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
            </svg>
          </div>
          <span class="text-xs font-semibold text-gray-700">Mi Vehículo</span>
          <span class="text-[10px] text-gray-400">Próximamente</span>
        </div>

        <div class="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm flex flex-col items-center gap-2 text-center opacity-50">
          <div class="w-12 h-12 rounded-xl bg-violet-50 flex items-center justify-center">
            <svg class="w-6 h-6 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </div>
          <span class="text-xs font-semibold text-gray-700">Notificaciones</span>
          <span class="text-[10px] text-gray-400">Próximamente</span>
        </div>

      </div>

      <!-- Info de sesión (debug — quitar en producción) -->
      <div v-if="auth.usuario" class="mt-6 p-3 bg-white rounded-xl border border-gray-100 text-xs text-gray-400">
        <p><span class="font-medium text-gray-600">Rol:</span> {{ auth.usuario.rol }}</p>
        <p><span class="font-medium text-gray-600">Email:</span> {{ auth.usuario.email }}</p>
        <p><span class="font-medium text-gray-600">Empresa ID:</span> {{ auth.usuario.empresa }}</p>
      </div>
    </main>
  </div>
</template>
