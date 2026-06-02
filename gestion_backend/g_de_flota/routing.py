from django.urls import re_path


# ── Lazy ASGI wrapper ─────────────────────────────────────────────────────────
# consumers.py importa simplejwt que a su vez importa modelos de Django.
# Si ese import ocurre a nivel de módulo (antes de django.setup()), Django
# lanza AppRegistryNotReady.  Este wrapper difiere la carga del consumer
# hasta la primera conexión WebSocket real, momento en que Django ya está listo.

class _Lazy:
    """Envuelve un consumer por nombre; lo resuelve en la primera petición."""
    def __init__(self, name):
        self._name = name
        self._app  = None

    async def __call__(self, scope, receive, send):
        if self._app is None:
            from g_de_flota import consumers as _c
            import django
            if not django.apps.registry.apps.ready:
                django.setup()
            self._app = getattr(_c, self._name).as_asgi()
        await self._app(scope, receive, send)


websocket_urlpatterns = [
    re_path(r'^ws/notificaciones/$',                         _Lazy('NotificacionesConsumer')),
    re_path(r'^ws/solicitudes/(?P<empresa_id>\d+)/$',        _Lazy('SolicitudesConsumer')),
    re_path(r'^ws/conductor/$',                              _Lazy('ConductorConsumer')),
    re_path(r'^ws/gps/(?P<empresa_id>\d+)/$',                _Lazy('GPSConsumer')),
]
