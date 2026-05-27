<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()
const route  = useRoute()
const suscripcion = ref(null)
let intervalo = null

async function cargar() {
  try {
    const res  = await apiFetch('/api/empresa/suscripcion/')
    if (!res.ok) return
    const data = await res.json()
    suscripcion.value = data.suscripcion
  } catch {}
}

onMounted(() => {
  cargar()
  intervalo = setInterval(cargar, 10 * 60 * 1000) // cada 10 minutos

  // Escuchar evento 402 emitido desde api.js
  window.addEventListener('suscripcion-bloqueada', onBloqueada)
})

onUnmounted(() => {
  clearInterval(intervalo)
  window.removeEventListener('suscripcion-bloqueada', onBloqueada)
})

function onBloqueada() {
  if (!enPaginaPago.value) {
    router.push('/empresa/pago')
  }
}

const mostrarBanner = computed(() => {
  if (!suscripcion.value) return false
  return suscripcion.value.estado === 'gracia' ||
    (suscripcion.value.estado === 'activa' && suscripcion.value.dias_para_vencer !== null && suscripcion.value.dias_para_vencer <= 7)
})

// No mostrar el overlay si el usuario ya está en la página de pago
const enPaginaPago = computed(() => route.path.startsWith('/empresa/pago'))

const mostrarOverlay = computed(() =>
  !enPaginaPago.value && (
    suscripcion.value?.estado === 'suspendida' ||
    suscripcion.value?.estado === 'pendiente'
  )
)

const overlayEsPendiente = computed(() =>
  suscripcion.value?.estado === 'pendiente'
)

const mensajeBanner = computed(() => {
  if (!suscripcion.value) return ''
  if (suscripcion.value.estado === 'gracia') {
    const d = suscripcion.value.dias_para_vencer
    return `Tu suscripción venció. Tienes ${d !== null ? Math.abs(d) : '?'} días para pagar antes de que el servicio sea suspendido.`
  }
  const d = suscripcion.value.dias_para_vencer
  return `Tu suscripción vence en ${d} día${d === 1 ? '' : 's'}.`
})
</script>

<template>
  <!-- Banner naranja/amarillo -->
  <div v-if="mostrarBanner" :class="['suscripcion-banner', suscripcion.estado === 'gracia' ? 'naranja' : 'amarillo']">
    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
    </svg>
    <span>{{ mensajeBanner }}</span>
    <button class="banner-btn" @click="router.push('/empresa/pago')">
      {{ suscripcion.estado === 'gracia' ? 'Pagar ahora' : 'Renovar' }}
    </button>
  </div>

  <!-- Overlay bloqueante para pendiente y suspendida -->
  <div v-if="mostrarOverlay" class="suspension-overlay">
    <div class="suspension-box">
      <div class="suspension-icon">{{ overlayEsPendiente ? '💳' : '⚠' }}</div>
      <h2>{{ overlayEsPendiente ? 'Pago pendiente' : 'Servicio suspendido' }}</h2>
      <p>
        <template v-if="overlayEsPendiente">
          Tu empresa aún no ha realizado el primer pago del plan. Debes pagar para acceder al sistema.
        </template>
        <template v-else>
          Tu cuenta ha sido suspendida por falta de pago. Regulariza tu situación para continuar.
        </template>
      </p>
      <button class="suspension-btn" :class="{ pendiente: overlayEsPendiente }" @click="router.push('/empresa/pago')">
        {{ overlayEsPendiente ? 'Realizar pago' : 'Regularizar pago' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.suscripcion-banner {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.625rem 1.5rem; font-size: 0.875rem; font-weight: 500;
}
.suscripcion-banner.naranja { background: #FEF3C7; color: #92400E; border-bottom: 1px solid #FDE68A; }
.suscripcion-banner.amarillo{ background: #FFFBEB; color: #78350F; border-bottom: 1px solid #FDE68A; }
.suscripcion-banner span    { flex: 1; }
.banner-btn {
  padding: 0.3rem 0.875rem; background: #D97706; color: #fff;
  border: none; border-radius: 6px; font-size: 0.8125rem; font-weight: 600;
  cursor: pointer; font-family: inherit; white-space: nowrap;
}
.banner-btn:hover { background: #B45309; }

.suspension-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  z-index: 9999; display: flex; align-items: center; justify-content: center;
}
.suspension-box {
  background: #fff; border-radius: 16px; padding: 2.5rem 3rem;
  max-width: 420px; width: 90%; text-align: center;
}
.suspension-icon {
  font-size: 2.5rem; margin-bottom: 1rem;
}
.suspension-box h2 { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.suspension-box p  { font-size: 0.9rem; color: #4B5563; margin: 0 0 1.5rem; line-height: 1.5; }
.suspension-btn {
  width: 100%; padding: 0.75rem; background: #DC2626; color: #fff;
  border: none; border-radius: 10px; font-size: 0.9375rem; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.suspension-btn:hover         { background: #B91C1C; }
.suspension-btn.pendiente     { background: #4F46E5; }
.suspension-btn.pendiente:hover { background: #4338CA; }
</style>
