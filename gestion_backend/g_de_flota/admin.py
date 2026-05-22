from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Empresa,
    Flota, Vehiculo, Asignacion,
    Mantencion,
    LogAuditoria, PlanSuscripcion, Permiso,
    PlanMantenimiento, ReglaMantenimiento, VehiculoPlan,
    MantencionProgramada, AlertaMantencion,
    GastoOperativo, PresupuestoMensual, Documento,
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
