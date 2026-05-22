from django.db import migrations

PERMISOS_RUTAS = [
    ('rutas.ver',      'Ver rutas y trabajos',            'rutas'),
    ('rutas.crear',    'Crear y editar rutas',            'rutas'),
    ('rutas.eliminar', 'Eliminar rutas',                  'rutas'),
    ('rutas.exportar', 'Exportar rutas a XLSX',           'rutas'),
]

PERMISOS_POR_PLAN = {
    'basico':     ['rutas.ver', 'rutas.crear'],
    'pro':        ['rutas.ver', 'rutas.crear', 'rutas.eliminar', 'rutas.exportar'],
    'enterprise': ['rutas.ver', 'rutas.crear', 'rutas.eliminar', 'rutas.exportar'],
}


def agregar_permisos_rutas(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permisos_obj = {}
    for codigo, nombre, categoria in PERMISOS_RUTAS:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        permisos_obj[codigo] = p

    for nombre_plan, codigos in PERMISOS_POR_PLAN.items():
        try:
            plan = PlanSuscripcion.objects.get(nombre=nombre_plan)
        except PlanSuscripcion.DoesNotExist:
            continue

        for codigo in codigos:
            plan.permisos.add(permisos_obj[codigo])

        modulos = plan.modulos or []
        if 'trabajos_y_rutas' not in modulos:
            plan.modulos = modulos + ['trabajos_y_rutas']
            plan.save(update_fields=['modulos'])


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(categoria='rutas').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0028_vehiculo_consumo_l_100km_configuracionruta_peaje_and_more'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos_rutas, revertir),
    ]
