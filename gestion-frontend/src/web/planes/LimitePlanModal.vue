<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const detalle = ref(null)

const pct = computed(() => {
  if (!detalle.value) return 0
  if (detalle.value.porcentaje !== undefined) return Math.min(detalle.value.porcentaje, 100)
  if (detalle.value.limite > 0) return Math.min(Math.round(detalle.value.uso / detalle.value.limite * 100), 100)
  return 100
})

const colorBarra = computed(() => {
  if (pct.value >= 100) return '#DC2626'
  if (pct.value >= 80)  return '#D97706'
  return '#16A34A'
})

const abrir = (event) => {
  detalle.value = event.detail
  visible.value = true
}

const cerrar = () => {
  visible.value = false
  detalle.value = null
}

onMounted(() => {
  window.addEventListener('limite-plan', abrir)
})
onUnmounted(() => {
  window.removeEventListener('limite-plan', abrir)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="overlay" @click.self="cerrar">
        <div class="modal">

          <div class="modal-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
          </div>

          <h2 class="modal-title">Límite del plan alcanzado</h2>

          <p class="modal-msg">{{ detalle?.error || 'Has alcanzado un límite de tu plan actual.' }}</p>

          <div v-if="detalle?.uso !== undefined" class="progress-wrap">
            <div class="progress-labels">
              <span class="progress-label-left">{{ detalle.uso }} / {{ detalle.limite }}</span>
              <span class="progress-label-right" :style="{ color: colorBarra }">{{ pct }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: pct + '%', background: colorBarra }"/>
            </div>
            <p v-if="detalle.dimension" class="progress-dim">{{ detalle.dimension }}</p>
          </div>

          <div v-if="detalle?.plan" class="plan-pill">
            Plan {{ detalle.plan }}
          </div>

          <p class="contact-msg">
            Contacta al administrador de tu sistema para actualizar el plan.
          </p>

          <div class="modal-actions">
            <button class="btn-primary" @click="cerrar">Entendido</button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 9000;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.modal {
  background: #fff; border-radius: 16px;
  padding: 2rem; max-width: 420px; width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  text-align: center;
}
.modal-icon {
  width: 56px; height: 56px; border-radius: 50%;
  background: #FFF7ED; margin: 0 auto 1.25rem;
  display: flex; align-items: center; justify-content: center;
}
.modal-icon svg { width: 28px; height: 28px; color: #D97706; }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.modal-msg { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.25rem; line-height: 1.6; }

.progress-wrap { margin-bottom: 1rem; }
.progress-labels {
  display: flex; justify-content: space-between;
  font-size: 0.8125rem; font-weight: 600; margin-bottom: 0.375rem;
  color: #374151;
}
.progress-label-right { font-weight: 700; }
.progress-track {
  height: 10px; background: #E5E7EB; border-radius: 100px; overflow: hidden;
}
.progress-bar {
  height: 100%; border-radius: 100px;
  transition: width 0.4s ease;
}
.progress-dim {
  font-size: 0.75rem; color: #9CA3AF; text-transform: capitalize;
  margin: 0.375rem 0 0; text-align: left;
}

.plan-pill {
  display: inline-block; margin-bottom: 1rem;
  padding: 0.25rem 0.875rem;
  background: #EEF2FF; color: #4338CA;
  border-radius: 100px; font-size: 0.8125rem; font-weight: 600;
}
.contact-msg { font-size: 0.8125rem; color: #6B7280; margin: 0 0 1.5rem; line-height: 1.5; }

.modal-actions { display: flex; justify-content: center; }
.btn-primary {
  padding: 0.6rem 1.75rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
  transition: opacity 0.15s; font-family: inherit;
}
.btn-primary:hover { opacity: 0.9; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
