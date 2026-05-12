import hashlib
from .models import Usuario, normalizar_rut


class RutBackend:
    """
    Autentica con RUT + contraseña en lugar de username + contraseña.
    Registrar en settings.py → AUTHENTICATION_BACKENDS.
    """

    def authenticate(self, request, rut=None, password=None, **kwargs):
        if not rut or not password:
            return None

        rut_hash = hashlib.sha256(normalizar_rut(rut).encode()).hexdigest()

        try:
            user = Usuario.objects.get(rut_hash=rut_hash)
        except Usuario.DoesNotExist:
            return None

        if user.check_password(password) and user.is_active:
            return user

        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
