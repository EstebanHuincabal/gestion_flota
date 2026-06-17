"""
Cifra los datos ya existentes en las columnas que pasaron a ser campos cifrados
(migración 0066). Es idempotente: omite valores vacíos y los que ya están
cifrados, por lo que puede re-ejecutarse sin doble cifrado.
"""
from django.db import migrations

# tabla -> columnas a cifrar
CAMPOS = {
    'g_de_flota_eventoruta':       ['texto'],
    'g_de_flota_gastooperativo':   ['descripcion'],
    'g_de_flota_mantencion':       ['descripcion', 'taller_proveedor', 'tipo_mantencion'],
    'g_de_flota_notificacion':     ['mensaje', 'titulo'],
    'g_de_flota_parada':           ['direccion', 'latitud', 'longitud', 'nombre', 'notas'],
    'g_de_flota_ruta':             ['descripcion', 'nombre', 'notas'],
    'g_de_flota_solicitudconductor': ['descripcion', 'respuesta', 'titulo'],
    'g_de_flota_ubicacion':        ['latitud', 'longitud', 'velocidad'],
    'g_de_flota_vehiculo':         ['marca', 'modelo'],
}


def cifrar_existentes(apps, schema_editor):
    from g_de_flota.fields import _cipher, cifrar_valor
    cipher = _cipher()
    conn = schema_editor.connection

    def ya_cifrado(valor: str) -> bool:
        try:
            cipher.decrypt(valor.encode())
            return True
        except Exception:
            return False

    with conn.cursor() as cur:
        for tabla, columnas in CAMPOS.items():
            cols = ', '.join(columnas)
            cur.execute(f'SELECT id, {cols} FROM {tabla}')
            filas = cur.fetchall()
            for fila in filas:
                pk = fila[0]
                updates = {}
                for idx, col in enumerate(columnas, start=1):
                    val = fila[idx]
                    if val is None or val == '':
                        continue
                    val = str(val)
                    if ya_cifrado(val):
                        continue
                    updates[col] = cifrar_valor(val)
                if updates:
                    set_clause = ', '.join(f'{c} = %s' for c in updates)
                    params = list(updates.values()) + [pk]
                    cur.execute(f'UPDATE {tabla} SET {set_clause} WHERE id = %s', params)


def revertir(apps, schema_editor):
    """Descifra de vuelta (por si se revierte la migración)."""
    from g_de_flota.fields import _cipher
    cipher = _cipher()
    conn = schema_editor.connection

    with conn.cursor() as cur:
        for tabla, columnas in CAMPOS.items():
            cols = ', '.join(columnas)
            cur.execute(f'SELECT id, {cols} FROM {tabla}')
            for fila in cur.fetchall():
                pk = fila[0]
                updates = {}
                for idx, col in enumerate(columnas, start=1):
                    val = fila[idx]
                    if val is None or val == '':
                        continue
                    try:
                        updates[col] = cipher.decrypt(str(val).encode()).decode()
                    except Exception:
                        continue
                if updates:
                    set_clause = ', '.join(f'{c} = %s' for c in updates)
                    params = list(updates.values()) + [pk]
                    cur.execute(f'UPDATE {tabla} SET {set_clause} WHERE id = %s', params)


class Migration(migrations.Migration):

    dependencies = [
        ('g_de_flota', '0066_alter_eventoruta_texto_and_more'),
    ]

    operations = [
        migrations.RunPython(cifrar_existentes, revertir),
    ]
