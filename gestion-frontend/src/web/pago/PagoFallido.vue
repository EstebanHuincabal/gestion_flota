<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const codigoError = ref('')

const MENSAJES = {
  rechazado:     'Tu pago fue rechazado. Verifica los datos de tu tarjeta e intenta nuevamente.',
  sin_token:     'Ocurrió un error en la sesión de pago. Por favor intenta nuevamente.',
  token_invalido:'El token de pago no es válido. Inicia el proceso nuevamente.',
  error_sistema: 'Error del sistema. Por favor intenta más tarde o contacta soporte.',
}

const mensaje = computed(() => MENSAJES[codigoError.value] || 'Hubo un problema con tu pago. Intenta nuevamente.')

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  codigoError.value = params.get('error') || ''
})
</script>

<template>
  <div class="fallido-page">
    <div class="fallido-card">
      <div class="fallido-icon">✕</div>
      <h1 class="fallido-title">Pago no procesado</h1>
      <p class="fallido-msg">{{ mensaje }}</p>

      <div class="fallido-actions">
        <button class="btn-reintentar" @click="router.push('/empresa/pago')">
          Reintentar pago
        </button>
        <button class="btn-panel" @click="router.push('/empresa/dashboard')">
          Volver al panel
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fallido-page { display: flex; align-items: center; justify-content: center; min-height: 70vh; padding: 2rem; }
.fallido-card {
  background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  padding: 2.5rem; max-width: 440px; width: 100%; text-align: center;
}
.fallido-icon {
  width: 60px; height: 60px; border-radius: 50%;
  background: #FEE2E2; color: #DC2626; font-size: 1.5rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem;
}
.fallido-title { font-size: 1.375rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.fallido-msg   { font-size: 0.9rem; color: #4B5563; margin: 0 0 1.75rem; line-height: 1.5; }

.fallido-actions { display: flex; flex-direction: column; gap: 0.75rem; }
.btn-reintentar {
  padding: 0.7rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 10px; font-size: 0.9375rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-reintentar:hover { background: #4338CA; }
.btn-panel {
  padding: 0.7rem; background: #fff; color: #374151; border: 1px solid #E5E7EB;
  border-radius: 10px; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-panel:hover { background: #F9FAFB; }
</style>
