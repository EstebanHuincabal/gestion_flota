from django.db import migrations


def eliminar_peajes_no_liviano(apps, schema_editor):
    Peaje = apps.get_model('g_de_flota', 'Peaje')
    Peaje.objects.exclude(categoria='liviano').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0030_radio_peaje_2000m'),
    ]

    operations = [
        migrations.DeleteModel(name='Ubicacion'),
        migrations.DeleteModel(name='Evento'),
        migrations.RunPython(eliminar_peajes_no_liviano, migrations.RunPython.noop),
        migrations.RemoveField(model_name='peaje', name='categoria'),
        migrations.AlterUniqueTogether(
            name='peaje',
            unique_together={('nombre', 'ruta')},
        ),
    ]
