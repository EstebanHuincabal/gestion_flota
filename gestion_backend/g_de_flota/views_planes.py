import json
import logging
import uuid
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.utils import timezone

logger = logging.getLogger(__name__)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.conf import settings as django_settings
from django.core.mail import EmailMultiAlternatives
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Empresa, Usuario, Flota, Vehiculo, PlanSuscripcion, CambioPlan,
    Rol, TipoNotificacion, Notificacion, Permiso,
    ConfiguracionSistema, Suscripcion, PagoTransbank, TarjetaGuardada,
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
        # Re-notificar si no hay notificación no leída NI notificación en las últimas 24 horas
        from django.utils import timezone as tz
        hace_24h = tz.now() - tz.timedelta(hours=24)
        ya_notificado = Notificacion.objects.filter(
            tipo=TipoNotificacion.LIMITE_PLAN,
            extra__tipo_alerta='limite_plan',
            extra__dimension=dimension,
            usuario__empresa=empresa,
            fecha__gte=hace_24h,
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
@transaction.atomic
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

    # ── Detectar tipo de cambio ───────────────────────────────────────────────
    if plan_anterior is None:
        tipo_cambio = 'nuevo'
    elif plan_anterior.pk == plan.pk:
        tipo_cambio = 'sin_cambio'
    else:
        p_ant = plan_anterior.precio_mensual or 0
        p_nvo = plan.precio_mensual or 0
        if p_nvo > p_ant:
            tipo_cambio = 'upgrade'
        elif p_nvo < p_ant:
            tipo_cambio = 'downgrade'
        else:
            tipo_cambio = 'lateral'

    # ── Verificar límites si es downgrade ────────────────────────────────────
    advertencias = []
    if tipo_cambio in ('downgrade', 'lateral') and plan_anterior:
        uso_flotas      = Flota.objects.filter(empresa=empresa).count()
        uso_vehiculos   = Vehiculo.objects.filter(flota__empresa=empresa, activo=True).count()
        uso_conductores = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR, is_active=True).count()
        uso_usuarios    = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO,    is_active=True).count()

        if uso_flotas      > plan.max_flotas:
            advertencias.append(f'Flotas: tiene {uso_flotas} (nuevo límite: {plan.max_flotas})')
        if uso_vehiculos   > plan.max_vehiculos:
            advertencias.append(f'Vehículos: tiene {uso_vehiculos} (nuevo límite: {plan.max_vehiculos})')
        if uso_conductores > plan.max_conductores:
            advertencias.append(f'Conductores: tiene {uso_conductores} (nuevo límite: {plan.max_conductores})')
        if uso_usuarios    > plan.max_usuarios:
            advertencias.append(f'Usuarios: tiene {uso_usuarios} (nuevo límite: {plan.max_usuarios})')

    CambioPlan.objects.create(
        empresa      = empresa,
        plan_antes   = plan_anterior,
        plan_despues = plan,
        cambiado_por = request.user,
        motivo       = motivo,
    )

    empresa.plan = plan
    empresa.save(update_fields=['plan'])

    # Crear o actualizar la suscripción de la empresa
    sus_existente = Suscripcion.objects.filter(empresa=empresa).first()

    if sus_existente is None:
        Suscripcion.objects.create(
            empresa = empresa,
            plan    = plan,
            ciclo   = 'mensual',
            estado  = 'pendiente',
        )
    else:
        sus_existente.plan = plan
        sus_existente.save(update_fields=['plan'])

    registrar_log('ACTIVIDAD', 'plan_asignado', request, detalle={
        'empresa':      empresa.nombre,
        'empresa_id':   empresa.id,
        'plan_antes':   plan_anterior.get_nombre_display() if plan_anterior else None,
        'plan_despues': plan.get_nombre_display(),
        'tipo_cambio':  tipo_cambio,
        'motivo':       motivo,
        'advertencias': advertencias,
    })

    # ── Notificación a la empresa con mensaje según tipo de cambio ────────────
    if tipo_cambio == 'upgrade':
        titulo_notif = '📈 Plan mejorado'
        cuerpo_notif = (
            f'Tu plan fue actualizado a {plan.get_nombre_display()} (plan superior). '
            f'Los nuevos límites y módulos están disponibles de inmediato. '
            f'El próximo cobro será al precio del nuevo plan. {motivo}'
        ).strip()
    elif tipo_cambio == 'downgrade':
        titulo_notif = '📉 Plan ajustado'
        cuerpo_notif = (
            f'Tu plan fue ajustado a {plan.get_nombre_display()} (plan inferior). '
            f'Los nuevos límites aplican de inmediato. '
            f'El próximo cobro será al precio del nuevo plan. {motivo}'
        ).strip()
    elif tipo_cambio == 'nuevo':
        titulo_notif = '🎉 Plan asignado'
        cuerpo_notif = (
            f'Se te asignó el plan {plan.get_nombre_display()}. '
            f'Realiza el pago para activar tu acceso al sistema. {motivo}'
        ).strip()
    else:
        titulo_notif = 'Plan de suscripción actualizado'
        cuerpo_notif = f'Tu plan ha sido actualizado a {plan.get_nombre_display()}. {motivo}'.strip()

    if tipo_cambio != 'sin_cambio':
        notificar_admins_empresa(
            empresa,
            TipoNotificacion.ACTIVIDAD,
            titulo_notif,
            cuerpo_notif,
            url_accion='/empresa/dashboard',
        )

    return Response({
        'message':      f"Plan asignado correctamente a {empresa.nombre}.",
        'plan':         PlanSuscripcionSerializer(plan).data,
        'tipo_cambio':  tipo_cambio,
        'advertencias': advertencias,
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


# ─────────────────────────────────────────────────────────────────────────────
# Transbank Webpay Plus — helpers y vistas
# ─────────────────────────────────────────────────────────────────────────────

def _get_webpay_transaction():
    """Devuelve una instancia de Transaction configurada según el entorno."""
    try:
        from transbank.webpay.webpay_plus.transaction import Transaction
        from transbank.common.options import WebpayOptions
        from transbank.common.integration_type import IntegrationType
    except ImportError:
        raise ImportError("transbank-sdk no está instalado. Ejecuta: pip install transbank-sdk>=4.0.0")

    env = getattr(django_settings, 'TRANSBANK_ENVIRONMENT', 'integration')
    commerce_code = django_settings.TRANSBANK_COMMERCE_CODE
    api_key       = django_settings.TRANSBANK_API_KEY

    if env == 'production':
        options = WebpayOptions(
            commerce_code=commerce_code,
            api_key=api_key,
            integration_type=IntegrationType.LIVE,
        )
    else:
        options = WebpayOptions(
            commerce_code=commerce_code,
            api_key=api_key,
            integration_type=IntegrationType.TEST,
        )
    return Transaction(options)


def _get_oneclick_inscription():
    """Devuelve una instancia de MallInscription (OneClick) según el entorno."""
    try:
        from transbank.webpay.oneclick.mall_inscription import MallInscription
        from transbank.common.options import WebpayOptions
        from transbank.common.integration_type import IntegrationType
    except ImportError:
        raise ImportError("transbank-sdk no está instalado.")

    env  = getattr(django_settings, 'TRANSBANK_ENVIRONMENT', 'integration')
    code = django_settings.ONECLICK_COMMERCE_CODE
    key  = django_settings.TRANSBANK_API_KEY
    itype = IntegrationType.LIVE if env == 'production' else IntegrationType.TEST
    return MallInscription(WebpayOptions(commerce_code=code, api_key=key, integration_type=itype))


def _get_oneclick_transaction():
    """Devuelve una instancia de MallTransaction (OneClick) según el entorno."""
    try:
        from transbank.webpay.oneclick.mall_transaction import MallTransaction
        from transbank.common.options import WebpayOptions
        from transbank.common.integration_type import IntegrationType
    except ImportError:
        raise ImportError("transbank-sdk no está instalado.")

    env  = getattr(django_settings, 'TRANSBANK_ENVIRONMENT', 'integration')
    code = django_settings.ONECLICK_COMMERCE_CODE
    key  = django_settings.TRANSBANK_API_KEY
    itype = IntegrationType.LIVE if env == 'production' else IntegrationType.TEST
    return MallTransaction(WebpayOptions(commerce_code=code, api_key=key, integration_type=itype))


# ─────────────────────────────────────────
# POST /api/pago/iniciar/
# ─────────────────────────────────────────

class PagoIniciarView(APIView):
    """
    Inicia un pago. Soporta dos modos:
      - usar_tarjeta=false (default): Webpay Plus → devuelve {url, token}
      - usar_tarjeta=true: OneClick Mall → cobra directamente y devuelve {ok, cobrado, ...}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'rol', None) != 'USUARIO':
            return Response({'error': 'Sin acceso.'}, status=403)

        plan_id       = request.data.get('plan_id')
        ciclo         = request.data.get('ciclo', 'mensual')
        usar_tarjeta  = request.data.get('usar_tarjeta', False)
        empresa       = request.user.empresa

        if not empresa:
            return Response({'error': 'Sin empresa asignada.'}, status=403)

        try:
            plan = PlanSuscripcion.objects.get(id=plan_id, activo=True)
        except PlanSuscripcion.DoesNotExist:
            return Response({'error': 'Plan no encontrado.'}, status=404)

        # ── Bloqueo temporal: no se puede pagar si la suscripción aún tiene > 7 días ──
        sus_existente = Suscripcion.objects.filter(empresa=empresa).first()
        if sus_existente and sus_existente.estado == 'activa':
            dias = sus_existente.dias_para_vencer
            if dias is not None and dias > 7:
                fecha_str = sus_existente.fecha_fin_periodo.strftime('%d/%m/%Y') \
                            if sus_existente.fecha_fin_periodo else None
                return Response({
                    'error':         f'Tu suscripción está activa hasta el {fecha_str}.',
                    'codigo':        'PAGO_NO_PERMITIDO',
                    'proxima_fecha': fecha_str,
                    'dias_restantes': dias,
                }, status=400)

        monto = int(plan.precio_anual if ciclo == 'anual' else plan.precio_mensual or 0)
        if not monto:
            return Response({'error': 'Este plan no tiene precio configurado.'}, status=400)

        # Idempotencia: bloquear si ya hay un pago iniciado en los últimos 3 minutos
        desde = timezone.now() - timezone.timedelta(minutes=3)
        pago_reciente = PagoTransbank.objects.filter(
            empresa=empresa, estado='iniciado', created_at__gte=desde,
        ).first()
        if pago_reciente:
            return Response({
                'error': 'Ya hay un pago en proceso. Espera unos minutos antes de intentar nuevamente.',
                'codigo': 'PAGO_EN_PROCESO',
            }, status=400)

        orden_compra = f"ORD-{empresa.id}-{uuid.uuid4().hex[:8].upper()}"

        # ── Modo OneClick: cobro con tarjeta guardada ─────────────────────────────
        if usar_tarjeta:
            try:
                tarjeta = empresa.tarjeta_guardada
            except TarjetaGuardada.DoesNotExist:
                return Response({'error': 'No tienes una tarjeta guardada.'}, status=400)

            child_order = f"CHD-{empresa.id}-{uuid.uuid4().hex[:8].upper()}"
            sus, _ = Suscripcion.objects.get_or_create(
                empresa=empresa,
                defaults={'plan': plan, 'ciclo': ciclo, 'estado': 'pendiente'},
            )

            try:
                tx = _get_oneclick_transaction()
                oc_resp = tx.authorize(
                    user_name=tarjeta.username_tb,
                    tbk_user=tarjeta.tbk_user,
                    parent_buy_order=orden_compra,
                    details=[{
                        'commerce_code':       django_settings.ONECLICK_CHILD_CODE,
                        'buy_order':           child_order,
                        'amount':              monto,
                        'installments_number': 1,
                    }],
                )
            except Exception as e:
                import traceback
                print(f"[ONECLICK ERROR] {traceback.format_exc()}")
                registrar_log('SEGURIDAD', 'oneclick_error', request, detalle={'error': str(e)})
                return Response({'error': f'Error al cobrar con tarjeta guardada: {str(e)}'}, status=502)

            # Verificar resultado del cobro
            if isinstance(oc_resp, dict):
                details = oc_resp.get('details', [])
            else:
                details = getattr(oc_resp, 'details', [])

            if details:
                det = details[0]
                resp_code = det.get('response_code', -1) if isinstance(det, dict) else getattr(det, 'response_code', -1)
                auth_code = det.get('authorization_code', '') if isinstance(det, dict) else getattr(det, 'authorization_code', '')
            else:
                resp_code = -1
                auth_code = ''

            if resp_code != 0:
                return Response({'error': 'El cobro fue rechazado por Transbank.'}, status=400)

            # Pago aprobado → actualizar suscripción
            PagoTransbank.objects.create(
                empresa=empresa, suscripcion=sus,
                token=f"OC-{orden_compra}",
                orden_compra=orden_compra,
                monto=monto, ciclo=ciclo,
                plan_nombre=plan.get_nombre_display(),
                estado='aprobado',
                fecha_pago=timezone.now(),
                respuesta_tb={'auth_code': auth_code, 'response_code': resp_code, 'via': 'oneclick'},
            )
            sus.ciclo  = ciclo
            sus.estado = 'activa'
            sus.plan   = plan
            sus.fecha_inicio      = timezone.now()
            sus.fecha_fin_periodo = (
                timezone.now() + timezone.timedelta(days=365)
                if ciclo == 'anual'
                else timezone.now() + timezone.timedelta(days=30)
            )
            sus.save()
            empresa.plan = plan
            empresa.save(update_fields=['plan'])

            notificar_admins_empresa(
                empresa=empresa, tipo='actividad',
                titulo='Pago automático procesado',
                mensaje=(
                    f'Se cobró {monto:,} CLP con tu tarjeta guardada '
                    f'({tarjeta.card_type} ****{tarjeta.last_4}). '
                    f'Próximo cobro: {sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.'
                ),
            )
            registrar_log('ACTIVIDAD', 'pago_oneclick', request, detalle={
                'plan': plan.nombre, 'monto': monto, 'ciclo': ciclo,
            })
            return Response({
                'ok': True, 'cobrado': True,
                'monto': monto,
                'plan':  plan.get_nombre_display(),
                'nueva_fecha_fin': sus.fecha_fin_periodo.strftime('%d/%m/%Y'),
            })

        # ── Modo Webpay Plus (nueva tarjeta) ──────────────────────────────────────
        session_id = f"SES-{request.user.id}-{uuid.uuid4().hex[:6]}"
        return_url = request.build_absolute_uri('/api/pago/retorno/')

        try:
            tx       = _get_webpay_transaction()
            response = tx.create(
                buy_order=orden_compra,
                session_id=session_id,
                amount=monto,
                return_url=return_url,
            )
        except Exception as e:
            import traceback
            print(f"[TRANSBANK ERROR] {traceback.format_exc()}")
            registrar_log('SEGURIDAD', 'pago_error_crear', request, detalle={'error': str(e)})
            return Response({'error': f'Error al conectar con Transbank: {str(e)}'}, status=502)

        sus, _ = Suscripcion.objects.get_or_create(
            empresa=empresa,
            defaults={'plan': plan, 'ciclo': ciclo, 'estado': 'trial'},
        )

        token_tb = response.get('token') if isinstance(response, dict) else getattr(response, 'token', None)
        url_tb   = response.get('url')   if isinstance(response, dict) else getattr(response, 'url', None)

        print(f"[TRANSBANK] token={token_tb!r}  url={url_tb!r}")

        if not token_tb or not url_tb:
            return Response({'error': 'Transbank no devolvió token/url válidos.'}, status=502)

        PagoTransbank.objects.create(
            empresa=empresa, suscripcion=sus,
            token=token_tb, orden_compra=orden_compra,
            monto=monto, ciclo=ciclo,
            plan_nombre=plan.get_nombre_display(),
        )

        registrar_log('ACTIVIDAD', 'pago_iniciado', request, detalle={
            'plan': plan.nombre, 'monto': monto, 'ciclo': ciclo,
        })

        return Response({'url': url_tb, 'token': token_tb})


# ─────────────────────────────────────────
# POST /api/pago/retorno/  (retorno desde Transbank)
# ─────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class PagoRetornoView(View):
    """
    Endpoint de retorno desde Transbank.
    Webpay puede redirigir con GET (?token_ws=...) o con POST (body token_ws).
    Confirma la transacción y redirige al frontend.
    """

    def get(self, request):
        """Transbank redirige al navegador del usuario con GET + ?token_ws=..."""
        return self._procesar(request, request.GET.get('token_ws'))

    def post(self, request):
        """Compatibilidad con versiones que envían token_ws por POST body."""
        token_ws = request.POST.get('token_ws') or request.GET.get('token_ws')
        return self._procesar(request, token_ws)

    def _procesar(self, request, token_ws):
        if not token_ws:
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/fallido?error=sin_token")

        try:
            pago = PagoTransbank.objects.select_related(
                'empresa', 'suscripcion', 'suscripcion__plan',
            ).get(token=token_ws)
        except PagoTransbank.DoesNotExist:
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/fallido?error=token_invalido")

        # Evitar doble commit si el pago ya fue procesado
        if pago.estado in ('aprobado', 'rechazado'):
            if pago.estado == 'aprobado':
                return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/exitoso?orden={pago.orden_compra}")
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/fallido?error=rechazado")

        try:
            tx       = _get_webpay_transaction()
            response = tx.commit(token_ws)

            resp_dict = response if isinstance(response, dict) else vars(response)
            pago.respuesta_tb = resp_dict
            pago.fecha_pago   = timezone.now()

            resp_code = resp_dict.get('response_code', -1)

            if resp_code == 0:
                pago.estado = 'aprobado'
                pago.save()

                sus        = pago.suscripcion
                sus.ciclo  = pago.ciclo
                sus.estado = 'activa'
                sus.fecha_inicio      = timezone.now()
                sus.fecha_fin_periodo = (
                    timezone.now() + timezone.timedelta(days=365)
                    if pago.ciclo == 'anual'
                    else timezone.now() + timezone.timedelta(days=30)
                )
                sus.save()

                # Sincronizar plan en Empresa
                sus.empresa.plan = sus.plan
                sus.empresa.save(update_fields=['plan'])

                notificar_admins_empresa(
                    empresa=pago.empresa,
                    tipo='actividad',
                    titulo='Pago procesado correctamente',
                    mensaje=(
                        f'Tu plan {sus.plan.get_nombre_display()} está activo. '
                        f'Próximo cobro: {sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.'
                    ),
                    extra={'pago_id': pago.id},
                )

                # ── Email de pago aprobado ───────────────────────────────────
                try:
                    from .email_service import email_pago_aprobado
                    admins = Usuario.objects.filter(
                        empresa=pago.empresa, rol=Rol.USUARIO, is_active=True,
                    )
                    for admin in admins:
                        email_pago_aprobado(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=pago.empresa.nombre,
                            plan_nombre=pago.plan_nombre,
                            monto=pago.monto,
                            ciclo=pago.ciclo,
                            fecha_proximo_cobro=sus.fecha_fin_periodo.strftime('%d/%m/%Y'),
                            orden_compra=pago.orden_compra,
                        )
                except Exception as e_email:
                    logger.error('Email pago aprobado falló para empresa %s: %s', pago.empresa.nombre, e_email)

                registrar_log('ACTIVIDAD', 'pago_aprobado', request, detalle={
                    'empresa_id': pago.empresa.id,
                    'monto':      pago.monto,
                    'plan':       pago.plan_nombre,
                })

                return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/exitoso?orden={pago.orden_compra}")

            else:
                pago.estado = 'rechazado'
                pago.save()

                notificar_admins_empresa(
                    empresa=pago.empresa,
                    tipo='seguridad',
                    titulo='Pago rechazado',
                    mensaje='Tu pago fue rechazado por Transbank. Intenta nuevamente.',
                    extra={'pago_id': pago.id},
                )

                # ── Email de pago rechazado ──────────────────────────────────
                try:
                    from .email_service import email_pago_rechazado
                    admins = Usuario.objects.filter(
                        empresa=pago.empresa, rol=Rol.USUARIO, is_active=True,
                    )
                    for admin in admins:
                        email_pago_rechazado(
                            email=admin.email,
                            nombre=admin.nombre or admin.email,
                            empresa_nombre=pago.empresa.nombre,
                            monto=pago.monto,
                            url_reintentar=f"{django_settings.FRONTEND_URL}/empresa/pago",
                        )
                except Exception as e_email:
                    logger.error('Email pago rechazado falló para empresa %s: %s', pago.empresa.nombre, e_email)

                return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/fallido?error=rechazado")

        except Exception as e:
            import traceback
            print(f"[TRANSBANK COMMIT ERROR] {traceback.format_exc()}")
            pago.estado = 'fallido'
            pago.save()
            registrar_log('SEGURIDAD', 'pago_error', request, detalle={'error': str(e), 'pago_id': pago.id})
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago/fallido?error=error_sistema")


# ─────────────────────────────────────────
# GET /api/pago/historial/
# ─────────────────────────────────────────

class PagoHistorialView(APIView):
    """Historial de pagos aprobados (USUARIO ve su empresa; SUPERADMIN puede filtrar)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'rol', None) not in ('USUARIO', 'SUPERADMIN'):
            return Response({'error': 'Sin acceso.'}, status=403)

        if request.user.rol == 'SUPERADMIN':
            empresa_id = request.query_params.get('empresa_id')
            if not empresa_id:
                return Response({'error': 'Se requiere empresa_id.'}, status=400)
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                return Response({'error': 'Empresa no encontrada.'}, status=404)
        else:
            empresa = request.user.empresa

        pagos = PagoTransbank.objects.filter(
            empresa=empresa, estado='aprobado',
        ).select_related('empresa', 'suscripcion__plan')

        data = [{
            'id':             p.id,
            'orden_compra':   p.orden_compra,
            'monto':          p.monto,
            'plan':           p.plan_nombre,
            'ciclo':          p.ciclo,
            'fecha':          p.fecha_pago.strftime('%d/%m/%Y %H:%M') if p.fecha_pago else None,
            'estado':         p.estado,
            'empresa_nombre': p.empresa.nombre,
            'empresa_rut':    getattr(p.empresa, 'rut', '') or '',
            'via':            p.respuesta_tb.get('via', 'webpay') if p.respuesta_tb else 'webpay',
        } for p in pagos]

        return Response({'pagos': data})


# ─────────────────────────────────────────
# GET/PUT /api/admin/terminos/
# ─────────────────────────────────────────

class TerminosView(APIView):
    """Gestión de términos y configuración de pagos (solo SUPERADMIN)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        config = ConfiguracionSistema.get()
        return Response({
            'terminos':        config.terminos_condiciones,
            'version':         config.terminos_version,
            'updated_at':      config.terminos_updated_at.isoformat() if config.terminos_updated_at else None,
            'dias_gracia':     config.dias_gracia_pago,
            'bloqueo_auto':    config.bloqueo_automatico,
            'mensaje_bloqueo': config.mensaje_pago_pendiente,
            'ambiente_tb':     getattr(django_settings, 'TRANSBANK_ENVIRONMENT', 'integration').upper(),
        })

    def put(self, request):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        body   = request.data
        config = ConfiguracionSistema.get()
        if 'terminos' in body:
            config.terminos_condiciones = body['terminos']
            config.terminos_version     = body.get('version', config.terminos_version)
            config.terminos_updated_at  = timezone.now()
        if 'dias_gracia'     in body: config.dias_gracia_pago      = body['dias_gracia']
        if 'bloqueo_auto'    in body: config.bloqueo_automatico     = body['bloqueo_auto']
        if 'mensaje_bloqueo' in body: config.mensaje_pago_pendiente = body['mensaje_bloqueo']
        config.save()

        registrar_log('ACTIVIDAD', 'terminos_actualizados', request, detalle={
            'version': config.terminos_version,
        })
        return Response({'ok': True})


# ─────────────────────────────────────────
# GET /api/terminos/  (público)
# ─────────────────────────────────────────

class TerminosPublicosView(APIView):
    """Devuelve los términos vigentes sin requerir autenticación."""
    permission_classes = [AllowAny]

    def get(self, request):
        config = ConfiguracionSistema.get()
        return Response({
            'terminos': config.terminos_condiciones,
            'version':  config.terminos_version,
            'fecha':    config.terminos_updated_at.strftime('%d/%m/%Y') if config.terminos_updated_at else None,
        })


# ─────────────────────────────────────────
# POST /api/empresa/terminos/aceptar/
# ─────────────────────────────────────────

class TerminosAceptarView(APIView):
    """Registra que el usuario aceptó los términos (versión y fecha)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        version = request.data.get('version', '')
        extra = request.user.extra or {}
        extra.update({
            'terminos_version':     version,
            'terminos_aceptado_at': timezone.now().isoformat(),
        })
        request.user.extra = extra
        request.user.save(update_fields=['extra'])
        return Response({'ok': True})


# ─────────────────────────────────────────
# GET /api/empresa/suscripcion/
# ─────────────────────────────────────────

class SuscripcionEmpresaView(APIView):
    """Devuelve el estado de la suscripción de la empresa del usuario."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'suscripcion': None})

        try:
            sus = empresa.suscripcion
        except Suscripcion.DoesNotExist:
            return Response({'suscripcion': None})

        return Response({
            'suscripcion': {
                'estado':            sus.estado,
                'ciclo':             sus.ciclo,
                'plan':              sus.plan.get_nombre_display() if sus.plan else None,
                'fecha_fin_periodo': sus.fecha_fin_periodo.strftime('%d/%m/%Y') if sus.fecha_fin_periodo else None,
                'dias_para_vencer':  sus.dias_para_vencer,
                'esta_bloqueada':    sus.esta_bloqueada,
            }
        })


# ─────────────────────────────────────────
# GET/PUT /api/admin/suscripciones/<id>/
# ─────────────────────────────────────────

class SuscripcionesAdminView(APIView):
    """Lista todas las suscripciones o modifica una (SUPERADMIN)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, sus_id=None):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        suscripciones = Suscripcion.objects.select_related(
            'empresa', 'plan',
        ).order_by('-created_at')

        estado = request.query_params.get('estado')
        buscar = request.query_params.get('q', '').strip()
        if estado:
            suscripciones = suscripciones.filter(estado=estado)
        if buscar:
            suscripciones = suscripciones.filter(empresa__nombre__icontains=buscar)

        from django.db.models import Sum
        ahora      = timezone.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        mrr = PagoTransbank.objects.filter(
            estado='aprobado',
            ciclo='mensual',
            fecha_pago__gte=inicio_mes,
        ).aggregate(total=Sum('monto'))['total'] or 0

        data = []
        for s in suscripciones:
            ultimo_pago = s.pagos.filter(estado='aprobado').first()
            data.append({
                'id':               s.id,
                'empresa':          s.empresa.nombre,
                'empresa_id':       s.empresa.id,
                'plan':             s.plan.get_nombre_display() if s.plan else None,
                'ciclo':            s.ciclo,
                'estado':           s.estado,
                'fecha_fin':        s.fecha_fin_periodo.strftime('%d/%m/%Y') if s.fecha_fin_periodo else None,
                'dias_para_vencer': s.dias_para_vencer,
                'ultimo_pago':      ultimo_pago.fecha_pago.strftime('%d/%m/%Y') if ultimo_pago and ultimo_pago.fecha_pago else None,
            })

        activas     = Suscripcion.objects.filter(estado='activa').count()
        pendientes  = Suscripcion.objects.filter(estado='pendiente').count()
        en_gracia   = Suscripcion.objects.filter(estado='gracia').count()
        suspendidas = Suscripcion.objects.filter(estado='suspendida').count()

        return Response({
            'suscripciones': data,
            'kpis': {
                'mrr':         mrr,
                'activas':     activas,
                'pendientes':  pendientes,
                'en_gracia':   en_gracia,
                'suspendidas': suspendidas,
            },
        })

    def put(self, request, sus_id=None):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        if sus_id is None:
            return Response({'error': 'Se requiere ID de suscripción.'}, status=400)

        try:
            sus = Suscripcion.objects.select_related('empresa').get(id=sus_id)
        except Suscripcion.DoesNotExist:
            return Response({'error': 'Suscripción no encontrada.'}, status=404)

        accion = request.data.get('accion')

        if accion == 'reactivar':
            sus.estado = 'activa'
            sus.fecha_fin_periodo = timezone.now() + timezone.timedelta(days=30)
            sus.empresa.estado = 'activa'
            sus.empresa.save(update_fields=['estado'])
            sus.save()
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='actividad',
                titulo='Suscripción reactivada',
                mensaje='Tu suscripción ha sido reactivada por el administrador.',
            )
            registrar_log('ACTIVIDAD', 'suscripcion_reactivada', request, detalle={
                'empresa_id': sus.empresa.id,
                'empresa':    sus.empresa.nombre,
            })
            return Response({'ok': True, 'estado': sus.estado})

        elif accion == 'extender_gracia':
            dias_extra = int(request.data.get('dias', 7))
            if sus.fecha_fin_periodo:
                sus.fecha_fin_periodo += timezone.timedelta(days=dias_extra)
            sus.save()
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='actividad',
                titulo=f'Período de gracia extendido {dias_extra} días',
                mensaje=f'El administrador extendió tu período de gracia {dias_extra} días más.',
            )
            registrar_log('ACTIVIDAD', 'gracia_extendida', request, detalle={
                'empresa_id': sus.empresa.id,
                'dias_extra': dias_extra,
            })
            return Response({'ok': True})

        elif accion == 'pago_manual':
            # Registra un pago manual (transferencia, efectivo, etc.) y activa la suscripción
            ciclo  = request.data.get('ciclo', 'mensual')
            monto  = int(request.data.get('monto', 0))
            metodo = request.data.get('metodo', 'Transferencia bancaria')
            nota   = request.data.get('nota', '').strip()

            if not monto:
                return Response({'error': 'El monto es requerido.'}, status=400)

            ahora = timezone.now()
            dias_periodo = 365 if ciclo == 'anual' else 30

            # Si ya tiene fecha activa, extender desde ahí; si no, desde hoy
            base = sus.fecha_fin_periodo if sus.fecha_fin_periodo and sus.fecha_fin_periodo > ahora else ahora

            sus.estado           = 'activa'
            sus.ciclo            = ciclo
            sus.fecha_inicio     = ahora
            sus.fecha_fin_periodo = base + timezone.timedelta(days=dias_periodo)
            sus.empresa.estado   = 'activa'
            sus.empresa.save(update_fields=['estado'])
            sus.save()

            import uuid
            PagoTransbank.objects.create(
                empresa      = sus.empresa,
                suscripcion  = sus,
                token        = f"MANUAL-{uuid.uuid4().hex[:12].upper()}",
                orden_compra = f"MANUAL-{sus.empresa.id}-{uuid.uuid4().hex[:8].upper()}",
                monto        = monto,
                ciclo        = ciclo,
                plan_nombre  = sus.plan.get_nombre_display() if sus.plan else '',
                estado       = 'aprobado',
                fecha_pago   = ahora,
                respuesta_tb = {
                    'via':    'manual',
                    'metodo': metodo,
                    'nota':   nota,
                    'registrado_por': request.user.email,
                },
            )

            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='actividad',
                titulo='Pago registrado — suscripción activada',
                mensaje=(
                    f'El administrador registró un pago de ${monto:,} CLP '
                    f'({metodo}). Tu suscripción está activa hasta el '
                    f'{sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.'
                ),
            )
            registrar_log('ACTIVIDAD', 'pago_manual_registrado', request, detalle={
                'empresa_id': sus.empresa.id,
                'empresa':    sus.empresa.nombre,
                'monto':      monto,
                'ciclo':      ciclo,
                'metodo':     metodo,
            })
            return Response({
                'ok':        True,
                'estado':    sus.estado,
                'fecha_fin': sus.fecha_fin_periodo.strftime('%d/%m/%Y'),
            })

        return Response({'error': 'Acción no reconocida.'}, status=400)


# ═══════════════════════════════════════════════════════════════════════════════
# OneClick Mall — tarjeta guardada para cobros automáticos
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────
# GET /api/empresa/tarjeta/
# ─────────────────────────────────────────

class TarjetaEstadoView(APIView):
    """Devuelve la tarjeta guardada de la empresa o null."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'rol', None) != 'USUARIO':
            return Response({'tarjeta': None})
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'tarjeta': None})
        try:
            t = empresa.tarjeta_guardada
            return Response({'tarjeta': {
                'card_type':  t.card_type,
                'last_4':     t.last_4,
                'created_at': t.created_at.strftime('%d/%m/%Y'),
            }})
        except TarjetaGuardada.DoesNotExist:
            return Response({'tarjeta': None})


# ─────────────────────────────────────────
# POST /api/empresa/tarjeta/inscribir/
# ─────────────────────────────────────────

class TarjetaInscribirView(APIView):
    """Inicia la inscripción de tarjeta con OneClick Mall."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'rol', None) != 'USUARIO':
            return Response({'error': 'Sin acceso.'}, status=403)

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Sin empresa asignada.'}, status=403)

        # No permitir si ya tiene tarjeta guardada
        try:
            empresa.tarjeta_guardada
            return Response({'error': 'Ya tienes una tarjeta guardada. Elimínala primero.'}, status=400)
        except TarjetaGuardada.DoesNotExist:
            pass

        username   = f"emp-{empresa.id}"
        email      = request.user.email or f"empresa{empresa.id}@gestionflota.cl"
        return_url = request.build_absolute_uri('/api/empresa/tarjeta/retorno/')

        try:
            insc     = _get_oneclick_inscription()
            response = insc.start(username=username, email=email, response_url=return_url)
        except Exception as e:
            import traceback
            print(f"[ONECLICK INSCRIPCION ERROR] {traceback.format_exc()}")
            return Response({'error': f'Error al iniciar inscripción: {str(e)}'}, status=502)

        if isinstance(response, dict):
            token = response.get('token')
            url   = response.get('url_webpay')
        else:
            token = getattr(response, 'token', None)
            url   = getattr(response, 'url_webpay', None)

        if not token or not url:
            return Response({'error': 'Transbank no devolvió datos de inscripción.'}, status=502)

        return Response({'url': url, 'token': token})


# ─────────────────────────────────────────
# GET /api/empresa/tarjeta/retorno/
# ─────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class TarjetaInscripcionRetornoView(View):
    """
    Transbank redirige aquí después de que el usuario inscribe su tarjeta.
    Llama a finish(), guarda TarjetaGuardada y redirige al frontend.
    """

    def get(self, request):
        return self._procesar(request, request.GET.get('TBK_TOKEN') or request.GET.get('token'))

    def post(self, request):
        token = request.POST.get('TBK_TOKEN') or request.GET.get('TBK_TOKEN')
        return self._procesar(request, token)

    def _procesar(self, request, token):
        if not token:
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago?inscripcion=sin_token")

        try:
            insc     = _get_oneclick_inscription()
            response = insc.finish(token=token)
        except Exception as e:
            import traceback
            print(f"[ONECLICK FINISH ERROR] {traceback.format_exc()}")
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago?inscripcion=error")

        # Extraer datos de la respuesta
        if isinstance(response, dict):
            tbk_user   = response.get('tbk_user')
            username   = response.get('user_name', '')
            last_4     = response.get('last_4_card_digits', '')
            card_type  = response.get('card_type', '')
            ins_status = response.get('inscription_status', -1)
        else:
            tbk_user   = getattr(response, 'tbk_user', None)
            username   = getattr(response, 'user_name', '')
            last_4     = getattr(response, 'last_4_card_digits', '')
            card_type  = getattr(response, 'card_type', '')
            ins_status = getattr(response, 'inscription_status', -1)

        if ins_status != 0 or not tbk_user:
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago?inscripcion=rechazada")

        # Derivar empresa desde el username (formato "emp-{id}")
        try:
            empresa_id = int(username.replace('emp-', ''))
            empresa    = Empresa.objects.get(id=empresa_id)
        except (ValueError, Empresa.DoesNotExist):
            return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago?inscripcion=error_empresa")

        # Crear o actualizar TarjetaGuardada
        TarjetaGuardada.objects.update_or_create(
            empresa=empresa,
            defaults={
                'tbk_user':    tbk_user,
                'username_tb': username,
                'last_4':      last_4,
                'card_type':   card_type,
            },
        )

        notificar_admins_empresa(
            empresa=empresa,
            tipo='actividad',
            titulo='Tarjeta guardada correctamente',
            mensaje=f'Tu {card_type} terminada en {last_4} fue inscrita para cobros automáticos.',
        )

        return redirect(f"{django_settings.FRONTEND_URL}/empresa/pago?inscripcion=ok")


# ─────────────────────────────────────────
# DELETE /api/empresa/tarjeta/
# ─────────────────────────────────────────

class TarjetaEliminarView(APIView):
    """Elimina la tarjeta guardada del usuario (desuscribe de OneClick)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        if getattr(request.user, 'rol', None) != 'USUARIO':
            return Response({'error': 'Sin acceso.'}, status=403)

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Sin empresa asignada.'}, status=403)

        try:
            tarjeta = empresa.tarjeta_guardada
        except TarjetaGuardada.DoesNotExist:
            return Response({'error': 'No tienes tarjeta guardada.'}, status=404)

        # Intentar eliminar en Transbank (no crítico si falla)
        try:
            insc = _get_oneclick_inscription()
            insc.delete(tbk_user=tarjeta.tbk_user, username=tarjeta.username_tb)
        except Exception as e:
            print(f"[ONECLICK DELETE WARNING] {e}")

        tarjeta.delete()
        registrar_log('ACTIVIDAD', 'tarjeta_eliminada', request, detalle={
            'empresa': empresa.nombre,
        })
        return Response({'ok': True})


# ═══════════════════════════════════════════════════════════════════════════════
# Configuración de email SMTP
# ═══════════════════════════════════════════════════════════════════════════════

class EmailConfigView(APIView):
    """
    GET /api/admin/email/  — Devuelve la config SMTP (contraseña enmascarada).
    PUT /api/admin/email/  — Actualiza la config SMTP.
    Solo SUPERADMIN.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        config = ConfiguracionSistema.get()
        return Response({
            'email_host':         config.email_host,
            'email_port':         config.email_port,
            'email_host_user':    config.email_host_user,
            'email_host_password': '••••••••' if config.email_host_password else '',
            'email_use_tls':      config.email_use_tls,
            'email_use_ssl':      config.email_use_ssl,
            'email_from_name':    config.email_from_name,
            'email_from_address': config.email_from_address,
            'email_activo':       config.email_activo,
            'notificaciones': {
                'pago_aprobado':         config.notif_pago_aprobado,
                'pago_rechazado':        config.notif_pago_rechazado,
                'suscripcion_vence':     config.notif_suscripcion_vence,
                'suscripcion_gracia':    config.notif_suscripcion_gracia,
                'suscripcion_bloqueada': config.notif_suscripcion_bloqueada,
                'documento_vence':       config.notif_documento_vence,
                'mantencion_vence':      config.notif_mantencion_vence,
                'solicitud_nueva':       config.notif_solicitud_nueva,
                'solicitud_resuelta':    config.notif_solicitud_resuelta,
                'ruta_asignada':         config.notif_ruta_asignada,
                'checklist_fallas':      config.notif_checklist_fallas,
                'bienvenida':            config.notif_bienvenida,
                'reset_password':        config.notif_reset_password,
                'recordatorio_pago':     config.notif_recordatorio_pago,
            },
        })

    def put(self, request):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        body   = request.data
        config = ConfiguracionSistema.get()

        # Campos SMTP (solo actualizar si vienen en el body)
        if 'email_host'         in body: config.email_host         = body['email_host']
        if 'email_port'         in body: config.email_port         = int(body['email_port'])
        if 'email_host_user'    in body: config.email_host_user    = body['email_host_user']
        if 'email_use_tls'      in body: config.email_use_tls      = bool(body['email_use_tls'])
        if 'email_use_ssl'      in body: config.email_use_ssl      = bool(body['email_use_ssl'])
        if 'email_from_name'    in body: config.email_from_name    = body['email_from_name']
        if 'email_from_address' in body: config.email_from_address = body['email_from_address']
        if 'email_activo'       in body: config.email_activo       = bool(body['email_activo'])

        # Contraseña: solo actualizar si no es el valor enmascarado
        pwd = body.get('email_host_password', '')
        if pwd and pwd != '••••••••':
            config.set_email_password(pwd)

        # Toggles de notificaciones
        notif = body.get('notificaciones', {})
        if 'pago_aprobado'         in notif: config.notif_pago_aprobado         = bool(notif['pago_aprobado'])
        if 'pago_rechazado'        in notif: config.notif_pago_rechazado        = bool(notif['pago_rechazado'])
        if 'suscripcion_vence'     in notif: config.notif_suscripcion_vence     = bool(notif['suscripcion_vence'])
        if 'suscripcion_gracia'    in notif: config.notif_suscripcion_gracia    = bool(notif['suscripcion_gracia'])
        if 'suscripcion_bloqueada' in notif: config.notif_suscripcion_bloqueada = bool(notif['suscripcion_bloqueada'])
        if 'documento_vence'       in notif: config.notif_documento_vence       = bool(notif['documento_vence'])
        if 'mantencion_vence'      in notif: config.notif_mantencion_vence      = bool(notif['mantencion_vence'])
        if 'solicitud_nueva'       in notif: config.notif_solicitud_nueva       = bool(notif['solicitud_nueva'])
        if 'solicitud_resuelta'    in notif: config.notif_solicitud_resuelta    = bool(notif['solicitud_resuelta'])
        if 'ruta_asignada'         in notif: config.notif_ruta_asignada         = bool(notif['ruta_asignada'])
        if 'checklist_fallas'      in notif: config.notif_checklist_fallas      = bool(notif['checklist_fallas'])
        if 'bienvenida'            in notif: config.notif_bienvenida            = bool(notif['bienvenida'])
        if 'reset_password'        in notif: config.notif_reset_password        = bool(notif['reset_password'])
        if 'recordatorio_pago'     in notif: config.notif_recordatorio_pago     = bool(notif['recordatorio_pago'])

        config.save()
        registrar_log('ACTIVIDAD', 'email_config_guardada', request, detalle={
            'email_host': config.email_host,
            'email_activo': config.email_activo,
        })
        return Response({'ok': True})


class EmailTestView(APIView):
    """
    POST /api/admin/email/test/
    Envía un email de prueba al destinatario indicado.
    Retorna el error SMTP si falla (para diagnóstico).
    Solo SUPERADMIN.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'rol', None) != 'SUPERADMIN':
            return Response({'error': 'Sin acceso.'}, status=403)

        destino = request.data.get('email_destino', '').strip()
        if not destino:
            return Response({'error': 'email_destino es requerido.'}, status=400)

        config = ConfiguracionSistema.get()

        from .email_service import _base_template, get_email_backend
        html = _base_template(
            'Email de prueba',
            f"""
            <p style="color:#444;font-size:15px;">
              Este es un email de prueba enviado desde FlotaSystem.
            </p>
            <p style="color:#888;font-size:13px;">
              Si recibes este mensaje, la configuración SMTP es correcta.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:16px 0;width:100%;">
              <tr>
                <td style="color:#666;font-size:13px;padding:4px 0;">Servidor SMTP:</td>
                <td style="color:#1a1a1a;font-size:13px;">{config.email_host}:{config.email_port}</td>
              </tr>
              <tr>
                <td style="color:#666;font-size:13px;padding:4px 0;">Usuario:</td>
                <td style="color:#1a1a1a;font-size:13px;">{config.email_host_user}</td>
              </tr>
            </table>
            """,
        )

        try:
            backend   = get_email_backend()
            if not backend:
                return Response({
                    'ok': False,
                    'error': 'El envío de emails no está configurado o está desactivado.',
                }, status=400)

            remitente = f"{config.email_from_name} <{config.email_from_address}>"
            msg = EmailMultiAlternatives(
                subject='Email de prueba — FlotaSystem',
                body='Email de prueba desde FlotaSystem.',
                from_email=remitente,
                to=[destino],
                connection=backend,
            )
            msg.attach_alternative(html, 'text/html')
            msg.send()

            registrar_log('ACTIVIDAD', 'email_test_enviado', request, detalle={
                'destino': destino,
            })
            return Response({'ok': True, 'mensaje': f'Email de prueba enviado a {destino}'})

        except Exception as e:
            return Response({'ok': False, 'error': str(e)}, status=400)
