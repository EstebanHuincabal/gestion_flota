"""
0048 — Agrega permiso calendario.ver y lo asigna a todos los planes activos.
"""
from django.db import migrations


def crear_permiso_calendario(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permiso, _ = Permiso.objects.get_or_create(
        codigo='calendario.ver',
        defaults={
            'nombre':    'Ver calendario global',
            'categoria': 'calendario',
        },
    )

    # Asignar a todos los planes existentes
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(permiso)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo='calendario.ver').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0047_ruta_hora_programada'),
    ]

    operations = [
        migrations.RunPython(crear_permiso_calendario, revertir),
    ]
