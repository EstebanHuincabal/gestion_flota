"""
0042 — Permisos granulares por tipo de solicitud de conductor.

Crea cuatro permisos (uno por tipo de solicitud) y los asigna
a todos los planes existentes.  El superadmin puede luego
quitar permisos de planes específicos desde el panel.
"""
from django.db import migrations

PERMISOS_TIPO = [
    ('solicitudes.mantencion',  'Solicitar mantención del vehículo', 'solicitudes'),
    ('solicitudes.combustible', 'Solicitar combustible',              'solicitudes'),
    ('solicitudes.incidencia',  'Reportar incidencia o accidente',    'solicitudes'),
    ('solicitudes.documento',   'Subir o renovar documentos',         'solicitudes'),
]

# Por defecto todos los tipos están disponibles en todos los planes.
# El administrador del sistema puede revocarlos desde el panel de planes.
PERMISOS_POR_PLAN = {
    'basico':     [p[0] for p in PERMISOS_TIPO],
    'pro':        [p[0] for p in PERMISOS_TIPO],
    'enterprise': [p[0] for p in PERMISOS_TIPO],
}


def agregar_permisos(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')

    # Crear / obtener los permisos
    permisos_obj = {}
    for codigo, nombre, categoria in PERMISOS_TIPO:
        p, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        permisos_obj[codigo] = p

    # Asignar a cada plan
    for nombre_plan, codigos in PERMISOS_POR_PLAN.items():
        try:
            plan = PlanSuscripcion.objects.get(nombre=nombre_plan)
        except PlanSuscripcion.DoesNotExist:
            continue
        for codigo in codigos:
            plan.permisos.add(permisos_obj[codigo])


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    codigos = [p[0] for p in PERMISOS_TIPO]
    Permiso.objects.filter(codigo__in=codigos).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0041_vehiculo_en_mantencion'),
    ]

    operations = [
        migrations.RunPython(agregar_permisos, revertir),
    ]
