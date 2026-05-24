"""
views_conductor.py — Endpoints exclusivos para la app móvil de conductores.

Todos los endpoints verifican que el usuario autenticado tenga rol=CONDUCTOR.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Ruta, Rol
from .audit import registrar_log


def _serializar_ruta(ruta, detallado=False):
    """Convierte un objeto Ruta al dict que consume la app móvil."""
    paradas = ruta.paradas.all().order_by('orden')

    paradas_list = [
        {
            'id':          p.id,
            'orden':       p.orden,
            'tipo':        p.tipo,
            'nombre':      p.nombre,
            'direccion':   p.direccion,
            'latitud':     p.latitud,
            'longitud':    p.longitud,
            'notas':       p.notas,
            'hora_estimada': p.hora_estimada.isoformat() if p.hora_estimada else None,
        }
        for p in paradas
    ]

    origen_p  = next((p for p in paradas if p.tipo == 'origen'),  None)
    destino_p = next((p for p in paradas if p.tipo == 'destino'), None)

    result = {
        'id':                    ruta.id,
        'nombre':                ruta.nombre,
        'tipo':                  ruta.tipo,
        'estado':                ruta.estado,
        'descripcion':           ruta.descripcion,
        'origen':                origen_p.nombre  if origen_p  else '',
        'destino':               destino_p.nombre if destino_p else '',
        'fecha_programada':      ruta.fecha_programada.isoformat() if ruta.fecha_programada else None,
        'fecha_inicio':          ruta.fecha_inicio.isoformat()     if ruta.fecha_inicio     else None,
        'fecha_fin':             ruta.fecha_fin.isoformat()        if ruta.fecha_fin        else None,
        'distancia_km':          float(ruta.distancia_km) if ruta.distancia_km else None,
        'duracion_min':          ruta.duracion_min,
        'km_inicio':             ruta.km_inicio,
        'km_fin':                ruta.km_fin,
        'km_reales':             ruta.km_reales,
        'costo_combustible_est': ruta.costo_combustible_est,
        'costo_peajes_est':      ruta.costo_peajes_est,
        'costo_total_est':       ruta.costo_total_est,
        'costo_combustible_real': ruta.costo_combustible_real,
        'costo_peajes_real':      ruta.costo_peajes_real,
        'costo_total_real':       ruta.costo_total_real,
        'notas':                 ruta.notas,
        'polyline':              ruta.polyline or [],
        'paradas':               paradas_list,
        # Vehículo y conductor (siempre incluidos, ligeros)
        'vehiculo': {
            'id':              ruta.vehiculo.id,
            'patente':         ruta.vehiculo.patente,
            'marca':           ruta.vehiculo.marca,
            'modelo':          ruta.vehiculo.modelo,
            'tipo_combustible': ruta.vehiculo.tipo_combustible,
            'km_actuales':     ruta.vehiculo.km_actuales,
            'consumo_l_100km': float(ruta.vehiculo.consumo_l_100km) if ruta.vehiculo.consumo_l_100km else None,
        } if ruta.vehiculo else None,
        'conductor': {
            'id':     ruta.conductor.id,
            'nombre': ruta.conductor.nombre,
        } if ruta.conductor else None,
    }

    # Peajes: solo en vista de detalle individual
    if detallado:
        result['peajes_ruta'] = [
            {
                'id':       pr.id,
                'nombre':   pr.peaje.nombre,
                'ruta':     pr.peaje.ruta,
                'tarifa':   int(pr.tarifa),
                'latitud':  pr.peaje.latitud,
                'longitud': pr.peaje.longitud,
            }
            for pr in ruta.peajesruta.select_related('peaje').all()
        ]

    return result


# ─────────────────────────────────────────
# GET /api/conductor/rutas/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_rutas(request):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores pueden acceder a este endpoint.'}, status=403)

    rutas_qs = (
        Ruta.objects
        .filter(conductor=request.user, estado__in=['pendiente', 'activo', 'finalizado'])
        .select_related('vehiculo', 'conductor')
        .prefetch_related('paradas')
        .order_by('fecha_programada', '-created_at')
    )

    return Response({'rutas': [_serializar_ruta(r) for r in rutas_qs]})


# ─────────────────────────────────────────
# GET /api/conductor/rutas/:id/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_detalle_ruta(request, ruta_id):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    try:
        ruta = (
            Ruta.objects
            .select_related('vehiculo', 'conductor')
            .prefetch_related('paradas', 'peajesruta__peaje')
            .get(id=ruta_id, conductor=request.user)
        )
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    return Response(_serializar_ruta(ruta, detallado=True))


# ─────────────────────────────────────────
# POST /api/conductor/rutas/:id/iniciar/
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_iniciar_ruta(request, ruta_id):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    try:
        ruta = Ruta.objects.select_related('vehiculo', 'conductor').get(id=ruta_id, conductor=request.user)
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    if ruta.estado != 'pendiente':
        return Response({'error': f'La ruta está en estado "{ruta.estado}", no se puede iniciar.'}, status=400)

    km_inicio = request.data.get('km_inicio')
    ruta.estado       = 'activo'
    ruta.fecha_inicio = timezone.now()
    if km_inicio is not None:
        ruta.km_inicio = int(km_inicio)
        # Actualizar km_actuales del vehículo también
        if ruta.vehiculo:
            ruta.vehiculo.km_actuales = int(km_inicio)
            ruta.vehiculo.save(update_fields=['km_actuales'])
    ruta.save()

    registrar_log('ACTIVIDAD', 'ruta_iniciada', request, detalle={
        'ruta_id': ruta.id, 'ruta_nombre': ruta.nombre, 'km_inicio': ruta.km_inicio
    })

    return Response({'ok': True, 'ruta': _serializar_ruta(ruta)})


# ─────────────────────────────────────────
# POST /api/conductor/rutas/:id/finalizar/
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_finalizar_ruta(request, ruta_id):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    try:
        ruta = Ruta.objects.select_related('vehiculo', 'conductor').get(id=ruta_id, conductor=request.user)
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    if ruta.estado != 'activo':
        return Response({'error': f'La ruta está en estado "{ruta.estado}", no se puede finalizar.'}, status=400)

    km_fin                 = request.data.get('km_fin')
    costo_combustible_real = request.data.get('costo_combustible_real')
    costo_peajes_real      = request.data.get('costo_peajes_real')
    notas                  = request.data.get('notas', '')

    ruta.estado    = 'finalizado'
    ruta.fecha_fin = timezone.now()

    if km_fin is not None:
        ruta.km_fin = int(km_fin)
        if ruta.vehiculo:
            ruta.vehiculo.km_actuales = int(km_fin)
            ruta.vehiculo.save(update_fields=['km_actuales'])

    if costo_combustible_real is not None:
        ruta.costo_combustible_real = int(costo_combustible_real)
    if costo_peajes_real is not None:
        ruta.costo_peajes_real = int(costo_peajes_real)
        ruta.costo_total_real  = (ruta.costo_combustible_real or 0) + int(costo_peajes_real)
    if notas:
        ruta.notas = notas
    ruta.save()

    registrar_log('ACTIVIDAD', 'ruta_finalizada', request, detalle={
        'ruta_id': ruta.id, 'ruta_nombre': ruta.nombre,
        'km_fin': ruta.km_fin, 'costo_total_real': ruta.costo_total_real,
    })

    return Response({'ok': True, 'ruta': _serializar_ruta(ruta)})
