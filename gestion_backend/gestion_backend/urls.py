from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from g_de_flota.views import (
    home_view, login_view, dashboard_global_view, empresa_dashboard_view,
    empresas_lista, empresas_crear, empresas_detalle,
    usuarios_lista, usuarios_crear, usuarios_detalle,
    usuario_reset_password, usuario_toggle_block, usuario_historial,
    conductores_lista_crear, conductores_detalle, conductores_asignar, conductores_desasignar,
    admin_flotas_lista, flotas_lista_crear, flotas_detalle,
    vehiculos_lista_crear, vehiculos_detalle,
    mantenciones_lista_crear, mantenciones_detalle, mantenciones_resumen,
    mantenciones_calendario, mantenciones_sugerencias,
    logs_lista,
    permisos_lista, usuario_permisos,
    PlanMantenimientoViewSet, AlertaMantencionViewSet, simulador_vencimientos,
    vehiculo_planes_lista_crear, vehiculo_plan_detalle,
    predictivo_resumen, predictivo_generar_alertas,
    notificaciones_lista, notificaciones_no_leidas, notificaciones_leer, notificaciones_preferencias,
)
from g_de_flota.views_planes import (
    planes_lista_crear, planes_detalle,
    plan_asignar_empresa, plan_uso, plan_permisos,
    solicitar_cambio_plan,
)
from g_de_flota.views_config import (
    usuario_perfil, usuario_cambiar_password, plan_historial,
)
from g_de_flota.views_gastos import (
    GastosListView, GastoDetailView, GastosExportarView,
    PresupuestoView, PresupuestoDetailView,
    FinanzasSaasView, FinanzasHistoricoView,
)
from g_de_flota.views_reportes import (
    reporte_mantencion, reporte_flota, reporte_exportar, reporte_admin_empresas,
    reporte_tco, reporte_conductores,
)
from g_de_flota.views_documentos import (
    DocumentosListView, DocumentoDetailView,
    DocumentoDescargarView, DocumentoRenovarView,
)

router = DefaultRouter()
router.register(r'empresa/planes-mantenimiento', PlanMantenimientoViewSet, basename='planes-mantenimiento')
router.register(r'empresa/alertas-mantenimiento', AlertaMantencionViewSet, basename='alertas-mantenimiento')

urlpatterns = [
    path('',                          home_view,         name='home'),
    path('admin/',                    admin.site.urls),
    path('api/login/',                login_view,           name='login'),
    path('api/token/refresh/',        TokenRefreshView.as_view(), name='token-refresh'),
    
    path('api/dashboard/',            dashboard_global_view,  name='dashboard-global'),
    path('api/empresa/dashboard/',    empresa_dashboard_view, name='empresa-dashboard'),

    # Configuración Global del Sistema — Planes de Suscripción
    path('api/configuracion/planes/',               planes_lista_crear,      name='config-planes-lista'),
    path('api/configuracion/planes/<int:pk>/',      planes_detalle,          name='config-planes-detalle'),
    path('api/configuracion/planes/<int:pk>/asignar/',   plan_asignar_empresa, name='config-planes-asignar'),
    path('api/configuracion/planes/<int:pk>/permisos/', plan_permisos,        name='config-planes-permisos'),
    path('api/empresa/plan-uso/',                   plan_uso,                name='empresa-plan-uso'),
    path('api/empresa/solicitar-cambio-plan/',      solicitar_cambio_plan,   name='empresa-solicitar-plan'),

    path('api/empresas/',             empresas_lista,    name='empresas-lista'),
    path('api/empresas/crear/',       empresas_crear,    name='empresas-crear'),
    path('api/empresas/<int:pk>/',    empresas_detalle,  name='empresas-detalle'),

    path('api/usuarios/',             usuarios_lista,    name='usuarios-lista'),
    path('api/usuarios/crear/',       usuarios_crear,    name='usuarios-crear'),
    path('api/usuarios/<int:pk>/',    usuarios_detalle,  name='usuarios-detalle'),
    path('api/usuarios/<int:pk>/reset-password/', usuario_reset_password, name='usuario-reset-password'),
    path('api/usuarios/<int:pk>/toggle-block/',   usuario_toggle_block,   name='usuario-toggle-block'),
    path('api/usuarios/<int:pk>/historial/',      usuario_historial,      name='usuario-historial'),

    path('api/empresa/conductores/',                        conductores_lista_crear,  name='conductores-lista'),
    path('api/empresa/conductores/<int:pk>/',               conductores_detalle,      name='conductores-detalle'),
    path('api/empresa/conductores/<int:pk>/asignar/',       conductores_asignar,      name='conductores-asignar'),
    path('api/empresa/conductores/<int:pk>/desasignar/',    conductores_desasignar,   name='conductores-desasignar'),

    path('api/admin/flotas/',                admin_flotas_lista,    name='admin-flotas'),
    path('api/empresa/flotas/',              flotas_lista_crear,    name='flotas-lista'),
    path('api/empresa/flotas/<int:pk>/',     flotas_detalle,        name='flotas-detalle'),
    path('api/empresa/vehiculos/',           vehiculos_lista_crear, name='vehiculos-lista'),
    path('api/empresa/vehiculos/<int:pk>/',  vehiculos_detalle,     name='vehiculos-detalle'),
    
    path('api/empresa/mantenciones/',              mantenciones_lista_crear,  name='mantenciones-lista'),
    path('api/empresa/mantenciones/resumen/',      mantenciones_resumen,      name='mantenciones-resumen'),
    path('api/empresa/mantenciones/calendario/',   mantenciones_calendario,   name='mantenciones-calendario'),
    path('api/empresa/mantenciones/sugerencias/', mantenciones_sugerencias,   name='mantenciones-sugerencias'),
    path('api/empresa/mantenciones/<int:pk>/',     mantenciones_detalle,      name='mantenciones-detalle'),

    path('api/', include(router.urls)),
    path('api/empresa/simulador-vencimientos/',    simulador_vencimientos,        name='simulador-vencimientos'),
    path('api/empresa/vehiculo-planes/',           vehiculo_planes_lista_crear,   name='vehiculo-planes-lista'),
    path('api/empresa/vehiculo-planes/<int:pk>/',  vehiculo_plan_detalle,         name='vehiculo-planes-detalle'),
    path('api/empresa/predictivo/resumen/',        predictivo_resumen,            name='predictivo-resumen'),
    path('api/empresa/predictivo/generar-alertas/', predictivo_generar_alertas,   name='predictivo-generar-alertas'),

    path('api/logs/',                        logs_lista,            name='logs-lista'),

    path('api/usuario/perfil/',              usuario_perfil,             name='usuario-perfil'),
    path('api/usuario/cambiar-password/',    usuario_cambiar_password,   name='usuario-cambiar-password'),
    path('api/empresa/plan-historial/',      plan_historial,             name='plan-historial'),

    path('api/permisos/',                              permisos_lista,   name='permisos-lista'),
    path('api/usuarios/<int:pk>/permisos/',            usuario_permisos, name='usuario-permisos'),

    path('api/notificaciones/',              notificaciones_lista,         name='notificaciones-lista'),
    path('api/notificaciones/no-leidas/',    notificaciones_no_leidas,     name='notificaciones-no-leidas'),
    path('api/notificaciones/leer/',         notificaciones_leer,          name='notificaciones-leer'),
    path('api/notificaciones/preferencias/', notificaciones_preferencias,  name='notificaciones-preferencias'),

    # Finanzas — gastos operativos (USUARIO)
    path('api/empresa/gastos/',                  GastosListView.as_view(),       name='gastos-lista'),
    path('api/empresa/gastos/exportar/',         GastosExportarView.as_view(),   name='gastos-exportar'),
    path('api/empresa/gastos/<int:gasto_id>/',   GastoDetailView.as_view(),      name='gastos-detalle'),
    path('api/empresa/presupuesto/',             PresupuestoView.as_view(),      name='presupuesto-lista'),
    path('api/empresa/presupuesto/<int:pk>/',    PresupuestoDetailView.as_view(), name='presupuesto-detalle'),

    # Finanzas — dashboard SaaS (SUPERADMIN)
    path('api/admin/finanzas/',              FinanzasSaasView.as_view(),      name='finanzas-saas'),
    path('api/admin/finanzas/historico/',    FinanzasHistoricoView.as_view(), name='finanzas-historico'),

    # Documentos
    path('api/empresa/documentos/',                          DocumentosListView.as_view(),    name='documentos-lista'),
    path('api/empresa/documentos/<int:doc_id>/',             DocumentoDetailView.as_view(),   name='documentos-detalle'),
    path('api/empresa/documentos/<int:doc_id>/descargar/',   DocumentoDescargarView.as_view(), name='documentos-descargar'),
    path('api/empresa/documentos/<int:doc_id>/renovar/',     DocumentoRenovarView.as_view(),  name='documentos-renovar'),

    # Reportes
    path('api/empresa/reportes/mantencion/', reporte_mantencion,       name='reporte-mantencion'),
    path('api/empresa/reportes/flota/',      reporte_flota,            name='reporte-flota'),
    path('api/empresa/reportes/exportar/',   reporte_exportar,         name='reporte-exportar'),
    path('api/empresa/reportes/tco/',        reporte_tco,              name='reporte-tco'),
    path('api/empresa/reportes/conductores/', reporte_conductores,     name='reporte-conductores'),
    path('api/admin/reportes/empresas/',     reporte_admin_empresas,   name='reporte-admin-empresas'),
]
