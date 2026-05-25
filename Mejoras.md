Vas a implementar el módulo de Solicitudes de Conductores en el panel web (rol USUARIO y SUPERADMIN). Es una sección nueva que recibe las solicitudes enviadas desde la app móvil.

---

## MODELOS NUEVOS (agregar en models.py)

### SolicitudConductor
```python
class SolicitudConductor(models.Model):
    TIPOS = [
        ('mantencion',  'Mantención'),
        ('combustible', 'Combustible'),
        ('incidencia',  'Incidencia'),
        ('documento',   'Documento'),
    ]
    ESTADOS = [
        ('pendiente',   'Pendiente'),
        ('en_revision', 'En revisión'),
        ('aprobado',    'Aprobado'),
        ('rechazado',   'Rechazado'),
    ]
    PRIORIDADES = [
        ('alta',  'Alta'),
        ('media', 'Media'),
        ('baja',  'Baja'),
    ]

    empresa     = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='solicitudes_conductores')
    conductor   = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitudes', limit_choices_to={'rol': 'CONDUCTOR'})
    vehiculo    = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    tipo        = models.CharField(max_length=20, choices=TIPOS)
    titulo      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    prioridad   = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
    estado      = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    foto        = models.FileField(upload_to='solicitudes/%Y/%m/', null=True, blank=True)
    respuesta   = models.TextField(blank=True, default='')
    respondido_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_respondidas')
    respondido_at  = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Solicitud de conductor'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.conductor} — {self.get_estado_display()}"
```

---

## ENDPOINTS NUEVOS

### Panel web (USUARIO)
Agregar en views.py:
GET  /api/empresa/solicitudes/
GET  /api/empresa/solicitudes/:id/
PUT  /api/empresa/solicitudes/:id/aprobar/
PUT  /api/empresa/solicitudes/:id/rechazar/
GET  /api/empresa/solicitudes/conteo/

#### GET /api/empresa/solicitudes/
Parámetros opcionales: estado, tipo, conductor_id, fecha_desde, fecha_hasta, buscar, page, page_size (default 20)

Retorna:
```json
{
  "solicitudes": [...],
  "total": 28,
  "page": 1,
  "pages": 2,
  "resumen": {
    "pendientes": 5,
    "en_revision": 3,
    "aprobadas_hoy": 4,
    "total_mes": 28
  }
}
```

#### PUT /api/empresa/solicitudes/:id/aprobar/
Body: { respuesta: "texto opcional" }
- Cambia estado a 'aprobado'
- Registra respondido_por = request.user, respondido_at = now()
- Envía push al conductor: título "Solicitud aprobada", cuerpo = respuesta o "Tu solicitud fue aprobada"
- Si tipo == 'mantencion': crear Mantencion vinculada con estado='pendiente'
- Si tipo == 'documento': crear Documento vinculado con los datos de la solicitud
- Si tipo == 'combustible': crear GastoOperativo con categoria='combustible' si viene con monto
- registrar_log acción 'solicitud_aprobada'
- notificar al conductor usando notificar()

#### PUT /api/empresa/solicitudes/:id/rechazar/
Body: { respuesta: "motivo obligatorio" }
- Cambia estado a 'rechazado'
- respuesta es obligatoria al rechazar
- Envía push al conductor: título "Solicitud rechazada", cuerpo = respuesta
- registrar_log acción 'solicitud_rechazada'
- notificar al conductor usando notificar()

#### GET /api/empresa/solicitudes/conteo/
Retorna solo el conteo de pendientes para el badge del navbar:
```json
{ "pendientes": 5 }
```
Este endpoint se llama frecuentemente (cada 30s para el badge) — debe ser muy liviano.

### App móvil (CONDUCTOR)
Agregar en views.py:
GET  /api/conductor/solicitudes/
POST /api/conductor/solicitudes/

#### GET /api/conductor/solicitudes/
Solo retorna las solicitudes del conductor autenticado.
Ordenadas por created_at desc.

#### POST /api/conductor/solicitudes/
Acepta multipart/form-data (con foto) o JSON (sin foto).
Body: tipo, titulo, descripcion, prioridad, foto (opcional).
Validar que el conductor tenga un vehículo asignado activo.
Asignar empresa = conductor.empresa y vehiculo = asignacion activa del conductor.
registrar_log acción 'solicitud_creada'.
Notificar a los admins de la empresa con notificar_admins_empresa():
- tipo: 'solicitud_conductor'
- titulo: f"Nueva solicitud de {nombre_conductor}: {titulo}"
- url_accion: '/empresa/solicitudes'

---

## NOTIFICACIONES EN TIEMPO REAL — WebSocket

Para el badge de la campana en tiempo real sin polling, usar Django Channels.

### Backend: consumers.py (agregar o crear)
```python
import json
from channels.generic.websocket import AsyncWebSocketConsumer
from channels.db import database_sync_to_async

class SolicitudesConsumer(AsyncWebSocketConsumer):
    async def connect(self):
        self.empresa_id = self.scope['url_route']['kwargs']['empresa_id']
        self.group_name = f'solicitudes_{self.empresa_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def nueva_solicitud(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'nueva_solicitud',
            'solicitud': event['solicitud'],
        }))
```

### Backend: routing.py
```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/solicitudes/(?P<empresa_id>\d+)/$', consumers.SolicitudesConsumer.as_asgi()),
]
```

### Backend: enviar evento al crear solicitud
En la vista POST /api/conductor/solicitudes/, después de crear la solicitud:
```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    f'solicitudes_{empresa.id}',
    {
        'type': 'nueva_solicitud',
        'solicitud': {
            'id':      solicitud.id,
            'tipo':    solicitud.tipo,
            'titulo':  solicitud.titulo,
            'conductor': nombre_conductor,
        }
    }
)
```

Si el proyecto no tiene Django Channels configurado, usar polling como fallback:
GET /api/empresa/solicitudes/conteo/ cada 30 segundos desde el frontend.

---

## FRONTEND WEB — SolicitudesConductores.vue

Crear src/web/solicitudes/SolicitudesConductores.vue

### Header
Título "Solicitudes de conductores" + nombre empresa.
Botón "Exportar" → GET /api/empresa/solicitudes/?formato=csv

### KPI cards (4)
Pendientes (naranja) · En revisión (azul) · Aprobadas hoy (verde) · Total mes (gris)
Cargados desde resumen del endpoint.

### Tabs + filtros
Tabs: Todas | Pendientes (badge con conteo) | En revisión | Resueltas
Filtros inline: select tipo, select conductor, input búsqueda.

### Tabla
Columnas: Conductor (avatar + nombre + patente), Tipo (badge), Solicitud (título + descripción truncada), Prioridad (badge), Foto (thumbnail clickeable), Fecha (relativa), Estado (badge), Acciones.

Filas con estado 'pendiente': fondo amarillo muy suave (#FFFBEB) para destacarlas visualmente.

Acciones por estado:
- pendiente/en_revision: botones "Aprobar" (verde) y "✗" (rojo)
- aprobado/rechazado: botón "Ver" solo

Click en fila → abre modal de detalle.

Paginación al pie: mostrando X de Y · botones página.

### Modal detalle solicitud
Layout de dos columnas:
- Izquierda: datos de la solicitud (tipo, conductor, vehículo, prioridad, descripción, fecha)
- Derecha: foto si existe (imagen full en el modal con zoom al click), respuesta si existe

Si estado pendiente/en_revision:
- Textarea "Respuesta para el conductor" (obligatoria al rechazar, opcional al aprobar)
- Botones "Aprobar" y "Rechazar" al pie
- Select para cambiar estado a "En revisión" (para marcar que se está procesando)

Si aprobado/rechazado:
- Mostrar la respuesta enviada
- Mostrar quién respondió y cuándo

### Modal rechazar (confirmación)
Cuando se presiona "Rechazar" abrir un modal de confirmación con:
- Campo obligatorio de motivo (mínimo 10 caracteres)
- Aviso: "El conductor recibirá una notificación con este mensaje"
- Botones Cancelar / Rechazar

### Notificación en tiempo real (campana en navbar)
En el componente que maneja el navbar (buscar en contexto.md):
```javascript
// Conectar WebSocket al montar
const ws = new WebSocket(`ws://localhost:8000/ws/solicitudes/${empresaId}/`)

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.tipo === 'nueva_solicitud') {
    contadoPendientes.value++
    showToast(`Nueva solicitud de ${data.solicitud.conductor}: ${data.solicitud.titulo}`, 'info')
  }
}
```

Si no hay WebSocket disponible, fallback con polling:
```javascript
// Polling cada 30 segundos
setInterval(async () => {
  const data = await apiFetch('/api/empresa/solicitudes/conteo/')
  contadoPendientes.value = data.pendientes
}, 30000)
```

El badge con el conteo va sobre el ícono de campana en el navbar.
Si contadoPendientes === 0: no mostrar badge.
Si contadoPendientes > 9: mostrar "9+".

---

## NAVEGACIÓN WEB

Agregar en el sidebar del USUARIO (buscar en contexto.md):
Ítem: Solicitudes
Ícono: ti-message-dots
Ruta: /empresa/solicitudes
Badge: conteo de pendientes (número rojo)

Agregar en router/index.js:
```javascript
{
  path: '/empresa/solicitudes',
  component: () => import('@/web/solicitudes/SolicitudesConductores.vue'),
  meta: { requiresAuth: true, roles: ['USUARIO'] }
}
```

---

## SERIALIZER

```python
class SolicitudConductorSerializer(serializers.ModelSerializer):
    conductor_nombre  = serializers.SerializerMethodField()
    conductor_iniciales = serializers.SerializerMethodField()
    vehiculo_patente  = serializers.CharField(source='vehiculo.patente', read_only=True, default=None)
    tipo_display      = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display    = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    respondido_por_nombre = serializers.SerializerMethodField()
    tiene_foto        = serializers.SerializerMethodField()

    class Meta:
        model  = SolicitudConductor
        fields = [
            'id', 'tipo', 'tipo_display', 'titulo', 'descripcion',
            'prioridad', 'prioridad_display', 'estado', 'estado_display',
            'foto', 'tiene_foto', 'respuesta',
            'conductor', 'conductor_nombre', 'conductor_iniciales',
            'vehiculo', 'vehiculo_patente',
            'respondido_por', 'respondido_por_nombre', 'respondido_at',
            'created_at', 'updated_at',
        ]

    def get_conductor_nombre(self, obj):
        try:
            from .models import descifrar
            return descifrar(obj.conductor.nombre_cifrado)
        except Exception:
            return obj.conductor.email

    def get_conductor_iniciales(self, obj):
        nombre = self.get_conductor_nombre(obj)
        partes = nombre.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        return nombre[:2].upper()

    def get_respondido_por_nombre(self, obj):
        if not obj.respondido_por:
            return None
        try:
            from .models import descifrar
            return descifrar(obj.respondido_por.nombre_cifrado)
        except Exception:
            return obj.respondido_por.email

    def get_tiene_foto(self, obj):
        return bool(obj.foto)
```

---

## URLS (agregar en urls.py)

```python
# Panel web USUARIO
path('api/empresa/solicitudes/',                         SolicitudesListView.as_view()),
path('api/empresa/solicitudes/conteo/',                  SolicitudesConteoView.as_view()),
path('api/empresa/solicitudes/<int:sol_id>/',            SolicitudDetailView.as_view()),
path('api/empresa/solicitudes/<int:sol_id>/aprobar/',    SolicitudAprobarView.as_view()),
path('api/empresa/solicitudes/<int:sol_id>/rechazar/',   SolicitudRechazarView.as_view()),

# App móvil CONDUCTOR
path('api/conductor/solicitudes/',                       ConductorSolicitudesView.as_view()),
```

---

## PUSH AL CONDUCTOR — función helper

Agregar en views.py o en un servicio separado push_service.py:

```python
def push_conductor(conductor, titulo, cuerpo, data=None):
    """Envía push notification al conductor si tiene fcm_token."""
    if not hasattr(conductor, 'fcm_token') or not conductor.fcm_token:
        return
    try:
        import firebase_admin
        from firebase_admin import messaging
        msg = messaging.Message(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data=data or {},
            token=conductor.fcm_token,
            android=messaging.AndroidConfig(priority='high'),
        )
        messaging.send(msg)
    except Exception as e:
        registrar_log(None, 'SEGURIDAD', 'push_error', {'error': str(e), 'conductor': conductor.id})
```

Si Firebase Admin SDK no está configurado, la función falla silenciosamente con log.

---

## CONVENCIONES

- Nunca usar fetch directo — siempre apiFetch
- Composition API <script setup>
- registrar_log en aprobar y rechazar
- notificar() al conductor en aprobar y rechazar
- Si tipo == 'mantencion' al aprobar: crear Mantencion automáticamente
- Si tipo == 'documento' al aprobar: crear Documento automáticamente
- La foto se sirve desde el backend, nunca URL directa del filesystem
- Textos en español es-CL
- Fechas relativas: "hace 2h", "ayer", "hace 3 días"
- Badge del navbar se actualiza por WebSocket (o polling fallback cada 30s)
- Al aprobar/rechazar: cerrar modal + showToast + actualizar tabla sin recargar página

---

## ARCHIVOS A ENTREGAR

Backend:
1. models_patch.py — modelo SolicitudConductor completo
2. serializers_patch.py — SolicitudConductorSerializer completo
3. views_solicitudes_patch.py — todas las vistas con indicación de dónde van en views.py
4. consumers_patch.py — WebSocket consumer
5. routing_patch.py — websocket URL patterns
6. urls_patch.py — las 6 rutas nuevas

Frontend web:
7. SolicitudesConductores.vue — completo
8. navbar_patch.vue — solo el fragmento del badge de campana a agregar
9. router_patch.js — la ruta nueva
10. nav_patch.md — ítem a agregar en el sidebar

Sin "# resto igual".