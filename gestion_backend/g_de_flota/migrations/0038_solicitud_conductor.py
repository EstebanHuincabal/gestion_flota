from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0037_mejorar_peajes_categorias'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudConductor',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo',        models.CharField(choices=[('mantencion', 'Mantención'), ('combustible', 'Combustible'), ('incidencia', 'Incidencia'), ('documento', 'Documento')], max_length=20)),
                ('titulo',      models.CharField(max_length=200)),
                ('descripcion', models.TextField(blank=True, default='')),
                ('estado',      models.CharField(choices=[('pendiente', 'Pendiente'), ('en_revision', 'En revisión'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=20)),
                ('prioridad',   models.CharField(choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')], default='media', max_length=10)),
                ('foto',        models.ImageField(blank=True, null=True, upload_to='solicitudes/%Y/%m/')),
                ('respuesta',   models.TextField(blank=True, null=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('conductor',   models.ForeignKey(
                    limit_choices_to={'rol': 'CONDUCTOR'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='solicitudes_conductor',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Solicitud de Conductor',
                'verbose_name_plural': 'Solicitudes de Conductores',
                'ordering': ['-created_at'],
            },
        ),
    ]
