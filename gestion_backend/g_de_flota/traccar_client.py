"""
traccar_client.py — Sincronización de dispositivos con Traccar (gateway GPS).

Para que Traccar acepte las conexiones de un GPS, el dispositivo debe existir en
Traccar con su `uniqueId` = IMEI. En vez de registrarlo a mano, el sistema lo
sincroniza automáticamente vía la API REST de Traccar: el admin solo gestiona el
dispositivo en nuestro panel y aquí se replican las altas/bajas/cambios.

Configuración (settings / variables de entorno):
    TRACCAR_URL       URL base de la API de Traccar (ej: http://traccar:8082).
                      Si está vacío, la sincronización queda DESACTIVADA (dev).
    TRACCAR_USER      email del usuario admin de Traccar (default: admin).
    TRACCAR_PASSWORD  contraseña de ese usuario.

Todas las funciones son *fail-silent*: si Traccar no responde, NUNCA bloquean la
operación en nuestro sistema (el dispositivo se crea igual en nuestra BD).
"""
import base64
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def _habilitado() -> bool:
    return bool(getattr(settings, 'TRACCAR_URL', ''))


def _auth_header() -> str:
    user = getattr(settings, 'TRACCAR_USER', 'admin')
    pwd  = getattr(settings, 'TRACCAR_PASSWORD', '')
    cred = base64.b64encode(f'{user}:{pwd}'.encode()).decode()
    return f'Basic {cred}'


def _request(method: str, path: str, data=None):
    """Llama a la API de Traccar. Devuelve el JSON de respuesta o None."""
    url = getattr(settings, 'TRACCAR_URL', '').rstrip('/') + path
    headers = {
        'Authorization': _auth_header(),
        'Content-Type':  'application/json',
        'Accept':        'application/json',
    }
    body = json.dumps(data).encode() if data is not None else None
    req  = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def _buscar_por_imei(imei: str):
    """Devuelve el dispositivo de Traccar con ese uniqueId, o None."""
    res = _request('GET', f"/api/devices?uniqueId={urllib.parse.quote(imei)}")
    if isinstance(res, list) and res:
        return res[0]
    return None


def sincronizar_dispositivo(imei: str, nombre: str) -> None:
    """Crea el dispositivo en Traccar si no existe; si existe, actualiza su nombre."""
    if not _habilitado():
        return
    try:
        existente = _buscar_por_imei(imei)
        if existente:
            if existente.get('name') != nombre:
                existente['name'] = nombre
                _request('PUT', f"/api/devices/{existente['id']}", existente)
        else:
            _request('POST', '/api/devices', {'name': nombre, 'uniqueId': imei})
    except Exception as e:
        logger.warning('Traccar: no se pudo sincronizar dispositivo %s: %s', imei, e)


def renombrar_dispositivo(imei: str, nombre: str) -> None:
    """Atajo: actualiza el nombre del dispositivo en Traccar (p. ej. al asignar vehículo)."""
    sincronizar_dispositivo(imei, nombre)


def cambiar_imei(imei_anterior: str, imei_nuevo: str, nombre: str) -> None:
    """Refleja el cambio de IMEI: actualiza el uniqueId del dispositivo en Traccar."""
    if not _habilitado():
        return
    try:
        existente = _buscar_por_imei(imei_anterior)
        if existente:
            existente['uniqueId'] = imei_nuevo
            existente['name']     = nombre
            _request('PUT', f"/api/devices/{existente['id']}", existente)
        else:
            sincronizar_dispositivo(imei_nuevo, nombre)
    except Exception as e:
        logger.warning('Traccar: no se pudo cambiar IMEI %s→%s: %s', imei_anterior, imei_nuevo, e)


def eliminar_dispositivo(imei: str) -> None:
    """Elimina el dispositivo de Traccar (si existe)."""
    if not _habilitado():
        return
    try:
        existente = _buscar_por_imei(imei)
        if existente:
            _request('DELETE', f"/api/devices/{existente['id']}")
    except Exception as e:
        logger.warning('Traccar: no se pudo eliminar dispositivo %s: %s', imei, e)
