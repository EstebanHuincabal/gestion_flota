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
