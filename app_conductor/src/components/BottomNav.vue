<script setup>
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route  = useRoute()

const items = [
  {
    to:    '/rutas',
    label: 'Rutas',
    icon:  'rutas',
  },
  {
    to:    '/solicitudes',
    label: 'Solicitudes',
    icon:  'solicitudes',
  },
  {
    to:    '/ajustes',
    label: 'Ajustes',
    icon:  'ajustes',
  },
]

const esActivo = (to) => route.path.startsWith(to)
</script>

<template>
  <nav
    class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 z-50"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <div class="flex justify-around py-2">
      <button
        v-for="item in items"
        :key="item.to"
        @click="router.push(item.to)"
        :class="[
          'flex flex-col items-center gap-0.5 px-5 py-1.5 min-h-[44px] transition-colors',
          esActivo(item.to) ? 'text-[var(--color-acento)]' : 'text-gray-400'
        ]"
      >
        <!-- Rutas -->
        <svg v-if="item.icon === 'rutas'" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        <!-- Solicitudes -->
        <svg v-if="item.icon === 'solicitudes'" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
        </svg>
        <!-- Ajustes -->
        <svg v-if="item.icon === 'ajustes'" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>

        <span class="text-[10px] font-medium">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>
