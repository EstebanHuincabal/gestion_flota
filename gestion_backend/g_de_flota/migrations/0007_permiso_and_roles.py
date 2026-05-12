from django.db import migrations, models

PERMISOS_DATA = [
    ('dashboard.empresa',    'Ver dashboard de empresa',       'dashboard'),
    ('conductores.ver',      'Ver conductores',                'conductores'),
    ('conductores.crear',    'Crear conductores',              'conductores'),
    ('conductores.editar',   'Editar conductores',             'conductores'),
    ('conductores.eliminar', 'Eliminar conductores',           'conductores'),
    ('conductores.asignar',  'Asignar vehículo a conductor',   'conductores'),
    ('flotas.ver',           'Ver flotas',                     'flotas'),
    ('flotas.crear',         'Crear flotas',                   'flotas'),
    ('flotas.editar',        'Editar flotas',                  'flotas'),
    ('flotas.eliminar',      'Eliminar flotas',                'flotas'),
    ('vehiculos.ver',        'Ver vehículos',                  'vehiculos'),
    ('vehiculos.crear',      'Crear vehículos',                'vehiculos'),
    ('vehiculos.editar',     'Editar vehículos',               'vehiculos'),
    ('vehiculos.eliminar',   'Eliminar vehículos',             'vehiculos'),
    ('usuarios.ver',         'Ver usuarios de la empresa',     'usuarios'),
    ('usuarios.crear',       'Crear usuarios',                 'usuarios'),
    ('usuarios.editar',      'Editar usuarios',                'usuarios'),
    ('usuarios.eliminar',    'Desactivar usuarios',            'usuarios'),
    ('mantenciones.ver',     'Ver mantenciones',               'mantenciones'),
    ('mantenciones.crear',   'Crear mantenciones',             'mantenciones'),
    ('mantenciones.editar',  'Editar mantenciones',            'mantenciones'),
    ('mantenciones.eliminar','Eliminar mantenciones',          'mantenciones'),
    ('documentos.ver',       'Ver documentos',                 'documentos'),
    ('documentos.crear',     'Crear documentos',               'documentos'),
    ('documentos.editar',    'Editar documentos',              'documentos'),
    ('documentos.eliminar',  'Eliminar documentos',            'documentos'),
]


def poblar_permisos_y_migrar_roles(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Usuario = apps.get_model('g_de_flota', 'Usuario')

    permisos_creados = []
    for codigo, nombre, categoria in PERMISOS_DATA:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo, defaults={'nombre': nombre, 'categoria': categoria}
        )
        permisos_creados.append(p)

    for user in Usuario.objects.filter(rol='ADMIN'):
        user.rol = 'USUARIO'
        user.save(update_fields=['rol'])
        user.permisos.set(permisos_creados)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0006_logauditoria'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permiso',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo',    models.CharField(max_length=100, unique=True)),
                ('nombre',    models.CharField(max_length=200)),
                ('categoria', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'Permiso',
                'verbose_name_plural': 'Permisos',
                'ordering': ['categoria', 'codigo'],
            },
        ),
        migrations.AddField(
            model_name='usuario',
            name='permisos',
            field=models.ManyToManyField(blank=True, related_name='usuarios', to='g_de_flota.Permiso'),
        ),
        migrations.RunPython(poblar_permisos_y_migrar_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('SUPERADMIN', 'Super Administrador'),
                    ('USUARIO',    'Usuario'),
                    ('CONDUCTOR',  'Conductor'),
                ],
                default='USUARIO',
                max_length=20,
            ),
        ),
    ]
