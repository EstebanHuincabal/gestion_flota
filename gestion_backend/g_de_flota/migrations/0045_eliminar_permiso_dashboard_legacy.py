"""
0045 — Elimina el permiso dashboard.empresa (categoría lowercase 'dashboard')
que es un residuo de la migración 0007 y fue reemplazado por los 6 permisos
granulares creados en 0034 (categoría 'Dashboard' con D mayúscula).

No se usa en ningún lugar del código: no hay views, guards ni UI que lo
referencie. Se elimina para evitar el doble grupo en GestionPermisos.
"""
from django.db import migrations


def eliminar_permiso_legacy(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    # Solo borra el permiso con código exacto; no toca los demás.
    Permiso.objects.filter(codigo='dashboard.empresa').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0044_add_extra_to_ruta_and_solicitudconductor'),
    ]

    operations = [
        migrations.RunPython(eliminar_permiso_legacy, migrations.RunPython.noop),
    ]
