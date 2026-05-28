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
    '/api/planes/',
    '/api/auto-registro/',
    '/api/verificar-rut/',
    '/api/pago/',                          # checkout Webpay Plus
    '/api/pago/retorno/',                  # retorno Webpay Plus
    '/api/terminos/',                      # ver términos públicos
    '/api/empresa/tarjeta/retorno/',       # retorno OneClick (inscripción)
    '/api/empresa/tarjeta/inscribir/',     # iniciar inscripción OneClick
    '/api/empresa/tarjeta/',              # consultar tarjeta guardada (necesario en página de pago)
    '/api/empresa/suscripcion/',          # consultar estado (necesario para mostrar overlay de bloqueo)
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

        rol = getattr(request.user, 'rol', None)

        # SUPERADMIN nunca es bloqueado
        if rol not in ('USUARIO', 'CONDUCTOR'):
            return self.get_response(request)

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return self.get_response(request)

        try:
            sus = empresa.suscripcion
        except Exception:
            # Sin suscripción asignada → 402 solo si realmente es falta de suscripción
            if not empresa.pk:
                return self.get_response(request)
            return JsonResponse({
                'error':  'Tu empresa aún no tiene una suscripción activa. Realiza el pago de tu plan para continuar.',
                'codigo': 'SUSCRIPCION_BLOQUEADA',
                'estado': 'sin_suscripcion',
            }, status=402)

        if sus.esta_bloqueada:
            from .models import ConfiguracionSistema
            config = ConfiguracionSistema.get()

            if sus.estado == 'pendiente':
                if rol == 'CONDUCTOR':
                    mensaje = 'Tu empresa aún no ha activado su plan. Contacta al administrador.'
                else:
                    mensaje = 'Tu empresa aún no tiene un pago registrado. Realiza el pago de tu plan para continuar.'
            elif rol == 'CONDUCTOR':
                mensaje = 'La suscripción de tu empresa está suspendida. Contacta al administrador.'
            else:
                mensaje = config.mensaje_pago_pendiente

            return JsonResponse({
                'error':  mensaje,
                'codigo': 'SUSCRIPCION_BLOQUEADA',
                'estado': sus.estado,
            }, status=402)

        # Advertencia en header si está en período de gracia (solo USUARIO)
        response = self.get_response(request)
        if rol == 'USUARIO' and sus.estado == 'gracia':
            dias = sus.dias_para_vencer
            response['X-Gracia-Dias'] = str(dias if dias is not None else 0)

        return response

class ErrorHandlerMiddleware:
    """
    Captura cualquier excepción no manejada y retorna JSON en lugar de HTML.
    Evita que Django devuelva páginas de error 500 a una SPA que espera JSON.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        import traceback as tb
        try:
            from .audit import registrar_log
            user = request.user if hasattr(request, 'user') else None
            registrar_log(
                'SEGURIDAD', 'excepcion_no_manejada',
                request if user and user.is_authenticated else None,
                detalle={
                    'error':     str(exception),
                    'traceback': tb.format_exc()[-800:],
                },
            )
        except Exception:
            pass
        return JsonResponse({
            'error':  'Error interno del servidor.',
            'codigo': 'ERROR_INTERNO',
        }, status=500)


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
