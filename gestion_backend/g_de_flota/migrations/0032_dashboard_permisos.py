from django.db import migrations

PERMISOS_NUEVOS = [
    ('dashboard.flota',        'Indicadores de flota',         'Dashboard — Flota'),
    ('dashboard.mantenimiento','Indicadores de mantenimiento', 'Dashboard — Mantenimiento'),
    ('dashboard.finanzas',     'Indicadores de finanzas',      'Dashboard — Finanzas'),
    ('dashboard.documentos',   'Indicadores de documentos',    'Dashboard — Documentos'),
    ('dashboard.rutas',        'Indicadores de rutas',         'Dashboard — Rutas'),
    ('dashboard.conductores',  'Indicadores de conductores',   'Dashboard — Conductores'),
]


def agregar_permisos(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    nuevos = []
    for codigo, nombre, categoria in PERMISOS_NUEVOS:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        nuevos.append(p)

    # Asignar a todos los planes existentes (retrocompatibilidad)
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(*nuevos)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0031_cleanup_unused_tables'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos, migrations.RunPython.noop),
    ]
