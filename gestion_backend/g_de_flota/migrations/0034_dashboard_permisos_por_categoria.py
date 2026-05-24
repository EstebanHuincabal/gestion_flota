from django.db import migrations

PERMISOS_DASHBOARD = [
    ('dashboard.flota',        'Flota',          'Dashboard'),
    ('dashboard.mantenimiento','Mantenimiento',   'Dashboard'),
    ('dashboard.finanzas',     'Finanzas',        'Dashboard'),
    ('dashboard.documentos',   'Documentos',      'Dashboard'),
    ('dashboard.rutas',        'Rutas',           'Dashboard'),
    ('dashboard.conductores',  'Conductores',     'Dashboard'),
]


def crear_permisos(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    # Eliminar el permiso genérico anterior
    Permiso.objects.filter(codigo='dashboard.ver').delete()

    nuevos = []
    for codigo, nombre, categoria in PERMISOS_DASHBOARD:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        nuevos.append(p)

    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(*nuevos)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0033_dashboard_permiso_unico'),
    ]

    operations = [
        migrations.RunPython(crear_permisos, migrations.RunPython.noop),
    ]
