import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0020_predictivo_permisos'),
    ]

    operations = [
        # ── Nuevos campos en PlanSuscripcion ──────────────────────────────
        migrations.AddField(
            model_name='plansuscripcion',
            name='descripcion',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='precio_mensual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='precio_anual',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='max_usuarios',
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='modulos',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='orden',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='plansuscripcion',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        # Cambiar tipo de max_flotas, max_vehiculos, max_conductores a PositiveIntegerField
        migrations.AlterField(
            model_name='plansuscripcion',
            name='max_flotas',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='plansuscripcion',
            name='max_vehiculos',
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.AlterField(
            model_name='plansuscripcion',
            name='max_conductores',
            field=models.PositiveIntegerField(default=10),
        ),

        # ── Nuevo modelo CambioPlan ───────────────────────────────────────
        migrations.CreateModel(
            name='CambioPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('motivo', models.CharField(blank=True, default='', max_length=500)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('cambiado_por', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='cambios_plan',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cambios_plan',
                    to='g_de_flota.empresa',
                )),
                ('plan_antes', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='cambios_salida',
                    to='g_de_flota.plansuscripcion',
                )),
                ('plan_despues', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='cambios_entrada',
                    to='g_de_flota.plansuscripcion',
                )),
            ],
            options={
                'verbose_name': 'Cambio de Plan',
                'verbose_name_plural': 'Cambios de Plan',
                'ordering': ['-fecha'],
            },
        ),
    ]
