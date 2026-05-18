import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


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
