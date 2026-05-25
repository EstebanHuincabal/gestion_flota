from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0038_solicitud_conductor'),
    ]

    operations = [
        # empresa FK (nullable para no romper registros existentes)
        migrations.AddField(
            model_name='solicitudconductor',
            name='empresa',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='solicitudes_conductores',
                to='g_de_flota.empresa',
            ),
        ),
        # vehiculo FK
        migrations.AddField(
            model_name='solicitudconductor',
            name='vehiculo',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='solicitudes_vehiculo',
                to='g_de_flota.vehiculo',
            ),
        ),
        # respondido_por FK
        migrations.AddField(
            model_name='solicitudconductor',
            name='respondido_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='solicitudes_respondidas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # respondido_at
        migrations.AddField(
            model_name='solicitudconductor',
            name='respondido_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # respuesta: cambiar de null=True a blank=True, default=''
        migrations.AlterField(
            model_name='solicitudconductor',
            name='respuesta',
            field=models.TextField(blank=True, default=''),
        ),
        # foto: ImageField → FileField
        migrations.AlterField(
            model_name='solicitudconductor',
            name='foto',
            field=models.FileField(blank=True, null=True, upload_to='solicitudes/%Y/%m/'),
        ),
    ]
