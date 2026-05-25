from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Empresa, CambioPlan,
    Flota, Vehiculo, Asignacion,
    Mantencion,
    LogAuditoria, PlanSuscripcion, Permiso,
    Notificacion,
    PlanMantenimiento, ReglaMantenimiento, VehiculoPlan,
    MantencionProgramada, AlertaMantencion,
    GastoOperativo, PresupuestoMensual, Documento,
    Peaje, ConfiguracionRuta,
    Ruta, Parada, PeajeRuta,
    SolicitudConductor,
)

# ─────────────────────────────────────────
# Configuración del Panel de Administración
# ─────────────────────────────────────────
admin.site.site_header = "Administración de Gestión de Flota"
admin.site.site_title  = "Portal de Administración"
admin.site.index_title = "Panel de Control Principal"


@admin.register(Usuario)
class CustomUsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'rut', 'nombre', 'rol', 'empresa', 'is_active', 'is_blocked')
    list_filter = ('rol', 'is_active', 'is_blocked', 'empresa')
    search_fields = ('email', 'nombre_cifrado', 'rut_hash')
    ordering = ('email',)

    fieldsets = (
        ("Credenciales", {'fields': ('email', 'password')}),
        ("Información Personal", {'fields': ('rut_cifrado', 'nombre_cifrado', 'telefono_cifrado', 'licencia_cifrada')}),
        ("Empresa y Rol", {'fields': ('empresa', 'rol', 'permisos')}),
        ("Seguridad", {'fields': ('is_active', 'is_blocked', 'intentos_fallidos')}),
        ("Fechas", {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'estado', 'plan', 'created_at')
    list_filter = ('estado', 'region', 'plan')
    search_fields = ('nombre', 'rut_hash')


@admin.register(PlanSuscripcion)
class PlanSuscripcionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'max_flotas', 'max_vehiculos', 'max_conductores')
    search_fields = ('nombre',)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('codigo', 'nombre')


@admin.register(Flota)
class FlotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa')
    list_filter = ('empresa',)
    search_fields = ('nombre', 'empresa__nombre')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'tipo_combustible', 'flota', 'activo')
    list_filter = ('tipo_combustible', 'activo', 'flota__empresa')
    search_fields = ('patente', 'marca', 'modelo')


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'conductor', 'activo', 'desde', 'hasta')
    list_filter = ('activo', 'vehiculo__flota__empresa')
    search_fields = ('vehiculo__patente', 'conductor__email')


@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ('tipo_mantencion', 'vehiculo', 'fecha_programada', 'estado', 'costo')
    list_filter = ('estado', 'vehiculo__flota__empresa')
    search_fields = ('vehiculo__patente', 'tipo_mantencion')



@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'accion', 'usuario', 'ip', 'fecha')
    list_filter = ('tipo', 'accion', 'fecha')
    search_fields = ('usuario__email', 'ip')
    readonly_fields = ('tipo', 'accion', 'usuario', 'detalle', 'ip', 'fecha')


# ─────────────────────────────────────────
# Mantenimiento Predictivo
# ─────────────────────────────────────────

@admin.register(PlanMantenimiento)
class PlanMantenimientoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'activo', 'created_at')
    list_filter = ('activo', 'empresa')
    search_fields = ('nombre', 'empresa__nombre')


@admin.register(ReglaMantenimiento)
class ReglaMantenimientoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'plan', 'prioridad', 'intervalo_dias', 'umbral_alerta_dias', 'costo_estimado')
    list_filter = ('prioridad', 'canal', 'plan__empresa')
    search_fields = ('tipo', 'plan__nombre')


@admin.register(VehiculoPlan)
class VehiculoPlanAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'plan', 'fecha_asignacion')
    list_filter = ('plan__empresa',)
    search_fields = ('vehiculo__patente', 'plan__nombre')


@admin.register(MantencionProgramada)
class MantencionProgramadaAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'regla', 'fecha_ultima', 'fecha_siguiente', 'estado')
    list_filter = ('estado', 'vehiculo__flota__empresa')
    search_fields = ('vehiculo__patente', 'regla__tipo')


@admin.register(AlertaMantencion)
class AlertaMantencionAdmin(admin.ModelAdmin):
    list_display = ('mantencion_programada', 'nivel', 'dias_restantes', 'enviada', 'atendida', 'fecha_creacion')
    list_filter = ('nivel', 'enviada', 'atendida')
    search_fields = ('mantencion_programada__vehiculo__patente',)


# ─────────────────────────────────────────
# Finanzas
# ─────────────────────────────────────────

@admin.register(GastoOperativo)
class GastoOperativoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'vehiculo', 'categoria', 'monto', 'fecha')
    list_filter = ('categoria', 'empresa')
    search_fields = ('vehiculo__patente', 'descripcion')


@admin.register(PresupuestoMensual)
class PresupuestoMensualAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'anio', 'mes', 'monto')
    list_filter = ('empresa', 'anio')


# ─────────────────────────────────────────
# Documentos
# ─────────────────────────────────────────

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'entidad', 'tipo', 'vehiculo', 'conductor', 'fecha_vencimiento')
    list_filter = ('entidad', 'tipo', 'empresa')
    search_fields = ('vehiculo__patente', 'conductor__email')


# ─────────────────────────────────────────
# Suscripciones
# ─────────────────────────────────────────

@admin.register(CambioPlan)
class CambioPlanAdmin(admin.ModelAdmin):
    list_display  = ('empresa', 'plan_antes', 'plan_despues', 'cambiado_por', 'fecha')
    list_filter   = ('plan_antes', 'plan_despues')
    search_fields = ('empresa__nombre', 'cambiado_por__email', 'motivo')
    readonly_fields = ('fecha',)


# ─────────────────────────────────────────
# Notificaciones
# ─────────────────────────────────────────

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'tipo', 'titulo', 'leida', 'fecha')
    list_filter   = ('tipo', 'leida')
    search_fields = ('usuario__email', 'titulo', 'mensaje')
    readonly_fields = ('fecha',)


# ─────────────────────────────────────────
# Rutas y Trabajos
# ─────────────────────────────────────────

@admin.register(Peaje)
class PeajeAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'ruta', 'categoria', 'tarifa_normal', 'tarifa_punta', 'radio_metros', 'activo')
    list_filter   = ('categoria', 'activo', 'ruta')
    search_fields = ('nombre', 'ruta', 'autopista')


@admin.register(ConfiguracionRuta)
class ConfiguracionRutaAdmin(admin.ModelAdmin):
    list_display  = ('empresa', 'precio_bencina', 'precio_diesel', 'radio_deteccion_peaje')
    search_fields = ('empresa__nombre',)


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'empresa', 'tipo', 'estado', 'conductor', 'vehiculo', 'fecha_programada', 'distancia_km', 'costo_total_est')
    list_filter   = ('tipo', 'estado', 'empresa')
    search_fields = ('nombre', 'conductor__email', 'vehiculo__patente')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'ruta', 'tipo', 'orden', 'direccion')
    list_filter   = ('tipo',)
    search_fields = ('nombre', 'ruta__nombre', 'direccion')


@admin.register(PeajeRuta)
class PeajeRutaAdmin(admin.ModelAdmin):
    list_display  = ('ruta', 'peaje', 'tarifa')
    list_filter   = ('peaje__categoria',)
    search_fields = ('ruta__nombre', 'peaje__nombre')


# ─────────────────────────────────────────
# Solicitudes de Conductores
# ─────────────────────────────────────────

@admin.register(SolicitudConductor)
class SolicitudConductorAdmin(admin.ModelAdmin):
    list_display   = ('id', 'conductor', 'tipo', 'titulo', 'estado', 'prioridad', 'created_at')
    list_filter    = ('tipo', 'estado', 'prioridad')
    search_fields  = ('titulo', 'descripcion', 'conductor__email')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('conductor',)
    fieldsets = (
        ('Solicitud', {
            'fields': ('conductor', 'tipo', 'titulo', 'descripcion', 'prioridad', 'foto'),
        }),
        ('Gestión', {
            'fields': ('estado', 'respuesta'),
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
