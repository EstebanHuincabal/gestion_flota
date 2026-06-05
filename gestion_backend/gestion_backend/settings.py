"""
Django settings for gestion_backend project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# En dev carga el .env de la raíz del monorepo; en Docker las variables llegan por env_file.
load_dotenv(BASE_DIR.parent / '.env', override=False)

SECRET_KEY = os.environ['SECRET_KEY']
# Clave maestra del cifrado Fernet (RUTs, teléfonos, etc.). NO cambiar en
# producción: los datos ya cifrados quedarían ilegibles.
ENCRYPTION_KEY = os.environ['ENCRYPTION_KEY']
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []

INSTALLED_APPS = [
    'daphne',                       # debe ser primero: convierte runserver a ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'g_de_flota',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'g_de_flota.middleware.ErrorHandlerMiddleware',
    'g_de_flota.middleware.ConfiguracionSeguridadMiddleware',
    'g_de_flota.middleware.BloqueoSuscripcionMiddleware',
]

ROOT_URLCONF = 'gestion_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestion_backend.wsgi.application'

# Si POSTGRES_DB está definido (producción/Docker) usa PostgreSQL; si no, SQLite (dev local).
if os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.environ['POSTGRES_DB'],
            'USER':     os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST':     os.environ.get('POSTGRES_HOST', 'db'),
            'PORT':     os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # destino de collectstatic (lo sirve Nginx en prod)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Media (fotos de solicitudes, comprobantes, etc.) ──────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Firebase Cloud Messaging (push notifications) ─────────────────────────────
# Descarga tu serviceAccountKey.json desde Firebase Console →
# Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada
# y guárdalo en: gestion_backend/serviceAccountKey.json
FIREBASE_CREDENTIALS = BASE_DIR / 'serviceAccountKey.json'

CORS_ALLOWED_ORIGINS = [
    # Sistema web
    "http://localhost:7183",
    "http://127.0.0.1:7183",
    # App conductores — Vite dev server
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    # App conductores — Capacitor WebView (Android usa http://localhost internamente)
    "http://localhost",
    # App conductores — Capacitor WebView iOS (usa este esquema en producción)
    "capacitor://localhost",
]
CORS_ALLOW_ALL_ORIGINS = DEBUG  # en dev permite todos los orígenes para WS
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:7183",
    "http://127.0.0.1:7183",
    "http://localhost:5174",
    "http://localhost",
    "capacitor://localhost",
]

# Orígenes adicionales de producción (IP/dominio del servidor), separados por coma.
# Ej: CORS_ALLOWED_ORIGINS_EXTRA="http://157.180.85.17"
_extra_cors = os.getenv('CORS_ALLOWED_ORIGINS_EXTRA', '')
if _extra_cors:
    CORS_ALLOWED_ORIGINS += [o.strip() for o in _extra_cors.split(',') if o.strip()]
_extra_csrf = os.getenv('CSRF_TRUSTED_ORIGINS_EXTRA', '')
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS += [o.strip() for o in _extra_csrf.split(',') if o.strip()]

# ── Headers de seguridad HTTP (solo producción) ────────────────────────────────
# Se aplican únicamente con DEBUG=False para no entorpecer el desarrollo local
# (el SSL redirect y HSTS requieren HTTPS, que no hay en dev). Detrás de un proxy
# (Nginx) Django reconoce HTTPS por la cabecera X-Forwarded-Proto.
SECURE_CONTENT_TYPE_NOSNIFF = True          # bloquea MIME sniffing
X_FRAME_OPTIONS             = 'DENY'        # anti-clickjacking (refuerza el middleware)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER     = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT         = True
    SESSION_COOKIE_SECURE       = True
    CSRF_COOKIE_SECURE          = True
    SECURE_HSTS_SECONDS         = 31536000   # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD         = True

AUTH_USER_MODEL = 'g_de_flota.Usuario'

# ── Email ──────────────────────────────────────────────────────────────────────
# En desarrollo usa el backend de consola (imprime en terminal).
# Para producción configura las variables SMTP en .env.
EMAIL_BACKEND       = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST          = os.getenv('EMAIL_HOST', '')
EMAIL_PORT          = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS       = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.getenv('DEFAULT_FROM_EMAIL', 'Sistema de Flota <no-reply@flota.cl>')

AUTHENTICATION_BACKENDS = [
    'g_de_flota.backends.RutBackend',           # login frontend: RUT + password
    'django.contrib.auth.backends.ModelBackend', # login admin:    username + password
]

# El email no es único (varios usuarios pueden compartir dirección de contacto).
# El login siempre usa RUT, no email, por lo que auth.W004 no aplica.
SILENCED_SYSTEM_CHECKS = ['auth.W004']

# ── JWT ────────────────────────────────────────────────────────────────────────
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'AUTH_HEADER_TYPES':      ('Bearer',),
    'USER_ID_FIELD':          'id',
    'USER_ID_CLAIM':          'user_id',
}

# ── WebSockets (Django Channels) ───────────────────────────────────────────────
ASGI_APPLICATION = 'gestion_backend.asgi.application'

# ── Transbank Webpay Plus ──────────────────────────────────────────────────────
# Credenciales fuera del código: vienen del .env (dev usa las de integración
# pública; producción, las reales). 'integration' es el fallback seguro de ambiente.
TRANSBANK_ENVIRONMENT   = os.environ.get('TRANSBANK_ENVIRONMENT', 'integration')  # 'integration' | 'production'
TRANSBANK_COMMERCE_CODE = os.environ.get('TRANSBANK_COMMERCE_CODE', '')
TRANSBANK_API_KEY       = os.environ.get('TRANSBANK_API_KEY', '')

# URL base del frontend (para redirects de retorno Transbank)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:7183')

# OneClick Mall (tarjeta guardada / cobros automáticos)
ONECLICK_COMMERCE_CODE = os.environ.get('ONECLICK_COMMERCE_CODE', '')
ONECLICK_CHILD_CODE    = os.environ.get('ONECLICK_CHILD_CODE',    '')

# Clave del webhook de Traccar (gateway GPS). Si está vacía, el endpoint no
# exige autenticación (útil en desarrollo). En producción definir un valor y
# configurar Traccar para enviarlo en el header X-Webhook-Key.
GPS_WEBHOOK_KEY = os.getenv('GPS_WEBHOOK_KEY', '')

# Sincronización con Traccar (alta/baja automática de dispositivos).
# Si TRACCAR_URL está vacío, la sincronización queda desactivada (dev sin Traccar).
TRACCAR_URL      = os.getenv('TRACCAR_URL', '')          # ej: http://traccar:8082
TRACCAR_USER     = os.getenv('TRACCAR_USER', 'admin')
TRACCAR_PASSWORD = os.getenv('TRACCAR_PASSWORD', '')

# En producción usa Redis (si REDIS_URL está definido); en dev, capa en memoria.
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
    # Cache compartida entre workers → el rate limiting cuenta bien en producción.
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }
    # En dev, cache en memoria del proceso (suficiente para probar el rate limiting).
    CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    }

# ── Rate limiting (django-ratelimit) ───────────────────────────────────────────
RATELIMIT_ENABLE = os.getenv('RATELIMIT_ENABLE', 'True') == 'True'
