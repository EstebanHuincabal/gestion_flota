"""
Cifra las patentes existentes y puebla `patente_hash` (SHA-256 de la patente
normalizada) para mantener búsquedas y unicidad. Idempotente.
"""
import hashlib
from django.db import migrations


def normalizar_patente(p):
    return (p or "").replace(" ", "").replace("-", "").upper().strip()


def cifrar_patentes(apps, schema_editor):
    from g_de_flota.fields import _cipher, cifrar_valor
    cipher = _cipher()
    conn = schema_editor.connection

    with conn.cursor() as cur:
        cur.execute('SELECT id, patente FROM g_de_flota_vehiculo')
        filas = cur.fetchall()
        for pk, patente in filas:
            if patente is None or patente == '':
                continue
            # ¿ya está cifrada?
            try:
                plano = cipher.decrypt(str(patente).encode()).decode()
            except Exception:
                plano = str(patente)   # estaba en claro
                patente_cifrada = cifrar_valor(normalizar_patente(plano))
                cur.execute('UPDATE g_de_flota_vehiculo SET patente = %s WHERE id = %s',
                            [patente_cifrada, pk])
            phash = hashlib.sha256(normalizar_patente(plano).encode()).hexdigest()
            cur.execute('UPDATE g_de_flota_vehiculo SET patente_hash = %s WHERE id = %s',
                        [phash, pk])


def revertir(apps, schema_editor):
    from g_de_flota.fields import _cipher
    cipher = _cipher()
    conn = schema_editor.connection
    with conn.cursor() as cur:
        cur.execute('SELECT id, patente FROM g_de_flota_vehiculo')
        for pk, patente in cur.fetchall():
            if not patente:
                continue
            try:
                plano = cipher.decrypt(str(patente).encode()).decode()
            except Exception:
                continue
            cur.execute('UPDATE g_de_flota_vehiculo SET patente = %s, patente_hash = NULL WHERE id = %s',
                        [plano, pk])


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0068_vehiculo_patente_hash_alter_vehiculo_patente'),
    ]

    operations = [
        migrations.RunPython(cifrar_patentes, revertir),
    ]
