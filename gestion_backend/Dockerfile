FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Fix AppRegistryNotReady ───────────────────────────────────────────────────
# Reescribe asgi.py dentro de la imagen para garantizar que django.setup() se
# llama ANTES de cualquier import de routing/consumers, independientemente de
# lo que haya copiado el paso COPY anterior.
RUN python - <<'EOF'
import textwrap, pathlib

asgi = textwrap.dedent("""\
    import os
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestion_backend.settings")

    # django.setup() DEBE ejecutarse antes de cualquier import de apps, modelos
    # o middlewares de terceros (simplejwt, DRF) para evitar AppRegistryNotReady.
    django.setup()

    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter, URLRouter
    from g_de_flota import routing

    application = ProtocolTypeRouter({
        "http":      get_asgi_application(),
        "websocket": URLRouter(routing.websocket_urlpatterns),
    })
""")

pathlib.Path("gestion_backend/asgi.py").write_text(asgi)
print("asgi.py parcheado correctamente.")
EOF

EXPOSE 8000
