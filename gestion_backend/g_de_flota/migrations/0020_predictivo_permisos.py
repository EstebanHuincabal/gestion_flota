from django.db import migrations

NUEVOS_PERMISOS = [
    ('predictivo.ver',       'Ver alertas y planes predictivos',   'predictivo'),
    ('predictivo.gestionar', 'Gestionar planes y atender alertas', 'predictivo'),
]


def agregar_permisos_predictivo(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Usuario = apps.get_model('g_de_flota', 'Usuario')

    nuevos = []
    for codigo, nombre, categoria in NUEVOS_PERMISOS:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria}
        )
        nuevos.append(p)

    for usuario in Usuario.objects.filter(rol='USUARIO'):
        usuario.permisos.add(*nuevos)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0019_usuario_notif_prefs_notificacion'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos_predictivo, migrations.RunPython.noop),
    ]
