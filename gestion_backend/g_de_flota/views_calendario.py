"""
views_calendario.py
Endpoint único que agrega todos los eventos con fecha del sistema
y los devuelve como una lista plana para el calendario global.
"""
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Rol, Ruta, Mantencion, MantencionProgramada,
    Documento, SolicitudConductor, AlertaMantencion,
)


def _empresa_id(request):
    """Devuelve el empresa_id del contexto: query param (SUPERADMIN) o perfil (USUARIO)."""
    if request.user.rol == Rol.SUPERADMIN:
        eid = request.query_params.get('empresa_id')
        return int(eid) if eid else None
    return request.user.empresa_id


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendario_eventos(request):
    """
    GET /api/empresa/calendario/
    Parámetros:
      - desde  (YYYY-MM-DD, default: primer día del mes actual)
      - hasta  (YYYY-MM-DD, default: último día del mes actual)
      - empresa_id (solo SUPERADMIN)
    Respuesta:
      Lista de { id, tipo, subtipo, titulo, subtitulo, fecha, hora, color, ref_id, url }
    """
    hoy = timezone.now().date()

    # Rango de fechas
    try:
        desde = date.fromisoformat(request.query_params.get('desde') or hoy.replace(day=1).isoformat())
    except ValueError:
        desde = hoy.replace(day=1)

    try:
        # Fin de mes por defecto
        if request.query_params.get('hasta'):
            hasta = date.fromisoformat(request.query_params['hasta'])
        else:
            import calendar as _cal
            ultimo = _cal.monthrange(hoy.year, hoy.month)[1]
            hasta = hoy.replace(day=ultimo)
    except ValueError:
        import calendar as _cal
        ultimo = _cal.monthrange(hoy.year, hoy.month)[1]
        hasta = hoy.replace(day=ultimo)

    empresa_id = _empresa_id(request)
    if not empresa_id:
        return Response({'error': 'Empresa no identificada.'}, status=400)

    eventos = []

    # ── 1. RUTAS ────────────────────────────────────────────────────────────────
    COLOR_RUTA = {
        'pendiente':  'indigo',
        'activo':     'green',
        'finalizado': 'slate',
        'cancelado':  'red',
        'borrador':   'gray',
    }
    rutas = (
        Ruta.objects
        .filter(empresa_id=empresa_id)
        .select_related('conductor', 'vehiculo')
    )
    # Rutas por fecha_programada (pendiente / borrador)
    for r in rutas.filter(
        estado__in=['pendiente', 'borrador'],
        fecha_programada__range=(desde, hasta),
    ):
        conductor_nombre = r.conductor.nombre if r.conductor else 'Sin conductor'
        vehiculo_label   = r.vehiculo.patente  if r.vehiculo  else 'Sin vehículo'
        hora = r.hora_programada.strftime('%H:%M') if r.hora_programada else None
        eventos.append({
            'id':        f'ruta-prog-{r.pk}',
            'tipo':      'ruta',
            'subtipo':   r.estado,
            'titulo':    r.nombre,
            'subtitulo': f'{conductor_nombre} · {vehiculo_label}',
            'fecha':     r.fecha_programada.isoformat(),
            'hora':      hora,
            'color':     COLOR_RUTA.get(r.estado, 'indigo'),
            'ref_id':    r.pk,
            'url':       '/rutas',
        })

    # Rutas activas por fecha_inicio
    for r in rutas.filter(estado='activo', fecha_inicio__date__range=(desde, hasta)):
        conductor_nombre = r.conductor.nombre if r.conductor else 'Sin conductor'
        eventos.append({
            'id':        f'ruta-inicio-{r.pk}',
            'tipo':      'ruta',
            'subtipo':   'activo',
            'titulo':    r.nombre,
            'subtitulo': f'En curso · {conductor_nombre}',
            'fecha':     r.fecha_inicio.date().isoformat(),
            'hora':      r.fecha_inicio.strftime('%H:%M'),
            'color':     'green',
            'ref_id':    r.pk,
            'url':       '/rutas',
        })

    # Rutas finalizadas/canceladas por fecha_fin
    for r in rutas.filter(
        estado__in=['finalizado', 'cancelado'],
        fecha_fin__date__range=(desde, hasta),
    ):
        conductor_nombre = r.conductor.nombre if r.conductor else 'Sin conductor'
        eventos.append({
            'id':        f'ruta-fin-{r.pk}',
            'tipo':      'ruta',
            'subtipo':   r.estado,
            'titulo':    r.nombre,
            'subtitulo': f'{r.get_estado_display()} · {conductor_nombre}',
            'fecha':     r.fecha_fin.date().isoformat(),
            'hora':      r.fecha_fin.strftime('%H:%M'),
            'color':     COLOR_RUTA.get(r.estado, 'slate'),
            'ref_id':    r.pk,
            'url':       '/rutas',
        })

    # ── 2. MANTENCIONES ─────────────────────────────────────────────────────────
    mantenciones = (
        Mantencion.objects
        .filter(vehiculo__empresa_id=empresa_id)
        .select_related('vehiculo')
    )
    COLOR_MANT = {
        'pendiente':  'orange',
        'en_proceso': 'amber',
        'realizada':  'blue',
        'cancelada':  'gray',
    }
    for m in mantenciones.filter(
        fecha_programada__range=(desde, hasta),
    ):
        eventos.append({
            'id':        f'mant-{m.pk}',
            'tipo':      'mantencion',
            'subtipo':   m.estado,
            'titulo':    m.tipo_mantencion,
            'subtitulo': f'{m.vehiculo.patente} · {m.get_estado_display()}',
            'fecha':     m.fecha_programada.isoformat(),
            'hora':      None,
            'color':     COLOR_MANT.get(m.estado, 'orange'),
            'ref_id':    m.pk,
            'url':       '/mantenciones',
        })
    # Realizadas en el rango (fecha_realizada diferente a fecha_programada)
    for m in mantenciones.filter(
        estado='realizada',
        fecha_realizada__range=(desde, hasta),
    ).exclude(fecha_realizada=None):
        if m.fecha_programada == m.fecha_realizada:
            continue  # ya incluida arriba
        eventos.append({
            'id':        f'mant-real-{m.pk}',
            'tipo':      'mantencion',
            'subtipo':   'realizada',
            'titulo':    m.tipo_mantencion,
            'subtitulo': f'{m.vehiculo.patente} · Completada',
            'fecha':     m.fecha_realizada.isoformat(),
            'hora':      None,
            'color':     'blue',
            'ref_id':    m.pk,
            'url':       '/mantenciones',
        })

    # ── 3. MANTENCIONES PREDICTIVAS ─────────────────────────────────────────────
    mp_qs = (
        MantencionProgramada.objects
        .filter(vehiculo__empresa_id=empresa_id, estado='activa')
        .select_related('vehiculo', 'regla')
    )
    for mp in mp_qs.filter(fecha_siguiente__range=(desde, hasta)):
        dias_rest = (mp.fecha_siguiente - hoy).days
        color = 'red' if dias_rest < 0 else ('amber' if dias_rest <= 7 else 'yellow')
        label = 'Vencida' if dias_rest < 0 else (f'En {dias_rest} día{"s" if dias_rest != 1 else ""}')
        eventos.append({
            'id':        f'mant-pred-{mp.pk}',
            'tipo':      'mantencion_predictiva',
            'subtipo':   'vencida' if dias_rest < 0 else 'proxima',
            'titulo':    mp.regla.tipo,
            'subtitulo': f'{mp.vehiculo.patente} · {label}',
            'fecha':     mp.fecha_siguiente.isoformat(),
            'hora':      None,
            'color':     color,
            'ref_id':    mp.pk,
            'url':       '/predictivo',
        })

    # ── 4. DOCUMENTOS — vencimientos ────────────────────────────────────────────
    docs_qs = Documento.objects.filter(
        empresa_id=empresa_id,
        fecha_vencimiento__isnull=False,
    ).select_related('vehiculo', 'conductor')

    # Margen extendido: mostramos documentos que vencen dentro de los próximos 60 días
    # y los que vencieron en los últimos 30 días (para no perder historial)
    margen_antes = desde - timedelta(days=30)
    margen_despues = hasta + timedelta(days=60)

    for doc in docs_qs.filter(fecha_vencimiento__range=(margen_antes, margen_despues)):
        dias = (doc.fecha_vencimiento - hoy).days
        if dias < 0:
            color, subtipo = 'red', 'vencido'
            estado_label = f'Venció hace {abs(dias)} día{"s" if abs(dias) != 1 else ""}'
        elif dias <= 15:
            color, subtipo = 'red', 'por_vencer'
            estado_label = f'Vence en {dias} día{"s" if dias != 1 else ""}'
        elif dias <= 30:
            color, subtipo = 'amber', 'por_vencer'
            estado_label = f'Vence en {dias} días'
        else:
            color, subtipo = 'yellow', 'vigente'
            estado_label = f'Vence en {dias} días'

        if doc.entidad == 'vehiculo' and doc.vehiculo:
            entidad_label = doc.vehiculo.patente
        elif doc.entidad == 'conductor' and doc.conductor:
            entidad_label = doc.conductor.nombre or doc.conductor.email
        else:
            entidad_label = '—'

        eventos.append({
            'id':        f'doc-{doc.pk}',
            'tipo':      'documento',
            'subtipo':   subtipo,
            'titulo':    doc.get_tipo_display(),
            'subtitulo': f'{entidad_label} · {estado_label}',
            'fecha':     doc.fecha_vencimiento.isoformat(),
            'hora':      None,
            'color':     color,
            'ref_id':    doc.pk,
            'url':       '/documentos',
        })

    # ── 5. SOLICITUDES ──────────────────────────────────────────────────────────
    COLOR_SOL = {
        'pendiente':   'purple',
        'en_revision': 'violet',
        'aprobado':    'teal',
        'rechazado':   'gray',
    }
    solic_qs = (
        SolicitudConductor.objects
        .filter(empresa_id=empresa_id)
        .select_related('conductor')
    )
    for s in solic_qs.filter(created_at__date__range=(desde, hasta)):
        conductor_nombre = s.conductor.nombre if s.conductor else '—'
        eventos.append({
            'id':        f'sol-{s.pk}',
            'tipo':      'solicitud',
            'subtipo':   s.estado,
            'titulo':    s.titulo,
            'subtitulo': f'{conductor_nombre} · {s.get_tipo_display()} · {s.get_estado_display()}',
            'fecha':     s.created_at.date().isoformat(),
            'hora':      s.created_at.strftime('%H:%M'),
            'color':     COLOR_SOL.get(s.estado, 'purple'),
            'ref_id':    s.pk,
            'url':       '/solicitudes',
        })

    # Ordenar por fecha + hora
    eventos.sort(key=lambda e: (e['fecha'], e['hora'] or '00:00'))

    return Response(eventos)
