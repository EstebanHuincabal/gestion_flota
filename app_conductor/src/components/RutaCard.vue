<script setup>
import { formatDuracion, formatFechaRuta } from '@/utils/formato.js'

const props = defineProps({
  ruta:     { type: Object,  required: true },
  variante: { type: String,  default: 'pendiente' }, // 'activa' | 'pendiente' | 'finalizada'
})

const emit = defineEmits(['click'])
</script>

<template>
  <!-- ── ACTIVA (tarjeta héroe con gradiente) ──────────────────────────────── -->
  <div
    v-if="variante === 'activa'"
    class="card-activa"
    @click="emit('click', ruta.id)"
  >
    <!-- Decoración de fondo -->
    <div class="card-activa-deco" aria-hidden="true"/>

    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
      <span class="activa-badge">
        <span class="activa-dot"/>
        En curso
      </span>
      <span class="text-[11px] font-semibold text-white/70 bg-white/10 rounded-full px-2.5 py-0.5 border border-white/15">
        {{ ruta.tipo === 'carga' ? '📦 Carga' : '👥 Personas' }}
      </span>
    </div>

    <!-- Nombre -->
    <p class="text-white font-bold text-lg leading-tight mb-1">{{ ruta.nombre }}</p>

    <!-- Métricas -->
    <p class="text-white/65 text-sm mb-5">
      <template v-if="ruta.distancia_km">{{ ruta.distancia_km }} km</template>
      <template v-if="ruta.distancia_km && ruta.duracion_min"> · </template>
      <template v-if="ruta.duracion_min">{{ formatDuracion(ruta.duracion_min) }}</template>
    </p>

    <!-- CTA -->
    <button
      @click.stop="emit('click', ruta.id)"
      class="cta-btn-activa"
    >
      Ver ruta activa
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
      </svg>
    </button>
  </div>

  <!-- ── PENDIENTE ──────────────────────────────────────────────────────────── -->
  <button
    v-else-if="variante === 'pendiente'"
    @click="emit('click', ruta.id)"
    class="card-pendiente"
  >
    <!-- Acento izquierdo -->
    <span class="card-pendiente-accent" aria-hidden="true"/>

    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-2 mb-1">
        <p class="font-semibold text-gray-800 text-sm leading-snug">{{ ruta.nombre }}</p>
        <span class="shrink-0 text-[10px] font-bold text-indigo-600 bg-indigo-50 rounded-full px-2.5 py-0.5">
          Pendiente
        </span>
      </div>

      <p class="text-xs text-gray-400 mb-1.5">
        📅 {{ formatFechaRuta(ruta.fecha_programada) }}
        <template v-if="ruta.distancia_km"> · {{ ruta.distancia_km }} km</template>
        <template v-if="ruta.duracion_min"> · ~{{ formatDuracion(ruta.duracion_min) }}</template>
      </p>

      <p v-if="ruta.origen || ruta.destino" class="text-xs text-gray-400 truncate mb-1">
        📍 {{ ruta.origen }} → {{ ruta.destino }}
      </p>

    </div>

    <svg class="w-4 h-4 text-gray-300 shrink-0 ml-2" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
    </svg>
  </button>

  <!-- ── FINALIZADA ─────────────────────────────────────────────────────────── -->
  <button
    v-else
    @click="emit('click', ruta.id)"
    class="card-finalizada"
  >
    <!-- Ícono check -->
    <span class="fin-icon">
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
      </svg>
    </span>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-gray-600 truncate">{{ ruta.nombre }}</p>
      <p class="text-xs text-gray-400">
        {{ formatFechaRuta(ruta.fecha_fin) }}
        <span v-if="ruta.distancia_km"> · {{ ruta.distancia_km }} km</span>
        <span v-if="ruta.km_reales"> · {{ ruta.km_reales }} km recorridos</span>
      </p>
    </div>
    <svg class="w-3.5 h-3.5 text-gray-300 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
    </svg>
  </button>
</template>

<style scoped>
/* ── Tarjeta Activa ────────────────────────────────────────────────────── */
.card-activa {
  position: relative;
  overflow: hidden;
  border-radius: 1.25rem;
  background: var(--gradient-success);
  box-shadow: var(--shadow-green);
  padding: 1.25rem;
  cursor: pointer;
}
.card-activa:active { opacity: 0.9; transform: scale(0.99); transition: all 0.1s; }

.card-activa-deco {
  position: absolute;
  top: -30px; right: -30px;
  width: 120px; height: 120px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
}

.activa-badge {
  display: inline-flex; align-items: center; gap: 0.375rem;
  background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);
  color: white; font-size: 0.75rem; font-weight: 700;
  border-radius: 999px; padding: 0.25rem 0.75rem;
}
.activa-dot {
  display: inline-block;
  width: 7px; height: 7px; border-radius: 50%;
  background: #4ade80;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.6; transform: scale(1.3); }
}

.cost-chip {
  font-size: 0.6875rem; font-weight: 600;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.25);
  color: white; border-radius: 0.5rem; padding: 0.2rem 0.5rem;
}
.cost-chip--total {
  background: rgba(255,255,255,0.28); border-color: rgba(255,255,255,0.4);
  font-weight: 700;
}

.cta-btn-activa {
  display: flex; align-items: center; justify-content: center; gap: 0.375rem;
  width: 100%;
  background: rgba(255,255,255,0.22); border: 1.5px solid rgba(255,255,255,0.35);
  color: white; font-size: 0.875rem; font-weight: 700;
  border-radius: 0.875rem; padding: 0.75rem;
  cursor: pointer;
}
.cta-btn-activa:active { background: rgba(255,255,255,0.32); }

/* ── Tarjeta Pendiente ─────────────────────────────────────────────────── */
.card-pendiente {
  position: relative;
  width: 100%;
  text-align: left;
  display: flex; align-items: center; gap: 0;
  border-radius: 1rem;
  background: white;
  border: 1px solid #E5E7EB;
  box-shadow: var(--shadow-xs);
  padding: 1rem 1rem 1rem 1.25rem;
  min-height: 44px;
  overflow: hidden;
  cursor: pointer;
}
.card-pendiente:active { opacity: 0.75; transform: scale(0.99); transition: all 0.1s; }

.card-pendiente-accent {
  position: absolute; left: 0; top: 0; bottom: 0;
  width: 4px;
  background: var(--gradient-primary);
  border-radius: 4px 0 0 4px;
}

/* ── Tarjeta Finalizada ────────────────────────────────────────────────── */
.card-finalizada {
  width: 100%; text-align: left;
  display: flex; align-items: center; gap: 0.75rem;
  border-radius: 0.875rem;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  padding: 0.75rem 0.875rem;
  min-height: 44px;
  cursor: pointer;
}
.card-finalizada:active { background: #F3F4F6; opacity: 0.8; transition: all 0.1s; }

.fin-icon {
  width: 28px; height: 28px; flex-shrink: 0; border-radius: 50%;
  background: #DCFCE7; color: #16A34A;
  display: flex; align-items: center; justify-content: center;
}
</style>
