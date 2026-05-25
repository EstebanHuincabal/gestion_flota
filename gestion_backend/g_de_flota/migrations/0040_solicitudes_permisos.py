from django.db import migrations

PERMISOS_SOLICITUDES = [
    ('solicitudes.ver', 'Ver y gestionar solicitudes de conductores', 'solicitudes'),
]

# El permiso aplica a todos los planes — cualquier empresa puede gestionar solicitudes
PERMISOS_POR_PLAN = {
    'basico':     ['solicitudes.ver'],
    'pro':        ['solicitudes.ver'],
    'enterprise': ['solicitudes.ver'],
}


def agregar_permisos_solicitudes(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permisos_obj = {}
    for codigo, nombre, categoria in PERMISOS_SOLICITUDES:
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


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(categoria='solicitudes').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0039_solicitud_conductor_campos_extras'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos_solicitudes, revertir),
    ]
