from django.db import migrations


def agregar_permiso_geo(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permiso, _ = Permiso.objects.get_or_create(
        codigo='geolocalizacion.ver',
        defaults={
            'nombre':    'Ver mapa de geolocalización en tiempo real',
            'categoria': 'geolocalizacion',
        },
    )

    # Asignar a todos los planes activos existentes
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(permiso)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo='geolocalizacion.ver').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0071_cifrar_emails'),
    ]

    operations = [
        migrations.RunPython(agregar_permiso_geo, revertir),
    ]
