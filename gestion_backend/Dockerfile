FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Fix AppRegistryNotReady ───────────────────────────────────────────────────
# Reescribe los tres archivos que causan el error, garantizando que django.setup()
# ocurre ANTES de cualquier import de routing/consumers/simplejwt.
# Se hace en un RUN (siempre se ejecuta con --no-cache) para no depender de
# que COPY sincronice correctamente los archivos desde Windows.
RUN python - <<'PYEOF'
import pathlib, textwrap

# ── 1. asgi.py ────────────────────────────────────────────────────────────────
pathlib.Path("gestion_backend/asgi.py").write_text(textwrap.dedent("""\
    import os
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestion_backend.settings")
    django.setup()

    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter, URLRouter
    from g_de_flota import routing

    application = ProtocolTypeRouter({
        "http":      get_asgi_application(),
        "websocket": URLRouter(routing.websocket_urlpatterns),
    })
"""))

# ── 2. routing.py ─────────────────────────────────────────────────────────────
# Carga los consumers de forma lazy (en la primera conexion WS real),
# evitando importar simplejwt a nivel de modulo antes de django.setup().
pathlib.Path("g_de_flota/routing.py").write_text(textwrap.dedent("""\
    from django.urls import re_path


    class _Lazy:
        \"\"\"Envuelve un consumer por nombre; lo resuelve en la primera peticion.\"\"\"
        def __init__(self, name):
            self._name = name
            self._app  = None

        async def __call__(self, scope, receive, send):
            if self._app is None:
                from g_de_flota import consumers as _c
                self._app = getattr(_c, self._name).as_asgi()
            await self._app(scope, receive, send)


    websocket_urlpatterns = [
        re_path(r'^ws/notificaciones/$',                         _Lazy('NotificacionesConsumer')),
        re_path(r'^ws/solicitudes/(?P<empresa_id>\\d+)/$',       _Lazy('SolicitudesConsumer')),
        re_path(r'^ws/conductor/$',                              _Lazy('ConductorConsumer')),
        re_path(r'^ws/gps/(?P<empresa_id>\\d+)/$',               _Lazy('GPSConsumer')),
    ]
"""))

# ── 3. consumers.py — eliminar imports de simplejwt a nivel de modulo ─────────
src = pathlib.Path("g_de_flota/consumers.py").read_text()
old = (
    "from rest_framework_simplejwt.tokens import UntypedToken\n"
    "from rest_framework_simplejwt.exceptions import InvalidToken, TokenError\n"
)
if old in src:
    src = src.replace(old, (
        "# simplejwt se importa de forma lazy dentro de cada connect()\n"
        "# para evitar AppRegistryNotReady durante el arranque de Daphne.\n"
    ))
    # Patch cada bloque try que usa UntypedToken
    src = src.replace(
        "            validated = UntypedToken(token_str)\n"
        "            user_id = validated['user_id']\n"
        "        except (InvalidToken, TokenError):",
        "            from rest_framework_simplejwt.tokens import UntypedToken\n"
        "            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError\n"
        "            validated = UntypedToken(token_str)\n"
        "            user_id = validated['user_id']\n"
        "        except Exception:",
    )
    src = src.replace(
        "            validated  = UntypedToken(token_str)\n"
        "            user_id    = validated['user_id']\n"
        "        except (InvalidToken, TokenError):",
        "            from rest_framework_simplejwt.tokens import UntypedToken\n"
        "            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError\n"
        "            validated  = UntypedToken(token_str)\n"
        "            user_id    = validated['user_id']\n"
        "        except Exception:",
    )
    pathlib.Path("g_de_flota/consumers.py").write_text(src)
    print("consumers.py parcheado.")
else:
    print("consumers.py ya estaba parcheado o tiene formato distinto.")

print("Parche completado.")
PYEOF

EXPOSE 8000
