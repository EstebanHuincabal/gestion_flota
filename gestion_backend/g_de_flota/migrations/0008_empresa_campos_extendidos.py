import hashlib
import base64
from django.db import migrations, models


def migrar_datos_empresa(apps, schema_editor):
    from cryptography.fernet import Fernet
    from django.conf import settings

    key    = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    cipher = Fernet(base64.urlsafe_b64encode(key))

    def cifrar(valor):
        return cipher.encrypt(valor.encode()).decode()

    Empresa = apps.get_model('g_de_flota', 'Empresa')
    for emp in Empresa.objects.all():
        update_fields = ['estado']
        rut    = getattr(emp, 'rut', None)
        activa = getattr(emp, 'activa', True)

        emp.estado = 'activa' if activa else 'suspendida'

        if rut:
            rut_norm     = rut.replace('.', '').strip().lower()
            emp.rut_cifrado = cifrar(rut_norm)
            emp.rut_hash    = hashlib.sha256(rut_norm.encode()).hexdigest()
            update_fields  += ['rut_cifrado', 'rut_hash']

        emp.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ('g_de_flota', '0007_permiso_and_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa', name='rut_cifrado',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='rut_hash',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='email_cifrado',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='telefono_cifrado',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='direccion_cifrada',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='comuna_cifrada',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='ciudad_cifrada',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='empresa', name='region',
            field=models.CharField(
                blank=True, default='', max_length=30,
                choices=[
                    ('arica_y_parinacota', 'Arica y Parinacota'),
                    ('tarapaca', 'Tarapacá'),
                    ('antofagasta', 'Antofagasta'),
                    ('atacama', 'Atacama'),
                    ('coquimbo', 'Coquimbo'),
                    ('valparaiso', 'Valparaíso'),
                    ('metropolitana', 'Metropolitana'),
                    ('ohiggins', "O'Higgins"),
                    ('maule', 'Maule'),
                    ('nuble', 'Ñuble'),
                    ('biobio', 'Biobío'),
                    ('la_araucania', 'La Araucanía'),
                    ('los_rios', 'Los Ríos'),
                    ('los_lagos', 'Los Lagos'),
                    ('aysen', 'Aysén'),
                    ('magallanes', 'Magallanes'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='empresa', name='pais',
            field=models.CharField(blank=True, default='Chile', max_length=100),
        ),
        migrations.AddField(
            model_name='empresa', name='estado',
            field=models.CharField(
                choices=[('activa', 'Activa'), ('suspendida', 'Suspendida')],
                default='activa', max_length=20,
            ),
        ),
        migrations.RunPython(migrar_datos_empresa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='empresa', name='rut_hash',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.RemoveField(model_name='empresa', name='rut'),
        migrations.RemoveField(model_name='empresa', name='activa'),
    ]
