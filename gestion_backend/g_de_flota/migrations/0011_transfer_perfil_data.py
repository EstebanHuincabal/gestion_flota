from django.db import migrations

def transfer_data(apps, schema_editor):
    Usuario = apps.get_model('g_de_flota', 'Usuario')
    PerfilUsuario = apps.get_model('g_de_flota', 'PerfilUsuario')
    Asignacion = apps.get_model('g_de_flota', 'Asignacion')
    DocumentoConductor = apps.get_model('g_de_flota', 'DocumentoConductor')

    for perfil in PerfilUsuario.objects.all():
        usuario = perfil.user
        changed = False
        if perfil.telefono_cifrado:
            usuario.telefono_cifrado = perfil.telefono_cifrado
            changed = True
        if perfil.licencia_cifrada:
            usuario.licencia_cifrada = perfil.licencia_cifrada
            changed = True
        if changed:
            usuario.save()

    for asig in Asignacion.objects.filter(perfil__isnull=False):
        asig.conductor = asig.perfil.user
        asig.save()

    for doc in DocumentoConductor.objects.filter(perfil__isnull=False):
        doc.conductor = doc.perfil.user
        doc.save()

def reverse_transfer(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0010_documentovehiculo_delete_configuracionglobal_and_more'),
    ]

    operations = [
        migrations.RunPython(transfer_data, reverse_transfer),
    ]