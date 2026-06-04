from django.db import migrations, models


# Mapeo de los modelos antiguos (marca + modelo específico) a la nueva lista
# simplificada que solo distingue por marca.
MAPEO_MODELOS = {
    'teltonika_fmb920': 'teltonika',
    'teltonika_fmc125': 'teltonika',
    'queclink_gl300':   'queclink',
    'coban_tk103':      'coban',
}


def simplificar_modelos(apps, schema_editor):
    DispositivoGPS = apps.get_model('g_de_flota', 'DispositivoGPS')
    for antiguo, nuevo in MAPEO_MODELOS.items():
        DispositivoGPS.objects.filter(modelo=antiguo).update(modelo=nuevo)


def revertir_modelos(apps, schema_editor):
    # No es posible reconstruir el modelo específico desde la marca; se deja en la
    # marca genérica (la migración inversa no pierde dispositivos).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0077_gps_permisos'),
    ]

    operations = [
        migrations.AddField(
            model_name='dispositivogps',
            name='modelo_otro',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='dispositivogps',
            name='modelo',
            field=models.CharField(
                choices=[
                    ('emulador', 'Emulador NMEA'),
                    ('teltonika', 'Teltonika'),
                    ('queclink', 'Queclink'),
                    ('coban', 'Coban'),
                    ('otro', 'Otro'),
                ],
                default='emulador',
                max_length=30,
            ),
        ),
        migrations.RunPython(simplificar_modelos, revertir_modelos),
    ]
