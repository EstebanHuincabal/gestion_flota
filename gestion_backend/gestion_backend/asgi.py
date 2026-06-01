import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestion_backend.settings")

# django.setup() debe llamarse ANTES de cualquier import de modelos, consumers o
# rest_framework. get_asgi_application() lo invoca internamente, pero hacerlo
# explícito garantiza el orden correcto incluso si el import chain cambia.
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from g_de_flota import routing

application = ProtocolTypeRouter({
    "http":      get_asgi_application(),
    "websocket": URLRouter(routing.websocket_urlpatterns),
})
