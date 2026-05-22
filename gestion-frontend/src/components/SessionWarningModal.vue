<script setup>
import { computed } from 'vue'

const props = defineProps({
  segundosRestantes: { type: Number, default: 120 },
})
const emit = defineEmits(['extender', 'cerrar'])

const tiempoFormateado = computed(() => {
  const s   = Math.max(0, props.segundosRestantes)
  const min = Math.floor(s / 60)
  const sec = s % 60
  return `${min}:${String(sec).padStart(2, '0')}`
})
</script>

<template>
  <Teleport to="body">
    <div class="session-overlay">
      <div class="session-modal" role="alertdialog" aria-modal="true">

        <div class="modal-icon">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>

        <h2 class="modal-title">Tu sesión está por expirar</h2>
        <p class="modal-desc">La sesión se cerrará automáticamente en</p>
        <div class="modal-countdown">{{ tiempoFormateado }}</div>
        <p class="modal-hint">¿Deseas mantener la sesión activa?</p>

        <div class="modal-actions">
          <button class="btn-extend" @click="emit('extender')">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Extender sesión
          </button>
          <button class="btn-logout" @click="emit('cerrar')">
            Cerrar sesión
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.session-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(3px);
}

.session-modal {
  background: #fff;
  border-radius: 18px;
  padding: 2.25rem 2rem;
  width: min(400px, calc(100vw - 2rem));
  text-align: center;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.22);
  animation: appear 0.22s ease;
}

@keyframes appear {
  from { opacity: 0; transform: scale(0.94) translateY(-10px); }
  to   { opacity: 1; transform: scale(1)    translateY(0);     }
}

.modal-icon {
  width: 60px; height: 60px;
  background: #FEF3C7;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 1.25rem;
}
.modal-icon svg { width: 30px; height: 30px; color: #D97706; }

.modal-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.5rem;
}

.modal-desc {
  font-size: 0.9375rem;
  color: #6B7280;
  margin: 0;
}

.modal-countdown {
  font-size: 3rem;
  font-weight: 800;
  color: #DC2626;
  letter-spacing: -0.02em;
  margin: 0.875rem 0 0.25rem;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.modal-hint {
  font-size: 0.875rem;
  color: #6B7280;
  margin: 0 0 1.75rem;
}

.modal-actions {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.btn-extend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.8rem 1.5rem;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  font-family: inherit;
}
.btn-extend:hover { opacity: 0.9; }
.btn-extend svg { width: 17px; height: 17px; }

.btn-logout {
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  border: 1px solid #E5E7EB;
  background: #fff;
  color: #6B7280;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  font-family: inherit;
}
.btn-logout:hover { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }
</style>
