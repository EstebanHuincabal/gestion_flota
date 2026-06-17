from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0040_solicitudes_permisos'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiculo',
            name='en_mantencion',
            field=models.BooleanField(
                default=False,
                verbose_name='En mantención',
                help_text='True mientras el vehículo está fuera de servicio por una mantención activa.',
            ),
        ),
    ]
