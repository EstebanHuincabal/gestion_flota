"""
0092 — Crea el modelo Aviso y los permisos avisos.ver / avisos.enviar.
Los permisos se asignan a todos los planes existentes.
"""
from django.db import migrations, models
import django.db.models.deletion


PERMISOS = [
    ('avisos.ver',     'Ver bandeja de avisos',       'avisos'),
    ('avisos.enviar',  'Redactar y enviar avisos',    'avisos'),
]


def crear_permisos_avisos(apps, schema_editor):
    Permiso         = apps.get_model('g_de_flota', 'Permiso')
    PlanSuscripcion = apps.get_model('g_de_flota', 'PlanSuscripcion')
    creados = []
    for codigo, nombre, categoria in PERMISOS:
        permiso, _ = Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'categoria': categoria},
        )
        creados.append(permiso)
    for plan in PlanSuscripcion.objects.all():
        plan.permisos.add(*creados)


def revertir(apps, schema_editor):
    Permiso = apps.get_model('g_de_flota', 'Permiso')
    Permiso.objects.filter(codigo__in=[c for c, _, _ in PERMISOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0091_mantencion_es_correctivo_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aviso',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destino',      models.CharField(max_length=20, choices=[('flota','Toda la flota'),('conductor','Conductor específico'),('admins','Administradores')])),
                ('asunto',       models.CharField(max_length=150)),
                ('mensaje',      models.TextField(max_length=2000)),
                ('fecha',        models.DateTimeField(auto_now_add=True)),
                ('empresa',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avisos', to='g_de_flota.empresa')),
                ('emisor',       models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='avisos_enviados', to='g_de_flota.usuario')),
                ('destinatario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='avisos_recibidos_directo', to='g_de_flota.usuario')),
            ],
            options={'ordering': ['-fecha'], 'verbose_name': 'Aviso', 'verbose_name_plural': 'Avisos'},
        ),
        migrations.RunPython(crear_permisos_avisos, revertir),
    ]
