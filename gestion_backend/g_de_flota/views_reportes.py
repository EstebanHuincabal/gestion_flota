import csv
import io
from datetime import date as date_cls, timedelta

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from django.db.models import Sum
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Empresa, Vehiculo, Mantencion, Rol,
    GastoOperativo, Documento, Usuario, PresupuestoMensual,
    Ruta, SolicitudConductor,
)


def _xlsx_response(headers, rows, filename, sheet_title='Reporte'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    ws.append(headers)
    ws.row_dimensions[1].height = 22
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for row in rows:
        ws.append([str(v) if v is not None else '' for v in row])

    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 45)

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _es_superadmin(user):
    return getattr(user, 'rol', None) == Rol.SUPERADMIN


def _sin_permiso(user, codigo):
    """True si el usuario NO tiene el permiso (SUPERADMIN siempre lo tiene)."""
    from .views import tiene_permiso
    return not tiene_permiso(user, codigo)


def _get_empresa(user, params):
    if _es_superadmin(user):
        eid = params.get('empresa_id')
        if eid:
            try:
                return Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                return None
        return None
    return user.empresa


def _label_vehiculo(v):
    return f"{v.marca} {v.modelo} · {v.patente}"


# ─────────────────────────────────────────
# Reporte de mantenciones
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_mantencion(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'mantenciones.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Mantencion.objects.filter(
        vehiculo__empresa=empresa
    ).select_related('vehiculo', 'vehiculo__empresa')

    mes         = request.query_params.get('mes')
    anio        = request.query_params.get('anio')
    vehiculo_id = request.query_params.get('vehiculo_id')

    if anio:
        qs = qs.filter(fecha_programada__year=int(anio))
    if mes:
        qs = qs.filter(fecha_programada__month=int(mes))
    if vehiculo_id:
        qs = qs.filter(vehiculo_id=int(vehiculo_id))

    mantenciones = list(qs.order_by('-fecha_programada'))

    por_estado  = {'pendiente': 0, 'en_proceso': 0, 'realizada': 0, 'cancelada': 0}
    tipos       = {}
    meses_dict  = {}
    costo_total = 0

    for m in mantenciones:
        costo = int(m.costo or 0)
        costo_total += costo
        por_estado[m.estado] = por_estado.get(m.estado, 0) + 1

        tipo = m.tipo_mantencion or 'Sin tipo'
        if tipo not in tipos:
            tipos[tipo] = {'tipo': tipo, 'cantidad': 0, 'costo': 0}
        tipos[tipo]['cantidad'] += 1
        tipos[tipo]['costo']    += costo

        if m.fecha_programada:
            key = (m.fecha_programada.year, m.fecha_programada.month)
            if key not in meses_dict:
                meses_dict[key] = {'anio': key[0], 'mes': key[1], 'cantidad': 0, 'costo': 0}
            meses_dict[key]['cantidad'] += 1
            meses_dict[key]['costo']    += costo

    total    = len(mantenciones)
    por_tipo = sorted(tipos.values(), key=lambda x: x['costo'], reverse=True)[:10]
    por_mes  = sorted(meses_dict.values(), key=lambda x: (x['anio'], x['mes']))

    detalle = [
        {
            'id':               m.id,
            'vehiculo':         _label_vehiculo(m.vehiculo),
            'tipo':             m.tipo_mantencion or '—',
            'fecha_programada': m.fecha_programada.isoformat() if m.fecha_programada else None,
            'fecha_realizada':  m.fecha_realizada.isoformat()  if m.fecha_realizada  else None,
            'costo':            int(m.costo or 0),
            'estado':           m.estado,
            'taller':           m.taller_proveedor or '—',
        }
        for m in mantenciones
    ]

    return Response({
        'resumen': {
            'total':          total,
            'costo_total':    costo_total,
            'costo_promedio': round(costo_total / total) if total else 0,
            'por_estado':     por_estado,
            'por_tipo':       por_tipo,
            'por_mes':        por_mes,
        },
        'detalle': detalle,
    })


# ─────────────────────────────────────────
# Reporte de estado de flota
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_flota(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'flotas.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    vehiculos = Vehiculo.objects.filter(
        empresa=empresa, activo=True
    ).prefetch_related(
        'docs_v', 'mantenciones', 'asignaciones__conductor'
    )

    vehiculos_data    = []
    con_docs_vencidos = 0
    sin_conductor     = 0

    for v in vehiculos:
        asig      = v.asignaciones.filter(activo=True).first()
        conductor = asig.conductor.nombre if asig and asig.conductor else None
        if not conductor:
            sin_conductor += 1

        docs_v          = list(v.docs_v.all())
        docs_vigentes   = sum(1 for d in docs_v if d.estado() == 'vigente')
        docs_por_vencer = sum(1 for d in docs_v if d.estado() == 'por_vencer')
        docs_vencidos   = sum(1 for d in docs_v if d.estado() == 'vencido')
        if docs_vencidos:
            con_docs_vencidos += 1

        ultima = (
            v.mantenciones.filter(estado='realizada')
            .order_by('-fecha_realizada')
            .first()
        )
        costo_total = int(
            v.mantenciones.filter(estado='realizada')
            .aggregate(t=Sum('costo'))['t'] or 0
        )

        vehiculos_data.append({
            'id':                       v.id,
            'patente':                  v.patente,
            'marca':                    v.marca,
            'modelo':                   v.modelo,
            'anio':                     v.anio,
            'km_actuales':              v.km_actuales or 0,
            'conductor':                conductor,
            'docs_vigentes':            docs_vigentes,
            'docs_por_vencer':          docs_por_vencer,
            'docs_vencidos':            docs_vencidos,
            'ultima_mantencion':        ultima.fecha_realizada.isoformat() if ultima and ultima.fecha_realizada else None,
            'costo_total_mantenciones': costo_total,
        })

    return Response({
        'resumen': {
            'total':             len(vehiculos_data),
            'con_docs_vencidos': con_docs_vencidos,
            'sin_conductor':     sin_conductor,
        },
        'vehiculos': vehiculos_data,
    })


# ─────────────────────────────────────────
# Exportación CSV
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_exportar(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR:
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    tipo = request.query_params.get('tipo', 'mantencion')

    # Cada exportación exige el permiso del módulo correspondiente.
    _PERMISO_EXPORT = {'mantencion': 'mantenciones.ver', 'flota': 'flotas.ver'}
    if _sin_permiso(user, _PERMISO_EXPORT.get(tipo, 'mantenciones.ver')):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    if tipo == 'mantencion':
        qs = Mantencion.objects.filter(
            vehiculo__empresa=empresa
        ).select_related('vehiculo')

        mes         = request.query_params.get('mes')
        anio        = request.query_params.get('anio')
        vehiculo_id = request.query_params.get('vehiculo_id')
        if anio:        qs = qs.filter(fecha_programada__year=int(anio))
        if mes:         qs = qs.filter(fecha_programada__month=int(mes))
        if vehiculo_id: qs = qs.filter(vehiculo_id=int(vehiculo_id))

        headers = ['Vehículo', 'Tipo', 'Estado', 'Fecha Programada', 'Fecha Realizada', 'Costo', 'Taller']
        rows = [
            [
                _label_vehiculo(m.vehiculo),
                m.tipo_mantencion or '',
                m.estado,
                m.fecha_programada.strftime('%d/%m/%Y') if m.fecha_programada else '',
                m.fecha_realizada.strftime('%d/%m/%Y')  if m.fecha_realizada  else '',
                int(m.costo or 0),
                m.taller_proveedor or '',
            ]
            for m in qs.order_by('-fecha_programada')
        ]
        suffix = f"_{anio}" if anio else ''
        return _xlsx_response(headers, rows, f'reporte_mantenciones{suffix}.xlsx', 'Mantenciones')

    elif tipo == 'flota':
        vehiculos = Vehiculo.objects.filter(
            empresa=empresa, activo=True
        ).prefetch_related(
            'docs_v', 'mantenciones', 'asignaciones__conductor'
        )

        headers = [
            'Patente', 'Marca', 'Modelo', 'Año',
            'KM', 'Conductor', 'Docs Vencidos',
            'Última Mantención', 'Costo Total Mantenciones',
        ]
        rows = []
        for v in vehiculos:
            asig          = v.asignaciones.filter(activo=True).first()
            conductor     = asig.conductor.nombre if asig and asig.conductor else ''
            docs_vencidos = sum(1 for d in v.docs_v.all() if d.estado() == 'vencido')
            ultima        = v.mantenciones.filter(estado='realizada').order_by('-fecha_realizada').first()
            costo_total   = int(v.mantenciones.filter(estado='realizada').aggregate(t=Sum('costo'))['t'] or 0)
            rows.append([
                v.patente, v.marca, v.modelo, v.anio or '',
                v.km_actuales or 0, conductor,
                docs_vencidos,
                ultima.fecha_realizada.strftime('%d/%m/%Y') if ultima and ultima.fecha_realizada else '',
                costo_total,
            ])
        return _xlsx_response(headers, rows, 'reporte_flota.xlsx', 'Estado de Flota')

    return Response({'error': 'Tipo inválido. Use mantencion o flota.'}, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────
# Reporte global por empresa (SUPERADMIN)
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_admin_empresas(request):
    if not _es_superadmin(request.user):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    anio = int(request.query_params.get('anio', date_cls.today().year))

    empresas = Empresa.objects.filter(estado='activa').select_related('plan')

    data               = []
    total_vehiculos    = 0
    total_mantenciones = 0
    total_costo        = 0

    for e in empresas:
        vehiculos_count   = Vehiculo.objects.filter(empresa=e, activo=True).count()
        conductores_count = e.usuarios.filter(rol=Rol.CONDUCTOR, is_active=True).count()

        mants      = Mantencion.objects.filter(vehiculo__empresa=e, fecha_programada__year=anio)
        mant_count = mants.count()
        costo_mant = int(mants.aggregate(t=Sum('costo'))['t'] or 0)

        docs_vencidos = Documento.objects.filter(
            empresa=e, entidad='vehiculo',
            fecha_vencimiento__lt=date_cls.today(),
        ).count()

        total_vehiculos    += vehiculos_count
        total_mantenciones += mant_count
        total_costo        += costo_mant

        data.append({
            'id':                      e.id,
            'nombre':                  e.nombre,
            'plan':                    e.plan.nombre if e.plan else None,
            'plan_display':            e.plan.get_nombre_display() if e.plan else '—',
            'vehiculos':               vehiculos_count,
            'conductores':             conductores_count,
            'mantenciones_anio':       mant_count,
            'costo_mantenciones_anio': costo_mant,
            'docs_vencidos':           docs_vencidos,
        })

    data.sort(key=lambda x: x['costo_mantenciones_anio'], reverse=True)

    return Response({
        'anio':               anio,
        'total_empresas':     len(data),
        'total_vehiculos':    total_vehiculos,
        'total_mantenciones': total_mantenciones,
        'total_costo':        total_costo,
        'empresas':           data,
    })


# ─────────────────────────────────────────
# Reporte TCO (costo total por vehículo)
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_tco(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'finanzas.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    anio = request.query_params.get('anio')
    mes  = request.query_params.get('mes')

    vehiculos_qs = Vehiculo.objects.filter(
        empresa=empresa
    ).prefetch_related('asignaciones__conductor')

    resultados = []
    for v in vehiculos_qs:
        qs_gastos = GastoOperativo.objects.filter(empresa=empresa, vehiculo=v)
        if anio: qs_gastos = qs_gastos.filter(fecha__year=int(anio))
        if mes:  qs_gastos = qs_gastos.filter(fecha__month=int(mes))

        gastos_total = int(qs_gastos.aggregate(t=Sum('monto'))['t'] or 0)
        gastos_cat   = {}
        for row in qs_gastos.values('categoria').annotate(s=Sum('monto')):
            gastos_cat[row['categoria']] = int(row['s'])

        qs_mant = Mantencion.objects.filter(vehiculo=v, estado='realizada')
        if anio: qs_mant = qs_mant.filter(fecha_programada__year=int(anio))
        if mes:  qs_mant = qs_mant.filter(fecha_programada__month=int(mes))

        mant_total = int(qs_mant.aggregate(t=Sum('costo'))['t'] or 0)
        mant_count = qs_mant.count()
        tco_total  = gastos_total + mant_total

        asig = v.asignaciones.filter(activo=True).select_related('conductor').first()
        conductor = asig.conductor.nombre if asig else None

        resultados.append({
            'vehiculo_id':       v.id,
            'patente':           v.patente,
            'marca':             v.marca,
            'modelo':            v.modelo,
            'anio_fab':          v.anio,
            'conductor':         conductor,
            'km_actuales':       v.km_actuales,
            'gastos_total':      gastos_total,
            'gastos_cat':        gastos_cat,
            'mantenciones_total': mant_total,
            'mantenciones_count': mant_count,
            'tco_total':         tco_total,
            'costo_por_km':      round(tco_total / v.km_actuales) if v.km_actuales and v.km_actuales > 0 and tco_total > 0 else None,
        })

    resultados.sort(key=lambda x: x['tco_total'], reverse=True)
    total_flota   = sum(r['tco_total'] for r in resultados)
    total_gastos  = sum(r['gastos_total'] for r in resultados)
    total_mant    = sum(r['mantenciones_total'] for r in resultados)

    # Distribución global de gastos por categoría (suma de todos los vehículos)
    categorias_global = {}
    for r in resultados:
        for cat, monto in r['gastos_cat'].items():
            categorias_global[cat] = categorias_global.get(cat, 0) + monto

    return Response({
        'resumen': {
            'total_flota':    total_flota,
            'total_gastos':   total_gastos,
            'total_mant':     total_mant,
            'vehiculos':      len(resultados),
            'costo_promedio': round(total_flota / len(resultados)) if resultados else 0,
        },
        'vehiculos':         resultados,
        'gastos_categoria':  categorias_global,   # dona de distribución
    })


# ─────────────────────────────────────────
# Reporte de conductores
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_conductores(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'conductores.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    conductores_qs = Usuario.objects.filter(
        empresa=empresa, rol=Rol.CONDUCTOR
    ).prefetch_related('asignaciones_conductor__vehiculo')

    hoy = date_cls.today()
    resultados = []

    for c in conductores_qs:
        docs = list(Documento.objects.filter(conductor=c))
        docs_vigentes    = sum(1 for d in docs if d.estado() == 'vigente')
        docs_por_vencer  = sum(1 for d in docs if d.estado() == 'por_vencer')
        docs_vencidos    = sum(1 for d in docs if d.estado() == 'vencido')

        asig = c.asignaciones_conductor.filter(activo=True).select_related('vehiculo').first()
        vehiculo_asignado = str(asig.vehiculo) if asig else None

        gastos = int(GastoOperativo.objects.filter(
            empresa=empresa, conductor=c
        ).aggregate(t=Sum('monto'))['t'] or 0)

        if docs_vencidos:
            estado_docs = 'vencido'
        elif docs_por_vencer:
            estado_docs = 'por_vencer'
        elif docs_vigentes:
            estado_docs = 'vigente'
        else:
            estado_docs = 'sin_docs'

        resultados.append({
            'id':                c.id,
            'nombre':            c.nombre,
            'rut':               c.rut,
            'email':             c.email,
            'vehiculo_asignado': vehiculo_asignado,
            'docs_vigentes':     docs_vigentes,
            'docs_por_vencer':   docs_por_vencer,
            'docs_vencidos':     docs_vencidos,
            'docs_total':        len(docs),
            'gastos_total':      gastos,
            'estado_docs':       estado_docs,
        })

    return Response({
        'resumen': {
            'total':             len(resultados),
            'con_docs_vencidos': sum(1 for r in resultados if r['docs_vencidos'] > 0),
            'sin_vehiculo':      sum(1 for r in resultados if not r['vehiculo_asignado']),
            'sin_docs':          sum(1 for r in resultados if r['docs_total'] == 0),
        },
        'conductores': resultados,
    })


# ─────────────────────────────────────────
# Reporte presupuesto vs gasto real
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_presupuesto(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'finanzas.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    anio = int(request.query_params.get('anio', date_cls.today().year))
    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    resultado = []
    for mes in range(1, 13):
        ppto  = PresupuestoMensual.objects.filter(empresa=empresa, mes=mes, anio=anio).first()
        gasto = GastoOperativo.objects.filter(
            empresa=empresa, fecha__year=anio, fecha__month=mes,
        ).aggregate(total=Sum('monto'))['total'] or 0
        resultado.append({
            'mes':         mes,
            'mes_label':   MESES_ES[mes - 1],
            'anio':        anio,
            'presupuesto': int(ppto.monto) if ppto else 0,
            'gasto_real':  int(gasto),
        })

    return Response({'anio': anio, 'meses': resultado})


# ─────────────────────────────────────────
# Reporte de documentos de flota
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_documentos(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'documentos.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    hoy       = date_cls.today()
    limite_60 = hoy + timedelta(days=60)
    tipos_label = dict(Documento.TODOS_TIPOS)

    docs_qs = Documento.objects.filter(
        entidad='vehiculo',
        vehiculo__empresa=empresa,
        fecha_vencimiento__isnull=False,
    ).select_related('vehiculo').order_by('fecha_vencimiento')

    vigentes   = 0
    por_vencer = 0
    vencidos   = 0
    por_vehiculo = {}
    proximos   = []

    for d in docs_qs:
        est = d.estado()
        if   est == 'vigente':    vigentes   += 1
        elif est == 'por_vencer': por_vencer += 1
        else:                      vencidos   += 1

        vkey = d.vehiculo_id
        if vkey not in por_vehiculo:
            por_vehiculo[vkey] = {
                'vehiculo':   _label_vehiculo(d.vehiculo),
                'documentos': [],
            }
        dias = (d.fecha_vencimiento - hoy).days
        por_vehiculo[vkey]['documentos'].append({
            'tipo':              d.tipo,
            'tipo_display':      tipos_label.get(d.tipo, d.tipo),
            'fecha_vencimiento': d.fecha_vencimiento.isoformat(),
            'estado':            est,
            'dias':              dias,
        })

        if d.fecha_vencimiento <= limite_60:
            proximos.append({
                'vehiculo':          d.vehiculo.patente,
                'tipo_display':      tipos_label.get(d.tipo, d.tipo),
                'fecha_vencimiento': d.fecha_vencimiento.isoformat(),
                'dias':              dias,
                'estado':            est,
            })

    proximos.sort(key=lambda x: x['fecha_vencimiento'])

    return Response({
        'resumen':        {'vigentes': vigentes, 'por_vencer': por_vencer, 'vencidos': vencidos},
        'por_vehiculo':   list(por_vehiculo.values()),
        'proximos_vencer': proximos[:30],
    })


# ─────────────────────────────────────────
# Reporte de combustible
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_combustible(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'finanzas.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    anio = request.query_params.get('anio')
    mes  = request.query_params.get('mes')

    qs = GastoOperativo.objects.filter(empresa=empresa, categoria='combustible')
    if anio: qs = qs.filter(fecha__year=int(anio))
    if mes:  qs = qs.filter(fecha__month=int(mes))

    gasto_total = int(qs.aggregate(t=Sum('monto'))['t'] or 0)

    por_vehiculo_qs = (
        qs.filter(vehiculo__isnull=False)
        .values('vehiculo_id', 'vehiculo__patente', 'vehiculo__marca', 'vehiculo__modelo')
        .annotate(gasto_total=Sum('monto'))
        .order_by('-gasto_total')[:10]
    )
    por_vehiculo = [
        {
            'patente':     r['vehiculo__patente'],
            'vehiculo':    f"{r['vehiculo__marca']} {r['vehiculo__modelo']} · {r['vehiculo__patente']}",
            'gasto_total': int(r['gasto_total']),
        }
        for r in por_vehiculo_qs
    ]

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    hoy = date_cls.today()
    qs_mensual = GastoOperativo.objects.filter(empresa=empresa, categoria='combustible')
    meses_dict = {}
    for r in qs_mensual.values('fecha__year', 'fecha__month').annotate(gasto=Sum('monto')):
        meses_dict[(r['fecha__year'], r['fecha__month'])] = int(r['gasto'])

    por_mes = []
    anio_inicio = hoy.year - 1
    for y in (anio_inicio, hoy.year):
        for m in range(1, 13):
            if y == hoy.year and m > hoy.month:
                break
            por_mes.append({
                'mes':       m,
                'mes_label': MESES_ES[m - 1],
                'anio':      y,
                'gasto':     meses_dict.get((y, m), 0),
            })
    por_mes = por_mes[-12:]

    gastos_con_datos = [p['gasto'] for p in por_mes if p['gasto'] > 0]
    promedio_mes = round(sum(gastos_con_datos) / len(gastos_con_datos)) if gastos_con_datos else 0
    top_vehiculo = por_vehiculo[0]['vehiculo'] if por_vehiculo else None

    return Response({
        'gasto_total':        gasto_total,
        'gasto_promedio_mes': promedio_mes,
        'top_vehiculo':       top_vehiculo,
        'por_vehiculo':       por_vehiculo,
        'por_mes':            por_mes,
    })


# ─────────────────────────────────────────
# Reporte de rutas por mes
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_rutas(request):
    """Rutas completadas vs canceladas por mes (últimos 12 meses)."""
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'rutas.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    hoy    = date_cls.today()
    inicio = date_cls(hoy.year - 1 if hoy.month == 12 else hoy.year, (hoy.month % 12) + 1, 1)

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    rutas_qs = Ruta.objects.filter(
        empresa=empresa,
        estado__in=['finalizado', 'cancelado'],
        fecha_fin__date__gte=inicio,
    )

    meses_dict = {}
    for r in rutas_qs:
        if not r.fecha_fin:
            continue
        key = (r.fecha_fin.year, r.fecha_fin.month)
        if key not in meses_dict:
            meses_dict[key] = {'finalizadas': 0, 'canceladas': 0}
        if r.estado == 'finalizado':
            meses_dict[key]['finalizadas'] += 1
        else:
            meses_dict[key]['canceladas'] += 1

    # Rellenar los 12 meses aunque no haya datos
    resultado = []
    for i in range(12):
        m = (inicio.month + i - 1) % 12 + 1
        a = inicio.year + ((inicio.month + i - 1) // 12)
        d = meses_dict.get((a, m), {'finalizadas': 0, 'canceladas': 0})
        resultado.append({
            'mes_label':   MESES_ES[m - 1],
            'anio':        a,
            'finalizadas': d['finalizadas'],
            'canceladas':  d['canceladas'],
            'total':       d['finalizadas'] + d['canceladas'],
        })

    # KPIs globales
    total_rutas       = Ruta.objects.filter(empresa=empresa).count()
    total_finalizadas = Ruta.objects.filter(empresa=empresa, estado='finalizado').count()
    total_canceladas  = Ruta.objects.filter(empresa=empresa, estado='cancelado').count()
    total_activas     = Ruta.objects.filter(empresa=empresa, estado='activo').count()
    tipos = {}
    for r in Ruta.objects.filter(empresa=empresa).values('tipo'):
        tipos[r['tipo']] = tipos.get(r['tipo'], 0) + 1

    return Response({
        'resumen': {
            'total':       total_rutas,
            'finalizadas': total_finalizadas,
            'canceladas':  total_canceladas,
            'activas':     total_activas,
            'por_tipo':    tipos,
        },
        'por_mes': resultado,
    })


# ─────────────────────────────────────────
# Reporte de solicitudes de conductores
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_solicitudes(request):
    """Solicitudes de conductores por tipo y mes (últimos 12 meses)."""
    user = request.user
    if user.rol == Rol.CONDUCTOR or _sin_permiso(user, 'solicitudes.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    hoy    = date_cls.today()
    inicio = date_cls(hoy.year - 1 if hoy.month == 12 else hoy.year, (hoy.month % 12) + 1, 1)

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    TIPOS    = ['mantencion', 'combustible', 'incidencia', 'documento']

    solicitudes = SolicitudConductor.objects.filter(
        empresa=empresa,
        created_at__date__gte=inicio,
    )

    # Agrupar por mes y tipo
    meses_dict = {}
    for s in solicitudes:
        key = (s.created_at.year, s.created_at.month)
        if key not in meses_dict:
            meses_dict[key] = {t: 0 for t in TIPOS}
        if s.tipo in meses_dict[key]:
            meses_dict[key][s.tipo] += 1

    resultado = []
    for i in range(12):
        m = (inicio.month + i - 1) % 12 + 1
        a = inicio.year + ((inicio.month + i - 1) // 12)
        d = meses_dict.get((a, m), {t: 0 for t in TIPOS})
        resultado.append({
            'mes_label':  MESES_ES[m - 1],
            'anio':       a,
            **{t: d.get(t, 0) for t in TIPOS},
            'total':      sum(d.get(t, 0) for t in TIPOS),
        })

    # Totales por tipo y por estado
    por_tipo   = {t: solicitudes.filter(tipo=t).count() for t in TIPOS}
    por_estado = {}
    for s in solicitudes.values('estado'):
        por_estado[s['estado']] = por_estado.get(s['estado'], 0) + 1

    return Response({
        'resumen': {
            'total':     solicitudes.count(),
            'por_tipo':  por_tipo,
            'por_estado': por_estado,
        },
        'por_mes': resultado,
    })
