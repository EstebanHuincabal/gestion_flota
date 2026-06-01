from django.db import migrations


def eliminar_permisos(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo__in=['geolocalizacion.ver', 'rutas.gantt']).delete()


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0073_gantt_permiso'),
    ]

    operations = [
        migrations.RunPython(eliminar_permisos, revertir),
    ]
