"""
0047 — Agrega hora_programada (TimeField) a Ruta.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0046_reconstruir_rutas'),
    ]

    operations = [
        migrations.AddField(
            model_name='ruta',
            name='hora_programada',
            field=models.TimeField(
                null=True, blank=True,
                help_text='Hora de inicio programada',
            ),
        ),
    ]
