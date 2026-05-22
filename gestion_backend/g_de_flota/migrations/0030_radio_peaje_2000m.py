from django.db import migrations, models


def actualizar_radio(apps, schema_editor):
    ConfiguracionRuta = apps.get_model('g_de_flota', 'ConfiguracionRuta')
    ConfiguracionRuta.objects.filter(radio_deteccion_peaje=500).update(radio_deteccion_peaje=2000)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0029_rutas_permisos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracionruta',
            name='radio_deteccion_peaje',
            field=models.IntegerField(default=2000, help_text='Radio en metros'),
        ),
        migrations.RunPython(actualizar_radio, migrations.RunPython.noop),
    ]
