"""
Migración de datos: corrige suscripciones activas que nunca tuvieron un pago aprobado.
Esas empresas quedaron con acceso sin pagar, generalmente asignadas
desde el formulario de edición de empresa (que no creaba la suscripción).
Las pasa a 'pendiente' para que deban pagar antes de acceder.
"""
from django.db import migrations


def corregir_activas_sin_pago(apps, schema_editor):
    Suscripcion    = apps.get_model('g_de_flota', 'Suscripcion')
    PagoTransbank  = apps.get_model('g_de_flota', 'PagoTransbank')

    # IDs de suscripciones activas que tienen al menos un pago aprobado
    ids_con_pago = PagoTransbank.objects.filter(
        estado='aprobado',
        suscripcion__isnull=False,
    ).values_list('suscripcion_id', flat=True).distinct()

    actualizadas = Suscripcion.objects.filter(
        estado='activa',
    ).exclude(id__in=ids_con_pago).update(estado='pendiente')

    if actualizadas:
        print(f'\n  ✔ {actualizadas} suscripción(es) activa(s) sin pago → pendiente.')


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0052_suscripcion_pendiente_replace_trial'),
    ]

    operations = [
        migrations.RunPython(corregir_activas_sin_pago, migrations.RunPython.noop),
    ]
