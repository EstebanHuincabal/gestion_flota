<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const toasts = ref([])
let nextId = 0

const agregar = (mensaje, tipo = 'info', duracion = 4000) => {
  const id = ++nextId
  toasts.value.push({ id, mensaje, tipo })
  setTimeout(() => eliminar(id), duracion)
}

const eliminar = (id) => {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

const onGlobalToast = (e) => agregar(e.detail.msg, e.detail.tipo)

onMounted(()   => window.addEventListener('app-toast', onGlobalToast))
onUnmounted(() => window.removeEventListener('app-toast', onGlobalToast))

defineExpose({ agregar })
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="['toast', `toast-${t.tipo}`]"
        >
          <!-- Icono -->
          <div class="toast-icon">
            <svg v-if="t.tipo === 'error'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <svg v-else-if="t.tipo === 'success'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>

          <span class="toast-msg">{{ t.mensaje }}</span>

          <button class="toast-close" @click="eliminar(t.id)">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-radius: 12px;
  min-width: 280px;
  max-width: 380px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
  pointer-events: all;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
}

.toast-error   { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }
.toast-success { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; }
.toast-info    { background: #EEF2FF; border: 1px solid #C7D2FE; color: #3730A3; }

.toast-icon { flex-shrink: 0; }
.toast-icon svg { width: 18px; height: 18px; }

.toast-msg { flex: 1; line-height: 1.4; }

.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  color: inherit;
  opacity: 0.5;
  transition: opacity 0.15s;
}
.toast-close:hover { opacity: 1; }
.toast-close svg { width: 14px; height: 14px; display: block; }

/* Animación */
.toast-enter-active { transition: all 0.25s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from  { opacity: 0; transform: translateX(24px); }
.toast-leave-to    { opacity: 0; transform: translateX(24px); }
</style>
