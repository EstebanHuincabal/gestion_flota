<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMantencionesStore } from '@/stores/mantenciones.js'
import { usePermisos } from '@/composables/usePermisos.js'

const router      = useRouter()
const route       = useRoute()
const mantenStore = useMantencionesStore()

const { tieneModulo, cargando: cargandoPermisos } = usePermisos()

// modulo: null → siempre visible; modulo: 'xxx' → visible solo si está en el plan
const items = [
  { to: '/rutas',       label: 'Rutas',      icon: 'rutas',       modulo: 'rutas'        },
  { to: '/solicitudes', label: 'Solicitudes', icon: 'solicitudes', modulo: 'solicitudes'  },
  { to: '/mantencion',  label: 'Mantención',  icon: 'mantencion',  modulo: 'mantenciones' },
  { to: '/ajustes',     label: 'Ajustes',     icon: 'ajustes',     modulo: null           },
]

// Mientras cargamos los permisos mostramos todos los ítems para evitar un flash
const itemsVisibles = computed(() => {
  if (cargandoPermisos.value) return items
  return items.filter(item => !item.modulo || tieneModulo(item.modulo))
})

const esActivo = (to) => route.path.startsWith(to)
</script>

<template>
  <!--
    Altura total = 64px (contenido) + env(safe-area-inset-bottom).
    --nav-h = 64px definido en main.css.
    El contenido de todas las vistas usa .pb-nav = calc(64px + safe-area-bottom).
  -->
  <nav class="nav-glass" style="padding-bottom: env(safe-area-inset-bottom, 0px)">
    <div class="nav-inner">
      <button
        v-for="item in itemsVisibles"
        :key="item.to"
        @click="router.push(item.to)"
        :aria-label="item.label"
        :class="['nav-btn', esActivo(item.to) ? 'nav-btn--active' : 'nav-btn--idle']"
      >
        <!-- Pill activo -->
        <span v-if="esActivo(item.to)" class="nav-pill" aria-hidden="true"/>

        <!-- ── Ícono Rutas ── -->
        <span class="nav-icon-wrap">
          <svg v-if="item.icon === 'rutas'" class="nav-icon" viewBox="0 0 24 24">
            <!-- Relleno cuando activo -->
            <path v-if="esActivo(item.to)"
              fill="currentColor"
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
            <!-- Contorno cuando inactivo -->
            <path v-else fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
          </svg>

          <!-- ── Ícono Solicitudes ── -->
          <svg v-if="item.icon === 'solicitudes'" class="nav-icon" viewBox="0 0 24 24">
            <path v-if="esActivo(item.to)"
              fill="currentColor"
              d="M8 10h8M8 14h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
            />
            <path v-else fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
              d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
            />
          </svg>

          <!-- ── Ícono Mantención ── con badge -->
          <span v-if="item.icon === 'mantencion'" class="relative inline-flex">
            <svg class="nav-icon" viewBox="0 0 24 24">
              <path v-if="esActivo(item.to)"
                fill="currentColor"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path v-else fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <!-- Badge rojo urgente -->
            <span v-if="mantenStore.hayUrgente"
              class="badge-dot badge-dot--red"
            >!</span>
            <!-- Badge azul cantidad -->
            <span v-else-if="mantenStore.totalActivas > 0"
              class="badge-dot badge-dot--blue"
            >{{ mantenStore.totalActivas }}</span>
          </span>

          <!-- ── Ícono Ajustes ── -->
          <svg v-if="item.icon === 'ajustes'" class="nav-icon" viewBox="0 0 24 24">
            <path v-if="esActivo(item.to)"
              fill="currentColor"
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
            <path v-else fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        </span>

        <span class="nav-label">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.nav-glass {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  z-index: 50;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 -4px 24px rgba(0,0,0,0.06);
}

.nav-inner {
  display: flex;
  justify-content: space-around;
  align-items: stretch;
  height: var(--nav-h, 64px);
}

.nav-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 1;
  border: none;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.1s;
}
.nav-btn:active { opacity: 0.65; }

/* Pill / indicador activo */
.nav-pill {
  position: absolute;
  top: 7px;
  width: 36px; height: 4px;
  border-radius: 0 0 4px 4px;
  background: var(--color-acento);
  box-shadow: 0 2px 8px rgba(83,74,183,0.5);
}

.nav-btn--active { color: var(--color-acento); }
.nav-btn--idle   { color: #9CA3AF; }

.nav-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.nav-icon {
  width: 23px; height: 23px;
}

.nav-label {
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.01em;
}
.nav-btn--active .nav-label { font-weight: 700; }

/* Badges */
.badge-dot {
  position: absolute;
  top: -4px; right: -5px;
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2px solid white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 7px;
  font-weight: 800;
  line-height: 1;
  color: white;
}
.badge-dot--red  { background: #EF4444; }
.badge-dot--blue { background: var(--color-acento); }
</style>
