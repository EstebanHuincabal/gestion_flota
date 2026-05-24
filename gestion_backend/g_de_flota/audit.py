import re

from .models import LogAuditoria


# ── Helpers de request ───────────────────────────────────────────

def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def _parse_navegador(ua):
    """Nombre del navegador a partir del User-Agent."""
    if not ua:
        return None
    if re.search(r'Edg/', ua):          return 'Edge'
    if re.search(r'OPR|Opera', ua):     return 'Opera'
    if re.search(r'Firefox/', ua):      return 'Firefox'
    if re.search(r'Chrome/', ua):       return 'Chrome'
    if re.search(r'Safari/', ua):       return 'Safari'
    if re.search(r'MSIE|Trident/', ua): return 'Internet Explorer'
    return 'Otro'


def _parse_so(ua):
    """Sistema operativo a partir del User-Agent."""
    if not ua:
        return None
    if re.search(r'Windows NT 10|Windows NT 11', ua): return 'Windows 10/11'
    if re.search(r'Windows NT 6\.3', ua):             return 'Windows 8.1'
    if re.search(r'Windows NT 6\.1', ua):             return 'Windows 7'
    if re.search(r'Windows', ua):                     return 'Windows'
    if re.search(r'iPhone|iPad',      ua):            return 'iOS'
    if re.search(r'Android',          ua):            return 'Android'
    if re.search(r'Mac OS X',         ua):            return 'macOS'
    if re.search(r'Linux',            ua):            return 'Linux'
    return 'Otro'


# ── Diff de campos ───────────────────────────────────────────────

def _diff_campos(antes, despues):
    """
    Compara dos dicts {campo: valor_str} y devuelve lista de cambios:
      [{'campo': 'marca', 'antes': 'Toyota', 'despues': 'Ford'}, ...]
    Solo incluye campos cuyo valor cambió (ignorando Nones → '').
    """
    cambios = []
    for campo, v_antes in antes.items():
        v_despues = despues.get(campo)
        s_antes   = str(v_antes   if v_antes   is not None else '')
        s_despues = str(v_despues if v_despues is not None else '')
        if s_antes != s_despues:
            cambios.append({'campo': campo, 'antes': s_antes, 'despues': s_despues})
    return cambios


def _snap(obj, campos):
    """Captura un dict {campo: str_valor} de un objeto Django antes del save."""
    return {c: str(getattr(obj, c, '') or '') for c in campos}


# ── Registro principal ───────────────────────────────────────────

def registrar_log(tipo, accion, request, usuario=None, detalle=None):
    actor = usuario
    if actor is None and hasattr(request, 'user') and request.user.is_authenticated:
        actor = request.user

    ua = request.META.get('HTTP_USER_AGENT', '') or None

    LogAuditoria.objects.create(
        tipo       = tipo,
        accion     = accion,
        usuario    = actor,
        detalle    = detalle or {},
        ip         = _get_ip(request),
        user_agent = ua,
        so         = _parse_so(ua),
        metodo     = request.method,
        endpoint   = request.path,
    )
