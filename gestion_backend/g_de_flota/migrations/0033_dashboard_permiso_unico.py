from django.db import migrations

CODIGOS_VIEJOS = [
    'dashboard.flota',
    'dashboard.mantenimiento',
    'dashboard.finanzas',
    'dashboard.documentos',
    'dashboard.rutas',
    'dashboard.conductores',
]


def consolidar_permiso(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    # Crear / obtener el permiso único
    nuevo, _ = Permiso.objects.get_or_create(
        codigo='dashboard.ver',
        defaults={'nombre': 'Acceso al dashboard', 'categoria': 'Dashboard'},
    )

    # Asignar a todos los planes
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(nuevo)

    # Eliminar los 6 permisos anteriores
    Permiso.objects.filter(codigo__in=CODIGOS_VIEJOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0032_dashboard_permisos'),
    ]

    operations = [
        migrations.RunPython(consolidar_permiso, migrations.RunPython.noop),
    ]
