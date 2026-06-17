from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0055_remove_dias_trial'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='notif_reset_password',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='configuracionsistema',
            name='notif_recordatorio_pago',
            field=models.BooleanField(default=True),
        ),
    ]
