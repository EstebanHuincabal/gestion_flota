"""
views_conductor.py — Endpoints exclusivos para la app móvil de conductores.

Todos los endpoints verifican que el usuario autenticado tenga rol=CONDUCTOR.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Ruta, Rol, SolicitudConductor, Asignacion, Mantencion
from .audit import registrar_log
from .notificaciones import notificar_admins_empresa


# ─────────────────────────────────────────
# Helpers de plan / permisos
# ─────────────────────────────────────────

# Todos los tipos posibles de solicitud
TODOS_LOS_TIPOS = ['mantencion', 'combustible', 'incidencia', 'documento']


def _tipos_permitidos_por_plan(empresa) -> list[str]:
    """
    Devuelve la lista de tipos de solicitud habilitados según el plan de la empresa.

    - Si la empresa no tiene plan asignado → se permiten todos los tipos
      (comportamiento conservador para no romper empresas sin plan).
    - Si el plan no tiene ningún permiso de solicitudes → se bloquean todos
      (significa que el admin quitó explícitamente los permisos).
    """
    if not empresa or not empresa.plan_id:
        return TODOS_LOS_TIPOS

    codigos_plan = set(
        empresa.plan.permisos.values_list('codigo', flat=True)
    )

    permitidos = [
        tipo for tipo in TODOS_LOS_TIPOS
        if f'solicitudes.{tipo}' in codigos_plan
    ]

    # Si el plan no tiene NINGÚN permiso de solicitudes, devolver lista vacía
    return permitidos


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
            'en_mantencion':   ruta.vehiculo.en_mantencion,
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


# ─────────────────────────────────────────
# Serializer auxiliar de solicitudes
# ─────────────────────────────────────────

def _serializar_solicitud(s):
    return {
        'id':          s.id,
        'tipo':        s.tipo,
        'titulo':      s.titulo,
        'descripcion': s.descripcion,
        'estado':      s.estado,
        'prioridad':   s.prioridad,
        'foto_url':    s.foto.url if s.foto else None,
        'respuesta':   s.respuesta,
        'created_at':  s.created_at.isoformat(),
        'updated_at':  s.updated_at.isoformat(),
    }


# ─────────────────────────────────────────
# GET + POST /api/conductor/solicitudes/
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conductor_solicitudes(request):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores pueden acceder a este endpoint.'}, status=403)

    empresa          = request.user.empresa
    tipos_permitidos = _tipos_permitidos_por_plan(empresa)

    # ── GET ──────────────────────────────────────────────────────────────────
    if request.method == 'GET':
        qs = (
            SolicitudConductor.objects
            .filter(conductor=request.user)
            .order_by('-created_at')
        )
        return Response({
            'solicitudes':     [_serializar_solicitud(s) for s in qs],
            'tipos_permitidos': tipos_permitidos,
        })

    # ── POST ─────────────────────────────────────────────────────────────────
    tipo        = request.data.get('tipo', '').strip()
    titulo      = request.data.get('titulo', '').strip()
    descripcion = request.data.get('descripcion', '').strip()
    prioridad   = request.data.get('prioridad', 'media').strip()
    foto        = request.FILES.get('foto')

    # Validaciones básicas
    prioridades_validas = ['baja', 'media', 'alta']

    errores = {}
    if tipo not in TODOS_LOS_TIPOS:
        errores['tipo'] = f'Tipo inválido. Opciones: {", ".join(TODOS_LOS_TIPOS)}'
    elif tipo not in tipos_permitidos:
        # El tipo es válido pero el plan de la empresa no lo incluye
        nombre_plan = empresa.plan.get_nombre_display() if empresa and empresa.plan else 'actual'
        return Response(
            {
                'error': (
                    f'Tu plan "{nombre_plan}" no incluye solicitudes de tipo '
                    f'"{tipo}". Contacta al administrador de tu empresa para más información.'
                ),
                'codigo': 'plan_sin_permiso',
                'tipo': tipo,
            },
            status=403,
        )
    if not titulo or len(titulo) < 5:
        errores['titulo'] = 'El título debe tener al menos 5 caracteres.'
    if tipo != 'documento' and len(descripcion) < 10:
        errores['descripcion'] = 'La descripción debe tener al menos 10 caracteres.'
    if prioridad not in prioridades_validas:
        prioridad = 'media'

    if errores:
        return Response(errores, status=400)

    # Obtener empresa y vehículo activo del conductor
    empresa  = request.user.empresa
    vehiculo = None
    asignacion = Asignacion.objects.filter(conductor=request.user, activo=True).select_related('vehiculo').first()
    if asignacion:
        vehiculo = asignacion.vehiculo

    solicitud = SolicitudConductor.objects.create(
        conductor=request.user,
        empresa=empresa,
        vehiculo=vehiculo,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        prioridad=prioridad,
        foto=foto,
    )

    registrar_log('ACTIVIDAD', 'solicitud_creada', request, detalle={
        'solicitud_id': solicitud.id, 'tipo': tipo, 'titulo': titulo,
    })

    # Notificar a los admins de la empresa
    if empresa:
        nombre_conductor = request.user.nombre or request.user.email
        notificar_admins_empresa(
            empresa=empresa,
            tipo='actividad',
            titulo=f'Nueva solicitud de {nombre_conductor}: {titulo}',
            mensaje=descripcion or titulo,
            url_accion='/empresa/solicitudes',
            extra={'solicitud_id': solicitud.id, 'tipo': tipo},
        )

        # Evento WebSocket en tiempo real para el panel web
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'solicitudes_{empresa.id}',
                    {
                        'type':      'nueva_solicitud',
                        'solicitud': {
                            'id':        solicitud.id,
                            'tipo':      solicitud.tipo,
                            'titulo':    solicitud.titulo,
                            'conductor': nombre_conductor,
                        },
                    }
                )
        except Exception:
            pass  # WS no disponible — no interrumpir el flujo

    return Response({'ok': True, 'solicitud': _serializar_solicitud(solicitud)}, status=201)


# ─────────────────────────────────────────
# GET /api/conductor/mantenciones/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_mantenciones(request):
    """
    Devuelve las mantenciones del vehículo actualmente asignado al conductor.
    Solo estados pendiente y en_proceso (las que le incumben directamente).
    Incluye también si el vehículo está bloqueado por mantención activa.
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()

    if not asignacion:
        return Response({
            'mantenciones':        [],
            'vehiculo_en_mantencion': False,
            'vehiculo':            None,
        })

    vehiculo = asignacion.vehiculo

    qs = Mantencion.objects.filter(
        vehiculo=vehiculo,
        estado__in=['pendiente', 'en_proceso'],
    ).order_by('fecha_programada', '-id')

    from django.utils import timezone
    hoy = timezone.now().date()

    def _dias(fecha_programada):
        if not fecha_programada:
            return None
        delta = (fecha_programada - hoy).days
        return delta

    mantenciones = [
        {
            'id':               m.id,
            'tipo':             m.tipo_mantencion,
            'descripcion':      m.descripcion,
            'estado':           m.estado,
            'fecha_programada': m.fecha_programada.isoformat() if m.fecha_programada else None,
            'taller':           m.taller_proveedor,
            'presupuesto':      float(m.presupuesto) if m.presupuesto else None,
            'dias_restantes':   _dias(m.fecha_programada),
            'urgente':          (_dias(m.fecha_programada) is not None and _dias(m.fecha_programada) <= 3),
        }
        for m in qs
    ]

    return Response({
        'mantenciones':           mantenciones,
        'vehiculo_en_mantencion': vehiculo.en_mantencion,
        'vehiculo': {
            'id':      vehiculo.id,
            'patente': vehiculo.patente,
            'marca':   vehiculo.marca,
            'modelo':  vehiculo.modelo,
        },
    })


# ─────────────────────────────────────────
# POST /api/conductor/push-token/
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_push_token(request):
    """
    Registra o actualiza el token FCM del dispositivo del conductor.
    La app llama a este endpoint al iniciar sesión y cuando FCM renueva el token.
    Body: { "token": "<fcm_token>" }
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    token = request.data.get('token', '').strip()
    if not token:
        return Response({'error': 'Token requerido.'}, status=400)

    prefs = request.user.notif_prefs or {}
    prefs['push_token'] = token
    request.user.notif_prefs = prefs
    request.user.save(update_fields=['notif_prefs'])

    return Response({'ok': True})
