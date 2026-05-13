from django.db import migrations

CODIGOS_MANTENCIONES = [
    ('mantenciones.ver',      'Ver mantenciones',      'mantenciones'),
    ('mantenciones.crear',    'Crear mantenciones',    'mantenciones'),
    ('mantenciones.editar',   'Editar mantenciones',   'mantenciones'),
    ('mantenciones.eliminar', 'Eliminar mantenciones', 'mantenciones'),
]


def asignar_permisos_mantenciones(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Usuario = apps.get_model('g_de_flota', 'Usuario')

    permisos = []
    for codigo, nombre, categoria in CODIGOS_MANTENCIONES:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria}
        )
        permisos.append(p)

    for usuario in Usuario.objects.filter(rol='USUARIO'):
        usuario.permisos.add(*permisos)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0016_mantencion_campos_extendidos'),
    ]

    operations = [
        migrations.RunPython(asignar_permisos_mantenciones, migrations.RunPython.noop),
    ]
