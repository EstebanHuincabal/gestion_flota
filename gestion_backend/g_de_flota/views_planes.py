from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Empresa, Usuario, Flota, Vehiculo, PlanSuscripcion, CambioPlan,
    Rol, TipoNotificacion, Notificacion, Permiso
)
from .audit import registrar_log
from .notificaciones import notificar, notificar_admins_empresa
from .serializers import PlanSuscripcionSerializer, CambioPlanSerializer, PermisoSerializer


def _es_superadmin(user):
    return getattr(user, 'rol', None) == Rol.SUPERADMIN


# ─────────────────────────────────────────
# Helpers de enforcement (importables desde views.py)
# ─────────────────────────────────────────

def verificar_limite_plan(empresa, dimension):
    """
    Verifica si la empresa puede crear un nuevo recurso.
    dimension: 'flotas' | 'vehiculos' | 'conductores' | 'usuarios'
    Retorna: (puede: bool, error_response: JsonResponse | None, uso: int, limite: int, pct: int)
    Si puede crear → retorna (True, None, uso, limite, pct)
    Si no puede    → retorna (False, JsonResponse(403), uso, limite, pct)
    """
    if not empresa.plan:
        resp = JsonResponse({
            'error': 'La empresa no tiene un plan asignado. Contacta al administrador.',
            'codigo': 'SIN_PLAN',
        }, status=403)
        return False, resp, 0, 0, 0

    plan = empresa.plan

    conteos = {
        'flotas':      (Flota.objects.filter(empresa=empresa).count(),
                        plan.max_flotas),
        'vehiculos':   (Vehiculo.objects.filter(flota__empresa=empresa, activo=True).count(),
                        plan.max_vehiculos),
        'conductores': (Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR, is_active=True).count(),
                        plan.max_conductores),
        'usuarios':    (Usuario.objects.filter(empresa=empresa, is_active=True).exclude(rol=Rol.CONDUCTOR).count(),
                        plan.max_usuarios),
    }

    uso, limite = conteos.get(dimension, (0, 0))
    pct = round((uso / limite * 100) if limite > 0 else 0)

    if uso >= limite:
        ya_notificado = Notificacion.objects.filter(
            tipo=TipoNotificacion.LIMITE_PLAN,
            leida=False,
            extra__tipo_alerta='limite_plan',
            extra__dimension=dimension,
            usuario__empresa=empresa,
        ).exists()

        if not ya_notificado:
            notificar_admins_empresa(
                empresa=empresa,
                tipo=TipoNotificacion.LIMITE_PLAN,
                titulo=f'Límite de {dimension} alcanzado',
                mensaje=(
                    f'Tu empresa ha alcanzado el límite de {limite} {dimension} '
                    f'del plan {plan.get_nombre_display()}. '
                    f'Contacta al administrador para ampliar tu plan.'
                ),
                url_accion='/empresa/dashboard',
                extra={'tipo_alerta': 'limite_plan', 'dimension': dimension, 'uso': uso, 'limite': limite},
            )

        resp = JsonResponse({
            'error': (
                f'Has alcanzado el límite de {limite} {dimension} '
                f'de tu plan {plan.get_nombre_display()}. '
                f'Contacta al administrador para actualizar el plan.'
            ),
            'codigo':     'LIMITE_PLAN',
            'dimension':  dimension,
            'uso':        uso,
            'limite':     limite,
            'porcentaje': pct,
            'plan':       plan.get_nombre_display(),
        }, status=403)
        return False, resp, uso, limite, pct

    return True, None, uso, limite, pct


def verificar_modulo_plan(empresa, modulo):
    """
    Verifica si el plan de la empresa incluye el módulo dado.
    Retorna (habilitado: bool, mensaje: str)
    """
    if not empresa.plan:
        return True, ''
    modulos = empresa.plan.modulos or []
    if modulo in modulos:
        return True, ''
    return (
        False,
        f"El módulo '{modulo}' no está incluido en tu plan {empresa.plan.get_nombre_display()}.",
    )


# ─────────────────────────────────────────
# Planes — lista y creación
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def planes_lista_crear(request):
    if request.method == 'GET':
        if _es_superadmin(request.user):
            planes = PlanSuscripcion.objects.all().order_by('orden', 'id')
        else:
            planes = PlanSuscripcion.objects.filter(activo=True).order_by('orden', 'id')
        return Response(PlanSuscripcionSerializer(planes, many=True).data)

    if not _es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    serializer = PlanSuscripcionSerializer(data=request.data)
    if serializer.is_valid():
        plan = serializer.save()
        registrar_log('ACTIVIDAD', 'plan_creado', request,
                      detalle={'plan': plan.nombre, 'plan_id': plan.id})
        return Response(PlanSuscripcionSerializer(plan).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────
# Planes — detalle, edición, eliminación
# ─────────────────────────────────────────

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def planes_detalle(request, pk):
    if not _es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        plan = PlanSuscripcion.objects.get(pk=pk)
    except PlanSuscripcion.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(PlanSuscripcionSerializer(plan).data)

    if request.method == 'PUT':
        serializer = PlanSuscripcionSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            plan = serializer.save()
            registrar_log('ACTIVIDAD', 'plan_editado', request,
                          detalle={'plan': plan.nombre, 'plan_id': plan.id})
            return Response(PlanSuscripcionSerializer(plan).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        empresas_activas = plan.empresas.filter(estado='activa').count()
        if empresas_activas > 0:
            return Response(
                {"error": f"No se puede eliminar: {empresas_activas} empresa(s) activa(s) usa(n) este plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nombre = plan.get_nombre_display()
        plan.delete()
        registrar_log('ACTIVIDAD', 'plan_eliminado', request, detalle={'plan': nombre})
        return Response({"message": "Plan eliminado."})


# ─────────────────────────────────────────
# Asignar plan a empresa
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plan_asignar_empresa(request, pk):
    if not _es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        plan = PlanSuscripcion.objects.get(pk=pk)
    except PlanSuscripcion.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    empresa_id = request.data.get('empresa_id')
    motivo     = (request.data.get('motivo') or '').strip()

    if not empresa_id:
        return Response({"error": "Se requiere empresa_id."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        empresa = Empresa.objects.select_related('plan').get(pk=empresa_id)
    except Empresa.DoesNotExist:
        return Response({"error": "Empresa no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    plan_anterior = empresa.plan

    CambioPlan.objects.create(
        empresa      = empresa,
        plan_antes   = plan_anterior,
        plan_despues = plan,
        cambiado_por = request.user,
        motivo       = motivo,
    )

    empresa.plan = plan
    empresa.save(update_fields=['plan'])

    registrar_log('ACTIVIDAD', 'plan_asignado', request, detalle={
        'empresa':      empresa.nombre,
        'empresa_id':   empresa.id,
        'plan_antes':   plan_anterior.get_nombre_display() if plan_anterior else None,
        'plan_despues': plan.get_nombre_display(),
        'motivo':       motivo,
    })

    notificar_admins_empresa(
        empresa,
        TipoNotificacion.ACTIVIDAD,
        "Plan de suscripción actualizado",
        f"Tu plan ha sido actualizado a {plan.get_nombre_display()}. {motivo}".strip(),
        url_accion='/empresa/dashboard',
    )

    return Response({
        "message": f"Plan asignado correctamente a {empresa.nombre}.",
        "plan": PlanSuscripcionSerializer(plan).data,
    })


# ─────────────────────────────────────────
# Permisos por plan
# ─────────────────────────────────────────

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def plan_permisos(request, pk):
    if not _es_superadmin(request.user):
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)

    try:
        plan = PlanSuscripcion.objects.get(pk=pk)
    except PlanSuscripcion.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    todos = Permiso.objects.all().order_by('categoria', 'codigo')

    if request.method == 'GET':
        return Response({
            "plan_id":       plan.id,
            "plan_nombre":   plan.get_nombre_display(),
            "permisos_plan": list(plan.permisos.values_list('codigo', flat=True)),
            "todos_permisos": PermisoSerializer(todos, many=True).data,
        })

    codigos = request.data.get('permisos', [])
    nuevos  = Permiso.objects.filter(codigo__in=codigos)
    plan.permisos.set(nuevos)
    registrar_log('ACTIVIDAD', 'plan_permisos_editados', request,
                  detalle={'plan': plan.nombre, 'plan_id': plan.id, 'total': nuevos.count()})
    return Response({
        "permisos_plan": list(plan.permisos.values_list('codigo', flat=True)),
    })


# ─────────────────────────────────────────
# Uso del plan por empresa
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_uso(request):
    user = request.user

    if _es_superadmin(user):
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            return Response({"error": "Se requiere empresa_id."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            empresa = Empresa.objects.select_related('plan').get(pk=empresa_id)
        except Empresa.DoesNotExist:
            return Response({"error": "Empresa no encontrada."}, status=status.HTTP_404_NOT_FOUND)
    else:
        if not user.empresa_id:
            return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)
        empresa = Empresa.objects.select_related('plan').get(pk=user.empresa_id)

    if not empresa.plan:
        return Response({"plan": None, "uso": None, "alertas": []})

    plan = empresa.plan

    def _dim(actual, limite):
        pct = round(actual / limite * 100) if limite > 0 else 0
        return {"actual": actual, "limite": limite, "pct": pct}

    uso = {
        "flotas":      _dim(Flota.objects.filter(empresa=empresa).count(), plan.max_flotas),
        "vehiculos":   _dim(Vehiculo.objects.filter(flota__empresa=empresa).count(), plan.max_vehiculos),
        "conductores": _dim(Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR, is_active=True).count(), plan.max_conductores),
        "usuarios":    _dim(Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True).count(), plan.max_usuarios),
    }

    alertas = [
        {"dimension": key, **val, "nivel": "danger" if val["pct"] >= 100 else "warning"}
        for key, val in uso.items()
        if val["pct"] >= 80
    ]

    return Response({
        "plan":    PlanSuscripcionSerializer(plan).data,
        "uso":     uso,
        "alertas": alertas,
    })


# ─────────────────────────────────────────
# Solicitud de cambio de plan (USUARIO → SUPERADMIN)
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def solicitar_cambio_plan(request):
    user = request.user
    if user.rol != Rol.USUARIO:
        return Response({"error": "Sin permisos."}, status=status.HTTP_403_FORBIDDEN)
    if not user.empresa_id:
        return Response({"error": "Sin empresa asignada."}, status=status.HTTP_403_FORBIDDEN)

    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({"error": "Se requiere plan_id."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = PlanSuscripcion.objects.get(pk=plan_id, activo=True)
    except PlanSuscripcion.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    empresa     = Empresa.objects.select_related('plan').get(pk=user.empresa_id)
    plan_actual = empresa.plan

    if plan_actual and plan_actual.pk == plan.pk:
        return Response({"error": "Tu empresa ya tiene este plan activo."}, status=status.HTTP_400_BAD_REQUEST)

    # Notificar directamente (sin filtro de prefs) a todos los SUPERADMIN
    superadmins = Usuario.objects.filter(rol=Rol.SUPERADMIN, is_active=True)
    titulo_notif  = 'Solicitud de cambio de plan'
    mensaje_notif = (
        f'La empresa "{empresa.nombre}" solicita cambiar al plan '
        f'"{plan.get_nombre_display()}" '
        f'(plan actual: "{plan_actual.get_nombre_display() if plan_actual else "Sin plan"}").'
    )
    extra_notif = {'tipo': 'solicitud_plan', 'empresa_id': empresa.id, 'plan_id': plan.id}
    for sa in superadmins:
        notificar(sa, TipoNotificacion.ACTIVIDAD, titulo_notif, mensaje_notif,
                  url_accion='/empresas', extra=extra_notif, forzar=True)

    registrar_log('ACTIVIDAD', 'solicitud_cambio_plan', request,
                  detalle={'empresa': empresa.nombre, 'plan_solicitado': plan.nombre})

    return Response({"message": "Solicitud enviada. El administrador recibirá una notificación."})
