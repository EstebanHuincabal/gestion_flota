<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { clearEmpresaActiva } from '../utils/empresaActiva.js'

const router = useRouter()
const route  = useRoute()
const usuario = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const navCollapsed = ref(false)

const ROL_LABELS  = { SUPERADMIN: 'Super Administrador', USUARIO: 'Usuario', CONDUCTOR: 'Conductor' }
const rolLabel    = computed(() => ROL_LABELS[usuario.value.rol] || usuario.value.rol || '')
const esSuperadmin = computed(() => usuario.value.rol === 'SUPERADMIN')
const esConductor  = computed(() => usuario.value.rol === 'CONDUCTOR')

// ── Navegación ─────────────────────────────────────────
const navDashboard = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>`
  },
]

const navAdmin = [
  {
    label: 'Empresas',
    path: '/empresas',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>`
  },
  {
    label: 'Usuarios',
    path: '/usuarios',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>`
  },
  {
    label: 'Planes',
    path: '/planes',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>`
  },
  {
    label: 'Permisos',
    path: '/permisos',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>`
  },
  {
    label: 'Logs',
    path: '/logs',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>`
  },
]

const navOperaciones = [
  {
    label: 'Flota',
    path: '/flota',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>`
  },
  {
    label: 'Conductores',
    path: '/conductores',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>`
  },
  {
    label: 'Mantenciones',
    path: '/mantenciones',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>`
  },
  {
    label: 'Documentos',
    path: '/documentos',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`
  },
  {
    label: 'Finanzas',
    path: '/finanzas',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>`
  },
  {
    label: 'Reportes',
    path: '/reportes',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>`
  },
]

const navConductor = [
  {
    label: 'Documentos',
    path: '/documentos',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`
  },
]

const navSoporte = [
  {label: 'Sistema de soporte',
   path: '#',
  }
]

const isActive = (path) => route.path.startsWith(path)

const cerrarSesion = () => {
  clearEmpresaActiva()
  localStorage.removeItem('usuario')
  router.push('/login')
}
</script>

<template>
  <div class="layout">

    <!-- ── Sidebar ── -->
    <aside :class="['sidebar', { collapsed: navCollapsed }]">

      <!-- Logo / Branding -->
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>
          </svg>
        </div>
        <span v-if="!navCollapsed" class="brand-name">Gestión de Flota</span>
      </div>

      <!-- Toggle colapsar -->
      <button class="collapse-btn" @click="navCollapsed = !navCollapsed" :title="navCollapsed ? 'Expandir' : 'Colapsar'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            :d="navCollapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'"/>
        </svg>
      </button>

      <!-- Nav -->
      <nav class="nav">

        <!-- Dashboard — todos los roles -->
        <router-link
          v-for="item in navDashboard"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          :title="navCollapsed ? item.label : ''"
        >
          <span class="nav-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
          </span>
          <span v-if="!navCollapsed" class="nav-label">{{ item.label }}</span>
          <span v-if="!navCollapsed && isActive(item.path)" class="active-bar"/>
        </router-link>

        <!-- Administración — solo SUPERADMIN -->
        <template v-if="esSuperadmin">
          <div class="nav-separator"/>
          <p v-if="!navCollapsed" class="nav-section-label">Administración</p>
          <router-link
            v-for="item in navAdmin"
            :key="item.path"
            :to="item.path"
            :class="['nav-item', { active: isActive(item.path) }]"
            :title="navCollapsed ? item.label : ''"
          >
            <span class="nav-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
            </span>
            <span v-if="!navCollapsed" class="nav-label">{{ item.label }}</span>
            <span v-if="!navCollapsed && isActive(item.path)" class="active-bar"/>
          </router-link>
        </template>

        <!-- Operaciones — SUPERADMIN + USUARIO -->
        <template v-if="!esConductor">
          <div class="nav-separator"/>
          <p v-if="!navCollapsed" class="nav-section-label">Operaciones</p>
          <router-link
            v-for="item in navOperaciones"
            :key="item.path"
            :to="item.path"
            :class="['nav-item', { active: isActive(item.path) }]"
            :title="navCollapsed ? item.label : ''"
          >
            <span class="nav-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
            </span>
            <span v-if="!navCollapsed" class="nav-label">{{ item.label }}</span>
            <span v-if="!navCollapsed && isActive(item.path)" class="active-bar"/>
          </router-link>
        </template>

        <!-- Mi Panel — solo CONDUCTOR -->
        <template v-if="esConductor">
          <div class="nav-separator"/>
          <p v-if="!navCollapsed" class="nav-section-label">Mi Panel</p>
          <router-link
            v-for="item in navConductor"
            :key="item.path"
            :to="item.path"
            :class="['nav-item', { active: isActive(item.path) }]"
            :title="navCollapsed ? item.label : ''"
          >
            <span class="nav-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
            </span>
            <span v-if="!navCollapsed" class="nav-label">{{ item.label }}</span>
            <span v-if="!navCollapsed && isActive(item.path)" class="active-bar"/>
          </router-link>
        </template>

      </nav>

      <!-- Footer: usuario + logout -->
      <div class="sidebar-footer">
        <div class="user-block" v-if="!navCollapsed">
          <div class="user-avatar">{{ (usuario.nombre || 'U')[0].toUpperCase() }}</div>
          <div class="user-info">
            <p class="user-name">{{ usuario.nombre }}</p>
            <p class="user-role">{{ rolLabel }}</p>
          </div>
        </div>
        <div v-else class="user-avatar solo">{{ (usuario.nombre || 'U')[0].toUpperCase() }}</div>
        <button class="logout-btn" @click="cerrarSesion" :title="navCollapsed ? 'Cerrar sesión' : ''">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          <span v-if="!navCollapsed">Salir</span>
        </button>
      </div>

    </aside>

    <!-- ── Contenido principal ── -->
    <main class="main-content">
      <RouterView />
    </main>

  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.layout {
  display: flex;
  min-height: 100vh;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: #F8FAFC;
}

/* ── Sidebar ── */
.sidebar {
  position: fixed;
  top: 0; left: 0;
  height: 100vh;
  width: 240px;
  background: linear-gradient(160deg, #4F46E5 0%, #7C3AED 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  z-index: 100;
  overflow: hidden;
}
.sidebar.collapsed { width: 68px; }

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  min-height: 64px;
}
.brand-icon {
  flex-shrink: 0;
  width: 36px; height: 36px;
  background: rgba(255,255,255,0.18);
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
}
.brand-icon svg { width: 20px; height: 20px; color: #fff; }
.brand-name {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}

.collapse-btn {
  position: absolute;
  top: 18px; right: -13px;
  width: 26px; height: 26px;
  background: #7C3AED;
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: background 0.2s;
  z-index: 10;
}
.collapse-btn:hover { background: #4F46E5; }
.collapse-btn svg { width: 14px; height: 14px; }

/* Nav */
.nav {
  flex: 1;
  padding: 1rem 0.625rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.25) transparent;
}
.nav::-webkit-scrollbar {
  width: 4px;
}
.nav::-webkit-scrollbar-track {
  background: transparent;
}
.nav::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.25);
  border-radius: 999px;
}
.nav::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.45);
}
.nav-separator {
  height: 1px;
  background: rgba(255,255,255,0.12);
  margin: 0.5rem 0.5rem 0.75rem;
}
.nav-section-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: rgba(255,255,255,0.45);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0 0.5rem;
  margin: 0 0 0.5rem;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  text-decoration: none;
  color: rgba(255,255,255,0.7);
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}
.nav-item:hover { background: rgba(255,255,255,0.12); color: #fff; }
.nav-item.active { background: rgba(255,255,255,0.18); color: #fff; font-weight: 600; }
.nav-icon { flex-shrink: 0; display: flex; align-items: center; }
.nav-icon svg { width: 20px; height: 20px; }
.nav-label { flex: 1; }
.active-bar { width: 3px; height: 16px; background: #fff; border-radius: 2px; }

/* ── Footer ── */
.sidebar-footer {
  padding: 0.75rem 0.625rem;
  border-top: 1px solid rgba(255,255,255,0.12);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-block {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem;
  border-radius: 10px;
  background: rgba(255,255,255,0.1);
}
.user-avatar {
  flex-shrink: 0;
  width: 32px; height: 32px;
  background: rgba(255,255,255,0.25);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #fff;
}
.user-avatar.solo { margin: 0 auto; }
.user-info { overflow: hidden; }
.user-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #fff;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role { font-size: 0.7rem; color: rgba(255,255,255,0.55); margin: 0; }

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1.5px solid rgba(255,255,255,0.2);
  border-radius: 10px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.75);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, background 0.2s;
  font-family: inherit;
}
.logout-btn:hover { border-color: rgba(255,255,255,0.5); color: #fff; background: rgba(255,255,255,0.15); }
.logout-btn svg { width: 16px; height: 16px; flex-shrink: 0; }

/* Contenido */
.main-content {
  margin-left: 240px;
  flex: 1;
  min-height: 100vh;
  transition: margin-left 0.25s ease;
  display: flex;
  flex-direction: column;
}
.sidebar.collapsed ~ .main-content { margin-left: 68px; }

/* ── Top Bar ── */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  background: linear-gradient(160deg, #4F46E5 0%, #7C3AED 100%);
  border-bottom: 1px solid rgba(255,255,255,0.12);
  height: 64px;
  flex-shrink: 0;
}
.top-bar-spacer { flex: 1; }
.top-bar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.session-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.35rem 0.5rem;
  border-radius: 50px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.session-avatar {
  width: 32px; height: 32px;
  background: rgba(255, 255, 255, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.85rem;
}
.session-details {
  display: flex;
  flex-direction: column;
  padding-right: 0.5rem;
}
.session-name {
  font-size: 0.8125rem; font-weight: 600; color: #fff; line-height: 1.2;
}
.session-role {
  font-size: 0.7rem; color: rgba(255, 255, 255, 0.7); font-weight: 500;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
