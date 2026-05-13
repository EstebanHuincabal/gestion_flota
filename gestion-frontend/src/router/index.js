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
import Planes from '../web/configuracion/Configuracion.vue'
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

// Layout empresa (solo USUARIO)
import EmpresaLayout from '../web/empresa/EmpresaLayout.vue'

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
      { path: 'mantenciones/:id/editar', component: MantencionesForm },
      { path: 'mantenciones/historial',  component: MantencionesHistorial },
      { path: 'documentos',   component: Pendiente('Documentos')    },
      { path: 'finanzas',     component: Pendiente('Finanzas')      },
      { path: 'reportes',     component: Pendiente('Reportes')      },
    ],
  },

  // ── Panel Empresa (solo USUARIO) ──────────────────────
  {
    path: '/empresa',
    component: EmpresaLayout,
    meta: { requiresAuth: true, roles: ['USUARIO'] },
    children: [
      { path: 'dashboard',                            component: Dashboard },
      { path: 'flota',                                component: ListaFlota       },
      { path: 'flota/nueva',                          component: NuevaFlota       },
      { path: 'flota/:id/editar',                     component: EditarFlota      },
      { path: 'flota/:flotaId/nuevo-vehiculo',         component: FormVehiculo, props: { modo: 'nuevo' } },
      { path: 'vehiculos/:id/editar',                  component: FormVehiculo, props: { modo: 'editar' } },
      { path: 'conductores',              component: ListaConductores },
      { path: 'conductores/nuevo',        component: NuevoConductor  },
      { path: 'conductores/:id',          component: DetalleConductor },
      { path: 'conductores/:id/editar',   component: EditarConductor },
      { path: 'mantenciones',            component: MantencionesLista },
      { path: 'mantenciones/calendario', component: MantencionesCalendario },
      { path: 'mantenciones/nueva',      component: MantencionesForm },
      { path: 'mantenciones/:id/editar', component: MantencionesForm },
      { path: 'mantenciones/historial',  component: MantencionesHistorial },
      { path: 'documentos',   component: Pendiente('Documentos')    },
      { path: 'finanzas',     component: Pendiente('Finanzas')      },
      { path: 'reportes',     component: Pendiente('Reportes')      },
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

  next()
})

export default router
