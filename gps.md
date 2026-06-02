Necesito que implementes el módulo GPS completo. El sistema ya existe, está en producción y funciona — tu trabajo es agregar este módulo sin romper absolutamente nada de lo existente.

Stack tecnológico
Backend:

Python 3.11 / Django 5
Django REST Framework
Django Channels + Daphne (ASGI) — ya configurado y funcionando
djangorestframework-simplejwt
cryptography (Fernet) — cifrado de campos sensibles en BD
SQLite en desarrollo / PostgreSQL en producción
firebase-admin 7.4.x (push notifications)

Frontend web:

Vue 3 Composition API (<script setup>)
Vite (puerto 7183)
Vue Router
TailwindCSS
Chart.js
Leaflet.js (ya usado en MapaRuta.vue)

App móvil:

Vue 3 + Capacitor 8
Pinia
Leaflet.js


Estructura del repositorio
gestion_flota/
├── gestion_backend/
│   ├── manage.py
│   └── g_de_flota/
│       ├── models.py
│       ├── views.py
│       ├── views_rutas.py
│       ├── views_conductor.py
│       ├── views_solicitudes.py
│       ├── views_gastos.py
│       ├── views_reportes.py
│       ├── views_documentos.py
│       ├── views_planes.py
│       ├── views_config.py
│       ├── consumers.py
│       ├── routing.py
│       ├── audit.py
│       ├── error_helpers.py
│       ├── serializers.py
│       ├── backends.py
│       ├── firebase_push.py
│       ├── ruta_calculator.py
│       └── middleware.py
└── gestion-frontend/
    └── src/
        ├── utils/
        │   ├── api.js
        │   └── permisos.js
        ├── components/
        │   ├── AppToast.vue
        │   ├── ConfirmModal.vue
        │   └── NotificacionesBell.vue
        └── web/
            ├── empresa/
            │   ├── EmpresaLayout.vue
            │   └── flota/
            │       ├── ListaFlota.vue
            │       └── FormVehiculo.vue
            └── rutas/
                └── MapaRuta.vue

Modelos existentes que debes conocer pero NO modificar
python# Cifrado Fernet — así funciona en este proyecto
class EncryptedFloatField(models.Field):
    # Almacena floats cifrados con Fernet en la BD
    # Se usa igual que FloatField pero el valor en BD es texto cifrado
    # Al leer devuelve float, al escribir cifra automáticamente

class Vehiculo(models.Model):
    flota        = models.ForeignKey(Flota, on_delete=models.CASCADE)
    patente      = models.CharField(max_length=10, unique=True)
    marca        = models.CharField(max_length=50)
    modelo       = models.CharField(max_length=50)
    anio         = models.IntegerField()
    km_actuales  = models.IntegerField(default=0)
    activo       = models.BooleanField(default=True)
    en_mantencion = models.BooleanField(default=False)
    # related_names disponibles: 'ubicaciones', 'asignaciones', 'dispositivo_gps'

class Asignacion(models.Model):
    # Relación conductor ↔ vehículo (NO es asignación de GPS)
    conductor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='asignaciones_conductor',
        null=True, blank=True,
        limit_choices_to={'rol': Rol.CONDUCTOR}
    )
    vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='asignaciones')
    activo    = models.BooleanField(default=True)
    desde     = models.DateTimeField(auto_now_add=True)
    hasta     = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['vehiculo'], condition=models.Q(activo=True), name='unique_active_vehicle_assignment'),
            models.UniqueConstraint(fields=['conductor'], condition=models.Q(activo=True), name='unique_active_conductor_assignment'),
        ]

class Ubicacion(models.Model):
    # Este modelo YA EXISTE y es exactamente lo que necesitamos — no crear otro
    vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='ubicaciones')
    latitud   = EncryptedFloatField()
    longitud  = EncryptedFloatField()
    velocidad = EncryptedFloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

class Empresa(models.Model):
    nombre = models.CharField(max_length=30)
    # tiene rut_cifrado, email_cifrado, etc.
    # related_name: 'flotas', 'usuarios', 'dispositivos_gps'

class Usuario(models.Model):
    # hereda AbstractUser
    empresa = models.ForeignKey(Empresa, ...)
    rol     = models.CharField(choices=Rol.choices)  # SUPERADMIN, USUARIO, CONDUCTOR

Patrones del proyecto — debes seguirlos exactamente
1. Manejo de errores — error_helpers.py
python# Importar así en cada vista nueva
from .error_helpers import error_response, validar_campos, vista_segura

# Usar así — NUNCA retornar JsonResponse directo con error
return error_response('Dispositivo no encontrado', 'NO_ENCONTRADO', 404)
return error_response('IMEI requerido', 'VALIDACION', 400)

# Decorar TODOS los métodos de vistas-clase
class DispositivoGPSView(View):
    @vista_segura
    def get(self, request):
        ...
    @vista_segura
    def post(self, request):
        ...
Códigos de error estándar disponibles:

SIN_AUTENTICACION → 401
SIN_PERMISO → 403
NO_ENCONTRADO → 404
VALIDACION → 400
LIMITE_PLAN → 403
MODULO_NO_INCLUIDO → 403
SUSCRIPCION_BLOQUEADA → 402
ERROR_INTERNO → 500

2. Auditoría — audit.py
pythonfrom .audit import registrar_log

# Llamar en TODA operación de escritura (POST, PUT, DELETE)
registrar_log(
    tipo='ACTIVIDAD',
    accion='gps_dispositivo_creado',   # snake_case descriptivo
    usuario=request.user,
    request=request,
    detalle={
        'imei': dispositivo.imei,
        'modelo': dispositivo.modelo,
        'vehiculo_id': vehiculo.id if vehiculo else None
    }
)
Acciones a registrar: gps_dispositivo_creado, gps_dispositivo_editado, gps_dispositivo_eliminado, gps_asignado, gps_desasignado, gps_config_guardada, gps_posicion_recibida (solo log en errores, no en cada posición normal).
3. Autenticación y empresa en vistas Django
python# Patrón usado en TODAS las vistas existentes — seguir exactamente
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class MiVista(View):
    @vista_segura
    def get(self, request):
        # 1. Autenticar JWT
        auth = JWTAuthentication()
        try:
            validated = auth.authenticate(request)
            if not validated:
                return error_response('Token requerido', 'SIN_AUTENTICACION', 401)
            user, token = validated
        except Exception:
            return error_response('Token inválido', 'SIN_AUTENTICACION', 401)

        # 2. Verificar rol
        if user.rol not in ['USUARIO', 'SUPERADMIN']:
            return error_response('Sin permiso', 'SIN_PERMISO', 403)

        # 3. Obtener empresa (USUARIO usa la suya, SUPERADMIN puede recibir ?empresa_id=)
        if user.rol == 'SUPERADMIN':
            empresa_id = request.GET.get('empresa_id')
            empresa = Empresa.objects.get(id=empresa_id)
        else:
            empresa = user.empresa

        # 4. Filtrar SIEMPRE por empresa — nunca exponer datos de otras empresas
        dispositivos = DispositivoGPS.objects.filter(empresa=empresa)
4. WebSocket — seguir patrón de ConductorConsumer
python# consumers.py — patrón existente que debes replicar para GPSConsumer
class ConductorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Obtener token del query string
        query = parse_qs(self.scope['query_string'].decode())
        token_key = query.get('token', [None])[0]

        # 2. Validar JWT
        try:
            UntypedToken(token_key)
            decoded = decode(token_key, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = decoded.get('user_id')
            self.user = await get_user(user_id)
        except Exception:
            await self.close()
            return

        # 3. Unirse al grupo por empresa
        self.group_name = f'conductor_{self.user.empresa_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def solicitud_actualizada(self, event):
        await self.send(text_data=json.dumps(event))
El GPSConsumer debe:

Ruta: ws/gps/<empresa_id>/
Autenticar JWT igual que arriba
Verificar que empresa_id de la URL coincida con user.empresa_id — si no, cerrar
Grupo: gps_{empresa_id}
Manejar evento tipo position_update y reenviarlo al frontend

5. Frontend — apiFetch
javascript// src/utils/api.js — usar siempre así, nunca fetch directo
import { apiFetch } from '@/utils/api.js'

// GET
const data = await apiFetch('/api/empresa/gps/dispositivos/')

// POST
const nuevo = await apiFetch('/api/empresa/gps/dispositivos/', {
  method: 'POST',
  body: { imei: '123456789012345', modelo: 'teltonika_fmb920' }
})

// PUT
await apiFetch(`/api/empresa/gps/dispositivos/${id}/`, {
  method: 'PUT',
  body: { activo: false }
})

// DELETE
await apiFetch(`/api/empresa/gps/dispositivos/${id}/`, { method: 'DELETE' })

// apiFetch maneja automáticamente:
// - Header Authorization: Bearer <token>
// - Refresh JWT en 401
// - Inyección de empresa_id
// - Timeout de 15 segundos
// - Parseo seguro de JSON
6. Frontend — toasts
javascript// Usar en TODA operación de escritura exitosa o fallida
window.dispatchEvent(new CustomEvent('app-toast', {
  detail: {
    tipo: 'exito',        // 'exito' | 'error' | 'info' | 'advertencia'
    mensaje: 'Dispositivo GPS registrado correctamente.'
  }
}))
7. Frontend — permisos
javascript// src/utils/permisos.js — importar así
import { tieneModulo, tienePermiso } from '@/utils/permisos.js'

// En el template
tieneModulo('gps')              // muestra/oculta sección entera
tienePermiso('gps.ver')         // puede ver la lista
tienePermiso('gps.gestionar')   // puede crear/editar/eliminar/asignar
8. Frontend — ConfirmModal
vue<!-- Reutilizar el componente existente — no crear modales de confirmación nuevos -->
<ConfirmModal
  v-if="mostrarConfirm"
  titulo="Eliminar dispositivo"
  mensaje="¿Estás seguro? Esta acción no se puede deshacer."
  @confirmar="eliminarDispositivo"
  @cancelar="mostrarConfirm = false"
/>

Lo que debes crear
Archivo 1: gestion_backend/g_de_flota/models_gps.py
Modelos nuevos:
DispositivoGPS

empresa → ForeignKey a Empresa, related_name='dispositivos_gps', CASCADE
vehiculo → OneToOneField a Vehiculo, related_name='dispositivo_gps', SET_NULL, null=True, blank=True
imei → CharField max_length=20, unique=True
modelo → CharField choices: emulador, teltonika_fmb920, teltonika_fmc125, queclink_gl300, coban_tk103, otro
activo → BooleanField default=True
creado_at → DateTimeField auto_now_add=True
__str__: f"{self.imei} — {self.get_modelo_display()}"
Meta: ordering = ['-creado_at'], verbose_name = 'Dispositivo GPS'

ConfiguracionGPS

empresa → OneToOneField a Empresa, related_name='configuracion_gps', CASCADE
servidor_ip → CharField max_length=50, blank=True, default=''
servidor_puerto → IntegerField default=5000
protocolo → CharField choices: tcp, udp, default='tcp'
activo → BooleanField default=True
actualizado_at → DateTimeField auto_now=True
__str__: f"Config GPS — {self.empresa.nombre}"


Archivo 2: gestion_backend/g_de_flota/views_gps.py
Implementar estas 7 vistas/endpoints completos:
DispositivosListView — GET/POST /api/empresa/gps/dispositivos/
GET response:
json{
  "dispositivos": [
    {
      "id": 1,
      "imei": "123456789012345",
      "modelo": "teltonika_fmb920",
      "modelo_display": "Teltonika FMB920",
      "activo": true,
      "vehiculo_id": 3,
      "vehiculo_patente": "ABCD12",
      "vehiculo_nombre": "Toyota Hilux 2022",
      "creado_at": "2026-06-01T10:00:00Z"
    }
  ],
  "total": 1
}
POST body:
json{ "imei": "123456789012345", "modelo": "teltonika_fmb920", "activo": true }
Validar: IMEI requerido, longitud entre 10 y 20 caracteres, único en toda la plataforma. Registrar log gps_dispositivo_creado.
DispositivoDetailView — GET/PUT/DELETE /api/empresa/gps/dispositivos/<id>/
PUT permite cambiar imei, modelo, activo. Validar que el dispositivo pertenezca a la empresa del usuario. Log en PUT (gps_dispositivo_editado) y DELETE (gps_dispositivo_eliminado). Al eliminar, si tiene vehículo asignado, desasignar primero.
AsignarVehiculoView — POST /api/empresa/gps/dispositivos/<id>/asignar/
Body: { "vehiculo_id": 3 }
Validaciones:

El vehículo debe pertenecer a la misma empresa
El vehículo no debe tener ya otro dispositivo GPS asignado (verificar hasattr(vehiculo, 'dispositivo_gps'))
El dispositivo no debe tener ya un vehículo asignado

Si pasa validaciones: dispositivo.vehiculo = vehiculo, dispositivo.save(). Log gps_asignado.
Response: { "ok": true, "vehiculo_patente": "ABCD12" }
DesasignarVehiculoView — POST /api/empresa/gps/dispositivos/<id>/desasignar/
Setear dispositivo.vehiculo = None, save. Log gps_desasignado. Response: { "ok": true }.
PosicionView — POST /api/empresa/gps/posicion/
Este es el endpoint que llama el adaptador GPS (emulador o físico). Body:
json{ "imei": "123456789012345", "latitud": -33.4372, "longitud": -70.6506, "velocidad": 48.5 }
Lógica:

Buscar DispositivoGPS por IMEI — si no existe: 404
Verificar que tenga vehículo asignado — si no: 400 con "Sin vehículo asignado"
Verificar que el dispositivo esté activo — si no: 400
Crear Ubicacion(vehiculo=dispositivo.vehiculo, latitud=lat, longitud=lng, velocidad=vel)
Emitir por WebSocket al grupo gps_{empresa_id}:

json{
  "type": "position_update",
  "vehiculo_id": 3,
  "patente": "ABCD12",
  "latitud": -33.4372,
  "longitud": -70.6506,
  "velocidad": 48.5,
  "timestamp": "2026-06-01T10:05:00Z"
}

Response: { "ok": true }

IMPORTANTE: Este endpoint NO requiere JWT — lo llaman dispositivos físicos que se autentican solo por IMEI. Agregar un campo api_key opcional a DispositivoGPS para autenticación futura, pero por ahora validar solo por IMEI existente y activo.
UltimasPosicionesView — GET /api/empresa/gps/vehiculos/posicion/
Devuelve la última Ubicacion de cada vehículo de la empresa que tenga un DispositivoGPS activo asignado.
json{
  "vehiculos": [
    {
      "vehiculo_id": 3,
      "patente": "ABCD12",
      "marca": "Toyota",
      "modelo": "Hilux",
      "latitud": -33.4372,
      "longitud": -70.6506,
      "velocidad": 48.5,
      "timestamp": "2026-06-01T10:05:00Z",
      "tiene_conductor": true,
      "conductor_nombre": "Juan Pérez",
      "estado": "movimiento"  // 'movimiento' si velocidad > 2, 'detenido' si velocidad <= 2
    }
  ]
}
Obtener la última ubicación con: vehiculo.ubicaciones.order_by('-timestamp').first()
ConfiguracionGPSView — GET/PUT /api/empresa/gps/configuracion/
GET: devuelve o crea con defaults la ConfiguracionGPS de la empresa (get_or_create).
PUT body: { "servidor_ip": "190.20.30.40", "servidor_puerto": 5000, "protocolo": "tcp" }
Log en PUT: gps_config_guardada.

Archivo 3: gestion_backend/g_de_flota/gps_providers/__init__.py
Vacío.

Archivo 4: gestion_backend/g_de_flota/gps_providers/base.py
pythonfrom abc import ABC, abstractmethod
from typing import Callable, Dict

class IGPSProvider(ABC):
    """
    Interfaz estándar que todo adaptador GPS debe implementar.
    El sistema de flota solo interactúa con esta interfaz —
    nunca con el hardware directamente.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establece conexión con el dispositivo o servicio GPS."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra la conexión limpiamente."""
        pass

    @abstractmethod
    def get_position(self) -> Dict:
        """
        Retorna la posición actual.
        Returns: { 'latitud': float, 'longitud': float, 'velocidad': float, 'timestamp': str ISO8601 }
        """
        pass

    @abstractmethod
    def on_position_update(self, callback: Callable[[Dict], None]) -> None:
        """
        Registra un callback que se invoca cada vez que hay nueva posición.
        El callback recibe el mismo dict que get_position().
        """
        pass

    @abstractmethod
    def parse_raw(self, raw: str) -> Dict:
        """
        Parsea una trama cruda del protocolo del dispositivo
        y retorna el dict estándar de posición.
        """
        pass

Archivo 5: gestion_backend/g_de_flota/gps_providers/nmea_emulator.py
Implementación completa de NMEAEmulatorAdapter(IGPSProvider):

Rutas hardcodeadas con coordenadas REALES de Santiago:

Ruta 1: Providencia → Las Condes (5+ puntos reales)
Ruta 2: Ñuñoa → Santiago Centro (5+ puntos reales)
Ruta 3: Maipú → Vitacura (5+ puntos reales)


Constructor: __init__(self, imei: str, api_url: str, intervalo_seg: int = 5)
connect(): inicia un threading.Thread que en loop cada intervalo_seg segundos:

Avanza al siguiente punto de la ruta (circular)
Agrega ruido aleatorio pequeño a lat/lng (±0.0005)
Genera velocidad aleatoria entre 20 y 70 km/h
Llama al callback registrado con on_position_update
Hace POST a {api_url}/api/empresa/gps/posicion/ con los datos


disconnect(): setea flag _running = False para detener el thread
parse_raw(raw): parsea una trama $GPRMC real y extrae lat, lng, velocidad
Generar trama NMEA $GPRMC válida en cada tick para el log


Archivo 6: gestion_backend/g_de_flota/gps_providers/teltonika.py
Esqueleto documentado de TeltonikaAdapter(IGPSProvider):
pythonclass TeltonikaAdapter(IGPSProvider):
    """
    Adaptador para dispositivos Teltonika (FMB920, FMC125).
    Protocolo: CODEC8 sobre TCP.

    Configuración del dispositivo físico (se hace UNA sola vez con el software Teltonika Configurator):
    - Server IP: la IP pública de tu servidor Django
    - Server Port: el puerto configurado en ConfiguracionGPS (default 5000)
    - Protocol: TCP
    - APN: según operador (Entel: 'bam.entelpcs.cl', Movistar: 'web.movistar.cl')

    Protocolo CODEC8:
    - El dispositivo abre conexión TCP al servidor
    - Envía paquete de handshake con el IMEI (15 bytes ASCII)
    - El servidor responde 0x01 (aceptado) o 0x00 (rechazado)
    - Luego envía paquetes de datos con AVL (posición + parámetros)
    - Estructura: Preamble(4) + DataLength(4) + CodecID(1) + RecordCount(1) + Records + CRC(4)

    Para activar cuando llegue el hardware físico:
    1. Implementar servidor TCP en gps_tcp_server.py que escuche en ConfiguracionGPS.servidor_puerto
    2. Descomentar parse_raw() con el parser CODEC8 completo
    3. Registrar el adaptador en el registry con modelo='teltonika_fmb920'
    """

    def connect(self): ...
    def disconnect(self): ...
    def get_position(self): ...
    def on_position_update(self, callback): ...
    def parse_raw(self, raw: str) -> dict: ...
        # TODO cuando llegue hardware:
        # 1. raw es bytes del paquete CODEC8
        # 2. Parsear según spec: https://wiki.teltonika-networks.com/view/CODEC
        # 3. Extraer lat = record['lat'] / 10000000.0
        # 4. Extraer lng = record['lng'] / 10000000.0
        # 5. Extraer speed = record['speed'] (km/h directo en CODEC8)
        # 6. Retornar dict estándar

Archivo 7: gestion-frontend/src/web/empresa/flota/GestionGPS.vue
Vista Vue 3 completa (<script setup>, TailwindCSS). Debe incluir:
Estructura de la vista:

Header con título "Gestión GPS" y botón "Registrar dispositivo" (visible solo si tienePermiso('gps.gestionar'))
Dos tabs: "Dispositivos" y "Configuración servidor"

Tab Dispositivos:

Tabla con columnas: IMEI, Modelo, Vehículo asignado, Estado (badge verde/rojo), Acciones
Columna "Vehículo asignado": mostrar patente + modelo o chip "Sin asignar" en gris
Columna "Estado": badge verde "Activo" / rojo "Inactivo"
Acciones por fila (solo si tienePermiso('gps.gestionar')):

Botón "Asignar vehículo" (si no tiene vehículo)
Botón "Desasignar" (si tiene vehículo) — con ConfirmModal
Botón "Editar"
Botón "Eliminar" — con ConfirmModal


Estado vacío: mensaje "No hay dispositivos GPS registrados" con botón de alta

Modal alta/edición de dispositivo:

Campo IMEI (text, maxlength 20, pattern numérico)
Select modelo con todas las opciones
Toggle activo/inactivo
Botones Cancelar / Guardar

Modal asignar vehículo:

Select con vehículos de la empresa que NO tengan GPS asignado
Carga la lista desde GET /api/empresa/vehiculos/ filtrando los que ya tienen dispositivo_gps
Botones Cancelar / Asignar

Tab Configuración servidor:

Campos: IP del servidor, Puerto, Protocolo (radio: TCP/UDP)
Texto explicativo: "Esta IP y puerto deben configurarse en el dispositivo GPS físico. Durante el desarrollo con el emulador no es necesario."
Botón Guardar configuración

Comportamiento general:

onMounted: cargar dispositivos y configuración
Loading skeleton mientras carga
Cada operación exitosa dispara toast exito
Cada error dispara toast error con el mensaje del backend
Usar ConfirmModal en eliminar y desasignar


Archivo 8: gestion-frontend/src/web/empresa/flota/MapaFlota.vue
Componente Leaflet completo:
Inicialización:

Cargar Leaflet desde CDN unpkg (igual que MapaRuta.vue existente)
Centrar en Santiago: [-33.45, -70.65], zoom 12
Tiles: OpenStreetMap estándar

Carga inicial:

onMounted: llamar GET /api/empresa/gps/vehiculos/posicion/
Crear un marcador por vehículo con icono SVG diferenciado:

Azul: estado === 'movimiento'
Gris: estado === 'detenido'
Rojo: sin posición o timestamp > 5 minutos



Popup por marcador:
ABCD12 — Toyota Hilux
Velocidad: 48 km/h
Conductor: Juan Pérez
Última señal: hace 30 segundos
WebSocket tiempo real:
javascript// Conectar a ws://localhost:8000/ws/gps/{empresa_id}/?token={jwt}
// empresa_id y jwt se obtienen de sessionStorage igual que el resto del sistema
// Al recibir evento position_update:
//   - Si el marcador existe: mover con marker.setLatLng([lat, lng])
//   - Si no existe: crear marcador nuevo
//   - Actualizar popup con nueva velocidad y timestamp
Reconexión automática WebSocket:
javascript// Backoff exponencial: 1s → 2s → 4s → 8s → máx 30s
// Igual que services/websocket.js de la app conductores
let reconnectDelay = 1000
function conectarWS() {
  ws = new WebSocket(url)
  ws.onclose = () => {
    setTimeout(conectarWS, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, 30000)
  }
  ws.onopen = () => { reconnectDelay = 1000 }
}
onUnmounted: cerrar WebSocket limpiamente.

Archivos existentes que modificas — cambios mínimos y exactos
models.py — agregar al final del archivo:
pythonfrom .models_gps import DispositivoGPS, ConfiguracionGPS
consumers.py — agregar clase GPSConsumer al final:
Seguir exactamente el patrón de ConductorConsumer:

Ruta: ws/gps/<empresa_id>/
Validar JWT del query string
Validar que user.empresa_id == empresa_id de la URL — si no coincide: await self.close()
Grupo: gps_{empresa_id}
Manejar y reenviar evento position_update

routing.py — agregar al websocket_urlpatterns:
pythonpath('ws/gps/<int:empresa_id>/', GPSConsumer.as_asgi()),
urls.py — agregar al urlpatterns:
pythonpath('api/empresa/gps/dispositivos/', views_gps.DispositivosListView.as_view()),
path('api/empresa/gps/dispositivos/<int:id>/', views_gps.DispositivoDetailView.as_view()),
path('api/empresa/gps/dispositivos/<int:id>/asignar/', views_gps.AsignarVehiculoView.as_view()),
path('api/empresa/gps/dispositivos/<int:id>/desasignar/', views_gps.DesasignarVehiculoView.as_view()),
path('api/empresa/gps/posicion/', views_gps.PosicionView.as_view()),
path('api/empresa/gps/vehiculos/posicion/', views_gps.UltimasPosicionesView.as_view()),
path('api/empresa/gps/configuracion/', views_gps.ConfiguracionGPSView.as_view()),
EmpresaLayout.vue — agregar en el menú lateral:
vue<!-- Después del enlace de Flota, antes de Conductores -->
<router-link
  v-if="tieneModulo('gps')"
  to="/empresa/flota/gps"
  class="... igual que los otros enlaces del menú ..."
>
  <!-- Ícono satélite SVG o el que uses en el proyecto -->
  GPS
</router-link>
router/index.js — agregar rutas:
javascript{
  path: '/empresa/flota/gps',
  component: () => import('@/web/empresa/flota/GestionGPS.vue'),
  meta: { modulo: 'gps' }
},
{
  path: '/empresa/flota/mapa',
  component: () => import('@/web/empresa/flota/MapaFlota.vue'),
  meta: { modulo: 'gps' }
}

Restricciones absolutas — sin excepción

NO modificar Ubicacion, Asignacion, ni ningún modelo ya existente en models.py
NO instalar librerías nuevas — solo las que ya están en requirements.txt y package.json
NO crear migraciones en el output — solo el código Python. El desarrollador corre makemigrations y migrate manualmente
NO usar JsonResponse directo para errores — siempre error_response()
NO hacer fetch directo en Vue — siempre apiFetch
NO crear modales de confirmación nuevos — reutilizar ConfirmModal.vue
Cada método de vista Django debe tener el decorador @vista_segura
Toda operación de escritura debe llamar a registrar_log()
El GPSConsumer debe cerrar la conexión si el JWT es inválido o si empresa_id no coincide


Entrega esperada
Entregar cada archivo completo, listo para copiar a su ruta exacta. Sin placeholders, sin # TODO pendiente, sin // implementar. Código de producción funcional. En este orden:

models_gps.py
gps_providers/__init__.py
gps_providers/base.py
gps_providers/nmea_emulator.py
gps_providers/teltonika.py
views_gps.py
Modificación de consumers.py (solo el GPSConsumer nuevo)
Modificación de routing.py (solo la línea nueva)
Modificación de urls.py (solo las líneas nuevas)
Modificación de models.py (solo el import nuevo al final)
GestionGPS.vue
MapaFlota.vue
Modificación de EmpresaLayout.vue (solo el enlace nuevo)
Modificación de router/index.js (solo las rutas nuevas)