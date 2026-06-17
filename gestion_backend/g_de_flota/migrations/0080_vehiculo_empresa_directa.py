import django.db.models.deletion
from django.db import migrations, models


def poblar_empresa(apps, schema_editor):
    """Copia la empresa de la flota de cada vehículo al nuevo campo directo."""
    Vehiculo = apps.get_model('g_de_flota', 'Vehiculo')
    for v in Vehiculo.objects.select_related('flota').all():
        Vehiculo.objects.filter(pk=v.pk).update(empresa_id=v.flota.empresa_id)


def revertir_empresa(apps, schema_editor):
    """Reversa: reconstruye una flota por empresa y reasigna los vehículos.

    No se puede recuperar el nombre original de la flota; se usa 'General'.
    """
    Vehiculo = apps.get_model('g_de_flota', 'Vehiculo')
    Flota    = apps.get_model('g_de_flota', 'Flota')
    for v in Vehiculo.objects.all():
        flota, _ = Flota.objects.get_or_create(empresa_id=v.empresa_id, defaults={'nombre': 'General'})
        Vehiculo.objects.filter(pk=v.pk).update(flota_id=flota.id)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0079_delete_configuraciongps'),
    ]

    operations = [
        # 1. Nuevo FK directo a Empresa (temporalmente nullable para poder poblarlo).
        migrations.AddField(
            model_name='vehiculo',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='vehiculos',
                to='g_de_flota.empresa',
            ),
        ),
        # 2. Poblar empresa desde la flota actual.
        migrations.RunPython(poblar_empresa, revertir_empresa),
        # 3. Ahora empresa es obligatorio.
        migrations.AlterField(
            model_name='vehiculo',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='vehiculos',
                to='g_de_flota.empresa',
            ),
        ),
        # 4. Quitar el FK a Flota y borrar el modelo Flota.
        migrations.RemoveField(
            model_name='vehiculo',
            name='flota',
        ),
        migrations.DeleteModel(
            name='Flota',
        ),
    ]
