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
ENCRYPTION_KEY = os.environ['ENCRYPTION_KEY']
FERNET_KEYS = [os.environ['FERNET_KEY']]
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
TRANSBANK_ENVIRONMENT  = os.environ.get('TRANSBANK_ENVIRONMENT', 'integration')  # 'integration' | 'production'
TRANSBANK_COMMERCE_CODE = os.environ.get('TRANSBANK_COMMERCE_CODE', '597055555532')
TRANSBANK_API_KEY       = os.environ.get('TRANSBANK_API_KEY', '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C')

# URL base del frontend (para redirects de retorno Transbank)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:7183')

# OneClick Mall (tarjeta guardada / cobros automáticos)
ONECLICK_COMMERCE_CODE = os.environ.get('ONECLICK_COMMERCE_CODE', '597055555541')
ONECLICK_CHILD_CODE    = os.environ.get('ONECLICK_CHILD_CODE',    '597055555542')

# En producción usa Redis (si REDIS_URL está definido); en dev, capa en memoria.
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }
