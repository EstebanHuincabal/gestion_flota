Vas a implementar el módulo de geolocalización en tiempo real para el panel web. Muestra la ubicación de todos los vehículos de la empresa en un mapa Leaflet con estado en tiempo real via WebSocket obteniendo la ubicacion del gps del telefono, agrega los permisos.

---

## CONTEXTO DEL SISTEMA

- El modelo Ubicacion ya existe: vehiculo FK, latitud, longitud, velocidad, combustible, timestamp
- El modelo Ruta ya existe con polyline JSONField y estados (pendiente/activo/finalizado)
- El modelo Vehiculo ya existe con patente, marca, modelo, activo
- El modelo Asignacion ya existe: conductor FK, vehiculo FK, activo
- Django Channels ya está configurado (WebSockets funcionando para notificaciones)
- Leaflet ya se usa en MapaRuta.vue — mismo patrón de carga dinámica
- apiFetch en src/utils/api.js — usar siempre
- WebSocket de notificaciones en consumers.py ya existe — agregar nuevo consumer

---

## PARTE 1 — BACKEND

### Lógica de estado del vehículo

Crear gestion_backend/g_de_flota/geo_helpers.py:

```python
from django.utils import timezone
from datetime import timedelta

UMBRAL_INACTIVO_MIN  = 5   # minutos sin señal → desconocido
UMBRAL_DETENIDO_KMH  = 3   # km/h por debajo = detenido
UMBRAL_MOVIMIENTO_KMH = 3  # km/h por encima = en movimiento

def calcular_estado_vehiculo(ultima_ubicacion, ruta_activa=None):
    """
    Retorna: 'en_ruta' | 'en_movimiento' | 'detenido' | 'sin_señal'
    Jerarquía: si tiene ruta activa Y está en movimiento → 'en_ruta'
    """
    if not ultima_ubicacion:
        return 'sin_señal'

    ahora    = timezone.now()
    antiguedad = (ahora - ultima_ubicacion.timestamp).total_seconds() / 60

    if antiguedad > UMBRAL_INACTIVO_MIN:
        return 'sin_señal'

    velocidad = ultima_ubicacion.velocidad or 0

    if ruta_activa and velocidad > UMBRAL_MOVIMIENTO_KMH:
        return 'en_ruta'
    if velocidad > UMBRAL_MOVIMIENTO_KMH:
        return 'en_movimiento'
    return 'detenido'


def get_resumen_flota(empresa):
    """Resumen de estados para los KPI cards."""
    from .models import Vehiculo, Ubicacion, Ruta

    vehiculos = Vehiculo.objects.filter(
        flota__empresa=empresa, activo=True
    ).prefetch_related('asignaciones', 'ubicaciones')

    resumen = {
        'en_ruta':       0,
        'en_movimiento': 0,
        'detenido':      0,
        'sin_señal':     0,
        'total':         0,
    }

    for v in vehiculos:
        ultima = v.ubicaciones.order_by('-timestamp').first()
        ruta   = Ruta.objects.filter(
            vehiculo=v, estado='activo'
        ).first()
        estado = calcular_estado_vehiculo(ultima, ruta)
        resumen[estado] += 1
        resumen['total'] += 1

    return resumen
```

### Endpoint REST inicial

GET /api/empresa/geolocalizacion/
Carga inicial del mapa — retorna todos los vehículos con su última ubicación conocida.
Solo rol USUARIO con empresa activa o SUPERADMIN con empresa_id param.

```python
class GeolocalizacionView(View):
    def get(self, request):
        from .models import Vehiculo, Ubicacion, Ruta, Asignacion
        from .geo_helpers import calcular_estado_vehiculo, get_resumen_flota
        from .models import descifrar

        empresa = request.user.empresa
        if not empresa:
            return JsonResponse({'error': 'Sin empresa.'}, status=400)

        vehiculos = Vehiculo.objects.filter(
            flota__empresa=empresa, activo=True
        ).select_related('flota')

        data = []
        for v in vehiculos:
            ultima = Ubicacion.objects.filter(
                vehiculo=v
            ).order_by('-timestamp').first()

            ruta_activa = Ruta.objects.filter(
                vehiculo=v, estado='activo'
            ).prefetch_related('paradas').first()

            asignacion = Asignacion.objects.filter(
                vehiculo=v, activo=True
            ).select_related('conductor').first()

            conductor_nombre = None
            if asignacion and asignacion.conductor:
                try:
                    conductor_nombre = descifrar(asignacion.conductor.nombre_cifrado)
                except Exception:
                    conductor_nombre = asignacion.conductor.email

            estado = calcular_estado_vehiculo(ultima, ruta_activa)

            data.append({
                'id':              v.id,
                'patente':         v.patente,
                'marca':           v.marca,
                'modelo':          v.modelo,
                'tipo_combustible': v.tipo_combustible,
                'flota':           v.flota.nombre,
                'estado':          estado,
                'conductor':       conductor_nombre,
                'ultima_ubicacion': {
                    'latitud':    ultima.latitud    if ultima else None,
                    'longitud':   ultima.longitud   if ultima else None,
                    'velocidad':  ultima.velocidad  if ultima else None,
                    'combustible': ultima.combustible if ultima else None,
                    'timestamp':  ultima.timestamp.isoformat() if ultima else None,
                } if ultima else None,
                'ruta_activa': {
                    'id':       ruta_activa.id,
                    'nombre':   ruta_activa.nombre,
                    'polyline': ruta_activa.polyline,
                    'paradas':  [
                        {
                            'tipo':     p.tipo,
                            'nombre':   p.nombre,
                            'latitud':  p.latitud,
                            'longitud': p.longitud,
                        }
                        for p in ruta_activa.paradas.order_by('orden')
                    ],
                } if ruta_activa else None,
            })

        return JsonResponse({
            'vehiculos': data,
            'resumen':   get_resumen_flota(empresa),
        })
```

### Endpoint para registrar ubicación desde la app del conductor

POST /api/conductor/ubicacion/
Recibe la posición actual del conductor y la guarda en Ubicacion.
También notifica via WebSocket a los admins de la empresa.

```python
class RegistrarUbicacionView(View):
    def post(self, request):
        if request.user.rol != 'CONDUCTOR':
            return JsonResponse({'error': 'Solo conductores.'}, status=403)

        body = json.loads(request.body)
        lat  = body.get('latitud')
        lng  = body.get('longitud')
        vel  = body.get('velocidad', 0)
        comb = body.get('combustible', 0)

        if lat is None or lng is None:
            return JsonResponse({'error': 'Coordenadas requeridas.'}, status=400)

        # Obtener vehículo asignado al conductor
        from .models import Asignacion
        asignacion = Asignacion.objects.filter(
            conductor=request.user, activo=True
        ).select_related('vehiculo__flota__empresa').first()

        if not asignacion:
            return JsonResponse({'error': 'Sin vehículo asignado.'}, status=400)

        vehiculo = asignacion.vehiculo
        empresa  = vehiculo.flota.empresa

        # Guardar ubicación
        ubicacion = Ubicacion.objects.create(
            vehiculo=vehiculo,
            latitud=lat,
            longitud=lng,
            velocidad=vel,
            combustible=comb,
        )

        # Calcular estado
        from .geo_helpers import calcular_estado_vehiculo
        ruta_activa = Ruta.objects.filter(vehiculo=vehiculo, estado='activo').first()
        estado      = calcular_estado_vehiculo(ubicacion, ruta_activa)

        # Notificar via WebSocket a admins de la empresa
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'geolocalizacion_{empresa.id}',
            {
                'type': 'ubicacion_update',
                'data': {
                    'vehiculo_id': vehiculo.id,
                    'patente':     vehiculo.patente,
                    'latitud':     lat,
                    'longitud':    lng,
                    'velocidad':   vel,
                    'combustible': comb,
                    'estado':      estado,
                    'timestamp':   ubicacion.timestamp.isoformat(),
                    'ruta_id':     ruta_activa.id if ruta_activa else None,
                }
            }
        )

        return JsonResponse({'ok': True, 'estado': estado})
```

### Management command: purgar_ubicaciones
Crear g_de_flota/management/commands/purgar_ubicaciones.py
Elimina ubicaciones de más de 30 días excepto las marcadas como es_punto_clave=True.
Cron diario: 0 3 * * * python manage.py purgar_ubicaciones

```python
def handle(self, *args, **kwargs):
    from django.utils import timezone
    from datetime import timedelta
    limite = timezone.now() - timedelta(days=30)
    eliminadas, _ = Ubicacion.objects.filter(
        timestamp__lt=limite
    ).delete()
    self.stdout.write(self.style.SUCCESS(f'{eliminadas} ubicaciones eliminadas.'))
```

### WebSocket Consumer: GeolocalizacionConsumer

Agregar en consumers.py:

```python
class GeolocalizacionConsumer(AsyncWebSocketConsumer):
    async def connect(self):
        # Verificar autenticación y rol
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        if user.rol not in ('USUARIO', 'SUPERADMIN'):
            await self.close()
            return

        empresa_id = (
            user.empresa.id
            if user.rol == 'USUARIO' and user.empresa
            else self.scope['url_route']['kwargs'].get('empresa_id')
        )
        if not empresa_id:
            await self.close()
            return

        self.group_name = f'geolocalizacion_{empresa_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def ubicacion_update(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'ubicacion_update',
            'data': event['data'],
        }))
```

Agregar en routing.py:
```python
re_path(r'ws/geolocalizacion/(?P<empresa_id>\d+)/$', GeolocalizacionConsumer.as_asgi()),
```

### URLs a agregar en urls.py

```python
path('api/empresa/geolocalizacion/',  GeolocalizacionView.as_view()),
path('api/conductor/ubicacion/',      RegistrarUbicacionView.as_view()),
```

---

## PARTE 2 — FRONTEND WEB

### Crear src/web/rutas/Geolocalizacion.vue

Vista completa del módulo de geolocalización en tiempo real.

#### Layout
Header: "Geolocalización en tiempo real"  [● En vivo]  [última actualiz: hace 30s]
KPI cards (4):
[En ruta N]  [En movimiento N]  [Detenidos N]  [Sin señal N]
Filtros: [Todos] [En ruta] [En movimiento] [Detenidos] [Sin señal]  🔍 Buscar patente
Panel de dos columnas:
┌──────────────────────────────┬────────────────────────────────┐
│  Lista de vehículos (scroll) │  Mapa Leaflet (flex: 1)        │
│                              │                                │
│  [PPU-4421] ● En ruta        │   [mapa con marcadores]        │
│  J. Muñoz · 62 km/h          │                                │
│  Ruta STG→VAL · 45 min       │                                │
│                              │                                │
│  [BBTF-12] ● En movimiento   │                                │
│  Sin conductor asignado      │                                │
│  65 km/h                     │                                │
│                              │                                │
│  [PPQ-9901] ● Detenido       │                                │
│  C. Rojas · 0 km/h           │                                │
│  Hace 4 min                  │                                │
│                              │                                │
│  [FGKL-44] ○ Sin señal       │                                │
│  A. Silva                    │                                │
│  Última señal: hace 12 min   │                                │
└──────────────────────────────┴────────────────────────────────┘

#### Lista de vehículos (columna izquierda)

Cada card:
[dot color estado]  PPU-4421 — Mercedes Actros
J. Muñoz  ·  62 km/h  ·  ⛽ 45%
● En ruta: STG → VAL
Última actualización: hace 30s

Colores del dot según estado:
- en_ruta: verde (#1D9E75) con animación pulse
- en_movimiento: azul (#378ADD) con animación pulse
- detenido: naranja (#EF9F27) estático
- sin_señal: gris (#9CA3AF) estático

Al hacer click en una card:
- Centrar el mapa en ese vehículo (flyTo con zoom 15)
- Abrir panel lateral de detalle del vehículo
- Resaltar su marcador en el mapa

Filtrar lista según tab activo y búsqueda.

#### Mapa Leaflet (columna derecha)

Cargar Leaflet dinámicamente si window.L no existe — mismo patrón que MapaRuta.vue.
Tile: OpenStreetMap.
Altura: 100% del viewport menos header (usar calc(100vh - 180px)).

**Marcadores por vehículo:**
SVG inline según estado:
```javascript
const COLORES_ESTADO = {
  en_ruta:       '#1D9E75',
  en_movimiento: '#378ADD',
  detenido:      '#EF9F27',
  sin_señal:     '#9CA3AF',
}

function crearIconoVehiculo(vehiculo, estado) {
  const color = COLORES_ESTADO[estado]
  const svg = `
    <svg width="36" height="44" viewBox="0 0 36 44" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 0C8.1 0 0 8.1 0 18c0 13.5 18 26 18 26S36 31.5 36 18C36 8.1 27.9 0 18 0z"
        fill="${color}" stroke="white" stroke-width="2"/>
      <text x="18" y="22" text-anchor="middle" fill="white"
        font-size="10" font-weight="bold" font-family="Arial">
        ${vehiculo.patente.slice(-4)}
      </text>
    </svg>`
  return L.divIcon({
    html:       svg,
    className:  '',
    iconSize:   [36, 44],
    iconAnchor: [18, 44],
    popupAnchor:[0, -44],
  })
}
```

**Popup del marcador al hacer click:**
PPU-4421 — Mercedes Actros
Estado: ● En ruta
Conductor: Juan Muñoz
Velocidad: 62 km/h
Combustible: 45%
Última señal: hace 30s
[Ver detalle →]

**Ruta dibujada si vehiculo.ruta_activa:**
- Polyline azul (weight 3, opacity 0.7, dashArray '8 4')
- Marcadores de origen (verde) y destino (rojo) en los extremos de la ruta
- La polyline se actualiza si el vehículo actualiza su ruta

**Trail de movimiento (últimas posiciones):**
Al recibir actualizaciones via WebSocket, dibujar una línea de trail (últimas 5 posiciones) en color más claro que el marcador, opacity 0.4.

```javascript
// Por vehículo, mantener cola de últimas 5 posiciones:
const trails = ref({})  // { vehiculo_id: [[lat,lng], ...] }

function agregarPosicionTrail(vehiculoId, lat, lng) {
  if (!trails.value[vehiculoId]) trails.value[vehiculoId] = []
  trails.value[vehiculoId].push([lat, lng])
  if (trails.value[vehiculoId].length > 5) {
    trails.value[vehiculoId].shift()
  }
}
```

**Animación de movimiento del marcador:**
Al recibir nueva posición via WebSocket, mover el marcador suavemente con interpolación:
```javascript
function animarMarcador(marker, nuevaLat, nuevaLng, duracionMs = 1000) {
  const posInicial = marker.getLatLng()
  const inicio     = Date.now()

  function step() {
    const t = Math.min((Date.now() - inicio) / duracionMs, 1)
    const lat = posInicial.lat + (nuevaLat - posInicial.lat) * t
    const lng = posInicial.lng + (nuevaLng - posInicial.lng) * t
    marker.setLatLng([lat, lng])
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
```

#### Panel lateral de detalle (al seleccionar vehículo)

Slide desde la derecha, 320px de ancho sobre el mapa:
[←]  PPU-4421
Mercedes Actros · Diésel
[● En ruta]
Conductor:    Juan Muñoz
Velocidad:    62 km/h
Combustible:  ████████░░ 45%
Señal:        hace 30s
Coordenadas:  -33.4489, -70.6693
─── Ruta activa ───────────────
STG → VAL #084
Origen:   Bodega Central
Destino:  Puerto Valparaíso
[Ver detalle de ruta →]
─── Historial reciente ────────
Hoy 08:30  Inicio de ruta
Hoy 09:15  En tránsito (62 km/h)
Hoy 09:47  Ahora
[Cerrar]

#### WebSocket en Geolocalizacion.vue

Conectar al cargar la vista, desconectar al desmontar:

```javascript
import { onMounted, onUnmounted, ref } from 'vue'

let ws = null
const conectado = ref(false)
const ultimaActualizacion = ref(null)

function conectarWebSocket(empresaId) {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocolo}://localhost:8000/ws/geolocalizacion/${empresaId}/`)

  ws.onopen = () => {
    conectado.value = true
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.tipo === 'ubicacion_update') {
      actualizarVehiculo(msg.data)
      ultimaActualizacion.value = new Date()
    }
  }

  ws.onclose = () => {
    conectado.value = false
    // Reconectar en 5 segundos
    setTimeout(() => conectarWebSocket(empresaId), 5000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

function actualizarVehiculo(data) {
  // Actualizar en la lista de vehículos
  const idx = vehiculos.value.findIndex(v => v.id === data.vehiculo_id)
  if (idx !== -1) {
    vehiculos.value[idx].ultima_ubicacion = {
      latitud:   data.latitud,
      longitud:  data.longitud,
      velocidad: data.velocidad,
      combustible: data.combustible,
      timestamp: data.timestamp,
    }
    vehiculos.value[idx].estado = data.estado

    // Actualizar marcador en el mapa
    actualizarMarcadorMapa(data)
    agregarPosicionTrail(data.vehiculo_id, data.latitud, data.longitud)
  }
}

onMounted(async () => {
  const data = await apiFetch('/api/empresa/geolocalizacion/')
  vehiculos.value = data.vehiculos
  resumen.value   = data.resumen

  inicializarMapa()
  vehiculos.value.forEach(v => {
    if (v.ultima_ubicacion) {
      agregarMarcadorMapa(v)
    }
    if (v.ruta_activa?.polyline?.length) {
      dibujarRuta(v)
    }
  })

  const usuario = JSON.parse(sessionStorage.getItem('usuario') || '{}')
  if (usuario.empresa_id) conectarWebSocket(usuario.empresa_id)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (mapaInstance) { mapaInstance.remove(); mapaInstance = null }
})
```

#### Indicador de conexión en tiempo real

Badge en el header:
- WebSocket conectado: `[● En vivo]` verde con pulse
- WebSocket desconectado: `[○ Reconectando...]` naranja
- Texto "Última actualización: hace Xs" que se actualiza cada segundo

```javascript
const tiempoDesdeActualizacion = ref('—')
let intervaloTiempo = null

onMounted(() => {
  intervaloTiempo = setInterval(() => {
    if (!ultimaActualizacion.value) return
    const seg = Math.floor((Date.now() - ultimaActualizacion.value) / 1000)
    tiempoDesdeActualizacion.value = seg < 60
      ? `hace ${seg}s`
      : `hace ${Math.floor(seg/60)}min`
  }, 1000)
})

onUnmounted(() => clearInterval(intervaloTiempo))
```

#### Alertas automáticas por estado

Al recibir una actualización via WebSocket que cambie el estado de un vehículo, mostrar toast:

```javascript
function verificarCambioEstado(vehiculoId, estadoNuevo) {
  const anterior = estadosAnteriores.value[vehiculoId]
  if (!anterior || anterior === estadoNuevo) {
    estadosAnteriores.value[vehiculoId] = estadoNuevo
    return
  }

  const v = vehiculos.value.find(v => v.id === vehiculoId)
  const patente = v?.patente || `Vehículo ${vehiculoId}`

  if (anterior === 'en_ruta' && estadoNuevo === 'detenido') {
    showToast(`${patente} se detuvo durante la ruta`, 'advertencia')
  }
  if (anterior !== 'sin_señal' && estadoNuevo === 'sin_señal') {
    showToast(`${patente} perdió señal GPS`, 'error')
  }
  if (anterior === 'sin_señal' && estadoNuevo !== 'sin_señal') {
    showToast(`${patente} recuperó señal GPS`, 'exito')
  }

  estadosAnteriores.value[vehiculoId] = estadoNuevo
}
```

---

## PARTE 3 — APP MÓVIL: ENVÍO DE UBICACIÓN

### Crear src/services/geolocalizacion.js en app_conductor/

Servicio que envía la posición del conductor al backend cada N segundos mientras hay una ruta activa.

```javascript
import { Geolocation } from '@capacitor/geolocation'
import { Network }     from '@capacitor/network'
import { apiFetch }    from './api.js'

let intervalo     = null
const INTERVALO_S = 30  // enviar cada 30 segundos

export async function iniciarEnvioUbicacion() {
  // Pedir permisos
  const permiso = await Geolocation.requestPermissions()
  if (permiso.location !== 'granted') return false

  intervalo = setInterval(async () => {
    const { connected } = await Network.getStatus()
    if (!connected) return  // no enviar si sin conexión

    try {
      const pos = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 10000,
      })

      await apiFetch('/api/conductor/ubicacion/', {
        method: 'POST',
        body: JSON.stringify({
          latitud:    pos.coords.latitude,
          longitud:   pos.coords.longitude,
          velocidad:  (pos.coords.speed || 0) * 3.6,  // m/s → km/h
          combustible: 0,  // si no hay sensor, enviar 0
        }),
      })
    } catch { /* fail silent — no interrumpir la app */ }

  }, INTERVALO_S * 1000)

  return true
}

export function detenerEnvioUbicacion() {
  if (intervalo) {
    clearInterval(intervalo)
    intervalo = null
  }
}
```

### Integrar en DetalleRuta.vue (app_conductor)

Al iniciar una ruta → llamar iniciarEnvioUbicacion()
Al finalizar o cancelar una ruta → llamar detenerEnvioUbicacion()

```javascript
import { iniciarEnvioUbicacion, detenerEnvioUbicacion } from '@/services/geolocalizacion.js'

async function confirmarIniciarRuta() {
  await rutasStore.iniciarRuta(ruta.value.id, { km_inicio: kmInicio.value })
  await iniciarEnvioUbicacion()
  // ...resto del flujo
}

async function confirmarFinalizarRuta() {
  detenerEnvioUbicacion()
  await rutasStore.finalizarRuta(ruta.value.id, datosFinalizacion.value)
  // ...resto del flujo
}

onUnmounted(() => {
  // Seguridad: detener envío si el componente se desmonta
  detenerEnvioUbicacion()
})
```

---

## PARTE 4 — NAVEGACIÓN

Agregar en el sidebar del USUARIO (buscar en contexto.md el archivo de navegación):
Ítem: Geolocalización
Ícono: ti-map-pin
Ruta: /empresa/geolocalizacion
Badge: conteo de vehículos en ruta (número verde)

Agregar en router/index.js:
```javascript
{
  path: '/empresa/geolocalizacion',
  component: () => import('@/web/rutas/Geolocalizacion.vue'),
  meta: { requiresAuth: true, roles: ['USUARIO'] }
}
```

---

## CONVENCIONES

- Composition API <script setup> siempre
- apiFetch siempre, nunca fetch directo
- Leaflet cargado dinámicamente si window.L no existe
- onUnmounted: destruir mapa y cerrar WebSocket — sin memory leaks
- WebSocket reconecta automáticamente cada 5s si se desconecta
- showToast con window.dispatchEvent CustomEvent 'app-toast' (patrón del sistema)
- Montos y velocidades con formato apropiado: km/h sin decimales, % sin decimales
- Fail-silent en el envío de ubicación desde la app — nunca interrumpir al conductor
- El intervalo de geolocalización solo corre cuando hay ruta activa
- Textos en español es-CL
- Sin modelos nuevos — usar Ubicacion, Ruta, Vehiculo, Asignacion existentes

---

## ARCHIVOS A ENTREGAR

Backend:
1. geo_helpers.py — completo
2. views_geo_patch.py — GeolocalizacionView y RegistrarUbicacionView con indicación de dónde van en views.py
3. consumers_geo_patch.py — GeolocalizacionConsumer con indicación de dónde va en consumers.py
4. routing_patch.py — la URL de WebSocket nueva
5. urls_patch.py — las 2 rutas REST nuevas
6. management/commands/purgar_ubicaciones.py — completo

Frontend web:
7. src/web/rutas/Geolocalizacion.vue — completo
8. router_patch.js — la ruta nueva
9. nav_patch.md — ítem a agregar en el sidebar

App móvil:
10. app_conductor/src/services/geolocalizacion.js — completo
11. detalleruta_geo_patch.vue — solo los fragmentos de iniciar/detener a agregar en DetalleRuta.vue

Sin "# resto igual".
