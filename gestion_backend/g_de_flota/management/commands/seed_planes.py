from django.core.management.base import BaseCommand
from g_de_flota.models import PlanSuscripcion


PLANES_DATA = [
    {
        'nombre':          'basico',
        'descripcion':     'Ideal para pequeñas empresas que inician la gestión de su flota.',
        'precio_mensual':  49000,
        'max_flotas':      2,
        'max_vehiculos':   10,
        'max_conductores': 15,
        'max_usuarios':    3,
        'modulos': [
            'flotas', 'vehiculos', 'conductores',
            'mantencion_correctiva', 'documentos', 'notificaciones_avanzadas',
            'dashboard', 'finanzas', 'trabajos_y_rutas',
        ],
        'activo': True,
        'orden':  1,
    },
    {
        'nombre':          'pro',
        'descripcion':     'Para empresas en crecimiento que necesitan gestión avanzada de su flota.',
        'precio_mensual':  149000,
        'max_flotas':      10,
        'max_vehiculos':   60,
        'max_conductores': 80,
        'max_usuarios':    9999,
        'modulos': [
            'flotas', 'vehiculos', 'conductores',
            'mantencion_correctiva', 'mantencion_predictiva',
            'documentos', 'notificaciones_avanzadas',
            'gps', 'geofencing', 'reportes', 'exportacion',
            'dashboard', 'finanzas', 'trabajos_y_rutas',
        ],
        'activo': True,
        'orden':  2,
    },
    {
        'nombre':          'enterprise',
        'descripcion':     'Solución completa para grandes flotas con soporte dedicado y acceso total.',
        'precio_mensual':  None,
        'max_flotas':      9999,
        'max_vehiculos':   9999,
        'max_conductores': 9999,
        'max_usuarios':    9999,
        'modulos': [
            'flotas', 'vehiculos', 'conductores',
            'mantencion_correctiva', 'mantencion_predictiva',
            'documentos', 'notificaciones_avanzadas',
            'gps', 'geofencing', 'reportes', 'exportacion', 'api_access',
            'dashboard', 'finanzas', 'trabajos_y_rutas',
        ],
        'activo': True,
        'orden':  3,
    },
]


class Command(BaseCommand):
    help = 'Crea o actualiza los planes de suscripción con sus módulos y precios.'

    def handle(self, *args, **options):
        for data in PLANES_DATA:
            nombre = data.pop('nombre')
            plan, created = PlanSuscripcion.objects.update_or_create(
                nombre=nombre,
                defaults=data,
            )
            accion = 'Creado' if created else 'Actualizado'
            self.stdout.write(self.style.SUCCESS(
                f'{accion}: Plan {plan.get_nombre_display()} — '
                f'${plan.precio_mensual:,.0f}/mes'.replace(',', '.') if plan.precio_mensual
                else f'{accion}: Plan {plan.get_nombre_display()} — A convenir'
            ))
        self.stdout.write(self.style.SUCCESS('Planes de suscripción listos.'))
