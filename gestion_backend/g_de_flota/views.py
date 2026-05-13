import json
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Max, Subquery, OuterRef, IntegerField, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Coalesce
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from .models import (
    Empresa, Rol, Permiso, Usuario, Flota, Vehiculo, Asignacion,
    Mantencion, DocumentoVehiculo, LogAuditoria, normalizar_rut, TipoLog, PlanSuscripcion
)
from .audit import registrar_log
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
    return user.permisos.filter(codigo=codigo).exists()

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

    return Response({
        "kpis": {
            "empresas_activas":    empresas_activas,
            "empresas_inactivas":  empresas_inactivas,
            "total_usuarios":      total_usuarios,
            "total_conductores":   total_conductores,
            "total_vehiculos":     total_vehiculos,
            "empresas_nuevas_mes": empresas_nuevas_mes,
            "usuarios_activos_hoy": usuarios_activos_hoy,
        },
        "charts": {
            "crecimiento": {"labels": crecimiento_labels, "data": crecimiento_values},
            "distribucion_flota": {
                "labels": list(distribucion_flota.keys()),
                "data":   list(distribucion_flota.values()),
            },
            "top_empresas": top_empresas_data,
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def empresa_dashboard_view(request):
    # El dashboard es accesible a todo USUARIO y SUPERADMIN.
    # CONDUCTOR no tiene panel web.
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

    # KPIs
    total_flotas      = Flota.objects.filter(empresa=empresa).count()
    total_vehiculos   = Vehiculo.objects.filter(flota__empresa=empresa).count()
    total_conductores = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR).count()
    mantenciones_pendientes = Mantencion.objects.filter(
        vehiculo__flota__empresa=empresa, estado='pendiente'
    ).count()
    docs_por_vencer = DocumentoVehiculo.objects.filter(
        vehiculo__flota__empresa=empresa,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=30),
    ).count()

    MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    # Gráfico 1: Vehículos por flota (bar, siempre snapshot)
    flotas_qs = (
        Flota.objects.filter(empresa=empresa)
        .annotate(num_vehiculos=Count('vehiculos'))
        .order_by('-num_vehiculos')
    )
    bar_labels = [f.nombre for f in flotas_qs]
    bar_values = [f.num_vehiculos for f in flotas_qs]

    # Gráfico 2: Mantenciones programadas por período (fecha_programada es DateField)
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

    else:  # 12m — granularidad mensual
        hace_12_meses = hoy - timedelta(days=365)
        rows = (
            Mantencion.objects.filter(
                vehiculo__flota__empresa=empresa,
                fecha_programada__gte=hace_12_meses,
                fecha_programada__lte=hoy,
            )
            .annotate(mes=TruncMonth('fecha_programada'))
            .values('mes').annotate(total=Count('id')).order_by('mes')
        )
        meses_data = {}
        curr = hoy.replace(day=1)
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
        mant_labels, mant_values = [], []
        for k in reversed(list(meses_data.keys())):
            y, m = k.split('-')
            mant_labels.append(f"{MESES_ES[int(m) - 1]} {y[2:]}")
            mant_values.append(meses_data[k])

    return Response({
        "kpis": {
            "total_flotas":           total_flotas,
            "total_vehiculos":        total_vehiculos,
            "total_conductores":      total_conductores,
            "mantenciones_pendientes": mantenciones_pendientes,
            "docs_por_vencer":        docs_por_vencer,
        },
        "charts": {
            "vehiculos_por_flota": {"labels": bar_labels, "data": bar_values},
            "mantenciones":        {"labels": mant_labels, "data": mant_values},
        },
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
            LogAuditoria.objects.create(tipo=TipoLog.SEGURIDAD, accion='login_fallido', usuario=user_obj, ip=ip, detalle={'intentos': user_obj.intentos_fallidos, 'bloqueado': user_obj.is_blocked})
        else:
            LogAuditoria.objects.create(tipo=TipoLog.SEGURIDAD, accion='login_fallido', ip=ip, detalle={'motivo': 'usuario_no_encontrado'})

        return JsonResponse({"error": "Credenciales inválidas"}, status=401)

    # 3. Éxito: Resetear intentos y registrar acceso
    user.intentos_fallidos = 0
    user.save()
    LogAuditoria.objects.create(tipo=TipoLog.SEGURIDAD, accion='login_exitoso', usuario=user, ip=ip)

    login(request, user)
    get_token(request)  # fuerza que Django emita la cookie csrftoken en esta respuesta

    return JsonResponse({
        "message": "Login exitoso",
        "user": {
            "nombre":   user.nombre or user.email,
            "rut":      rut,
            "email":    user.email,
            "rol":      user.rol,
            "empresa":  user.empresa.nombre if user.empresa else None,
            "permisos": list(user.permisos.values_list('codigo', flat=True)),
        },
    })


# ─────────────────────────────────────────
# Empresas
# ─────────────────────────────────────────

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
        serializer.save()
        registrar_log('ACTIVIDAD', 'empresa_creada', request,
                      detalle={'empresa_nombre': serializer.data['nombre'], 'empresa_id': serializer.data['id']})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def empresas_detalle(request, pk):
    try:
        empresa = Empresa.objects.get(pk=pk)
    except Empresa.DoesNotExist:
        return Response({"error": "Empresa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not es_superadmin(request.user):
            return Response(EmpresaSerializer(empresa).data)

        # Respuesta extendida para SUPERADMIN
        cantidad_flotas = Flota.objects.filter(empresa=empresa).count()
        cantidad_vehiculos = Vehiculo.objects.filter(flota__empresa=empresa).count()
        cantidad_conductores = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR).count()
        cantidad_mantenciones = Mantencion.objects.filter(vehiculo__flota__empresa=empresa).count()
        cantidad_documentos = DocumentoVehiculo.objects.filter(vehiculo__flota__empresa=empresa).count()

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
            serializer.save()
            return Response(serializer.data)
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
        qs = Usuario.objects.filter(rol=Rol.USUARIO).select_related('empresa')
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
        qs = qs.filter(Q(email__icontains=q) | Q(rut_hash=rut_hash))

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

    serializer = UsuarioCrearSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        registrar_log('ACTIVIDAD', 'usuario_creado', request,
                      detalle={'usuario_email': user.email, 'rol': user.rol})
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
    if not es_superadmin(request.user):
        return Response({"error": "Solo el Superadmin puede resetear contraseñas."}, status=403)
    
    try:
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    rut_plain = usuario.rut
    if not rut_plain:
         return Response({"error": "No se pudo recuperar el RUT para el reset."}, status=400)
    
    usuario.set_password(rut_plain)
    usuario.save()
    registrar_log('SEGURIDAD', 'cambio_password', request,
                  detalle={'usuario_email': usuario.email, 'usuario_id': pk})

    return Response({"message": f"Contraseña reseteada exitosamente al RUT del usuario: {rut_plain}"})


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

    serializer = ConductorCrearSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        conductor = serializer.save()
        return Response(ConductorListSerializer(conductor).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def conductores_detalle(request, pk):
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
        if not tiene_permiso(request.user, 'conductores.ver'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        return Response(ConductorListSerializer(conductor).data)

    if request.method == 'PUT':
        if not tiene_permiso(request.user, 'conductores.editar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ConductorEditarSerializer(conductor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            conductor.refresh_from_db()
            return Response(ConductorListSerializer(conductor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'conductores.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
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

    serializer = FlotaSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        serializer.save(empresa=empresa)
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
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'flotas.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
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
        ).select_related('flota').order_by('patente')
        return Response(VehiculoSerializer(vehiculos, many=True, context={'empresa': empresa}).data)

    if not tiene_permiso(request.user, 'vehiculos.crear'):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    serializer = VehiculoSerializer(data=request.data, context={'empresa': empresa})
    if serializer.is_valid():
        serializer.save()
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
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'vehiculos.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
        vehiculo.activo = False
        vehiculo.save(update_fields=['activo'])
        return Response({"message": "Vehículo desactivado."})


# ─────────────────────────────────────────
# Planes
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def planes_lista_crear(request):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        planes = PlanSuscripcion.objects.all().order_by('id')
        return Response(PlanSuscripcionSerializer(planes, many=True).data)

    if request.method == 'POST':
        serializer = PlanSuscripcionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def planes_detalle(request, pk):
    if not es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        plan = PlanSuscripcion.objects.get(pk=pk)
    except PlanSuscripcion.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = PlanSuscripcionSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        plan.delete()
        return Response({"message": "Plan eliminado."})


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
        qs = qs.filter(Q(usuario__email__icontains=q) | Q(ip__icontains=q))
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
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    if usuario.rol != Rol.USUARIO:
        return Response({"error": "Los permisos solo aplican a usuarios con rol USUARIO."}, status=400)

    if request.method == 'GET':
        return Response({
            "usuario_id": usuario.pk,
            "permisos": list(usuario.permisos.values_list('codigo', flat=True)),
        })

    if request.method == 'PUT':
        codigos = request.data.get('permisos', [])
        permisos = Permiso.objects.filter(codigo__in=codigos)
        usuario.permisos.set(permisos)
        registrar_log('SEGURIDAD', 'cambio_permisos', request, detalle={
            'usuario_email': usuario.email,
            'permisos': list(usuario.permisos.values_list('codigo', flat=True)),
        })
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

    # Validar que el vehículo pertenece a la empresa
    vehiculo_id = request.data.get('vehiculo_id')
    if not Vehiculo.objects.filter(pk=vehiculo_id, flota__empresa=empresa).exists():
        return Response({"error": "Vehículo no válido."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = MantencionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
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
        
        # Check if marking as done
        data = request.data.copy()
        if data.get('estado') == 'realizada' and mantencion.estado != 'realizada':
            if not data.get('fecha_realizada'):
                data['fecha_realizada'] = timezone.now().date().isoformat()
            if not data.get('kilometraje_realizado') and mantencion.vehiculo.km_actuales:
                data['kilometraje_realizado'] = mantencion.vehiculo.km_actuales
                
        serializer = MantencionSerializer(mantencion, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not tiene_permiso(request.user, 'mantenciones.eliminar'):
            return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
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