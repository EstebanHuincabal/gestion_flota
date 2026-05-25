"""
views_solicitudes.py — Panel web para gestión de solicitudes de conductores.

Endpoints:
    GET  /api/empresa/solicitudes/              → lista paginada + filtros + resumen
    GET  /api/empresa/solicitudes/conteo/       → solo {pendientes: N} (badge navbar)
    GET  /api/empresa/solicitudes/:id/          → detalle
    PUT  /api/empresa/solicitudes/:id/aprobar/  → aprobar + acciones automáticas
    PUT  /api/empresa/solicitudes/:id/rechazar/ → rechazar (respuesta obligatoria)
"""
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Empresa, SolicitudConductor, Mantencion, Documento, GastoOperativo, Rol, Asignacion
from .serializers import SolicitudConductorSerializer
from .audit import registrar_log
from .notificaciones import notificar


def _emitir_cambio_estado_conductor(solicitud):
    """
    Envía evento WebSocket `solicitud_actualizada` al conductor de forma
    que la app móvil pueda actualizar el estado en tiempo real sin polling.
    Nunca lanza excepción — falla silenciosamente.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'conductor_{solicitud.conductor_id}',
                {
                    'type':         'solicitud_actualizada',
                    'solicitud_id': solicitud.id,
                    'estado':       solicitud.estado,
                    'respuesta':    solicitud.respuesta or '',
                },
            )
    except Exception:
        pass


def _get_empresa(request):
    """Devuelve la Empresa del usuario o None. Compatible con empresa_id query-param para SUPERADMIN."""
    if request.user.rol == Rol.SUPERADMIN:
        eid = request.query_params.get('empresa_id') or request.data.get('empresa_id')
        if eid:
            return Empresa.objects.filter(pk=eid).first()
        return None
    return request.user.empresa


def _notificar_conductor(solicitud, aprobado, extra=None):
    """Notifica al conductor del resultado de su solicitud."""
    extra = extra or {}
    if aprobado:
        titulo = 'Solicitud aprobada'
        if solicitud.tipo == 'mantencion' and (extra.get('fecha_programada') or extra.get('taller')):
            partes = []
            if extra.get('fecha_programada'):
                partes.append(f"programada para el {extra['fecha_programada']}")
            if extra.get('taller'):
                partes.append(f"en {extra['taller']}")
            detalle = 'Mantención ' + ' '.join(partes) + '.'
            mensaje = detalle
        else:
            mensaje = solicitud.respuesta or 'Tu solicitud fue aprobada.'
    else:
        titulo  = 'Solicitud rechazada'
        mensaje = solicitud.respuesta or 'Tu solicitud fue rechazada.'
    notificar(
        solicitud.conductor,
        tipo='actividad',
        titulo=titulo,
        mensaje=mensaje,
        url_accion='/solicitudes',
        forzar=True,
    )


def _crear_entidad_automatica(solicitud, request_user, extra=None):
    """
    Al aprobar, crea entidades derivadas según el tipo.

    extra (dict) — solo relevante para tipo 'mantencion':
        fecha_programada (str|None) — fecha ISO
        taller           (str)      — nombre del taller / mecánico
        presupuesto      (float|None)
        suspender_vehiculo (bool)   — poner vehiculo.en_mantencion = True
    """
    extra = extra or {}

    if solicitud.tipo == 'mantencion' and solicitud.vehiculo:
        mantencion = Mantencion.objects.create(
            vehiculo=solicitud.vehiculo,
            tipo_mantencion=solicitud.titulo,
            descripcion=solicitud.descripcion,
            estado='pendiente',
            fecha_programada=extra.get('fecha_programada') or None,
            taller_proveedor=extra.get('taller', ''),
            presupuesto=extra.get('presupuesto') or None,
        )
        # Suspender vehículo si se indicó explícitamente
        if extra.get('suspender_vehiculo'):
            solicitud.vehiculo.en_mantencion = True
            solicitud.vehiculo.save(update_fields=['en_mantencion'])
        return mantencion

    elif solicitud.tipo == 'documento' and solicitud.vehiculo:
        Documento.objects.create(
            empresa=solicitud.empresa,
            entidad='vehiculo',
            tipo='revision_tecnica',      # tipo genérico; se puede ajustar manualmente
            vehiculo=solicitud.vehiculo,
            subido_por=request_user,
            notas=f'Generado automáticamente desde solicitud #{solicitud.id}',
            archivo=solicitud.foto if solicitud.foto else None,
        )


# ─────────────────────────────────────────
# GET /api/empresa/solicitudes/
# ─────────────────────────────────────────

class SolicitudesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)

        qs = SolicitudConductor.objects.filter(empresa=empresa).select_related(
            'conductor', 'vehiculo', 'respondido_por'
        )

        # Filtros
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        tipo = request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        conductor_id = request.query_params.get('conductor_id')
        if conductor_id:
            qs = qs.filter(conductor_id=conductor_id)

        fecha_desde = request.query_params.get('fecha_desde')
        if fecha_desde:
            qs = qs.filter(created_at__date__gte=fecha_desde)

        fecha_hasta = request.query_params.get('fecha_hasta')
        if fecha_hasta:
            qs = qs.filter(created_at__date__lte=fecha_hasta)

        buscar = request.query_params.get('buscar', '').strip()
        if buscar:
            qs = qs.filter(titulo__icontains=buscar)

        total = qs.count()

        # Resumen (sobre el QS sin paginación para tenerlo siempre completo)
        from django.utils.timezone import now
        hoy = now().date()
        qs_empresa_full = SolicitudConductor.objects.filter(empresa=empresa)
        resumen = {
            'pendientes':    qs_empresa_full.filter(estado='pendiente').count(),
            'en_revision':   qs_empresa_full.filter(estado='en_revision').count(),
            'aprobadas_hoy': qs_empresa_full.filter(estado='aprobado', respondido_at__date=hoy).count(),
            'total_mes':     qs_empresa_full.filter(
                created_at__year=hoy.year, created_at__month=hoy.month
            ).count(),
        }

        # Paginación
        page      = max(1, int(request.query_params.get('page', 1)))
        page_size = min(100, int(request.query_params.get('page_size', 20)))
        offset    = (page - 1) * page_size
        pages     = max(1, (total + page_size - 1) // page_size)

        page_qs = qs[offset: offset + page_size]
        serializer = SolicitudConductorSerializer(
            page_qs, many=True, context={'request': request}
        )

        return Response({
            'solicitudes': serializer.data,
            'total':       total,
            'page':        page,
            'pages':       pages,
            'resumen':     resumen,
        })


# ─────────────────────────────────────────
# GET /api/empresa/solicitudes/conteo/
# ─────────────────────────────────────────

class SolicitudesConteoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'pendientes': 0})
        pendientes = SolicitudConductor.objects.filter(
            empresa=empresa, estado__in=['pendiente', 'en_revision']
        ).count()
        return Response({'pendientes': pendientes})


# ─────────────────────────────────────────
# GET + PUT /api/empresa/solicitudes/:id/
# ─────────────────────────────────────────

class SolicitudDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_sol(self, request, sol_id):
        empresa = _get_empresa(request)
        if not empresa:
            return None, Response({'error': 'Empresa no encontrada.'}, status=404)
        try:
            sol = SolicitudConductor.objects.select_related(
                'conductor', 'vehiculo', 'respondido_por'
            ).get(pk=sol_id, empresa=empresa)
            return sol, None
        except SolicitudConductor.DoesNotExist:
            return None, Response({'error': 'Solicitud no encontrada.'}, status=404)

    def get(self, request, sol_id):
        sol, err = self._get_sol(request, sol_id)
        if err:
            return err
        return Response(SolicitudConductorSerializer(sol, context={'request': request}).data)

    def put(self, request, sol_id):
        """Cambiar estado a 'en_revision' desde el panel."""
        sol, err = self._get_sol(request, sol_id)
        if err:
            return err
        if sol.estado not in ('pendiente', 'en_revision'):
            return Response({'error': 'La solicitud ya fue resuelta.'}, status=400)
        sol.estado = 'en_revision'
        sol.save(update_fields=['estado', 'updated_at'])
        return Response(SolicitudConductorSerializer(sol, context={'request': request}).data)


# ─────────────────────────────────────────
# PUT /api/empresa/solicitudes/:id/aprobar/
# ─────────────────────────────────────────

class SolicitudAprobarView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, sol_id):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)
        try:
            sol = SolicitudConductor.objects.select_related(
                'conductor', 'vehiculo', 'respondido_por'
            ).get(pk=sol_id, empresa=empresa)
        except SolicitudConductor.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=404)

        if sol.estado in ('aprobado', 'rechazado'):
            return Response({'error': 'La solicitud ya fue resuelta.'}, status=400)

        sol.estado         = 'aprobado'
        sol.respuesta      = request.data.get('respuesta', '')
        sol.respondido_por = request.user
        sol.respondido_at  = timezone.now()
        sol.save()

        # Parámetros de programación de mantención (opcionales)
        extra = {}
        if sol.tipo == 'mantencion':
            extra['fecha_programada']  = request.data.get('fecha_programada') or None
            extra['taller']            = str(request.data.get('taller', '')).strip()
            raw_pres = request.data.get('presupuesto')
            try:
                extra['presupuesto'] = float(raw_pres) if raw_pres not in (None, '') else None
            except (ValueError, TypeError):
                extra['presupuesto'] = None
            extra['suspender_vehiculo'] = bool(request.data.get('suspender_vehiculo', False))

        entidad   = _crear_entidad_automatica(sol, request.user, extra)
        _notificar_conductor(sol, aprobado=True, extra=extra)
        _emitir_cambio_estado_conductor(sol)   # tiempo real → app conductores

        # Push notification al conductor si hay token registrado
        from .firebase_push import enviar_push
        if sol.tipo == 'mantencion':
            partes = []
            if extra.get('fecha_programada'):
                partes.append(f"para el {extra['fecha_programada']}")
            if extra.get('taller'):
                partes.append(f"en {extra['taller']}")
            detalle_push = ('Mantención programada ' + ' '.join(partes)).strip() if partes else 'Revisa los detalles en la app.'
            enviar_push(
                sol.conductor,
                titulo='Mantención aprobada 🔧',
                cuerpo=detalle_push,
                data={'tipo': 'mantencion_aprobada', 'solicitud_id': str(sol.id)},
            )
        else:
            enviar_push(
                sol.conductor,
                titulo='Solicitud aprobada ✓',
                cuerpo=sol.respuesta or 'Tu solicitud fue aprobada.',
                data={'tipo': 'solicitud_aprobada', 'solicitud_id': str(sol.id)},
            )

        registrar_log('ACTIVIDAD', 'solicitud_aprobada', request, detalle={
            'solicitud_id': sol.id, 'tipo': sol.tipo, 'titulo': sol.titulo,
            **({'fecha_programada': extra.get('fecha_programada'), 'taller': extra.get('taller')} if sol.tipo == 'mantencion' else {}),
        })

        resp = {
            'ok': True,
            'solicitud': SolicitudConductorSerializer(sol, context={'request': request}).data,
        }
        # Si se creó una mantención, incluir su id para redirigir al formulario
        if entidad and sol.tipo == 'mantencion':
            resp['mantencion_id'] = entidad.id

        return Response(resp)


# ─────────────────────────────────────────
# PUT /api/empresa/solicitudes/:id/rechazar/
# ─────────────────────────────────────────

class SolicitudRechazarView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, sol_id):
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=404)
        try:
            sol = SolicitudConductor.objects.select_related(
                'conductor', 'vehiculo', 'respondido_por'
            ).get(pk=sol_id, empresa=empresa)
        except SolicitudConductor.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=404)

        if sol.estado in ('aprobado', 'rechazado'):
            return Response({'error': 'La solicitud ya fue resuelta.'}, status=400)

        respuesta = request.data.get('respuesta', '').strip()
        if len(respuesta) < 10:
            return Response({'respuesta': 'El motivo de rechazo debe tener al menos 10 caracteres.'}, status=400)

        sol.estado         = 'rechazado'
        sol.respuesta      = respuesta
        sol.respondido_por = request.user
        sol.respondido_at  = timezone.now()
        sol.save()

        _notificar_conductor(sol, aprobado=False)
        _emitir_cambio_estado_conductor(sol)   # tiempo real → app conductores

        from .firebase_push import enviar_push
        enviar_push(
            sol.conductor,
            titulo='Solicitud rechazada',
            cuerpo=respuesta[:100],
            data={'tipo': 'solicitud_rechazada', 'solicitud_id': str(sol.id)},
        )

        registrar_log('ACTIVIDAD', 'solicitud_rechazada', request, detalle={
            'solicitud_id': sol.id, 'tipo': sol.tipo, 'titulo': sol.titulo,
        })

        return Response({
            'ok': True,
            'solicitud': SolicitudConductorSerializer(sol, context={'request': request}).data,
        })
