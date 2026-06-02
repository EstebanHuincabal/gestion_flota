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
    GET/PUT         /api/empresa/gps/configuracion/
"""
import secrets

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    Empresa, Vehiculo, Ubicacion, Rol,
    DispositivoGPS, ConfiguracionGPS,
)
from .error_helpers import error_response
from .audit import registrar_log


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


def _serializar_dispositivo(d):
    """Dict de un DispositivoGPS para las respuestas de lista/detalle."""
    veh = d.vehiculo
    return {
        'id':               d.id,
        'imei':             d.imei,
        'modelo':           d.modelo,
        'modelo_display':   d.get_modelo_display(),
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

        dispositivo = DispositivoGPS.objects.create(
            empresa=empresa,
            imei=imei,
            modelo=modelo,
            activo=bool(activo),
            api_key=secrets.token_urlsafe(32),   # secreto de ingesta, generado por el sistema
        )
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
            if nuevo_modelo != dispositivo.modelo:
                cambios.append('modelo')
                dispositivo.modelo = nuevo_modelo

        if 'activo' in request.data:
            nuevo_activo = bool(request.data.get('activo'))
            if nuevo_activo != dispositivo.activo:
                cambios.append('activo')
                dispositivo.activo = nuevo_activo

        dispositivo.save()
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

        vehiculo = Vehiculo.objects.filter(pk=vehiculo_id, flota__empresa=empresa).first()
        if not vehiculo:
            return error_response('Vehículo no encontrado en esta empresa.', 'NO_ENCONTRADO', 404)

        if dispositivo.vehiculo_id:
            return error_response('El dispositivo ya tiene un vehículo asignado.', 'VALIDACION', 400)
        if hasattr(vehiculo, 'dispositivo_gps'):
            return error_response('El vehículo ya tiene un dispositivo GPS asignado.', 'VALIDACION', 400)

        dispositivo.vehiculo = vehiculo
        dispositivo.save(update_fields=['vehiculo'])

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


# ── Ingesta de posición (sin JWT — autenticación por IMEI + clave) ────────────

class PosicionView(APIView):
    """Endpoint que llaman los dispositivos GPS (emulador o físico).

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

        ubicacion = Ubicacion.objects.create(
            vehiculo=dispositivo.vehiculo,
            latitud=lat,
            longitud=lng,
            velocidad=vel,
        )

        _broadcast_posicion(dispositivo.empresa_id, {
            'vehiculo_id': dispositivo.vehiculo_id,
            'patente':     dispositivo.vehiculo.patente,
            'latitud':     lat,
            'longitud':    lng,
            'velocidad':   vel,
            'timestamp':   ubicacion.timestamp.isoformat(),
        })

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
            .select_related('vehiculo', 'vehiculo__flota')
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
                'flota':            veh.flota.nombre if veh.flota else None,
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


# ── Configuración del servidor GPS ────────────────────────────────────────────

class ConfiguracionGPSView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.ver'):
            return error_response('Sin permiso para ver GPS.', 'SIN_PERMISO', 403)

        config, _ = ConfiguracionGPS.objects.get_or_create(empresa=empresa)
        return Response({
            'servidor_ip':     config.servidor_ip,
            'servidor_puerto': config.servidor_puerto,
            'protocolo':       config.protocolo,
            'activo':          config.activo,
        })

    def put(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return error_response('Empresa no identificada.', 'VALIDACION', 400)
        if not _tiene_permiso(request.user, 'gps.gestionar'):
            return error_response('Sin permiso para gestionar GPS.', 'SIN_PERMISO', 403)

        config, _ = ConfiguracionGPS.objects.get_or_create(empresa=empresa)

        if 'servidor_ip' in request.data:
            config.servidor_ip = (request.data.get('servidor_ip') or '').strip()
        if 'servidor_puerto' in request.data:
            try:
                puerto = int(request.data.get('servidor_puerto'))
            except (TypeError, ValueError):
                return error_response('Puerto inválido.', 'VALIDACION', 400)
            if not (1 <= puerto <= 65535):
                return error_response('El puerto debe estar entre 1 y 65535.', 'VALIDACION', 400)
            config.servidor_puerto = puerto
        if 'protocolo' in request.data:
            protocolo = request.data.get('protocolo')
            if protocolo not in ('tcp', 'udp'):
                return error_response('Protocolo inválido (tcp/udp).', 'VALIDACION', 400)
            config.protocolo = protocolo
        if 'activo' in request.data:
            config.activo = bool(request.data.get('activo'))

        config.save()
        registrar_log('ACTIVIDAD', 'gps_config_guardada', request, detalle={
            'servidor_ip': config.servidor_ip,
            'servidor_puerto': config.servidor_puerto,
            'protocolo': config.protocolo,
        })
        return Response({
            'servidor_ip':     config.servidor_ip,
            'servidor_puerto': config.servidor_puerto,
            'protocolo':       config.protocolo,
            'activo':          config.activo,
        })
