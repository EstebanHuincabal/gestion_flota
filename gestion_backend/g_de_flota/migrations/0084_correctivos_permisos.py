from django.db import migrations

# Permisos dedicados del módulo de gastos correctivos (CRUD propio).
PERMISOS_CORRECTIVOS = [
    ('correctivos.ver',      'Ver gastos correctivos',       'correctivos'),
    ('correctivos.crear',    'Registrar gastos correctivos', 'correctivos'),
    ('correctivos.editar',   'Editar gastos correctivos',    'correctivos'),
    ('correctivos.eliminar', 'Eliminar gastos correctivos',  'correctivos'),
]


def agregar_permisos_correctivos(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    permisos = {}
    for codigo, nombre, categoria in PERMISOS_CORRECTIVOS:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo, defaults={'nombre': nombre, 'categoria': categoria}
        )
        permisos[codigo] = p

    # A cada plan que YA tenga finanzas se le otorgan los correctivos equivalentes,
    # para no quitar acceso a quien hoy ve el tab. Si tiene 'finanzas.ver' → ve
    # correctivos; si tiene crear/editar/eliminar de finanzas → el correctivo análogo.
    MAPEO = {
        'finanzas.ver':      'correctivos.ver',
        'finanzas.crear':    'correctivos.crear',
        'finanzas.editar':   'correctivos.editar',
        'finanzas.eliminar': 'correctivos.eliminar',
    }
    for plan in PlanSuscripcion.objects.all():
        codigos_plan = set(plan.permisos.values_list('codigo', flat=True))
        otorgar = [permisos[dst] for src, dst in MAPEO.items() if src in codigos_plan]
        if otorgar:
            plan.permisos.add(*otorgar)
            modulos = plan.modulos or []
            if 'correctivos' not in modulos:
                plan.modulos = modulos + ['correctivos']
                plan.save(update_fields=['modulos'])


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(categoria='correctivos').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0083_gastooperativo_categoria_correctiva_and_more'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos_correctivos, revertir),
    ]
