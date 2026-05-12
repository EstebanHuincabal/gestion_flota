import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0009_asignacion_hasta_alter_permiso_id_documentoconductor'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Documento',
            new_name='DocumentoVehiculo',
        ),
        migrations.AlterField(
            model_name='documentovehiculo',
            name='estado',
            field=models.CharField(choices=[('vigente', 'Vigente'), ('por_vencer', 'Por vencer'), ('vencido', 'Vencido')], default='vigente', max_length=20),
        ),
        migrations.DeleteModel(
            name='ConfiguracionGlobal',
        ),
        migrations.RemoveField(
            model_name='historialacceso',
            name='user',
        ),
        migrations.DeleteModel(
            name='IPBloqueada',
        ),
        migrations.DeleteModel(
            name='PlantillaCorreo',
        ),
        migrations.RemoveConstraint(
            model_name='asignacion',
            name='uq_asignacion_activa',
        ),
        migrations.AddField(
            model_name='asignacion',
            name='conductor',
            field=models.ForeignKey(blank=True, limit_choices_to={'rol': 'CONDUCTOR'}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_conductor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='documentoconductor',
            name='conductor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documentos_conductor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='usuario',
            name='licencia_cifrada',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='telefono_cifrado',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='asignacion',
            name='perfil',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones', to='g_de_flota.perfilusuario'),
        ),
        migrations.AlterField(
            model_name='documentoconductor',
            name='perfil',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='g_de_flota.perfilusuario'),
        ),
        migrations.DeleteModel(
            name='HistorialAcceso',
        ),
    ]