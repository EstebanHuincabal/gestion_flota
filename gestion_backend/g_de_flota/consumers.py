import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.db import database_sync_to_async


# ── Helpers de verificación compartidos ──────────────────────────────────────

@database_sync_to_async
def _verificar_empresa_db(user_id, empresa_id):
    """True si el usuario pertenece a la empresa dada o es SUPERADMIN."""
    from .models import Usuario, Rol
    try:
        u = Usuario.objects.get(pk=user_id)
        if u.rol == Rol.SUPERADMIN:
            return True
        return str(u.empresa_id) == str(empresa_id)
    except Usuario.DoesNotExist:
        return False


@database_sync_to_async
def _verificar_conductor_db(user_id):
    """True si el usuario tiene rol CONDUCTOR."""
    from .models import Usuario, Rol
    try:
        u = Usuario.objects.get(pk=user_id)
        return u.rol == Rol.CONDUCTOR
    except Usuario.DoesNotExist:
        return False


class NotificacionesConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        qs = parse_qs(self.scope['query_string'].decode())
        token_str = qs.get('token', [None])[0]

        if not token_str:
            await self.close(code=4001)
            return

        try:
            validated = UntypedToken(token_str)
            user_id = validated['user_id']
        except (InvalidToken, TokenError):
            await self.close(code=4001)
            return

        self.group_name = f'notif_user_{user_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def nueva_notificacion(self, event):
        await self.send(text_data=json.dumps({
            'type': 'nueva_notificacion',
            'count': event['count'],
            'notificacion': event.get('notificacion'),
        }))


class SolicitudesConsumer(AsyncWebsocketConsumer):
    """
    Canal WebSocket para notificaciones en tiempo real de solicitudes de conductores.
    El panel web se suscribe al grupo de su empresa para recibir alertas instantáneas.
    Autenticación: JWT en query param ?token=<access_token>
    """

    async def connect(self):
        qs         = parse_qs(self.scope['query_string'].decode())
        token_str  = qs.get('token', [None])[0]

        if not token_str:
            await self.close(code=4001)
            return

        try:
            validated  = UntypedToken(token_str)
            user_id    = validated['user_id']
        except (InvalidToken, TokenError):
            await self.close(code=4001)
            return

        # Verificar que el usuario pertenece a la empresa del canal
        empresa_id = self.scope['url_route']['kwargs'].get('empresa_id')
        ok         = await _verificar_empresa_db(user_id, empresa_id)
        if not ok:
            await self.close(code=4003)
            return

        self.group_name = f'solicitudes_{empresa_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def nueva_solicitud(self, event):
        await self.send(text_data=json.dumps({
            'tipo':      'nueva_solicitud',
            'solicitud': event['solicitud'],
        }))


class ConductorConsumer(AsyncWebsocketConsumer):
    """
    Canal WebSocket para la app móvil de conductores.

    Cada conductor se suscribe a su propio grupo `conductor_{user_id}` y recibe:
      - solicitud_actualizada: cuando un admin aprueba o rechaza una de sus solicitudes.

    Autenticación: JWT en query param ?token=<access_token>
    """

    async def connect(self):
        qs        = parse_qs(self.scope['query_string'].decode())
        token_str = qs.get('token', [None])[0]

        if not token_str:
            await self.close(code=4001)
            return

        try:
            validated = UntypedToken(token_str)
            user_id   = validated['user_id']
        except (InvalidToken, TokenError):
            await self.close(code=4001)
            return

        # Verificar que el usuario tiene rol CONDUCTOR
        ok = await _verificar_conductor_db(user_id)
        if not ok:
            await self.close(code=4003)
            return

        self.group_name = f'conductor_{user_id}'
        self.user_id    = user_id
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def solicitud_actualizada(self, event):
        """Notifica al conductor que el estado de una de sus solicitudes cambió."""
        await self.send(text_data=json.dumps({
            'type':         'solicitud_actualizada',
            'solicitud_id': event['solicitud_id'],
            'estado':       event['estado'],
            'respuesta':    event.get('respuesta', ''),
        }))


