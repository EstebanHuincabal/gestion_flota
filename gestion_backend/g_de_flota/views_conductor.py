"""
views_conductor.py — Endpoints exclusivos para la app móvil de conductores.

Todos los endpoints verifican que el usuario autenticado tenga rol=CONDUCTOR.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils import timezone

from datetime import datetime, timedelta

from .models import EventoRuta, Ruta, Rol, SolicitudConductor, Asignacion, Mantencion, GastoOperativo, Documento, Usuario
from .audit import registrar_log
from .notificaciones import notificar_admins_empresa
from .firebase_push import enviar_push
from .checklist_items import get_items, ITEMS_MAP, MAP_DOC_ITEM
from .views_rutas import _validar_anticipacion_inicio
from .views_gps import notificar_rutas_cambiadas


# ─────────────────────────────────────────
# Endpoint: info del plan actual
# ─────────────────────────────────────────

# Mapeo: clave que usa la app → prefijo en plan.permisos M2M
# plan.modulos usa claves distintas ('trabajos_y_rutas', etc.) por eso
# derivamos la visibilidad desde los permisos granulares, que son la
# fuente de verdad que gestiona GestionPermisos.vue.
# Cada módulo de la app se activa si el plan tiene AL MENOS UN permiso con
# alguno de estos prefijos.
_MODULO_A_PREFIJO = {
    'rutas':        ('rutas.',),
    'solicitudes':  ('solicitudes.',),
    'mantenciones': ('mantenciones.',),
    'documentos':   ('documentos.',),
    'avisos':       ('avisos.',),
}


def _modulos_desde_permisos(plan) -> list:
    """
    Devuelve la lista de módulos que la app debe mostrar,
    derivados de los permisos M2M del plan.
    Un módulo está activo si el plan tiene AL MENOS UN permiso de ese módulo.
    """
    codigos = set(plan.permisos.values_list('codigo', flat=True))
    return [
        modulo
        for modulo, prefijos in _MODULO_A_PREFIJO.items()
        if any(c.startswith(p) for c in codigos for p in prefijos)
    ]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_mi_plan(request):
    """
    Devuelve los módulos visibles en la app y el nombre del plan.

    La visibilidad se deriva de plan.permisos (M2M), NO de plan.modulos
    (JSONField), porque plan.modulos usa claves internas distintas a las
    que maneja GestionPermisos.vue. Así, añadir/quitar permisos de rutas
    en el panel de superadmin se refleja automáticamente en la app.
    """
    empresa     = request.user.empresa
    modulos     = []
    plan_nombre = ''

    if empresa and empresa.plan_id:
        plan        = empresa.plan
        plan_nombre = plan.get_nombre_display() or plan.nombre or ''
        modulos     = _modulos_desde_permisos(plan)

    return Response({'plan_modulos': modulos, 'plan_nombre': plan_nombre})


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
        'id':               ruta.id,
        'nombre':           ruta.nombre,
        'tipo':             ruta.tipo,
        'estado':           ruta.estado,
        'descripcion':      ruta.descripcion,
        'origen':           origen_p.nombre  if origen_p  else '',
        'destino':          destino_p.nombre if destino_p else '',
        'fecha_programada': ruta.fecha_programada.isoformat() if ruta.fecha_programada else None,
        'hora_programada':  ruta.hora_programada.strftime('%H:%M') if ruta.hora_programada else None,
        'fecha_inicio':     ruta.fecha_inicio.isoformat()     if ruta.fecha_inicio     else None,
        'fecha_fin':        ruta.fecha_fin.isoformat()        if ruta.fecha_fin        else None,
        'distancia_km':     float(ruta.distancia_km) if ruta.distancia_km else None,
        'duracion_min':     ruta.duracion_min,
        'km_inicio':        ruta.km_inicio,
        'km_fin':           ruta.km_fin,
        'km_reales':        ruta.km_reales,
        'notas':            ruta.notas,
        'extra':            ruta.extra or {},
        'polyline':         ruta.polyline or [],
        'paradas':          paradas_list,
        'vehiculo': {
            'id':           ruta.vehiculo.id,
            'patente':      ruta.vehiculo.patente,
            'marca':        ruta.vehiculo.marca,
            'modelo':       ruta.vehiculo.modelo,
            'tipo_combustible': ruta.vehiculo.tipo_combustible,
            'km_actuales':  ruta.vehiculo.km_actuales,
            'en_mantencion': ruta.vehiculo.en_mantencion,
        } if ruta.vehiculo else None,
        'conductor': {
            'id':     ruta.conductor.id,
            'nombre': ruta.conductor.nombre,
        } if ruta.conductor else None,
    }

    return result


# ─────────────────────────────────────────
# ─────────────────────────────────────────
# Recordatorios push — se evalúan al cargar rutas
# ─────────────────────────────────────────

_VENTANA_INICIO_MIN     = 30   # avisa cuando faltan ≤ 30 min para la hora de salida
_VENTANA_CHECKLIST_MIN  = 60   # avisa cuando faltan ≤ 60 min y el checklist no está listo
_MARGEN_FINALIZAR_MIN   = 30   # avisa cuando la ruta activa supera duracion_min + 30 min
_DIAS_DOC_AVISO         = 7    # avisa docs que vencen en ≤ 7 días (o ya vencidos hasta -30)
_HORA_VISPERA           = 18   # avisa ruta de mañana solo desde las 18:00 hs


def _enviar_recordatorios_conductor(conductor, rutas_qs):
    """
    Evalúa las rutas del conductor recién cargadas y envía push si corresponde.
    Idempotente: cada recordatorio se marca en Ruta.extra para no repetirse.
    Falla silenciosamente — nunca interrumpe la respuesta al conductor.
    """
    try:
        ahora = timezone.localtime()
        hoy   = ahora.date()

        for ruta in rutas_qs:
            extra_modificado = False

            # ── 1. Inicio de ruta próxima ───────────────────────────────────
            if (ruta.estado == 'pendiente'
                    and ruta.fecha_programada == hoy
                    and ruta.hora_programada
                    and not ruta.extra.get('recordatorio_inicio_enviado')):

                dt_prog  = timezone.make_aware(
                    datetime.combine(ruta.fecha_programada, ruta.hora_programada),
                    timezone.get_current_timezone(),
                )
                restante = (dt_prog - ahora).total_seconds() / 60
                if 0 < restante <= _VENTANA_INICIO_MIN:
                    n = int(round(restante))
                    hora_fmt = ruta.hora_programada.strftime('%H:%M')
                    cuando   = 'en 1 minuto' if n <= 1 else f'en {n} minutos'
                    enviar_push(
                        conductor,
                        titulo='Recordatorio de ruta ⏰',
                        cuerpo=f'Debes iniciar "{ruta.nombre}" {cuando} (salida {hora_fmt}).',
                        data={'tipo': 'recordatorio_ruta', 'ruta_id': str(ruta.id)},
                    )
                    ruta.extra['recordatorio_inicio_enviado'] = True
                    extra_modificado = True

            # ── 2. Checklist pre-viaje pendiente ───────────────────────────
            if (ruta.estado == 'pendiente'
                    and ruta.fecha_programada == hoy
                    and ruta.hora_programada
                    and not ruta.extra.get('checklist_completo')
                    and not ruta.extra.get('recordatorio_checklist_enviado')):

                dt_prog  = timezone.make_aware(
                    datetime.combine(ruta.fecha_programada, ruta.hora_programada),
                    timezone.get_current_timezone(),
                )
                restante = (dt_prog - ahora).total_seconds() / 60
                if 0 < restante <= _VENTANA_CHECKLIST_MIN:
                    n = int(round(restante))
                    enviar_push(
                        conductor,
                        titulo='Checklist pendiente 📋',
                        cuerpo=f'Completa el checklist de "{ruta.nombre}" antes de iniciar (salida en {n} min).',
                        data={'tipo': 'recordatorio_checklist', 'ruta_id': str(ruta.id)},
                    )
                    ruta.extra['recordatorio_checklist_enviado'] = True
                    extra_modificado = True

            # ── 3. Ruta activa sin finalizar ───────────────────────────────
            if (ruta.estado == 'activo'
                    and ruta.fecha_inicio
                    and ruta.duracion_min
                    and not ruta.extra.get('recordatorio_finalizar_enviado')):

                transcurrido = (ahora - timezone.localtime(ruta.fecha_inicio)).total_seconds() / 60
                if transcurrido > ruta.duracion_min + _MARGEN_FINALIZAR_MIN:
                    enviar_push(
                        conductor,
                        titulo='¿Olvidaste finalizar tu ruta? 🏁',
                        cuerpo=f'"{ruta.nombre}" lleva más tiempo del estimado. Si ya llegaste, finalízala en la app.',
                        data={'tipo': 'recordatorio_finalizar', 'ruta_id': str(ruta.id)},
                    )
                    ruta.extra['recordatorio_finalizar_enviado'] = True
                    extra_modificado = True

            # ── 4. Ruta para mañana (víspera) ──────────────────────────────
            if (ruta.estado == 'pendiente'
                    and ruta.fecha_programada == hoy + timedelta(days=1)
                    and ahora.hour >= _HORA_VISPERA
                    and not ruta.extra.get('recordatorio_vispera_enviado')):

                hora_txt = f' a las {ruta.hora_programada.strftime("%H:%M")}' if ruta.hora_programada else ''
                enviar_push(
                    conductor,
                    titulo='Ruta programada para mañana 🗓',
                    cuerpo=f'Mañana tienes la ruta "{ruta.nombre}"{hora_txt}. Prepárate con tiempo.',
                    data={'tipo': 'recordatorio_vispera', 'ruta_id': str(ruta.id)},
                )
                ruta.extra['recordatorio_vispera_enviado'] = True
                extra_modificado = True

            if extra_modificado:
                ruta.save(update_fields=['extra'])

        # ── 5. Documentos por vencer (1 aviso al día por conductor) ────────
        prefs = conductor.notif_prefs or {}
        if prefs.get('recordatorio_docs_ultima') != str(hoy):
            asignacion = Asignacion.objects.filter(conductor=conductor, activo=True).first()
            docs = list(Documento.objects.filter(entidad='conductor', conductor=conductor))
            if asignacion and asignacion.vehiculo:
                docs += list(Documento.objects.filter(entidad='vehiculo', vehiculo=asignacion.vehiculo))

            # Quedarse con el doc más reciente por tipo
            mejor = {}
            for d in docs:
                if d.fecha_vencimiento is None:
                    continue
                if d.tipo not in mejor or d.fecha_vencimiento > mejor[d.tipo].fecha_vencimiento:
                    mejor[d.tipo] = d

            criticos = [d for d in mejor.values()
                        if d.dias_para_vencer() is not None and -30 <= d.dias_para_vencer() <= _DIAS_DOC_AVISO]
            if criticos:
                if len(criticos) == 1:
                    d    = criticos[0]
                    dias = d.dias_para_vencer()
                    estado = ('está vencido/a' if dias < 0
                              else 'vence hoy' if dias == 0
                              else f'vence en {dias} día{"s" if dias != 1 else ""}')
                    cuerpo = f'Tu {d.get_tipo_display()} {estado}. Renuévalo cuanto antes.'
                else:
                    cuerpo = f'Tienes {len(criticos)} documentos por vencer o vencidos. Revísalos en la app.'

                enviar_push(
                    conductor,
                    titulo='Documentos por vencer 📄',
                    cuerpo=cuerpo,
                    data={'tipo': 'recordatorio_documentos'},
                )
                prefs['recordatorio_docs_ultima'] = str(hoy)
                conductor.notif_prefs = prefs
                conductor.save(update_fields=['notif_prefs'])

    except Exception:
        pass  # fail-silent — nunca bloquear la respuesta al conductor


# GET /api/conductor/rutas/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_rutas(request):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores pueden acceder a este endpoint.'}, status=403)

    # Verificar módulo 'rutas' en el plan de la empresa
    # Se usa plan.permisos (M2M) como fuente de verdad, igual que conductor_mi_plan,
    # porque plan.modulos usa la clave 'trabajos_y_rutas' (no 'rutas').
    empresa = request.user.empresa
    if empresa and empresa.plan_id:
        if 'rutas' not in _modulos_desde_permisos(empresa.plan):
            return Response(
                {'error': 'Tu plan no incluye el módulo de rutas.', 'codigo': 'MODULO_NO_INCLUIDO', 'modulo': 'rutas'},
                status=403,
            )

    rutas_qs = list(
        Ruta.objects
        .filter(conductor=request.user, estado__in=['pendiente', 'activo', 'finalizado'])
        .select_related('vehiculo', 'conductor')
        .prefetch_related('paradas')
        .order_by('fecha_programada', '-created_at')
    )

    _enviar_recordatorios_conductor(request.user, rutas_qs)

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
            .prefetch_related('paradas')
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

    # Validar anticipación de hora programada
    error_hora = _validar_anticipacion_inicio(ruta)
    if error_hora:
        return Response({'error': error_hora}, status=400)

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

    # Evento automático
    _km_txt = f" Km inicio: {ruta.km_inicio}." if ruta.km_inicio is not None else ""
    EventoRuta.objects.create(ruta=ruta, tipo='auto', texto=f"Ruta iniciada por conductor.{_km_txt}")

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
                                 url_accion='/empresa/rutas', permiso='rutas.ver')

    # Avisar al mapa de flota para que dibuje el trazado en tiempo real
    notificar_rutas_cambiadas(ruta.empresa_id)
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

    km_fin = request.data.get('km_fin')
    notas  = request.data.get('notas', '')

    ruta.estado    = 'finalizado'
    ruta.fecha_fin = timezone.now()

    if km_fin is not None:
        ruta.km_fin = int(km_fin)
        if ruta.vehiculo:
            ruta.vehiculo.km_actuales = int(km_fin)
            ruta.vehiculo.save(update_fields=['km_actuales'])

    if notas:
        ruta.notas = notas
    ruta.save()

    # Evento automático
    _km_recorridos = f" Km recorridos: {ruta.km_reales}." if ruta.km_reales is not None else ""
    EventoRuta.objects.create(ruta=ruta, tipo='auto', texto=f"Ruta finalizada por conductor.{_km_recorridos}")

    registrar_log('ACTIVIDAD', 'ruta_finalizada', request, detalle={
        'ruta_id': ruta.id, 'ruta_nombre': ruta.nombre, 'km_fin': ruta.km_fin,
    })
    # Notificar a los admins de la empresa
    _empresa_rf = request.user.empresa
    if _empresa_rf:
        _nombre_cf = request.user.nombre or request.user.email
        _km_txt    = f" — {ruta.km_reales} km recorridos" if ruta.km_reales else ""
        notificar_admins_empresa(_empresa_rf, 'actividad',
                                 f"Ruta finalizada por {_nombre_cf}",
                                 f"{_nombre_cf} finalizó la ruta '{ruta.nombre}'{_km_txt}.",
                                 url_accion='/empresa/rutas', permiso='rutas.ver')

    # Avisar al mapa de flota para que quite el trazado en tiempo real
    notificar_rutas_cambiadas(ruta.empresa_id)
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

    extra_data = {}
    if tipo == 'combustible':
        try:
            monto = float(request.data.get('monto', 0))
            litros = float(request.data.get('litros', 0))
            if monto <= 0 or litros <= 0:
                raise ValueError
            extra_data['monto'] = monto
            extra_data['litros'] = litros
        except (TypeError, ValueError):
            return Response({'error': 'Monto y litros deben ser números positivos válidos.'}, status=400)
        if not foto:
            return Response({'error': 'Para recargas de combustible es obligatorio adjuntar el comprobante.'}, status=400)

    elif tipo == 'incidencia':
        subtipo = request.data.get('subtipo', '').strip()
        if subtipo:
            extra_data['subtipo'] = subtipo
        if subtipo == 'multa':
            try:
                monto = float(request.data.get('monto', 0))
                if monto <= 0:
                    raise ValueError
                extra_data['monto'] = monto
            except (TypeError, ValueError):
                return Response({'error': 'El monto de la multa debe ser un número positivo válido.'}, status=400)

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
    if tipo not in ['documento', 'combustible'] and len(descripcion) < 10:
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

    # Evitar duplicados: si ya hay una solicitud de mantención sin resolver para
    # el mismo vehículo, avisar (a menos que el conductor confirme con forzar=true).
    forzar = str(request.data.get('forzar', '')).lower() in ('1', 'true', 'sí', 'si')
    if tipo == 'mantencion' and vehiculo and not forzar:
        existente = SolicitudConductor.objects.filter(
            conductor=request.user, vehiculo=vehiculo, tipo='mantencion',
            estado__in=['pendiente', 'en_revision'],
        ).first()
        if existente:
            return Response({
                'error':  'Ya tienes una solicitud de mantención pendiente para este vehículo.',
                'codigo': 'solicitud_duplicada',
                'solicitud_id': existente.id,
            }, status=409)

    solicitud = SolicitudConductor.objects.create(
        conductor=request.user,
        empresa=empresa,
        vehiculo=vehiculo,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        prioridad=prioridad,
        foto=foto,
        extra=extra_data,
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

    # ── Email a los admins: nueva solicitud ──────────────────────────────────
    if empresa:
        try:
            from .email_service import email_solicitud_nueva
            from django.conf import settings as _settings
            conductor_nombre = request.user.nombre or request.user.email
            admins = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True)
            for admin in admins:
                email_solicitud_nueva(
                    email=admin.email,
                    nombre_admin=admin.nombre or admin.email,
                    empresa_nombre=empresa.nombre,
                    tipo=tipo,
                    titulo_sol=titulo,
                    conductor_nombre=conductor_nombre,
                    url_solicitudes=f"{_settings.FRONTEND_URL}/empresa/solicitudes",
                )
        except Exception:
            pass

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
        page_size = min(100, max(1, int(request.query_params.get('page_size', 15))))
    except (ValueError, TypeError):
        page, page_size = 1, 15

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
        mantencion = Mantencion.objects.select_related('vehiculo__empresa').get(
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
    _empresa_mi = vehiculo.empresa if vehiculo.empresa_id else None
    if _empresa_mi:
        _nombre_mi = request.user.nombre or request.user.email
        notificar_admins_empresa(_empresa_mi, 'actividad',
                                 f"Mantención iniciada por {_nombre_mi}",
                                 f"{_nombre_mi} inició '{mantencion.tipo_mantencion}' del vehículo {vehiculo.patente}.",
                                 url_accion='/empresa/mantenciones', permiso='mantenciones.ver')

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
    # Si la mantención es correctiva (falla no presupuestada), el gasto se marca
    # como correctivo para que cuente en Correctivos, no como mantención normal.
    empresa = vehiculo.empresa if vehiculo.empresa_id else None
    gasto   = None
    if empresa:
        es_corr = getattr(mantencion, 'es_correctivo', False)
        gasto = GastoOperativo.objects.create(
            empresa       = empresa,
            vehiculo      = vehiculo,
            conductor     = request.user,
            categoria     = 'mantencion',
            es_correctivo = es_corr,
            categoria_correctiva = 'otro_correctivo' if es_corr else '',
            prioridad_correctiva = 'media' if es_corr else '',
            descripcion   = (('Correctivo: ' if es_corr else 'Mantención: ')
                             + f'{mantencion.tipo_mantencion} — {vehiculo.patente}'),
            monto         = int(costo),
            fecha         = fecha_realizada,
            comprobante   = mantencion.foto_comprobante if mantencion.foto_comprobante else None,
            registrado_por= request.user,
        )
        if es_corr and not mantencion.gasto_correctivo_generado:
            mantencion.gasto_correctivo_generado = True
            mantencion.save(update_fields=['gasto_correctivo_generado'])

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
                                 url_accion='/empresa/mantenciones', permiso='mantenciones.ver')

    return Response({
        'ok':         True,
        'mantencion': _serializar_mantencion(mantencion, request),
        'gasto_id':   gasto.id if gasto else None,
    }, status=200)


# ─────────────────────────────────────────
# PATCH /api/conductor/perfil/
# ─────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def conductor_actualizar_perfil(request):
    """
    El conductor actualiza sus propios datos personales desde la app móvil.
    Campos permitidos: telefono, licencia, nombre.
    Notifica a los admins de la empresa cuando hay cambios.
    """
    import re
    user = request.user
    if user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    data             = request.data
    campos_cambiados = []
    errores          = {}

    if 'telefono' in data:
        tel = re.sub(r'[\s\-\(\)]', '', str(data['telefono'] or ''))
        if not re.match(r'^(\+56)?9\d{8}$', tel):
            errores['telefono'] = 'Formato inválido. Use +569XXXXXXXX o 9XXXXXXXX.'
        else:
            user.set_telefono(tel)
            campos_cambiados.append('teléfono')

    if 'licencia' in data:
        from .serializers import LICENCIA_PATRON, LICENCIA_ERROR
        lic = str(data['licencia'] or '').strip().upper()
        if not lic:
            errores['licencia'] = 'El número de licencia no puede estar vacío.'
        # Licencia chilena: 3 letras + 10 dígitos (mismo patrón que el panel web).
        elif not re.match(LICENCIA_PATRON, lic):
            errores['licencia'] = LICENCIA_ERROR
        else:
            user.set_licencia(lic)
            if (user.extra or {}).get('requiere_licencia'):
                user.extra['requiere_licencia'] = False
            campos_cambiados.append('N° de licencia')

    if 'nombre' in data:
        nom = str(data['nombre'] or '').strip()
        if len(nom) < 2:
            errores['nombre'] = 'El nombre debe tener al menos 2 caracteres.'
        else:
            user.nombre_cifrado = nom
            campos_cambiados.append('nombre')

    # Completar onboarding → marca primer_login=False
    if data.get('completar_onboarding') and not errores:
        user.primer_login = False
        campos_cambiados.append('_onboarding')

    if errores:
        return Response({'errores': errores}, status=400)

    if not campos_cambiados:
        return Response({'ok': True, 'mensaje': 'Sin cambios.'})

    user.save()

    # Notificar a los admins de la empresa (excluir flag interno de onboarding)
    campos_visibles = [c for c in campos_cambiados if c != '_onboarding']
    if user.empresa_id and campos_visibles:
        from .notificaciones import notificar_admins_empresa
        from .models import TipoNotificacion
        detalle_txt = ', '.join(campos_visibles)
        notificar_admins_empresa(
            empresa    = user.empresa,
            tipo       = TipoNotificacion.ACTIVIDAD,
            titulo     = f'Conductor actualizó su perfil',
            mensaje    = f'{user.nombre or user.email} actualizó su información: {detalle_txt}.',
            url_accion = f'/empresa/conductores',
            permiso    = 'conductores.ver',
        )

    return Response({
        'ok':               True,
        'nombre':           user.nombre or user.email,
        # Coherente con el login: se pide la licencia mientras el conductor no la tenga.
        'requiere_licencia': user.rol == Rol.CONDUCTOR and not user.licencia,
        'primer_login':     user.primer_login,
    })


# POST /api/conductor/recuperar-password/  (público — sin JWT)
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([])
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def conductor_recuperar_password(request):
    """
    Genera una contraseña temporal y la envía por email al conductor.
    Endpoint público — responde siempre con 200 para no filtrar si el RUT existe.
    Body: { "rut": "12345678-9" }
    """
    import secrets
    import hashlib
    from .models import normalizar_rut

    # Rate limit: endpoint público → evita spam de correos y enumeración de RUTs.
    if getattr(request, 'limited', False):
        return Response({'ok': True})

    rut_raw = str(request.data.get('rut', '')).strip()
    if not rut_raw:
        return Response({'ok': True})  # respuesta genérica siempre

    rut_norm = normalizar_rut(rut_raw)
    rut_hash = hashlib.sha256(rut_norm.encode()).hexdigest()

    conductor = Usuario.objects.filter(rut_hash=rut_hash, rol=Rol.CONDUCTOR, is_active=True).first()
    if not conductor:
        return Response({'ok': True})  # no filtrar existencia

    clave_temp = secrets.token_urlsafe(10)
    conductor.set_password(clave_temp)
    conductor.intentos_fallidos = 0
    conductor.is_blocked        = False
    conductor.save(update_fields=['password', 'intentos_fallidos', 'is_blocked'])

    try:
        from .email_service import email_reset_password
        email_reset_password(
            email          = conductor.email,
            nombre         = conductor.nombre or conductor.email,
            empresa_nombre = conductor.empresa.nombre if conductor.empresa else 'FlotaSystem',
            clave_temporal = clave_temp,
            url_login      = '',
        )
    except Exception:
        pass  # fail-silent

    registrar_log('SEGURIDAD', 'recuperar_password_conductor', request, usuario=conductor,
                  detalle={'rut_hash': rut_hash[:8] + '...'})

    return Response({'ok': True})


# PATCH /api/conductor/cambiar-password/
# ─────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def conductor_cambiar_password(request):
    """
    El conductor cambia su propia contraseña.
    Body: { "password_actual": "...", "password_nuevo": "...", "confirmar": "..." }
    """
    user = request.user
    if user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    data       = request.data
    actual     = str(data.get('password_actual', ''))
    nuevo      = str(data.get('password_nuevo', ''))
    confirmar  = str(data.get('confirmar', ''))

    errores = {}

    if not user.check_password(actual):
        errores['password_actual'] = 'La contraseña actual es incorrecta.'

    if len(nuevo) < 8:
        errores['password_nuevo'] = 'Debe tener al menos 8 caracteres.'
    elif not any(c.isupper() for c in nuevo):
        errores['password_nuevo'] = 'Debe incluir al menos una letra mayúscula.'
    elif not any(c.isdigit() for c in nuevo):
        errores['password_nuevo'] = 'Debe incluir al menos un número.'
    elif nuevo == actual:
        errores['password_nuevo'] = 'La nueva contraseña debe ser diferente a la actual.'

    if not errores and nuevo != confirmar:
        errores['confirmar'] = 'Las contraseñas no coinciden.'

    if errores:
        return Response({'errores': errores}, status=400)

    user.set_password(nuevo)
    user.save(update_fields=['password'])

    registrar_log('SEGURIDAD', 'password_cambiado', request,
                  detalle={'conductor_id': user.id})

    return Response({'ok': True})


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


# ─────────────────────────────────────────
# GET + POST /api/conductor/checklist/:ruta_id/
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conductor_checklist(request, ruta_id):
    """
    Checklist pre-viaje vinculado a una ruta.

    GET  → devuelve ítems con estado de documentos pre-cargado + borrador si existe.
    POST → guarda o actualiza el checklist como SolicitudConductor tipo='mantencion'.
    """
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    # ── Obtener ruta ──────────────────────────────────────────────────────────
    try:
        ruta = (
            Ruta.objects
            .select_related('vehiculo', 'conductor')
            .get(id=ruta_id, conductor=request.user)
        )
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    # ── GET ───────────────────────────────────────────────────────────────────
    if request.method == 'GET':
        items = get_items()

        # Enriquecer ítems de documentos del vehículo con estado real
        docs_vehiculo = {}
        if ruta.vehiculo:
            for doc in Documento.objects.filter(vehiculo=ruta.vehiculo):
                docs_vehiculo[doc.tipo] = doc

        for item in items:
            if item['id'] in ('doc_permiso', 'doc_revision', 'doc_soap'):
                tipo_doc = {v: k for k, v in MAP_DOC_ITEM.items()}.get(item['id'])
                doc = docs_vehiculo.get(tipo_doc) if tipo_doc else None
                if doc:
                    estado_doc = doc.estado()
                    item['estado_documento']  = estado_doc
                    item['fecha_vencimiento'] = doc.fecha_vencimiento.isoformat() if doc.fecha_vencimiento else None
                    item['pre_resultado']     = 'ok' if estado_doc == 'vigente' else None
                else:
                    item['estado_documento']  = None
                    item['fecha_vencimiento'] = None
                    item['pre_resultado']     = None
            # Ítem de licencia del conductor
            elif item['id'] == 'doc_licencia':
                doc_lic = Documento.objects.filter(
                    conductor=request.user, tipo='licencia'
                ).first()
                if doc_lic:
                    estado_doc = doc_lic.estado()
                    item['estado_documento']  = estado_doc
                    item['fecha_vencimiento'] = doc_lic.fecha_vencimiento.isoformat() if doc_lic.fecha_vencimiento else None
                    item['pre_resultado']     = 'ok' if estado_doc == 'vigente' else None
                else:
                    item['estado_documento']  = None
                    item['fecha_vencimiento'] = None
                    item['pre_resultado']     = None

        respuestas_guardadas = {}

        return Response({
            'items':               items,
            'respuestas_guardadas': respuestas_guardadas,
            'ruta': {
                'id':     ruta.id,
                'nombre': ruta.nombre,
            },
            'vehiculo': {
                'patente': ruta.vehiculo.patente if ruta.vehiculo else '',
                'marca':   ruta.vehiculo.marca   if ruta.vehiculo else '',
            },
        })

    # ── POST ──────────────────────────────────────────────────────────────────
    respuestas = request.data.get('respuestas', {})
    firma_b64  = request.data.get('firma_base64', '')

    # 1. Validar ítems obligatorios
    items = get_items()
    obligatorios = [i['id'] for i in items if i['obligatorio']]
    faltantes    = [i for i in obligatorios if i not in respuestas or not respuestas[i].get('resultado')]

    if faltantes:
        nombres_faltantes = [ITEMS_MAP.get(f, f) for f in faltantes]
        return Response({
            'error':    f'Faltan {len(faltantes)} ítem(s) obligatorio(s).',
            'faltantes': nombres_faltantes,
        }, status=400)

    # 2. Detectar fallas
    fallas = [iid for iid in obligatorios if respuestas.get(iid, {}).get('resultado') == 'falla']

    # 3. Resumen de fallas
    resumen_fallas = '; '.join(
        f"{ITEMS_MAP.get(iid, iid)}: {respuestas[iid].get('observacion', '').strip() or 'sin observación'}"
        for iid in fallas
    )

    tiene_fallas = bool(fallas)

    # 4. Datos de contexto
    empresa          = request.user.empresa
    vehiculo         = ruta.vehiculo
    nombre_conductor = request.user.nombre or request.user.email
    patente          = vehiculo.patente if vehiculo else '—'

    # 5. Notificación in-app a los admins
    if empresa:
        if not tiene_fallas:
            notificar_admins_empresa(
                empresa,
                tipo='actividad',
                titulo=f'✓ Vehículo en orden — {patente}',
                mensaje=f'{nombre_conductor} completó el checklist. Vehículo listo para partir en {ruta.nombre}.',
                url_accion='/empresa/mantenciones/',
            )
        else:
            notificar_admins_empresa(
                empresa,
                tipo='mantencion',
                titulo=f'⚠ Checklist con fallas — {patente}',
                mensaje=f'{nombre_conductor} detectó fallas antes de partir: {resumen_fallas}',
                url_accion='/empresa/mantenciones/',
            )

    # 6. Actualizar ruta.extra
    extra_ruta = ruta.extra or {}
    extra_ruta['checklist_completo'] = True
    extra_ruta['checklist_fallas']   = fallas
    ruta.extra = extra_ruta
    ruta.save(update_fields=['extra'])

    # 7. Push al conductor (fail-silent)
    try:
        if not tiene_fallas:
            enviar_push(request.user, 'Checklist completado ✓', 'Todo en orden. Ya puedes iniciar la ruta.',
                        data={'tipo': 'checklist_completado', 'ruta_id': str(ruta.id)})
        else:
            enviar_push(request.user, 'Checklist enviado ⚠', 'Se notificó al administrador sobre las fallas.',
                        data={'tipo': 'checklist_enviado', 'ruta_id': str(ruta.id)})
    except Exception:
        registrar_log('ERROR', 'checklist_push_fallido', request, detalle={'ruta_id': ruta.id})

    # 8. Email a los admins
    if empresa:
        try:
            from .email_service import email_checklist_fallas, email_checklist_ok
            from django.conf import settings as _settings
            admins   = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True)
            url_mant = f"{_settings.FRONTEND_URL}/empresa/mantenciones/"
            if tiene_fallas:
                lista_fallas = [
                    f"{ITEMS_MAP.get(iid, iid)}: "
                    f"{respuestas.get(iid, {}).get('observacion', '').strip() or 'sin observación'}"
                    for iid in fallas
                ]
                for admin in admins:
                    email_checklist_fallas(
                        email=admin.email,
                        nombre_admin=admin.nombre or admin.email,
                        empresa_nombre=empresa.nombre,
                        conductor_nombre=nombre_conductor,
                        patente=patente,
                        fallas=lista_fallas,
                        url_solicitudes=url_mant,
                    )
            else:
                for admin in admins:
                    email_checklist_ok(
                        email=admin.email,
                        nombre_admin=admin.nombre or admin.email,
                        empresa_nombre=empresa.nombre,
                        conductor_nombre=nombre_conductor,
                        patente=patente,
                        ruta_nombre=ruta.nombre,
                        url_solicitudes=url_mant,
                    )
        except Exception:
            pass

    # 9. Registrar log
    registrar_log('ACTIVIDAD', 'checklist_completado', request, detalle={
        'ruta_id':      ruta.id,
        'tiene_fallas': tiene_fallas,
        'fallas':       fallas,
    })

    # 10. Retornar
    return Response({
        'ok':           True,
        'tiene_fallas': tiene_fallas,
        'mensaje': (
            'Todo en orden. Puedes iniciar la ruta.'
            if not tiene_fallas
            else 'Checklist enviado con fallas. El administrador fue notificado.'
        ),
    })


# ─────────────────────────────────────────
# GET  /api/conductor/rutas/:id/comentarios/
# POST /api/conductor/rutas/:id/comentario/
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conductor_eventos_ruta(request, ruta_id):
    """Devuelve el historial de eventos de una ruta del conductor."""
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    try:
        ruta = Ruta.objects.get(id=ruta_id, conductor=request.user)
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    eventos = EventoRuta.objects.filter(ruta=ruta).select_related('autor').order_by('created_at')
    return Response([
        {
            'id':         e.id,
            'tipo':       e.tipo,
            'texto':      e.texto,
            'autor':      e.autor.nombre if e.autor else None,
            'created_at': e.created_at.isoformat(),
        }
        for e in eventos
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductor_agregar_comentario(request, ruta_id):
    """El conductor agrega un comentario al historial de la ruta."""
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    try:
        ruta = Ruta.objects.get(id=ruta_id, conductor=request.user)
    except Ruta.DoesNotExist:
        return Response({'error': 'Ruta no encontrada.'}, status=404)

    texto = request.data.get('texto', '').strip()
    if not texto:
        return Response({'error': 'El texto del comentario es requerido.'}, status=400)

    evento = EventoRuta.objects.create(
        ruta=ruta,
        tipo='comentario',
        texto=texto,
        autor=request.user,
    )
    return Response({
        'id':         evento.id,
        'tipo':       evento.tipo,
        'texto':      evento.texto,
        'autor':      request.user.nombre,
        'created_at': evento.created_at.isoformat(),
    }, status=201)


# GET/PATCH /api/conductor/vehiculo/foto/
# GET: foto actual del vehículo asignado. PATCH: subir/actualizar la foto.
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def conductor_subir_foto_vehiculo(request):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo conductores.'}, status=403)

    asignacion = Asignacion.objects.filter(
        conductor=request.user, activo=True
    ).select_related('vehiculo').first()
    if not asignacion or not asignacion.vehiculo:
        return Response({'error': 'No tienes un vehiculo asignado.'}, status=404)

    vehiculo = asignacion.vehiculo

    # GET: devuelve la foto actual (para refrescar la app al abrir Ajustes).
    if request.method == 'GET':
        return Response({
            'foto_url': request.build_absolute_uri(vehiculo.foto.url) if vehiculo.foto else None,
        })

    foto = request.FILES.get('foto')
    if not foto:
        return Response({'error': 'No se envio ninguna imagen.'}, status=400)
    if foto.size > 8 * 1024 * 1024:
        return Response({'error': 'La imagen no puede superar 8 MB.'}, status=400)
    if not (foto.content_type or '').startswith('image/'):
        return Response({'error': 'El archivo debe ser una imagen.'}, status=400)

    vehiculo.foto = foto
    vehiculo.save(update_fields=['foto'])
    registrar_log('ACTIVIDAD', 'vehiculo_foto_conductor', request, detalle={'patente': vehiculo.patente})
    return Response({'ok': True, 'foto_url': request.build_absolute_uri(vehiculo.foto.url)})
