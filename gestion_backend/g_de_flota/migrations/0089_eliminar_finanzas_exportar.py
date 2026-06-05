"""
Elimina el permiso `finanzas.exportar`: la exportación de gastos se quitó del
módulo de finanzas (vista y endpoint eliminados). Al borrar el Permiso se quita
también de plan.permisos (M2M).
"""
from django.db import migrations

CODIGO = 'finanzas.exportar'


def eliminar(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo=CODIGO).delete()


def recrear(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.get_or_create(
        codigo=CODIGO,
        defaults={'nombre': 'Exportar datos a CSV', 'categoria': 'finanzas'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0088_permiso_dashboard_ver'),
    ]

    operations = [
        migrations.RunPython(eliminar, recrear),
    ]
