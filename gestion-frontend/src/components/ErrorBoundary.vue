<template>
  <slot v-if="!tieneError" />
  <div v-else style="padding:48px 24px; text-align:center; max-width:480px; margin:0 auto;">
    <i class="ti ti-alert-triangle" style="font-size:40px; color:#ef4444;"></i>
    <p style="font-size:16px; font-weight:600; margin:16px 0 6px; color:#1a1a1a;">Algo salió mal</p>
    <p style="font-size:14px; color:#6b7280; margin:0 0 20px;">{{ mensajeError }}</p>
    <button
      @click="reintentar"
      style="padding:8px 20px; background:#4f46e5; color:#fff; border:none; border-radius:8px; font-size:14px; cursor:pointer;"
    >
      Reintentar
    </button>
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'

const tieneError   = ref(false)
const mensajeError = ref('')

onErrorCaptured((error) => {
  tieneError.value   = true
  mensajeError.value = error.message || 'Error inesperado en la interfaz.'
  return false
})

function reintentar() {
  tieneError.value = false
}
</script>
