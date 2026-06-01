import json
import hashlib
import logging

logger = logging.getLogger(__name__)
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Max, Subquery, OuterRef, IntegerField, Q, Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Coalesce
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from decimal import Decimal

from .models import (
    Empresa, Rol, Permiso, Usuario, Flota, Vehiculo, Asignacion,
    Mantencion, Documento, LogAuditoria, normalizar_rut, TipoLog, PlanSuscripcion,
    TipoNotificacion, CambioPlan, GastoOperativo, PresupuestoMensual, MantencionProgramada,
    Suscripcion,
    Ruta,
)
from .views_planes import verificar_limite_plan, verificar_modulo_plan
from .audit import registrar_log, _diff_campos, _snap
from .notificaciones import notificar, notificar_admins_empresa
from .firebase_push import enviar_push
from .serializers import (
    EmpresaSerializer,
    PermisoSerializer,
    UsuarioListSerializer,
    UsuarioCrearSerializer,
    UsuarioEditarSerializer,
    ConductorListSerializer,
    ConductorDetalleSerializer,
    ConductorCrearSerializer,
    ConductorEditarSerializer,
    FlotaSerializer,
    VehiculoSerializer,
    VehiculoResumenSerializer,
    MantencionSerializer,
    PlanSuscripcionSerializer,
    LogAuditoriaSerializer
)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def es_superadmin(user):
    return getattr(user, 'rol', None) == Rol.SUPERADMIN

def tiene_permiso(user, codigo: str) -> bool:
    rol = getattr(user, 'rol', None)
    if rol == Rol.SUPERADMIN:
        return True
    if rol == Rol.CONDUCTOR:
        return False
    plan = getattr(user.empresa, 'plan', None) if user.empresa_id else None
    if not plan:
        return False
    return plan.permisos.filter(codigo=codigo).exists()

def get_empresa(request):
    user = request.user
    if user.rol == Rol.SUPERADMIN:
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            raise PermissionError
        try:
            return Empresa.objects.get(pk=empresa_id)
        except Empresa.DoesNotExist:
            raise PermissionError
    if not user.empresa_id:
        raise PermissionError
    return user.empresa


# ─────────────────────────────────────────
# Auth & Dashboard Global
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_global_view(request):
    if not es_superadmin(request.user):
        return Response({"detail": "No tienes permiso para ver este dashboard."}, status=403)

    periodo = request.query_params.get('periodo', '12m')
    if periodo not in ('7d', '30d', '3m', '6m', '12m'):
        periodo = '12m'

    now = timezone.now()

    # KPIs
    empresas_activas     = Empresa.objects.filter(estado='activa').count()
    empresas_inactivas   = Empresa.objects.filter(estado='suspendida').count()
    total_usuarios       = Usuario.objects.filter(rol__in=[Rol.USUARIO, Rol.CONDUCTOR]).count()
    total_conductores    = Usuario.objects.filter(rol=Rol.CONDUCTOR).count()
    total_vehiculos      = Vehiculo.objects.count()
    empresas_nuevas_mes  = Empresa.objects.filter(created_at__year=now.year, created_at__month=now.month).count()
    usuarios_activos_hoy = Usuario.objects.filter(last_login__date=now.date()).count()

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    # Gráfico 1: Crecimiento de empresas (granularidad según periodo)
    if periodo in ('7d', '30d'):
        days = 7 if periodo == '7d' else 30
        desde = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = (
            Empresa.objects.filter(created_at__gte=desde)
            .annotate(dia=TruncDay('created_at'))
            .values('dia').annotate(total=Count('id')).order_by('dia')
        )
        data_map = {r['dia'].date(): r['total'] for r in rows if r['dia']}
        crecimiento_labels, crecimiento_values = [], []
        for i in range(days):
            d = (desde + timedelta(days=i)).date()
            crecimiento_labels.append(f"{d.day:02d} {MESES_ES[d.month - 1]}")
            crecimiento_values.append(data_map.get(d, 0))

    elif periodo in ('3m', '6m'):
        weeks = 13 if periodo == '3m' else 26
        desde = now - timedelta(weeks=weeks)
        rows = (
            Empresa.objects.filter(created_at__gte=desde)
            .annotate(semana=TruncWeek('created_at'))
            .values('semana').annotate(total=Count('id')).order_by('semana')
        )
        data_map = {r['semana'].date(): r['total'] for r in rows if r['semana']}
        crecimiento_labels, crecimiento_values = [], []
        cursor = desde - timedelta(days=desde.weekday())
        cursor = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        while cursor.date() <= now.date():
            d = cursor.date()
            crecimiento_labels.append(f"{d.day:02d} {MESES_ES[d.month - 1]}")
            crecimiento_values.append(data_map.get(d, 0))
            cursor += timedelta(weeks=1)

    else:  # 12m — granularidad mensual
        hace_12_meses = now - timedelta(days=365)
        rows = (
            Empresa.objects.filter(created_at__gte=hace_12_meses)
            .annotate(mes=TruncMonth('created_at'))
            .values('mes').annotate(total=Count('id')).order_by('mes')
        )
        meses_data = {}
        curr = now.replace(day=1)
        for _ in range(12):
            meses_data[curr.strftime("%Y-%m")] = 0
            if curr.month == 1:
                curr = curr.replace(year=curr.year - 1, month=12)
            else:
                curr = curr.replace(month=curr.month - 1)
        for r in rows:
            if r['mes']:
                ms = r['mes'].strftime("%Y-%m")
                if ms in meses_data:
                    meses_data[ms] = r['total']
        crecimiento_labels, crecimiento_values = [], []
        for k in reversed(list(meses_data.keys())):
            y, m = k.split('-')
            crecimiento_labels.append(f"{MESES_ES[int(m) - 1]} {y[2:]}")
            crecimiento_values.append(meses_data[k])

    # Gráfico 2: Distribución por tamaño de flota (snapshot actual)
    empresas_flota = Empresa.objects.annotate(num_vehiculos=Count('flotas__vehiculos'))
    distribucion_flota = {"0 vehículos": 0, "1-5 vehículos": 0, "6-10 vehículos": 0, "+10 vehículos": 0}
    for e in empresas_flota:
        n = e.num_vehiculos
        if n == 0:
            distribucion_flota["0 vehículos"] += 1
        elif n <= 5:
            distribucion_flota["1-5 vehículos"] += 1
        elif n <= 10:
            distribucion_flota["6-10 vehículos"] += 1
        else:
            distribucion_flota["+10 vehículos"] += 1

    # Gráfico 3: Top 5 empresas por vehículos
    top_empresas = Empresa.objects.annotate(num_vehiculos=Count('flotas__vehiculos')).order_by('-num_vehiculos')[:5]
    top_empresas_data = [{"nombre": e.nombre, "vehiculos": e.num_vehiculos} for e in top_empresas]

    # ── Nuevos datos globales ────────────────────────────────────

    # Distribución de empresas por plan
    distribucion_planes = []
    for plan in PlanSuscripcion.objects.filter(activo=True).order_by('orden'):
        n = Empresa.objects.filter(estado='activa', plan=plan).count()
        distribucion_planes.append({'plan': plan.nombre, 'empresas': n})

    # Empresas sin actividad en los últimos 30 días (sin mantenciones)
    hace_30 = now - timedelta(days=30)
    sin_actividad = []
    for e in Empresa.objects.filter(estado='activa').order_by('nombre'):
        tiene_act = Mantencion.objects.filter(
            vehiculo__flota__empresa=e, fecha_programada__gte=hace_30,
        ).exists()
        if not tiene_act:
            sin_actividad.append({'id': e.id, 'nombre': e.nombre})
        if len(sin_actividad) >= 8:
            break

    # MRR actual vs mes anterior (aproximación: empresas existentes antes del mes)
    def _calc_mrr(empresas_qs):
        total = Decimal(0)
        for e in empresas_qs.filter(plan__isnull=False).select_related('plan'):
            p = e.plan
            if p.precio_mensual:
                total += p.precio_mensual
        return int(total)

    inicio_mes  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mrr_actual  = _calc_mrr(Empresa.objects.filter(estado='activa'))
    mrr_ant_qs  = Empresa.objects.filter(estado='activa', created_at__lt=inicio_mes)
    mrr_anterior = _calc_mrr(mrr_ant_qs)
    mrr_variacion = (
        round((mrr_actual - mrr_anterior) / mrr_anterior * 100, 1)
        if mrr_anterior > 0 else None
    )

    # Distribución combustible de toda la flota
    COMBUSTIBLE_LABELS = {
        'bencina': 'Bencina', 'diesel': 'Diésel',
        'electrico': 'Eléctrico', 'hibrido': 'Híbrido', 'gas': 'Gas',
    }
    dist_comb_qs = (
        Vehiculo.objects.values('tipo_combustible')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    distribucion_combustible = [
        {'label': COMBUSTIBLE_LABELS.get(r['tipo_combustible'], r['tipo_combustible']), 'total': r['total']}
        for r in dist_comb_qs if r['total'] > 0
    ]

    # Top 10 empresas por vehículos (para bar chart)
    top_empresas_10 = Empresa.objects.annotate(num_vehiculos=Count('flotas__vehiculos')).order_by('-num_vehiculos')[:10]
    top_empresas_bar = [{"nombre": e.nombre, "vehiculos": e.num_vehiculos} for e in top_empresas_10]

    # ── S1: MRR histórico 12 meses ───────────────────────────────
    mrr_hist_labels, mrr_hist_data = [], []
    for i in range(11, -1, -1):
        dm = now.month - i
        mes_obj = now.replace(
            year=now.year - 1 if dm <= 0 else now.year,
            month=(dm + 12 if dm <= 0 else dm),
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )
        fin_mes = (mes_obj + timedelta(days=32)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        mrr_mes = _calc_mrr(Empresa.objects.filter(created_at__lt=fin_mes, estado='activa'))
        mrr_hist_labels.append(f"{MESES_ES[mes_obj.month - 1]} {str(mes_obj.year)[2:]}")
        mrr_hist_data.append(mrr_mes)

    # ── S2: Usuarios nuevos por mes (12 meses) ───────────────────
    hace_12m = now - timedelta(days=365)
    rows_usu = (
        Usuario.objects.filter(rol__in=[Rol.USUARIO, Rol.CONDUCTOR], date_joined__gte=hace_12m)
        .annotate(mes=TruncMonth('date_joined'))
        .values('mes').annotate(total=Count('id')).order_by('mes')
    )
    usu_map = {r['mes'].strftime('%Y-%m'): r['total'] for r in rows_usu if r['mes']}
    usu_labels, usu_data = [], []
    curr_usu = now.replace(day=1)
    meses_usu = []
    for _ in range(12):
        meses_usu.append(curr_usu.strftime('%Y-%m'))
        curr_usu = (curr_usu - timedelta(days=1)).replace(day=1)
    for k in reversed(meses_usu):
        y, m = k.split('-')
        usu_labels.append(f"{MESES_ES[int(m)-1]} {y[2:]}")
        usu_data.append(usu_map.get(k, 0))

    # ── S3: Top 8 empresas con más alertas predictivas vencidas ──
    alertas_glob_qs = (
        MantencionProgramada.objects
        .filter(estado='activa', fecha_siguiente__lte=now.date())
        .values('vehiculo__flota__empresa__nombre')
        .annotate(alertas=Count('id'))
        .order_by('-alertas')[:8]
    )
    empresas_alertas = [
        {'nombre': r['vehiculo__flota__empresa__nombre'], 'alertas': r['alertas']}
        for r in alertas_glob_qs
    ]

    # ── S4: Top 10 marcas de vehículos en toda la plataforma ─────
    top_marcas_qs = (
        Vehiculo.objects.values('marca')
        .annotate(total=Count('id')).order_by('-total')[:10]
    )
    top_marcas_global = [
        {'marca': r['marca'] or 'Sin marca', 'total': r['total']}
        for r in top_marcas_qs
    ]

    # ── S5: Usuarios activos últimos 30 días (por día) ───────────
    hace_30 = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows_activos = (
        Usuario.objects.filter(last_login__gte=hace_30)
        .annotate(dia=TruncDay('last_login'))
        .values('dia').annotate(total=Count('id')).order_by('dia')
    )
    activos_map = {r['dia'].date(): r['total'] for r in rows_activos if r['dia']}
    activos_labels, activos_data = [], []
    for i in range(30):
        d = (hace_30 + timedelta(days=i)).date()
        activos_labels.append(f"{d.day:02d} {MESES_ES[d.month - 1]}")
        activos_data.append(activos_map.get(d, 0))

    return Response({
        "kpis": {
            "empresas_activas":    empresas_activas,
            "empresas_inactivas":  empresas_inactivas,
            "total_usuarios":      total_usuarios,
            "total_conductores":   total_conductores,
            "total_vehiculos":     total_vehiculos,
            "empresas_nuevas_mes": empresas_nuevas_mes,
            "usuarios_activos_hoy": usuarios_activos_hoy,
            "mrr_actual":          mrr_actual,
            "mrr_variacion":       mrr_variacion,
        },
        "charts": {
            "crecimiento": {"labels": crecimiento_labels, "data": crecimiento_values},
            "distribucion_flota": {
                "labels": list(distribucion_flota.keys()),
                "data":   list(distribucion_flota.values()),
            },
            "top_empresas":             top_empresas_data,
            "distribucion_planes":      distribucion_planes,
            "distribucion_combustible": distribucion_combustible,
            "top_empresas_bar":         top_empresas_bar,
            "mrr_historico":   {"labels": mrr_hist_labels, "data": mrr_hist_data},
            "usuarios_nuevos": {"labels": usu_labels,      "data": usu_data},
            "activos_30d":     {"labels": activos_labels,  "data": activos_data},
            "top_marcas_global": top_marcas_global,
        },
        "sin_actividad":    sin_actividad,
        "empresas_alertas": empresas_alertas,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def empresa_dashboard_view(request):
    if request.user.rol == Rol.CONDUCTOR:
        return Response({"detail": "Sin permisos."}, status=403)

    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=403)

    periodo = request.query_params.get('periodo', '12m')
    if periodo not in ('7d', '30d', '3m', '6m', '12m'):
        periodo = '12m'

    hoy = timezone.now().date()
    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    # ── Permisos de dashboard por categoría ──────────────────────
    p_flota       = tiene_permiso(request.user, 'dashboard.flota')
    p_mant        = tiene_permiso(request.user, 'dashboard.mantenimiento')
    p_finanzas    = tiene_permiso(request.user, 'dashboard.finanzas')
    p_docs        = tiene_permiso(request.user, 'dashboard.documentos')
    p_rutas       = tiene_permiso(request.user, 'dashboard.rutas')
    p_conductores = tiene_permiso(request.user, 'dashboard.conductores')

    # Sin ningún permiso → panel vacío con indicador
    if not any([p_flota, p_mant, p_finanzas, p_docs, p_rutas, p_conductores]):
        return Response({
            "sin_acceso": True,
            "kpis": {}, "charts": {}, "widgets": {},
            "permisos_dashboard": {
                "flota": False, "mantenimiento": False, "finanzas": False,
                "documentos": False, "rutas": False, "conductores": False,
            },
        })

    # ── Pre-cómputos compartidos ──────────────────────────────────
    total_vehiculos = Vehiculo.objects.filter(flota__empresa=empresa).count()
    mant_pend = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa, estado='pendiente').count() if p_mant or p_flota else 0
    docs_pv = Documento.objects.filter(
        entidad='vehiculo', vehiculo__flota__empresa=empresa,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=30),
    ).count() if p_docs or p_flota else 0

    # ── KPIs (según permiso) ──────────────────────────────────────
    kpis = {}
    if p_flota:
        kpis['total_flotas']    = Flota.objects.filter(empresa=empresa).count()
        kpis['total_vehiculos'] = total_vehiculos
    if p_conductores:
        kpis['total_conductores'] = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR).count()
    if p_mant:
        kpis['mantenciones_pendientes'] = mant_pend
    if p_docs:
        kpis['docs_por_vencer'] = docs_pv

    charts = {}

    # ── FLOTA ─────────────────────────────────────────────────────
    if p_flota:
        flotas_qs = (
            Flota.objects.filter(empresa=empresa)
            .annotate(num_vehiculos=Count('vehiculos'))
            .order_by('-num_vehiculos')
        )
        charts['vehiculos_por_flota'] = {
            'labels': [f.nombre for f in flotas_qs],
            'data':   [f.num_vehiculos for f in flotas_qs],
        }
        charts['estado_flota'] = {
            'sin_alerta':     max(0, total_vehiculos - docs_pv - mant_pend),
            'docs_vencer':    docs_pv,
            'mant_pendiente': mant_pend,
        }
        marcas_qs = (
            Vehiculo.objects.filter(flota__empresa=empresa)
            .values('marca').annotate(total=Count('id')).order_by('-total')[:8]
        )
        charts['marcas_flota'] = [
            {'marca': r['marca'] or 'Sin marca', 'total': r['total']}
            for r in marcas_qs
        ]

    # ── MANTENIMIENTO ─────────────────────────────────────────────
    if p_mant:
        if periodo in ('7d', '30d'):
            days = 7 if periodo == '7d' else 30
            desde = hoy - timedelta(days=days - 1)
            rows = (
                Mantencion.objects.filter(
                    vehiculo__flota__empresa=empresa,
                    fecha_programada__gte=desde,
                    fecha_programada__lte=hoy,
                )
                .annotate(dia=TruncDay('fecha_programada'))
                .values('dia').annotate(total=Count('id')).order_by('dia')
            )
            data_map = {r['dia']: r['total'] for r in rows if r['dia']}
            mant_labels, mant_values = [], []
            for i in range(days):
                d = desde + timedelta(days=i)
                mant_labels.append(f"{d.day:02d} {MESES_ES[d.month - 1]}")
                mant_values.append(data_map.get(d, 0))
        elif periodo in ('3m', '6m'):
            weeks = 13 if periodo == '3m' else 26
            desde = hoy - timedelta(weeks=weeks)
            rows = (
                Mantencion.objects.filter(
                    vehiculo__flota__empresa=empresa,
                    fecha_programada__gte=desde,
                    fecha_programada__lte=hoy,
                )
                .annotate(semana=TruncWeek('fecha_programada'))
                .values('semana').annotate(total=Count('id')).order_by('semana')
            )
            data_map = {r['semana']: r['total'] for r in rows if r['semana']}
            mant_labels, mant_values = [], []
            cursor = desde - timedelta(days=desde.weekday())
            while cursor <= hoy:
                mant_labels.append(f"{cursor.day:02d} {MESES_ES[cursor.month - 1]}")
                mant_values.append(data_map.get(cursor, 0))
                cursor += timedelta(days=7)
        else:
            hace_12 = hoy - timedelta(days=365)
            rows = (
                Mantencion.objects.filter(
                    vehiculo__flota__empresa=empresa,
                    fecha_programada__gte=hace_12,
                    fecha_programada__lte=hoy,
                )
                .annotate(mes=TruncMonth('fecha_programada'))
                .values('mes').annotate(total=Count('id')).order_by('mes')
            )
            meses_data = {}
            curr = hoy.replace(day=1)
            for _ in range(12):
                meses_data[curr.strftime('%Y-%m')] = 0
                curr = (curr - timedelta(days=1)).replace(day=1)
            for r in rows:
                if r['mes']:
                    ms = r['mes'].strftime('%Y-%m')
                    if ms in meses_data:
                        meses_data[ms] = r['total']
            mant_labels, mant_values = [], []
            for k in reversed(list(meses_data.keys())):
                y, m = k.split('-')
                mant_labels.append(f"{MESES_ES[int(m) - 1]} {y[2:]}")
                mant_values.append(meses_data[k])

        charts['mantenciones'] = {'labels': mant_labels, 'data': mant_values}
        charts['mant_por_estado'] = {
            estado: Mantencion.objects.filter(
                vehiculo__flota__empresa=empresa, estado=estado
            ).count()
            for estado in ['pendiente', 'en_proceso', 'completada', 'cancelada']
        }
        alertas_qs = (
            MantencionProgramada.objects
            .filter(vehiculo__flota__empresa=empresa, estado='activa',
                    fecha_siguiente__lte=hoy)
            .values('regla__tipo').annotate(total=Count('id')).order_by('-total')[:6]
        )
        charts['alertas_por_tipo'] = [
            {'tipo': r['regla__tipo'] or 'General', 'total': r['total']}
            for r in alertas_qs
        ]

    # ── FINANZAS ──────────────────────────────────────────────────
    if p_finanzas:
        CATS_GASTO = ['combustible', 'mantencion', 'seguro', 'multa', 'otro']
        g6_labels, g6_ds = [], {c: [] for c in CATS_GASTO}
        g12_labels, g12_data = [], []
        for i in range(11, -1, -1):
            dm = hoy.month - i
            mes_obj = hoy.replace(year=hoy.year - 1 if dm <= 0 else hoy.year,
                                   month=(dm + 12 if dm <= 0 else dm), day=1)
            lbl = f"{MESES_ES[mes_obj.month - 1]} {str(mes_obj.year)[2:]}"
            g12_labels.append(lbl)
            total_mes = GastoOperativo.objects.filter(
                empresa=empresa, fecha__year=mes_obj.year, fecha__month=mes_obj.month,
            ).aggregate(t=Sum('monto'))['t'] or 0
            g12_data.append(int(total_mes))
            if i < 6:
                g6_labels.append(lbl)
                for cat in CATS_GASTO:
                    tc = GastoOperativo.objects.filter(
                        empresa=empresa, fecha__year=mes_obj.year,
                        fecha__month=mes_obj.month, categoria=cat,
                    ).aggregate(t=Sum('monto'))['t'] or 0
                    g6_ds[cat].append(int(tc))
        charts['gastos_6m']  = {'labels': g6_labels,  'datasets': {c: g6_ds[c] for c in CATS_GASTO}}
        charts['gastos_12m'] = {'labels': g12_labels, 'data': g12_data}

    # ── DOCUMENTOS ────────────────────────────────────────────────
    if p_docs:
        charts['docs_por_estado'] = {
            'vigentes':   Documento.objects.filter(
                entidad='vehiculo', vehiculo__flota__empresa=empresa,
                fecha_vencimiento__gt=hoy + timedelta(days=30),
            ).count(),
            'por_vencer': docs_pv,
            'vencidos':   Documento.objects.filter(
                entidad='vehiculo', vehiculo__flota__empresa=empresa,
                fecha_vencimiento__lt=hoy,
            ).count(),
        }

    # ── RUTAS ─────────────────────────────────────────────────────
    if p_rutas:
        r_labels, r_fin, r_can, r_km = [], [], [], []
        for i in range(5, -1, -1):
            dm = hoy.month - i
            mes_obj = hoy.replace(year=hoy.year - 1 if dm <= 0 else hoy.year,
                                   month=(dm + 12 if dm <= 0 else dm), day=1)
            r_labels.append(f"{MESES_ES[mes_obj.month - 1]} {str(mes_obj.year)[2:]}")
            base = Ruta.objects.filter(
                empresa=empresa, fecha_fin__year=mes_obj.year, fecha_fin__month=mes_obj.month)
            r_fin.append(base.filter(estado='finalizado').count())
            r_can.append(base.filter(estado='cancelado').count())
            r_km.append(float(base.filter(estado='finalizado').aggregate(
                t=Sum('distancia_km'))['t'] or 0))
        charts['rutas_6m']   = {'labels': r_labels, 'finalizadas': r_fin, 'canceladas': r_can}
        charts['km_por_mes'] = {'labels': r_labels, 'data': r_km}

    # ── CONDUCTORES ───────────────────────────────────────────────
    if p_conductores:
        top_qs = (
            Ruta.objects.filter(empresa=empresa, estado='finalizado', conductor__isnull=False)
            .values('conductor_id').annotate(total_km=Sum('distancia_km')).order_by('-total_km')[:5]
        )
        cond_ids = [r['conductor_id'] for r in top_qs]
        cond_map = {u.id: u for u in Usuario.objects.filter(id__in=cond_ids)}
        charts['top_conductores_km'] = [
            {'nombre': cond_map[r['conductor_id']].nombre or f"Conductor {r['conductor_id']}",
             'km': float(r['total_km'] or 0)}
            for r in top_qs if r['conductor_id'] in cond_map
        ]

    # ── Widgets ───────────────────────────────────────────────────
    widgets = {}

    if p_mant:
        proximas_qs = Mantencion.objects.filter(
            vehiculo__flota__empresa=empresa,
            estado__in=['pendiente', 'en_proceso'],
            fecha_programada__gte=hoy,
            fecha_programada__lte=hoy + timedelta(days=7),
        ).select_related('vehiculo').order_by('fecha_programada')[:5]
        widgets['proximas_7_dias'] = [
            {'id': m.id,
             'vehiculo': f"{m.vehiculo.marca} {m.vehiculo.modelo} · {m.vehiculo.patente}",
             'tipo': m.tipo_mantencion, 'fecha': m.fecha_programada.isoformat(), 'estado': m.estado}
            for m in proximas_qs
        ]
        planes_act  = MantencionProgramada.objects.filter(vehiculo__flota__empresa=empresa, estado='activa')
        pred_al_dia   = planes_act.filter(fecha_siguiente__gt=hoy).count()
        pred_vencidas = planes_act.filter(fecha_siguiente__lte=hoy).count()
        pred_total    = pred_al_dia + pred_vencidas
        widgets['predictivo'] = {
            'al_dia': pred_al_dia, 'vencidas': pred_vencidas,
            'total': pred_total,
            'pct': round(pred_al_dia / pred_total * 100) if pred_total else 100,
        }

    if p_finanzas:
        gasto_mes = GastoOperativo.objects.filter(
            empresa=empresa, fecha__year=hoy.year, fecha__month=hoy.month,
        ).aggregate(t=Sum('monto'))['t'] or 0
        try:
            presup = PresupuestoMensual.objects.get(empresa=empresa, mes=hoy.month, anio=hoy.year)
            pct = round(float(gasto_mes) / float(presup.monto) * 100) if presup.monto > 0 else None
            widgets['gasto_vs_presupuesto'] = {
                'gasto': int(gasto_mes), 'presupuesto': int(presup.monto), 'pct': pct}
        except PresupuestoMensual.DoesNotExist:
            widgets['gasto_vs_presupuesto'] = {'gasto': int(gasto_mes), 'presupuesto': None, 'pct': None}

        top_veh_qs = (
            GastoOperativo.objects.filter(
                empresa=empresa, fecha__year=hoy.year, fecha__month=hoy.month,
                vehiculo__isnull=False,
            )
            .values('vehiculo_id', 'vehiculo__patente', 'vehiculo__marca', 'vehiculo__modelo')
            .annotate(total=Sum('monto')).order_by('-total')[:3]
        )
        widgets['top_vehiculos_costo'] = [
            {'vehiculo_id': v['vehiculo_id'], 'patente': v['vehiculo__patente'],
             'label': f"{v['vehiculo__marca']} {v['vehiculo__modelo']}", 'total': int(v['total'])}
            for v in top_veh_qs
        ]

    return Response({
        "permisos_dashboard": {
            "flota":        p_flota,
            "mantenimiento": p_mant,
            "finanzas":     p_finanzas,
            "documentos":   p_docs,
            "rutas":        p_rutas,
            "conductores":  p_conductores,
        },
        "kpis":    kpis,
        "charts":  charts,
        "widgets": widgets,
    })


def home_view(request):
    return JsonResponse({
        "status": "API Running",
        "message": "Backend de Gestión de Flota",
        "endpoints": {"login": "/api/login/"},
    })


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    rut      = data.get("rut", "").strip()
    password = data.get("password", "")

    if not rut or not password:
        return JsonResponse({"error": "RUT y contraseña son requeridos"}, status=400)

    # 1. Buscar usuario para chequear bloqueos e intentos fallidos
    rut_hash = hashlib.sha256(normalizar_rut(rut).encode()).hexdigest()
    user_obj = Usuario.objects.filter(rut_hash=rut_hash).first()

    if user_obj and user_obj.is_blocked:
        return JsonResponse({
            "error": "Cuenta bloqueada por seguridad debido a demasiados intentos fallidos. Contacta a un administrador."
        }, status=403)

    # 2. Intentar autenticar
    user = authenticate(request, rut=rut, password=password)
    ip   = request.META.get('REMOTE_ADDR')

    if user is None:
        if user_obj:
            user_obj.intentos_fallidos += 1
            if user_obj.intentos_fallidos >= 5:
                user_obj.is_blocked = True
            user_obj.save()
            registrar_log('SEGURIDAD', 'login_fallido', request, usuario=user_obj,
                          detalle={'intentos': user_obj.intentos_fallidos, 'bloqueado': user_obj.is_blocked})
            if user_obj.is_blocked:
                notificar(user_obj, TipoNotificacion.SEGURIDAD,
                          "Cuenta bloqueada",
                          "Tu cuenta fue bloqueada por exceso de intentos fallidos. Contacta a un administrador.",
                          url_accion='')
                for superadmin in Usuario.objects.filter(rol=Rol.SUPERADMIN, is_active=True):
                    notificar(superadmin, TipoNotificacion.SEGURIDAD,
                              f"Cuenta bloqueada: {user_obj.nombre or user_obj.email}",
                              f"La cuenta de '{user_obj.nombre or user_obj.email}' fue bloqueada automáticamente por {user_obj.intentos_fallidos} intentos fallidos desde IP {ip}.",
                              url_accion='/usuarios')
        else:
            registrar_log('SEGURIDAD', 'login_fallido', request,
                          detalle={'motivo': 'usuario_no_encontrado'})

        return JsonResponse({"error": "Credenciales inválidas"}, status=401)

    # 3. Éxito: Resetear intentos y registrar acceso
    user.intentos_fallidos = 0
    user.save()
    registrar_log('SEGURIDAD', 'login_exitoso', request, usuario=user)

    refresh = RefreshToken.for_user(user)

    plan_modulos  = []
    plan_nombre   = ''
    plan_permisos = []
    if user.empresa and user.empresa.plan:
        plan = user.empresa.plan
        plan_modulos  = plan.modulos or []
        plan_nombre   = plan.get_nombre_display()
        plan_permisos = list(plan.permisos.values_list('codigo', flat=True))

    # Vehículo asignado (para la app de conductores)
    vehiculo_asignado = None
    if user.rol == 'CONDUCTOR':
        from .models import Asignacion
        asignacion = Asignacion.objects.filter(conductor=user, activo=True).select_related('vehiculo').first()
        if asignacion:
            v = asignacion.vehiculo
            vehiculo_asignado = {
                'id':      v.id,
                'patente': v.patente,
                'marca':   v.marca,
                'modelo':  v.modelo,
            }

    return JsonResponse({
        "message": "Login exitoso",
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id":                user.id,
            "nombre":            user.nombre or user.email,
            "rut":               rut,
            "email":             user.email,
            "rol":               user.rol,
            "primer_login":      user.primer_login,
            "empresa":           user.empresa.nombre if user.empresa else None,
            "empresa_id":        user.empresa_id,
            "vehiculo_asignado":  vehiculo_asignado,
            "plan_modulos":       plan_modulos,
            "plan_nombre":        plan_nombre,
            "plan_permisos":      plan_permisos,
            "requiere_licencia":  bool((user.extra or {}).get('requiere_licencia')),
        },
    })


# ─────────────────────────────────────────
# Empresas
# ─────────────────────────────────────────

def _sincronizar_suscripcion(empresa, plan):
    """
    Crea o actualiza la suscripción al asignar un plan a una empresa.
    - Sin suscripción  → crea en 'pendiente' (debe pagar para activarse).
    - Ya pendiente     → actualiza el plan.
    - Activa/gracia/suspendida → solo actualiza el plan; mantiene estado.
    """
    sus = Suscripcion.objects.filter(empresa=empresa).first()
    if sus is None:
        Suscripcion.objects.create(
            empresa = empresa,
            plan    = plan,
            ciclo   = 'mensual',
            estado  = 'pendiente',
        )
    elif sus.estado == 'pendiente':
        sus.plan = plan
        sus.save(update_fields=['plan'])
    else:
        sus.plan = plan
        sus.save(update_fields=['plan'])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def empresas_lista(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    # Subconsultas para evitar el producto cartesiano en los COUNT
    sq_flotas = Flota.objects.filter(empresa=OuterRef('pk')).values('empresa').annotate(cnt=Count('id')).values('cnt')
    sq_vehiculos = Vehiculo.objects.filter(flota__empresa=OuterRef('pk')).values('flota__empresa').annotate(cnt=Count('id')).values('cnt')
    sq_conductores = Usuario.objects.filter(empresa=OuterRef('pk'), rol=Rol.CONDUCTOR).values('empresa').annotate(cnt=Count('id')).values('cnt')
    sq_actividad = Usuario.objects.filter(empresa=OuterRef('pk')).values('empresa').annotate(last_login=Max('last_login')).values('last_login')

    empresas = Empresa.objects.annotate(
        cantidad_flotas=Coalesce(Subquery(sq_flotas, output_field=IntegerField()), 0),
        cantidad_vehiculos=Coalesce(Subquery(sq_vehiculos, output_field=IntegerField()), 0),
        cantidad_conductores=Coalesce(Subquery(sq_conductores, output_field=IntegerField()), 0),
        ultima_actividad=Subquery(sq_actividad)
    ).order_by('nombre')
    
    return Response(EmpresaSerializer(empresas, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def empresas_crear(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    serializer = EmpresaSerializer(data=request.data)
    if serializer.is_valid():
        empresa = serializer.save()

        plan_id = request.data.get('plan_id')
        if plan_id:
            try:
                plan = PlanSuscripcion.objects.get(pk=plan_id)
                CambioPlan.objects.create(
                    empresa=empresa, plan_antes=None, plan_despues=plan,
                    cambiado_por=request.user, motivo='Asignado al crear la empresa'
                )
                empresa.plan = plan
                empresa.save(update_fields=['plan'])
                _sincronizar_suscripcion(empresa, plan)
            except PlanSuscripcion.DoesNotExist:
                pass

        registrar_log('ACTIVIDAD', 'empresa_creada', request,
                      detalle={'empresa_nombre': empresa.nombre, 'empresa_id': empresa.pk})
        return Response(EmpresaSerializer(empresa).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def empresas_detalle(request, pk):
    # USUARIO solo puede ver su propia empresa
    if not es_superadmin(request.user):
        if request.method in ('PUT', 'DELETE'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        empresa_propia = getattr(request.user, 'empresa', None)
        if not empresa_propia or str(empresa_propia.pk) != str(pk):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(EmpresaSerializer(empresa_propia).data)

    try:
        empresa = Empresa.objects.get(pk=pk)
    except Empresa.DoesNotExist:
        return Response({"error": "Empresa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':

        # Respuesta extendida para SUPERADMIN
        cantidad_flotas = Flota.objects.filter(empresa=empresa).count()
        cantidad_vehiculos = Vehiculo.objects.filter(flota__empresa=empresa).count()
        cantidad_conductores = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR).count()
        cantidad_mantenciones = Mantencion.objects.filter(vehiculo__flota__empresa=empresa).count()
        cantidad_documentos = Documento.objects.filter(entidad='vehiculo', vehiculo__flota__empresa=empresa).count()

        usuarios = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO).order_by('email')
        usuarios_data = UsuarioListSerializer(usuarios, many=True).data

        actividad = usuarios.exclude(last_login__isnull=True).order_by('-last_login')[:5]
        actividad_data = [{
            "usuario": u.nombre or u.email,
            "rol": u.rol,
            "fecha": u.last_login
        } for u in actividad]

        data = {
            "informacion": EmpresaSerializer(empresa).data,
            "estadisticas": {
                "flotas": cantidad_flotas,
                "vehiculos": cantidad_vehiculos,
                "conductores": cantidad_conductores,
                "mantenciones": cantidad_mantenciones,
                "documentos": cantidad_documentos
            },
            "usuarios": usuarios_data,
            "actividad": actividad_data
        }
        return Response(data)

    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = EmpresaSerializer(empresa, data=request.data, partial=True)
        if serializer.is_valid():
            empresa = serializer.save()

            if 'plan_id' in request.data:
                plan_id      = request.data.get('plan_id')
                plan_anterior = empresa.plan
                nuevo_plan    = None
                if plan_id:
                    try:
                        nuevo_plan = PlanSuscripcion.objects.get(pk=plan_id)
                    except PlanSuscripcion.DoesNotExist:
                        nuevo_plan = plan_anterior

                if nuevo_plan and nuevo_plan != plan_anterior:
                    CambioPlan.objects.create(
                        empresa=empresa, plan_antes=plan_anterior, plan_despues=nuevo_plan,
                        cambiado_por=request.user, motivo='Modificado desde formulario de empresa'
                    )
                    empresa.plan = nuevo_plan
                    empresa.save(update_fields=['plan'])
                    _sincronizar_suscripcion(empresa, nuevo_plan)

                    # Notificar según tipo de cambio
                    if plan_anterior is None:
                        _tit = '🎉 Plan asignado'
                        _msg = (
                            f'Se te asignó el plan {nuevo_plan.get_nombre_display()}. '
                            f'Realiza el pago para activar tu acceso.'
                        )
                    else:
                        p_ant = plan_anterior.precio_mensual or 0
                        p_nvo = nuevo_plan.precio_mensual or 0
                        if p_nvo > p_ant:
                            _tit = '📈 Plan mejorado'
                            _msg = (
                                f'Tu plan fue actualizado a {nuevo_plan.get_nombre_display()} (plan superior). '
                                f'Los nuevos límites y módulos están disponibles de inmediato. '
                                f'El próximo cobro será al precio del nuevo plan.'
                            )
                        elif p_nvo < p_ant:
                            _tit = '📉 Plan ajustado'
                            _msg = (
                                f'Tu plan fue ajustado a {nuevo_plan.get_nombre_display()} (plan inferior). '
                                f'Los nuevos límites aplican de inmediato. '
                                f'El próximo cobro será al precio del nuevo plan.'
                            )
                        else:
                            _tit = 'Plan actualizado'
                            _msg = f'Tu plan fue actualizado a {nuevo_plan.get_nombre_display()}.'
                    notificar_admins_empresa(
                        empresa, TipoNotificacion.ACTIVIDAD,
                        _tit, _msg, url_accion='/empresa/dashboard',
                    )

                elif nuevo_plan and nuevo_plan == plan_anterior:
                    # Plan sin cambio pero puede no tener suscripción aún
                    _sincronizar_suscripcion(empresa, nuevo_plan)

            return Response(EmpresaSerializer(empresa).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        registrar_log('ACTIVIDAD', 'empresa_suspendida', request,
                      detalle={'empresa_nombre': empresa.nombre, 'empresa_id': empresa.pk})
        empresa.estado = 'suspendida'
        empresa.save(update_fields=['estado'])
        return Response({"message": "Empresa suspendida."})


# ─────────────────────────────────────────
# Usuarios
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuarios_lista(request):
    if es_superadmin(request.user):
        # Para el Superadmin, listamos solo los usuarios administradores de empresas (excluimos superadmins y conductores)
        qs = Usuario.objects.filter(
            rol=Rol.USUARIO, empresa__isnull=False
        ).select_related('empresa')
    elif tiene_permiso(request.user, 'usuarios.ver'):
        if not request.user.empresa_id:
            return Response([])
        # Para administradores de empresa, listamos solo sus pares (rol USUARIO), excluyendo conductores
        qs = Usuario.objects.filter(
            empresa=request.user.empresa,
            rol=Rol.USUARIO
        ).select_related('empresa')
    else:
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    # Filtros
    empresa_id = request.query_params.get('empresa_id')
    rol        = request.query_params.get('rol')
    estado     = request.query_params.get('estado')
    q          = request.query_params.get('q')

    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    if rol:
        qs = qs.filter(rol=rol)
    if estado:
        if estado == 'bloqueado':
            qs = qs.filter(is_blocked=True)
        elif estado == 'activo':
            qs = qs.filter(is_blocked=False, is_active=True)

    if q:
        q = q.strip()
        # Intentamos normalizar por si es un RUT
        rut_hash = hashlib.sha256(normalizar_rut(q).encode()).hexdigest()
        # email está cifrado → se filtra en Python por el email descifrado
        ql = q.lower()
        ids_email = [u.id for u in qs.only('id', 'email') if ql in (u.email or '').lower()]
        qs = qs.filter(Q(id__in=ids_email) | Q(rut_hash=rut_hash))

    return Response(UsuarioListSerializer(qs.order_by('email'), many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def usuarios_crear(request):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'usuarios.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data.copy()

    if not es_superadmin(request.user):
        if data.get('rol') in (Rol.SUPERADMIN, Rol.USUARIO):
            return Response({"error": "Sin permisos para crear ese rol."}, status=status.HTTP_403_FORBIDDEN)
        data['empresa_id'] = request.user.empresa_id

    # Enforcement de límite de usuarios por plan (solo para rol USUARIO)
    empresa_id_para_check = data.get('empresa_id') or (request.user.empresa_id if not es_superadmin(request.user) else None)
    rol_nuevo = data.get('rol')
    if rol_nuevo == Rol.USUARIO and empresa_id_para_check:
        try:
            empresa_check = Empresa.objects.select_related('plan').get(pk=empresa_id_para_check)
            puede, error_resp, _, _, _ = verificar_limite_plan(empresa_check, 'usuarios')
            if not puede:
                return error_resp
        except Empresa.DoesNotExist:
            pass

    serializer = UsuarioCrearSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        registrar_log('ACTIVIDAD', 'usuario_creado', request,
                      detalle={'usuario_email': user.email, 'rol': user.rol})

        # ── Email de bienvenida ──────────────────────────────────────────────
        try:
            from .email_service import email_bienvenida
            from django.conf import settings as _settings
            email_bienvenida(
                email=user.email,
                nombre=user.nombre or user.email,
                empresa_nombre=user.empresa.nombre if user.empresa else '',
                plan_nombre=(
                    user.empresa.plan.get_nombre_display()
                    if user.empresa and user.empresa.plan else 'Sin plan'
                ),
                url_login=f"{_settings.FRONTEND_URL}/login",
            )
        except Exception:
            pass

        return Response(UsuarioListSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def usuarios_detalle(request, pk):
    try:
        usuario = Usuario.objects.select_related('empresa').get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not es_superadmin(request.user):
        if not tiene_permiso(request.user, 'usuarios.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        if usuario.empresa_id != request.user.empresa_id:
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(UsuarioListSerializer(usuario).data)

    if request.method == 'PUT':
        if not es_superadmin(request.user) and not tiene_permiso(request.user, 'usuarios.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        if not es_superadmin(request.user) and data.get('rol') in (Rol.USUARIO, Rol.SUPERADMIN):
            return Response({"error": "Sin permisos para asignar ese rol."}, status=status.HTTP_403_FORBIDDEN)

        rol_anterior = usuario.rol
        serializer = UsuarioEditarSerializer(usuario, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if 'rol' in data and data['rol'] != rol_anterior:
                registrar_log('SEGURIDAD', 'cambio_rol', request, detalle={
                    'usuario_email': usuario.email,
                    'rol_anterior': rol_anterior,
                    'rol_nuevo': usuario.rol,
                })
            elif 'permisos' in data:
                registrar_log('SEGURIDAD', 'cambio_permisos', request, detalle={
                    'usuario_email': usuario.email,
                    'permisos': data.get('permisos', []),
                })
            else:
                registrar_log('ACTIVIDAD', 'usuario_modificado', request,
                              detalle={'usuario_email': usuario.email})
            return Response(UsuarioListSerializer(usuario).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not es_superadmin(request.user) and not tiene_permiso(request.user, 'usuarios.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        registrar_log('ACTIVIDAD', 'usuario_eliminado', request,
                      detalle={'usuario_email': usuario.email})
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return Response({"message": "Usuario desactivado."})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def usuario_reset_password(request, pk):
    import secrets
    import string

    if not es_superadmin(request.user):
        return Response({"error": "Solo el Superadmin puede resetear contraseñas."}, status=403)

    try:
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    # Generar contraseña temporal segura de 10 caracteres (letras + dígitos)
    alfabeto    = string.ascii_letters + string.digits
    clave_temp  = ''.join(secrets.choice(alfabeto) for _ in range(10))

    usuario.set_password(clave_temp)
    # Limpiar bloqueo y contadores — el reset debe dejar la cuenta usable de inmediato
    usuario.is_blocked        = False
    usuario.intentos_fallidos = 0
    usuario.save(update_fields=['password', 'is_blocked', 'intentos_fallidos'])

    registrar_log('SEGURIDAD', 'cambio_password', request,
                  detalle={'usuario_email': usuario.email, 'usuario_id': pk})

    notificar(usuario, TipoNotificacion.SEGURIDAD,
              "Contraseña restablecida",
              "Un administrador restableció tu contraseña. Revisa tu correo para obtener la clave temporal.",
              url_accion='')

    # Enviar clave temporal por correo (fire-and-forget)
    email_enviado = False
    email_error   = ''
    try:
        from g_de_flota.email_service import email_reset_password
        from django.conf import settings as dj_settings
        from g_de_flota.models import ConfiguracionSistema

        config = ConfiguracionSistema.get()
        if not config.email_activo:
            email_error = 'El sistema de correo está desactivado en Configuración → Correo.'
        elif not usuario.email:
            email_error = 'El usuario no tiene email registrado.'
        else:
            empresa_nombre = (
                usuario.empresa.nombre
                if usuario.empresa_id and usuario.empresa
                else 'FlotaSystem'
            )
            url_login = getattr(dj_settings, 'FRONTEND_URL', '') + '/login'
            enviado = email_reset_password(
                email=usuario.email,
                nombre=usuario.nombre or usuario.email,
                empresa_nombre=empresa_nombre,
                clave_temporal=clave_temp,
                url_login=url_login,
            )
            if enviado is False:
                email_error = 'Error SMTP al enviar el correo. Revisa la configuración en Configuración → Correo.'
            else:
                email_enviado = True
    except Exception as e:
        logger.exception(f"[RESET_PASSWORD] Error al enviar correo a usuario {pk}: {e}")
        email_error = f'Error inesperado al enviar el correo: {e}'

    msg = 'Contraseña restablecida correctamente.'
    if email_enviado:
        msg += f' Se envió la clave temporal a {usuario.email}.'
    else:
        msg += f' ⚠ El correo no pudo enviarse: {email_error}'

    return Response({"message": msg, "email_enviado": email_enviado, "clave_temp": clave_temp})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def usuario_toggle_block(request, pk):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=403)

    try:
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    if usuario.rol == Rol.SUPERADMIN:
        return Response({"error": "No se puede bloquear a un Superadmin."}, status=400)

    usuario.is_blocked = not usuario.is_blocked
    if not usuario.is_blocked:
        usuario.intentos_fallidos = 0
    usuario.save()

    accion_log = 'usuario_bloqueado' if usuario.is_blocked else 'usuario_desbloqueado'
    registrar_log('ACTIVIDAD', accion_log, request,
                  detalle={'usuario_email': usuario.email, 'usuario_id': pk})

    # Notificar al usuario afectado
    if usuario.is_blocked:
        notificar(usuario, TipoNotificacion.SEGURIDAD,
                  "Tu cuenta ha sido bloqueada",
                  "Un administrador bloqueó tu cuenta. Contacta al soporte si crees que es un error.",
                  url_accion='')
    else:
        notificar(usuario, TipoNotificacion.SEGURIDAD,
                  "Tu cuenta ha sido desbloqueada",
                  "Un administrador desbloqueó tu cuenta. Ya puedes iniciar sesión.",
                  url_accion='')

    estado = "bloqueado" if usuario.is_blocked else "desbloqueado"
    return Response({"message": f"Usuario {estado} exitosamente.", "is_blocked": usuario.is_blocked})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuario_historial(request, pk):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=403)

    historial = LogAuditoria.objects.filter(usuario_id=pk, tipo=TipoLog.SEGURIDAD, accion__in=['login_exitoso', 'login_fallido']).order_by('-fecha')[:20]
    data = [{
        "fecha": h.fecha,
        "exito": h.accion == 'login_exitoso',
        "ip": h.ip
    } for h in historial]
    
    return Response(data)


# ─────────────────────────────────────────
# Conductores
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conductores_lista_crear(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'conductores.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        qs = Usuario.objects.filter(
            empresa=empresa, rol=Rol.CONDUCTOR
        ).select_related('empresa').prefetch_related(
            'asignaciones_conductor__vehiculo'
        ).order_by('email')
        return Response(ConductorListSerializer(qs, many=True).data)

    if not tiene_permiso(request.user, 'conductores.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'conductores')
    if not puede:
        return error_resp

    serializer = ConductorCrearSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        conductor = serializer.save()
        registrar_log('ACTIVIDAD', 'conductor_creado', request, detalle={
            'email':  conductor.email,
            'nombre': conductor.nombre or '',
        })
        return Response(ConductorListSerializer(conductor).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def conductores_detalle(request, pk):
    # Un CONDUCTOR solo puede ver/editar su propio perfil
    if request.user.rol == Rol.CONDUCTOR and str(request.user.pk) != str(pk):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        empresa   = get_empresa(request)
        conductor = Usuario.objects.prefetch_related(
            'asignaciones_conductor__vehiculo'
        ).get(pk=pk, empresa=empresa, rol=Rol.CONDUCTOR)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
    except Usuario.DoesNotExist:
        return Response({"error": "Conductor no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if request.user.rol != Rol.CONDUCTOR and not tiene_permiso(request.user, 'conductores.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(ConductorDetalleSerializer(conductor).data)

    if request.method == 'PUT':
        if not tiene_permiso(request.user, 'conductores.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ConductorEditarSerializer(conductor, data=request.data, partial=True)
        if serializer.is_valid():
            _campos_cond = ['nombre_cifrado', 'email', 'telefono', 'licencia_tipo']
            _antes = _snap(conductor, _campos_cond)
            serializer.save()
            conductor.refresh_from_db()
            _despues = _snap(conductor, _campos_cond)
            registrar_log('ACTIVIDAD', 'conductor_editado', request, detalle={
                'email':        conductor.email,
                'conductor_id': pk,
                'cambios':      _diff_campos(_antes, _despues),
            })
            return Response(ConductorListSerializer(conductor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'conductores.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        registrar_log('ACTIVIDAD', 'conductor_desactivado', request, detalle={
            'email': conductor.email, 'conductor_id': pk,
        })
        conductor.is_active = False
        conductor.save(update_fields=['is_active'])
        return Response({"message": "Conductor desactivado."})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductores_asignar(request, pk):
    if not tiene_permiso(request.user, 'conductores.asignar'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
    try:
        empresa   = get_empresa(request)
        conductor = Usuario.objects.get(pk=pk, empresa=empresa, rol=Rol.CONDUCTOR)
        vehiculo  = Vehiculo.objects.get(pk=request.data.get('vehiculo_id'), flota__empresa=empresa)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
    except (Usuario.DoesNotExist, Vehiculo.DoesNotExist):
        return Response({"error": "Conductor o vehículo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    # 1. Desactivar cualquier asignación previa de ESTE conductor
    Asignacion.objects.filter(conductor=conductor, activo=True).update(activo=False, hasta=timezone.now())

    # 2. Verificar si el vehículo ya está asignado a OTRO conductor
    asignacion_actual = Asignacion.objects.filter(vehiculo=vehiculo, activo=True).first()
    if asignacion_actual:
        return Response({
            "error": "Este vehículo ya está asignado a otro usuario"
        }, status=status.HTTP_400_BAD_REQUEST)

    # 3. Crear la nueva asignación
    Asignacion.objects.create(
        conductor=conductor,
        vehiculo=vehiculo,
        activo=True,
        desde=timezone.now()
    )
    conductor.refresh_from_db()
    registrar_log('ACTIVIDAD', 'conductor_asignado', request, detalle={
        'conductor': conductor.email,
        'vehiculo':  vehiculo.patente,
    })
    notificar_admins_empresa(
        empresa, TipoNotificacion.ACTIVIDAD,
        "Nueva asignación de vehículo",
        f"El conductor {conductor.nombre or conductor.email} fue asignado al vehículo {vehiculo.patente}.",
        url_accion='/empresa/conductores'
    )
    return Response(ConductorListSerializer(conductor).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conductores_desasignar(request, pk):
    if not tiene_permiso(request.user, 'conductores.asignar'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
    try:
        empresa   = get_empresa(request)
        conductor = Usuario.objects.get(pk=pk, empresa=empresa, rol=Rol.CONDUCTOR)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_400_BAD_REQUEST)
    except Usuario.DoesNotExist:
        return Response({"error": "Conductor no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    Asignacion.objects.filter(conductor=conductor, activo=True).update(activo=False)
    conductor.refresh_from_db()
    registrar_log('ACTIVIDAD', 'conductor_desasignado', request, detalle={
        'conductor': conductor.email,
    })
    notificar_admins_empresa(
        empresa, TipoNotificacion.ACTIVIDAD,
        "Conductor desasignado",
        f"El conductor {conductor.nombre or conductor.email} fue desasignado de su vehículo.",
        url_accion='/empresa/conductores'
    )
    return Response(ConductorListSerializer(conductor).data)


# ─────────────────────────────────────────
# Flotas — vista global SUPERADMIN
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_flotas_lista(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    flotas = list(
        Flota.objects.select_related('empresa')
        .prefetch_related('vehiculos')
        .order_by('empresa__nombre', 'nombre')
    )

    # Un admin (rol USUARIO) por empresa, pre-cargado
    empresa_ids = {f.empresa_id for f in flotas}
    admins = {}
    for emp_id in empresa_ids:
        user = Usuario.objects.filter(empresa_id=emp_id, rol=Rol.USUARIO, is_active=True).first()
        if user:
            admins[emp_id] = {'nombre': user.nombre, 'email': user.email}

    result = []
    for f in flotas:
        admin = admins.get(f.empresa_id)
        vehiculos = list(f.vehiculos.all())
        result.append({
            'id':             f.id,
            'nombre':         f.nombre,
            'empresa_id':     f.empresa_id,
            'empresa_nombre': f.empresa.nombre,
            'admin_nombre':   admin['nombre'] if admin else None,
            'admin_email':    admin['email']  if admin else None,
            'total_vehiculos': sum(1 for v in vehiculos if v.activo),
            'vehiculos':      VehiculoResumenSerializer(vehiculos, many=True).data,
        })

    return Response(result)


# ─────────────────────────────────────────
# Flotas
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def flotas_lista_crear(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'flotas.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        flotas = Flota.objects.filter(empresa=empresa).select_related('empresa').prefetch_related('vehiculos').order_by('nombre')
        return Response(FlotaSerializer(flotas, many=True, context={'empresa': empresa}).data)

    if not tiene_permiso(request.user, 'flotas.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'flotas')
    if not puede:
        return error_resp

    serializer = FlotaSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        flota = serializer.save(empresa=empresa)
        registrar_log('ACTIVIDAD', 'flota_creada', request, detalle={
            'nombre': flota.nombre, 'empresa': empresa.nombre,
        })
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def flotas_detalle(request, pk):
    try:
        empresa = get_empresa(request)
        flota   = Flota.objects.prefetch_related('vehiculos').get(pk=pk, empresa=empresa)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
    except Flota.DoesNotExist:
        return Response({"error": "Flota no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'flotas.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(FlotaSerializer(flota, context={'empresa': empresa}).data)

    if request.method == 'PUT':
        if not tiene_permiso(request.user, 'flotas.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        serializer = FlotaSerializer(flota, data=request.data, partial=True, context={'empresa': empresa})
        if serializer.is_valid():
            _antes = _snap(flota, ['nombre', 'descripcion'])
            serializer.save()
            flota.refresh_from_db()
            _despues = _snap(flota, ['nombre', 'descripcion'])
            registrar_log('ACTIVIDAD', 'flota_editada', request, detalle={
                'nombre':   flota.nombre,
                'flota_id': pk,
                'cambios':  _diff_campos(_antes, _despues),
            })
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'flotas.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        registrar_log('ACTIVIDAD', 'flota_eliminada', request, detalle={
            'nombre': flota.nombre, 'flota_id': pk,
        })
        flota.delete()
        return Response({"message": "Flota eliminada."})


# ─────────────────────────────────────────
# Vehículos
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehiculos_lista_crear(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'vehiculos.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        vehiculos = Vehiculo.objects.filter(
            flota__empresa=empresa
        ).select_related('flota').prefetch_related(
            'asignaciones__conductor'
        ).order_by('patente')
        return Response(VehiculoSerializer(vehiculos, many=True, context={'empresa': empresa}).data)

    if not tiene_permiso(request.user, 'vehiculos.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'vehiculos')
    if not puede:
        return error_resp

    serializer = VehiculoSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        vehiculo = serializer.save()
        registrar_log('ACTIVIDAD', 'vehiculo_creado', request, detalle={
            'patente': vehiculo.patente,
            'marca':   vehiculo.marca or '',
            'modelo':  vehiculo.modelo or '',
        })
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def vehiculos_detalle(request, pk):
    try:
        empresa  = get_empresa(request)
        vehiculo = Vehiculo.objects.select_related('flota').get(pk=pk, flota__empresa=empresa)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
    except Vehiculo.DoesNotExist:
        return Response({"error": "Vehículo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'vehiculos.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(VehiculoSerializer(vehiculo, context={'empresa': empresa}).data)

    if request.method == 'PUT':
        if not tiene_permiso(request.user, 'vehiculos.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        serializer = VehiculoSerializer(vehiculo, data=request.data, partial=True, context={'empresa': empresa})
        if serializer.is_valid():
            _campos_veh = ['patente', 'marca', 'modelo', 'anio', 'color', 'km_actuales']
            _antes = _snap(vehiculo, _campos_veh)
            serializer.save()
            vehiculo.refresh_from_db()
            _despues = _snap(vehiculo, _campos_veh)
            registrar_log('ACTIVIDAD', 'vehiculo_editado', request, detalle={
                'patente':    vehiculo.patente,
                'vehiculo_id': pk,
                'cambios':    _diff_campos(_antes, _despues),
            })
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'vehiculos.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        registrar_log('ACTIVIDAD', 'vehiculo_desactivado', request, detalle={
            'patente': vehiculo.patente, 'vehiculo_id': pk,
        })
        vehiculo.activo = False
        vehiculo.save(update_fields=['activo'])
        return Response({"message": "Vehículo desactivado."})


# ─────────────────────────────────────────
# Logs y Auditoría
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logs_lista(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    qs = LogAuditoria.objects.select_related('usuario').all()

    tipo        = request.query_params.get('tipo')
    accion      = request.query_params.get('accion')
    q           = request.query_params.get('q')
    fecha_desde = request.query_params.get('fecha_desde')
    fecha_hasta = request.query_params.get('fecha_hasta')

    if tipo:
        qs = qs.filter(tipo=tipo)
    if accion:
        qs = qs.filter(accion=accion)
    if q:
        # email cifrado → se resuelven en Python los usuarios cuyo correo coincide
        ql = q.lower()
        user_ids = [u.id for u in Usuario.objects.only('id', 'email') if ql in (u.email or '').lower()]
        qs = qs.filter(Q(usuario_id__in=user_ids) | Q(ip__icontains=q))
    if fecha_desde:
        qs = qs.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__date__lte=fecha_hasta)

    page_num  = max(1, int(request.query_params.get('page', 1)))
    paginator = Paginator(qs, 50)
    page      = paginator.get_page(page_num)

    return Response({
        'count':     paginator.count,
        'num_pages': paginator.num_pages,
        'results':   LogAuditoriaSerializer(page.object_list, many=True).data,
    })


# ─────────────────────────────────────────
# Permisos
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permisos_lista(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
    permisos = Permiso.objects.all()
    return Response(PermisoSerializer(permisos, many=True).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def usuario_permisos(request, pk):
    if not es_superadmin(request.user):
        return Response({"error": "Solo el Superadmin puede gestionar permisos."}, status=403)

    try:
        usuario = Usuario.objects.select_related('empresa__plan').get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    if usuario.rol != Rol.USUARIO:
        return Response({"error": "Los permisos solo aplican a usuarios con rol USUARIO."}, status=400)

    if request.method == 'GET':
        plan_modulos = []
        plan_nombre  = ''
        if usuario.empresa and usuario.empresa.plan:
            plan_modulos = usuario.empresa.plan.modulos or []
            plan_nombre  = usuario.empresa.plan.get_nombre_display()
        return Response({
            "usuario_id":   usuario.pk,
            "permisos":     list(usuario.permisos.values_list('codigo', flat=True)),
            "plan_modulos": plan_modulos,
            "plan_nombre":  plan_nombre,
        })

    if request.method == 'PUT':
        codigos = request.data.get('permisos', [])
        permisos = Permiso.objects.filter(codigo__in=codigos)
        usuario.permisos.set(permisos)
        registrar_log('SEGURIDAD', 'cambio_permisos', request, detalle={
            'usuario_email': usuario.email,
            'permisos': list(usuario.permisos.values_list('codigo', flat=True)),
        })
        notificar(usuario, TipoNotificacion.SEGURIDAD,
                  "Tus permisos fueron actualizados",
                  "Un administrador modificó los permisos de tu cuenta.",
                  url_accion='')
        return Response({
            "usuario_id": usuario.pk,
            "permisos": list(usuario.permisos.values_list('codigo', flat=True)),
        })


# ─────────────────────────────────────────
# Mantenciones
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mantenciones_lista_crear(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'mantenciones.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        
        vehiculo_id  = request.query_params.get('vehiculo_id')
        estado_param = request.query_params.get('estado')
        qs = Mantencion.objects.filter(vehiculo__flota__empresa=empresa).select_related('vehiculo')

        if vehiculo_id:
            qs = qs.filter(vehiculo_id=vehiculo_id)
        if estado_param:
            qs = qs.filter(estado=estado_param)

        return Response(MantencionSerializer(qs.order_by('-fecha_programada', '-id'), many=True).data)

    if not tiene_permiso(request.user, 'mantenciones.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    vehiculo_id      = request.data.get('vehiculo_id')
    tipo_mantencion  = request.data.get('tipo_mantencion', '').strip()
    fecha_programada = request.data.get('fecha_programada')

    # Vehículo válido y activo
    vehiculo = Vehiculo.objects.filter(pk=vehiculo_id, flota__empresa=empresa).first()
    if not vehiculo:
        return Response({"error": "Vehículo no válido."}, status=status.HTTP_400_BAD_REQUEST)
    if not vehiculo.activo:
        return Response({"error": "No se pueden programar mantenciones para un vehículo inactivo."}, status=status.HTTP_400_BAD_REQUEST)

    # Duplicado: mismo tipo en estado activo para este vehículo
    if Mantencion.objects.filter(
        vehiculo_id=vehiculo_id,
        tipo_mantencion=tipo_mantencion,
        estado__in=['pendiente', 'en_proceso']
    ).exists():
        return Response({"error": f"Ya existe una mantención de '{tipo_mantencion}' pendiente o en proceso para este vehículo."}, status=status.HTTP_400_BAD_REQUEST)

    # Dos mantenciones el mismo día para el mismo vehículo
    if fecha_programada and Mantencion.objects.filter(
        vehiculo_id=vehiculo_id,
        fecha_programada=fecha_programada,
        estado__in=['pendiente', 'en_proceso']
    ).exists():
        return Response({"error": "Este vehículo ya tiene una mantención programada para esa fecha."}, status=status.HTTP_400_BAD_REQUEST)

    # Límite de flota: no más del 50 % de vehículos activos en mantenimiento simultáneamente
    total_activos = Vehiculo.objects.filter(flota__empresa=empresa, activo=True).count()
    if total_activos > 0:
        en_mantencion = Mantencion.objects.filter(
            vehiculo__flota__empresa=empresa,
            estado__in=['pendiente', 'en_proceso']
        ).values('vehiculo_id').distinct().count()
        if en_mantencion / total_activos >= 0.50:
            return Response({
                "error": f"El {round(en_mantencion/total_activos*100)}% de la flota ya está en mantenimiento ({en_mantencion} de {total_activos} vehículos). Completa o cancela mantenciones activas antes de agregar más."
            }, status=status.HTTP_400_BAD_REQUEST)

    serializer = MantencionSerializer(data=request.data)
    if serializer.is_valid():
        mantencion = serializer.save()
        registrar_log('ACTIVIDAD', 'mantencion_creada', request, detalle={
            'vehiculo': vehiculo.patente,
            'tipo':     tipo_mantencion,
            'fecha':    str(fecha_programada or ''),
        })
        # Notificar al conductor asignado al vehículo
        _asig_c = Asignacion.objects.filter(vehiculo=vehiculo, activo=True).select_related('conductor').first()
        if _asig_c:
            _cond = _asig_c.conductor
            _fecha_txt = f" el {fecha_programada}" if fecha_programada else ""
            notificar(_cond, TipoNotificacion.ACTIVIDAD,
                      "Nueva mantención programada",
                      f"Se programó '{tipo_mantencion}' para tu vehículo {vehiculo.patente}{_fecha_txt}.",
                      url_accion='/mantencion')
            enviar_push(_cond,
                        titulo='Nueva mantención programada 🔧',
                        cuerpo=f"{tipo_mantencion} — {vehiculo.patente}{_fecha_txt}",
                        data={'tipo': 'mantencion_programada', 'mantencion_id': str(mantencion.id)})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def mantenciones_detalle(request, pk):
    try:
        empresa = get_empresa(request)
        mantencion = Mantencion.objects.select_related('vehiculo').get(pk=pk, vehiculo__flota__empresa=empresa)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
    except Mantencion.DoesNotExist:
        return Response({"error": "Mantención no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not tiene_permiso(request.user, 'mantenciones.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(MantencionSerializer(mantencion).data)

    if request.method == 'PUT':
        if not tiene_permiso(request.user, 'mantenciones.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

        data          = request.data.copy()
        estado_actual = mantencion.estado
        nuevo_estado  = data.get('estado', estado_actual)

        # Cancelación definitiva
        if estado_actual == 'cancelada':
            return Response({"error": "Una mantención cancelada no puede modificarse."}, status=status.HTTP_400_BAD_REQUEST)

        # Estado solo avanza: transiciones válidas
        TRANSICIONES_VALIDAS = {
            'pendiente':  {'pendiente', 'en_proceso', 'realizada', 'cancelada'},
            'en_proceso': {'en_proceso', 'realizada', 'cancelada'},
            'realizada':  {'realizada'},
        }
        if nuevo_estado not in TRANSICIONES_VALIDAS.get(estado_actual, set()):
            return Response({"error": f"No se puede cambiar el estado de '{estado_actual}' a '{nuevo_estado}'."}, status=status.HTTP_400_BAD_REQUEST)

        # Al completar: fecha y costo obligatorios
        if nuevo_estado == 'realizada' and estado_actual != 'realizada':
            if not data.get('fecha_realizada'):
                data['fecha_realizada'] = timezone.now().date().isoformat()
            costo = data.get('costo')
            if costo is None or float(costo) <= 0:
                return Response({"error": "El costo real debe ser mayor a 0 para marcar una mantención como realizada."}, status=status.HTTP_400_BAD_REQUEST)
            # Fecha realizada no puede ser futura
            from datetime import date as date_type
            fecha_r = data.get('fecha_realizada')
            if fecha_r and str(fecha_r) > timezone.now().date().isoformat():
                return Response({"error": "La fecha realizada no puede ser una fecha futura."}, status=status.HTTP_400_BAD_REQUEST)

        _campos_mant = ['descripcion', 'fecha_programada', 'kilometraje_programado', 'costo', 'notas']
        _antes_mant  = _snap(mantencion, _campos_mant)

        # Foto comprobante: llega en request.FILES si es multipart
        foto = request.FILES.get('foto_comprobante')

        serializer   = MantencionSerializer(mantencion, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            # Guardar foto por separado (el serializer no incluye ImageField en escritura)
            if foto:
                mantencion.foto_comprobante = foto
                mantencion.save(update_fields=['foto_comprobante'])
            mantencion.refresh_from_db()

            # Sincronizar flag en_mantencion del vehículo según el nuevo estado
            if nuevo_estado != estado_actual:
                vehiculo = mantencion.vehiculo
                if nuevo_estado == 'en_proceso':
                    vehiculo.en_mantencion = True
                    vehiculo.save(update_fields=['en_mantencion'])
                elif nuevo_estado in ('realizada', 'cancelada'):
                    vehiculo.en_mantencion = False
                    vehiculo.save(update_fields=['en_mantencion'])

                registrar_log('ACTIVIDAD', 'mantencion_estado_cambiado', request, detalle={
                    'vehiculo':      mantencion.vehiculo.patente,
                    'tipo':          mantencion.tipo_mantencion,
                    'estado_previo': estado_actual,
                    'estado_nuevo':  nuevo_estado,
                })
                # Notificar al conductor asignado al vehículo
                _asig_e = Asignacion.objects.filter(vehiculo=vehiculo, activo=True).select_related('conductor').first()
                if _asig_e:
                    _labels = {
                        'en_proceso': ('Mantención en proceso', 'La mantención fue iniciada.'),
                        'realizada':  ('Mantención completada', 'La mantención fue marcada como realizada.'),
                        'cancelada':  ('Mantención cancelada',  'La mantención fue cancelada por un administrador.'),
                    }
                    if nuevo_estado in _labels:
                        _tit, _msg_base = _labels[nuevo_estado]
                        _msg = f"'{mantencion.tipo_mantencion}' — {vehiculo.patente}. {_msg_base}"
                        notificar(_asig_e.conductor, TipoNotificacion.ACTIVIDAD, _tit, _msg, url_accion='/mantencion')
                        enviar_push(_asig_e.conductor, titulo=_tit, cuerpo=_msg,
                                    data={'tipo': 'mantencion_estado', 'mantencion_id': str(mantencion.id), 'estado': nuevo_estado})
            else:
                registrar_log('ACTIVIDAD', 'mantencion_editada', request, detalle={
                    'vehiculo': mantencion.vehiculo.patente,
                    'tipo':     mantencion.tipo_mantencion,
                    'cambios':  _diff_campos(_antes_mant, _snap(mantencion, _campos_mant)),
                })
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'mantenciones.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        # Notificar al conductor antes de eliminar
        _asig_d = Asignacion.objects.filter(vehiculo=mantencion.vehiculo, activo=True).select_related('conductor').first()
        if _asig_d:
            _msg_del = f"La mantención '{mantencion.tipo_mantencion}' de {mantencion.vehiculo.patente} fue eliminada por un administrador."
            notificar(_asig_d.conductor, TipoNotificacion.ACTIVIDAD, "Mantención eliminada", _msg_del, url_accion='/mantencion')
            enviar_push(_asig_d.conductor, titulo='Mantención eliminada',
                        cuerpo=f"{mantencion.tipo_mantencion} — {mantencion.vehiculo.patente}",
                        data={'tipo': 'mantencion_eliminada'})
        registrar_log('ACTIVIDAD', 'mantencion_eliminada', request, detalle={
            'vehiculo': mantencion.vehiculo.patente,
            'tipo':     mantencion.tipo_mantencion,
        })
        mantencion.delete()
        return Response({"message": "Mantención eliminada."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mantenciones_resumen(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if not tiene_permiso(request.user, 'mantenciones.ver'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    from django.db.models import Sum
    
    # Costo total mes actual
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    
    costo_mes = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        estado='realizada',
        fecha_realizada__gte=inicio_mes
    ).aggregate(total=Sum('costo'))['total'] or 0

    costo_total = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        estado='realizada'
    ).aggregate(total=Sum('costo'))['total'] or 0
    
    pendientes = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        estado='pendiente'
    ).count()

    en_proceso = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        estado='en_proceso'
    ).count()

    realizadas = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        estado='realizada'
    ).count()

    return Response({
        "costo_mes":   costo_mes,
        "costo_total": costo_total,
        "pendientes":  pendientes,
        "en_proceso":  en_proceso,
        "realizadas":  realizadas,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mantenciones_sugerencias(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    vehiculo_id = request.query_params.get('vehiculo_id')

    # Tipos desde historial de mantenciones de la empresa
    tipos_historial = list(
        Mantencion.objects
        .filter(vehiculo__flota__empresa=empresa)
        .exclude(tipo_mantencion='')
        .values_list('tipo_mantencion', flat=True)
        .distinct()
        .order_by('tipo_mantencion')
    )

    # Tipos y presupuestos desde reglas de planes activos de la empresa
    from .models import ReglaMantenimiento, VehiculoPlan
    reglas_qs = ReglaMantenimiento.objects.filter(
        plan__vehiculos_asignados__vehiculo__flota__empresa=empresa
    ).distinct()
    if vehiculo_id:
        reglas_qs = ReglaMantenimiento.objects.filter(
            plan__vehiculos_asignados__vehiculo_id=vehiculo_id
        ).distinct()

    tipos_planes = list(reglas_qs.values_list('tipo', flat=True).order_by('tipo'))
    presupuesto_por_tipo = {
        r['tipo']: float(r['costo_estimado'])
        for r in reglas_qs.values('tipo', 'costo_estimado')
        if r['costo_estimado']
    }

    # Unión sin duplicados manteniendo orden: planes primero, luego historial
    tipos_vistos = set(tipos_planes)
    tipos = tipos_planes + [t for t in tipos_historial if t not in tipos_vistos]

    # Talleres desde historial
    talleres = list(
        Mantencion.objects
        .filter(vehiculo__flota__empresa=empresa)
        .exclude(taller_proveedor='')
        .values_list('taller_proveedor', flat=True)
        .distinct()
        .order_by('taller_proveedor')
    )

    return Response({
        "tipos": tipos,
        "talleres": talleres,
        "presupuesto_por_tipo": presupuesto_por_tipo,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mantenciones_calendario(request):
    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    if not tiene_permiso(request.user, 'mantenciones.ver'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    year  = request.query_params.get('year',  timezone.now().date().year)
    month = request.query_params.get('month', timezone.now().date().month)

    qs = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa,
        fecha_programada__year=year,
        fecha_programada__month=month,
    ).exclude(estado='cancelada').select_related('vehiculo').order_by('fecha_programada')

    result = {}
    for m in qs:
        key = m.fecha_programada.isoformat()
        result.setdefault(key, []).append({
            'id':               m.id,
            'tipo_mantencion':  m.tipo_mantencion,
            'vehiculo_patente': m.vehiculo.patente,
            'estado':           m.estado,
            'estado_display':   m.get_estado_display(),
        })
    return Response(result)


# ─────────────────────────────────────────
# Mantenimiento Predictivo
# ─────────────────────────────────────────

from rest_framework import viewsets
from .models import (
    PlanMantenimiento, VehiculoPlan, ReglaMantenimiento,
    MantencionProgramada, AlertaMantencion, Vehiculo, EstadoMantencion
)
from .serializers import (
    PlanMantenimientoSerializer, AlertaMantencionSerializer
)
from rest_framework.decorators import action

class PlanMantenimientoViewSet(viewsets.ModelViewSet):
    serializer_class = PlanMantenimientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            empresa = get_empresa(self.request)
            return PlanMantenimiento.objects.filter(empresa=empresa).prefetch_related('reglas')
        except PermissionError:
            return PlanMantenimiento.objects.none()

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'GET':
            if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.ver'):
                self.permission_denied(request, message="Sin permisos.")
        else:
            if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.gestionar'):
                self.permission_denied(request, message="Sin permisos.")

    def perform_create(self, serializer):
        empresa = get_empresa(self.request)
        serializer.save(empresa=empresa)
        registrar_log('ACTIVIDAD', 'crear_plan_mantenimiento', self.request,
                      detalle={"plan_id": serializer.instance.id})

    def perform_update(self, serializer):
        serializer.save()
        registrar_log('ACTIVIDAD', 'actualizar_plan_mantenimiento', self.request, 
                      detalle={"plan_id": serializer.instance.id})

    def perform_destroy(self, instance):
        registrar_log('ACTIVIDAD', 'eliminar_plan_mantenimiento', self.request, 
                      detalle={"plan_id": instance.id})
        instance.delete()


class AlertaMantencionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaMantencionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not es_superadmin(self.request.user) and not tiene_permiso(self.request.user, 'predictivo.ver'):
            return AlertaMantencion.objects.none()
        try:
            empresa = get_empresa(self.request)
            qs = AlertaMantencion.objects.filter(
                mantencion_programada__vehiculo__flota__empresa=empresa
            ).select_related('mantencion_programada__vehiculo', 'mantencion_programada__regla')

            estado = self.request.query_params.get('estado')
            nivel  = self.request.query_params.get('nivel')

            if estado == 'pendiente':
                qs = qs.filter(atendida=False)
            elif estado == 'atendida':
                qs = qs.filter(atendida=True)

            if nivel in ['por_vencer', 'vencida']:
                qs = qs.filter(nivel=nivel)

            return qs.order_by('-nivel', 'dias_restantes')

        except PermissionError:
            return AlertaMantencion.objects.none()

    @action(detail=True, methods=['post'])
    def atender(self, request, pk=None):
        if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.gestionar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
            
        alerta = self.get_object()
        if alerta.atendida:
            return Response({"error": "La alerta ya fue atendida."}, status=status.HTTP_400_BAD_REQUEST)

        fecha_realizada_str = request.data.get('fecha_realizada')
        if not fecha_realizada_str:
            return Response({"error": "fecha_realizada es requerida."}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime, timedelta
        fecha_realizada = datetime.strptime(fecha_realizada_str, '%Y-%m-%d').date()

        # Crear mantención en historial
        prog = alerta.mantencion_programada
        costo_val = request.data.get('costo', 0.00)
        Mantencion.objects.create(
            vehiculo=prog.vehiculo,
            tipo_mantencion=prog.regla.tipo,
            fecha_programada=prog.fecha_siguiente,
            fecha_realizada=fecha_realizada,
            estado=EstadoMantencion.REALIZADA,
            costo=costo_val,
            descripcion=f"Mantención preventiva - Plan: {prog.regla.plan.nombre}"
        )

        # Actualizar programación
        prog.fecha_ultima = fecha_realizada
        prog.fecha_siguiente = fecha_realizada + timedelta(days=prog.regla.intervalo_dias)
        prog.save()

        # Cerrar alerta
        alerta.atendida = True
        alerta.fecha_atencion = timezone.now()
        alerta.save()

        registrar_log('ACTIVIDAD', 'atender_alerta_mantencion', request, detalle={"alerta_id": alerta.id})
        return Response({"status": "Alerta atendida y mantención registrada."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def simulador_vencimientos(request):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.ver'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        empresa = get_empresa(request)
    except PermissionError:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    vehiculo_id = request.query_params.get('vehiculo_id')
    meses = int(request.query_params.get('meses', 3))

    if not vehiculo_id:
        return Response({"error": "vehiculo_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vehiculo = Vehiculo.objects.get(id=vehiculo_id, flota__empresa=empresa)
    except Vehiculo.DoesNotExist:
        return Response({"error": "Vehículo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    # Buscar mantenciones programadas para el vehículo
    programadas = MantencionProgramada.objects.filter(vehiculo=vehiculo, estado='activa').select_related('regla')
    
    from datetime import timedelta
    hoy = timezone.now().date()
    fecha_fin = hoy + timedelta(days=meses * 30) # Aprox 30 dias por mes

    eventos = []
    presupuesto_total = 0

    for prog in programadas:
        fecha_actual = prog.fecha_siguiente
        while fecha_actual <= fecha_fin:
            if fecha_actual >= hoy:
                eventos.append({
                    'tipo': prog.regla.tipo,
                    'fecha': fecha_actual.isoformat(),
                    'costo_estimado': float(prog.regla.costo_estimado)
                })
                presupuesto_total += float(prog.regla.costo_estimado)
            fecha_actual += timedelta(days=prog.regla.intervalo_dias)

    eventos.sort(key=lambda x: x['fecha'])

    return Response({
        'eventos': eventos,
        'total_eventos': len(eventos),
        'presupuesto_total': presupuesto_total
    })


# ── Asignación de planes a vehículos ─────────────────────────
from .serializers import VehiculoPlanSerializer

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vehiculo_planes_lista_crear(request):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.ver'):
        return Response({'error': 'Sin permisos.'}, status=403)
    empresa = get_empresa(request)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=400)

    if request.method == 'GET':
        qs = VehiculoPlan.objects.filter(
            vehiculo__flota__empresa=empresa
        ).select_related('vehiculo', 'plan')
        return Response(VehiculoPlanSerializer(qs, many=True).data)

    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.gestionar'):
        return Response({'error': 'Sin permisos para gestionar.'}, status=403)

    vehiculo_id = request.data.get('vehiculo_id')
    plan_id     = request.data.get('plan_id')
    if not vehiculo_id or not plan_id:
        return Response({'error': 'vehiculo_id y plan_id son requeridos.'}, status=400)

    try:
        vehiculo = Vehiculo.objects.get(id=vehiculo_id, flota__empresa=empresa)
    except Vehiculo.DoesNotExist:
        return Response({'error': 'Vehículo no encontrado.'}, status=404)
    try:
        plan = PlanMantenimiento.objects.get(id=plan_id, empresa=empresa)
    except PlanMantenimiento.DoesNotExist:
        return Response({'error': 'Plan no encontrado.'}, status=404)

    asig, created = VehiculoPlan.objects.get_or_create(vehiculo=vehiculo, plan=plan)
    if not created:
        return Response({'error': 'Este vehículo ya tiene este plan asignado.'}, status=400)

    registrar_log('ACTIVIDAD', 'asignar_plan_vehiculo', request,
                  detalle={'vehiculo_id': vehiculo.id, 'plan_id': plan.id})
    return Response(VehiculoPlanSerializer(asig).data, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vehiculo_plan_detalle(request, pk):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.gestionar'):
        return Response({'error': 'Sin permisos.'}, status=403)
    empresa = get_empresa(request)
    try:
        asig = VehiculoPlan.objects.get(id=pk, vehiculo__flota__empresa=empresa)
    except VehiculoPlan.DoesNotExist:
        return Response({'error': 'Asignación no encontrada.'}, status=404)
    asig.delete()
    registrar_log('ACTIVIDAD', 'desasignar_plan_vehiculo', request, detalle={'asignacion_id': pk})
    return Response(status=204)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predictivo_resumen(request):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.ver'):
        return Response({'error': 'Sin permisos.'}, status=403)
    empresa = get_empresa(request)
    if not empresa:
        return Response({'error': 'Empresa no encontrada.'}, status=400)

    alertas_qs = AlertaMantencion.objects.filter(
        mantencion_programada__vehiculo__flota__empresa=empresa
    )
    pendientes    = alertas_qs.filter(atendida=False)
    inicio_mes    = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return Response({
        'alertas_pendientes':  pendientes.count(),
        'alertas_vencidas':    pendientes.filter(nivel='vencida').count(),
        'alertas_por_vencer':  pendientes.filter(nivel='por_vencer').count(),
        'atendidas_mes':       alertas_qs.filter(atendida=True, fecha_atencion__gte=inicio_mes).count(),
        'vehiculos_con_alerta': pendientes.values('mantencion_programada__vehiculo_id').distinct().count(),
        'planes_activos':      PlanMantenimiento.objects.filter(empresa=empresa, activo=True).count(),
        'vehiculos_asignados': VehiculoPlan.objects.filter(
            vehiculo__flota__empresa=empresa
        ).values('vehiculo_id').distinct().count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predictivo_generar_alertas(request):
    if not es_superadmin(request.user) and not tiene_permiso(request.user, 'predictivo.gestionar'):
        return Response({'error': 'Sin permisos.'}, status=403)
    empresa = get_empresa(request)

    hoy = timezone.now().date()
    filtro = {'vehiculo__activo': True, 'plan__activo': True}
    if empresa:
        filtro['vehiculo__flota__empresa'] = empresa

    vps = VehiculoPlan.objects.filter(**filtro).select_related(
        'vehiculo', 'plan'
    ).prefetch_related('plan__reglas')

    TIPOS_MANTENCION_MAP = {
        'aceite': 'Cambio de aceite',
        'frenos': 'Revisión de frenos',
        'neumaticos': 'Cambio de neumáticos',
        'filtro_aire': 'Filtro de aire',
        'filtro_combustible': 'Filtro de combustible',
        'rtv': 'Revisión técnica (RTV)',
        'electrica': 'Revisión eléctrica',
        'otro': 'Otro'
    }

    creadas = actualizadas = 0
    for vp in vps:
        for regla in vp.plan.reglas.all():
            prog, _ = MantencionProgramada.objects.get_or_create(
                vehiculo=vp.vehiculo, regla=regla,
                defaults={
                    'fecha_ultima':    vp.fecha_asignacion.date(),
                    'fecha_siguiente': vp.fecha_asignacion.date() + timedelta(days=regla.intervalo_dias),
                    'estado':          'activa',
                }
            )
            if prog.estado != 'activa':
                continue

            dias_transcurridos = (hoy - prog.fecha_ultima).days
            dias_restantes     = (prog.fecha_siguiente - hoy).days
            pct_avance         = round(dias_transcurridos / regla.intervalo_dias * 100, 2) if regla.intervalo_dias > 0 else 100.0
            nivel              = 'vencida' if dias_restantes <= 0 else 'por_vencer'

            if dias_restantes > regla.umbral_alerta_dias:
                continue

            existente = AlertaMantencion.objects.filter(
                mantencion_programada=prog, atendida=False
            ).first()

            if not existente:
                AlertaMantencion.objects.create(
                    mantencion_programada=prog, nivel=nivel,
                    dias_restantes=dias_restantes, pct_avance=pct_avance,
                )
                creadas += 1
                tipo_notif = (TipoNotificacion.MANTENCION_VENCIDA if nivel == 'vencida'
                              else TipoNotificacion.MANTENCION_POR_VENCER)
                
                tipo_amigable = TIPOS_MANTENCION_MAP.get(prog.regla.tipo, prog.regla.tipo)
                notificar_admins_empresa(
                    prog.vehiculo.flota.empresa, tipo_notif,
                    f"Mantención {nivel.replace('_',' ')}: {prog.vehiculo.patente}",
                    f"El vehículo {prog.vehiculo.patente} requiere '{tipo_amigable}'. Días restantes: {dias_restantes}.",
                    url_accion='/empresa/predictivo',
                    extra={'vehiculo_id': prog.vehiculo.id},
                )
            else:
                if existente.nivel != nivel or existente.dias_restantes != dias_restantes:
                    existente.nivel = nivel
                    existente.dias_restantes = dias_restantes
                    existente.pct_avance = pct_avance
                    existente.save()
                    actualizadas += 1

    registrar_log('ACTIVIDAD', 'generar_alertas_predictivas', request)
    return Response({'alertas_creadas': creadas, 'alertas_actualizadas': actualizadas})


# ─────────────────────────────────────────
# Notificaciones
# ─────────────────────────────────────────

from .models import Notificacion, NOTIF_PREFS_DEFAULT
from .serializers import NotificacionSerializer, PreferenciasNotificacionSerializer
from django.core.paginator import Paginator as _Paginator


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notificaciones_lista(request):
    qs = Notificacion.objects.filter(usuario=request.user)

    leida = request.query_params.get('leida')
    tipo  = request.query_params.get('tipo')
    if leida == 'false':
        qs = qs.filter(leida=False)
    elif leida == 'true':
        qs = qs.filter(leida=True)
    if tipo:
        qs = qs.filter(tipo=tipo)

    page_num  = max(1, int(request.query_params.get('page', 1)))
    paginator = _Paginator(qs, 20)
    page      = paginator.get_page(page_num)

    return Response({
        'count':     paginator.count,
        'num_pages': paginator.num_pages,
        'results':   NotificacionSerializer(page.object_list, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notificaciones_no_leidas(request):
    count = Notificacion.objects.filter(usuario=request.user, leida=False).count()
    return Response({'count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notificaciones_leer(request):
    todas = request.data.get('todas', False)
    ids   = request.data.get('ids', [])

    qs = Notificacion.objects.filter(usuario=request.user, leida=False)
    if not todas:
        qs = qs.filter(id__in=ids)
    updated = qs.update(leida=True)
    return Response({'marcadas': updated})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notificaciones_preferencias(request):
    usuario = request.user
    prefs   = usuario.notif_prefs or {}

    current = {
        'inapp':      prefs.get('inapp',      NOTIF_PREFS_DEFAULT['inapp']),
        'email':      prefs.get('email',      NOTIF_PREFS_DEFAULT['email']),
        'push_token': prefs.get('push_token', ''),
    }

    if request.method == 'GET':
        return Response(current)

    serializer = PreferenciasNotificacionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    usuario.notif_prefs = {
        'inapp':      serializer.validated_data['inapp'],
        'email':      serializer.validated_data['email'],
        'push_token': serializer.validated_data.get('push_token', current['push_token']),
    }
    usuario.save(update_fields=['notif_prefs'])
    return Response(usuario.notif_prefs)