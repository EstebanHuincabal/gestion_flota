import os
from datetime import date as date_cls
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Empresa, GastoOperativo, PresupuestoMensual, Vehiculo, Usuario, Rol,
    Mantencion, PlanSuscripcion, CambioPlan, PagoTransbank, Suscripcion,
    TipoNotificacion,
)
from .audit import registrar_log
from .notificaciones import notificar_admins_empresa


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

        # Los gastos correctivos NO se mezclan con el presupuesto normal: tienen
        # su propio módulo (tab "Correctivos"). Aquí se excluyen siempre.
        qs = GastoOperativo.objects.filter(empresa=empresa, es_correctivo=False).select_related(
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
                vehiculo__empresa=empresa,
                fecha_realizada__month=int(mes),
                fecha_realizada__year=int(anio),
                kilometraje_realizado__isnull=False,
            ).aggregate(km=Sum('kilometraje_realizado'))
            total_km = km_data['km'] or 0
            if total_km > 0 and total > 0:
                costo_por_km = round(int(total) / total_km)

        presupuesto_data = None  # se calcula más abajo, tras sumar correctivos

        # Tendencia últimos 6 meses
        from datetime import date as _today_cls
        hoy_t = _today_cls.today()
        MESES_ES_T = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        tendencia_6meses = []
        for i in range(5, -1, -1):
            m_t = hoy_t.month - i
            a_t = hoy_t.year
            if m_t <= 0:
                m_t += 12
                a_t -= 1
            tot_t = GastoOperativo.objects.filter(
                empresa=empresa, es_correctivo=False, fecha__year=a_t, fecha__month=m_t
            ).aggregate(t=Sum('monto'))['t'] or 0
            tendencia_6meses.append({'label': f"{MESES_ES_T[m_t-1]} {str(a_t)[2:]}", 'total': int(tot_t)})

        # Por conductor
        por_conductor = []
        cond_totales = (
            GastoOperativo.objects.filter(empresa=empresa, es_correctivo=False)
            .filter(**({'fecha__month': int(mes), 'fecha__year': int(anio)} if mes and anio else ({'fecha__year': int(anio)} if anio else {})))
            .exclude(conductor__isnull=True)
            .values('conductor_id')
            .annotate(s=Sum('monto'))
            .order_by('-s')
        )
        cond_ids = [r['conductor_id'] for r in cond_totales]
        cond_nombres = {u.id: u.nombre for u in Usuario.objects.filter(id__in=cond_ids)}
        for row in cond_totales:
            por_conductor.append({
                'conductor_id': row['conductor_id'],
                'nombre':       cond_nombres.get(row['conductor_id'], '—'),
                'total':        int(row['s']),
            })

        # Variación vs mes anterior
        variacion_mes_anterior = None
        if mes and anio:
            m_ant = int(mes) - 1 if int(mes) > 1 else 12
            a_ant = int(anio) if int(mes) > 1 else int(anio) - 1
            tot_ant = GastoOperativo.objects.filter(
                empresa=empresa, es_correctivo=False, fecha__month=m_ant, fecha__year=a_ant
            ).aggregate(t=Sum('monto'))['t'] or 0
            variacion_mes_anterior = {
                'total_anterior': int(tot_ant),
                'variacion_pct':  round((float(total) - float(tot_ant)) / float(tot_ant) * 100, 1) if tot_ant > 0 else None,
            }

        # ── Incluir mantenciones realizadas en el período ──────────────
        mant_qs = Mantencion.objects.filter(
            vehiculo__empresa=empresa,
            estado='realizada',
            costo__gt=0,
        ).select_related('vehiculo')
        if mes and anio:
            mant_qs = mant_qs.filter(fecha_realizada__month=int(mes), fecha_realizada__year=int(anio))
        elif anio:
            mant_qs = mant_qs.filter(fecha_realizada__year=int(anio))
        if vid:
            mant_qs = mant_qs.filter(vehiculo_id=vid)
        if cat and cat != 'mantencion':
            mant_qs = mant_qs.none()

        mant_gastos = [
            {
                'id':             f'mant_{m.id}',
                'categoria':      'mantencion',
                'descripcion':    m.tipo_mantencion or 'Mantención',
                'monto':          int(m.costo),
                'fecha':          (m.fecha_realizada or m.fecha_programada).isoformat() if (m.fecha_realizada or m.fecha_programada) else '',
                'vehiculo_id':    m.vehiculo_id,
                'vehiculo':       str(m.vehiculo),
                'conductor_id':   None,
                'conductor':      None,
                'comprobante':    None,
                'registrado_por': None,
                'created_at':     (m.fecha_realizada or m.fecha_programada).isoformat() if (m.fecha_realizada or m.fecha_programada) else '',
                'readonly':       True,
            }
            for m in mant_qs
        ]

        # Sumar al total y por_categoria
        mant_total = sum(g['monto'] for g in mant_gastos)
        if mant_total:
            por_cat['mantencion'] = por_cat.get('mantencion', 0) + mant_total
            total = int(total) + mant_total

        # Sumar a por_vehiculo
        mant_por_veh = {}
        for g in mant_gastos:
            vid_m = g['vehiculo_id']
            if vid_m not in mant_por_veh:
                mant_por_veh[vid_m] = {'vehiculo_id': vid_m, 'patente': g['vehiculo'], 'total': 0}
            mant_por_veh[vid_m]['total'] += g['monto']
        for vid_m, datos in mant_por_veh.items():
            existe = next((v for v in por_vehiculo if v['vehiculo_id'] == vid_m), None)
            if existe:
                existe['total'] += datos['total']
            else:
                por_vehiculo.append(datos)
        por_vehiculo.sort(key=lambda x: x['total'], reverse=True)

        # Sumar mantenciones a tendencia_6meses (consulta independiente del período seleccionado)
        _MESES_CORTO = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        from datetime import date as _d2
        _hoy2 = _d2.today()
        _q_tend = Q()
        for _i in range(5, -1, -1):
            _mt = _hoy2.month - _i
            _at = _hoy2.year
            if _mt <= 0:
                _mt += 12
                _at -= 1
            _q_tend |= Q(fecha_realizada__month=_mt, fecha_realizada__year=_at)
        _mant_tend_map = {}
        for _m in Mantencion.objects.filter(
            vehiculo__empresa=empresa,
            estado='realizada', costo__gt=0, fecha_realizada__isnull=False,
        ).filter(_q_tend):
            _k = (_m.fecha_realizada.month, _m.fecha_realizada.year % 100)
            _mant_tend_map[_k] = _mant_tend_map.get(_k, 0) + int(_m.costo)
        for punto in tendencia_6meses:
            partes = punto['label'].split()
            if len(partes) == 2:
                try:
                    m_idx = _MESES_CORTO.index(partes[0]) + 1
                    _k = (m_idx, int(partes[1]))
                    if _k in _mant_tend_map:
                        punto['total'] += _mant_tend_map[_k]
                except Exception:
                    pass

        lista_gastos = [_gasto_dict(g) for g in qs] + mant_gastos

        # ── Pagos de servicio (PagoTransbank aprobados) ────────────────
        ptb_qs = PagoTransbank.objects.filter(
            empresa=empresa, estado='aprobado',
        ).order_by('-fecha_pago')
        if mes and anio:
            ptb_qs = ptb_qs.filter(fecha_pago__month=int(mes), fecha_pago__year=int(anio))
        elif anio:
            ptb_qs = ptb_qs.filter(fecha_pago__year=int(anio))

        total_servicio = int(ptb_qs.aggregate(t=Sum('monto'))['t'] or 0)
        pagos_servicio = []
        for p in ptb_qs:
            resp = p.respuesta_tb if isinstance(p.respuesta_tb, dict) else {}
            via  = resp.get('via', 'webpay')
            pagos_servicio.append({
                'id':     p.id,
                'monto':  p.monto,
                'fecha':  p.fecha_pago.date().isoformat() if p.fecha_pago else '',
                'plan':   p.plan_nombre or '—',
                'ciclo':  p.ciclo,
                'via':    via,
                'metodo': resp.get('metodo', '') or ('Webpay Plus' if via != 'manual' else 'Manual'),
                'orden':  p.orden_compra or '',
            })

        # Correctivos del período.
        corr_qs = GastoOperativo.objects.filter(empresa=empresa, es_correctivo=True)
        if mes and anio:
            corr_qs = corr_qs.filter(fecha__month=int(mes), fecha__year=int(anio))
        elif anio:
            corr_qs = corr_qs.filter(fecha__year=int(anio))
        if vid:
            corr_qs = corr_qs.filter(vehiculo_id=vid)
        total_correctivos = int(corr_qs.aggregate(t=Sum('monto'))['t'] or 0)

        # Presupuesto: ejecución = gastos normales + mantenciones + correctivos.
        if mes and anio:
            try:
                p = PresupuestoMensual.objects.get(empresa=empresa, mes=int(mes), anio=int(anio))
                total_utilizado = int(total) + total_correctivos
                pct = round(float(total_utilizado) / float(p.monto) * 100) if p.monto > 0 else 0
                presupuesto_data = {'id': p.id, 'monto': int(p.monto), 'utilizado_pct': pct}
            except PresupuestoMensual.DoesNotExist:
                presupuesto_data = None

        return Response({
            'gastos':          lista_gastos,
            'pagos_servicio':  pagos_servicio,
            'total_servicio':  total_servicio,
            'resumen': {
                'total':                 total,
                'por_categoria':         por_cat,
                'por_vehiculo':          por_vehiculo,
                'por_conductor':         por_conductor,
                'costo_por_km':          costo_por_km,
                'presupuesto':           presupuesto_data,
                'tendencia_6meses':      tendencia_6meses,
                'variacion_mes_anterior': variacion_mes_anterior,
                'total_correctivos_mes': total_correctivos,
                'tiene_correctivos':     total_correctivos > 0,
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
            vehiculo = Vehiculo.objects.get(pk=vehiculo_id, empresa=empresa)
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
                    gasto.vehiculo = Vehiculo.objects.get(pk=data['vehiculo_id'], empresa=empresa)
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


class PresupuestoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        puede = (
            _tiene_permiso(request.user, 'finanzas.ver') or
            _tiene_permiso(request.user, 'correctivos.ver')
        )
        if not puede:
            return Response({'error': 'Sin permisos para ver el presupuesto.'}, status=403)
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
        mrr_int = int(mrr)
        arr     = mrr_int * 12

        ingresos_por_plan = []
        for plan in PlanSuscripcion.objects.filter(activo=True).order_by('orden'):
            emps = empresas_con_plan.filter(plan=plan)
            plan_mrr = Decimal(0)
            for e in emps:
                if plan.precio_mensual:
                    plan_mrr += plan.precio_mensual
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
            try:
                estado_sus = e.suscripcion.estado
            except Exception:
                estado_sus = e.estado
            empresas_suscritas.append({
                'empresa_id':         e.id,
                'nombre':             e.nombre,
                'plan':               e.plan.nombre,
                'mrr':                int(_precio_plan(e.plan)),
                'estado_suscripcion': estado_sus,
            })

        # ── Ingresos reales cobrados (PagoTransbank aprobados) ─────────────
        pagos_mes_qs = PagoTransbank.objects.filter(
            estado='aprobado',
            fecha_pago__date__gte=inicio_mes,
        ).select_related('empresa', 'suscripcion')

        cobrado_total     = pagos_mes_qs.aggregate(t=Sum('monto'))['t'] or 0
        cobrado_transbank = pagos_mes_qs.exclude(
            respuesta_tb__via='manual'
        ).aggregate(t=Sum('monto'))['t'] or 0
        cobrado_manual    = pagos_mes_qs.filter(
            respuesta_tb__via='manual'
        ).aggregate(t=Sum('monto'))['t'] or 0

        pagos_fallidos_mes = PagoTransbank.objects.filter(
            estado__in=['rechazado', 'fallido'],
            fecha_pago__date__gte=inicio_mes,
        ).count()

        # Últimos 10 pagos aprobados del mes para la tabla
        pagos_recientes = []
        for p in pagos_mes_qs.order_by('-fecha_pago')[:10]:
            via = (p.respuesta_tb or {}).get('via', 'transbank')
            pagos_recientes.append({
                'empresa':    p.empresa.nombre if p.empresa else '—',
                'plan':       p.plan_nombre or '—',
                'monto':      p.monto,
                'ciclo':      p.ciclo,
                'via':        via,
                'metodo':     (p.respuesta_tb or {}).get('metodo', 'Webpay') if via == 'manual' else 'Webpay Plus',
                'fecha':      p.fecha_pago.strftime('%d/%m/%Y') if p.fecha_pago else '—',
                'orden':      p.orden_compra,
            })

        return Response({
            'mrr':               mrr_int,
            'arr':               arr,
            'churn_rate':        churn_rate,
            'ltv_promedio':      ltv,
            'empresas_activas':  empresas_activas,
            'empresas_pendientes': Suscripcion.objects.filter(estado='pendiente').count(),
            'ingresos_por_plan': ingresos_por_plan,
            'cobrado_mes': {
                'total':      cobrado_total,
                'transbank':  cobrado_transbank,
                'manual':     cobrado_manual,
                'cantidad':   pagos_mes_qs.count(),
            },
            'movimientos_mes': {
                'nuevas_suscripciones': {'cantidad': nuevas.count(),     'mrr_ganado': mrr_ganado},
                'upgrades':             {'cantidad': upgrades.count(),    'mrr_expansion': mrr_expansion},
                'cancelaciones':        {'cantidad': canceladas.count(),  'mrr_perdido': mrr_perdido},
                'pagos_fallidos':       {'cantidad': pagos_fallidos_mes},
            },
            'empresas_suscritas': empresas_suscritas,
            'pagos_recientes':    pagos_recientes,
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

            cambios    = CambioPlan.objects.filter(fecha__date__gte=inicio, fecha__date__lt=fin)
            nuevas     = cambios.filter(plan_antes__isnull=True).count()
            canceladas = cambios.filter(plan_despues__isnull=True).count()

            # Ingresos reales cobrados en ese mes
            cobrado = PagoTransbank.objects.filter(
                estado='aprobado',
                fecha_pago__date__gte=inicio,
                fecha_pago__date__lt=fin,
            ).aggregate(t=Sum('monto'))['t'] or 0

            resultado.append({
                'mes':           mes_num,
                'anio':          anio_num,
                'mrr':           int(mrr_actual),   # MRR teórico actual
                'cobrado':       cobrado,            # Ingresos reales cobrados ese mes
                'nuevas':        nuevas,
                'cancelaciones': canceladas,
            })

        return Response(resultado)


# ═════════════════════════════════════════════════════════════════════════════
# Gastos correctivos no presupuestados
# ═════════════════════════════════════════════════════════════════════════════

# Validación inline del comprobante (no existe file_validators en el proyecto).
_COMPROBANTE_MAX_MB = 10


def _validar_comprobante(archivo):
    """Devuelve un mensaje de error si el archivo no es válido, o None si lo es."""
    if archivo.size > _COMPROBANTE_MAX_MB * 1024 * 1024:
        return f'El archivo no puede superar {_COMPROBANTE_MAX_MB} MB.'
    ct = (archivo.content_type or '')
    if not (ct == 'application/pdf' or ct.startswith('image/')):
        return 'Solo se permiten archivos PDF o imágenes.'
    return None


def _gasto_correctivo_dict(g):
    return {
        'id':                   g.id,
        'vehiculo_id':          g.vehiculo_id,
        'vehiculo_patente':     g.vehiculo.patente if g.vehiculo else None,
        'categoria_correctiva': g.categoria_correctiva,
        'categoria_display':    g.get_categoria_correctiva_display() if g.categoria_correctiva else '',
        'prioridad':            g.prioridad_correctiva,
        'prioridad_display':    g.get_prioridad_correctiva_display() if g.prioridad_correctiva else '',
        'descripcion':          g.descripcion,
        'monto':                int(g.monto),
        'fecha':                g.fecha.isoformat(),
        'comprobante':          g.comprobante.url if g.comprobante else None,
        'tiene_comprobante':    bool(g.comprobante),
        'registrado_por':       g.registrado_por.nombre if g.registrado_por else None,
        'created_at':           g.created_at.isoformat(),
    }


class GastosCorrectivosList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _tiene_permiso(request.user, 'correctivos.ver'):
            return Response({'error': 'Sin permisos para ver correctivos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        mes  = request.query_params.get('mes')
        anio = request.query_params.get('anio')
        vid  = request.query_params.get('vehiculo_id')
        cat  = request.query_params.get('categoria_correctiva')
        prio = request.query_params.get('prioridad')

        base = GastoOperativo.objects.filter(empresa=empresa, es_correctivo=True)
        if mes and anio:
            base = base.filter(fecha__month=int(mes), fecha__year=int(anio))
        elif anio:
            base = base.filter(fecha__year=int(anio))

        qs = base.select_related('vehiculo', 'registrado_por')
        if vid:  qs = qs.filter(vehiculo_id=vid)
        if cat:  qs = qs.filter(categoria_correctiva=cat)
        if prio: qs = qs.filter(prioridad_correctiva=prio)

        gastos = [_gasto_correctivo_dict(g) for g in qs.order_by('-fecha', '-created_at')]
        total_correctivos = int(qs.aggregate(t=Sum('monto'))['t'] or 0)

        # Total NORMAL del período (denominador del impacto): gasto operativo no
        # correctivo. La regla: el impacto se calcula sobre el gasto normal.
        normal_qs = GastoOperativo.objects.filter(empresa=empresa, es_correctivo=False)
        if mes and anio:
            normal_qs = normal_qs.filter(fecha__month=int(mes), fecha__year=int(anio))
        elif anio:
            normal_qs = normal_qs.filter(fecha__year=int(anio))
        total_normal = int(normal_qs.aggregate(t=Sum('monto'))['t'] or 0)
        impacto = round(total_correctivos / total_normal * 100) if total_normal > 0 else 0

        # Por categoría correctiva.
        por_categoria = []
        for row in qs.values('categoria_correctiva').annotate(s=Sum('monto')).order_by('-s'):
            code  = row['categoria_correctiva']
            label = dict(GastoOperativo.CATEGORIAS_CORRECTIVAS).get(code, code)
            tot   = int(row['s'])
            por_categoria.append({
                'categoria': code, 'label': label, 'total': tot,
                'pct': round(tot / total_correctivos * 100) if total_correctivos else 0,
            })

        # Por vehículo: correctivo vs normal del período.
        corr_por_veh = {r['vehiculo_id']: int(r['s'])
                        for r in qs.values('vehiculo_id').annotate(s=Sum('monto'))}
        norm_por_veh = {r['vehiculo_id']: int(r['s'])
                        for r in normal_qs.values('vehiculo_id').annotate(s=Sum('monto'))}
        veh_ids = {i for i in (set(corr_por_veh) | set(norm_por_veh)) if i}
        veh_map = {v.id: v for v in Vehiculo.objects.filter(id__in=veh_ids)}
        por_vehiculo = []
        for vidk in veh_ids:
            v = veh_map.get(vidk)
            por_vehiculo.append({
                'vehiculo_id':      vidk,
                'patente':          v.patente if v else '—',
                'total_correctivo': corr_por_veh.get(vidk, 0),
                'total_normal':     norm_por_veh.get(vidk, 0),
            })
        por_vehiculo.sort(key=lambda x: x['total_correctivo'], reverse=True)
        vehiculo_top = None
        if por_vehiculo and por_vehiculo[0]['total_correctivo'] > 0:
            vehiculo_top = {
                'vehiculo_id': por_vehiculo[0]['vehiculo_id'],
                'patente':     por_vehiculo[0]['patente'],
                'total':       por_vehiculo[0]['total_correctivo'],
            }

        # Evolución últimos 6 meses (siempre 6 puntos).
        _MS = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        hoy = date_cls.today()
        evolucion = []
        for i in range(5, -1, -1):
            m_e = hoy.month - i; a_e = hoy.year
            if m_e <= 0: m_e += 12; a_e -= 1
            tc = int(GastoOperativo.objects.filter(
                empresa=empresa, es_correctivo=True, fecha__month=m_e, fecha__year=a_e
            ).aggregate(t=Sum('monto'))['t'] or 0)
            tn = int(GastoOperativo.objects.filter(
                empresa=empresa, es_correctivo=False, fecha__month=m_e, fecha__year=a_e
            ).aggregate(t=Sum('monto'))['t'] or 0)
            evolucion.append({'mes': f"{_MS[m_e-1]} {str(a_e)[2:]}",
                              'total_correctivo': tc, 'total_normal': tn})

        presupuesto_mensual = None
        if mes and anio:
            try:
                p = PresupuestoMensual.objects.get(empresa=empresa, mes=int(mes), anio=int(anio))
                presupuesto_mensual = {'id': p.id, 'monto': int(p.monto)}
            except PresupuestoMensual.DoesNotExist:
                pass

        return Response({
            'gastos': gastos,
            'resumen': {
                'total_correctivos':     total_correctivos,
                'total_normal':          total_normal,
                'impacto_porcentaje':    impacto,
                'vehiculo_mas_afectado': vehiculo_top,
                'por_categoria':         por_categoria,
                'por_vehiculo':          por_vehiculo,
                'evolucion_mensual':     evolucion,
                'presupuesto_mensual':   presupuesto_mensual,
            },
        })

    def post(self, request):
        if not _tiene_permiso(request.user, 'correctivos.crear'):
            return Response({'error': 'Sin permisos para registrar correctivos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)

        d = request.data
        try:
            monto = int(d.get('monto') or 0)
        except (TypeError, ValueError):
            return Response({'error': 'Monto inválido.'}, status=400)
        if monto <= 0:
            return Response({'error': 'El monto debe ser mayor a 0.'}, status=400)

        cat = (d.get('categoria_correctiva') or '').strip()
        if cat not in dict(GastoOperativo.CATEGORIAS_CORRECTIVAS):
            return Response({'error': 'Categoría correctiva inválida.'}, status=400)
        prio = (d.get('prioridad_correctiva') or '').strip()
        if prio and prio not in dict(GastoOperativo.PRIORIDADES):
            return Response({'error': 'Prioridad inválida.'}, status=400)

        try:
            fecha = date_cls.fromisoformat((d.get('fecha') or '').strip())
        except ValueError:
            return Response({'error': 'Fecha inválida.'}, status=400)
        if fecha > date_cls.today():
            return Response({'error': 'La fecha no puede ser futura.'}, status=400)

        vehiculo = Vehiculo.objects.filter(pk=d.get('vehiculo_id'), empresa=empresa).first()
        if not vehiculo:
            return Response({'error': 'Vehículo no encontrado en esta empresa.'}, status=404)

        descripcion = (d.get('descripcion') or '').strip()
        if len(descripcion) < 10:
            return Response({'error': 'La descripción debe tener al menos 10 caracteres.'}, status=400)
        if len(descripcion) > 200:
            return Response({'error': 'La descripción no puede superar los 200 caracteres.'}, status=400)

        gasto = GastoOperativo.objects.create(
            empresa=empresa, vehiculo=vehiculo,
            categoria='mantencion',          # los correctivos siempre son de mantención
            es_correctivo=True,
            categoria_correctiva=cat,
            prioridad_correctiva=prio,
            descripcion=descripcion,
            monto=monto, fecha=fecha,
            registrado_por=request.user,
        )

        archivo = request.FILES.get('comprobante')
        if archivo:
            err = _validar_comprobante(archivo)
            if err:
                gasto.delete()
                return Response({'error': err}, status=400)
            gasto.comprobante = archivo
            gasto.save(update_fields=['comprobante'])

        registrar_log('ACTIVIDAD', 'gasto_correctivo_registrado', request, detalle={
            'gasto_id': gasto.id, 'patente': vehiculo.patente, 'monto': monto, 'categoria': cat,
        })
        try:
            monto_fmt = f"{monto:,}".replace(',', '.')
            notificar_admins_empresa(
                empresa, TipoNotificacion.ACTIVIDAD,
                f'Nuevo gasto correctivo: {vehiculo.patente}',
                f'Se registró un gasto correctivo de ${monto_fmt} por {descripcion}.',
                url_accion='/empresa/finanzas',
                extra={'gasto_id': gasto.id},
                permiso='correctivos.ver',
            )
        except Exception:
            pass

        return Response(_gasto_correctivo_dict(gasto), status=201)


class GastoCorrectivoDetail(APIView):
    permission_classes = [IsAuthenticated]

    def _obtener(self, request):
        empresa = _get_empresa(request)
        return empresa

    def _gasto(self, request, gasto_id):
        empresa = _get_empresa(request)
        if not empresa:
            return None
        return (GastoOperativo.objects
                .filter(pk=gasto_id, empresa=empresa, es_correctivo=True)
                .select_related('vehiculo', 'registrado_por').first())

    def get(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'correctivos.ver'):
            return Response({'error': 'Sin permisos.'}, status=403)
        g = self._gasto(request, gasto_id)
        if not g:
            return Response({'error': 'Gasto no encontrado.'}, status=404)
        return Response(_gasto_correctivo_dict(g))

    def put(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'correctivos.editar'):
            return Response({'error': 'Sin permisos.'}, status=403)
        g = self._gasto(request, gasto_id)
        if not g:
            return Response({'error': 'Gasto no encontrado.'}, status=404)

        d = request.data
        if 'monto' in d:
            try:
                m = int(d['monto'])
            except (TypeError, ValueError):
                return Response({'error': 'Monto inválido.'}, status=400)
            if m <= 0:
                return Response({'error': 'El monto debe ser mayor a 0.'}, status=400)
            g.monto = m
        if 'fecha' in d:
            try:
                f = date_cls.fromisoformat(str(d['fecha']))
            except ValueError:
                return Response({'error': 'Fecha inválida.'}, status=400)
            if f > date_cls.today():
                return Response({'error': 'La fecha no puede ser futura.'}, status=400)
            g.fecha = f
        if 'categoria_correctiva' in d:
            c = (d['categoria_correctiva'] or '').strip()
            if c not in dict(GastoOperativo.CATEGORIAS_CORRECTIVAS):
                return Response({'error': 'Categoría correctiva inválida.'}, status=400)
            g.categoria_correctiva = c
        if 'prioridad_correctiva' in d:
            p = (d['prioridad_correctiva'] or '').strip()
            if p and p not in dict(GastoOperativo.PRIORIDADES):
                return Response({'error': 'Prioridad inválida.'}, status=400)
            g.prioridad_correctiva = p
        if 'descripcion' in d:
            desc = (d['descripcion'] or '').strip()
            if len(desc) < 10:
                return Response({'error': 'La descripción debe tener al menos 10 caracteres.'}, status=400)
            if len(desc) > 200:
                return Response({'error': 'La descripción no puede superar los 200 caracteres.'}, status=400)
            g.descripcion = desc

        g.save()
        registrar_log('ACTIVIDAD', 'gasto_correctivo_editado', request, detalle={'gasto_id': g.id})
        return Response(_gasto_correctivo_dict(g))

    def delete(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'correctivos.eliminar'):
            return Response({'error': 'Sin permisos.'}, status=403)
        g = self._gasto(request, gasto_id)
        if not g:
            return Response({'error': 'Gasto no encontrado.'}, status=404)
        if g.comprobante:
            try:
                g.comprobante.delete(save=False)
            except Exception:
                pass
        gid = g.id
        g.delete()
        registrar_log('ACTIVIDAD', 'gasto_correctivo_eliminado', request, detalle={'gasto_id': gid})
        return Response({'ok': True})


class GastoCorrectivoComprobante(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, gasto_id):
        if not _tiene_permiso(request.user, 'correctivos.editar'):
            return Response({'error': 'Sin permisos.'}, status=403)
        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'Empresa no encontrada.'}, status=400)
        g = GastoOperativo.objects.filter(pk=gasto_id, empresa=empresa, es_correctivo=True).first()
        if not g:
            return Response({'error': 'Gasto no encontrado.'}, status=404)
        archivo = request.FILES.get('comprobante')
        if not archivo:
            return Response({'error': 'No se envió ningún archivo.'}, status=400)
        err = _validar_comprobante(archivo)
        if err:
            return Response({'error': err}, status=400)
        if g.comprobante:
            try:
                g.comprobante.delete(save=False)
            except Exception:
                pass
        g.comprobante = archivo
        g.save(update_fields=['comprobante'])
        registrar_log('ACTIVIDAD', 'gasto_correctivo_editado', request, detalle={'gasto_id': g.id, 'comprobante': True})
        return Response(_gasto_correctivo_dict(g))
