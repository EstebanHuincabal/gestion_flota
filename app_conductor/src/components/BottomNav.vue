<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useMantencionesStore } from '@/stores/mantenciones.js'

const router    = useRouter()
const route     = useRoute()
const mantenStore = useMantencionesStore()

const items = [
  { to: '/rutas',       label: 'Rutas',       icon: 'rutas'       },
  { to: '/solicitudes', label: 'Solicitudes',  icon: 'solicitudes' },
  { to: '/mantencion',  label: 'Mantención',   icon: 'mantencion'  },
  { to: '/ajustes',     label: 'Ajustes',      icon: 'ajustes'     },
]

const esActivo = (to) => route.path.startsWith(to)
</script>

<template>
  <!--
    La altura total del nav = 60px (contenido) + env(safe-area-inset-bottom).
    Esta variable CSS --nav-h = 60px está declarada en main.css.
    El contenido de todas las vistas usa .pb-nav = calc(60px + safe-area-bottom).
  -->
  <nav
    class="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-100"
    style="padding-bottom: env(safe-area-inset-bottom, 0px)"
  >
    <div class="flex justify-around items-stretch" style="height: var(--nav-h, 60px)">
      <button
        v-for="item in items"
        :key="item.to"
        @click="router.push(item.to)"
        :aria-label="item.label"
        :class="[
          'relative flex flex-col items-center justify-center gap-0.5 flex-1 transition-colors',
          'active:opacity-70',
          esActivo(item.to) ? 'text-[var(--color-acento)]' : 'text-gray-400'
        ]"
      >
        <!-- Indicador activo (barra superior) -->
        <span
          v-if="esActivo(item.to)"
          class="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-[3px] rounded-b-full"
          style="background: var(--color-acento)"
        />

        <!-- Ícono Rutas -->
        <svg v-if="item.icon === 'rutas'" class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>

        <!-- Ícono Solicitudes -->
        <svg v-if="item.icon === 'solicitudes'" class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
        </svg>

        <!-- Ícono Mantención (llave inglesa) con badge si hay urgente -->
        <span v-if="item.icon === 'mantencion'" class="relative">
          <svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <!-- Badge rojo si hay mantención urgente o vehículo bloqueado -->
          <span
            v-if="mantenStore.hayUrgente"
            class="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-500 rounded-full border border-white
                   flex items-center justify-center text-[8px] text-white font-bold leading-none"
          >!</span>
          <!-- Badge azul con cantidad si hay activas pero sin urgencia -->
          <span
            v-else-if="mantenStore.totalActivas > 0"
            class="absolute -top-1 -right-1 w-3.5 h-3.5 bg-[var(--color-acento)] rounded-full border border-white
                   flex items-center justify-center text-[8px] text-white font-bold leading-none"
          >{{ mantenStore.totalActivas }}</span>
        </span>

        <!-- Ícono Ajustes -->
        <svg v-if="item.icon === 'ajustes'" class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
        </svg>

        <span
          class="text-[10px] font-semibold leading-none"
          :class="esActivo(item.to) ? 'font-bold' : ''"
        >{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>
