<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router      = useRouter()
const orden       = ref('')
const suscripcion = ref(null)
const esNuevo     = ref(false)   // true cuando viene del auto-registro

onMounted(async () => {
  const params  = new URLSearchParams(window.location.search)
  orden.value   = params.get('orden') || ''
  esNuevo.value = params.get('nuevo') === '1'

  try {
    const res  = await apiFetch('/api/empresa/suscripcion/')
    if (res.ok) {
      const data = await res.json()
      suscripcion.value = data.suscripcion
    }
  } catch {}
})
</script>

<template>
  <div class="exito-page">
    <div class="exito-card">
      <div class="exito-icon">✓</div>
      <h1 class="exito-title">
        {{ esNuevo ? '¡Bienvenido a FlotaSystem!' : '¡Pago realizado con éxito!' }}
      </h1>
      <p class="exito-sub">
        {{ esNuevo
            ? 'Tu empresa ya está activa. Recibirás un email de bienvenida con los detalles de tu cuenta.'
            : 'Tu suscripción ha sido activada correctamente.' }}
      </p>

      <div v-if="orden" class="detalle-row">
        <span class="detalle-label">N° de orden</span>
        <span class="detalle-val">{{ orden }}</span>
      </div>

      <template v-if="suscripcion">
        <div class="detalle-row">
          <span class="detalle-label">Plan</span>
          <span class="detalle-val">{{ suscripcion.plan }}</span>
        </div>
        <div class="detalle-row">
          <span class="detalle-label">Estado</span>
          <span class="badge-activa">Activa</span>
        </div>
        <div v-if="suscripcion.fecha_fin_periodo" class="detalle-row">
          <span class="detalle-label">Próximo cobro</span>
          <span class="detalle-val">{{ suscripcion.fecha_fin_periodo }}</span>
        </div>
      </template>

      <button class="btn-panel" @click="router.push('/empresa/dashboard')">
        Ir al panel →
      </button>
    </div>
  </div>
</template>

<style scoped>
.exito-page { display: flex; align-items: center; justify-content: center; min-height: 70vh; padding: 2rem; }
.exito-card {
  background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  padding: 2.5rem; max-width: 440px; width: 100%; text-align: center;
}
.exito-icon {
  width: 60px; height: 60px; border-radius: 50%;
  background: #D1FAE5; color: #065F46; font-size: 1.75rem;
  display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; font-weight: 700;
}
.exito-title { font-size: 1.375rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.exito-sub   { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.5rem; }

.detalle-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 0; border-bottom: 1px solid #F3F4F6; font-size: 0.875rem;
}
.detalle-label { color: #6B7280; }
.detalle-val   { font-weight: 600; color: #111827; }
.badge-activa  {
  background: #D1FAE5; color: #065F46; font-size: 0.75rem;
  font-weight: 600; padding: 2px 10px; border-radius: 99px;
}

.btn-panel {
  margin-top: 1.75rem; width: 100%; padding: 0.75rem;
  background: #4F46E5; color: #fff; border: none; border-radius: 10px;
  font-size: 0.9375rem; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: background 0.15s;
}
.btn-panel:hover { background: #4338CA; }
</style>
