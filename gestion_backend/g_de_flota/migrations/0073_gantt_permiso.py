from django.db import migrations


def agregar_permiso_gantt(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permiso, _ = Permiso.objects.get_or_create(
        codigo='rutas.gantt',
        defaults={
            'nombre':    'Ver Carta Gantt de rutas y mantenciones',
            'categoria': 'rutas',
        },
    )

    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(permiso)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo='rutas.gantt').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0072_geolocalizacion_permiso'),
    ]

    operations = [
        migrations.RunPython(agregar_permiso_gantt, revertir),
    ]
