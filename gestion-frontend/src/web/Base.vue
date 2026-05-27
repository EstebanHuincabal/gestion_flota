<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { clearEmpresaActiva } from '../utils/empresaActiva.js'
import NotificacionesBell from '../components/NotificacionesBell.vue'
import SessionWarningModal from '../components/SessionWarningModal.vue'
import { useSessionTimer } from '../utils/useSessionTimer.js'

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
    label: 'Rutas',
    path: '/rutas',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>`
  },
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
    label: 'Predictivo',
    path: '/predictivo',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 10V3L4 14h7v7l9-11h-7z"/>`
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
    label: 'Pagos',
    path: '/pagos',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>`
  },
  {
    label: 'Reportes',
    path: '/reportes',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>`
  },
  {
    label: 'Solicitudes',
    path: '/solicitudes',
    badge: true,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>`
  },
  {
    label: 'Calendario',
    path: '/calendario',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z"/>`
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

const navCuenta = [
  {
    label: 'Configuración',
    path: '/configuracion',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
]

const isActive = (path) => route.path.startsWith(path)

// ── Badge de solicitudes para SUPERADMIN ──────────────────────────────────────
const solicitudesPendientes = ref(0)
let pollingSolAdmin = null

async function refrescarConteoSolicitudesAdmin() {
  if (!esSuperadmin.value) return
  try {
    const empresa = JSON.parse(sessionStorage.getItem('empresaActiva') || 'null')
    if (!empresa?.id) return
    const res  = await apiFetch(`/api/empresa/solicitudes/conteo/?empresa_id=${empresa.id}`)
    if (!res.ok) return
    const data = await res.json()
    solicitudesPendientes.value = data.pendientes ?? 0
  } catch {}
}

function onSolicitudesAdminBadge(e) {
  solicitudesPendientes.value = e.detail ?? 0
}

const { mostrarModal, segundosRestantes, extenderSesion, logoutDesdeModal } = useSessionTimer()

const cerrarSesion = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('plan_permisos')
  clearEmpresaActiva()
  router.push('/login')
}

onMounted(() => {
  if (esSuperadmin.value) {
    refrescarConteoSolicitudesAdmin()
    pollingSolAdmin = setInterval(refrescarConteoSolicitudesAdmin, 60_000)
    window.addEventListener('solicitudes-admin-badge', onSolicitudesAdminBadge)
  }
})

onUnmounted(() => {
  clearInterval(pollingSolAdmin)
  window.removeEventListener('solicitudes-admin-badge', onSolicitudesAdminBadge)
})
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
            <span class="nav-icon" style="position:relative">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
              <!-- Punto rojo en modo colapsado -->
              <span v-if="navCollapsed && item.badge && solicitudesPendientes > 0" class="base-badge-dot"/>
            </span>
            <span v-if="!navCollapsed" class="nav-label">{{ item.label }}</span>
            <!-- Contador inline en modo expandido -->
            <span v-if="!navCollapsed && item.badge && solicitudesPendientes > 0" class="base-badge-count">
              {{ solicitudesPendientes > 99 ? '99+' : solicitudesPendientes }}
            </span>
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

        <!-- Cuenta -->
        <div class="nav-separator"/>
        <p v-if="!navCollapsed" class="nav-section-label">Cuenta</p>
        <router-link
          v-for="item in navCuenta"
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

      </nav>

    </aside>

    <!-- ── Contenido principal ── -->
    <main class="main-content">
      <header class="top-bar">
        <div class="top-bar-spacer"/>
        <div class="top-bar-right">
          <NotificacionesBell />
          <div class="session-info">
            <div class="session-avatar">{{ (usuario.nombre || 'U')[0].toUpperCase() }}</div>
            <div class="session-details">
              <span class="session-name">{{ usuario.nombre }}</span>
              <span class="session-role">{{ rolLabel }}</span>
            </div>
          </div>
          <button class="logout-btn-top" @click="cerrarSesion" title="Cerrar sesión">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
            <span>Salir</span>
          </button>
        </div>
      </header>
      <div class="page-content">
        <RouterView />
      </div>
    </main>

  </div>

  <SessionWarningModal
    v-if="mostrarModal"
    :segundos-restantes="segundosRestantes"
    @extender="extenderSesion"
    @cerrar="logoutDesdeModal"
  />
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
  background: linear-gradient(160deg, var(--sidebar-from, #4F46E5) 0%, var(--sidebar-to, #7C3AED) 100%);
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
  background: var(--sidebar-to, #7C3AED);
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: background 0.2s;
  z-index: 10;
}
.collapse-btn:hover { background: var(--sidebar-from, #4F46E5); }
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
  align-items: center;
  padding: 0 1.5rem;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
  height: 64px;
  flex-shrink: 0;
}
.top-bar-spacer { flex: 1; }
.top-bar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.session-info {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.3rem 0.75rem 0.3rem 0.4rem;
  background: #F3F4F6;
  border-radius: 50px;
}
.session-avatar {
  width: 30px; height: 30px;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.8125rem; flex-shrink: 0;
}
.session-details {
  display: flex;
  flex-direction: column;
}
.session-name {
  font-size: 0.8125rem; font-weight: 600; color: #111827; line-height: 1.2;
}
.session-role {
  font-size: 0.6875rem; color: #6B7280;
}
.logout-btn-top {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.45rem 0.875rem; border-radius: 8px;
  border: 1px solid #E5E7EB; background: #fff;
  color: #6B7280; font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; transition: background 0.15s, color 0.15s, border-color 0.15s; font-family: inherit;
}
.logout-btn-top:hover { background: #FEF2F2; border-color: #FECACA; color: #DC2626; }
.logout-btn-top svg { width: 16px; height: 16px; }
.page-content { flex: 1; overflow-y: auto; }

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Badge de solicitudes en sidebar ── */
.base-badge-dot {
  position: absolute;
  top: -3px; right: -3px;
  width: 9px; height: 9px;
  border-radius: 50%;
  background: #EF4444;
  border: 2px solid transparent;
  box-shadow: 0 0 0 1.5px rgba(239,68,68,0.4);
}
.base-badge-count {
  margin-left: auto;
  min-width: 20px;
  padding: 0.1rem 0.4rem;
  border-radius: 9999px;
  background: #EF4444;
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 700;
  line-height: 1.5;
  text-align: center;
  flex-shrink: 0;
}
</style>
