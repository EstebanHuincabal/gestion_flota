<script setup>
import { ref, computed } from 'vue'
import PerfilTab from './tabs/PerfilTab.vue'
import AparienciaTab from './tabs/AparienciaTab.vue'
import NotificacionesTab from './tabs/NotificacionesTab.vue'
import MiPlanTab from './tabs/MiPlanTab.vue'
import TerminosCondicionesTab from './tabs/TerminosCondicionesTab.vue'
import ConfiguracionEmailTab from './tabs/ConfiguracionEmailTab.vue'

const usuario = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))

const TABS = [
  {
    id: 'perfil',
    label: 'Perfil',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>`,
    component: PerfilTab,
    roles: ['SUPERADMIN', 'USUARIO'],
  },
  {
    id: 'apariencia',
    label: 'Apariencia',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>`,
    component: AparienciaTab,
    roles: ['SUPERADMIN', 'USUARIO'],
  },
  {
    id: 'notificaciones',
    label: 'Notificaciones',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>`,
    component: NotificacionesTab,
    roles: ['USUARIO'],
  },
  {
    id: 'miplan',
    label: 'Mi Plan',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>`,
    component: MiPlanTab,
    roles: ['USUARIO'],
  },
  {
    id: 'terminos',
    label: 'Términos y Pagos',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`,
    component: TerminosCondicionesTab,
    roles: ['SUPERADMIN'],
  },
  {
    id: 'email',
    label: 'Correo',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>`,
    component: ConfiguracionEmailTab,
    roles: ['SUPERADMIN'],
  },
]

const tabs = computed(() => TABS.filter(t => t.roles.includes(usuario.value.rol)))
const tabActiva = ref('perfil')
const tabActual = computed(() => tabs.value.find(t => t.id === tabActiva.value)?.component || PerfilTab)
</script>

<template>
  <div class="config-page">
    <div class="config-header">
      <h1 class="config-title">Configuración</h1>
      <p class="config-subtitle">Personaliza tu cuenta y preferencias</p>
    </div>

    <div class="config-body">
      <aside class="config-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['config-tab', { active: tabActiva === tab.id }]"
          @click="tabActiva = tab.id"
        >
          <span class="tab-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="tab.icon"/>
          </span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </aside>

      <section class="config-content">
        <component :is="tabActual" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.config-page {
  padding: 2rem 2.5rem;
  max-width: 980px;
  margin: 0 auto;
}

.config-header { margin-bottom: 1.75rem; }
.config-title {
  font-size: 1.625rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.25rem;
}
.config-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.config-body {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.config-nav {
  width: 196px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.config-tab {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 0.75rem;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #6B7280;
  font-size: 0.875rem;
  font-weight: 500;
  text-align: left;
  width: 100%;
  transition: background 0.15s, color 0.15s;
}
.config-tab:hover { background: #F3F4F6; color: #111827; }
.config-tab.active {
  background: #EEF2FF;
  color: var(--color-accent, #4F46E5);
  font-weight: 600;
}

.tab-icon { flex-shrink: 0; display: flex; }
.tab-icon svg { width: 18px; height: 18px; }
.tab-label { flex: 1; }

.config-content { flex: 1; min-width: 0; }
</style>
