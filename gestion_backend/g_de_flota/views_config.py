from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Usuario, CambioPlan, cifrar
from .audit import registrar_log


# ─────────────────────────────────────────
# Perfil del usuario autenticado
# ─────────────────────────────────────────

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def usuario_perfil(request):
    user = request.user

    if request.method == 'GET':
        plan_modulos  = []
        plan_nombre   = ''
        plan_permisos = []
        if user.empresa_id and user.empresa and user.empresa.plan:
            plan = user.empresa.plan
            plan_modulos  = plan.modulos or []
            plan_nombre   = plan.get_nombre_display()
            plan_permisos = list(plan.permisos.values_list('codigo', flat=True))
        return Response({
            'nombre':        user.nombre or '',
            'email':         user.email,
            'rol':           user.rol,
            'empresa':       user.empresa.nombre if user.empresa else None,
            'plan_modulos':  plan_modulos,
            'plan_nombre':   plan_nombre,
            'plan_permisos': plan_permisos,
        })

    nombre = (request.data.get('nombre') or '').strip()
    email  = (request.data.get('email')  or '').strip().lower()

    if not nombre:
        return Response({'error': 'El nombre no puede estar vacío.'}, status=400)
    if not email:
        return Response({'error': 'El email no puede estar vacío.'}, status=400)

    if email != user.email:
        if Usuario.objects.filter(email=email).exclude(pk=user.pk).exists():
            return Response({'error': 'Ese email ya está en uso.'}, status=400)
        user.email = email

    user.nombre_cifrado = cifrar(nombre)
    user.save(update_fields=['nombre_cifrado', 'email'])
    registrar_log('ACTIVIDAD', 'perfil_actualizado', request)

    return Response({'nombre': user.nombre, 'email': user.email})


# ─────────────────────────────────────────
# Cambio de contraseña
# ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def usuario_cambiar_password(request):
    user       = request.user
    actual     = request.data.get('password_actual', '')
    nueva      = request.data.get('password_nueva', '')
    confirmar  = request.data.get('password_confirmar', '')

    if not user.check_password(actual):
        return Response({'error': 'La contraseña actual es incorrecta.'}, status=400)
    if len(nueva) < 8:
        return Response({'error': 'La nueva contraseña debe tener al menos 8 caracteres.'}, status=400)
    if nueva != confirmar:
        return Response({'error': 'Las contraseñas no coinciden.'}, status=400)

    user.set_password(nueva)
    user.save(update_fields=['password'])
    registrar_log('SEGURIDAD', 'password_cambiado', request)

    return Response({'message': 'Contraseña actualizada correctamente.'})


# ─────────────────────────────────────────
# Historial de cambios de plan (empresa)
# ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_historial(request):
    user = request.user
    if not user.empresa_id:
        return Response([], status=200)

    historial = (
        CambioPlan.objects
        .filter(empresa_id=user.empresa_id)
        .select_related('plan_antes', 'plan_despues', 'cambiado_por')
        .order_by('-fecha')[:20]
    )

    data = []
    for c in historial:
        data.append({
            'fecha':        c.fecha.strftime('%d/%m/%Y %H:%M'),
            'plan_antes':   c.plan_antes.get_nombre_display()   if c.plan_antes   else 'Sin plan',
            'plan_despues': c.plan_despues.get_nombre_display() if c.plan_despues else 'Sin plan',
            'motivo':       c.motivo or '—',
            'cambiado_por': c.cambiado_por.nombre if c.cambiado_por else 'Sistema',
        })

    return Response(data)
