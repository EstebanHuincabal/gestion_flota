/**
 * router/index.js — Rutas de la app de conductores.
 *
 * Guard global:
 *  - Ruta protegida sin sesión  → redirige a /login
 *  - Ruta pública con sesión    → redirige a /rutas
 *  - useAuthStore se importa dinámicamente para evitar dependencia circular
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/login' },

  // ── Pública ──────────────────────────────────────────────────────────────
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { publica: true },
  },

  // ── Protegidas ───────────────────────────────────────────────────────────
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/views/Onboarding/SubirDocumentos.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/rutas',
    name: 'rutas',
    component: () => import('@/views/Rutas/ListaRutas.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/rutas/:id',
    name: 'detalle-ruta',
    component: () => import('@/views/Rutas/DetalleRuta.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/solicitudes',
    name: 'solicitudes',
    component: () => import('@/views/Solicitudes/ListaSolicitudes.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/mantencion',
    name: 'mantencion',
    component: () => import('@/views/Mantenciones/MiMantencion.vue'),
    meta: { requiereAuth: true },
  },
  {
    path: '/ajustes',
    name: 'ajustes',
    component: () => import('@/views/Ajustes/Ajustes.vue'),
    meta: { requiereAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/** Guard de navegación global */
router.beforeEach(async (to) => {
  // Importación dinámica para evitar dependencia circular con stores/auth
  const { useAuthStore } = await import('@/stores/auth.js')
  const auth = useAuthStore()

  // Restaurar sesión si el store aún no tiene usuario cargado
  if (!auth.usuario) await auth.cargarSesion()

  if (to.meta.requiereAuth && !auth.estaAutenticado) return { name: 'login' }
  if (to.meta.publica     &&  auth.estaAutenticado) return { name: 'rutas' }
  return true
})

export default router
