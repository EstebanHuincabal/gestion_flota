from django.core.mail import send_mail
from django.conf import settings

from .models import Notificacion, NOTIF_PREFS_DEFAULT, TIPO_NOTIF_CATEGORIA


def _prefs(usuario):
    raw = usuario.notif_prefs or {}
    return {
        "inapp": raw.get("inapp", NOTIF_PREFS_DEFAULT["inapp"]),
        "email": raw.get("email", NOTIF_PREFS_DEFAULT["email"]),
    }


def notificar(usuario, tipo: str, titulo: str, mensaje: str,
              url_accion: str = '', extra: dict = None):
    """
    Crea una notificación in-app y/o envía email según las preferencias del usuario.
    Nunca lanza excepción — falla silenciosamente para no interrumpir el flujo principal.
    """
    try:
        prefs = _prefs(usuario)
        categoria = TIPO_NOTIF_CATEGORIA.get(tipo, "actividad")

        if categoria in prefs["inapp"]:
            Notificacion.objects.create(
                usuario=usuario,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                url_accion=url_accion,
                extra=extra or {},
            )

        if categoria in prefs["email"] and usuario.email:
            send_mail(
                subject=f"[Gestión de Flota] {titulo}",
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=True,
            )
    except Exception:
        pass


def notificar_admins_empresa(empresa, tipo: str, titulo: str, mensaje: str,
                             url_accion: str = '', extra: dict = None):
    """Notifica a todos los usuarios USUARIO activos de una empresa."""
    from .models import Usuario, Rol
    admins = Usuario.objects.filter(empresa=empresa, rol=Rol.USUARIO, is_active=True)
    for admin in admins:
        notificar(admin, tipo, titulo, mensaje, url_accion, extra)
