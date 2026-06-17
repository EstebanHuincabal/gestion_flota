"""
0049 — Integración Transbank Webpay Plus:
  - Campo extra (JSONField) en Usuario
  - ConfiguracionSistema (singleton)
  - Suscripcion
  - PagoTransbank
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0048_calendario_permiso'),
    ]

    operations = [
        # Campo extra en Usuario
        migrations.AddField(
            model_name='usuario',
            name='extra',
            field=models.JSONField(blank=True, default=dict),
        ),

        # ConfiguracionSistema
        migrations.CreateModel(
            name='ConfiguracionSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('terminos_condiciones',   models.TextField(blank=True, default='')),
                ('terminos_version',       models.CharField(blank=True, default='1.0', max_length=20)),
                ('terminos_updated_at',    models.DateTimeField(blank=True, null=True)),
                ('dias_gracia_pago',       models.PositiveSmallIntegerField(default=7)),
                ('bloqueo_automatico',     models.BooleanField(default=True)),
                ('mensaje_pago_pendiente', models.TextField(
                    blank=True,
                    default='Tu suscripción tiene un pago pendiente. Por favor regulariza tu situación para continuar usando el servicio.'
                )),
            ],
            options={
                'verbose_name': 'Configuración del Sistema',
                'verbose_name_plural': 'Configuración del Sistema',
            },
        ),

        # Suscripcion
        migrations.CreateModel(
            name='Suscripcion',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ciclo',             models.CharField(choices=[('mensual', 'Mensual'), ('anual', 'Anual')], default='mensual', max_length=10)),
                ('estado',            models.CharField(choices=[('trial', 'Trial'), ('activa', 'Activa'), ('gracia', 'Período de gracia'), ('suspendida', 'Suspendida'), ('cancelada', 'Cancelada')], default='trial', max_length=20)),
                ('fecha_inicio',      models.DateTimeField(blank=True, null=True)),
                ('fecha_fin_periodo', models.DateTimeField(blank=True, null=True)),
                ('fecha_cancelacion', models.DateTimeField(blank=True, null=True)),
                ('trial_hasta',       models.DateTimeField(blank=True, null=True)),
                ('dias_gracia',       models.PositiveSmallIntegerField(default=7)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
                ('empresa',           models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='suscripcion', to='g_de_flota.empresa')),
                ('plan',              models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='g_de_flota.plansuscripcion')),
            ],
            options={
                'verbose_name': 'Suscripción',
            },
        ),

        # PagoTransbank
        migrations.CreateModel(
            name='PagoTransbank',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token',        models.CharField(max_length=200, unique=True)),
                ('orden_compra', models.CharField(max_length=64, unique=True)),
                ('monto',        models.PositiveIntegerField()),
                ('estado',       models.CharField(choices=[('iniciado', 'Iniciado'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado'), ('anulado', 'Anulado'), ('fallido', 'Fallido')], default='iniciado', max_length=20)),
                ('ciclo',        models.CharField(default='mensual', max_length=10)),
                ('plan_nombre',  models.CharField(blank=True, default='', max_length=50)),
                ('respuesta_tb', models.JSONField(blank=True, default=dict)),
                ('fecha_pago',   models.DateTimeField(blank=True, null=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('empresa',      models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagos', to='g_de_flota.empresa')),
                ('suscripcion',  models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagos', to='g_de_flota.suscripcion')),
            ],
            options={
                'verbose_name': 'Pago Transbank',
                'ordering': ['-created_at'],
            },
        ),
    ]
