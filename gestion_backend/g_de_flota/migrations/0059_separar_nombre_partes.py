# Data migration: separa nombre_cifrado existente en primer_nombre / apellido paterno / materno
from django.db import migrations


def _separar(nombre_completo):
    """Heurística de separación por espacios (entorno de desarrollo)."""
    partes = (nombre_completo or '').split()
    if not partes:
        return '', '', ''
    if len(partes) == 1:
        return partes[0], '', ''
    if len(partes) == 2:
        return partes[0], partes[1], ''
    # 3+ palabras: última = ap. materno, penúltima = ap. paterno, resto = nombre
    return ' '.join(partes[:-2]), partes[-2], partes[-1]


def separar_nombres(apps, schema_editor):
    from g_de_flota.models import cifrar, descifrar
    Usuario = apps.get_model('g_de_flota', 'Usuario')
    for u in Usuario.objects.exclude(nombre_cifrado__isnull=True).exclude(nombre_cifrado=''):
        try:
            completo = descifrar(u.nombre_cifrado)
        except Exception:
            continue
        if not completo:
            continue
        nombre, ap_pat, ap_mat = _separar(completo)
        u.primer_nombre_cifrado    = cifrar(nombre)  if nombre  else None
        u.apellido_paterno_cifrado = cifrar(ap_pat)  if ap_pat  else None
        u.apellido_materno_cifrado = cifrar(ap_mat)  if ap_mat  else None
        u.save(update_fields=[
            'primer_nombre_cifrado',
            'apellido_paterno_cifrado',
            'apellido_materno_cifrado',
        ])


def revertir(apps, schema_editor):
    # No se revierte la separación; nombre_cifrado se mantiene intacto.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0058_usuario_apellido_materno_cifrado_and_more'),
    ]

    operations = [
        migrations.RunPython(separar_nombres, revertir),
    ]
