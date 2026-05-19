import csv
from datetime import date as date_cls

from django.db.models import Sum
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Empresa, Vehiculo, Mantencion, DocumentoVehiculo, Rol,
    GastoOperativo, Documento, Usuario,
)


def _es_superadmin(user):
    return getattr(user, 'rol', None) == Rol.SUPERADMIN


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
    if user.rol == Rol.CONDUCTOR:
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa
    ).select_related('vehiculo', 'vehiculo__flota')

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
    if user.rol == Rol.CONDUCTOR:
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    vehiculos = Vehiculo.objects.filter(
        flota__empresa=empresa, activo=True
    ).select_related('flota').prefetch_related(
        'documentos', 'mantenciones', 'asignaciones__conductor'
    )

    vehiculos_data    = []
    con_docs_vencidos = 0
    sin_conductor     = 0

    for v in vehiculos:
        asig      = v.asignaciones.filter(activo=True).first()
        conductor = asig.conductor.nombre if asig and asig.conductor else None
        if not conductor:
            sin_conductor += 1

        docs_vigentes   = sum(1 for d in v.documentos.all() if d.estado == 'vigente')
        docs_por_vencer = sum(1 for d in v.documentos.all() if d.estado == 'por_vencer')
        docs_vencidos   = sum(1 for d in v.documentos.all() if d.estado == 'vencido')
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
            'flota':                    v.flota.nombre,
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

    if tipo == 'mantencion':
        qs = Mantencion.objects.filter(
            vehiculo__flota__empresa=empresa
        ).select_related('vehiculo')

        mes         = request.query_params.get('mes')
        anio        = request.query_params.get('anio')
        vehiculo_id = request.query_params.get('vehiculo_id')
        if anio:        qs = qs.filter(fecha_programada__year=int(anio))
        if mes:         qs = qs.filter(fecha_programada__month=int(mes))
        if vehiculo_id: qs = qs.filter(vehiculo_id=int(vehiculo_id))

        suffix   = f"_{anio}" if anio else ''
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="reporte_mantenciones{suffix}.csv"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow([
            'Vehículo', 'Tipo', 'Estado',
            'Fecha Programada', 'Fecha Realizada', 'Costo', 'Taller',
        ])
        for m in qs.order_by('-fecha_programada'):
            writer.writerow([
                _label_vehiculo(m.vehiculo),
                m.tipo_mantencion or '',
                m.estado,
                m.fecha_programada.isoformat() if m.fecha_programada else '',
                m.fecha_realizada.isoformat()  if m.fecha_realizada  else '',
                int(m.costo or 0),
                m.taller_proveedor or '',
            ])
        return response

    elif tipo == 'flota':
        vehiculos = Vehiculo.objects.filter(
            flota__empresa=empresa, activo=True
        ).select_related('flota').prefetch_related(
            'documentos', 'mantenciones', 'asignaciones__conductor'
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reporte_flota.csv"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow([
            'Patente', 'Marca', 'Modelo', 'Año', 'Flota',
            'KM', 'Conductor', 'Docs Vencidos',
            'Última Mantención', 'Costo Total Mantenciones',
        ])
        for v in vehiculos:
            asig          = v.asignaciones.filter(activo=True).first()
            conductor     = asig.conductor.nombre if asig and asig.conductor else ''
            docs_vencidos = sum(1 for d in v.documentos.all() if d.estado == 'vencido')
            ultima        = v.mantenciones.filter(estado='realizada').order_by('-fecha_realizada').first()
            costo_total   = int(v.mantenciones.filter(estado='realizada').aggregate(t=Sum('costo'))['t'] or 0)
            writer.writerow([
                v.patente, v.marca, v.modelo, v.anio or '',
                v.flota.nombre, v.km_actuales or 0, conductor,
                docs_vencidos,
                ultima.fecha_realizada.isoformat() if ultima and ultima.fecha_realizada else '',
                costo_total,
            ])
        return response

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
        vehiculos_count   = Vehiculo.objects.filter(flota__empresa=e, activo=True).count()
        conductores_count = e.usuarios.filter(rol=Rol.CONDUCTOR, is_active=True).count()
        flotas_count      = e.flotas.count()

        mants      = Mantencion.objects.filter(vehiculo__flota__empresa=e, fecha_programada__year=anio)
        mant_count = mants.count()
        costo_mant = int(mants.aggregate(t=Sum('costo'))['t'] or 0)

        docs_vencidos = DocumentoVehiculo.objects.filter(
            vehiculo__flota__empresa=e, estado='vencido'
        ).count()

        total_vehiculos    += vehiculos_count
        total_mantenciones += mant_count
        total_costo        += costo_mant

        data.append({
            'id':                      e.id,
            'nombre':                  e.nombre,
            'plan':                    e.plan.nombre if e.plan else None,
            'plan_display':            e.plan.get_nombre_display() if e.plan else '—',
            'flotas':                  flotas_count,
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
    if user.rol == Rol.CONDUCTOR:
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = _get_empresa(user, request.query_params)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

    anio = request.query_params.get('anio')
    mes  = request.query_params.get('mes')

    vehiculos_qs = Vehiculo.objects.filter(
        flota__empresa=empresa
    ).select_related('flota').prefetch_related('asignaciones__conductor')

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
            'flota':             v.flota.nombre,
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

    return Response({
        'resumen': {
            'total_flota':    total_flota,
            'total_gastos':   total_gastos,
            'total_mant':     total_mant,
            'vehiculos':      len(resultados),
            'costo_promedio': round(total_flota / len(resultados)) if resultados else 0,
        },
        'vehiculos': resultados,
    })


# ─────────────────────────────────────────
# Reporte de conductores
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_conductores(request):
    user = request.user
    if user.rol == Rol.CONDUCTOR:
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
