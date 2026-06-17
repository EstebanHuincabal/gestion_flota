<script setup>
import { ref, onMounted, computed } from 'vue'
import { apiFetch } from '../utils/api.js'

const datos    = ref(null)
const cargando = ref(true)

const suscripcionPendiente = computed(() =>
  datos.value?.suscripcion?.estado === 'pendiente'
)

const alertas = computed(() => {
  if (!datos.value?.uso) return []
  if (suscripcionPendiente.value) return []
  const resultado = []
  const etiquetas = {
    vehiculos:   'vehículos',
    conductores: 'conductores',
    usuarios:    'usuarios',
  }
  for (const [key, val] of Object.entries(datos.value.uso)) {
    if (val.limite >= 9999) continue
    if (val.pct >= 100) {
      resultado.push({ key, label: etiquetas[key], ...val, nivel: 'critico' })
    } else if (val.pct >= 80) {
      resultado.push({ key, label: etiquetas[key], ...val, nivel: 'advertencia' })
    }
  }
  return resultado
})

onMounted(async () => {
  try {
    const res = await apiFetch('/api/empresa/plan-uso/')
    if (res.ok) datos.value = await res.json()
  } catch {}
  cargando.value = false
})
</script>

<template>
  <div v-if="!cargando && alertas.length" class="banner-wrap">
    <div
      v-for="alerta in alertas"
      :key="alerta.key"
      :class="['banner', alerta.nivel]"
    >
      <svg class="banner-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <span class="banner-text">
        <template v-if="alerta.nivel === 'critico'">
          Has alcanzado el límite de <strong>{{ alerta.label }}</strong> de tu plan
          <strong>{{ datos.plan?.nombre_display }}</strong>
          ({{ alerta.actual }}/{{ alerta.limite }}).
        </template>
        <template v-else>
          Estás usando el <strong>{{ alerta.pct }}%</strong> de tu límite de
          <strong>{{ alerta.label }}</strong>
          ({{ alerta.actual }}/{{ alerta.limite }}).
        </template>
      </span>
    </div>
  </div>
</template>

<style scoped>
.banner-wrap { display: flex; flex-direction: column; gap: 0.5rem; padding: 0.75rem 1.5rem 0; }
.banner {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.625rem 1rem; border-radius: 8px;
  font-size: 0.8125rem;
}
.banner.advertencia { background: #FFF7ED; border: 1px solid #FED7AA; color: #92400E; }
.banner.critico     { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }
.banner-icon { width: 16px; height: 16px; flex-shrink: 0; }
.banner-text { line-height: 1.4; }
</style>
