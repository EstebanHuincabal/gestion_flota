from django.db import migrations

PERMISOS_FINANZAS = [
    ('finanzas.ver',         'Ver gastos e informes financieros', 'finanzas'),
    ('finanzas.crear',       'Registrar nuevos gastos',           'finanzas'),
    ('finanzas.editar',      'Editar gastos existentes',          'finanzas'),
    ('finanzas.eliminar',    'Eliminar gastos',                   'finanzas'),
    ('finanzas.exportar',    'Exportar datos a CSV',              'finanzas'),
    ('finanzas.presupuesto', 'Gestionar presupuesto mensual',     'finanzas'),
]

# Permisos que incluye cada plan
PERMISOS_POR_PLAN = {
    'basico':     ['finanzas.ver', 'finanzas.crear'],
    'pro':        ['finanzas.ver', 'finanzas.crear', 'finanzas.editar', 'finanzas.eliminar', 'finanzas.exportar', 'finanzas.presupuesto'],
    'enterprise': ['finanzas.ver', 'finanzas.crear', 'finanzas.editar', 'finanzas.eliminar', 'finanzas.exportar', 'finanzas.presupuesto'],
}


def agregar_permisos_finanzas(apps, schema_editor):
    Permiso          = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion  = apps.get_model('g_de_flota', 'PlanSuscripcion')

    # Crear todos los permisos de finanzas
    permisos_obj = {}
    for codigo, nombre, categoria in PERMISOS_FINANZAS:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        permisos_obj[codigo] = p

    # Asignar permisos a cada plan y agregar módulo 'finanzas'
    for nombre_plan, codigos in PERMISOS_POR_PLAN.items():
        try:
            plan = PlanSuscripcion.objects.get(nombre=nombre_plan)
        except PlanSuscripcion.DoesNotExist:
            continue

        # Agregar permisos al plan
        for codigo in codigos:
            plan.permisos.add(permisos_obj[codigo])

        # Agregar módulo 'finanzas' si no está ya
        modulos = plan.modulos or []
        if 'finanzas' not in modulos:
            plan.modulos = modulos + ['finanzas']
            plan.save(update_fields=['modulos'])


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(categoria='finanzas').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0024_gastooperativo_presupuestomensual'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos_finanzas, revertir),
    ]
