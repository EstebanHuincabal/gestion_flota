<script setup>
import { formatCLP, formatDuracion, formatFechaRuta } from '@/utils/formato.js'

const props = defineProps({
  ruta:     { type: Object,  required: true },
  variante: { type: String,  default: 'pendiente' }, // 'activa' | 'pendiente' | 'finalizada'
})

const emit = defineEmits(['click'])
</script>

<template>
  <!-- ── ACTIVA ─────────────────────────────────────────────────────────────── -->
  <div
    v-if="variante === 'activa'"
    class="rounded-2xl p-4 border-2 border-green-400 bg-green-50"
  >
    <!-- Badge -->
    <div class="flex items-center justify-between mb-3">
      <span class="flex items-center gap-1.5 text-xs font-semibold text-green-700">
        <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"/>
        En curso
      </span>
      <span class="text-xs text-gray-500 font-medium">{{ ruta.tipo === 'carga' ? 'Carga' : 'Personas' }}</span>
    </div>

    <!-- Nombre -->
    <p class="font-bold text-gray-800 text-base mb-1">{{ ruta.nombre }}</p>

    <!-- Detalle -->
    <p class="text-sm text-gray-500 mb-3">
      {{ ruta.distancia_km ? `${ruta.distancia_km} km` : '' }}
      {{ ruta.distancia_km && ruta.duracion_min ? ' · ' : '' }}
      {{ formatDuracion(ruta.duracion_min) }}
    </p>

    <!-- Costos -->
    <div class="flex gap-2 mb-4 flex-wrap">
      <span v-if="ruta.costo_combustible_est" class="text-xs bg-white border border-green-200 text-gray-600 rounded-lg px-2 py-1">
        {{ formatCLP(ruta.costo_combustible_est) }} comb.
      </span>
      <span v-if="ruta.costo_peajes_est" class="text-xs bg-white border border-green-200 text-gray-600 rounded-lg px-2 py-1">
        {{ formatCLP(ruta.costo_peajes_est) }} peajes
      </span>
      <span v-if="ruta.costo_total_est" class="text-xs bg-green-100 text-green-700 font-semibold rounded-lg px-2 py-1">
        Total {{ formatCLP(ruta.costo_total_est) }}
      </span>
    </div>

    <!-- Botón -->
    <button
      @click="emit('click', ruta.id)"
      class="w-full py-3 rounded-xl text-white text-sm font-semibold bg-green-500 hover:bg-green-600 transition min-h-[44px]"
    >
      Ver ruta activa →
    </button>
  </div>

  <!-- ── PENDIENTE ──────────────────────────────────────────────────────────── -->
  <button
    v-else-if="variante === 'pendiente'"
    @click="emit('click', ruta.id)"
    class="w-full text-left rounded-2xl p-4 border border-gray-200 bg-white
           transition-all active:scale-[0.98] active:bg-gray-50 min-h-[44px]"
  >
    <div class="flex items-start justify-between gap-2 mb-1">
      <p class="font-semibold text-gray-800 text-sm leading-snug">{{ ruta.nombre }}</p>
      <span class="shrink-0 text-[10px] font-semibold text-indigo-600 bg-indigo-50 rounded-full px-2 py-0.5">
        Pendiente
      </span>
    </div>

    <p class="text-xs text-gray-500 mb-2">
      {{ formatFechaRuta(ruta.fecha_programada) }}
      {{ ruta.distancia_km ? ` · ${ruta.distancia_km} km` : '' }}
      {{ ruta.duracion_min ? ` · ~${formatDuracion(ruta.duracion_min)}` : '' }}
    </p>

    <p v-if="ruta.origen || ruta.destino" class="text-xs text-gray-400 truncate mb-2">
      {{ ruta.origen }} → {{ ruta.destino }}
    </p>

    <p v-if="ruta.costo_total_est" class="text-xs text-gray-500">
      {{ formatCLP(ruta.costo_total_est) }} est.
    </p>
  </button>

  <!-- ── FINALIZADA ─────────────────────────────────────────────────────────── -->
  <button
    v-else
    @click="emit('click', ruta.id)"
    class="w-full text-left rounded-xl px-4 py-3 bg-gray-50 border border-gray-100
           flex items-center justify-between gap-3 min-h-[44px]
           active:bg-gray-100 active:scale-[0.99] transition-all"
  >
    <div class="min-w-0">
      <p class="text-sm font-medium text-gray-600 truncate">{{ ruta.nombre }}</p>
      <p class="text-xs text-gray-400">
        {{ formatFechaRuta(ruta.fecha_fin) }}
        <span v-if="ruta.distancia_km"> · {{ ruta.distancia_km }} km</span>
      </p>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      <span class="text-[10px] font-semibold text-gray-400 bg-gray-200 rounded-full px-2 py-0.5">
        Finalizada
      </span>
      <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
      </svg>
    </div>
  </button>
</template>
