from django.core.mail import send_mail
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notificacion, NOTIF_PREFS_DEFAULT, TIPO_NOTIF_CATEGORIA


def _prefs(usuario):
    raw = usuario.notif_prefs or {}
    return {
        "inapp": raw.get("inapp", NOTIF_PREFS_DEFAULT["inapp"]),
        "email": raw.get("email", NOTIF_PREFS_DEFAULT["email"]),
    }


def _plan_incluye_permiso(usuario, codigo: str) -> bool:
    """True si el plan de la empresa del usuario incluye `codigo`. SUPERADMIN siempre."""
    from .models import Rol
    if getattr(usuario, 'rol', None) == Rol.SUPERADMIN:
        return True
    plan = getattr(getattr(usuario, 'empresa', None), 'plan', None)
    if not plan:
        return False
    return plan.permisos.filter(codigo=codigo).exists()


def notificar(usuario, tipo: str, titulo: str, mensaje: str,
              url_accion: str = '', extra: dict = None, forzar: bool = False,
              permiso: str = None):
    """
    Crea una notificación in-app y/o envía email según las preferencias del usuario.
    forzar=True omite el filtro de preferencias (útil para alertas críticas).
    permiso='codigo' la asocia a un permiso del plan: si la empresa no lo tiene
    (p. ej. tras un downgrade), la notificación no se envía. Centraliza el filtro
    para que cada módulo no tenga que comprobarlo por su cuenta.
    Nunca lanza excepción — falla silenciosamente para no interrumpir el flujo principal.
    """
    try:
        # Filtro por permiso del plan: no notificar de módulos que la empresa no tiene.
        if permiso and not _plan_incluye_permiso(usuario, permiso):
            return

        prefs = _prefs(usuario)
        categoria = TIPO_NOTIF_CATEGORIA.get(tipo, "actividad")

        if forzar or categoria in prefs["inapp"]:
            notif = Notificacion.objects.create(
                usuario=usuario,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                url_accion=url_accion,
                extra=extra or {},
            )
            channel_layer = get_channel_layer()
            if channel_layer:
                count = Notificacion.objects.filter(usuario=usuario, leida=False).count()
                async_to_sync(channel_layer.group_send)(
                    f'notif_user_{usuario.id}',
                    {
                        'type': 'nueva_notificacion',
                        'count': count,
                        'notificacion': {
                            'id': notif.id,
                            'tipo': notif.tipo,
                            'titulo': notif.titulo,
                            'mensaje': notif.mensaje,
                            'url_accion': notif.url_accion,
                            'leida': False,
                            'fecha': notif.fecha.isoformat(),
                        },
                    }
                )

        if categoria in prefs["email"] and usuario.email:
            send_mail(
                subject=f"[Gestión de Flota] {titulo}",
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=True,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning('notificar() falló silenciosamente: %s', exc)


def notificar_admins_empresa(empresa, tipo: str, titulo: str, mensaje: str,
                             url_accion: str = '', extra: dict = None,
                             permiso: str = None):
    """Notifica a todos los usuarios USUARIO activos de una empresa.

    Si se pasa `permiso`, solo se notifica cuando el plan de la empresa lo
    incluye (se evalúa una vez, ya que el plan es por empresa).
    """
    from .models import Usuario, Rol
    admins = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True)
    for admin in admins:
        notificar(admin, tipo, titulo, mensaje, url_accion, extra, permiso=permiso)


def notificar_superadmins(tipo: str, titulo: str, mensaje: str,
                          url_accion: str = '', extra: dict = None):
    """Notifica a todos los SUPERADMIN activos del sistema."""
    from .models import Usuario, Rol
    superadmins = Usuario.objects.filter(rol=Rol.SUPERADMIN, is_active=True)
    for sa in superadmins:
        notificar(sa, tipo, titulo, mensaje, url_accion, extra)
