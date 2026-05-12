<script setup>
defineProps({
  titulo:    { type: String, default: '¿Estás seguro?' },
  mensaje:   { type: String, default: '' },
  labelOk:   { type: String, default: 'Confirmar' },
  peligroso: { type: Boolean, default: false },
})
defineEmits(['confirmar', 'cancelar'])
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('cancelar')">
      <div class="modal" role="dialog" aria-modal="true">

        <!-- Icono -->
        <div :class="['icon-wrap', peligroso ? 'icon-danger' : 'icon-info']">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="peligroso" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>

        <h3 class="titulo">{{ titulo }}</h3>
        <p class="mensaje">{{ mensaje }}</p>

        <div class="acciones">
          <button class="btn-cancel" @click="$emit('cancelar')">Cancelar</button>
          <button :class="['btn-ok', peligroso ? 'btn-danger' : 'btn-primary']" @click="$emit('confirmar')">
            {{ labelOk }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fade-in 0.15s ease;
}

.modal {
  background: #fff;
  border-radius: 18px;
  padding: 2rem;
  width: 100%;
  max-width: 380px;
  margin: 1rem;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  animation: slide-up 0.2s ease;
}

.icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}
.icon-wrap svg { width: 26px; height: 26px; }

.icon-danger { background: #FEF2F2; color: #DC2626; }
.icon-info   { background: #EEF2FF; color: #4F46E5; }

.titulo {
  font-size: 1.0625rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.5rem;
}

.mensaje {
  font-size: 0.875rem;
  color: #6B7280;
  margin: 0 0 1.75rem;
  line-height: 1.5;
}

.acciones {
  display: flex;
  gap: 0.75rem;
  width: 100%;
}

.btn-cancel, .btn-ok {
  flex: 1;
  padding: 0.65rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
  border: none;
}

.btn-cancel {
  background: #F3F4F6;
  color: #374151;
  border: 1.5px solid #E5E7EB;
}
.btn-cancel:hover { background: #E5E7EB; }

.btn-danger {
  background: #DC2626;
  color: #fff;
  box-shadow: 0 2px 8px rgba(220,38,38,0.3);
}
.btn-danger:hover { background: #B91C1C; }

.btn-primary {
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79,70,229,0.3);
}
.btn-primary:hover { opacity: 0.9; }

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes slide-up {
  from { opacity: 0; transform: translateY(12px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
