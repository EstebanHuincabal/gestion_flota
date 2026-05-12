from .models import LogAuditoria


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def registrar_log(tipo, accion, request, usuario=None, detalle=None):
    actor = usuario
    if actor is None and hasattr(request, 'user') and request.user.is_authenticated:
        actor = request.user
    LogAuditoria.objects.create(
        tipo=tipo,
        accion=accion,
        usuario=actor,
        detalle=detalle or {},
        ip=_get_ip(request),
    )
