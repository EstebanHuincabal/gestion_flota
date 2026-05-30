"""
Cifra los emails existentes y puebla `email_hash` (SHA-256 del email
normalizado) para deduplicación, búsqueda exacta y login del admin. Idempotente.
"""
import hashlib
from django.db import migrations


def cifrar_emails(apps, schema_editor):
    from g_de_flota.fields import _cipher, cifrar_valor
    cipher = _cipher()
    conn = schema_editor.connection

    with conn.cursor() as cur:
        cur.execute('SELECT id, email FROM g_de_flota_usuario')
        for pk, email in cur.fetchall():
            if email is None or email == '':
                continue
            try:
                plano = cipher.decrypt(str(email).encode()).decode()
            except Exception:
                plano = str(email)   # estaba en claro
                cur.execute('UPDATE g_de_flota_usuario SET email = %s WHERE id = %s',
                            [cifrar_valor(plano), pk])
            ehash = hashlib.sha256(plano.strip().lower().encode()).hexdigest()
            cur.execute('UPDATE g_de_flota_usuario SET email_hash = %s WHERE id = %s',
                        [ehash, pk])


def revertir(apps, schema_editor):
    from g_de_flota.fields import _cipher
    cipher = _cipher()
    conn = schema_editor.connection
    with conn.cursor() as cur:
        cur.execute('SELECT id, email FROM g_de_flota_usuario')
        for pk, email in cur.fetchall():
            if not email:
                continue
            try:
                plano = cipher.decrypt(str(email).encode()).decode()
            except Exception:
                continue
            cur.execute('UPDATE g_de_flota_usuario SET email = %s, email_hash = NULL WHERE id = %s',
                        [plano, pk])


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0070_usuario_email_hash_alter_usuario_email'),
    ]

    operations = [
        migrations.RunPython(cifrar_emails, revertir),
    ]
