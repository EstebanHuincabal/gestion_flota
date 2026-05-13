from django.contrib import admin
from django.urls import path
from g_de_flota.views import (
    home_view, login_view, dashboard_global_view, empresa_dashboard_view,
    empresas_lista, empresas_crear, empresas_detalle,
    usuarios_lista, usuarios_crear, usuarios_detalle,
    usuario_reset_password, usuario_toggle_block, usuario_historial,
    conductores_lista_crear, conductores_detalle, conductores_asignar, conductores_desasignar,
    admin_flotas_lista, flotas_lista_crear, flotas_detalle,
    vehiculos_lista_crear, vehiculos_detalle,
    planes_lista_crear, planes_detalle,
    mantenciones_lista_crear, mantenciones_detalle, mantenciones_resumen, mantenciones_calendario,
    logs_lista,
    permisos_lista, usuario_permisos,
)

urlpatterns = [
    path('',                          home_view,         name='home'),
    path('admin/',                    admin.site.urls),
    path('api/login/',                login_view,        name='login'),
    
    path('api/dashboard/',            dashboard_global_view,  name='dashboard-global'),
    path('api/empresa/dashboard/',    empresa_dashboard_view, name='empresa-dashboard'),

    # Configuración Global del Sistema
    path('api/configuracion/planes/',     planes_lista_crear,         name='config-planes-lista'),
    path('api/configuracion/planes/<int:pk>/', planes_detalle,        name='config-planes-detalle'),

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
    path('api/empresa/mantenciones/<int:pk>/',     mantenciones_detalle,      name='mantenciones-detalle'),

    path('api/logs/',                        logs_lista,            name='logs-lista'),

    path('api/permisos/',                              permisos_lista,   name='permisos-lista'),
    path('api/usuarios/<int:pk>/permisos/',            usuario_permisos, name='usuario-permisos'),
]
