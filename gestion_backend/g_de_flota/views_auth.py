"""
views_auth.py — Vistas de autenticación JWT con verificación de cuenta activa.

El TokenRefreshView estándar de simplejwt solo valida que el refresh token sea
válido, sin volver a consultar el estado del usuario. Esto permite que una cuenta
desactivada (is_active=False) siga renovando su access token indefinidamente.

TokenRefreshSeguroView cierra esa puerta: al refrescar, verifica que el usuario
exista y siga activo. Combinado con la verificación de is_active que simplejwt ya
hace en cada request (USER_AUTHENTICATION_RULE), un conductor desactivado pierde
el acceso en cuanto su access token vigente caduca o intenta renovarlo.
"""
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario


class TokenRefreshSeguroSerializer(TokenRefreshSerializer):
    """Refresh que rechaza tokens de usuarios inexistentes o desactivados."""

    def validate(self, attrs):
        # Decodificar el refresh token para obtener el user_id antes de renovar
        token   = RefreshToken(attrs['refresh'])
        user_id = token.get('user_id')

        try:
            user = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            raise InvalidToken('La cuenta ya no existe.')

        if not user.is_active:
            raise InvalidToken('La cuenta está desactivada.')
        if getattr(user, 'is_blocked', False):
            raise InvalidToken('La cuenta está bloqueada.')

        return super().validate(attrs)


class TokenRefreshSeguroView(TokenRefreshView):
    serializer_class = TokenRefreshSeguroSerializer
