"""
views_conductor.py — Endpoints exclusivos para la app móvil de conductores.

Todos los endpoints verifican que el usuario autenticado tenga rol=CONDUCTOR.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Ruta, Rol, SolicitudConductor, Asignacion, Mantencion, GastoOperativo
from .audit import registrar_log
from .notificaciones import notificar_admins_empresa
from .firebase_push import enviar_push


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
    # Notificar a los admins de la empresa
    _empresa_ri = request.user.empresa
    if _empresa_ri:
        _nombre_c = request.user.nombre or request.user.email
        notificar_admins_empresa(_empresa_ri, 'actividad',
                                 f"Ruta iniciada por {_nombre_c}",
                                 f"{_nombre_c} inició la ruta '{ruta.nombre}'.",
                                 url_accion='/empresa/rutas')

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
    # Notificar a los admins de la empresa
    _empresa_rf = request.user.empresa
    if _empresa_rf:
        _nombre_cf = request.user.nombre or request.user.email
        _km_txt    = f" — {ruta.km_reales} km recorridos" if ruta.km_reales else ""
        notificar_admins_empresa(_empresa_rf, 'actividad',
                                 f"Ruta finalizada por {_nombre_cf}",
                                 f"{_nombre_cf} finalizó la ruta '{ruta.nombre}'{_km_txt}.",
                                 url_accion='/empresa/rutas')

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
# Helpers de mantenciones
# ─────────────────────────────────────────

def _serializar_mantencion(m, request=None):
    """Serializa una Mantencion al dict que consume la app móvil."""
    from django.utils import timezone
    hoy = timezone.now().date()

    dias_restantes = None
    if m.fecha_programada:
        dias_restantes = (m.fecha_programada - hoy).days

    # URL absoluta de la foto (si existe)
    foto_url = None
    if m.foto_comprobante:
        if request:
            foto_url = request.build_absolute_uri(m.foto_comprobante.url)
        else:
            foto_url = m.foto_comprobante.url

    return {
        'id':                    m.id,
        'tipo':                  m.tipo_mantencion,
        'descripcion':           m.descripcion,
        'estado':                m.estado,
        'fecha_programada':      m.fecha_programada.isoformat() if m.fecha_programada and not isinstance(m.fecha_programada, str) else (m.fecha_programada or None),
        'fecha_realizada':       m.fecha_realizada.isoformat()  if m.fecha_realizada  and not isinstance(m.fecha_realizada,  str) else (m.fecha_realizada  or None),
        'taller':                m.taller_proveedor,
        'presupuesto':           float(m.presupuesto) if m.presupuesto else None,
        'costo_real':            float(m.costo)       if m.costo       else None,
        'dias_restantes':        dias_restantes,
        'urgente':               (dias_restantes is not None and dias_restantes <= 3 and m.estado != 'realizada'),
        'foto_comprobante_url':  foto_url,
        'confirmado_conductor':  m.confirmado_conductor,
        'fecha_confirmacion':    m.fecha_confirmacion.isoformat() if m.fecha_confirmacion else None,
    }


# ─────────────────────────────────────────
# GET /api/conductor/mantenciones/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_mantenciones(request):
    """
    Devuelve las mantenciones del vehículo asignado al conductor:
      - pendiente / en_proceso: mantenciones activas
      - realizada sin confirmar: el conductor todavía debe dar su conformidad
    Incluye también si el vehículo está bloqueado por mantención activa.
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()

    if not asignacion:
        return Response({
            'mantenciones':           [],
            'vehiculo_en_mantencion': False,
            'vehiculo':               None,
        })

    vehiculo = asignacion.vehiculo

    # Solo mantenciones activas que el conductor puede ver / actuar
    qs = Mantencion.objects.filter(
        vehiculo=vehiculo,
        estado__in=['pendiente', 'en_proceso'],
    ).order_by('fecha_programada', '-id')

    mantenciones = [_serializar_mantencion(m, request) for m in qs]

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
# GET /api/conductor/mantenciones/historial/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_historial_mantenciones(request):
    """
    Devuelve las mantenciones realizadas del vehículo asignado al conductor,
    ordenadas de más reciente a más antigua.
    Query params:
      page      — número de página (default 1)
      page_size — registros por página (default 20, máx 100)
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()

    if not asignacion:
        return Response({'historial': [], 'total': 0, 'vehiculo': None})

    vehiculo = asignacion.vehiculo

    try:
        page      = max(1, int(request.query_params.get('page', 1)))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
    except (ValueError, TypeError):
        page, page_size = 1, 20

    qs = Mantencion.objects.filter(
        vehiculo=vehiculo,
        estado='realizada',
    ).order_by('-fecha_realizada', '-id')

    total  = qs.count()
    offset = (page - 1) * page_size
    items  = [_serializar_mantencion(m, request) for m in qs[offset:offset + page_size]]

    return Response({
        'historial': items,
        'total':     total,
        'page':      page,
        'page_size': page_size,
        'has_more':  offset + page_size < total,
        'vehiculo': {
            'id':      vehiculo.id,
            'patente': vehiculo.patente,
            'marca':   vehiculo.marca,
            'modelo':  vehiculo.modelo,
        },
    })


# ─────────────────────────────────────────
# GET /api/conductor/mantenciones/:id/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_mantencion_detalle(request, mantencion_id):
    """
    Detalle completo de una mantención del vehículo asignado al conductor.
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()

    if not asignacion:
        return Response({'error': 'Sin vehículo asignado.'}, status=404)

    try:
        mantencion = Mantencion.objects.get(pk=mantencion_id, vehiculo=asignacion.vehiculo)
    except Mantencion.DoesNotExist:
        return Response({'error': 'Mantención no encontrada.'}, status=404)

    return Response(_serializar_mantencion(mantencion, request))


# ─────────────────────────────────────────
# POST /api/conductor/mantenciones/:id/iniciar/
# ─────────────────────────────────────────

def _get_mantencion_conductor(request, mantencion_id):
    """
    Helper: verifica rol CONDUCTOR, asignación activa y que la mantención
    pertenece al vehículo asignado. Devuelve (mantencion, asignacion) o lanza Response.
    """
    if request.user.rol != Rol.CONDUCTOR:
        return None, None, Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()

    if not asignacion:
        return None, None, Response({'error': 'Sin vehículo asignado.'}, status=404)

    try:
        mantencion = Mantencion.objects.select_related('vehiculo__flota__empresa').get(
            pk=mantencion_id, vehiculo=asignacion.vehiculo
        )
    except Mantencion.DoesNotExist:
        return None, None, Response({'error': 'Mantención no encontrada.'}, status=404)

    return mantencion, asignacion, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_iniciar_mantencion(request, mantencion_id):
    """
    El conductor inicia una mantención: pendiente → en_proceso.
    Bloquea el vehículo (en_mantencion=True).
    """
    mantencion, asignacion, err = _get_mantencion_conductor(request, mantencion_id)
    if err:
        return err

    if mantencion.estado != 'pendiente':
        return Response({'error': 'Solo puedes iniciar mantenciones en estado pendiente.'}, status=400)

    mantencion.estado = 'en_proceso'
    mantencion.save(update_fields=['estado'])

    vehiculo = asignacion.vehiculo
    vehiculo.en_mantencion = True
    vehiculo.save(update_fields=['en_mantencion'])

    registrar_log('ACTIVIDAD', 'mantencion_iniciada_conductor', request, detalle={
        'mantencion_id': mantencion.id,
        'tipo':          mantencion.tipo_mantencion,
        'vehiculo':      vehiculo.patente,
    })
    # Notificar a los admins de la empresa
    _empresa_mi = vehiculo.flota.empresa if vehiculo.flota else None
    if _empresa_mi:
        _nombre_mi = request.user.nombre or request.user.email
        notificar_admins_empresa(_empresa_mi, 'actividad',
                                 f"Mantención iniciada por {_nombre_mi}",
                                 f"{_nombre_mi} inició '{mantencion.tipo_mantencion}' del vehículo {vehiculo.patente}.",
                                 url_accion='/empresa/mantenciones')

    return Response({'ok': True, 'mantencion': _serializar_mantencion(mantencion, request)})


# ─────────────────────────────────────────
# POST /api/conductor/mantenciones/:id/completar/
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_completar_mantencion(request, mantencion_id):
    """
    El conductor marca la mantención como realizada.
    Body (multipart/form-data):
      costo_final       (Decimal, obligatorio)
      foto_comprobante  (File,    opcional)
      fecha_realizada   (Date,    default=hoy)
      notas             (str,     opcional)

    Efectos:
      - Mantencion: estado→realizada, costo, foto, fecha_realizada, confirmado_conductor=True
      - Vehiculo: en_mantencion=False
      - Crea GastoOperativo de categoría 'mantencion' automáticamente
    """
    mantencion, asignacion, err = _get_mantencion_conductor(request, mantencion_id)
    if err:
        return err

    if mantencion.estado not in ('pendiente', 'en_proceso'):
        return Response({'error': 'Solo puedes completar mantenciones pendientes o en proceso.'}, status=400)

    # Validar costo
    costo_raw = request.data.get('costo_final') or request.data.get('costo', '')
    try:
        costo = float(str(costo_raw).strip())
        if costo <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return Response({'error': 'El costo final debe ser mayor a 0.'}, status=400)

    # Fecha realizada — convertir siempre a objeto date para que
    # _serializar_mantencion pueda llamar .isoformat() sin errores
    from datetime import date as _date
    _fecha_str = request.data.get('fecha_realizada') or timezone.now().date().isoformat()
    if str(_fecha_str) > timezone.now().date().isoformat():
        return Response({'error': 'La fecha realizada no puede ser una fecha futura.'}, status=400)
    try:
        fecha_realizada = _date.fromisoformat(str(_fecha_str))
    except (ValueError, TypeError):
        fecha_realizada = timezone.now().date()

    notas = request.data.get('notas', '').strip()
    foto  = request.FILES.get('foto_comprobante')

    # ── Actualizar la mantención ──────────────────────────────────────────────
    mantencion.estado               = 'realizada'
    mantencion.costo                = costo
    mantencion.fecha_realizada      = fecha_realizada
    mantencion.confirmado_conductor = True
    mantencion.fecha_confirmacion   = timezone.now()
    if foto:
        mantencion.foto_comprobante = foto
    update_fields = ['estado', 'costo', 'fecha_realizada', 'confirmado_conductor', 'fecha_confirmacion']
    if foto:
        update_fields.append('foto_comprobante')
    mantencion.save(update_fields=update_fields)

    # ── Desbloquear el vehículo ───────────────────────────────────────────────
    vehiculo = asignacion.vehiculo
    vehiculo.en_mantencion = False
    vehiculo.save(update_fields=['en_mantencion'])

    # ── Crear GastoOperativo automáticamente ─────────────────────────────────
    empresa = vehiculo.flota.empresa if vehiculo.flota else None
    gasto   = None
    if empresa:
        gasto = GastoOperativo.objects.create(
            empresa       = empresa,
            vehiculo      = vehiculo,
            conductor     = request.user,
            categoria     = 'mantencion',
            descripcion   = f'Mantención: {mantencion.tipo_mantencion} — {vehiculo.patente}',
            monto         = int(costo),
            fecha         = fecha_realizada,
            comprobante   = mantencion.foto_comprobante if mantencion.foto_comprobante else None,
            registrado_por= request.user,
        )

    registrar_log('ACTIVIDAD', 'mantencion_completada_conductor', request, detalle={
        'mantencion_id': mantencion.id,
        'tipo':          mantencion.tipo_mantencion,
        'vehiculo':      vehiculo.patente,
        'costo':         costo,
        'gasto_id':      gasto.id if gasto else None,
    })
    # Notificar a los admins de la empresa
    if empresa:
        _nombre_mc = request.user.nombre or request.user.email
        notificar_admins_empresa(empresa, 'actividad',
                                 f"Mantención completada por {_nombre_mc}",
                                 f"{_nombre_mc} completó '{mantencion.tipo_mantencion}' del vehículo {vehiculo.patente}. Costo: ${int(costo):,}.",
                                 url_accion='/empresa/mantenciones')

    return Response({
        'ok':         True,
        'mantencion': _serializar_mantencion(mantencion, request),
        'gasto_id':   gasto.id if gasto else None,
    }, status=200)


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
