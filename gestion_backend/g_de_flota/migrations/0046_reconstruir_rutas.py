"""
Migración 0046: Reconstrucción del módulo de Rutas

Elimina:
  - Tabla g_de_flota_peaje
  - Tabla g_de_flota_peajeruta
  - Tabla g_de_flota_configuracionruta
  - Campos de costos de Ruta (costo_combustible_est/real, costo_peajes_est/real, costo_total_est/real)
  - Campos de Vehiculo (categoria_peaje, consumo_l_100km)

Crea:
  - Modelo EventoRuta (historial automático + comentarios manuales por ruta)
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0045_eliminar_permiso_dashboard_legacy'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── 1. Eliminar FK peajeruta antes de las tablas padre ─────────────────
        migrations.DeleteModel(
            name='PeajeRuta',
        ),

        # ── 2. Eliminar tablas completas ───────────────────────────────────────
        migrations.DeleteModel(
            name='Peaje',
        ),
        migrations.DeleteModel(
            name='ConfiguracionRuta',
        ),

        # ── 3. Eliminar campos de costos de Ruta ──────────────────────────────
        migrations.RemoveField(
            model_name='ruta',
            name='costo_combustible_est',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='costo_peajes_est',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='costo_total_est',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='costo_combustible_real',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='costo_peajes_real',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='costo_total_real',
        ),

        # ── 4. Eliminar campos de Vehiculo ─────────────────────────────────────
        migrations.RemoveField(
            model_name='vehiculo',
            name='categoria_peaje',
        ),
        migrations.RemoveField(
            model_name='vehiculo',
            name='consumo_l_100km',
        ),

        # ── 5. Crear EventoRuta ────────────────────────────────────────────────
        migrations.CreateModel(
            name='EventoRuta',
            fields=[
                ('id',         models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo',       models.CharField(
                    choices=[('auto', 'Automático'), ('comentario', 'Comentario')],
                    default='comentario',
                    max_length=20,
                )),
                ('texto',      models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eventos_ruta',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('ruta', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='eventos',
                    to='g_de_flota.ruta',
                )),
            ],
            options={
                'verbose_name': 'Evento de Ruta',
                'ordering': ['created_at'],
            },
        ),
    ]
