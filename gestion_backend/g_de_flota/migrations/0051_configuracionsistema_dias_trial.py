from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0050_tarjeta_guardada'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='dias_trial',
            field=models.PositiveSmallIntegerField(default=14),
        ),
    ]
