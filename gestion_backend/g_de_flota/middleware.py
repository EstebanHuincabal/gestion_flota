import time
from django.http import JsonResponse
from django.contrib.auth import logout
from django.conf import settings

# ─────────────────────────────────────────
# Rutas que nunca son bloqueadas por suscripción
# ─────────────────────────────────────────
_RUTAS_LIBRES = [
    '/api/login/',
    '/api/token/',
    '/api/token/refresh/',
    '/api/pago/',                          # checkout Webpay Plus
    '/api/pago/retorno/',                  # retorno Webpay Plus
    '/api/terminos/',                      # ver términos públicos
    '/api/empresa/tarjeta/retorno/',       # retorno OneClick (inscripción)
    '/admin/',
]


class BloqueoSuscripcionMiddleware:
    """
    Bloquea el acceso a la API (402) si la empresa tiene suscripción suspendida.
    Solo aplica a usuarios con rol USUARIO. SUPERADMIN y CONDUCTOR nunca son bloqueados.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(r) for r in _RUTAS_LIBRES):
            return self.get_response(request)

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)

        if getattr(request.user, 'rol', None) != 'USUARIO':
            return self.get_response(request)

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return self.get_response(request)

        try:
            sus = empresa.suscripcion
        except Exception:
            return self.get_response(request)

        if sus.esta_bloqueada:
            from .models import ConfiguracionSistema
            config = ConfiguracionSistema.get()
            return JsonResponse({
                'error':  config.mensaje_pago_pendiente,
                'codigo': 'SUSCRIPCION_BLOQUEADA',
                'estado': sus.estado,
            }, status=402)

        # Advertencia en header si está en período de gracia
        response = self.get_response(request)
        if sus.estado == 'gracia':
            dias = sus.dias_para_vencer
            response['X-Gracia-Dias'] = str(dias if dias is not None else 0)

        return response

class ConfiguracionSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            # Idle timeout — verificar ANTES de procesar la vista
            if request.path != '/api/login/' and hasattr(request, 'user') and request.user.is_authenticated:
                timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 3600)
                last_activity = request.session.get('_last_activity')
                now = time.time()

                if last_activity is not None and (now - last_activity) > timeout:
                    logout(request)
                    return JsonResponse(
                        {"error": "Sesión expirada por inactividad. Por favor inicia sesión nuevamente."},
                        status=401,
                    )

                request.session['_last_activity'] = now

        return self.get_response(request)
