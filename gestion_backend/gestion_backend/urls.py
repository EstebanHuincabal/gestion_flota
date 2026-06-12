from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from g_de_flota.views_auth import TokenRefreshSeguroView
from g_de_flota.views import (
    home_view, login_view, usuario_recuperar_password, dashboard_global_view, empresa_dashboard_view,
    empresas_lista, empresas_crear, empresas_detalle,
    usuarios_lista, usuarios_crear, usuarios_detalle,
    usuario_reset_password, usuario_toggle_block, usuario_historial,
    conductores_lista_crear, conductores_detalle, conductores_asignar, conductores_desasignar,
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
    solicitar_cambio_plan, cambiar_plan_self_service, cancelar_cambio_programado,
    # Transbank Webpay Plus
    PagoIniciarView, PagoRetornoView, PagoHistorialView,
    # Términos y suscripciones
    TerminosView, TerminosPublicosView, TerminosAceptarView,
    SuscripcionEmpresaView, SuscripcionesAdminView,
    # OneClick — tarjeta guardada
    TarjetaEstadoView, TarjetaInscribirView,
    TarjetaInscripcionRetornoView, TarjetaEliminarView,
    # Email
    EmailConfigView, EmailTestView,
)
from g_de_flota.views_config import (
    usuario_perfil, usuario_cambiar_password, plan_historial,
)
from g_de_flota.views_gastos import (
    GastosListView, GastoDetailView,
    PresupuestoView, PresupuestoDetailView,
    FinanzasSaasView, FinanzasHistoricoView,
    GastosCorrectivosList, GastoCorrectivoDetail, GastoCorrectivoComprobante,
)
from g_de_flota.views_reportes import (
    reporte_mantencion, reporte_flota, reporte_exportar, reporte_admin_empresas,
    reporte_admin_saas,
    reporte_tco, reporte_conductores,
    reporte_presupuesto, reporte_documentos, reporte_combustible,
    reporte_rutas, reporte_solicitudes,
)
from g_de_flota.views_documentos import (
    DocumentosListView, DocumentoDetailView,
    DocumentoDescargarView, DocumentoRenovarView,
)
from g_de_flota.views_rutas import (
    RutasListView, RutaDetailView,
    RutaIniciarView, RutaFinalizarView, RutaCancelarView,
    RouteCalcularView, RutaValidarView, RutaComentariosView,
)
from g_de_flota.views_conductor import (
    conductor_rutas, conductor_detalle_ruta,
    conductor_iniciar_ruta, conductor_finalizar_ruta,
    conductor_solicitudes,
    conductor_mantenciones, conductor_historial_mantenciones,
    conductor_mantencion_detalle,
    conductor_iniciar_mantencion, conductor_completar_mantencion,
    conductor_push_token,
    conductor_checklist,
    conductor_mi_plan,
    conductor_eventos_ruta, conductor_agregar_comentario,
    conductor_actualizar_perfil,
    conductor_recuperar_password,
    conductor_cambiar_password,
    conductor_subir_foto_vehiculo,
)
from g_de_flota.views_solicitudes import (
    SolicitudesListView, SolicitudesConteoView,
    SolicitudDetailView, SolicitudAprobarView, SolicitudRechazarView,
)
from g_de_flota.views_calendario import calendario_eventos
from g_de_flota import views_gps
from g_de_flota.views_publico import PlanesPublicosView, AutoRegistroView, VerificarRutView
from g_de_flota.views_avisos import empresa_avisos, empresa_avisos_conductores, conductor_avisos
from g_de_flota.views_moderacion import (
    moderar_texto, palabras_list,
    agregar_palabra, agregar_lote, eliminar_palabra,
)

router = DefaultRouter()
router.register(r'empresa/planes-mantenimiento', PlanMantenimientoViewSet, basename='planes-mantenimiento')
router.register(r'empresa/alertas-mantenimiento', AlertaMantencionViewSet, basename='alertas-mantenimiento')

urlpatterns = [
    path('',                          home_view,         name='home'),
    # Admin de Django solo disponible en desarrollo (DEBUG=True)
    *([path('admin/', admin.site.urls)] if settings.DEBUG else []),
    path('api/login/',                login_view,           name='login'),
    path('api/recuperar-password/',   usuario_recuperar_password, name='recuperar-password'),
    path('api/token/refresh/',        TokenRefreshSeguroView.as_view(), name='token-refresh'),
    
    path('api/dashboard/',            dashboard_global_view,  name='dashboard-global'),
    path('api/empresa/dashboard/',    empresa_dashboard_view, name='empresa-dashboard'),
    # Configuración Global del Sistema — Planes de Suscripción
    path('api/configuracion/planes/',               planes_lista_crear,      name='config-planes-lista'),
    path('api/configuracion/planes/<int:pk>/',      planes_detalle,          name='config-planes-detalle'),
    path('api/configuracion/planes/<int:pk>/asignar/',   plan_asignar_empresa, name='config-planes-asignar'),
    path('api/configuracion/planes/<int:pk>/permisos/', plan_permisos,        name='config-planes-permisos'),
    path('api/empresa/plan-uso/',                   plan_uso,                name='empresa-plan-uso'),
    path('api/empresa/solicitar-cambio-plan/',      solicitar_cambio_plan,   name='empresa-solicitar-plan'),
    path('api/empresa/cambiar-plan/',               cambiar_plan_self_service, name='empresa-cambiar-plan'),
    path('api/empresa/cancelar-cambio-plan/',       cancelar_cambio_programado, name='empresa-cancelar-cambio-plan'),

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

    # Finanzas — gastos correctivos (van ANTES de las rutas con <int:gasto_id>)
    path('api/empresa/gastos/correctivos/',                       GastosCorrectivosList.as_view(),     name='gastos-correctivos'),
    path('api/empresa/gastos/correctivos/<int:gasto_id>/',        GastoCorrectivoDetail.as_view(),     name='gastos-correctivo-detalle'),
    path('api/empresa/gastos/correctivos/<int:gasto_id>/comprobante/', GastoCorrectivoComprobante.as_view(), name='gastos-correctivo-comprobante'),

    # Finanzas — gastos operativos (USUARIO)
    path('api/empresa/gastos/',                  GastosListView.as_view(),       name='gastos-lista'),
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
    path('api/empresa/reportes/mantencion/',   reporte_mantencion,    name='reporte-mantencion'),
    path('api/empresa/reportes/flota/',        reporte_flota,         name='reporte-flota'),
    path('api/empresa/reportes/exportar/',     reporte_exportar,      name='reporte-exportar'),
    path('api/empresa/reportes/tco/',          reporte_tco,           name='reporte-tco'),
    path('api/empresa/reportes/conductores/',  reporte_conductores,   name='reporte-conductores'),
    path('api/empresa/reportes/presupuesto/',  reporte_presupuesto,   name='reporte-presupuesto'),
    path('api/empresa/reportes/documentos/',   reporte_documentos,    name='reporte-documentos'),
    path('api/empresa/reportes/combustible/',  reporte_combustible,   name='reporte-combustible'),
    path('api/empresa/reportes/rutas/',        reporte_rutas,         name='reporte-rutas'),
    path('api/empresa/reportes/solicitudes/',  reporte_solicitudes,   name='reporte-solicitudes'),
    path('api/admin/reportes/empresas/',       reporte_admin_empresas, name='reporte-admin-empresas'),
    path('api/admin/reportes/saas/',           reporte_admin_saas,     name='reporte-admin-saas'),

    # App conductores — endpoints exclusivos para la app móvil
    path('api/conductor/rutas/',                                    conductor_rutas,              name='conductor-rutas'),
    path('api/conductor/rutas/<int:ruta_id>/iniciar/',              conductor_iniciar_ruta,       name='conductor-iniciar-ruta'),
    path('api/conductor/rutas/<int:ruta_id>/finalizar/',            conductor_finalizar_ruta,     name='conductor-finalizar-ruta'),
    path('api/conductor/rutas/<int:ruta_id>/comentarios/',          conductor_eventos_ruta,       name='conductor-ruta-comentarios'),
    path('api/conductor/rutas/<int:ruta_id>/comentario/',           conductor_agregar_comentario, name='conductor-ruta-agregar-comentario'),
    path('api/conductor/rutas/<int:ruta_id>/',                      conductor_detalle_ruta,       name='conductor-detalle-ruta'),
    path('api/conductor/solicitudes/',                        conductor_solicitudes,     name='conductor-solicitudes'),
    path('api/conductor/mantenciones/',                               conductor_mantenciones,            name='conductor-mantenciones'),
    path('api/conductor/mantenciones/historial/',                     conductor_historial_mantenciones,  name='conductor-mantenciones-historial'),
    path('api/conductor/mantenciones/<int:mantencion_id>/',           conductor_mantencion_detalle,      name='conductor-mantencion-detalle'),
    path('api/conductor/mantenciones/<int:mantencion_id>/iniciar/',   conductor_iniciar_mantencion,    name='conductor-mantencion-iniciar'),
    path('api/conductor/mantenciones/<int:mantencion_id>/completar/', conductor_completar_mantencion,  name='conductor-mantencion-completar'),
    path('api/conductor/push-token/',                                 conductor_push_token,            name='conductor-push-token'),
    path('api/conductor/checklist/<int:ruta_id>/',                    conductor_checklist,              name='conductor-checklist'),
    path('api/conductor/mi-plan/',                                    conductor_mi_plan,               name='conductor-mi-plan'),
    path('api/conductor/perfil/',                                     conductor_actualizar_perfil,      name='conductor-perfil'),
    path('api/conductor/recuperar-password/',                         conductor_recuperar_password,      name='conductor-recuperar-password'),
    path('api/conductor/vehiculo/foto/',                              conductor_subir_foto_vehiculo,     name='conductor-vehiculo-foto'),
    path('api/conductor/cambiar-password/',                           conductor_cambiar_password,        name='conductor-cambiar-password'),
    path('api/conductor/avisos/',                                     conductor_avisos,                  name='conductor-avisos'),

    # Panel web — avisos internos
    path('api/empresa/avisos/',             empresa_avisos,             name='empresa-avisos'),
    path('api/empresa/avisos/conductores/', empresa_avisos_conductores, name='empresa-avisos-conductores'),

    # Panel web — gestión de solicitudes de conductores (USUARIO/ADMIN)
    path('api/empresa/solicitudes/',                              SolicitudesListView.as_view(),    name='solicitudes-lista'),
    path('api/empresa/solicitudes/conteo/',                       SolicitudesConteoView.as_view(),  name='solicitudes-conteo'),
    path('api/empresa/solicitudes/<int:sol_id>/',                 SolicitudDetailView.as_view(),    name='solicitudes-detalle'),
    path('api/empresa/solicitudes/<int:sol_id>/aprobar/',         SolicitudAprobarView.as_view(),   name='solicitudes-aprobar'),
    path('api/empresa/solicitudes/<int:sol_id>/rechazar/',        SolicitudRechazarView.as_view(),  name='solicitudes-rechazar'),

    # Calendario global
    path('api/empresa/calendario/', calendario_eventos, name='calendario-eventos'),

    # ── Geolocalización GPS ─────────────────────────────────────────────────────
    path('api/empresa/gps/dispositivos/',                    views_gps.DispositivosListView.as_view(),    name='gps-dispositivos'),
    path('api/empresa/gps/dispositivos/<int:id>/',           views_gps.DispositivoDetailView.as_view(),   name='gps-dispositivo-detalle'),
    path('api/empresa/gps/dispositivos/<int:id>/asignar/',   views_gps.AsignarVehiculoView.as_view(),     name='gps-asignar'),
    path('api/empresa/gps/dispositivos/<int:id>/desasignar/', views_gps.DesasignarVehiculoView.as_view(), name='gps-desasignar'),
    path('api/empresa/gps/dispositivos/<int:id>/regenerar-clave/', views_gps.RegenerarClaveView.as_view(), name='gps-regenerar-clave'),
    path('api/empresa/gps/posicion/',                        views_gps.PosicionView.as_view(),            name='gps-posicion'),
    path('api/empresa/gps/traccar/',                         views_gps.TraccarWebhookView.as_view(),      name='gps-traccar'),
    path('api/empresa/gps/vehiculos/posicion/',              views_gps.UltimasPosicionesView.as_view(),   name='gps-ultimas-posiciones'),

    # ── Transbank Webpay Plus ───────────────────────────────────────────────────
    path('api/pago/iniciar/',                          PagoIniciarView.as_view(),         name='pago-iniciar'),
    path('api/pago/retorno/',                          PagoRetornoView.as_view(),         name='pago-retorno'),
    path('api/pago/historial/',                        PagoHistorialView.as_view(),       name='pago-historial'),
    path('api/admin/terminos/',                        TerminosView.as_view(),            name='admin-terminos'),
    path('api/terminos/',                              TerminosPublicosView.as_view(),    name='terminos-publicos'),
    path('api/empresa/terminos/aceptar/',              TerminosAceptarView.as_view(),     name='terminos-aceptar'),
    path('api/empresa/suscripcion/',                   SuscripcionEmpresaView.as_view(),  name='empresa-suscripcion'),
    path('api/admin/suscripciones/',                   SuscripcionesAdminView.as_view(),  name='admin-suscripciones'),
    path('api/admin/suscripciones/<int:sus_id>/',      SuscripcionesAdminView.as_view(),  name='admin-suscripciones-detalle'),

    # ── Configuración de email ──────────────────────────────────────────────────
    path('api/admin/email/',                           EmailConfigView.as_view(),    name='admin-email-config'),
    path('api/admin/email/test/',                      EmailTestView.as_view(),      name='admin-email-test'),

    # ── OneClick Mall — tarjeta guardada ────────────────────────────────────────
    path('api/empresa/tarjeta/',                       TarjetaEstadoView.as_view(),              name='empresa-tarjeta'),
    path('api/empresa/tarjeta/inscribir/',             TarjetaInscribirView.as_view(),           name='empresa-tarjeta-inscribir'),
    path('api/empresa/tarjeta/retorno/',               TarjetaInscripcionRetornoView.as_view(),  name='empresa-tarjeta-retorno'),
    path('api/empresa/tarjeta/eliminar/',              TarjetaEliminarView.as_view(),            name='empresa-tarjeta-eliminar'),

    # Rutas y trabajos — rutas específicas ANTES de las rutas con :id
    path('api/empresa/rutas/calcular/',                          RouteCalcularView.as_view(),     name='rutas-calcular'),
    path('api/empresa/rutas/validar/',                           RutaValidarView.as_view(),        name='rutas-validar'),
    path('api/empresa/rutas/',                                   RutasListView.as_view(),         name='rutas-lista'),
    path('api/empresa/rutas/<int:ruta_id>/',                     RutaDetailView.as_view(),        name='rutas-detalle'),
    path('api/empresa/rutas/<int:ruta_id>/iniciar/',             RutaIniciarView.as_view(),       name='rutas-iniciar'),
    path('api/empresa/rutas/<int:ruta_id>/finalizar/',           RutaFinalizarView.as_view(),     name='rutas-finalizar'),
    path('api/empresa/rutas/<int:ruta_id>/cancelar/',            RutaCancelarView.as_view(),      name='rutas-cancelar'),
    path('api/empresa/rutas/<int:ruta_id>/comentarios/',         RutaComentariosView.as_view(),   name='rutas-comentarios'),
    # ── Moderación de contenido ─────────────────────────────────────────────────
    path('api/moderar/',                                moderar_texto,    name='moderar-texto'),
    path('api/admin/moderacion/palabras/',              palabras_list,    name='moderacion-palabras'),
    path('api/admin/moderacion/palabras/agregar/',      agregar_palabra,  name='moderacion-agregar'),
    path('api/admin/moderacion/palabras/lote/',         agregar_lote,     name='moderacion-lote'),
    path('api/admin/moderacion/palabras/eliminar/',     eliminar_palabra, name='moderacion-eliminar'),

    # ── Endpoints públicos (sin autenticación) ──────────────────────────────────
    path('api/planes/',          PlanesPublicosView.as_view(), name='planes-publicos'),
    path('api/auto-registro/',   AutoRegistroView.as_view(),   name='auto-registro'),
    path('api/verificar-rut/',   VerificarRutView.as_view(),   name='verificar-rut'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
