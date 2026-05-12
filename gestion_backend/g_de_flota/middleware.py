import time
from django.http import JsonResponse
from django.contrib.auth import logout
from django.conf import settings

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
