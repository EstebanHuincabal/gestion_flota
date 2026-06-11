"""
views_avisos.py — Módulo de avisos internos.

Permite a admins enviar avisos a toda la flota o a un conductor específico,
y a conductores enviar avisos a los admins de su empresa.

Endpoints:
  POST /api/empresa/avisos/            Crear y enviar aviso (admin)
  GET  /api/empresa/avisos/            Bandeja de avisos (admin)
  GET  /api/empresa/avisos/conductores/ Lista conductores para el selector
  POST /api/conductor/avisos/          Conductor envía aviso a admins
  GET  /api/conductor/avisos/          Bandeja del conductor (avisos recibidos)
"""
import threading

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Aviso, Usuario, Empresa, Rol
from .sanitizers import sanitizar_texto
from .email_service import email_aviso
from .notificaciones import notificar


def _tiene_permiso(user, codigo):
    """Chequea permiso a nivel de usuario O de plan (el mismo criterio que el guard del frontend).

    El router del frontend permite la ruta si el PLAN tiene el permiso; el backend
    debe aceptar con el mismo criterio para no bloquear a usuarios cuyo plan sí lo
    incluye pero cuya cuenta se creó antes de que existiera el permiso a nivel de usuario.
    SUPERADMIN siempre pasa.
    """
    if user.rol == Rol.SUPERADMIN:
        return True
    # 1. Permiso asignado directamente al usuario
    if user.permisos.filter(codigo=codigo).exists():
        return True
    # 2. Permiso incluido en el plan de la empresa del usuario
    plan = getattr(getattr(user, 'empresa', None), 'plan', None)
    if plan and plan.permisos.filter(codigo=codigo).exists():
        return True
    return False


def _nombre(usuario):
    return usuario.nombre or usuario.email


def _aviso_dict(aviso):
    return {
        'id':             aviso.id,
        'destino':        aviso.destino,
        'asunto':         aviso.asunto,
        'mensaje':        aviso.mensaje,
        'fecha':          aviso.fecha.isoformat(),
        'emisor':         _nombre(aviso.emisor) if aviso.emisor else '—',
        'emisor_rol':     aviso.emisor.rol if aviso.emisor else None,
        'empresa_nombre': aviso.empresa.nombre if aviso.empresa else '—',
        'destinatario':   _nombre(aviso.destinatario) if aviso.destinatario else None,
    }


# ─────────────────────────────────────────
# Admin: bandeja + envío
# ─────────────────────────────────────────

EMPRESA_TODAS = '__todas__'


def _es_todas(request):
    """True si el SUPERADMIN pidió ver "Todas las empresas" (solo lectura)."""
    return request.user.rol == Rol.SUPERADMIN \
        and (request.query_params.get('empresa_id') or request.data.get('empresa_id')) == EMPRESA_TODAS


def _resolver_empresa(request):
    """Devuelve la empresa a operar: la propia del USUARIO o la indicada por SUPERADMIN.

    El centinela "__todas__" se trata como "sin empresa concreta" (None) para no
    castear un pk inválido (evita el 500) y bloquear las escrituras.
    """
    if request.user.rol == Rol.SUPERADMIN:
        # Priorizar el ID del body (POST) sobre el query param para permitir
        # enviar a una empresa específica estando en la vista "Todas".
        eid = request.data.get('empresa_id') or request.query_params.get('empresa_id')
        if not eid or eid == EMPRESA_TODAS:
            return None
        try:
            return Empresa.objects.get(pk=eid)
        except (Empresa.DoesNotExist, ValueError, TypeError):
            return None
    return request.user.empresa


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def empresa_avisos(request):
    if not _tiene_permiso(request.user, 'avisos.ver'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)

    # Modo "Todas las empresas" (SUPERADMIN, solo lectura): bandeja sin filtro.
    todas = _es_todas(request) and request.method == 'GET'
    empresa = None if todas else _resolver_empresa(request)

    # ── GET: bandeja ─────────────────────────────────────────────────────────
    if request.method == 'GET':
        if not todas and not empresa:
            return Response({'error': 'Sin empresa.'}, status=status.HTTP_400_BAD_REQUEST)
        avisos_qs = Aviso.objects.select_related('emisor', 'destinatario', 'empresa').order_by('-fecha')
        if not todas:
            avisos_qs = avisos_qs.filter(empresa=empresa)

        if todas:
            # Los avisos con destino='todas' se crean uno por empresa; deduplicar
            # para mostrar solo uno en la bandeja del SUPERADMIN.
            # Se sobreescribe empresa_nombre → None para que el frontend sepa que
            # es un aviso global y lo muestre independientemente del filtro de empresa.
            seen_globales = set()
            resultado = []
            for a in avisos_qs:
                if a.destino == Aviso.DESTINO_TODAS:
                    key = (a.emisor_id, a.asunto, a.fecha.date())
                    if key in seen_globales:
                        continue
                    seen_globales.add(key)
                    d = _aviso_dict(a)
                    d['empresa_nombre'] = None   # global, sin empresa concreta
                    resultado.append(d)
                else:
                    resultado.append(_aviso_dict(a))
            return Response(resultado)

        return Response([_aviso_dict(a) for a in avisos_qs])

    # ── POST: enviar ──────────────────────────────────────────────────────────
    if not _tiene_permiso(request.user, 'avisos.enviar'):
        return Response({'error': 'Sin permisos para enviar avisos.'}, status=status.HTTP_403_FORBIDDEN)

    destino = request.data.get('destino', '')
    asunto  = sanitizar_texto(request.data.get('asunto', '')).strip()
    mensaje = sanitizar_texto(request.data.get('mensaje', '')).strip()

    DESTINOS_VALIDOS = (Aviso.DESTINO_FLOTA, Aviso.DESTINO_CONDUCTOR, Aviso.DESTINO_TODAS, Aviso.DESTINO_ADMINS, Aviso.DESTINO_SUPERADMIN)
    if destino not in DESTINOS_VALIDOS:
        return Response({'error': 'Destino inválido.'}, status=status.HTTP_400_BAD_REQUEST)
    if not asunto:
        return Response({'error': 'El asunto es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
    if not mensaje:
        return Response({'error': 'El mensaje es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

    # Solo el SUPERADMIN puede usar destino='todas'
    if destino == Aviso.DESTINO_TODAS and request.user.rol != Rol.SUPERADMIN:
        return Response({'error': 'Sin permisos para enviar a todas las empresas.'}, status=status.HTTP_403_FORBIDDEN)

    # Solo el SUPERADMIN puede enviar a 'admins' desde este endpoint
    if destino == Aviso.DESTINO_ADMINS and request.user.rol != Rol.SUPERADMIN:
        return Response({'error': 'Sin permisos para enviar a administradores.'}, status=status.HTTP_403_FORBIDDEN)

    # Solo el USUARIO (admin empresa) puede enviar a 'superadmin'
    if destino == Aviso.DESTINO_SUPERADMIN and request.user.rol != Rol.USUARIO:
        return Response({'error': 'Sin permisos para enviar a soporte.'}, status=status.HTTP_403_FORBIDDEN)

    nombre_emisor = _nombre(request.user)

    # ── Envío a todas las empresas (solo SUPERADMIN) ──────────────────────────
    if destino == Aviso.DESTINO_TODAS:
        empresas = list(Empresa.objects.filter(estado='activa'))
        datos_email = []   # pre-colectados antes del hilo para no hacer ORM dentro del thread
        for emp in empresas:
            Aviso.objects.create(
                empresa=emp,
                emisor=request.user,
                destino=Aviso.DESTINO_TODAS,
                asunto=asunto,
                mensaje=mensaje,
            )
            admins = list(Usuario.objects.filter(empresa=emp, is_active=True, rol=Rol.USUARIO))
            for admin in admins:
                notificar(admin, tipo='ACTIVIDAD', titulo=f'📢 {asunto}',
                          mensaje=mensaje, url_accion='/avisos')
                if admin.email:
                    datos_email.append((admin.email, _nombre(admin), emp.nombre))

        if datos_email:
            def _enviar_emails(datos=datos_email):
                for email, nombre, emp_nombre in datos:
                    email_aviso(email, nombre, emp_nombre, nombre_emisor, asunto, mensaje)
            threading.Thread(target=_enviar_emails, daemon=True).start()

        return Response({'enviado': True, 'empresas': len(empresas)}, status=status.HTTP_201_CREATED)

    # ── Envío normal (una empresa) ────────────────────────────────────────────
    # Los envíos dirigidos exigen una empresa concreta (no aplica "Todas").
    if not empresa:
        return Response(
            {'error': 'Selecciona una empresa para enviar este aviso.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    destinatario = None
    if destino == Aviso.DESTINO_CONDUCTOR:
        cid = request.data.get('destinatario_id')
        if not cid:
            return Response({'error': 'Debes seleccionar un conductor.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            destinatario = Usuario.objects.get(pk=cid, empresa=empresa, rol=Rol.CONDUCTOR, is_active=True)
        except Usuario.DoesNotExist:
            return Response({'error': 'Conductor no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    aviso = Aviso.objects.create(
        empresa=empresa,
        emisor=request.user,
        destino=destino,
        destinatario=destinatario,
        asunto=asunto,
        mensaje=mensaje,
    )

    empresa_nombre = 'FlotaSystem' if destino == Aviso.DESTINO_SUPERADMIN else empresa.nombre
    if destino == Aviso.DESTINO_CONDUCTOR:
        receptores = [destinatario]
    elif destino == Aviso.DESTINO_ADMINS:
        receptores = list(Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True))
    elif destino == Aviso.DESTINO_SUPERADMIN:
        receptores = list(Usuario.objects.filter(rol=Rol.SUPERADMIN, is_active=True))
    else:
        receptores = list(Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR, is_active=True))

    # Notificaciones push sincrónicamente (BD local, rápido)
    for receptor in receptores:
        notificar(receptor, tipo='ACTIVIDAD', titulo=f'📢 {asunto}',
                  mensaje=mensaje, url_accion='/avisos')

    # Envío de correos en hilo separado para no bloquear la respuesta HTTP
    receptores_email = [(r.email, _nombre(r)) for r in receptores if r.email]

    def _enviar_emails():
        for email, nombre in receptores_email:
            email_aviso(email, nombre, empresa_nombre, nombre_emisor, asunto, mensaje)

    if receptores_email:
        threading.Thread(target=_enviar_emails, daemon=True).start()

    return Response(_aviso_dict(aviso), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def empresa_avisos_conductores(request):
    """Lista conductores activos de la empresa para el selector del formulario."""
    if not _tiene_permiso(request.user, 'avisos.enviar'):
        return Response({'error': 'Sin permisos.'}, status=status.HTTP_403_FORBIDDEN)
    empresa = _resolver_empresa(request)
    if not empresa:
        return Response([])
    conductores = Usuario.objects.filter(empresa=empresa, rol=Rol.CONDUCTOR, is_active=True).order_by('nombre_cifrado')
    return Response([{'id': c.id, 'nombre': _nombre(c)} for c in conductores])


# ─────────────────────────────────────────
# Conductor: bandeja + envío a admins
# ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conductor_avisos(request):
    if request.user.rol != Rol.CONDUCTOR:
        return Response({'error': 'Solo para conductores.'}, status=status.HTTP_403_FORBIDDEN)

    empresa = request.user.empresa
    if not empresa:
        return Response({'error': 'Sin empresa.'}, status=status.HTTP_400_BAD_REQUEST)

    # ── GET: avisos recibidos por el conductor ────────────────────────────────
    if request.method == 'GET':
        avisos = Aviso.objects.filter(
            empresa=empresa,
            destino__in=[Aviso.DESTINO_FLOTA, Aviso.DESTINO_CONDUCTOR],
        ).filter(
            # Flota (todos) O este conductor en particular
            **{}
        ).select_related('emisor', 'destinatario')

        resultado = []
        for a in avisos:
            if a.destino == Aviso.DESTINO_FLOTA or a.destinatario_id == request.user.id:
                resultado.append(_aviso_dict(a))
        return Response(resultado)

    # ── POST: conductor envía a admins ────────────────────────────────────────
    asunto  = sanitizar_texto(request.data.get('asunto', '')).strip()
    mensaje = sanitizar_texto(request.data.get('mensaje', '')).strip()

    if not asunto:
        return Response({'error': 'El asunto es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
    if not mensaje:
        return Response({'error': 'El mensaje es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

    aviso = Aviso.objects.create(
        empresa=empresa,
        emisor=request.user,
        destino=Aviso.DESTINO_ADMINS,
        asunto=asunto,
        mensaje=mensaje,
    )

    nombre_emisor  = _nombre(request.user)
    empresa_nombre = empresa.nombre
    url_avisos_admin = '/empresa/avisos'

    admins = list(Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True))
    for admin in admins:
        notificar(
            admin,
            tipo='ACTIVIDAD',
            titulo=f'📢 {asunto}',
            mensaje=f'Aviso de {nombre_emisor}: {mensaje}',
            url_accion=url_avisos_admin,
        )

    admins_email = [(a.email, _nombre(a)) for a in admins if a.email]

    def _enviar_emails():
        for email, nombre in admins_email:
            email_aviso(email, nombre, empresa_nombre, nombre_emisor, asunto, mensaje)

    if admins_email:
        threading.Thread(target=_enviar_emails, daemon=True).start()

    return Response(_aviso_dict(aviso), status=status.HTTP_201_CREATED)
