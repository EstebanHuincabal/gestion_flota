"""
0093 — Agrega la opción 'todas' al campo destino de Aviso (envío a todas las empresas).
Solo actualiza el estado del modelo; no altera la tabla (Django no impone choices a nivel BD).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0092_aviso_and_permisos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aviso',
            name='destino',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('flota',     'Toda la flota'),
                    ('conductor', 'Conductor específico'),
                    ('admins',    'Administradores'),
                    ('todas',     'Todas las empresas'),
                ],
            ),
        ),
    ]
