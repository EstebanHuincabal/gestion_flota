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
import NuevaFlota       from '../web/empresa/flota/NuevaFlota.vue'
import EditarFlota      from '../web/empresa/flota/EditarFlota.vue'
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

const homePorRol = (rol) => {
  if (rol === 'SUPERADMIN') return '/dashboard'
  if (rol === 'USUARIO')    return '/empresa/dashboard'
  return '/login'
}

const routes = [
  { path: '/', redirect: '/login' },
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
      { path: 'flota/nueva',                              component: NuevaFlota       },
      { path: 'flota/:id/editar',                         component: EditarFlota      },
      { path: 'flota/:flotaId/nuevo-vehiculo',            component: FormVehiculo, props: { modo: 'nuevo' } },
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
      { path: 'reportes',     component: ReportesSuperAdmin },
      { path: 'rutas',        component: Rutas },
      { path: 'solicitudes',  component: SolicitudesAdmin },
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
      { path: 'dashboard',                            component: Dashboard },
      { path: 'flota',                                component: ListaFlota,       meta: { permiso: 'flotas.ver' } },
      { path: 'flota/nueva',                          component: NuevaFlota,       meta: { permiso: 'flotas.ver' } },
      { path: 'flota/:id/editar',                     component: EditarFlota,      meta: { permiso: 'flotas.ver' } },
      { path: 'flota/:flotaId/nuevo-vehiculo',         component: FormVehiculo,     meta: { permiso: 'flotas.ver' }, props: { modo: 'nuevo' } },
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
      { path: 'reportes',        component: ReportesEmpresa },
      { path: 'rutas',           component: Rutas,                   meta: { permiso: 'rutas.ver' } },
      { path: 'solicitudes',     component: SolicitudesConductores },
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

router.beforeEach((to, _from, next) => {
  let usuario = JSON.parse(localStorage.getItem('usuario') || 'null')

  if (usuario && !usuario.rol) {
    localStorage.removeItem('usuario')
    usuario = null
  }

  if (to.meta.requiresAuth && !usuario) return next('/login')
  if (to.meta.guest && usuario) return next(homePorRol(usuario.rol))

  if (to.meta.roles && usuario && !to.meta.roles.includes(usuario.rol)) {
    return next(homePorRol(usuario.rol))
  }

  // Guard de permisos de plan: solo aplica a rutas de empresa (USUARIO)
  if (to.meta.permiso && usuario?.rol === 'USUARIO') {
    const planPermisos = JSON.parse(sessionStorage.getItem('plan_permisos') || '[]')
    if (!planPermisos.includes(to.meta.permiso)) {
      return next('/empresa/dashboard')
    }
  }

  next()
})

export default router
