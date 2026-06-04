"""
views_gps.py — Endpoints del módulo de Geolocalización GPS.

Sigue los patrones del proyecto:
  - DRF APIView + IsAuthenticated (salvo PosicionView, que es ingesta por IMEI).
  - Aislamiento por empresa: toda consulta filtra por la empresa del usuario.
  - error_response() para errores, Response() para éxito.
  - registrar_log() en toda operación de escritura.

Endpoints:
    GET/POST        /api/empresa/gps/dispositivos/
    GET/PUT/DELETE  /api/empresa/gps/dispositivos/<id>/
    POST            /api/empresa/gps/dispositivos/<id>/asignar/
    POST            /api/empresa/gps/dispositivos/<id>/desasignar/
    POST            /api/empresa/gps/posicion/              (sin JWT — ingesta)
    GET             /api/empresa/gps/vehiculos/posicion/
"""
import math
import secrets

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    Empresa, Vehiculo, Ubicacion, Rol,
    DispositivoGPS, Ruta, TipoNotificacion,
)
from .error_helpers import error_response
from .audit import registrar_log
from . import traccar_client


def _nombre_traccar(dispositivo):
    """Nombre visible en Traccar: patente del vehículo si lo tiene, si no el IMEI."""
    if dispositivo.vehiculo_id and dispositivo.vehiculo:
        return dispositivo.vehiculo.patente
    return dispositivo.imei


# ── Helpers locales (evitan import circular con views.py) ─────────────────────

def _get_empresa(request):
    """Empresa del USUARIO, o la indicada por ?empresa_id= para SUPERADMIN.

    Devuelve None si no se puede determinar (el caller responde el error).
    """
    user = request.user
    if user.rol == Rol.SUPERADMIN:
        eid = request.query_params.get('empresa_id') or request.data.get('empresa_id')
        if not eid:
            return None
        return Empresa.objects.filter(pk=eid).first()
    if not user.empresa_id:
        return None
    return user.empresa


def _tiene_permiso(user, codigo):
    """True si el plan de la empresa del usuario incluye `codigo`. SUPERADMIN siempre."""
    if user.rol == Rol.SUPERADMIN:
        return True
    if user.rol == Rol.CONDUCTOR:
        return False
    plan = getattr(user.empresa, 'plan', None) if user.empresa_id else None
    if not plan:
        return False
    return plan.permisos.filter(codigo=codigo).exists()


def _modelo_display(d):
    """Texto visible del modelo: el nombre libre si la marca es 'otro'."""
    if d.modelo == 'otro' and d.modelo_otro:
        return d.modelo_otro
    return d.get_modelo_display()


# Longitud del nombre libre del modelo cuando la marca es 'otro'.
MODELO_OTRO_MIN, MODELO_OTRO_MAX = 2, 50


def _validar_modelo_otro(modelo, modelo_otro):
    """Normaliza y valida el nombre libre del modelo.

    Devuelve (valor_normalizado, error). Solo se exige cuando la marca es 'otro';
    para las marcas conocidas el nombre libre se descarta (queda vacío).
    """
    modelo_otro = (modelo_otro or '').strip()
    if modelo == 'otro':
        if not (MODELO_OTRO_MIN <= len(modelo_otro) <= MODELO_OTRO_MAX):
            return None, (f'El nombre del modelo debe tener entre {MODELO_OTRO_MIN} '
                          f'y {MODELO_OTRO_MAX} caracteres.')
        return modelo_otro, None
    return '', None


def _serializar_dispositivo(d):
    """Dict de un DispositivoGPS para las respuestas de lista/detalle."""
    veh = d.vehiculo
    return {
        'id':               d.id,
        'imei':             d.imei,
        'modelo':           d.modelo,
        'modelo_otro':      d.modelo_otro,
        'modelo_display':   _modelo_display(d),
        'activo':           d.activo,
        'vehiculo_id':      veh.id if veh else None,
        'vehiculo_patente': veh.patente if veh else None,
        'vehiculo_nombre':  (f"{veh.marca} {veh.modelo}".strip() if veh else None),
        'tiene_clave':      bool(d.api_key),   # nunca se expone el valor en la lista
        'creado_at':        d.creado_at.isoformat(),
    }


def _broadcast_posicion(empresa_id, payload):
    """Emite la posición al grupo WebSocket gps_{empresa_id}. Falla en silencio."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(f'gps_{empresa_id}', {
                'type': 'position_update',
                **payload,
            })
    except Exception:
        pass


def notificar_rutas_cambiadas(empresa_id):
    """Señala al mapa de flota que las rutas activas cambiaron (alguna se inició,
    finalizó o canceló) para que recargue los trazados en tiempo real.

    Es una señal liviana sin payload: el cliente reconsulta el endpoint de
    posiciones. Falla en silencio para nunca bloquear el flujo de rutas.
    """
    if not empresa_id:
        return
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(f'gps_{empresa_id}', {
                'type': 'rutas_cambiadas',
            })
    except Exception:
        pass


# ── Detección de desviación de ruta ──────────────────────────────────────────

UMBRAL_DESVIACION_M = 200   # metros fuera del corredor para disparar la alerta
COOLDOWN_NOTIF_S    = 300   # segundos mínimos entre notificaciones del mismo vehículo

# Estado en memoria por vehículo. En multi-worker aplica por proceso; suficiente
# para dev y para despliegues con un único worker (gunicorn -w 1 / daphne).
_estado_desviacion = {}   # vehiculo_id → {'desviado': bool, 'ultima_notif': datetime|None}


def _haversine_m(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos puntos geográficos (Haversine)."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _dist_punto_a_segmento(lat, lng, lat1, lng1, lat2, lng2):
    """Distancia mínima en metros del punto al segmento (proyección plana local)."""
    cos_lat = math.cos(math.radians((lat1 + lat2) / 2))
    px = (lng - lng1) * cos_lat
    py = lat - lat1
    dx = (lng2 - lng1) * cos_lat
    dy = lat2 - lat1
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return _haversine_m(lat, lng, lat1, lng1)
    t = max(0.0, min(1.0, (px * dx + py * dy) / seg2))
    return _haversine_m(lat, lng, lat1 + t * dy, lng1 + t * (lng2 - lng1))


def _distancia_a_polyline(lat, lng, polyline):
    """Distancia mínima en metros del punto a la polilínea [[lat,lng],...]."""
    if not polyline or len(polyline) < 2:
        return float('inf')
    return min(
        _dist_punto_a_segmento(lat, lng,
                               polyline[i][0], polyline[i][1],
                               polyline[i + 1][0], polyline[i + 1][1])
        for i in range(len(polyline) - 1)
    )


def _broadcast_evento_gps(empresa_id, payload):
    """Emite un evento genérico al grupo WebSocket gps_{empresa_id}."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(f'gps_{empresa_id}', payload)
    except Exception:
        pass


def _verificar_desviacion_ruta(dispositivo, lat, lng):
    """Detecta si el vehículo se alejó de su ruta activa y emite alertas."""
    vid = dispositivo.vehiculo_id
    if not vid:
        return

    ruta = (
        Ruta.objects
        .filter(vehiculo_id=vid, estado='activo')
        .exclude(polyline=[])
        .only('id', 'nombre', 'polyline')
        .first()
    )
    if not ruta or not ruta.polyline or len(ruta.polyline) < 2:
        _estado_desviacion.pop(vid, None)
        return

    distancia = _distancia_a_polyline(lat, lng, ruta.polyline)
    estado    = _estado_desviacion.get(vid, {'desviado': False, 'ultima_notif': None})
    ahora     = timezone.now()

    if distancia > UMBRAL_DESVIACION_M:
        ya_notificado = (
            estado['ultima_notif'] is not None and
            (ahora - estado['ultima_notif']).total_seconds() < COOLDOWN_NOTIF_S
        )
        if not ya_notificado:
            patente      = dispositivo.vehiculo.patente
            ruta_nombre  = ruta.nombre or f'Ruta #{ruta.id}'
            dist_m       = round(distancia)
            _broadcast_evento_gps(dispositivo.empresa_id, {
                'type':        'route_deviation',
                'vehiculo_id': vid,
                'patente':     patente,
                'distancia_m': dist_m,
                'ruta_nombre': ruta_nombre,
            })
            try:
                from .notificaciones import notificar_admins_empresa
                notificar_admins_empresa(
                    dispositivo.empresa,
                    TipoNotificacion.ACTIVIDAD,
                    f'Vehículo fuera de ruta: {patente}',
                    f'{patente} se alejó {dist_m} m de "{ruta_nombre}".',
                    url_accion='/empresa/mapa',
                    extra={'vehiculo_id': vid, 'ruta_id': ruta.id},
                )
            except Exception:
                pass
            _estado_desviacion[vid] = {'desviado': True, 'ultima_notif': ahora}
        else:
            _estado_desviacion[vid] = {**estado, 'desviado': True}
    else:
        if estado.get('desviado'):
            _broadcast_evento_gps(dispositivo.empresa_id, {
                'type':        'route_on_track',
                'vehiculo_id': vid,
                'patente':     dispositivo.vehiculo.patente,
            })
        _estado_desviacion[vid] = {'desviado': False, 'ultima_notif': estado.get('ultima_notif')}


# ── Dispositivos: lista y creación ────────────────────────────────────────────

class DispositivosListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.ver'):
            return error_response('Sin permiso para ver GPS.', 'SIN_PERMISO', 403)

        dispositivos = (
            DispositivoGPS.objects
            .filter(empresa=empresa)
            .select_related('vehiculo')
        )
        data = [_serializar_dispositivo(d) for d in dispositivos]
        return Response({'dispositivos': data, 'total': len(data)})

    def post(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)

        imei   = (request.data.get('imei') or '').strip()
        modelo = request.data.get('modelo') or 'emulador'
        activo = request.data.get('activo', True)

        if not imei:
            return error_response('El IMEI es obligatorio.', 'VALIDACION', 400)
        if not (10 <= len(imei) <= 20):
            return error_response('El IMEI debe tener entre 10 y 20 caracteres.', 'VALIDACION', 400)
        if DispositivoGPS.objects.filter(imei=imei).exists():
            return error_response('Ya existe un dispositivo con ese IMEI.', 'VALIDACION', 400)

        modelos_validos = [m[0] for m in DispositivoGPS.MODELOS]
        if modelo not in modelos_validos:
            return error_response('Modelo de dispositivo no válido.', 'VALIDACION', 400)

        modelo_otro, err = _validar_modelo_otro(modelo, request.data.get('modelo_otro'))
        if err:
            return error_response(err, 'VALIDACION', 400)

        dispositivo = DispositivoGPS.objects.create(
            empresa=empresa,
            imei=imei,
            modelo=modelo,
            modelo_otro=modelo_otro,
            activo=bool(activo),
            api_key=secrets.token_urlsafe(32),   # secreto de ingesta, generado por el sistema
        )
        # Alta automática en Traccar (si está configurado)
        traccar_client.sincronizar_dispositivo(dispositivo.imei, _nombre_traccar(dispositivo))

        registrar_log('ACTIVIDAD', 'gps_dispositivo_creado', request, detalle={
            'imei': dispositivo.imei,
            'modelo': dispositivo.modelo,
        })
        data = _serializar_dispositivo(dispositivo)
        # La clave se muestra UNA sola vez (al crear) para cargarla en el dispositivo.
        data['api_key'] = dispositivo.api_key
        return Response(data, status=201)


# ── Dispositivo: detalle, edición, eliminación ────────────────────────────────

class DispositivoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _obtener(self, request, id):
        empresa = _get_empresa(request)
        if not empresa:
            return None, None
        dispositivo = (
            DispositivoGPS.objects
            .filter(pk=id, empresa=empresa)
            .select_related('vehiculo')
            .first()
        )
        return empresa, dispositivo

    def get(self, request, id):
        empresa, dispositivo = self._obtener(request, id)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.ver'):
            return error_response('Sin permiso para ver GPS.', 'SIN_PERMISO', 403)
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)
        return Response(_serializar_dispositivo(dispositivo))

    def put(self, request, id):
        empresa, dispositivo = self._obtener(request, id)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)

        cambios = []
        imei_anterior = dispositivo.imei

        if 'imei' in request.data:
            nuevo_imei = (request.data.get('imei') or '').strip()
            if not (10 <= len(nuevo_imei) <= 20):
                return error_response('El IMEI debe tener entre 10 y 20 caracteres.', 'VALIDACION', 400)
            if DispositivoGPS.objects.filter(imei=nuevo_imei).exclude(pk=dispositivo.pk).exists():
                return error_response('Ya existe un dispositivo con ese IMEI.', 'VALIDACION', 400)
            if nuevo_imei != dispositivo.imei:
                cambios.append('imei')
                dispositivo.imei = nuevo_imei

        if 'modelo' in request.data:
            nuevo_modelo = request.data.get('modelo')
            modelos_validos = [m[0] for m in DispositivoGPS.MODELOS]
            if nuevo_modelo not in modelos_validos:
                return error_response('Modelo de dispositivo no válido.', 'VALIDACION', 400)
            # Nombre libre asociado: se exige solo si la marca es 'otro'; en otro
            # caso queda vacío aunque el cliente lo haya enviado.
            nuevo_otro, err = _validar_modelo_otro(nuevo_modelo, request.data.get('modelo_otro'))
            if err:
                return error_response(err, 'VALIDACION', 400)
            if nuevo_modelo != dispositivo.modelo:
                cambios.append('modelo')
                dispositivo.modelo = nuevo_modelo
            if nuevo_otro != dispositivo.modelo_otro:
                cambios.append('modelo_otro')
                dispositivo.modelo_otro = nuevo_otro

        if 'activo' in request.data:
            nuevo_activo = bool(request.data.get('activo'))
            if nuevo_activo != dispositivo.activo:
                cambios.append('activo')
                dispositivo.activo = nuevo_activo

        dispositivo.save()

        # Reflejar el cambio de IMEI en Traccar (si cambió)
        if 'imei' in cambios:
            traccar_client.cambiar_imei(imei_anterior, dispositivo.imei, _nombre_traccar(dispositivo))

        registrar_log('ACTIVIDAD', 'gps_dispositivo_editado', request, detalle={
            'imei': dispositivo.imei,
            'cambios': cambios,
        })
        return Response(_serializar_dispositivo(dispositivo))

    def delete(self, request, id):
        empresa, dispositivo = self._obtener(request, id)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)

        imei = dispositivo.imei
        # Al eliminar, el vehículo asociado queda libre (OneToOne SET_NULL lo hace
        # automáticamente al borrar, pero lo desasignamos explícito para el log).
        if dispositivo.vehiculo_id:
            dispositivo.vehiculo = None
            dispositivo.save(update_fields=['vehiculo'])
        dispositivo.delete()

        # Baja automática en Traccar
        traccar_client.eliminar_dispositivo(imei)

        registrar_log('ACTIVIDAD', 'gps_dispositivo_eliminado', request, detalle={
            'imei': imei,
        })
        return Response({'ok': True})


# ── Asignar / desasignar vehículo ─────────────────────────────────────────────

class AsignarVehiculoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)

        dispositivo = DispositivoGPS.objects.filter(pk=id, empresa=empresa).first()
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)

        vehiculo_id = request.data.get('vehiculo_id')
        if not vehiculo_id:
            return error_response('vehiculo_id es obligatorio.', 'VALIDACION', 400)

        vehiculo = Vehiculo.objects.filter(pk=vehiculo_id, empresa=empresa).first()
        if not vehiculo:
            return error_response('Vehículo no encontrado en esta empresa.', 'NO_ENCONTRADO', 404)

        if dispositivo.vehiculo_id:
            return error_response('El dispositivo ya tiene un vehículo asignado.', 'VALIDACION', 400)
        if hasattr(vehiculo, 'dispositivo_gps'):
            return error_response('El vehículo ya tiene un dispositivo GPS asignado.', 'VALIDACION', 400)

        dispositivo.vehiculo = vehiculo
        dispositivo.save(update_fields=['vehiculo'])

        # Renombrar en Traccar con la patente para identificarlo fácil
        traccar_client.renombrar_dispositivo(dispositivo.imei, vehiculo.patente)

        registrar_log('ACTIVIDAD', 'gps_asignado', request, detalle={
            'imei': dispositivo.imei,
            'vehiculo_id': vehiculo.id,
            'patente': vehiculo.patente,
        })
        return Response({'ok': True, 'vehiculo_patente': vehiculo.patente})


class DesasignarVehiculoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)

        dispositivo = DispositivoGPS.objects.filter(pk=id, empresa=empresa).first()
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)

        patente = dispositivo.vehiculo.patente if dispositivo.vehiculo_id else None
        dispositivo.vehiculo = None
        dispositivo.save(update_fields=['vehiculo'])

        # Al quedar sin vehículo, el nombre en Traccar vuelve a ser el IMEI
        traccar_client.renombrar_dispositivo(dispositivo.imei, dispositivo.imei)

        registrar_log('ACTIVIDAD', 'gps_desasignado', request, detalle={
            'imei': dispositivo.imei,
            'patente': patente,
        })
        return Response({'ok': True})


# ── Regenerar clave de ingesta ────────────────────────────────────────────────

class RegenerarClaveView(APIView):
    """Genera una nueva clave de ingesta para el dispositivo y la devuelve una vez.

    Útil si se perdió la clave o se quiere rotar. La clave anterior deja de ser
    válida de inmediato, así que hay que recargar la nueva en el dispositivo.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)

        dispositivo = DispositivoGPS.objects.filter(pk=id, empresa=empresa).first()
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)

        dispositivo.api_key = secrets.token_urlsafe(32)
        dispositivo.save(update_fields=['api_key'])

        registrar_log('ACTIVIDAD', 'gps_clave_regenerada', request, detalle={'imei': dispositivo.imei})
        return Response({'api_key': dispositivo.api_key})


# ── Ingesta de posición (sin JWT) ─────────────────────────────────────────────

# Retención del historial de ubicaciones GPS. Se purga en una fracción de las
# inserciones (sin cron) para que la tabla no crezca indefinidamente.
UBICACION_RETENCION_DIAS = 30
_PURGA_PROBABILIDAD       = 0.01   # ~1 de cada 100 inserciones dispara la purga
_PURGA_LOTE_MAX           = 2000   # borra como mucho N filas por pasada (no traba la ingesta)


def _purgar_ubicaciones_antiguas():
    """Borra, en un lote acotado, las ubicaciones más viejas que la retención.

    Se ejecuta ocasionalmente desde la ingesta. Falla en silencio: nunca debe
    interrumpir el registro de una posición.
    """
    try:
        import random
        if random.random() >= _PURGA_PROBABILIDAD:
            return
        from django.utils import timezone as _tz
        from datetime import timedelta
        corte = _tz.now() - timedelta(days=UBICACION_RETENCION_DIAS)
        # Acotar con PKs para que el DELETE sea de tamaño limitado (no bloquea).
        viejas = list(
            Ubicacion.objects.filter(timestamp__lt=corte)
            .values_list('pk', flat=True)[:_PURGA_LOTE_MAX]
        )
        if viejas:
            Ubicacion.objects.filter(pk__in=viejas).delete()
    except Exception:
        pass


def _registrar_posicion(dispositivo, lat, lng, vel):
    """Crea la Ubicacion del vehículo y emite la posición por WebSocket.

    Reutilizado por la ingesta directa (PosicionView) y por el webhook de
    Traccar (TraccarWebhookView).
    """
    ubicacion = Ubicacion.objects.create(
        vehiculo=dispositivo.vehiculo,
        latitud=lat,
        longitud=lng,
        velocidad=vel,
    )
    # Mantenimiento ocasional del historial (auto-purga, sin cron).
    _purgar_ubicaciones_antiguas()
    # Conductor asignado (para que el mapa muestre el nombre aunque el marcador
    # se cree directamente desde el WebSocket, sin pasar por la carga REST).
    asig = (
        dispositivo.vehiculo.asignaciones
        .filter(activo=True).select_related('conductor').first()
    )
    conductor = asig.conductor if asig and asig.conductor else None
    _broadcast_posicion(dispositivo.empresa_id, {
        'vehiculo_id':      dispositivo.vehiculo_id,
        'patente':          dispositivo.vehiculo.patente,
        'latitud':          lat,
        'longitud':         lng,
        'velocidad':        vel,
        'timestamp':        ubicacion.timestamp.isoformat(),
        'tiene_conductor':  conductor is not None,
        'conductor_nombre': conductor.nombre if conductor else None,
    })
    _verificar_desviacion_ruta(dispositivo, lat, lng)
    return ubicacion


class PosicionView(APIView):
    """Endpoint que llaman los dispositivos GPS que hablan HTTP (o el emulador).

    No requiere JWT: el dispositivo se identifica por su IMEI. Crea una
    `Ubicacion` para el vehículo asignado y emite la posición por WebSocket.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        imei = (request.data.get('imei') or '').strip()
        if not imei:
            return error_response('IMEI requerido.', 'VALIDACION', 400)

        dispositivo = (
            DispositivoGPS.objects
            .select_related('vehiculo', 'empresa')
            .filter(imei=imei)
            .first()
        )
        if not dispositivo:
            return error_response('Dispositivo no encontrado.', 'NO_ENCONTRADO', 404)
        # Autenticación por clave del dispositivo (si tiene una asignada).
        # Retrocompatible: dispositivos sin api_key validan solo por IMEI.
        if dispositivo.api_key:
            if request.data.get('api_key', '') != dispositivo.api_key:
                return error_response('Credencial del dispositivo inválida.', 'SIN_AUTENTICACION', 401)
        if not dispositivo.activo:
            return error_response('Dispositivo inactivo.', 'VALIDACION', 400)
        if not dispositivo.vehiculo_id:
            return error_response('Dispositivo sin vehículo asignado.', 'VALIDACION', 400)

        try:
            lat = float(request.data.get('latitud'))
            lng = float(request.data.get('longitud'))
            vel = float(request.data.get('velocidad', 0) or 0)
        except (TypeError, ValueError):
            return error_response('Coordenadas inválidas.', 'VALIDACION', 400)

        _registrar_posicion(dispositivo, lat, lng, vel)
        return Response({'ok': True})


# ── Webhook de Traccar (gateway "cualquier GPS") ──────────────────────────────

class TraccarWebhookView(APIView):
    """Recibe el *position forwarding* de Traccar y registra la posición.

    Traccar (auto-hospedado) recibe a los GPS físicos en sus ~200 protocolos y
    reenvía cada posición a este endpoint como JSON:

        { "device": {"uniqueId": "<IMEI>"},
          "position": {"latitude": .., "longitude": .., "speed": <nudos>} }

    El dispositivo se identifica por IMEI (`device.uniqueId`). La velocidad de
    Traccar viene en NUDOS y se convierte a km/h. El canal Traccar→servidor se
    protege con una clave de webhook global opcional (settings.GPS_WEBHOOK_KEY),
    enviada por Traccar en el header `X-Webhook-Key` o el query param `?key=`.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.conf import settings

        clave_cfg = getattr(settings, 'GPS_WEBHOOK_KEY', '') or ''
        if clave_cfg:
            provista = request.headers.get('X-Webhook-Key') or request.query_params.get('key', '')
            if provista != clave_cfg:
                return error_response('Webhook no autorizado.', 'SIN_AUTENTICACION', 401)

        device   = request.data.get('device') or {}
        position = request.data.get('position') or {}
        imei = (device.get('uniqueId') or '').strip()
        if not imei:
            return error_response('Falta device.uniqueId (IMEI).', 'VALIDACION', 400)

        dispositivo = (
            DispositivoGPS.objects
            .select_related('vehiculo', 'empresa')
            .filter(imei=imei)
            .first()
        )
        if not dispositivo:
            # 200 para que Traccar no reintente indefinidamente un IMEI no registrado.
            return Response({'ok': False, 'motivo': 'IMEI no registrado en el sistema.'})
        if not dispositivo.activo or not dispositivo.vehiculo_id:
            return Response({'ok': False, 'motivo': 'Dispositivo inactivo o sin vehículo.'})

        try:
            lat = float(position.get('latitude'))
            lng = float(position.get('longitude'))
            vel_nudos = float(position.get('speed', 0) or 0)
        except (TypeError, ValueError):
            return error_response('Posición inválida.', 'VALIDACION', 400)

        vel_kmh = round(vel_nudos * 1.852, 1)  # Traccar entrega la velocidad en nudos
        _registrar_posicion(dispositivo, lat, lng, vel_kmh)
        return Response({'ok': True})


# ── Últimas posiciones de la flota ────────────────────────────────────────────

class UltimasPosicionesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.ver'):
            return error_response('Sin permiso para ver GPS.', 'SIN_PERMISO', 403)

        ahora = timezone.now()
        dispositivos = (
            DispositivoGPS.objects
            .filter(empresa=empresa, activo=True, vehiculo__isnull=False)
            .select_related('vehiculo', 'vehiculo__empresa')
        )

        vehiculos = []
        for d in dispositivos:
            veh = d.vehiculo
            ult = veh.ubicaciones.order_by('-timestamp').first()
            if not ult:
                continue

            asig = veh.asignaciones.filter(activo=True).select_related('conductor').first()
            conductor = asig.conductor if asig and asig.conductor else None

            # Ruta actualmente en curso del vehículo (si la hay)
            ruta_activa = veh.rutas.filter(estado='activo').order_by('-fecha_inicio').first()

            antiguedad_seg = (ahora - ult.timestamp).total_seconds()
            if antiguedad_seg > 300:           # > 5 minutos → sin señal reciente
                estado = 'sin_señal'
            elif (ult.velocidad or 0) > 2:
                estado = 'movimiento'
            else:
                estado = 'detenido'

            vehiculos.append({
                'vehiculo_id':      veh.id,
                'patente':          veh.patente,
                'marca':            veh.marca,
                'modelo':           veh.modelo,
                'latitud':          ult.latitud,
                'longitud':         ult.longitud,
                'velocidad':        round(ult.velocidad or 0, 1),
                'timestamp':        ult.timestamp.isoformat(),
                'tiene_conductor':  conductor is not None,
                'conductor_nombre': conductor.nombre if conductor else None,
                'estado':           estado,
                'ruta_activa':      ruta_activa.nombre if ruta_activa else None,
                'ruta_activa_id':   ruta_activa.id if ruta_activa else None,
                # Trazado de la ruta en curso para dibujarlo en el mapa ([[lat,lng],...])
                'ruta_polyline':    (ruta_activa.polyline or []) if ruta_activa else [],
            })

        # Ordenar: primero en movimiento, luego detenidos, luego sin señal
        orden = {'movimiento': 0, 'detenido': 1, 'sin_señal': 2}
        vehiculos.sort(key=lambda v: orden.get(v['estado'], 3))

        return Response({'vehiculos': vehiculos})
