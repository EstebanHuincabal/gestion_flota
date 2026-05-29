from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/notificaciones/$',                         consumers.NotificacionesConsumer.as_asgi()),
    re_path(r'^ws/solicitudes/(?P<empresa_id>\d+)/$',        consumers.SolicitudesConsumer.as_asgi()),
    re_path(r'^ws/geolocalizacion/(?P<empresa_id>\d+)/$',    consumers.GeolocalizacionConsumer.as_asgi()),
    re_path(r'^ws/conductor/$',                              consumers.ConductorConsumer.as_asgi()),
]
