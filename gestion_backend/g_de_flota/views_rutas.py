from datetime import date, date as _date, datetime, timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import registrar_log
from .notificaciones import notificar, notificar_admins_empresa
from .firebase_push import enviar_push
from .models import (
    AlertaMantencion, Documento, Empresa, EventoRuta, GastoOperativo, Mantencion, Parada,
    Rol, Ruta, TipoNotificacion, Usuario, Vehiculo,
)
from .ruta_calculator import calcular_ruta_osrm, calcular_ruta_fallback


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _iso(val):
    """Convierte date/datetime a isoformat, o devuelve el string tal cual."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


def _tiene_permiso(user, codigo: str) -> bool:
    if user.rol == Rol.SUPERADMIN:
        return True
    if user.rol == Rol.CONDUCTOR:
        return False
    plan = getattr(user.empresa, 'plan', None) if user.empresa_id else None
    if not plan:
        return False
    return plan.permisos.filter(codigo=codigo).exists()


def _get_empresa(request):
    if request.user.rol == Rol.SUPERADMIN:
        eid = request.query_params.get('empresa_id') or request.data.get('empresa_id')
        if eid:
            try:
                return Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                return None
        return None
    return request.user.empresa


def _ruta_dict(ruta, detalle=False):
    paradas_qs = list(ruta.paradas.order_by('orden'))
    origen_nombre  = next((p.nombre for p in paradas_qs if p.tipo == 'origen'),  '')
    destino_nombre = next((p.nombre for p in paradas_qs if p.tipo == 'destino'), '')

    d = {
        'id':               ruta.id,
        'nombre':           ruta.nombre,
        'tipo':             ruta.tipo,
        'estado':           ruta.estado,
        'descripcion':      ruta.descripcion,
        'conductor_id':     ruta.conductor_id,
        'conductor':        ruta.conductor.nombre if ruta.conductor else None,
        'vehiculo_id':      ruta.vehiculo_id,
        'vehiculo':         str(ruta.vehiculo) if ruta.vehiculo else None,
        'fecha_programada': _iso(ruta.fecha_programada),
        'hora_programada':  ruta.hora_programada.strftime('%H:%M') if ruta.hora_programada else None,
        'fecha_inicio':     _iso(ruta.fecha_inicio),
        'fecha_fin':        _iso(ruta.fecha_fin),
        'km_inicio':        ruta.km_inicio,
        'km_fin':           ruta.km_fin,
        'km_reales':        ruta.km_reales,
        'distancia_km':     float(ruta.distancia_km) if ruta.distancia_km else None,
        'duracion_min':     ruta.duracion_min,
        'origen':           origen_nombre,
        'destino':          destino_nombre,
        'notas':            ruta.notas,
        'created_at':       _iso(ruta.created_at),
    }

    if detalle:
        d['polyline'] = ruta.polyline or []
        d['paradas'] = [
            {
                'id':            p.id,
                'tipo':          p.tipo,
                'orden':         p.orden,
                'nombre':        p.nombre,
                'direccion':     p.direccion,
                'latitud':       p.latitud,
                'longitud':      p.longitud,
                'notas':         p.notas,
                'hora_estimada': _iso(p.hora_estimada),
            }
            for p in paradas_qs
        ]

    return d


def _evento_dict(evento):
    return {
        'id':         evento.id,
        'tipo':       evento.tipo,
        'texto':      evento.texto,
        'autor':      evento.autor.nombre if evento.autor else None,
        'autor_id':   evento.autor_id,
        'created_at': _iso(evento.created_at),
    }


def _crear_evento_auto(ruta, texto):
    """Crea un EventoRuta de tipo automático."""
    EventoRuta.objects.create(ruta=ruta, tipo='auto', texto=texto)


def _procesar_paradas_y_calcular(ruta, paradas_data):
    """Crea las paradas y llama OSRM (solo distancia/duración/polyline)."""
    Parada.objects.filter(ruta=ruta).delete()
    for p in paradas_data:
        Parada.objects.create(
            ruta=ruta,
            tipo=p.get('tipo', 'parada'),
            orden=p.get('orden', 0),
            nombre=p.get('nombre', ''),
            direccion=p.get('direccion', ''),
            latitud=p.get('lat') or p.get('latitud'),
            longitud=p.get('lng') or p.get('longitud'),
            notas=p.get('notas', ''),
        )

    puntos = [
        {'lat': p.get('lat') or p.get('latitud'), 'lng': p.get('lng') or p.get('longitud')}
        for p in sorted(paradas_data, key=lambda x: x.get('orden', 0))
        if (p.get('lat') or p.get('latitud')) and (p.get('lng') or p.get('longitud'))
    ]

    aviso_osrm = None
    if len(puntos) >= 2:
        osrm = calcular_ruta_osrm(puntos)
        es_fallback = False
        if not osrm:
            osrm = calcular_ruta_fallback(puntos)
            es_fallback = True

        if osrm:
            ruta.distancia_km = osrm['distancia_km']
            ruta.duracion_min = osrm['duracion_min']
            ruta.polyline     = osrm['polyline']
            if es_fallback:
                aviso_osrm = (
                    'OSRM no disponible. La distancia es una estimación en línea recta '
                    '(×1.3 de sinuosidad).'
                )

    ruta.save()
    return aviso_osrm


# ─────────────────────────────────────────
# Validaciones de negocio
# ─────────────────────────────────────────

MARGEN_DIAS_RUTA = 1   # días de buffer alrededor de la fecha programada


def _validar_conflictos(fecha_str, conductor_id, vehiculo_id, excluir_ruta_id=None):
    """
    Valida:
      • Fecha no anterior a hoy
      • Conductor/vehículo sin ruta ACTIVA en curso (independiente de fecha_programada)
      • Conductor/vehículo sin ruta PENDIENTE dentro del margen de ±MARGEN_DIAS_RUTA días

    Retorna dict de errores (vacío = sin conflictos).
    """
    from datetime import timedelta

    errores = {}

    if not fecha_str:
        return errores

    try:
        fecha = _date.fromisoformat(str(fecha_str))
    except ValueError:
        return {'fecha_programada': 'Fecha inválida.'}

    if fecha < _date.today():
        errores['fecha_programada'] = 'La fecha no puede ser anterior a hoy.'
        return errores

    base_qs = Ruta.objects.all()
    if excluir_ruta_id:
        base_qs = base_qs.exclude(pk=excluir_ruta_id)

    # ── 1. Rutas activas (en curso) — bloquean siempre ────────────────────
    qs_activa = base_qs.filter(estado='activo')

    # ── 2. Rutas pendientes dentro del margen de días ─────────────────────
    desde = fecha - timedelta(days=MARGEN_DIAS_RUTA)
    hasta = fecha + timedelta(days=MARGEN_DIAS_RUTA)
    qs_pendiente = base_qs.filter(
        estado='pendiente',
        fecha_programada__range=(desde, hasta),
    )

    def _fmt_fecha(r):
        return f" ({r.fecha_programada})" if r.fecha_programada else ""

    if conductor_id:
        activa = qs_activa.filter(conductor_id=conductor_id).first()
        if activa:
            errores['conductor_id'] = (
                f'El conductor tiene la ruta "{activa.nombre}" actualmente en curso.'
            )
        elif not errores.get('conductor_id'):
            pendiente = qs_pendiente.filter(conductor_id=conductor_id).first()
            if pendiente:
                errores['conductor_id'] = (
                    f'El conductor ya tiene la ruta "{pendiente.nombre}" '
                    f'programada{_fmt_fecha(pendiente)} '
                    f'(margen de {MARGEN_DIAS_RUTA} día{"s" if MARGEN_DIAS_RUTA != 1 else ""}).'
                )

    if vehiculo_id:
        activa = qs_activa.filter(vehiculo_id=vehiculo_id).first()
        if activa:
            errores['vehiculo_id'] = (
                f'El vehículo está asignado a la ruta "{activa.nombre}" actualmente en curso.'
            )
        elif not errores.get('vehiculo_id'):
            pendiente = qs_pendiente.filter(vehiculo_id=vehiculo_id).first()
            if pendiente:
                errores['vehiculo_id'] = (
                    f'El vehículo ya está asignado a la ruta "{pendiente.nombre}" '
                    f'programada{_fmt_fecha(pendiente)} '
                    f'(margen de {MARGEN_DIAS_RUTA} día{"s" if MARGEN_DIAS_RUTA != 1 else ""}).'
                )

    return errores


def _validar_estado_operacional(vehiculo_id, conductor_id, empresa, fecha_str=None, excluir_ruta_id=None):
    """
    Validaciones ampliadas al crear/editar una ruta:

    Errores duros (impiden crear):
      • Vehículo inactivo o en mantención activa
      • Conductor inactivo o bloqueado
      • Mantención predictiva vencida sin atender en el vehículo
      + Los conflictos de fecha ya cubiertos por _validar_conflictos()

    Advertencias (permiten crear si el usuario confirma):
      • Documentos del vehículo vencidos (SOAP, revisión técnica, permiso de circulación)
      • Documentos del vehículo por vencer (≤ 15 días)
      • Licencia del conductor vencida
      • Licencia del conductor por vencer (≤ 30 días)
      • Mantención correctiva pendiente en el vehículo
      • Mantención predictiva próxima (≤ 7 días)

    Retorna:
      { 'errores': [...], 'advertencias': [...] }
      Cada ítem: { 'codigo': str, 'mensaje': str }
    """
    errores      = []
    advertencias = []
    hoy          = date.today()

    # ── Vehículo ──────────────────────────────────────────────────────────
    if vehiculo_id:
        try:
            vehiculo = Vehiculo.objects.get(pk=vehiculo_id, flota__empresa=empresa)
        except Vehiculo.DoesNotExist:
            return {'errores': [{'codigo': 'vehiculo_no_encontrado', 'mensaje': 'Vehículo no encontrado.'}], 'advertencias': []}

        if not vehiculo.activo:
            errores.append({'codigo': 'vehiculo_inactivo',
                            'mensaje': 'El vehículo está inactivo en la flota.'})

        if vehiculo.en_mantencion:
            errores.append({'codigo': 'vehiculo_en_mantencion',
                            'mensaje': 'El vehículo está actualmente en mantención y no puede ser asignado.'})

        # Mantenciones predictivas vencidas (advertencia — puede programar igual)
        mant_vencidas = (AlertaMantencion.objects
                         .filter(mantencion_programada__vehiculo=vehiculo,
                                 nivel='vencida', atendida=False)
                         .select_related('mantencion_programada__regla'))
        for alerta in mant_vencidas:
            tipo_m = alerta.mantencion_programada.regla.tipo
            advertencias.append({'codigo': 'mantencion_predictiva_vencida',
                                 'mensaje': f'Mantención predictiva vencida sin atender: {tipo_m}.'})

        # Documentos del vehículo (advertencias)
        DOCS_VEHICULO = [
            ('seguro_soap',          'SOAP'),
            ('revision_tecnica',     'Revisión técnica'),
            ('permiso_circulacion',  'Permiso de circulación'),
        ]
        for tipo_doc, label in DOCS_VEHICULO:
            doc = (Documento.objects
                   .filter(vehiculo=vehiculo, tipo=tipo_doc, fecha_vencimiento__isnull=False)
                   .order_by('-fecha_vencimiento').first())
            if doc:
                dias = (doc.fecha_vencimiento - hoy).days
                fecha_fmt = doc.fecha_vencimiento.strftime('%d/%m/%Y')
                if dias < 0:
                    advertencias.append({
                        'codigo':  f'{tipo_doc}_vencido',
                        'mensaje': f'El {label} del vehículo venció el {fecha_fmt} (hace {abs(dias)} día{"s" if abs(dias) != 1 else ""}).',
                    })
                elif dias <= 15:
                    advertencias.append({
                        'codigo':  f'{tipo_doc}_por_vencer',
                        'mensaje': f'El {label} del vehículo vence el {fecha_fmt} (en {dias} día{"s" if dias != 1 else ""}).',
                    })

        # Mantención correctiva pendiente (advertencia)
        mant_c = Mantencion.objects.filter(vehiculo=vehiculo, estado='pendiente').first()
        if mant_c:
            advertencias.append({
                'codigo':  'mantencion_correctiva_pendiente',
                'mensaje': f'El vehículo tiene una mantención correctiva pendiente: "{mant_c.tipo_mantencion}".',
            })

        # Mantenciones predictivas próximas ≤ 7 días (advertencia)
        mant_proximas = (AlertaMantencion.objects
                         .filter(mantencion_programada__vehiculo=vehiculo,
                                 nivel='por_vencer', atendida=False,
                                 dias_restantes__lte=7)
                         .select_related('mantencion_programada__regla'))
        for alerta in mant_proximas:
            tipo_m = alerta.mantencion_programada.regla.tipo
            d = alerta.dias_restantes
            advertencias.append({
                'codigo':  'mantencion_predictiva_proxima',
                'mensaje': f'Mantención predictiva próxima en {d} día{"s" if d != 1 else ""}: {tipo_m}.',
            })

    # ── Conductor ─────────────────────────────────────────────────────────
    if conductor_id:
        try:
            conductor = Usuario.objects.get(pk=conductor_id, empresa=empresa, rol=Rol.CONDUCTOR)
        except Usuario.DoesNotExist:
            return {'errores': [{'codigo': 'conductor_no_encontrado', 'mensaje': 'Conductor no encontrado.'}], 'advertencias': advertencias}

        if not conductor.is_active:
            errores.append({'codigo': 'conductor_inactivo',
                            'mensaje': 'El conductor no está activo en el sistema.'})

        if conductor.is_blocked:
            errores.append({'codigo': 'conductor_bloqueado',
                            'mensaje': 'El conductor tiene la cuenta bloqueada.'})

        # Licencia de conducir (advertencia)
        licencia = (Documento.objects
                    .filter(conductor=conductor, tipo='licencia', fecha_vencimiento__isnull=False)
                    .order_by('-fecha_vencimiento').first())
        if licencia:
            dias = (licencia.fecha_vencimiento - hoy).days
            fecha_fmt = licencia.fecha_vencimiento.strftime('%d/%m/%Y')
            if dias < 0:
                advertencias.append({
                    'codigo':  'licencia_vencida',
                    'mensaje': f'La licencia de conducir del conductor venció el {fecha_fmt} (hace {abs(dias)} día{"s" if abs(dias) != 1 else ""}).',
                })
            elif dias <= 30:
                advertencias.append({
                    'codigo':  'licencia_por_vencer',
                    'mensaje': f'La licencia del conductor vence el {fecha_fmt} (en {dias} día{"s" if dias != 1 else ""}).',
                })

    return {'errores': errores, 'advertencias': advertencias}


MINUTOS_ANTICIPACION = 30   # minutos antes de hora_programada en que se permite iniciar


def _validar_anticipacion_inicio(ruta):
    """
    Impide iniciar la ruta más de MINUTOS_ANTICIPACION antes de la hora programada.
    Retorna un mensaje de error (str) si no se puede iniciar, o None si está permitido.
    """
    if not ruta.hora_programada or not ruta.fecha_programada:
        return None   # sin hora definida → no se restringe

    dt_programado = datetime.combine(ruta.fecha_programada, ruta.hora_programada)
    limite        = dt_programado - timedelta(minutes=MINUTOS_ANTICIPACION)
    ahora         = datetime.now()

    if ahora < limite:
        restante      = dt_programado - ahora
        total_min     = int(restante.total_seconds() // 60)
        horas, minutos = divmod(total_min, 60)
        hora_fmt      = ruta.hora_programada.strftime('%H:%M')

        if horas > 0:
            tiempo_str = f'{horas}h {minutos}min'
        else:
            tiempo_str = f'{minutos} minuto{"s" if minutos != 1 else ""}'

        return (
            f'La ruta está programada para las {hora_fmt}. '
            f'Solo puede iniciarse con hasta {MINUTOS_ANTICIPACION} minutos de anticipación '
            f'(faltan {tiempo_str}).'
        )
    return None


# ─────────────────────────────────────────
# Vistas
# ─────────────────────────────────────────

class RutasListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _tiene_permiso(request.user, 'rutas.ver'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)

        qs = (Ruta.objects
              .filter(empresa=empresa)
              .select_related('conductor', 'vehiculo')
              .prefetch_related('paradas'))

        estado       = request.query_params.get('estado')
        tipo         = request.query_params.get('tipo')
        conductor_id = request.query_params.get('conductor_id')
        vehiculo_id  = request.query_params.get('vehiculo_id')
        fecha_desde  = request.query_params.get('fecha_desde')
        fecha_hasta  = request.query_params.get('fecha_hasta')

        if estado:       qs = qs.filter(estado=estado)
        if tipo:         qs = qs.filter(tipo=tipo)
        if conductor_id: qs = qs.filter(conductor_id=conductor_id)
        if vehiculo_id:  qs = qs.filter(vehiculo_id=vehiculo_id)
        if fecha_desde:  qs = qs.filter(fecha_programada__gte=fecha_desde)
        if fecha_hasta:  qs = qs.filter(fecha_programada__lte=fecha_hasta)

        qs = qs.order_by('-created_at')

        from django.db.models import Sum
        hoy   = date.today()
        todas = Ruta.objects.filter(empresa=empresa)
        mes   = todas.filter(fecha_programada__year=hoy.year, fecha_programada__month=hoy.month)

        resumen = {
            'total':              todas.count(),
            'activas':            todas.filter(estado='activo').count(),
            'pendientes':         todas.filter(estado='pendiente').count(),
            'finalizadas':        todas.filter(estado='finalizado').count(),
            'canceladas':         todas.filter(estado='cancelado').count(),
            'km_mes':             float(mes.aggregate(km=Sum('distancia_km'))['km'] or 0),
            'finalizadas_mes':    mes.filter(estado='finalizado').count(),
        }

        return Response({'rutas': [_ruta_dict(r) for r in qs], 'resumen': resumen})

    def post(self, request):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)

        data         = request.data
        paradas_data = data.get('paradas', [])
        tipos        = [p.get('tipo') for p in paradas_data]

        if 'origen' not in tipos or 'destino' not in tipos:
            return Response({'error': 'Se requiere al menos un origen y un destino.'}, status=400)

        errores = _validar_conflictos(
            data.get('fecha_programada'),
            data.get('conductor_id'),
            data.get('vehiculo_id'),
        )
        if errores:
            return Response(errores, status=400)

        # Validaciones de estado operacional (bloqueos duros)
        val_op = _validar_estado_operacional(
            data.get('vehiculo_id'),
            data.get('conductor_id'),
            empresa,
        )
        if val_op['errores']:
            return Response({'errores': val_op['errores']}, status=400)

        ruta = Ruta(
            empresa=empresa,
            tipo=data.get('tipo', 'carga'),
            nombre=data.get('nombre', '').strip(),
            descripcion=data.get('descripcion', ''),
            estado='pendiente',
            notas=data.get('notas', ''),
            fecha_programada=data.get('fecha_programada') or None,
            hora_programada=data.get('hora_programada') or None,
        )

        conductor_id = data.get('conductor_id')
        vehiculo_id  = data.get('vehiculo_id')
        if conductor_id:
            try:
                ruta.conductor = Usuario.objects.get(pk=conductor_id, empresa=empresa)
            except Usuario.DoesNotExist:
                pass
        if vehiculo_id:
            try:
                ruta.vehiculo = Vehiculo.objects.get(pk=vehiculo_id, flota__empresa=empresa)
            except Vehiculo.DoesNotExist:
                pass

        ruta.save()
        aviso = _procesar_paradas_y_calcular(ruta, paradas_data)

        # Evento automático
        _crear_evento_auto(ruta, 'Ruta creada.')

        registrar_log('ACTIVIDAD', 'ruta_creada', request,
                      detalle={'ruta_id': ruta.id, 'nombre': ruta.nombre})
        if ruta.conductor:
            _fecha_ruta = f" para el {ruta.fecha_programada}" if ruta.fecha_programada else ""
            notificar(ruta.conductor, TipoNotificacion.ACTIVIDAD,
                      "Nueva ruta asignada",
                      f"Se te asignó la ruta '{ruta.nombre}'{_fecha_ruta}.",
                      url_accion='/rutas')
            enviar_push(ruta.conductor,
                        titulo='Nueva ruta asignada 🚛',
                        cuerpo=f"{ruta.nombre}{_fecha_ruta}",
                        data={'tipo': 'ruta_asignada', 'ruta_id': str(ruta.id)})

            # ── Email al conductor ───────────────────────────────────────────
            try:
                from .email_service import email_ruta_asignada
                from django.conf import settings as _settings
                _origen  = ruta.paradas.filter(tipo='origen').first()
                _destino = ruta.paradas.filter(tipo='destino').first()
                email_ruta_asignada(
                    email=ruta.conductor.email,
                    nombre_conductor=ruta.conductor.nombre or ruta.conductor.email,
                    empresa_nombre=empresa.nombre,
                    nombre_ruta=ruta.nombre,
                    origen=_origen.nombre if _origen else '—',
                    destino=_destino.nombre if _destino else '—',
                    fecha=(
                        ruta.fecha_programada.strftime('%d/%m/%Y %H:%M')
                        if ruta.fecha_programada else '—'
                    ),
                    url_app=f"{_settings.FRONTEND_URL}/app",
                )
            except Exception:
                pass

        resp = _ruta_dict(ruta, detalle=True)
        if aviso:
            resp['aviso'] = aviso
        return Response(resp, status=201)


class RutaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_ruta(self, request, ruta_id):
        empresa = _get_empresa(request)
        if not empresa:
            return None, Response({'error': 'Empresa no encontrada.'}, status=404)
        try:
            ruta = (Ruta.objects
                    .select_related('conductor', 'vehiculo')
                    .prefetch_related('paradas')
                    .get(pk=ruta_id, empresa=empresa))
            return ruta, None
        except Ruta.DoesNotExist:
            return None, Response({'error': 'Ruta no encontrada.'}, status=404)

    def get(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.ver'):
            return Response({'error': 'Sin permisos.'}, status=403)
        ruta, err = self._get_ruta(request, ruta_id)
        if err:
            return err
        return Response(_ruta_dict(ruta, detalle=True))

    def put(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        ruta, err = self._get_ruta(request, ruta_id)
        if err:
            return err
        if ruta.estado not in ('borrador', 'pendiente'):
            return Response({'error': 'Solo se pueden editar rutas en borrador o pendiente.'}, status=400)

        empresa = _get_empresa(request)
        data    = request.data

        for campo in ('nombre', 'descripcion', 'notas', 'tipo'):
            if campo in data:
                setattr(ruta, campo, data[campo])
        if 'fecha_programada' in data:
            ruta.fecha_programada = data['fecha_programada'] or None
        if 'hora_programada' in data:
            ruta.hora_programada = data['hora_programada'] or None

        if 'conductor_id' in data:
            cid = data['conductor_id']
            ruta.conductor = Usuario.objects.filter(pk=cid, empresa=empresa).first() if cid else None
        if 'vehiculo_id' in data:
            vid = data['vehiculo_id']
            ruta.vehiculo = Vehiculo.objects.filter(pk=vid, flota__empresa=empresa).first() if vid else None

        errores = _validar_conflictos(
            data.get('fecha_programada', ruta.fecha_programada),
            data.get('conductor_id',    ruta.conductor_id),
            data.get('vehiculo_id',     ruta.vehiculo_id),
            excluir_ruta_id=ruta.id,
        )
        if errores:
            return Response(errores, status=400)

        ruta.save()

        aviso = None
        paradas_data = data.get('paradas')
        if paradas_data is not None:
            aviso = _procesar_paradas_y_calcular(ruta, paradas_data)

        resp = _ruta_dict(ruta, detalle=True)
        if aviso:
            resp['aviso'] = aviso
        return Response(resp)

    def delete(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        ruta, err = self._get_ruta(request, ruta_id)
        if err:
            return err
        if ruta.estado == 'activo':
            return Response({'error': 'No se puede eliminar una ruta activa.'}, status=400)
        nombre = ruta.nombre
        ruta.delete()
        registrar_log('ACTIVIDAD', 'ruta_eliminada', request, detalle={'nombre': nombre})
        return Response(status=204)


class RutaIniciarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        try:
            ruta = Ruta.objects.select_related('vehiculo').get(pk=ruta_id, empresa=empresa)
        except Ruta.DoesNotExist:
            return Response({'error': 'Ruta no encontrada.'}, status=404)

        if ruta.estado != 'pendiente':
            return Response({'error': 'Solo se pueden iniciar rutas pendientes.'}, status=400)

        # Validar anticipación de hora
        error_hora = _validar_anticipacion_inicio(ruta)
        if error_hora:
            return Response({'error': error_hora}, status=400)

        km_inicio = request.data.get('km_inicio')

        ruta.estado       = 'activo'
        ruta.km_inicio    = int(km_inicio) if km_inicio is not None else None
        ruta.fecha_inicio = timezone.now()
        ruta.save()

        # Evento automático
        _km_txt = f" Km inicio: {ruta.km_inicio}." if ruta.km_inicio is not None else ""
        _crear_evento_auto(ruta, f"Ruta iniciada.{_km_txt}")

        registrar_log('ACTIVIDAD', 'ruta_iniciada', request,
                      detalle={'ruta_id': ruta.id, 'km_inicio': ruta.km_inicio})
        if ruta.conductor:
            notificar(ruta.conductor, TipoNotificacion.ACTIVIDAD,
                      "Tu ruta ha comenzado",
                      f"La ruta '{ruta.nombre}' fue marcada como iniciada.",
                      url_accion='/rutas')
            enviar_push(ruta.conductor,
                        titulo='Ruta iniciada 🚛',
                        cuerpo=f"La ruta '{ruta.nombre}' ha comenzado.",
                        data={'tipo': 'ruta_iniciada', 'ruta_id': str(ruta.id)})
        return Response(_ruta_dict(ruta, detalle=True))


class RutaFinalizarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        try:
            ruta = Ruta.objects.select_related('vehiculo', 'conductor').get(pk=ruta_id, empresa=empresa)
        except Ruta.DoesNotExist:
            return Response({'error': 'Ruta no encontrada.'}, status=404)

        if ruta.estado != 'activo':
            return Response({'error': 'Solo se pueden finalizar rutas activas.'}, status=400)

        km_fin = request.data.get('km_fin')
        notas  = request.data.get('notas', '')

        if km_fin is None:
            return Response({'error': 'El campo km_fin es requerido.'}, status=400)

        ruta.km_fin    = int(km_fin)
        ruta.fecha_fin = timezone.now()
        ruta.estado    = 'finalizado'
        if notas:
            ruta.notas = (ruta.notas + '\n' + notas).strip()
        ruta.save()

        # Actualizar km del vehículo
        if ruta.vehiculo:
            ruta.vehiculo.km_actuales = ruta.km_fin
            ruta.vehiculo.save(update_fields=['km_actuales'])

        # Evento automático
        _km_recorridos = f" Km recorridos: {ruta.km_reales}." if ruta.km_reales is not None else ""
        _crear_evento_auto(ruta, f"Ruta finalizada.{_km_recorridos}")

        registrar_log('ACTIVIDAD', 'ruta_finalizada', request, detalle={
            'ruta_id':   ruta.id,
            'km_reales': ruta.km_reales,
        })
        if ruta.conductor:
            _km_msg = f" — {ruta.km_reales} km recorridos" if ruta.km_reales else ""
            notificar(ruta.conductor, TipoNotificacion.ACTIVIDAD,
                      "Ruta finalizada",
                      f"La ruta '{ruta.nombre}' fue marcada como finalizada{_km_msg}.",
                      url_accion='/rutas')
            enviar_push(ruta.conductor,
                        titulo='Ruta finalizada ✓',
                        cuerpo=f"'{ruta.nombre}' completada{_km_msg}.",
                        data={'tipo': 'ruta_finalizada', 'ruta_id': str(ruta.id)})
        return Response(_ruta_dict(ruta, detalle=True))


class RutaCancelarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        try:
            ruta = Ruta.objects.get(pk=ruta_id, empresa=empresa)
        except Ruta.DoesNotExist:
            return Response({'error': 'Ruta no encontrada.'}, status=404)

        if ruta.estado not in ('pendiente', 'activo'):
            return Response({'error': 'Solo se pueden cancelar rutas pendientes o activas.'}, status=400)

        motivo = request.data.get('motivo', '').strip()
        ruta.estado = 'cancelado'
        if motivo:
            ruta.notas = (ruta.notas + '\nCancelación: ' + motivo).strip()
        ruta.save()

        # Evento automático
        _motivo_txt = f" Motivo: {motivo}" if motivo else ""
        _crear_evento_auto(ruta, f"Ruta cancelada.{_motivo_txt}")

        registrar_log('ACTIVIDAD', 'ruta_cancelada', request,
                      detalle={'ruta_id': ruta.id, 'motivo': motivo})
        if ruta.conductor:
            notificar(ruta.conductor, TipoNotificacion.ACTIVIDAD,
                      "Ruta cancelada",
                      f"La ruta '{ruta.nombre}' fue cancelada.{_motivo_txt}",
                      url_accion='/rutas')
            enviar_push(ruta.conductor,
                        titulo='Ruta cancelada',
                        cuerpo=f"'{ruta.nombre}' fue cancelada.{_motivo_txt}",
                        data={'tipo': 'ruta_cancelada', 'ruta_id': str(ruta.id)})
        return Response(_ruta_dict(ruta))


class RouteCalcularView(APIView):
    """Calcula ruta con OSRM: distancia, duración y polyline. Sin costos ni peajes."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        paradas_data = request.data.get('paradas', [])

        puntos = [
            {'lat': p.get('lat') or p.get('latitud'), 'lng': p.get('lng') or p.get('longitud')}
            for p in sorted(paradas_data, key=lambda x: x.get('orden', 0))
            if (p.get('lat') or p.get('latitud')) and (p.get('lng') or p.get('longitud'))
        ]

        if len(puntos) < 2:
            return Response({'error': 'Se necesitan al menos 2 paradas con coordenadas.'}, status=400)

        osrm = calcular_ruta_osrm(puntos)
        if not osrm:
            osrm = calcular_ruta_fallback(puntos)
            if not osrm:
                return Response({
                    'distancia_km': None,
                    'duracion_min': None,
                    'polyline':     [],
                    'aviso':        'No se pudo calcular la ruta. Puede crear la ruta de todas formas.',
                })
            return Response({
                'distancia_km': osrm['distancia_km'],
                'duracion_min': osrm['duracion_min'],
                'polyline':     osrm['polyline'],
                'aviso':        'OSRM no disponible. La distancia es una estimación en línea recta (×1.3).',
            })

        return Response({
            'distancia_km': osrm['distancia_km'],
            'duracion_min': osrm['duracion_min'],
            'polyline':     osrm['polyline'],
        })


class RutaValidarView(APIView):
    """
    POST /api/empresa/rutas/validar/

    Valida conductor + vehículo + fecha antes de crear/editar una ruta.
    Retorna dos listas:
      • errores      → bloquean la creación (vehículo en mantención, conductor bloqueado…)
      • advertencias → el usuario puede confirmar y programar de todas formas
                       (documentos vencidos, mantención próxima…)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)

        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)

        data         = request.data
        vehiculo_id  = data.get('vehiculo_id')
        conductor_id = data.get('conductor_id')
        fecha_str    = data.get('fecha_programada')
        ruta_id      = data.get('ruta_id')      # para excluir al editar

        # Conflictos de fecha
        conflictos = _validar_conflictos(fecha_str, conductor_id, vehiculo_id,
                                         excluir_ruta_id=ruta_id)

        errores_fecha = [
            {'codigo': campo, 'mensaje': msg}
            for campo, msg in conflictos.items()
        ]

        # Estado operacional
        resultado = _validar_estado_operacional(vehiculo_id, conductor_id, empresa)

        errores      = errores_fecha + resultado['errores']
        advertencias = resultado['advertencias']

        return Response({'errores': errores, 'advertencias': advertencias})


class RutaComentariosView(APIView):
    """
    GET  → lista de EventoRuta de la ruta
    POST → crea un comentario manual (admin)
    """
    permission_classes = [IsAuthenticated]

    def _get_ruta(self, request, ruta_id):
        empresa = _get_empresa(request)
        if not empresa:
            return None, Response({'error': 'Empresa no encontrada.'}, status=404)
        try:
            return Ruta.objects.get(pk=ruta_id, empresa=empresa), None
        except Ruta.DoesNotExist:
            return None, Response({'error': 'Ruta no encontrada.'}, status=404)

    def get(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.ver'):
            return Response({'error': 'Sin permisos.'}, status=403)
        ruta, err = self._get_ruta(request, ruta_id)
        if err:
            return err
        eventos = ruta.eventos.select_related('autor').all()
        return Response([_evento_dict(e) for e in eventos])

    def post(self, request, ruta_id):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        ruta, err = self._get_ruta(request, ruta_id)
        if err:
            return err
        texto = request.data.get('texto', '').strip()
        if not texto:
            return Response({'error': 'El texto del comentario es requerido.'}, status=400)
        evento = EventoRuta.objects.create(
            ruta=ruta,
            tipo='comentario',
            texto=texto,
            autor=request.user,
        )
        return Response(_evento_dict(evento), status=201)
