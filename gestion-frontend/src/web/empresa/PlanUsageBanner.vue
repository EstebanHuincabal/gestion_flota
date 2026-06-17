<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const datos    = ref(null)
const expandido = ref(false)
let intervalo  = null

const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const esSuperadmin = usuario.rol === 'SUPERADMIN'

const ETIQUETAS = {
  vehiculos:   'Vehículos',
  conductores: 'Conductores',
  usuarios:    'Usuarios',
}

const suscripcionPendiente = computed(() =>
  datos.value?.suscripcion?.estado === 'pendiente'
)

const alertas = computed(() => {
  if (!datos.value?.alertas) return []
  if (suscripcionPendiente.value) return []
  return datos.value.alertas
})

const dimensionesCompletas = computed(() => {
  if (!datos.value?.uso) return []
  return Object.entries(datos.value.uso).map(([key, val]) => ({
    key,
    label: ETIQUETAS[key] || key,
    ...val,
    nivel: val.pct >= 100 ? 'danger' : val.pct >= 80 ? 'warning' : 'ok',
  }))
})

const colorPct = (pct) => {
  if (pct >= 100) return '#DC2626'
  if (pct >= 80)  return '#D97706'
  return '#16A34A'
}

const cargar = async () => {
  try {
    const res = await apiFetch('/api/empresa/plan-uso/')
    if (res.ok) datos.value = await res.json()
  } catch {}
}

onMounted(() => {
  if (esSuperadmin) return
  cargar()
  intervalo = setInterval(cargar, 5 * 60 * 1000)
})

onUnmounted(() => {
  if (intervalo) clearInterval(intervalo)
})
</script>

<template>
  <div v-if="!esSuperadmin && alertas.length" class="banner-wrap">

    <div
      v-for="alerta in alertas"
      :key="alerta.dimension"
      :class="['banner-fila', alerta.nivel]"
      @click="expandido = !expandido"
    >
      <svg class="banner-ico" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <span class="banner-texto">
        <strong>{{ ETIQUETAS[alerta.dimension] || alerta.dimension }}:</strong>
        {{ alerta.actual }} de {{ alerta.limite }} usados
      </span>
      <div class="banner-barra-wrap">
        <div class="banner-barra-track">
          <div class="banner-barra-fill"
            :style="{ width: Math.min(alerta.pct, 100) + '%', background: colorPct(alerta.pct) }"/>
        </div>
      </div>
      <span class="banner-pct" :style="{ color: colorPct(alerta.pct) }">{{ alerta.pct }}%</span>
      <svg class="expand-ico" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          :d="expandido ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'"/>
      </svg>
    </div>

    <div v-if="expandido && dimensionesCompletas.length" class="panel-expandido">
      <div v-for="dim in dimensionesCompletas" :key="dim.key" class="dim-fila">
        <span class="dim-label">{{ dim.label }}</span>
        <span class="dim-conteo">{{ dim.actual }} / {{ dim.limite }}</span>
        <div class="dim-track">
          <div class="dim-fill"
            :style="{ width: Math.min(dim.pct, 100) + '%', background: colorPct(dim.pct) }"/>
        </div>
        <span class="dim-pct" :style="{ color: colorPct(dim.pct) }">{{ dim.pct }}%</span>
      </div>
    </div>

  </div>
</template>

<style scoped>
.banner-wrap { display: flex; flex-direction: column; gap: 0; padding: 0.75rem 1.5rem 0; }

.banner-fila {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.625rem 1rem; border-radius: 8px; cursor: pointer;
  font-size: 0.8125rem; margin-bottom: 4px;
}
.banner-fila.warning { background: #FFF7ED; border: 1px solid #FED7AA; color: #92400E; }
.banner-fila.danger  { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }

.banner-ico { width: 16px; height: 16px; flex-shrink: 0; }
.banner-texto { flex: 1; line-height: 1.4; }
.banner-barra-wrap { width: 120px; flex-shrink: 0; }
.banner-barra-track { height: 6px; background: rgba(0,0,0,0.12); border-radius: 100px; overflow: hidden; }
.banner-barra-fill  { height: 100%; border-radius: 100px; transition: width 0.4s; }
.banner-pct { font-weight: 700; font-size: 0.8125rem; min-width: 36px; text-align: right; }
.expand-ico { width: 16px; height: 16px; flex-shrink: 0; opacity: 0.6; }

.panel-expandido {
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 0.875rem 1rem; margin-bottom: 4px;
  display: flex; flex-direction: column; gap: 0.625rem;
}
.dim-fila { display: flex; align-items: center; gap: 0.75rem; font-size: 0.8125rem; }
.dim-label { width: 90px; color: #374151; font-weight: 500; flex-shrink: 0; }
.dim-conteo { width: 70px; color: #6B7280; text-align: right; flex-shrink: 0; }
.dim-track { flex: 1; height: 8px; background: #E5E7EB; border-radius: 100px; overflow: hidden; }
.dim-fill  { height: 100%; border-radius: 100px; transition: width 0.4s; }
.dim-pct   { width: 36px; text-align: right; font-weight: 600; font-size: 0.8125rem; flex-shrink: 0; }
</style>
