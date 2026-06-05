"""
Crea el permiso `dashboard.ver` para poder ofrecer planes con o sin dashboard.

Se asigna a TODOS los planes existentes para no cambiar el comportamiento actual
(todos siguen viendo el dashboard). Para vender un plan sin dashboard, basta con
no incluir este permiso en ese plan.
"""
from django.db import migrations

PERMISO = ('dashboard.ver', 'Ver el panel / dashboard', 'dashboard')


def crear(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    codigo, nombre, categoria = PERMISO
    permiso, _ = Permiso.objects.get_or_create(
        codigo=codigo, defaults={'nombre': nombre, 'categoria': categoria},
    )
    # Asignar a todos los planes existentes (mantiene el comportamiento actual).
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(permiso)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo=PERMISO[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0087_pagotransbank_iniciado_por'),
    ]

    operations = [
        migrations.RunPython(crear, revertir),
    ]
