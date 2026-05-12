from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Empresa,
    Flota, Vehiculo, Asignacion,
    Ubicacion, Evento, Mantencion, DocumentoVehiculo, DocumentoConductor,
    LogAuditoria, PlanSuscripcion, Permiso
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


@admin.register(DocumentoVehiculo)
class DocumentoVehiculoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'vehiculo', 'fecha_vencimiento', 'estado')
    list_filter = ('estado', 'tipo')
    search_fields = ('vehiculo__patente',)


@admin.register(DocumentoConductor)
class DocumentoConductorAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'conductor', 'numero', 'fecha_vencimiento', 'estado')
    list_filter = ('estado', 'tipo')
    search_fields = ('conductor__email', 'numero')


@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ('tipo_mantencion', 'vehiculo', 'fecha_programada', 'estado', 'costo')
    list_filter = ('estado', 'vehiculo__flota__empresa')
    search_fields = ('vehiculo__patente', 'tipo_mantencion')


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'latitud', 'longitud', 'velocidad', 'timestamp')
    list_filter = ('vehiculo__flota__empresa',)
    search_fields = ('vehiculo__patente',)


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'vehiculo', 'fecha')
    list_filter = ('tipo', 'vehiculo__flota__empresa')
    search_fields = ('vehiculo__patente', 'descripcion')


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'accion', 'usuario', 'ip', 'fecha')
    list_filter = ('tipo', 'accion', 'fecha')
    search_fields = ('usuario__email', 'ip')
    readonly_fields = ('tipo', 'accion', 'usuario', 'detalle', 'ip', 'fecha')
