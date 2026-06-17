<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router  = useRouter()
const visible = ref(false)
const detalle = ref(null)

const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const esSuperadmin = usuario.rol === 'SUPERADMIN'

const abrir = (event) => {
  detalle.value = event.detail
  visible.value = true
}

const cerrar = () => {
  visible.value = false
  detalle.value = null
}

const irAPlanes = () => {
  cerrar()
  if (esSuperadmin) {
    router.push('/planes')
  }
}

onMounted(() => {
  window.addEventListener('limite-plan', abrir)
  window.addEventListener('modulo-bloqueado', abrir)
})
onUnmounted(() => {
  window.removeEventListener('limite-plan', abrir)
  window.removeEventListener('modulo-bloqueado', abrir)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="overlay" @click.self="cerrar">
        <div class="modal">
          <!-- Ícono -->
          <div class="modal-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>

          <h2 class="modal-title">Límite del plan alcanzado</h2>

          <p class="modal-msg">{{ detalle?.error || 'Has alcanzado un límite de tu plan actual.' }}</p>

          <div v-if="detalle?.uso !== undefined" class="uso-info">
            <span class="uso-badge">Uso: {{ detalle.uso }} / {{ detalle.limite }}</span>
            <span v-if="detalle.plan" class="plan-badge">Plan {{ detalle.plan }}</span>
          </div>

          <div class="modal-actions">
            <button class="btn-secondary" @click="cerrar">Entendido</button>
            <button v-if="esSuperadmin" class="btn-primary" @click="irAPlanes">
              Ver planes
            </button>
            <p v-else class="contact-msg">
              Contacta a tu administrador para actualizar el plan.
            </p>
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
  background: #FEF2F2; margin: 0 auto 1.25rem;
  display: flex; align-items: center; justify-content: center;
}
.modal-icon svg { width: 28px; height: 28px; color: #DC2626; }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.modal-msg { font-size: 0.875rem; color: #6B7280; margin: 0 0 1rem; line-height: 1.6; }
.uso-info {
  display: flex; gap: 0.5rem; justify-content: center;
  margin-bottom: 1.5rem; flex-wrap: wrap;
}
.uso-badge {
  padding: 0.25rem 0.75rem; background: #FEE2E2; color: #B91C1C;
  border-radius: 100px; font-size: 0.8125rem; font-weight: 600;
}
.plan-badge {
  padding: 0.25rem 0.75rem; background: #EEF2FF; color: #4338CA;
  border-radius: 100px; font-size: 0.8125rem; font-weight: 600;
}
.modal-actions { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.btn-secondary {
  padding: 0.6rem 1.25rem; border: 1.5px solid #E5E7EB;
  background: #fff; color: #374151; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: #F9FAFB; }
.btn-primary {
  padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.9; }
.contact-msg { font-size: 0.8125rem; color: #6B7280; margin: 0; align-self: center; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
