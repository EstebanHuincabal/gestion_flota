"""
sanitizers.py — Limpieza server-side de datos de entrada.

Estas funciones son la defensa real de las reglas que el frontend aplica de
forma cosmética (validators.soloTexto): el filtro de cliente puede saltarse
llamando la API directamente, así que la limpieza definitiva vive aquí y se
reutiliza tanto en las vistas públicas como en los serializers.
"""


def sanitizar_nombre(valor: str) -> str:
    """Deja solo texto en nombres y apellidos de personas.

    Conserva únicamente letras (con tildes y ñ, vía ``str.isalpha`` que es
    Unicode-aware), espacios, guion y apóstrofe; descarta dígitos y cualquier
    otro símbolo, y colapsa espacios múltiples.
    """
    if not valor:
        return ''
    limpio = ''.join(ch for ch in valor if ch.isalpha() or ch in " -'")
    return ' '.join(limpio.split())


def validar_nombre_persona(valor: str, etiqueta: str = 'Este campo'):
    """Valida un nombre/apellido de persona y lo devuelve capitalizado.

    Rechaza (en vez de limpiar a medias) cualquier valor que contenga dígitos o
    símbolos: si tras ``sanitizar_nombre`` el texto cambió, es porque tenía
    caracteres no permitidos, así que se lanza ``ValidationError`` en lugar de
    guardar un nombre corrupto ("Ju4n" -> "Jun"). Solo deja pasar letras (con
    tildes y ñ), espacios, guion y apóstrofe. Devuelve el valor con ``.title()``.
    """
    from rest_framework import serializers
    original = ' '.join((valor or '').split())
    if not original:
        raise serializers.ValidationError(f'{etiqueta} es obligatorio.')
    limpio = sanitizar_nombre(valor)
    if limpio != original:
        raise serializers.ValidationError(f'{etiqueta} solo puede contener letras.')
    return limpio.title()


def sanitizar_texto(valor: str) -> str:
    """Limpieza básica para campos de texto libre (razón social, dirección…).

    Permite números y signos habituales de un nombre comercial, pero elimina
    caracteres de control y los símbolos ``<`` y ``>`` para evitar inyección de
    HTML/scripts almacenada. No reemplaza al escape de salida: es defensa en
    profundidad.
    """
    if not valor:
        return ''
    limpio = ''.join(ch for ch in valor if ord(ch) >= 32 and ch not in '<>')
    return ' '.join(limpio.split())
