from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Empresa, CambioPlan,
    Vehiculo, Asignacion,
    Mantencion,
    LogAuditoria, PlanSuscripcion, Permiso,
    Notificacion,
    PlanMantenimiento, ReglaMantenimiento, VehiculoPlan,
    MantencionProgramada, AlertaMantencion,
    GastoOperativo, PresupuestoMensual, Documento,
    Ruta, Parada, EventoRuta, Ubicacion,
    SolicitudConductor,
    DispositivoGPS,
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
    search_fields = ('email_hash', 'rut_hash')   # email cifrado → buscar por hash exacto
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
    list_display = ('nombre', 'max_vehiculos', 'max_conductores')
    search_fields = ('nombre',)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('codigo', 'nombre')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'tipo_combustible', 'empresa', 'activo')
    list_filter = ('tipo_combustible', 'activo', 'empresa')
    search_fields = ('patente',)   # marca y modelo van cifrados


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'conductor', 'activo', 'desde', 'hasta')
    list_filter = ('activo', 'vehiculo__empresa')
    search_fields = ('vehiculo__patente', 'conductor__email')


@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ('tipo_mantencion', 'vehiculo', 'fecha_programada', 'estado', 'costo')
    list_filter = ('estado', 'vehiculo__empresa')
    search_fields = ('vehiculo__patente',)   # tipo_mantencion va cifrado



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
    list_filter = ('estado', 'vehiculo__empresa')
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
    search_fields = ('vehiculo__patente',)   # descripcion va cifrada


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
    search_fields = ('usuario__email',)   # titulo y mensaje van cifrados
    readonly_fields = ('fecha',)


# ─────────────────────────────────────────
# Rutas y Trabajos
# ─────────────────────────────────────────

@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'empresa', 'tipo', 'estado', 'conductor', 'vehiculo', 'fecha_programada', 'distancia_km')
    list_filter   = ('tipo', 'estado', 'empresa')
    search_fields = ('conductor__email', 'vehiculo__patente')   # nombre va cifrado
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'ruta', 'tipo', 'orden', 'direccion')
    list_filter   = ('tipo',)
    # nombre, ruta__nombre y direccion van cifrados → sin búsqueda de texto


@admin.register(EventoRuta)
class EventoRutaAdmin(admin.ModelAdmin):
    list_display  = ('ruta', 'tipo', 'autor', 'texto', 'created_at')
    list_filter   = ('tipo',)
    search_fields = ('autor__email',)   # ruta__nombre y texto van cifrados
    readonly_fields = ('created_at',)


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display  = ('vehiculo', 'latitud', 'longitud', 'velocidad', 'timestamp')
    list_filter   = ('vehiculo__empresa', 'vehiculo')
    search_fields = ('vehiculo__patente',)
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


# ─────────────────────────────────────────
# Solicitudes de Conductores
# ─────────────────────────────────────────

@admin.register(SolicitudConductor)
class SolicitudConductorAdmin(admin.ModelAdmin):
    list_display   = ('id', 'conductor', 'tipo', 'titulo', 'estado', 'prioridad', 'created_at')
    list_filter    = ('tipo', 'estado', 'prioridad')
    search_fields  = ('conductor__email',)   # titulo y descripcion van cifrados
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


# ─────────────────────────────────────────
# Geolocalización GPS
# ─────────────────────────────────────────

@admin.register(DispositivoGPS)
class DispositivoGPSAdmin(admin.ModelAdmin):
    list_display   = ('imei', 'modelo', 'empresa', 'vehiculo', 'activo', 'creado_at')
    list_filter    = ('modelo', 'activo', 'empresa')
    search_fields  = ('imei',)
    readonly_fields = ('creado_at',)
    list_select_related = ('empresa', 'vehiculo')
