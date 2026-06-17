from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0036_logauditoria_so_metodo_endpoint'),
    ]

    operations = [
        # ── Vehiculo: agregar categoria_peaje ────────────────────────────────
        migrations.AddField(
            model_name='vehiculo',
            name='categoria_peaje',
            field=models.CharField(
                choices=[
                    ('moto',        'Moto / Motoneta'),
                    ('liviano',     'Auto / Camioneta / SUV'),
                    ('liviano_rem', 'Auto/Camioneta con remolque'),
                    ('pesado_2',    'Bus / Camión 2 ejes'),
                    ('pesado_3',    'Camión 3+ ejes'),
                ],
                default='liviano',
                help_text='Categoría de peaje del vehículo',
                max_length=20,
            ),
        ),

        # ── Peaje: quitar unique_together anterior ───────────────────────────
        migrations.AlterUniqueTogether(
            name='peaje',
            unique_together=set(),
        ),

        # ── Peaje: agregar campo categoria ───────────────────────────────────
        migrations.AddField(
            model_name='peaje',
            name='categoria',
            field=models.CharField(
                choices=[
                    ('moto',        'Moto / Motoneta'),
                    ('liviano',     'Auto / Camioneta / SUV'),
                    ('liviano_rem', 'Auto/Camioneta con remolque'),
                    ('pesado_2',    'Bus / Camión 2 ejes'),
                    ('pesado_3',    'Camión 3+ ejes'),
                ],
                default='liviano',
                max_length=20,
            ),
        ),

        # ── Peaje: agregar km_ruta ────────────────────────────────────────────
        migrations.AddField(
            model_name='peaje',
            name='km_ruta',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Kilómetro en la ruta donde está el peaje',
                max_digits=7,
                null=True,
            ),
        ),

        # ── Peaje: agregar radio_metros ───────────────────────────────────────
        migrations.AddField(
            model_name='peaje',
            name='radio_metros',
            field=models.PositiveIntegerField(
                default=800,
                help_text='Radio de detección personalizado en metros',
            ),
        ),

        # ── Peaje: nuevo unique_together con categoria ────────────────────────
        migrations.AlterUniqueTogether(
            name='peaje',
            unique_together={('nombre', 'ruta', 'categoria')},
        ),

        # ── Peaje: actualizar ordering ────────────────────────────────────────
        migrations.AlterModelOptions(
            name='peaje',
            options={
                'ordering': ['ruta', 'nombre', 'categoria'],
                'verbose_name': 'Peaje',
                'verbose_name_plural': 'Peajes',
            },
        ),
    ]
