import csv
import os
from datetime import date as date_cls
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Empresa, GastoOperativo, PresupuestoMensual, Vehiculo, Usuario, Rol,
    Mantencion, PlanSuscripcion, CambioPlan,
)
from .audit import registrar_log


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
        eid = (
            request.query_params.get('empresa_id')
            or request.data.get('empresa_id')
        )
        if eid:
            try:
                return Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                return None
        return None
    return request.user.empresa


def _gasto_dict(g):
    return {
        'id':             g.id,
        'categoria':      g.categoria,
        'descripcion':    g.descripcion,
        'monto':          int(g.monto),
        'fecha':          g.fecha.isoformat(),
        'vehiculo_id':    g.vehiculo_id,
        'vehiculo':       str(g.vehiculo) if g.vehiculo else None,
        'conductor_id':   g.conductor_id,
        'conductor':      g.conductor.nombre if g.conductor else None,
        'comprobante':    g.comprobante.url if g.comprobante else None,
        'registrado_por': g.registrado_por.nombre if g.registrado_por else None,
        'created_at':     g.created_at.isoformat(),
    }


class GastosListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _tiene_permiso(request.user, 'finanzas.ver'):
            return Response({'error': 'Sin permisos para ver finanzas.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        mes  = request.query_params.get('mes')
        anio = request.query_params.get('anio')
        cat  = request.query_params.get('categoria')
        vid  = request.query_params.get('vehiculo_id')
        cid  = request.query_params.get('conductor_id')

        qs = GastoOperativo.objects.filter(empresa=empresa).select_related(
            'vehiculo', 'conductor', 'registrado_por'
        )

        if mes and anio:
            qs = qs.filter(fecha__month=int(mes), fecha__year=int(anio))
        elif anio:
            qs = qs.filter(fecha__year=int(anio))
        if cat:
            qs = qs.filter(categoria=cat)
        if vid:
            qs = qs.filter(vehiculo_id=vid)
        if cid:
            qs = qs.filter(conductor_id=cid)

        total = qs.aggregate(t=Sum('monto'))['t'] or Decimal(0)

        por_cat = {}
        for row in qs.values('categoria').annotate(s=Sum('monto')):
            por_cat[row['categoria']] = int(row['s'])

        por_vehiculo = []
        for row in (
            qs.values('vehiculo_id', 'vehiculo__patente')
              .annotate(s=Sum('monto'))
              .order_by('-s')
        ):
            por_vehiculo.append({
                'vehiculo_id': row['vehiculo_id'],
                'patente':     row['vehiculo__patente'] or '—',
                'total':       int(row['s']),
            })

        costo_por_km = None
        if mes and anio:
            km_data = Mantencion.objects.filter(
                vehiculo__flota__empresa=empresa,
                fecha_realizada__month=int(mes),
                fecha_realizada__year=int(anio),
                kilometraje_realizado__isnull=False,
            ).aggregate(km=Sum('kilometraje_realizado'))
            total_km = km_data['km'] or 0
            if total_km > 0 and total > 0:
                costo_por_km = round(int(total) / total_km)

        presupuesto_data = None
        if mes and anio:
            try:
                p = PresupuestoMensual.objects.get(empresa=empresa, mes=int(mes), anio=int(anio))
                pct = round(float(total) / float(p.monto) * 100) if p.monto > 0 else 0
                presupuesto_data = {'id': p.id, 'monto': int(p.monto), 'utilizado_pct': pct}
            except PresupuestoMensual.DoesNotExist:
                presupuesto_data = None

        return Response({
            'gastos': [_gasto_dict(g) for g in qs],
            'resumen': {
                'total':         int(total),
                'por_categoria': por_cat,
                'por_vehiculo':  por_vehiculo,
                'costo_por_km':  costo_por_km,
                'presupuesto':   presupuesto_data,
            },
        })

    def post(self, request):
        if not _tiene_permiso(request.user, 'finanzas.crear'):
            return Response({'error': 'Sin permisos para registrar gastos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        if request.user.rol == Rol.SUPERADMIN:
            return Response({'error': 'El SUPERADMIN no puede registrar gastos.'}, status=403)

        data = request.data
        categoria   = data.get('categoria', '')
        descripcion = data.get('descripcion', '')
        monto       = data.get('monto')
        fecha_str   = data.get('fecha')
        vehiculo_id = data.get('vehiculo_id')
        conductor_id = data.get('conductor_id')

        if not all([categoria, descripcion, monto, fecha_str, vehiculo_id]):
            return Response({'error': 'Faltan campos requeridos.'}, status=400)

        try:
            monto_val = Decimal(str(monto))
            if monto_val <= 0:
                raise ValueError
        except Exception:
            return Response({'error': 'Monto inválido.'}, status=400)

        try:
            fecha = date_cls.fromisoformat(fecha_str)
        except ValueError:
            return Response({'error': 'Fecha inválida.'}, status=400)

        if fecha > date_cls.today():
            return Response({'error': 'La fecha no puede ser futura.'}, status=400)

        try:
            vehiculo = Vehiculo.objects.get(pk=vehiculo_id, flota__empresa=empresa)
        except Vehiculo.DoesNotExist:
            return Response({'error': 'Vehículo no encontrado.'}, status=404)

        conductor = None
        if conductor_id:
            try:
                conductor = Usuario.objects.get(pk=conductor_id, empresa=empresa, rol=Rol.CONDUCTOR)
            except Usuario.DoesNotExist:
                pass

        gasto = GastoOperativo(
            empresa=empresa,
            vehiculo=vehiculo,
            conductor=conductor,
            categoria=categoria,
            descripcion=descripcion,
            monto=monto_val,
            fecha=fecha,
            registrado_por=request.user,
        )

        if 'comprobante' in request.FILES:
            gasto.comprobante = request.FILES['comprobante']

        gasto.save()

        registrar_log('ACTIVIDAD', 'gasto_creado', request, detalle={
            'gasto_id': gasto.id, 'monto': str(monto_val), 'categoria': categoria,
        })
        return Response(_gasto_dict(gasto), status=201)


class GastoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, gasto_id, empresa):
        try:
            return GastoOperativo.objects.select_related(
                'vehiculo', 'conductor', 'registrado_por'
            ).get(pk=gasto_id, empresa=empresa)
        except GastoOperativo.DoesNotExist:
            return None

    def get(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'finanzas.ver'):
            return Response({'error': 'Sin permisos para ver finanzas.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        gasto = self._get(gasto_id, empresa)
        if not gasto:
            return Response({'error': 'Gasto no encontrado.'}, status=404)
        return Response(_gasto_dict(gasto))

    def put(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'finanzas.editar'):
            return Response({'error': 'Sin permisos para editar gastos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        gasto = self._get(gasto_id, empresa)
        if not gasto:
            return Response({'error': 'Gasto no encontrado.'}, status=404)

        if request.user != gasto.registrado_por and request.user.rol != Rol.SUPERADMIN:
            return Response({'error': 'Sin permisos para editar este gasto.'}, status=403)

        data = request.data
        for campo in ['categoria', 'descripcion']:
            if campo in data:
                setattr(gasto, campo, data[campo])
        if 'monto' in data:
            try:
                gasto.monto = Decimal(str(data['monto']))
            except Exception:
                return Response({'error': 'Monto inválido.'}, status=400)
        if 'fecha' in data:
            try:
                gasto.fecha = date_cls.fromisoformat(data['fecha'])
            except ValueError:
                return Response({'error': 'Fecha inválida.'}, status=400)
        if 'vehiculo_id' in data:
            if data['vehiculo_id']:
                try:
                    gasto.vehiculo = Vehiculo.objects.get(pk=data['vehiculo_id'], flota__empresa=empresa)
                except Vehiculo.DoesNotExist:
                    return Response({'error': 'Vehículo no encontrado.'}, status=404)
            else:
                gasto.vehiculo = None
        if 'comprobante' in request.FILES:
            if gasto.comprobante:
                try:
                    os.remove(gasto.comprobante.path)
                except Exception:
                    pass
            gasto.comprobante = request.FILES['comprobante']

        gasto.save()
        registrar_log('ACTIVIDAD', 'gasto_editado', request, detalle={'gasto_id': gasto.id})
        return Response(_gasto_dict(gasto))

    def delete(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'finanzas.eliminar'):
            return Response({'error': 'Sin permisos para eliminar gastos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        gasto = self._get(gasto_id, empresa)
        if not gasto:
            return Response({'error': 'Gasto no encontrado.'}, status=404)

        if request.user != gasto.registrado_por and request.user.rol != Rol.SUPERADMIN:
            return Response({'error': 'Sin permisos para eliminar este gasto.'}, status=403)

        if gasto.comprobante:
            try:
                os.remove(gasto.comprobante.path)
            except Exception:
                pass

        registrar_log('ACTIVIDAD', 'gasto_eliminado', request, detalle={
            'gasto_id': gasto.id, 'categoria': gasto.categoria, 'monto': str(gasto.monto),
        })
        gasto.delete()
        return Response(status=204)


class GastosExportarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _tiene_permiso(request.user, 'finanzas.exportar'):
            return Response({'error': 'Sin permisos para exportar datos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        mes  = request.query_params.get('mes')
        anio = request.query_params.get('anio')
        fmt  = request.query_params.get('formato', 'csv')

        qs = GastoOperativo.objects.filter(empresa=empresa).select_related('vehiculo', 'conductor')
        if mes and anio:
            qs = qs.filter(fecha__month=int(mes), fecha__year=int(anio))
        elif anio:
            qs = qs.filter(fecha__year=int(anio))

        if fmt != 'csv':
            return Response({'error': 'Formato no soportado. Use formato=csv'}, status=400)

        periodo = f"{anio}_{mes}" if mes else str(anio or 'todos')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="gastos_{periodo}.csv"'
        response.write('﻿')  # BOM para Excel

        writer = csv.writer(response)
        writer.writerow(['Fecha', 'Categoría', 'Descripción', 'Vehículo', 'Conductor', 'Monto'])

        totales = {}
        for g in qs:
            cat_label = dict(GastoOperativo.CATEGORIAS).get(g.categoria, g.categoria)
            writer.writerow([
                g.fecha.strftime('%d/%m/%Y'),
                cat_label,
                g.descripcion,
                str(g.vehiculo) if g.vehiculo else '',
                g.conductor.nombre if g.conductor else '',
                int(g.monto),
            ])
            totales[cat_label] = totales.get(cat_label, 0) + int(g.monto)

        writer.writerow([])
        writer.writerow(['TOTALES POR CATEGORÍA'])
        for cat, total in totales.items():
            writer.writerow(['', cat, '', '', '', total])
        writer.writerow(['TOTAL GENERAL', '', '', '', '', sum(totales.values())])

        return response


class PresupuestoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _tiene_permiso(request.user, 'finanzas.ver'):
            return Response({'error': 'Sin permisos para ver finanzas.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        mes  = request.query_params.get('mes')
        anio = request.query_params.get('anio')

        qs = PresupuestoMensual.objects.filter(empresa=empresa)
        if mes:
            qs = qs.filter(mes=int(mes))
        if anio:
            qs = qs.filter(anio=int(anio))

        return Response([
            {'id': p.id, 'mes': p.mes, 'anio': p.anio, 'monto': int(p.monto)}
            for p in qs
        ])

    def post(self, request):
        if not _tiene_permiso(request.user, 'finanzas.presupuesto'):
            return Response({'error': 'Sin permisos para gestionar presupuesto.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        mes   = request.data.get('mes')
        anio  = request.data.get('anio')
        monto = request.data.get('monto')

        if not all([mes, anio, monto]):
            return Response({'error': 'Faltan campos requeridos.'}, status=400)

        try:
            monto_val = Decimal(str(monto))
            if monto_val <= 0:
                raise ValueError
        except Exception:
            return Response({'error': 'Monto inválido.'}, status=400)

        p, created = PresupuestoMensual.objects.update_or_create(
            empresa=empresa, mes=int(mes), anio=int(anio),
            defaults={'monto': monto_val},
        )
        registrar_log(
            'ACTIVIDAD',
            'presupuesto_creado' if created else 'presupuesto_editado',
            request,
            detalle={'mes': mes, 'anio': anio, 'monto': str(monto_val)},
        )
        return Response(
            {'id': p.id, 'mes': p.mes, 'anio': p.anio, 'monto': int(p.monto)},
            status=201 if created else 200,
        )


class PresupuestoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not _tiene_permiso(request.user, 'finanzas.presupuesto'):
            return Response({'error': 'Sin permisos para gestionar presupuesto.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        try:
            p = PresupuestoMensual.objects.get(pk=pk, empresa=empresa)
        except PresupuestoMensual.DoesNotExist:
            return Response({'error': 'Presupuesto no encontrado.'}, status=404)

        if 'monto' in request.data:
            try:
                p.monto = Decimal(str(request.data['monto']))
            except Exception:
                return Response({'error': 'Monto inválido.'}, status=400)
        p.save()
        registrar_log('ACTIVIDAD', 'presupuesto_editado', request,
                      detalle={'presupuesto_id': pk, 'monto': str(p.monto)})
        return Response({'id': p.id, 'mes': p.mes, 'anio': p.anio, 'monto': int(p.monto)})


# ─────────────────────────────────────────
# Dashboard SaaS — SUPERADMIN
# ─────────────────────────────────────────

class FinanzasSaasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol != Rol.SUPERADMIN:
            return Response({'error': 'Sin permisos.'}, status=403)

        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)

        empresas_con_plan = Empresa.objects.filter(
            estado='activa', plan__isnull=False
        ).select_related('plan')
        empresas_activas = Empresa.objects.filter(estado='activa').count()

        mrr = Decimal(0)
        for e in empresas_con_plan:
            if e.plan.precio_mensual:
                mrr += e.plan.precio_mensual
            elif e.plan.precio_anual:
                mrr += e.plan.precio_anual / 12
        mrr_int = int(mrr)
        arr     = mrr_int * 12

        ingresos_por_plan = []
        for plan in PlanSuscripcion.objects.filter(activo=True).order_by('orden'):
            emps = empresas_con_plan.filter(plan=plan)
            plan_mrr = Decimal(0)
            for e in emps:
                if plan.precio_mensual:
                    plan_mrr += plan.precio_mensual
                elif plan.precio_anual:
                    plan_mrr += plan.precio_anual / 12
            ingresos_por_plan.append({
                'plan':     plan.nombre,
                'empresas': emps.count(),
                'mrr':      int(plan_mrr),
                'pct':      round(int(plan_mrr) / mrr_int * 100) if mrr_int > 0 else 0,
            })

        cambios_mes = CambioPlan.objects.filter(
            fecha__date__gte=inicio_mes
        ).select_related('plan_antes', 'plan_despues')

        nuevas     = cambios_mes.filter(plan_antes__isnull=True,  plan_despues__isnull=False)
        canceladas = cambios_mes.filter(plan_despues__isnull=True)
        upgrades   = cambios_mes.filter(plan_antes__isnull=False, plan_despues__isnull=False)

        def _precio_plan(p):
            if not p:
                return Decimal(0)
            if p.precio_mensual:
                return p.precio_mensual
            if p.precio_anual:
                return p.precio_anual / 12
            return Decimal(0)

        mrr_ganado    = sum(int(_precio_plan(c.plan_despues)) for c in nuevas)
        mrr_perdido   = sum(int(_precio_plan(c.plan_antes))   for c in canceladas)
        mrr_expansion = sum(
            max(0, int(_precio_plan(c.plan_despues)) - int(_precio_plan(c.plan_antes)))
            for c in upgrades
        )

        churn_rate = 0.0
        if empresas_activas > 0:
            churn_rate = round(canceladas.count() / empresas_activas * 100, 1)

        precio_prom = mrr_int / empresas_activas if empresas_activas > 0 else 0
        churn_dec   = churn_rate / 100
        ltv         = int(precio_prom / churn_dec) if churn_dec > 0 else 0

        empresas_suscritas = []
        for e in empresas_con_plan.order_by('-id'):
            empresas_suscritas.append({
                'empresa_id':         e.id,
                'nombre':             e.nombre,
                'plan':               e.plan.nombre,
                'mrr':                int(_precio_plan(e.plan)),
                'estado_suscripcion': e.estado,
            })

        return Response({
            'mrr':               mrr_int,
            'arr':               arr,
            'churn_rate':        churn_rate,
            'ltv_promedio':      ltv,
            'empresas_activas':  empresas_activas,
            'empresas_trial':    0,
            'ingresos_por_plan': ingresos_por_plan,
            'movimientos_mes': {
                'nuevas_suscripciones': {'cantidad': nuevas.count(),     'mrr_ganado': mrr_ganado},
                'upgrades':             {'cantidad': upgrades.count(),    'mrr_expansion': mrr_expansion},
                'cancelaciones':        {'cantidad': canceladas.count(),  'mrr_perdido': mrr_perdido},
                'pagos_fallidos':       {'cantidad': 0},
            },
            'empresas_suscritas': empresas_suscritas,
        })


class FinanzasHistoricoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol != Rol.SUPERADMIN:
            return Response({'error': 'Sin permisos.'}, status=403)

        meses_count = int(request.query_params.get('meses', 12))
        hoy = timezone.now().date()

        empresas_con_plan = Empresa.objects.filter(
            estado='activa', plan__isnull=False
        ).select_related('plan')
        mrr_actual = Decimal(0)
        for e in empresas_con_plan:
            if e.plan.precio_mensual:
                mrr_actual += e.plan.precio_mensual
            elif e.plan.precio_anual:
                mrr_actual += e.plan.precio_anual / 12

        resultado = []
        for i in range(meses_count - 1, -1, -1):
            mes_num  = hoy.month - i
            anio_num = hoy.year
            while mes_num <= 0:
                mes_num  += 12
                anio_num -= 1

            try:
                inicio = hoy.replace(day=1, month=mes_num, year=anio_num)
                if mes_num == 12:
                    fin = inicio.replace(year=anio_num + 1, month=1)
                else:
                    fin = inicio.replace(month=mes_num + 1)
            except ValueError:
                continue

            cambios   = CambioPlan.objects.filter(fecha__date__gte=inicio, fecha__date__lt=fin)
            nuevas    = cambios.filter(plan_antes__isnull=True).count()
            canceladas = cambios.filter(plan_despues__isnull=True).count()

            resultado.append({
                'mes':          mes_num,
                'anio':         anio_num,
                'mrr':          int(mrr_actual),
                'nuevas':       nuevas,
                'cancelaciones': canceladas,
            })

        return Response(resultado)
