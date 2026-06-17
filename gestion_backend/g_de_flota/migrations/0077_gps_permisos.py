"""
0077 — Crea los permisos gps.ver y gps.gestionar y los asigna a todos los planes.

Como el módulo 'gps' del frontend se deriva de los prefijos de los permisos del
plan (cualquier permiso `gps.*` habilita la sección GPS), asignar estos permisos
hace visible el módulo automáticamente.
"""
from django.db import migrations


PERMISOS = [
    ('gps.ver',       'Ver mapa de flota y dispositivos GPS', 'gps'),
    ('gps.gestionar', 'Registrar, asignar y configurar GPS',  'gps'),
]


def crear_permisos_gps(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    creados = []
    for codigo, nombre, categoria in PERMISOS:
        permiso, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        creados.append(permiso)

    # Asignar ambos permisos a todos los planes existentes
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(*creados)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo__in=[c for c, _, _ in PERMISOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0076_configuraciongps_dispositivogps'),
    ]

    operations = [
        migrations.RunPython(crear_permisos_gps, revertir),
    ]
