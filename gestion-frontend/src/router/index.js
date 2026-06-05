import { createRouter, createWebHistory } from 'vue-router'
import Login from '../web/login.vue'

// Layout SUPERADMIN
import Base from '../web/Base.vue'
import Dashboard from '../web/Dashboard.vue'
import ListaEmpresas from '../web/clientes/ListaEmpresas.vue'
import NuevaEmpresa  from '../web/clientes/NuevaEmpresa.vue'
import DetalleEmpresa from '../web/clientes/DetalleEmpresa.vue'
import EditarEmpresa from '../web/clientes/EditarEmpresa.vue'
import ListaUsuarios from '../web/usuarios/ListaUsuarios.vue'
import NuevoUsuario  from '../web/usuarios/NuevoUsuario.vue'
import EditarUsuario from '../web/usuarios/EditarUsuario.vue'
import Planes from '../web/configuracion/Planes.vue'
import ConfiguracionPage from '../web/configuracion/ConfiguracionPage.vue'
import Logs from '../web/logs/Logs.vue'
import GestionPermisos from '../web/permisos/GestionPermisos.vue'

// Componentes operativos (compartidos entre Base y EmpresaLayout)
import ListaFlota       from '../web/empresa/flota/ListaFlota.vue'
import FormVehiculo     from '../web/empresa/flota/FormVehiculo.vue'
import ListaConductores from '../web/empresa/conductores/ListaConductores.vue'
import NuevoConductor   from '../web/empresa/conductores/NuevoConductor.vue'
import EditarConductor  from '../web/empresa/conductores/EditarConductor.vue'
import DetalleConductor from '../web/empresa/conductores/DetalleConductor.vue'
import MantencionesLista      from '../web/empresa/flota/mantenciones/MantencionesLista.vue'
import MantencionesCalendario from '../web/empresa/flota/mantenciones/MantencionesCalendario.vue'
import MantencionesForm       from '../web/empresa/flota/mantenciones/MantencionesForm.vue'
import MantencionesHistorial  from '../web/empresa/flota/mantenciones/MantencionesHistorial.vue'
import MantencionesDetalle    from '../web/empresa/flota/mantenciones/MantencionesDetalle.vue'
import MantencionPredictiva   from '../web/empresa/predictivo/MantencionPredictiva.vue'
import Notificaciones             from '../web/notificaciones/Notificaciones.vue'
import PreferenciasNotificaciones from '../web/notificaciones/PreferenciasNotificaciones.vue'

// Layout empresa (solo USUARIO)
import EmpresaLayout from '../web/empresa/EmpresaLayout.vue'

// Finanzas
import FinanzasEmpresa    from '../web/finanzas/FinanzasEmpresa.vue'
import FinanzasSuperAdmin from '../web/finanzas/FinanzasSuperAdmin.vue'
import GastosCorrectivosAdmin from '../web/finanzas/GastosCorrectivosAdmin.vue'
import GastosCorrectivosEmpresa from '../web/finanzas/GastosCorrectivosEmpresa.vue'

// Reportes
import ReportesEmpresa    from '../web/reportes/ReportesEmpresa.vue'
import ReportesSuperAdmin from '../web/reportes/ReportesSuperAdmin.vue'

// Documentos
import Documentos from '../web/documentos/Documentos.vue'

// Rutas y trabajos
import Rutas from '../web/rutas/Rutas.vue'

// Solicitudes de conductores (panel web)
import SolicitudesConductores from '../web/solicitudes/SolicitudesConductores.vue'
import SolicitudesAdmin       from '../web/solicitudes/SolicitudesAdmin.vue'

// Avisos
import Avisos from '../web/avisos/Avisos.vue'

// Calendario global
import CalendarioGlobal from '../web/calendario/CalendarioGlobal.vue'

// Pagos y suscripciones
import IniciarPago     from '../web/pago/IniciarPago.vue'
import PagoExitoso    from '../web/pago/PagoExitoso.vue'
import PagoFallido    from '../web/pago/PagoFallido.vue'
import HistorialPagos from '../web/pago/HistorialPagos.vue'
import PagosSuperAdmin from '../web/admin/PagosSuperAdmin.vue'

const Pendiente = (titulo) => ({
  template: `<div style="padding:2rem 2.5rem"><h1 style="font-size:1.5rem;font-weight:700;color:#1E1B4B">${titulo}</h1><p style="color:#6B7280">Próximamente</p></div>`
})

// Rutas de empresa por prioridad para el aterrizaje y los redirects de fallback.
// La última (Configuración) no requiere permiso → siempre hay un destino válido.
const RUTAS_EMPRESA_PRIORIDAD = [
  { path: '/empresa/dashboard',     permiso: 'dashboard.ver' },
  { path: '/empresa/finanzas',      permiso: 'finanzas.ver' },
  { path: '/empresa/flota',         permiso: 'flotas.ver' },
  { path: '/empresa/mantenciones',  permiso: 'mantenciones.ver' },
  { path: '/empresa/conductores',   permiso: 'conductores.ver' },
  { path: '/empresa/rutas',         permiso: 'rutas.ver' },
  { path: '/empresa/documentos',    permiso: 'documentos.ver' },
  { path: '/empresa/configuracion', permiso: null },
]

// Primera ruta de empresa que el usuario puede ver según los permisos de su plan.
const primeraRutaEmpresa = () => {
  const permisos = safeJsonParse(sessionStorage.getItem('plan_permisos'), [])
  const lista = Array.isArray(permisos) ? permisos : []
  for (const r of RUTAS_EMPRESA_PRIORIDAD) {
    if (!r.permiso || lista.includes(r.permiso)) return r.path
  }
  return '/empresa/configuracion'
}

const homePorRol = (rol) => {
  if (rol === 'SUPERADMIN') return '/dashboard'
  if (rol === 'USUARIO')    return primeraRutaEmpresa()
  return '/login'
}

const routes = [
  // ── Sitio público (landing + registro) ───────────────────────────────────
  {
    path: '/',
    component: () => import('../web/publico/PublicLayout.vue'),
    children: [
      {
        path: '',
        name: 'landing',
        component: () => import('../web/publico/LandingPage.vue'),
      },
      {
        path: 'registro',
        name: 'registro',
        component: () => import('../web/publico/RegistroPublico.vue'),
      },
      {
        path: 'terminos',
        name: 'terminos',
        component: () => import('../web/publico/Terminos.vue'),
      },
    ],
  },

  { path: '/login', component: Login, meta: { guest: true } },

  // ── Panel SUPERADMIN ──────────────────────────────────
  {
    path: '/',
    component: Base,
    meta: { requiresAuth: true, roles: ['SUPERADMIN'] },
    children: [
      // Administración global
      { path: 'dashboard',              component: Dashboard },
      { path: 'empresas',               component: ListaEmpresas },
      { path: 'empresas/nueva',         component: NuevaEmpresa  },
      { path: 'empresas/:id',           component: DetalleEmpresa },
      { path: 'empresas/:id/editar',    component: EditarEmpresa },
      { path: 'usuarios',               component: ListaUsuarios },
      { path: 'usuarios/nuevo',         component: NuevoUsuario  },
      { path: 'usuarios/:id/editar',    component: EditarUsuario },
      { path: 'planes',                 component: Planes },
      { path: 'permisos',               component: GestionPermisos },
      { path: 'logs',                   component: Logs },
      { path: 'configuracion',          component: ConfiguracionPage },

      // Operaciones de empresa (sin prefijo /empresa/)
      { path: 'flota',                                    component: ListaFlota       },
      { path: 'vehiculos/nuevo',                          component: FormVehiculo, props: { modo: 'nuevo' } },
      { path: 'vehiculos/:id/editar',                     component: FormVehiculo, props: { modo: 'editar' } },
      { path: 'conductores',                              component: ListaConductores },
      { path: 'conductores/nuevo',                        component: NuevoConductor  },
      { path: 'conductores/:id',                          component: DetalleConductor },
      { path: 'conductores/:id/editar',                   component: EditarConductor },
      { path: 'mantenciones',            component: MantencionesLista },
      { path: 'mantenciones/calendario', component: MantencionesCalendario },
      { path: 'mantenciones/nueva',      component: MantencionesForm },
      { path: 'mantenciones/historial',  component: MantencionesHistorial },
      { path: 'mantenciones/:id',        component: MantencionesDetalle },
      { path: 'mantenciones/:id/editar', component: MantencionesForm },
      { path: 'predictivo', component: MantencionPredictiva },
      { path: 'notificaciones',             component: Notificaciones },
      { path: 'notificaciones/preferencias', component: PreferenciasNotificaciones },
      { path: 'documentos',   component: Documentos },
      { path: 'finanzas',     component: FinanzasSuperAdmin },
      { path: 'finanzas/correctivos', component: GastosCorrectivosAdmin },
      { path: 'reportes',     component: ReportesSuperAdmin },
      { path: 'rutas',        component: Rutas },
      { path: 'mapa',         component: () => import('../web/empresa/flota/MapaFlota.vue') },
      { path: 'gps',          component: () => import('../web/empresa/flota/GestionGPS.vue') },
      { path: 'solicitudes',  component: SolicitudesAdmin },
      { path: 'avisos',       component: Avisos },
      { path: 'calendario',   component: CalendarioGlobal },
      { path: 'pagos',        component: PagosSuperAdmin },
    ],
  },

  // ── Panel Empresa (solo USUARIO) ──────────────────────
  {
    path: '/empresa',
    component: EmpresaLayout,
    meta: { requiresAuth: true, roles: ['USUARIO'] },
    children: [
      { path: 'dashboard',                            component: Dashboard,        meta: { permiso: 'dashboard.ver' } },
      { path: 'flota',                                component: ListaFlota,       meta: { permiso: 'flotas.ver' } },
      { path: 'vehiculos/nuevo',                       component: FormVehiculo,     meta: { permiso: 'flotas.ver' }, props: { modo: 'nuevo' } },
      { path: 'vehiculos/:id/editar',                  component: FormVehiculo,     meta: { permiso: 'flotas.ver' }, props: { modo: 'editar' } },
      { path: 'conductores',              component: ListaConductores, meta: { permiso: 'conductores.ver' } },
      { path: 'conductores/nuevo',        component: NuevoConductor,  meta: { permiso: 'conductores.ver' } },
      { path: 'conductores/:id',          component: DetalleConductor, meta: { permiso: 'conductores.ver' } },
      { path: 'conductores/:id/editar',   component: EditarConductor,  meta: { permiso: 'conductores.ver' } },
      { path: 'mantenciones',            component: MantencionesLista,      meta: { permiso: 'mantenciones.ver' } },
      { path: 'mantenciones/calendario', component: MantencionesCalendario, meta: { permiso: 'mantenciones.ver' } },
      { path: 'mantenciones/nueva',      component: MantencionesForm,       meta: { permiso: 'mantenciones.ver' } },
      { path: 'mantenciones/historial',  component: MantencionesHistorial,  meta: { permiso: 'mantenciones.ver' } },
      { path: 'mantenciones/:id',        component: MantencionesDetalle,    meta: { permiso: 'mantenciones.ver' } },
      { path: 'mantenciones/:id/editar', component: MantencionesForm,       meta: { permiso: 'mantenciones.ver' } },
      { path: 'predictivo',              component: MantencionPredictiva,   meta: { permiso: 'mantenciones.ver' } },
      { path: 'notificaciones',              component: Notificaciones },
      { path: 'notificaciones/preferencias', component: PreferenciasNotificaciones },
      { path: 'documentos',      component: Documentos,       meta: { permiso: 'documentos.ver' } },
      { path: 'finanzas',        component: FinanzasEmpresa,  meta: { permiso: 'finanzas.ver' } },
      { path: 'correctivos',     component: GastosCorrectivosEmpresa, meta: { permiso: 'correctivos.ver' } },
      { path: 'reportes',        component: ReportesEmpresa },
      { path: 'rutas',           component: Rutas,                   meta: { permiso: 'rutas.ver' } },
      { path: 'mapa',            component: () => import('../web/empresa/flota/MapaFlota.vue'),  meta: { permiso: 'gps.ver' } },
      { path: 'gps',             component: () => import('../web/empresa/flota/GestionGPS.vue'), meta: { permiso: 'gps.ver' } },
      { path: 'avisos',          component: Avisos,                  meta: { permiso: 'avisos.ver' } },
      { path: 'solicitudes',     component: SolicitudesConductores },
      { path: 'solicitudes/:id', component: SolicitudesConductores },   // notificaciones que apuntan al detalle
      { path: 'calendario',      component: CalendarioGlobal,        meta: { permiso: 'calendario.ver' } },
      { path: 'configuracion',   component: ConfiguracionPage },
      { path: 'pago',            component: IniciarPago },
      { path: 'pago/exitoso',    component: PagoExitoso },
      { path: 'pago/fallido',    component: PagoFallido },
      { path: 'pagos',           component: HistorialPagos },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function safeJsonParse(str, fallback) {
  try { return JSON.parse(str) } catch { return fallback }
}

// Devuelve true si el JWT no existe, está corrupto o ya venció (lee su `exp`).
function tokenExpirado(token) {
  if (!token) return true
  try {
    const payload = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
    )
    if (typeof payload.exp !== 'number') return false   // sin exp → no podemos afirmar que venció
    return payload.exp * 1000 < Date.now()
  } catch {
    return true   // token ilegible → tratar como expirado
  }
}

// Limpia toda la sesión local (igual que api.js / useSessionTimer).
function limpiarSesionLocal() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('plan_permisos')
  sessionStorage.removeItem('empresaActiva')
}

router.beforeEach((to, _from, next) => {
  let usuario = safeJsonParse(localStorage.getItem('usuario'), null)

  if (usuario && !usuario.rol) {
    localStorage.removeItem('usuario')
    usuario = null
  }

  // Sesión vieja en caché: hay 'usuario' guardado pero el refresh token ya venció.
  // El backend la rechazaría igual; se limpia acá para no entrar a una ruta
  // protegida con una sesión muerta (y evitar la alerta de "sin conexión/sesión").
  if (usuario && tokenExpirado(localStorage.getItem('refresh_token'))) {
    limpiarSesionLocal()
    usuario = null
  }

  // Rutas públicas (landing y registro): redirigir si ya está autenticado
  if ((to.name === 'landing' || to.name === 'registro') && usuario?.rol) {
    return next(homePorRol(usuario.rol))
  }

  if (to.meta.requiresAuth && !usuario) return next('/login')
  if (to.meta.guest && usuario) return next(homePorRol(usuario.rol))

  if (to.meta.roles && usuario && !to.meta.roles.includes(usuario.rol)) {
    return next(homePorRol(usuario.rol))
  }

  // Guard de permisos de plan: solo aplica a rutas de empresa (USUARIO)
  if (to.meta.permiso && usuario?.rol === 'USUARIO') {
    const planPermisos = safeJsonParse(sessionStorage.getItem('plan_permisos'), [])
    const lista = Array.isArray(planPermisos) ? planPermisos : []
    if (!lista.includes(to.meta.permiso)) {
      // Redirige a la primera ruta accesible (evita loop si no tiene dashboard).
      const destino = primeraRutaEmpresa()
      return next(destino === to.path ? '/empresa/configuracion' : destino)
    }
  }

  next()
})

export default router
