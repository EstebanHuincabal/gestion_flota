<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const alertas = ref([])

const agregar = (mensaje) => {
  const id = Date.now() + Math.random()
  alertas.value.push({ id, mensaje, saliendo: false })
  setTimeout(() => cerrar(id), 4000)
}

const cerrar = (id) => {
  const alerta = alertas.value.find(a => a.id === id)
  if (!alerta) return
  alerta.saliendo = true
  setTimeout(() => {
    alertas.value = alertas.value.filter(a => a.id !== id)
  }, 300)
}

const onPermisoDenegado = (e) => agregar(e.detail)

onMounted(() => window.addEventListener('permiso-denegado', onPermisoDenegado))
onUnmounted(() => window.removeEventListener('permiso-denegado', onPermisoDenegado))
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="alerta in alertas"
          :key="alerta.id"
          class="toast"
          :class="{ saliendo: alerta.saliendo }"
          @click="cerrar(alerta.id)"
        >
          <div class="toast-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 15v2m0 0v2m0-2h2m-2 0H10m2-5V7m-7 10a7 7 0 1114 0H5z"/>
            </svg>
          </div>
          <div class="toast-body">
            <p class="toast-titulo">Sin permisos</p>
            <p class="toast-mensaje">{{ alerta.mensaje }}</p>
          </div>
          <button class="toast-cerrar" @click.stop="cerrar(alerta.id)">
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
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: #fff;
  border: 1px solid #FED7AA;
  border-left: 4px solid #F97316;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-width: 340px;
  cursor: pointer;
  pointer-events: all;
  font-family: 'Inter', system-ui, sans-serif;
}

.toast-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  background: #FFF7ED;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #F97316;
}
.toast-icon svg { width: 16px; height: 16px; }

.toast-body { flex: 1; min-width: 0; }
.toast-titulo {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0 0 0.125rem;
}
.toast-mensaje {
  font-size: 0.8125rem;
  color: #6B7280;
  margin: 0;
  line-height: 1.4;
}

.toast-cerrar {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: #9CA3AF;
  padding: 0;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.toast-cerrar:hover { color: #374151; }
.toast-cerrar svg { width: 14px; height: 14px; }

/* Transiciones */
.toast-enter-active { transition: all 0.25s ease; }
.toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from  { opacity: 0; transform: translateX(100%); }
.toast-leave-to    { opacity: 0; transform: translateX(100%); }
</style>
