Vas a implementar la integración completa de Transbank Webpay Plus como pasarela de pago para el sistema SaaS multiempresas. Todo lo nuevo va en views_planes.py salvo indicación explícita.

---

## CONTEXTO DEL SISTEMA

- El sistema ya tiene PlanSuscripcion, Empresa, Suscripcion (o similar) en models.py
- Ya existe ConfiguracionSistema como singleton con get()
- Ya existe notificar_admins_empresa() y registrar_log()
- El SUPERADMIN gestiona empresas y planes desde el panel web
- Las empresas pagan mensual o anualmente por su plan
- Puerto backend: 8000 · Frontend: 7183

---

## PARTE 1 — INSTALACIÓN Y CONFIGURACIÓN

```bash
pip install transbank-sdk
```
Agregar en requirements.txt: transbank-sdk>=4.0.0

Agregar en settings.py:
```python
TRANSBANK_ENVIRONMENT = os.environ.get('TRANSBANK_ENVIRONMENT', 'integration')  # 'integration' | 'production'
TRANSBANK_COMMERCE_CODE = os.environ.get('TRANSBANK_COMMERCE_CODE', '597055555532')  # código de integración por defecto
TRANSBANK_API_KEY = os.environ.get('TRANSBANK_API_KEY', '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C')  # key de integración por defecto
```

Agregar en .env:
TRANSBANK_ENVIRONMENT=integration
TRANSBANK_COMMERCE_CODE=597055555532
TRANSBANK_API_KEY=579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C

Los valores de integración (597055555532 y la API key) son los oficiales de Transbank para pruebas — funcionan sin registro previo.

---

## PARTE 2 — MODELOS NUEVOS (agregar en models.py)

### Suscripcion
```python
class Suscripcion(models.Model):
    ESTADOS = [
        ('trial',      'Trial'),
        ('activa',     'Activa'),
        ('gracia',     'Período de gracia'),
        ('suspendida', 'Suspendida'),
        ('cancelada',  'Cancelada'),
    ]
    CICLOS = [('mensual', 'Mensual'), ('anual', 'Anual')]

    empresa           = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='suscripcion')
    plan              = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT)
    ciclo             = models.CharField(max_length=10, choices=CICLOS, default='mensual')
    estado            = models.CharField(max_length=20, choices=ESTADOS, default='trial')
    fecha_inicio      = models.DateTimeField(null=True, blank=True)
    fecha_fin_periodo = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    trial_hasta       = models.DateTimeField(null=True, blank=True)
    dias_gracia       = models.PositiveSmallIntegerField(default=7)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Suscripción'

    @property
    def esta_bloqueada(self):
        return self.estado in ('suspendida', 'cancelada')

    @property
    def dias_para_vencer(self):
        if not self.fecha_fin_periodo:
            return None
        from django.utils import timezone
        return (self.fecha_fin_periodo.date() - timezone.now().date()).days
```

### PagoTransbank
```python
class PagoTransbank(models.Model):
    ESTADOS = [
        ('iniciado',   'Iniciado'),
        ('aprobado',   'Aprobado'),
        ('rechazado',  'Rechazado'),
        ('anulado',    'Anulado'),
        ('fallido',    'Fallido'),
    ]

    empresa         = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='pagos')
    suscripcion     = models.ForeignKey(Suscripcion, on_delete=models.PROTECT, related_name='pagos')
    token           = models.CharField(max_length=200, unique=True)
    orden_compra    = models.CharField(max_length=64, unique=True)
    monto           = models.PositiveIntegerField()
    estado          = models.CharField(max_length=20, choices=ESTADOS, default='iniciado')
    ciclo           = models.CharField(max_length=10, default='mensual')
    plan_nombre     = models.CharField(max_length=50, blank=True, default='')
    respuesta_tb    = models.JSONField(default=dict, blank=True)
    fecha_pago      = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Pago Transbank'
```

### Agregar a ConfiguracionSistema (ya existe — solo estos campos nuevos)
```python
# Agregar en la clase ConfiguracionSistema existente:
terminos_condiciones   = models.TextField(blank=True, default='')
terminos_version       = models.CharField(max_length=20, blank=True, default='1.0')
terminos_updated_at    = models.DateTimeField(null=True, blank=True)
dias_gracia_pago       = models.PositiveSmallIntegerField(default=7)
bloqueo_automatico     = models.BooleanField(default=True)
mensaje_pago_pendiente = models.TextField(
    blank=True,
    default='Tu suscripción tiene un pago pendiente. Por favor regulariza tu situación para continuar usando el servicio.'
)
```

---

## PARTE 3 — MIDDLEWARE DE BLOQUEO (nuevo archivo)

Crear gestion_backend/g_de_flota/middleware.py (o agregar al existente si ya existe):

```python
from django.http import JsonResponse
from django.utils import timezone

RUTAS_LIBRES = [
    '/api/login/',
    '/api/token/',
    '/api/token/refresh/',
    '/api/pago/',           # checkout Transbank
    '/api/pago/retorno/',   # retorno Transbank
    '/api/terminos/',       # ver términos
    '/admin/',
]

class BloqueoSuscripcionMiddleware:
    """
    Bloquea el acceso a la API si la empresa tiene suscripción suspendida.
    Solo aplica a usuarios con rol USUARIO (no SUPERADMIN ni CONDUCTOR).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(r) for r in RUTAS_LIBRES):
            return self.get_response(request)

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)

        if request.user.rol != 'USUARIO':
            return self.get_response(request)

        empresa = request.user.empresa
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

        # Advertencia si está en período de gracia
        response = self.get_response(request)
        if sus.estado == 'gracia':
            dias = sus.dias_para_vencer
            response['X-Gracia-Dias'] = str(dias or 0)

        return response
```

Registrar en settings.py en MIDDLEWARE (después de AuthenticationMiddleware):
```python
'g_de_flota.middleware.BloqueoSuscripcionMiddleware',
```

---

## PARTE 4 — VISTAS DE PAGO (en views_planes.py)

Importar al inicio de views_planes.py:
```python
import uuid
from django.utils import timezone
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from django.conf import settings

def get_webpay_transaction():
    if settings.TRANSBANK_ENVIRONMENT == 'production':
        options = WebpayOptions(
            commerce_code=settings.TRANSBANK_COMMERCE_CODE,
            api_key=settings.TRANSBANK_API_KEY,
            integration_type=IntegrationType.LIVE,
        )
    else:
        options = WebpayOptions(
            commerce_code=settings.TRANSBANK_COMMERCE_CODE,
            api_key=settings.TRANSBANK_API_KEY,
            integration_type=IntegrationType.TEST,
        )
    return Transaction(options)
```

### POST /api/pago/iniciar/
Solo rol USUARIO con empresa activa.
Body: { plan_id, ciclo }

```python
class PagoIniciarView(View):
    def post(self, request):
        if not request.user.is_authenticated or request.user.rol != 'USUARIO':
            return JsonResponse({'error': 'Sin acceso.'}, status=403)

        body    = json.loads(request.body)
        plan_id = body.get('plan_id')
        ciclo   = body.get('ciclo', 'mensual')
        empresa = request.user.empresa

        try:
            plan = PlanSuscripcion.objects.get(id=plan_id, activo=True)
        except PlanSuscripcion.DoesNotExist:
            return JsonResponse({'error': 'Plan no encontrado.'}, status=404)

        monto = int(plan.precio_anual if ciclo == 'anual' else plan.precio_mensual)
        if not monto:
            return JsonResponse({'error': 'Este plan no tiene precio configurado.'}, status=400)

        orden_compra = f"ORD-{empresa.id}-{uuid.uuid4().hex[:8].upper()}"
        session_id   = f"SES-{request.user.id}-{uuid.uuid4().hex[:6]}"
        return_url   = f"{settings.FRONTEND_URL}/empresa/pago/retorno"

        tx = get_webpay_transaction()
        response = tx.create(
            buy_order=orden_compra,
            session_id=session_id,
            amount=monto,
            return_url=return_url,
        )

        # Obtener o crear suscripción
        sus, _ = Suscripcion.objects.get_or_create(
            empresa=empresa,
            defaults={'plan': plan, 'ciclo': ciclo, 'estado': 'trial'}
        )

        PagoTransbank.objects.create(
            empresa=empresa,
            suscripcion=sus,
            token=response['token'],
            orden_compra=orden_compra,
            monto=monto,
            ciclo=ciclo,
            plan_nombre=plan.get_nombre_display(),
        )

        registrar_log(request, 'ACTIVIDAD', 'pago_iniciado', {
            'plan': plan.nombre, 'monto': monto, 'ciclo': ciclo
        })

        return JsonResponse({
            'url':   response['url'],
            'token': response['token'],
        })
```

### POST /api/pago/retorno/ (retorno de Transbank)
Esta vista recibe el token_ws de Transbank después del pago.
Decorar con @csrf_exempt porque Transbank hace POST directo.

```python
@method_decorator(csrf_exempt, name='dispatch')
class PagoRetornoView(View):
    def post(self, request):
        token_ws = request.POST.get('token_ws') or request.GET.get('token_ws')

        if not token_ws:
            return redirect(f"{settings.FRONTEND_URL}/empresa/pago/fallido?error=sin_token")

        try:
            pago = PagoTransbank.objects.select_related(
                'empresa', 'suscripcion', 'suscripcion__plan'
            ).get(token=token_ws)
        except PagoTransbank.DoesNotExist:
            return redirect(f"{settings.FRONTEND_URL}/empresa/pago/fallido?error=token_invalido")

        try:
            tx       = get_webpay_transaction()
            response = tx.commit(token_ws)

            pago.respuesta_tb = dict(response)
            pago.fecha_pago   = timezone.now()

            # response_code 0 = aprobado
            if response.get('response_code') == 0:
                pago.estado = 'aprobado'
                pago.save()

                sus = pago.suscripcion
                sus.plan   = sus.plan  # mantener o actualizar si cambió
                sus.ciclo  = pago.ciclo
                sus.estado = 'activa'
                sus.fecha_inicio      = timezone.now()
                sus.fecha_fin_periodo = (
                    timezone.now() + timezone.timedelta(days=365)
                    if pago.ciclo == 'anual'
                    else timezone.now() + timezone.timedelta(days=30)
                )
                sus.save()

                # Actualizar plan de la empresa
                sus.empresa.plan = sus.plan
                sus.empresa.save()

                notificar_admins_empresa(
                    empresa=pago.empresa,
                    tipo='actividad',
                    titulo='Pago procesado correctamente',
                    mensaje=f'Tu plan {sus.plan.get_nombre_display()} está activo. Próximo cobro: {sus.fecha_fin_periodo.strftime("%d/%m/%Y")}.',
                    extra={'pago_id': pago.id}
                )

                registrar_log(None, 'ACTIVIDAD', 'pago_aprobado', {
                    'empresa_id': pago.empresa.id, 'monto': pago.monto, 'plan': pago.plan_nombre
                })

                return redirect(f"{settings.FRONTEND_URL}/empresa/pago/exitoso?orden={pago.orden_compra}")

            else:
                pago.estado = 'rechazado'
                pago.save()

                notificar_admins_empresa(
                    empresa=pago.empresa,
                    tipo='seguridad',
                    titulo='Pago rechazado',
                    mensaje='Tu pago fue rechazado por Transbank. Intenta nuevamente.',
                    extra={'pago_id': pago.id}
                )

                return redirect(f"{settings.FRONTEND_URL}/empresa/pago/fallido?error=rechazado")

        except Exception as e:
            pago.estado = 'fallido'
            pago.save()
            registrar_log(None, 'SEGURIDAD', 'pago_error', {'error': str(e), 'pago_id': pago.id})
            return redirect(f"{settings.FRONTEND_URL}/empresa/pago/fallido?error=error_sistema")
```

### GET /api/pago/historial/
Solo USUARIO — historial de pagos de su empresa:
```python
class PagoHistorialView(View):
    def get(self, request):
        if request.user.rol not in ('USUARIO', 'SUPERADMIN'):
            return JsonResponse({'error': 'Sin acceso.'}, status=403)

        empresa = request.user.empresa if request.user.rol == 'USUARIO' else None
        empresa_id = request.GET.get('empresa_id')

        if request.user.rol == 'SUPERADMIN' and empresa_id:
            empresa = Empresa.objects.get(id=empresa_id)

        pagos = PagoTransbank.objects.filter(
            empresa=empresa, estado='aprobado'
        ).select_related('suscripcion__plan')

        data = [{
            'id':           p.id,
            'orden_compra': p.orden_compra,
            'monto':        p.monto,
            'plan':         p.plan_nombre,
            'ciclo':        p.ciclo,
            'fecha':        p.fecha_pago.strftime('%d/%m/%Y %H:%M') if p.fecha_pago else None,
            'estado':       p.estado,
        } for p in pagos]

        return JsonResponse({'pagos': data})
```

### GET/PUT /api/admin/terminos/
Solo SUPERADMIN:
```python
class TerminosView(View):
    def get(self, request):
        config = ConfiguracionSistema.get()
        return JsonResponse({
            'terminos':         config.terminos_condiciones,
            'version':          config.terminos_version,
            'updated_at':       config.terminos_updated_at.isoformat() if config.terminos_updated_at else None,
            'dias_gracia':      config.dias_gracia_pago,
            'bloqueo_auto':     config.bloqueo_automatico,
            'mensaje_bloqueo':  config.mensaje_pago_pendiente,
        })

    def put(self, request):
        if request.user.rol != 'SUPERADMIN':
            return JsonResponse({'error': 'Sin acceso.'}, status=403)
        body   = json.loads(request.body)
        config = ConfiguracionSistema.get()
        if 'terminos' in body:
            config.terminos_condiciones = body['terminos']
            config.terminos_version     = body.get('version', config.terminos_version)
            config.terminos_updated_at  = timezone.now()
        if 'dias_gracia'     in body: config.dias_gracia_pago       = body['dias_gracia']
        if 'bloqueo_auto'    in body: config.bloqueo_automatico      = body['bloqueo_auto']
        if 'mensaje_bloqueo' in body: config.mensaje_pago_pendiente  = body['mensaje_bloqueo']
        config.save()
        registrar_log(request, 'ACTIVIDAD', 'terminos_actualizados', {'version': config.terminos_version})
        return JsonResponse({'ok': True})

# Endpoint público para que cualquier empresa pueda leer los términos:
class TerminosPublicosView(View):
    def get(self, request):
        config = ConfiguracionSistema.get()
        return JsonResponse({
            'terminos': config.terminos_condiciones,
            'version':  config.terminos_version,
            'fecha':    config.terminos_updated_at.strftime('%d/%m/%Y') if config.terminos_updated_at else None,
        })
```

### Management command: verificar_suscripciones
Crear g_de_flota/management/commands/verificar_suscripciones.py
Ejecutar diariamente con cron: 0 9 * * *

Lógica:
```python
def handle(self, *args, **kwargs):
    from django.utils import timezone
    config = ConfiguracionSistema.get()
    hoy    = timezone.now()

    suscripciones = Suscripcion.objects.filter(
        estado__in=['activa', 'gracia']
    ).select_related('empresa', 'plan')

    for sus in suscripciones:
        if not sus.fecha_fin_periodo:
            continue

        dias = (sus.fecha_fin_periodo - hoy).days

        if sus.estado == 'activa' and dias <= 0:
            # Vencida → pasar a gracia
            sus.estado = 'gracia'
            sus.save()
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='seguridad',
                titulo='Suscripción vencida — período de gracia iniciado',
                mensaje=f'Tu suscripción venció. Tienes {config.dias_gracia_pago} días para regularizar el pago antes de que el servicio sea suspendido.',
            )

        elif sus.estado == 'gracia':
            dias_en_gracia = (hoy - sus.fecha_fin_periodo).days
            if dias_en_gracia >= config.dias_gracia_pago and config.bloqueo_automatico:
                sus.estado = 'suspendida'
                sus.empresa.estado = 'suspendida'
                sus.empresa.save()
                sus.save()
                notificar_admins_empresa(
                    empresa=sus.empresa,
                    tipo='seguridad',
                    titulo='Servicio suspendido por falta de pago',
                    mensaje=config.mensaje_pago_pendiente,
                )

        elif sus.estado == 'activa' and dias in [30, 15, 7, 3, 1]:
            notificar_admins_empresa(
                empresa=sus.empresa,
                tipo='actividad',
                titulo=f'Tu suscripción vence en {dias} días',
                mensaje=f'El plan {sus.plan.get_nombre_display()} vence el {sus.fecha_fin_periodo.strftime("%d/%m/%Y")}. Renueva para evitar interrupciones.',
            )

    self.stdout.write(self.style.SUCCESS('Suscripciones verificadas.'))
```

---

## PARTE 5 — URLS (agregar en urls.py)

```python
path('api/pago/iniciar/',           PagoIniciarView.as_view()),
path('api/pago/retorno/',           PagoRetornoView.as_view()),
path('api/pago/historial/',         PagoHistorialView.as_view()),
path('api/admin/terminos/',         TerminosView.as_view()),
path('api/terminos/',               TerminosPublicosView.as_view()),
path('api/admin/suscripciones/',    SuscripcionesAdminView.as_view()),
path('api/empresa/suscripcion/',    SuscripcionEmpresaView.as_view()),
```

---

## PARTE 6 — FRONTEND WEB

### src/web/pago/IniciarPago.vue
Vista para que la empresa seleccione plan y ciclo antes de pagar.
Tabs mensual / anual con ahorro calculado.
Cards de planes disponibles (traídas de GET /api/configuracion/planes/).
Al seleccionar plan y ciclo → POST /api/pago/iniciar/ → redirigir a response.url con window.location.href.
Mostrar spinner mientras redirige.
Nota: "Serás redirigido a Webpay de Transbank para completar el pago de forma segura."

### src/web/pago/PagoExitoso.vue
Ruta: /empresa/pago/exitoso
Leer ?orden= de la URL y mostrar resumen del pago.
Botón "Ir al panel" → router.push('/empresa/dashboard').
Llamar GET /api/empresa/suscripcion/ para mostrar el estado actualizado.

### src/web/pago/PagoFallido.vue
Ruta: /empresa/pago/fallido
Leer ?error= de la URL y mostrar mensaje apropiado según el código:
- rechazado: "Tu pago fue rechazado. Verifica los datos de tu tarjeta."
- sin_token: "Ocurrió un error en la sesión de pago."
- error_sistema: "Error del sistema. Intenta nuevamente."
Botón "Reintentar pago" → router.push('/empresa/pago').

### src/web/pago/HistorialPagos.vue
Vista para el USUARIO: tabla de pagos aprobados con columnas orden, plan, ciclo, monto, fecha.
Formatear monto en CLP: $149.000.
Botón exportar CSV.

### src/web/admin/PagosSuperAdmin.vue
Vista para el SUPERADMIN con:

KPI cards: MRR del mes, total cobrado este mes, empresas activas, empresas en gracia/suspendidas.

Tabla de todas las empresas con columnas:
Empresa · Plan · Ciclo · Estado suscripción · Próximo cobro · Último pago · Acciones

Badges de estado:
- activa: verde
- trial: azul
- gracia: naranja con días restantes
- suspendida: rojo
- cancelada: gris

Acciones por fila:
- suspendida: botón "Reactivar" → PUT /api/admin/suscripciones/:id/reactivar/
- gracia: botón "Extender gracia" (N días más)
- activa: botón "Ver pagos"

Filtros: estado, plan, búsqueda por nombre.

### src/web/configuracion/TerminosCondiciones.vue
Vista dentro del módulo de configuración del SUPERADMIN.
Tab "Términos y condiciones":
- Editor de texto enriquecido (usar textarea grande, no WYSIWYG — mantener simple)
- Campo versión (ej: "1.2")
- Botón "Guardar y publicar" → PUT /api/admin/terminos/
- Fecha de última actualización

Tab "Configuración de pagos":
- Input: días de gracia antes del bloqueo (número)
- Toggle: bloqueo automático activado/desactivado
- Textarea: mensaje de bloqueo (lo que ve la empresa bloqueada)
- Badge de ambiente: TEST o PRODUCCIÓN según TRANSBANK_ENVIRONMENT

### src/web/empresa/BannerSuscripcion.vue
Banner que aparece en EmpresaLayout.vue cuando la suscripción está por vencer o en gracia.

Leer estado desde GET /api/empresa/suscripcion/ al montar. Refrescar cada 10 minutos.

Variantes:
- gracia (naranja): "Tu suscripción venció. Tienes X días para pagar antes de que el servicio sea suspendido. [Pagar ahora]"
- por_vencer ≤7 días (amarillo): "Tu suscripción vence en X días. [Renovar]"
- suspendida (rojo, pantalla completa bloqueante): overlay que cubre todo el contenido con el mensaje de bloqueo y botón "Regularizar pago"

El overlay de suspensión usa position:fixed con z-index alto para bloquear toda interacción. Solo permite ir a /empresa/pago.

### Interceptor en api.js
En apiFetch, después del manejo de 401/403 existente, agregar:
```javascript
if (res.status === 402) {
  const data = await res.json()
  if (data.codigo === 'SUSCRIPCION_BLOQUEADA') {
    window.dispatchEvent(new CustomEvent('suscripcion-bloqueada', { detail: data }))
    throw new Error(data.error)
  }
}
```

En EmpresaLayout.vue al montar:
```javascript
window.addEventListener('suscripcion-bloqueada', () => {
  router.push('/empresa/pago')
})
```

---

## PARTE 7 — TÉRMINOS Y CONDICIONES EN ONBOARDING

En el login web de la empresa (cuando primer_login=true), antes de acceder al panel mostrar pantalla de aceptación de términos:

GET /api/terminos/ → mostrar el texto con scroll obligatorio
Checkbox "He leído y acepto los términos y condiciones (versión X.X)"
Botón "Aceptar y continuar" — deshabilitado hasta que se marque el checkbox y se llegue al final del scroll
POST /api/empresa/terminos/aceptar/ → guarda version aceptada y fecha en Usuario.extra

Si los términos se actualizan (nueva versión), mostrar nuevamente la pantalla de aceptación al próximo login.

---

## URLS adicionales para términos

```python
path('api/empresa/terminos/aceptar/', TerminosAceptarView.as_view()),
```

Vista TerminosAceptarView:
- POST con { version }
- Guardar en request.user.extra = { ..., terminos_version: version, terminos_aceptado_at: now().isoformat() }
- Si Usuario no tiene campo extra: agregar extra = models.JSONField(default=dict, blank=True) en models.py

---

## TARJETAS DE PRUEBA TRANSBANK (ambiente integration)

Agregar en la vista de configuración del SUPERADMIN como sección informativa:

| Número | Resultado | CVC | Fecha exp |
|---|---|---|---|
| 4051 8856 0044 6623 | Aprobado | 123 | Cualquier fecha futura |
| 4051 8842 3993 7763 | Rechazado | 123 | Cualquier fecha futura |
| 5186 0595 5959 0568 | Aprobado (débito) | 123 | Cualquier fecha futura |

RUT para autenticación en ambiente test: 11.111.111-1, clave: 123

---

## NAVEGACIÓN

Agregar en sidebar USUARIO:
- Ítem: "Suscripción y pagos" · ícono: ti-credit-card · ruta: /empresa/pago

Agregar en sidebar SUPERADMIN:
- Ítem: "Pagos" · ícono: ti-report-money · ruta: /admin/pagos
- En módulo Configuración: tab "Términos y condiciones"

Agregar en router/index.js:
```javascript
{ path: '/empresa/pago',          component: () => import('@/web/pago/IniciarPago.vue'),        meta: { roles: ['USUARIO'] } },
{ path: '/empresa/pago/exitoso',  component: () => import('@/web/pago/PagoExitoso.vue'),         meta: { roles: ['USUARIO'] } },
{ path: '/empresa/pago/fallido',  component: () => import('@/web/pago/PagoFallido.vue'),         meta: { roles: ['USUARIO'] } },
{ path: '/empresa/pagos',         component: () => import('@/web/pago/HistorialPagos.vue'),      meta: { roles: ['USUARIO'] } },
{ path: '/admin/pagos',           component: () => import('@/web/admin/PagosSuperAdmin.vue'),    meta: { roles: ['SUPERADMIN'] } },
```

---

## CONVENCIONES
- Montos siempre en CLP entero sin decimales: $149.000
- @csrf_exempt solo en PagoRetornoView
- registrar_log en: pago iniciado, pago aprobado, pago rechazado, suspensión, reactivación, términos actualizados
- notificar_admins_empresa en: pago aprobado, vencimiento próximo, período de gracia, suspensión
- Fail-silent en BannerSuscripcion si el endpoint falla
- SUPERADMIN nunca es bloqueado por el middleware
- El bloqueo opera a nivel de API — el frontend muestra el overlay pero el backend igual rechaza las peticiones
- Cron diario obligatorio: 0 9 * * * python manage.py verificar_suscripciones
- Textos en español es-CL

---

## ARCHIVOS A ENTREGAR

Backend:
1. models_patch.py — Suscripcion, PagoTransbank + campos nuevos en ConfiguracionSistema + campo extra en Usuario
2. views_pago_patch.py — PagoIniciarView, PagoRetornoView, PagoHistorialView, TerminosView, TerminosPublicosView, TerminosAceptarView, SuscripcionEmpresaView, SuscripcionesAdminView con indicación de dónde van en views_planes.py
3. middleware_patch.py — BloqueoSuscripcionMiddleware con indicación de dónde va y cómo registrar en settings.py
4. management/commands/verificar_suscripciones.py — completo
5. urls_patch.py — todas las rutas nuevas
6. settings_patch.py — líneas a agregar en settings.py y MIDDLEWARE

Frontend:
7. IniciarPago.vue — completo
8. PagoExitoso.vue — completo
9. PagoFallido.vue — completo
10. HistorialPagos.vue — completo
11. PagosSuperAdmin.vue — completo
12. TerminosCondiciones.vue — completo
13. BannerSuscripcion.vue — completo
14. api_js_patch.js — solo el bloque 402 a agregar
15. router_patch.js — rutas nuevas
16. nav_patch.md — ítems a agregar en sidebars

Sin "# resto igual".