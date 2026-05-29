from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Vehiculo, Ubicacion, Ruta, Asignacion, Empresa, Rol, descifrar
from .geo_helpers import calcular_estado_vehiculo, get_resumen_flota
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def _empresa_para_geo(request):
    """Devuelve la Empresa para el usuario autenticado (USUARIO o SUPERADMIN)."""
    user = request.user
    if user.rol == Rol.SUPERADMIN:
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            return None, Response({'error': 'Se requiere empresa_id.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Empresa.objects.get(pk=empresa_id), None
        except Empresa.DoesNotExist:
            return None, Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    empresa = getattr(user, 'empresa', None)
    if not empresa:
        return None, Response({'error': 'Sin empresa asignada.'}, status=status.HTTP_400_BAD_REQUEST)
    return empresa, None


def _vehiculo_dict(v):
    ultima = Ubicacion.objects.filter(vehiculo=v).order_by('-timestamp').first()
    ruta_activa = Ruta.objects.filter(vehiculo=v, estado='activo').prefetch_related('paradas').first()
    asignacion  = Asignacion.objects.filter(vehiculo=v, activo=True).select_related('conductor').first()

    conductor_nombre = None
    if asignacion and asignacion.conductor:
        try:
            conductor_nombre = descifrar(asignacion.conductor.nombre_cifrado)
        except Exception:
            conductor_nombre = asignacion.conductor.email

    return {
        'id':               v.id,
        'patente':          v.patente,
        'marca':            v.marca,
        'modelo':           v.modelo,
        'tipo_combustible': v.tipo_combustible,
        'flota':            v.flota.nombre,
        'estado':           calcular_estado_vehiculo(ultima, ruta_activa),
        'conductor':        conductor_nombre,
        'ultima_ubicacion': {
            'latitud':    ultima.latitud,
            'longitud':   ultima.longitud,
            'velocidad':  ultima.velocidad,
            'timestamp':  ultima.timestamp.isoformat(),
        } if ultima else None,
        'ruta_activa': {
            'id':       ruta_activa.id,
            'nombre':   ruta_activa.nombre,
            'polyline': ruta_activa.polyline or [],
            'paradas':  [
                {
                    'tipo':     p.tipo,
                    'nombre':   p.nombre,
                    'latitud':  p.latitud,
                    'longitud': p.longitud,
                }
                for p in ruta_activa.paradas.order_by('orden')
                if p.latitud and p.longitud
            ],
        } if ruta_activa else None,
    }


class GeolocalizacionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa, err = _empresa_para_geo(request)
        if err:
            return err

        vehiculos = Vehiculo.objects.filter(
            flota__empresa=empresa, activo=True
        ).select_related('flota')

        data = [_vehiculo_dict(v) for v in vehiculos]

        return Response({
            'vehiculos': data,
            'resumen':   get_resumen_flota(empresa),
        })


class RegistrarUbicacionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.rol != Rol.CONDUCTOR:
            return Response({'error': 'Solo conductores.'}, status=status.HTTP_403_FORBIDDEN)

        lat  = request.data.get('latitud')
        lng  = request.data.get('longitud')
        vel  = request.data.get('velocidad', 0)

        if lat is None or lng is None:
            return Response({'error': 'Coordenadas requeridas.'}, status=status.HTTP_400_BAD_REQUEST)

        asignacion = Asignacion.objects.filter(
            conductor=request.user, activo=True
        ).select_related('vehiculo__flota__empresa').first()

        if not asignacion:
            return Response({'error': 'Sin vehículo asignado.'}, status=status.HTTP_400_BAD_REQUEST)

        vehiculo = asignacion.vehiculo
        empresa  = vehiculo.flota.empresa

        ubicacion = Ubicacion.objects.create(
            vehiculo=vehiculo,
            latitud=lat,
            longitud=lng,
            velocidad=vel,
        )

        ruta_activa = Ruta.objects.filter(vehiculo=vehiculo, estado='activo').first()
        estado      = calcular_estado_vehiculo(ubicacion, ruta_activa)

        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'geolocalizacion_{empresa.id}',
                {
                    'type': 'ubicacion_update',
                    'data': {
                        'vehiculo_id': vehiculo.id,
                        'patente':     vehiculo.patente,
                        'latitud':     float(lat),
                        'longitud':    float(lng),
                        'velocidad':   float(vel),
                            'estado':      estado,
                        'timestamp':   ubicacion.timestamp.isoformat(),
                        'ruta_id':     ruta_activa.id if ruta_activa else None,
                    },
                },
            )
        except Exception:
            pass  # WebSocket falla silenciosamente — la ubicación ya se guardó

        return Response({'ok': True, 'estado': estado})
