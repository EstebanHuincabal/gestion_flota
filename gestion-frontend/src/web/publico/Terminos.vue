<script setup>
import { ref, onMounted } from 'vue'

const cargando = ref(true)
const terminos = ref('')
const version  = ref('')
const fecha    = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/terminos/')
    if (res.ok) {
      const data = await res.json()
      terminos.value = data.terminos || ''
      version.value  = data.version  || ''
      fecha.value    = data.fecha    || ''
    }
  } catch {}
  cargando.value = false
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 pt-24 pb-16">
    <div class="max-w-3xl mx-auto px-6">

      <div class="mb-8">
        <h1 class="text-3xl font-extrabold text-gray-900 tracking-tight mb-2">
          Términos y condiciones
        </h1>
        <p v-if="version || fecha" class="text-sm text-gray-400">
          <span v-if="version">Versión {{ version }}</span>
          <span v-if="version && fecha"> · </span>
          <span v-if="fecha">Actualizado el {{ fecha }}</span>
        </p>
      </div>

      <!-- Cargando -->
      <div v-if="cargando" class="space-y-4">
        <div v-for="i in 6" :key="i" class="h-4 bg-gray-200 rounded animate-pulse" :style="`width: ${70 + (i % 3) * 10}%`"/>
      </div>

      <!-- Sin contenido -->
      <div
        v-else-if="!terminos"
        class="bg-white rounded-2xl border border-gray-100 p-12 text-center"
      >
        <svg class="w-10 h-10 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
        </svg>
        <p class="text-gray-500 text-sm">Los términos y condiciones aún no han sido publicados.</p>
        <p class="text-gray-400 text-xs mt-1">El administrador del sistema debe configurarlos desde el panel.</p>
      </div>

      <!-- Contenido -->
      <div
        v-else
        class="bg-white rounded-2xl border border-gray-100 p-8 prose prose-gray max-w-none text-sm leading-relaxed whitespace-pre-wrap text-gray-700"
      >{{ terminos }}</div>

    </div>
  </div>
</template>
