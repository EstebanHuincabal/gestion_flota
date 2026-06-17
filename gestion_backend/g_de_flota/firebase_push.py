"""
firebase_push.py — Servicio de push notifications via Firebase Cloud Messaging.

CONFIGURACIÓN NECESARIA (una sola vez):
  1. Ve a https://console.firebase.google.com
  2. Crea un proyecto (o usa uno existente).
  3. En el proyecto → Configuración (⚙) → Cuentas de servicio →
     "Generar nueva clave privada" → descarga el JSON.
  4. Guarda ese archivo como:
         gestion_backend/serviceAccountKey.json
  5. En settings.py agrega:
         FIREBASE_CREDENTIALS = BASE_DIR / 'serviceAccountKey.json'

El módulo funciona en modo "silencioso" si Firebase no está configurado:
las llamadas a enviar_push() se ignoran sin lanzar excepción.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Inicialización lazy (una sola vez) ───────────────────────────────────────
_firebase_app  = None
_firebase_ok   = False   # True solo después de inicializar con éxito
_init_intentado = False


def _inicializar():
    """Intenta inicializar el SDK de Firebase. Falla silenciosamente."""
    global _firebase_app, _firebase_ok, _init_intentado
    if _init_intentado:
        return
    _init_intentado = True

    try:
        import firebase_admin
        from firebase_admin import credentials

        from django.conf import settings
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS', None)

        if not cred_path or not Path(cred_path).exists():
            logger.warning(
                '[Push] Firebase no configurado. '
                'Agrega FIREBASE_CREDENTIALS en settings.py y el archivo serviceAccountKey.json.'
            )
            return

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(cred_path))
            _firebase_app = firebase_admin.initialize_app(cred)

        _firebase_ok = True
        logger.info('[Push] Firebase Admin SDK inicializado correctamente.')

    except ImportError:
        logger.warning(
            '[Push] firebase-admin no instalado. '
            'Ejecuta: pip install firebase-admin'
        )
    except Exception as e:
        logger.error(f'[Push] Error al inicializar Firebase: {e}')


# ─── Historial de notificaciones del conductor ─────────────────────────────────

# Tipos cuyo registro en el historial ya lo crea `notificar()` (con su propio
# título/mensaje/url_accion) en el sitio donde se llama a enviar_push(). Evita
# duplicar la notificación en el historial del conductor.
_TIPOS_YA_REGISTRADOS = {
    'mantencion_programada', 'mantencion_estado', 'mantencion_eliminada',
    'mantencion_aprobada', 'solicitud_aprobada', 'solicitud_rechazada',
    'ruta_asignada', 'ruta_iniciada', 'ruta_finalizada', 'ruta_cancelada',
}

# Mapeo tipo de push → URL a la que debe navegar la app al tocar la notificación.
_RUTAS_POR_TIPO = {
    'recordatorio_ruta':       lambda d: f"/rutas/{d.get('ruta_id')}",
    'recordatorio_finalizar':  lambda d: f"/rutas/{d.get('ruta_id')}",
    'recordatorio_vispera':    lambda d: f"/rutas/{d.get('ruta_id')}",
    'recordatorio_checklist':  lambda d: f"/rutas/{d.get('ruta_id')}/checklist",
    'recordatorio_documentos': lambda d: '/documentos',
    'checklist_completado':    lambda d: f"/rutas/{d.get('ruta_id')}",
    'checklist_enviado':       lambda d: f"/rutas/{d.get('ruta_id')}",
}


def _url_accion(tipo: str, data: dict) -> str:
    armar = _RUTAS_POR_TIPO.get(tipo)
    if not armar:
        return ''
    try:
        return armar(data)
    except Exception:
        return ''


def _registrar_notificacion(usuario, titulo: str, cuerpo: str, data: dict = None):
    """Guarda la push como notificación in-app para el historial del conductor.

    Se omite si el tipo ya fue registrado por notificar() en el sitio de llamada
    (ver _TIPOS_YA_REGISTRADOS), para no duplicar la entrada en el historial.
    Nunca lanza excepción — falla silenciosamente.
    """
    data = data or {}
    tipo = data.get('tipo')
    if not tipo or tipo in _TIPOS_YA_REGISTRADOS:
        return
    try:
        from .models import Notificacion, TipoNotificacion
        tipo_valido = tipo if tipo in TipoNotificacion.values else TipoNotificacion.ACTIVIDAD
        Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo_valido,
            titulo=titulo,
            mensaje=cuerpo,
            url_accion=_url_accion(tipo, data),
            extra=data,
        )
    except Exception as e:
        logger.error(f'[Push] Error al registrar notificación de usuario {usuario.id}: {e}')


# ─── API pública ───────────────────────────────────────────────────────────────

def enviar_push(usuario, titulo: str, cuerpo: str, data: dict = None):
    """
    Envía una push notification al dispositivo del usuario.

    - usuario: instancia de Usuario con notif_prefs['push_token'] guardado.
    - titulo:  Título de la notificación (texto corto).
    - cuerpo:  Cuerpo / descripción de la notificación.
    - data:    Dict de pares clave-valor que la app puede leer al abrir la notif.

    Registra la notificación en el historial del conductor (salvo que ya la haya
    registrado notificar()) y luego intenta enviarla por FCM.
    Nunca lanza excepción — falla silenciosamente.
    """
    _registrar_notificacion(usuario, titulo, cuerpo, data)

    _inicializar()
    if not _firebase_ok:
        return

    try:
        prefs = getattr(usuario, 'notif_prefs', None) or {}
        token = prefs.get('push_token', '').strip()
        if not token:
            logger.warning(f'[Push] Usuario {usuario.id} no tiene push_token — notificación omitida.')
            return

        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='solicitudes',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default'),
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f'[Push] Enviada a usuario {usuario.id} — FCM response: {response}')

    except Exception as e:
        logger.error(f'[Push] Error al enviar push a usuario {usuario.id}: {e}')
