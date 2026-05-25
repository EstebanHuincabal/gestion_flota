from datetime import date, date as _date

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import registrar_log
from .notificaciones import notificar, notificar_admins_empresa
from .firebase_push import enviar_push
from .models import (
    ConfiguracionRuta, Empresa, GastoOperativo, Parada, Peaje,
    PeajeRuta, Rol, Ruta, TipoNotificacion, Usuario, Vehiculo,
)
from .ruta_calculator import (
    calcular_costos, calcular_ruta_osrm, calcular_ruta_fallback,
    detectar_peajes_en_ruta,
)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _iso(val):
    """Convierte date/datetime a isoformat, o devuelve el string tal cual.

    Después de asignar un string a un DateField/DateTimeField y llamar
    a .save(), el objeto en memoria puede conservar el string original en
    lugar del tipo Python —Django solo realiza la conversión al leer desde
    la base de datos.  Este helper maneja ambos casos de forma segura.
    """
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
        'id':                     ruta.id,
        'nombre':                 ruta.nombre,
        'tipo':                   ruta.tipo,
        'estado':                 ruta.estado,
        'descripcion':            ruta.descripcion,
        'conductor_id':           ruta.conductor_id,
        'conductor':              ruta.conductor.nombre if ruta.conductor else None,
        'vehiculo_id':            ruta.vehiculo_id,
        'vehiculo':               str(ruta.vehiculo) if ruta.vehiculo else None,
        'fecha_programada':       _iso(ruta.fecha_programada),
        'fecha_inicio':           _iso(ruta.fecha_inicio),
        'fecha_fin':              _iso(ruta.fecha_fin),
        'km_inicio':              ruta.km_inicio,
        'km_fin':                 ruta.km_fin,
        'km_reales':              ruta.km_reales,
        'distancia_km':           float(ruta.distancia_km) if ruta.distancia_km else None,
        'duracion_min':           ruta.duracion_min,
        'costo_combustible_est':  ruta.costo_combustible_est,
        'costo_peajes_est':       ruta.costo_peajes_est,
        'costo_total_est':        ruta.costo_total_est,
        'costo_combustible_real': ruta.costo_combustible_real,
        'costo_peajes_real':      ruta.costo_peajes_real,
        'costo_total_real':       ruta.costo_total_real,
        'origen':                 origen_nombre,
        'destino':                destino_nombre,
        'notas':                  ruta.notas,
        'created_at':             _iso(ruta.created_at),
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
        d['peajes'] = [
            {
                'id':       pr.peaje.id,
                'nombre':   pr.peaje.nombre,
                'tarifa':   int(pr.tarifa),
                'latitud':  pr.peaje.latitud,
                'longitud': pr.peaje.longitud,
            }
            for pr in ruta.peajesruta.select_related('peaje').all()
        ]

    return d


def _procesar_paradas_y_calcular(ruta, paradas_data, es_punta, empresa):
    """Crea las paradas, llama OSRM, detecta peajes y calcula costos estimados."""
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
            ruta.polyline = osrm['polyline']
            if es_fallback:
                aviso_osrm = (
                    'OSRM no disponible. La distancia es una estimación en línea recta '
                    '(×1.3 de sinuosidad). Los costos son aproximados.'
                )

            config   = ConfiguracionRuta.get_for_empresa(empresa)
            cat      = ruta.vehiculo.categoria_peaje if ruta.vehiculo else 'liviano'
            peajes   = detectar_peajes_en_ruta(osrm['polyline'], categoria_vehiculo=cat)

            PeajeRuta.objects.filter(ruta=ruta).delete()
            for peaje in peajes:
                usar_punta = es_punta and peaje.tarifa_punta is not None
                tarifa = peaje.tarifa_punta if usar_punta else peaje.tarifa_normal
                PeajeRuta.objects.create(ruta=ruta, peaje=peaje, tarifa=tarifa)

            if ruta.vehiculo:
                costos = calcular_costos(
                    float(osrm['distancia_km']), ruta.vehiculo, peajes, config, es_punta,
                    categoria_vehiculo=cat,
                )
                ruta.costo_combustible_est = costos['combustible']
                ruta.costo_peajes_est      = costos['peajes_total']
                ruta.costo_total_est       = costos['total']

    ruta.save()
    return aviso_osrm


# ─────────────────────────────────────────
# Validaciones de negocio
# ─────────────────────────────────────────

def _validar_conflictos(fecha_str, conductor_id, vehiculo_id, excluir_ruta_id=None):
    """
    Valida:
      • Fecha no anterior a hoy
      • Conductor sin ruta pendiente/activa ese día
      • Vehículo sin ruta pendiente/activa ese día

    Retorna dict de errores (vacío = sin conflictos).
    Rutas canceladas/finalizadas NO cuentan como conflicto.
    Si no hay fecha_programada, no se aplica ninguna validación de conflicto.
    """
    errores = {}

    if not fecha_str:
        return errores

    try:
        fecha = _date.fromisoformat(str(fecha_str))
    except ValueError:
        return {'fecha_programada': 'Fecha inválida.'}

    if fecha < _date.today():
        errores['fecha_programada'] = 'La fecha no puede ser anterior a hoy.'
        return errores   # sin fecha válida no tiene sentido continuar

    qs = Ruta.objects.filter(
        fecha_programada=fecha,
        estado__in=['pendiente', 'activo'],
    )
    if excluir_ruta_id:
        qs = qs.exclude(pk=excluir_ruta_id)

    if conductor_id:
        conflicto = qs.filter(conductor_id=conductor_id).first()
        if conflicto:
            errores['conductor_id'] = (
                f'El conductor ya tiene la ruta "{conflicto.nombre}" '
                f'asignada para esa fecha.'
            )

    if vehiculo_id:
        conflicto = qs.filter(vehiculo_id=vehiculo_id).first()
        if conflicto:
            errores['vehiculo_id'] = (
                f'El vehículo ya está asignado a la ruta "{conflicto.nombre}" '
                f'para esa fecha.'
            )

    return errores


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

        estado      = request.query_params.get('estado')
        tipo        = request.query_params.get('tipo')
        conductor_id = request.query_params.get('conductor_id')
        vehiculo_id  = request.query_params.get('vehiculo_id')
        fecha_desde  = request.query_params.get('fecha_desde')
        fecha_hasta  = request.query_params.get('fecha_hasta')

        if estado:      qs = qs.filter(estado=estado)
        if tipo:        qs = qs.filter(tipo=tipo)
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
            'total':         todas.count(),
            'activas':       todas.filter(estado='activo').count(),
            'pendientes':    todas.filter(estado='pendiente').count(),
            'finalizadas':   todas.filter(estado='finalizado').count(),
            'canceladas':    todas.filter(estado='cancelado').count(),
            'km_mes':        float(mes.aggregate(km=Sum('distancia_km'))['km'] or 0),
            'costo_est_mes': int(mes.aggregate(c=Sum('costo_total_est'))['c'] or 0),
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

        # ── Validar conflictos de fecha / conductor / vehículo ────────────────
        errores = _validar_conflictos(
            data.get('fecha_programada'),
            data.get('conductor_id'),
            data.get('vehiculo_id'),
        )
        if errores:
            return Response(errores, status=400)

        ruta = Ruta(
            empresa=empresa,
            tipo=data.get('tipo', 'carga'),
            nombre=data.get('nombre', '').strip(),
            descripcion=data.get('descripcion', ''),
            estado='pendiente',
            notas=data.get('notas', ''),
            fecha_programada=data.get('fecha_programada') or None,
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
        aviso = _procesar_paradas_y_calcular(ruta, paradas_data, data.get('es_punta', False), empresa)

        registrar_log('ACTIVIDAD', 'ruta_creada', request,
                      detalle={'ruta_id': ruta.id, 'nombre': ruta.nombre})
        # Notificar al conductor asignado
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
                    .prefetch_related('paradas', 'peajesruta__peaje')
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

        if 'conductor_id' in data:
            cid = data['conductor_id']
            ruta.conductor = Usuario.objects.filter(pk=cid, empresa=empresa).first() if cid else None
        if 'vehiculo_id' in data:
            vid = data['vehiculo_id']
            ruta.vehiculo = Vehiculo.objects.filter(pk=vid, flota__empresa=empresa).first() if vid else None

        # ── Validar conflictos con los valores finales ─────────────────────────
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
            aviso = _procesar_paradas_y_calcular(ruta, paradas_data, data.get('es_punta', False), empresa)

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

        km_inicio = request.data.get('km_inicio')

        ruta.estado      = 'activo'
        ruta.km_inicio   = int(km_inicio) if km_inicio is not None else None
        ruta.fecha_inicio = timezone.now()
        ruta.save()

        registrar_log('ACTIVIDAD', 'ruta_iniciada', request,
                      detalle={'ruta_id': ruta.id, 'km_inicio': ruta.km_inicio})
        # Notificar al conductor asignado
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

        km_fin       = request.data.get('km_fin')
        costo_comb   = int(request.data.get('costo_combustible_real') or 0)
        costo_peaje  = int(request.data.get('costo_peajes_real') or 0)
        notas        = request.data.get('notas', '')

        if km_fin is None:
            return Response({'error': 'El campo km_fin es requerido.'}, status=400)

        ruta.km_fin                = int(km_fin)
        ruta.costo_combustible_real = costo_comb
        ruta.costo_peajes_real      = costo_peaje
        ruta.costo_total_real       = costo_comb + costo_peaje
        ruta.fecha_fin              = timezone.now()
        ruta.estado                 = 'finalizado'
        if notas:
            ruta.notas = (ruta.notas + '\n' + notas).strip()
        ruta.save()

        # Actualizar km del vehículo
        if ruta.vehiculo:
            ruta.vehiculo.km_actuales = ruta.km_fin
            ruta.vehiculo.save(update_fields=['km_actuales'])

        # Gasto operativo automático — solo peajes (combustible se registra al cargar estanque)
        hoy = timezone.now().date()
        if costo_peaje > 0:
            GastoOperativo.objects.create(
                empresa=empresa,
                vehiculo=ruta.vehiculo,
                conductor=ruta.conductor,
                categoria='peaje',
                descripcion=f'Peajes ruta {ruta.nombre}',
                monto=costo_peaje,
                fecha=hoy,
                registrado_por=request.user,
            )

        registrar_log('ACTIVIDAD', 'ruta_finalizada', request, detalle={
            'ruta_id': ruta.id,
            'km_reales': ruta.km_reales,
            'costo_total_real': ruta.costo_total_real,
        })
        # Notificar al conductor asignado
        if ruta.conductor:
            _km_txt = f" — {ruta.km_reales} km recorridos" if ruta.km_reales else ""
            notificar(ruta.conductor, TipoNotificacion.ACTIVIDAD,
                      "Ruta finalizada",
                      f"La ruta '{ruta.nombre}' fue marcada como finalizada{_km_txt}.",
                      url_accion='/rutas')
            enviar_push(ruta.conductor,
                        titulo='Ruta finalizada ✓',
                        cuerpo=f"'{ruta.nombre}' completada{_km_txt}.",
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

        registrar_log('ACTIVIDAD', 'ruta_cancelada', request,
                      detalle={'ruta_id': ruta.id, 'motivo': motivo})
        # Notificar al conductor asignado
        if ruta.conductor:
            _motivo_txt = f" Motivo: {motivo}" if motivo else ""
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
    """Calcula ruta, detecta peajes y costos sin guardar nada."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)

        paradas_data = request.data.get('paradas', [])
        vehiculo_id  = request.data.get('vehiculo_id')
        es_punta     = request.data.get('es_punta', False)

        puntos = [
            {'lat': p.get('lat') or p.get('latitud'), 'lng': p.get('lng') or p.get('longitud')}
            for p in sorted(paradas_data, key=lambda x: x.get('orden', 0))
            if (p.get('lat') or p.get('latitud')) and (p.get('lng') or p.get('longitud'))
        ]

        if len(puntos) < 2:
            return Response({'error': 'Se necesitan al menos 2 paradas con coordenadas.'}, status=400)

        osrm = calcular_ruta_osrm(puntos)
        if not osrm:
            return Response({
                'distancia_km':      None,
                'duracion_min':      None,
                'costos':            None,
                'peajes_detectados': [],
                'polyline':          [],
                'aviso':             'No se pudo calcular la ruta. Puede crear la ruta de todas formas.',
            })

        config   = ConfiguracionRuta.get_for_empresa(empresa)

        vehiculo = None
        if vehiculo_id:
            vehiculo = Vehiculo.objects.filter(pk=vehiculo_id, flota__empresa=empresa).first()

        cat    = vehiculo.categoria_peaje if vehiculo else 'liviano'
        peajes = detectar_peajes_en_ruta(osrm['polyline'], categoria_vehiculo=cat)

        costos = calcular_costos(
            float(osrm['distancia_km']), vehiculo, peajes, config, es_punta,
            categoria_vehiculo=cat,
        ) if vehiculo else None

        return Response({
            'distancia_km': osrm['distancia_km'],
            'duracion_min': osrm['duracion_min'],
            'polyline':     osrm['polyline'],
            'costos':       costos,
            'peajes_detectados': [
                {
                    'id':       p.id,
                    'nombre':   p.nombre,
                    'latitud':  p.latitud,
                    'longitud': p.longitud,
                    'tarifa':   int(p.tarifa_punta if es_punta and p.tarifa_punta else p.tarifa_normal),
                }
                for p in peajes
            ],
        })


class PeajesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        peajes = Peaje.objects.filter(activo=True).values(
            'id', 'nombre', 'ruta', 'autopista',
            'latitud', 'longitud', 'categoria',
            'tarifa_normal', 'tarifa_punta',
        )
        return Response(list(peajes))


class RutaConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)
        cfg = ConfiguracionRuta.get_for_empresa(empresa)
        return Response({
            'precio_bencina':        cfg.precio_bencina,
            'precio_diesel':         cfg.precio_diesel,
            'radio_deteccion_peaje': cfg.radio_deteccion_peaje,
        })

    def put(self, request):
        if not _tiene_permiso(request.user, 'rutas.crear'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)
        cfg  = ConfiguracionRuta.get_for_empresa(empresa)
        data = request.data
        if 'precio_bencina' in data:
            cfg.precio_bencina = int(data['precio_bencina'])
        if 'precio_diesel' in data:
            cfg.precio_diesel = int(data['precio_diesel'])
        if 'radio_deteccion_peaje' in data:
            cfg.radio_deteccion_peaje = int(data['radio_deteccion_peaje'])
        cfg.save()
        return Response({
            'precio_bencina':        cfg.precio_bencina,
            'precio_diesel':         cfg.precio_diesel,
            'radio_deteccion_peaje': cfg.radio_deteccion_peaje,
        })
