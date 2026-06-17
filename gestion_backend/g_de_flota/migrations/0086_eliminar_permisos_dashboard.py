"""
Elimina los permisos `dashboard.*` que quedaron en desuso.

Los gráficos del dashboard ahora se ligan al permiso del MÓDULO correspondiente
(flotas.ver, mantenciones.ver, finanzas.ver, documentos.ver, rutas.ver,
conductores.ver). Los permisos `dashboard.flota/mantenimiento/...` ya no tienen
efecto, así que se eliminan para no confundir en la pantalla de gestión de permisos.
Al borrarlos de la tabla Permiso se quitan también de plan.permisos (M2M).
"""
from django.db import migrations

CODIGOS = [
    'dashboard.flota',
    'dashboard.mantenimiento',
    'dashboard.finanzas',
    'dashboard.documentos',
    'dashboard.rutas',
    'dashboard.conductores',
]


def eliminar(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo__in=CODIGOS).delete()


def recrear(apps, schema_editor):
    # Reverso best-effort: recrea los permisos (sin reasignarlos a planes).
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    etiquetas = {
        'dashboard.flota':         'Flota',
        'dashboard.mantenimiento': 'Mantenimiento',
        'dashboard.finanzas':      'Finanzas',
        'dashboard.documentos':    'Documentos',
        'dashboard.rutas':         'Rutas',
        'dashboard.conductores':   'Conductores',
    }
    for codigo, nombre in etiquetas.items():
        Permiso.objects.get_or_create(
            codigo=codigo, defaults={'nombre': nombre, 'categoria': 'Dashboard'},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0085_suscripcion_fecha_cambio_programado_and_more'),
    ]

    operations = [
        migrations.RunPython(eliminar, recrear),
    ]
