<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Preferences } from '@capacitor/preferences'

const router     = useRouter()
const planNombre = ref('')

onMounted(async () => {
  const { value } = await Preferences.get({ key: 'plan_nombre' })
  planNombre.value = value || ''
})
</script>

<template>
  <div class="modulo-wrap">
    <!-- Icono de candado -->
    <div class="lock-circle">
      <svg class="lock-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0110 0v4"/>
      </svg>
    </div>

    <p class="titulo">Módulo no disponible</p>

    <p class="subtitulo">
      Tu empresa no tiene acceso a este módulo en el plan actual.
      Contacta al administrador para más información.
    </p>

    <p v-if="planNombre" class="plan-label">
      Plan actual: <strong>{{ planNombre }}</strong>
    </p>

    <!-- Acciones -->
    <div class="acciones">
      <button @click="router.push('/solicitudes')" class="btn-principal">
        Ir a Solicitudes
      </button>
      <button @click="router.back()" class="btn-secundario">
        Volver
      </button>
    </div>
  </div>
</template>

<style scoped>
.modulo-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: max(2rem, env(safe-area-inset-top)) 1.5rem
           max(2rem, env(safe-area-inset-bottom));
  text-align: center;
  background: #F9FAFB;
}

.lock-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: white;
  border: 1px solid #F3F4F6;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}

.lock-icon {
  width: 32px;
  height: 32px;
  color: #9CA3AF;
}

.titulo {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1F2937;
  margin: 0 0 0.625rem;
}

.subtitulo {
  font-size: 0.875rem;
  color: #6B7280;
  max-width: 280px;
  line-height: 1.55;
  margin: 0 0 1rem;
}

.plan-label {
  font-size: 0.75rem;
  color: #9CA3AF;
  margin: 0 0 2rem;
}

.acciones {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
  max-width: 280px;
}

.btn-principal {
  width: 100%;
  padding: 0.875rem 1.5rem;
  border-radius: 0.875rem;
  background: var(--gradient-primary);
  color: white;
  font-size: 0.9375rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.btn-principal:active { opacity: 0.85; }

.btn-secundario {
  width: 100%;
  padding: 0.875rem 1.5rem;
  border-radius: 0.875rem;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid #E5E7EB;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.btn-secundario:active { background: #F9FAFB; }
</style>
