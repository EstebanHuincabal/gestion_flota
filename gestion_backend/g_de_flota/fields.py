"""
Campos de modelo con cifrado transparente (Fernet/AES).

El valor se guarda cifrado en la base de datos y se descifra automáticamente
al leerlo, sin que serializers, vistas ni el admin tengan que cambiar: a nivel
de Python siempre trabajan con el texto en claro.

Limitaciones (por diseño de Fernet, que usa IV aleatorio):
  - No se puede filtrar, ordenar ni exigir `unique=True` sobre estos campos a
    nivel de base de datos. Para campos que necesiten búsqueda/unicidad se usa
    una columna `_hash` aparte (ver Vehiculo.patente_hash, Usuario.email_hash).

Durante la transición (datos antiguos en claro), el descifrado degrada con
gracia: si el valor almacenado no es un token Fernet válido, se devuelve tal
cual. Esto hace que el sistema funcione antes y después de la migración de datos.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _cipher() -> Fernet:
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def cifrar_valor(texto: str) -> str:
    return _cipher().encrypt(texto.encode()).decode()


def descifrar_valor(token: str) -> str:
    """Descifra un token Fernet. Si no lo es (dato en claro antiguo), lo devuelve igual."""
    try:
        return _cipher().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return token


class EncryptedTextField(models.TextField):
    """TextField cifrado de forma transparente."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return descifrar_valor(value)

    def to_python(self, value):
        if value is None:
            return None
        # Si ya es texto en claro (formularios), se queda igual.
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        value = str(value)
        if value == '':
            return ''
        return cifrar_valor(value)


class EncryptedCharField(EncryptedTextField):
    """
    Igual que EncryptedTextField pero conserva la semántica de CharField a nivel
    de formularios. En la base de datos se almacena como TEXT porque el texto
    cifrado es más largo que el original.
    """

    def __init__(self, *args, **kwargs):
        # max_length aplica al valor en claro (validación de formulario), no a la
        # columna; la columna es TEXT para alojar el cifrado.
        self.max_length_claro = kwargs.pop('max_length', None)
        super().__init__(*args, **kwargs)


class EncryptedFloatField(EncryptedTextField):
    """Float cifrado: se guarda como texto cifrado y se devuelve como float."""

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return None
        plano = descifrar_valor(value)
        try:
            return float(plano)
        except (ValueError, TypeError):
            return None

    def to_python(self, value):
        if value is None or value == '':
            return None
        if isinstance(value, float):
            return value
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        return cifrar_valor(str(value))


def hash_busqueda(valor: str) -> str:
    """SHA-256 determinista para columnas `_hash` que permiten búsqueda/unicidad."""
    return hashlib.sha256(valor.strip().lower().encode()).hexdigest()
