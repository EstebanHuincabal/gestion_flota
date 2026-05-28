/**
 * router/index.js — Rutas de la app de conductores.
 *
 * Guard global:
 *  - Ruta protegida sin sesión          → redirige a /login
 *  - Ruta pública con sesión            → redirige según módulos del plan
 *  - Ruta con meta.modulo no en el plan → redirige silenciosamente a /solicitudes
 *  - useAuthStore se importa dinámicamente para evitar dependencia circular
 */
import { createRouter, createWebHistory } from 'vue-router'
import { Preferences } from '@capacitor/preferences'

const routes = [
  { path: '/', redirect: '/login' },

  // ── Pública ──────────────────────────────────────────────────────────────
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { publica: true },
  },

  // ── Protegidas — sin módulo requerido ────────────────────────────────────
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/views/Onboarding/SubirDocumentos.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/solicitudes',
    name: 'solicitudes',
    component: () => import('@/views/Solicitudes/ListaSolicitudes.vue'),
    meta: { requiereAuth: true, modulo: 'solicitudes' },
  },
  {
    path: '/mantencion',
    name: 'mantencion',
    component: () => import('@/views/Mantenciones/MiMantencion.vue'),
    meta: { requiereAuth: true, modulo: 'mantenciones' },
  },
  {
    path: '/mantencion/historial',
    name: 'historial-mantencion',
    component: () => import('@/views/Mantenciones/HistorialMantenciones.vue'),
    meta: { requiereAuth: true, modulo: 'mantenciones' },
  },
  {
    path: '/documentos',
    name: 'documentos',
    component: () => import('@/views/Documentos/MisDocumentos.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/ajustes',
    name: 'ajustes',
    component: () => import('@/views/Ajustes/Ajustes.vue'),
    meta: { requiereAuth: true },
  },

  // ── Protegidas — módulo 'rutas' requerido ────────────────────────────────
  {
    path: '/rutas',
    name: 'rutas',
    component: () => import('@/views/Rutas/ListaRutas.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' },
  },
  {
    path: '/rutas/:id',
    name: 'detalle-ruta',
    component: () => import('@/views/Rutas/DetalleRuta.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' },
  },
  {
    path: '/rutas/:id/checklist',
    name: 'checklist-previaje',
    component: () => import('@/views/Rutas/ChecklistPreviaje.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/** Lee los módulos del plan desde Preferences de forma segura */
async function leerModulos() {
  try {
    const { value } = await Preferences.get({ key: 'plan_modulos' })
    const parsed = JSON.parse(value || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/**
 * Devuelve la ruta del primer módulo disponible según el plan.
 * Orden de prioridad: rutas → solicitudes → mantenciones → ajustes (siempre disponible).
 */
function _primerModuloDisponible(modulosArray) {
  if (modulosArray.includes('rutas'))        return { name: 'rutas' }
  if (modulosArray.includes('solicitudes'))  return { name: 'solicitudes' }
  if (modulosArray.includes('mantenciones')) return { name: 'mantencion' }
  return { name: 'ajustes' }
}

/** Guard de navegación global */
router.beforeEach(async (to) => {
  // Importación dinámica para evitar dependencia circular con stores/auth
  const { useAuthStore } = await import('@/stores/auth.js')
  const auth = useAuthStore()

  // Restaurar sesión si el store aún no tiene usuario cargado
  if (!auth.usuario) await auth.cargarSesion()

  // Sin sesión → redirigir al login
  if (to.meta.requiereAuth && !auth.estaAutenticado) return { name: 'login' }

  // Leer módulos una sola vez si la ruta es pública con sesión o requiere módulo
  const necesitaModulos = (to.meta.publica && auth.estaAutenticado) || !!to.meta.modulo
  if (necesitaModulos) {
    const modulosArray = await leerModulos()

    // Con sesión en ruta pública → redirigir al primer módulo disponible
    if (to.meta.publica && auth.estaAutenticado) {
      return _primerModuloDisponible(modulosArray)
    }

    // Si la ruta requiere un módulo que no está en el plan → redirigir
    if (to.meta.modulo && !modulosArray.includes(to.meta.modulo)) {
      return _primerModuloDisponible(modulosArray)
    }
  }

  return true
})

export default router
