<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import NotificacionesBell from '../../components/NotificacionesBell.vue'
import PlanUsageBanner from './PlanUsageBanner.vue'
import BannerSuscripcion from './BannerSuscripcion.vue'
import LimitePlanModal from '../planes/LimitePlanModal.vue'
import SessionWarningModal from '../../components/SessionWarningModal.vue'
import { useSessionTimer } from '../../utils/useSessionTimer.js'

const router  = useRouter()
const route   = useRoute()
const usuario = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))
const collapsed = ref(false)

// Permisos reactivos — inicializados desde sessionStorage para renderizado inmediato
const planPermisos = ref(JSON.parse(sessionStorage.getItem('plan_permisos') || '[]'))

function puedeVer(permiso) {
  if (!permiso) return true
  return planPermisos.value.includes(permiso)
}

async function refrescarPermisos() {
  try {
    const res = await apiFetch('/api/usuario/perfil/')
    if (!res.ok) return
    const data = await res.json()
    const nuevos = JSON.stringify(data.plan_permisos || [])
    const actuales = sessionStorage.getItem('plan_permisos') || '[]'
    sessionStorage.setItem('plan_permisos', nuevos)
    sessionStorage.setItem('plan_modulos',  JSON.stringify(data.plan_modulos || []))
    sessionStorage.setItem('plan_nombre',   data.plan_nombre || '')
    if (nuevos !== actuales) {
      planPermisos.value = data.plan_permisos || []
    }
  } catch {}
}

// ── Badge de solicitudes de conductores ──────────────────────────────────────
const solicitudesPendientes = ref(0)
let wsSolicitudes  = null
let pollingSol     = null

async function refrescarConteoSolicitudes() {
  try {
    const res  = await apiFetch('/api/empresa/solicitudes/conteo/')
    if (!res.ok) return
    const data = await res.json()
    solicitudesPendientes.value = data.pendientes ?? 0
  } catch {}
}

function conectarWSSolicitudes() {
  const usr = JSON.parse(localStorage.getItem('usuario') || '{}')
  const empresaId = usr.empresa_id
  const token     = localStorage.getItem('access_token')
  if (!empresaId || !token) return

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  wsSolicitudes = new WebSocket(`${proto}://${location.host}/ws/solicitudes/${empresaId}/?token=${token}`)

  wsSolicitudes.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.tipo === 'nueva_solicitud') {
        solicitudesPendientes.value++
      }
    } catch {}
  }
  wsSolicitudes.onclose = () => {
    if (wsSolicitudes._manuallyClosed) return
    setTimeout(conectarWSSolicitudes, 6000)
  }
}

let pollingInterval = null

function onSuscripcionBloqueada() {
  router.push('/empresa/pago')
}

onMounted(() => {
  refrescarPermisos()
  pollingInterval = setInterval(refrescarPermisos, 15_000)
  // Solicitudes badge
  refrescarConteoSolicitudes()
  conectarWSSolicitudes()
  pollingSol = setInterval(refrescarConteoSolicitudes, 30_000)
  // Escuchar bloqueo 402
  window.addEventListener('suscripcion-bloqueada', onSuscripcionBloqueada)
})

onUnmounted(() => {
  clearInterval(pollingInterval)
  clearInterval(pollingSol)
  if (wsSolicitudes) { wsSolicitudes._manuallyClosed = true; wsSolicitudes.close() }
  window.removeEventListener('suscripcion-bloqueada', onSuscripcionBloqueada)
})

const navItems = [
  {
    label: 'Dashboard',
    path: '/empresa/dashboard',
    permiso: null,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>`,
  },
  {
    label: 'Flota',
    path: '/empresa/flota',
    permiso: 'flotas.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1"/>`,
  },
  {
    label: 'Conductores',
    path: '/empresa/conductores',
    permiso: 'conductores.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
  {
    label: 'Mantenciones',
    path: '/empresa/mantenciones',
    permiso: 'mantenciones.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
  {
    label: 'Predictivo',
    path: '/empresa/predictivo',
    permiso: 'mantenciones.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M13 10V3L4 14h7v7l9-11h-7z"/>`
  },
  {
    label: 'Documentos',
    path: '/empresa/documentos',
    permiso: 'documentos.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`,
  },
  {
    label: 'Rutas',
    path: '/empresa/rutas',
    permiso: 'rutas.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>`,
  },
  {
    label: 'Solicitudes',
    path: '/empresa/solicitudes',
    permiso: null,
    badge: true,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>`,
  },
  {
    label: 'Calendario',
    path: '/empresa/calendario',
    permiso: 'calendario.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z"/>`,
  },
  {
    label: 'Finanzas',
    path: '/empresa/finanzas',
    permiso: 'finanzas.ver',
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>`,
  },
  {
    label: 'Reportes',
    path: '/empresa/reportes',
    permiso: null,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>`,
  },
  {
    label: 'Suscripción y pagos',
    path: '/empresa/pago',
    permiso: null,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>`,
  },
  {
    label: 'Configuración',
    path: '/empresa/configuracion',
    permiso: null,
    icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`,
  },
]

const navItemsFiltrados = computed(() =>
  navItems.filter(item => puedeVer(item.permiso))
)

const isActive = (path) => route.path.startsWith(path)

const { mostrarModal, segundosRestantes, extenderSesion, logoutDesdeModal } = useSessionTimer()

const cerrarSesion = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('plan_permisos')
  router.push('/login')
}
</script>

<template>
  <div class="layout">

    <aside :class="['sidebar', { collapsed }]">

      <!-- Branding -->
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
        </div>
        <div v-if="!collapsed" class="brand-text">
          <span class="brand-empresa">{{ usuario.empresa || 'Mi empresa' }}</span>
          <span class="brand-tag">Panel de empresa</span>
        </div>
      </div>

      <!-- Toggle -->
      <button class="collapse-btn" @click="collapsed = !collapsed" :title="collapsed ? 'Expandir' : 'Colapsar'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            :d="collapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'"/>
        </svg>
      </button>

      <!-- Nav -->
      <nav class="nav">
        <p v-if="!collapsed" class="nav-label-group">Gestión</p>
        <router-link
          v-for="item in navItemsFiltrados"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          :title="collapsed ? item.label : ''"
        >
          <span class="nav-icon" style="position:relative">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="item.icon"/>
            <!-- Badge de solicitudes pendientes -->
            <span
              v-if="item.badge && solicitudesPendientes > 0"
              class="nav-badge"
            >{{ solicitudesPendientes > 99 ? '99+' : solicitudesPendientes }}</span>
          </span>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          <!-- Badge visible también cuando está expandido -->
          <span
            v-if="!collapsed && item.badge && solicitudesPendientes > 0 && !isActive(item.path)"
            class="nav-badge-inline"
          >{{ solicitudesPendientes > 99 ? '99+' : solicitudesPendientes }}</span>
          <span v-if="!collapsed && isActive(item.path)" class="active-bar"/>
        </router-link>
      </nav>

    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="topbar-right">
          <NotificacionesBell />
          <div class="session-pill">
            <div class="session-avatar">{{ (usuario.nombre || 'U')[0].toUpperCase() }}</div>
            <div class="session-details">
              <span class="session-name">{{ usuario.nombre }}</span>
              <span class="session-role">{{ usuario.rol }}</span>
            </div>
          </div>
          <button class="topbar-logout" @click="cerrarSesion" title="Cerrar sesión">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
            <span>Salir</span>
          </button>
        </div>
      </header>
      <PlanUsageBanner />
      <BannerSuscripcion />
      <div class="page-content">
        <RouterView />
      </div>
    </main>

  </div>

  <LimitePlanModal />

  <SessionWarningModal
    v-if="mostrarModal"
    :segundos-restantes="segundosRestantes"
    @extender="extenderSesion"
    @cerrar="logoutDesdeModal"
  />
</template>

<style scoped>
* { box-sizing: border-box; }

.layout { display: flex; min-height: 100vh; font-family: 'Inter', system-ui, sans-serif; background: #F8FAFC; }

.sidebar {
  position: fixed; top: 0; left: 0; height: 100vh; width: 240px;
  background: linear-gradient(160deg, var(--sidebar-from, #4F46E5) 0%, var(--sidebar-to, #7C3AED) 100%);
  display: flex; flex-direction: column;
  transition: width 0.25s ease; z-index: 100; overflow: hidden;
}
.sidebar.collapsed { width: 68px; }

.sidebar-brand {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1.1rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.12); min-height: 64px;
}
.brand-icon {
  flex-shrink: 0; width: 36px; height: 36px;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.25);
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
}
.brand-icon svg { width: 20px; height: 20px; color: #fff; }
.brand-text { display: flex; flex-direction: column; min-width: 0; }
.brand-empresa {
  font-size: 0.875rem; font-weight: 700; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.brand-tag { font-size: 0.6875rem; color: rgba(255,255,255,0.5); font-weight: 500; }

.collapse-btn {
  position: absolute; top: 18px; right: -13px;
  width: 26px; height: 26px; background: var(--sidebar-to, #7C3AED);
  border: 1px solid rgba(255,255,255,0.25); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #fff; transition: background 0.2s; z-index: 10;
}
.collapse-btn:hover { background: var(--sidebar-from, #4F46E5); }
.collapse-btn svg { width: 14px; height: 14px; }

.nav { flex: 1; padding: 1rem 0.625rem; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
.nav-label-group {
  font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.45);
  text-transform: uppercase; letter-spacing: 0.08em;
  padding: 0 0.5rem; margin: 0 0 0.5rem;
}
.nav-item {
  position: relative; display: flex; align-items: center; gap: 0.75rem;
  padding: 0.6rem 0.75rem; border-radius: 10px; text-decoration: none;
  color: rgba(255,255,255,0.7); font-size: 0.875rem; font-weight: 500;
  transition: background 0.15s, color 0.15s; white-space: nowrap;
}
.nav-item:hover { background: rgba(255,255,255,0.12); color: #fff; }
.nav-item.active { background: rgba(255,255,255,0.18); color: #fff; font-weight: 600; }
.nav-icon { flex-shrink: 0; display: flex; align-items: center; }
.nav-icon svg { width: 20px; height: 20px; }
.nav-label { flex: 1; }
.active-bar { width: 3px; height: 16px; background: #fff; border-radius: 2px; }

.main-content {
  margin-left: 240px; flex: 1; min-height: 100vh;
  transition: margin-left 0.25s ease;
  display: flex; flex-direction: column;
}
.sidebar.collapsed ~ .main-content { margin-left: 68px; }

.topbar {
  height: 64px; background: #fff; border-bottom: 1px solid #E5E7EB;
  display: flex; align-items: center; justify-content: flex-end;
  padding: 0 1.5rem; flex-shrink: 0;
}
.topbar-right { display: flex; align-items: center; gap: 0.75rem; }
.session-pill {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.3rem 0.75rem 0.3rem 0.4rem;
  background: #F3F4F6; border-radius: 50px;
}
.session-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 0.8125rem; font-weight: 700; flex-shrink: 0;
}
.session-details { display: flex; flex-direction: column; }
.session-name { font-size: 0.8125rem; font-weight: 600; color: #111827; line-height: 1.2; }
.session-role { font-size: 0.6875rem; color: #6B7280; }
.topbar-logout {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.45rem 0.875rem; border-radius: 8px;
  border: 1px solid #E5E7EB; background: #fff;
  color: #6B7280; font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; transition: background 0.15s, color 0.15s, border-color 0.15s; font-family: inherit;
}
.topbar-logout:hover { background: #FEF2F2; border-color: #FECACA; color: #DC2626; }
.topbar-logout svg { width: 16px; height: 16px; }
.page-content { flex: 1; overflow-y: auto; }

/* Badge de solicitudes en el sidebar */
.nav-badge {
  position: absolute; top: -5px; right: -6px;
  min-width: 16px; height: 16px; border-radius: 9999px;
  background: #EF4444; color: #fff;
  font-size: 0.6rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px; line-height: 1; border: 1.5px solid transparent;
  pointer-events: none;
}
.nav-badge-inline {
  margin-left: auto; min-width: 20px; height: 18px;
  border-radius: 9999px; background: #EF4444; color: #fff;
  font-size: 0.65rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  padding: 0 5px; pointer-events: none;
}
</style>
