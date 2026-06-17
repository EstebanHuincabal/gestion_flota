from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0049_transbank_suscripcion'),
    ]

    operations = [
        migrations.CreateModel(
            name='TarjetaGuardada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tbk_user',    models.CharField(max_length=200)),
                ('username_tb', models.CharField(max_length=100)),
                ('last_4',      models.CharField(blank=True, max_length=4)),
                ('card_type',   models.CharField(blank=True, max_length=40)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('empresa', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tarjeta_guardada',
                    to='g_de_flota.empresa',
                )),
            ],
            options={
                'verbose_name': 'Tarjeta guardada',
                'verbose_name_plural': 'Tarjetas guardadas',
            },
        ),
    ]
