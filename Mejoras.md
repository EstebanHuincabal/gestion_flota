## STACK
- Mapas: Leaflet.js (CDN, gratuito)
- Ruteo: OSRM Demo Server (gratuito, sin API key)
- Peajes: tabla propia en DB con datos MOP (sin API externa)
- Combustible: cálculo local con consumo del vehículo

---

## MODELOS NUEVOS

### Peaje
nombre, ruta, autopista, latitud, longitud, categoria (liviano/camion2/camion3/bus/moto), tarifa_normal, tarifa_punta (nullable), activo, updated_at.
unique_together: (nombre, ruta, categoria)

### ConfiguracionRuta
OneToOne con Empresa. Campos: precio_bencina (default 1380), precio_diesel (default 1250), radio_deteccion_peaje en metros (default 500).
Método de clase: get_for_empresa(empresa) que hace get_or_create.

### Ruta
empresa FK, tipo (carga/personas), nombre, descripcion, estado (borrador/pendiente/activo/finalizado/cancelado), conductor FK nullable, vehiculo FK nullable, fecha_programada, fecha_inicio, fecha_fin, km_inicio, km_fin, distancia_km, duracion_min, costo_combustible_est, costo_peajes_est, costo_total_est, costo_combustible_real, costo_peajes_real, costo_total_real, polyline JSONField (lista de [lat,lng]), notas, created_at, updated_at.
@property km_reales: retorna km_fin - km_inicio si ambos existen.

### Parada
ruta FK, tipo (origen/parada/destino), orden, nombre, direccion, latitud, longitud, notas, hora_estimada nullable.
ordering: ['orden']

### PeajeRuta
ruta FK, peaje FK, tarifa.
unique_together: (ruta, peaje)

### Modificar Vehiculo
Agregar: consumo_l_100km = DecimalField(max_digits=5, decimal_places=2, default=10.0)

---

## MANAGEMENT COMMAND: seed_peajes

Crear g_de_flota/management/commands/seed_peajes.py

Para cada peaje del listado, crear una entrada por cada categoría aplicando estos multiplicadores sobre la tarifa de liviano: moto ×0.5, camion2 ×2.0, camion3 ×3.0, bus ×1.8.

Peajes a incluir (nombre, ruta, lat, lng, tarifa_liviano_normal, tarifa_punta):

Ruta 5 Norte:
- Lampa Troncal, -33.2847, -70.9142, 2917, None
- Las Vegas Troncal, -32.8234, -71.0123, 2917, None
- Pichidangui Troncal, -32.1456, -71.5234, 4376, None
- Los Vilos Troncal, -31.9098, -71.5012, 4050, None
- Socos Troncal, -30.7234, -71.4567, 4050, None
- Serena Troncal, -29.9456, -71.2345, 4050, None

Ruta 5 Sur:
- Río Maipo Troncal, -33.6789, -70.8901, 1320, None
- Angostura Troncal, -33.8901, -70.8456, 3100, None
- Talca Troncal, -35.4234, -71.6234, 3100, None
- Chillán Troncal, -36.6234, -72.1012, 3500, None
- Collipulli Troncal, -37.9456, -72.4345, 3500, None
- Temuco Troncal, -38.7345, -72.5901, 3500, None
- Osorno Troncal, -40.5678, -73.1234, 3500, None

Ruta 68 (Santiago–Valparaíso):
- Zapata, -33.4456, -70.9789, 2700, 4100
- Lo Prado, -33.4012, -71.1234, 2700, 4100
- Casablanca, -33.3234, -71.4123, 2700, 4100

Ruta 78 (free flow):
- Melipilla A, -33.6890, -71.2134, 3300, None
- Melipilla B, -33.7234, -71.4012, 5940, None

Ruta 60 CH:
- Quillota Troncal, -32.8789, -71.2345, 5000, 7000

Ruta 57 (Los Andes):
- Chacabuco, -33.0234, -70.6789, 2700, None
- Los Andes, -32.8345, -70.5901, 2700, None

---

## MOTOR DE CÁLCULO: ruta_calculator.py

Crear g_de_flota/ruta_calculator.py con estas funciones:

calcular_ruta_osrm(paradas):
- Llama a https://router.project-osrm.org/route/v1/driving/{coords}
- params: overview=full, geometries=geojson
- Retorna {distancia_km, duracion_min, polyline [[lat,lng],...]}
- Si falla retorna None

haversine_km(lat1, lng1, lat2, lng2):
- Distancia en km entre dos coordenadas usando fórmula de Haversine

detectar_peajes_en_ruta(polyline, categoria='liviano', radio_km=0.5):
- Para cada Peaje activo de la categoría, verificar si algún punto de la polyline está a ≤ radio_km
- Retorna lista de objetos Peaje sin duplicados

calcular_costos(distancia_km, vehiculo, peajes, config_ruta, es_punta=False):
- combustible = (distancia_km/100) × consumo_l_100km × precio_litro
- precio_litro: config_ruta.precio_diesel si vehiculo.tipo_combustible=='diesel', sino precio_bencina
- peajes_total = suma de tarifa_punta (si es_punta y existe) o tarifa_normal por cada peaje
- Retorna {combustible, peajes_total, total, desglose_peajes, litros_estimados}

---

## VISTAS (en views.py)

### GET /api/empresa/rutas/
Parámetros opcionales: estado, tipo, conductor_id, vehiculo_id, fecha_desde, fecha_hasta.
Retorna lista de rutas + resumen {total, activas, pendientes, finalizadas, canceladas, km_mes, costo_est_mes}.

### POST /api/empresa/rutas/
Body: tipo, nombre, descripcion, conductor_id, vehiculo_id, fecha_programada, notas, paradas [{tipo, orden, nombre, direccion, lat, lng, notas}], es_punta.
Al crear: validar 1 origen y 1 destino → llamar calcular_ruta_osrm → detectar_peajes_en_ruta → calcular_costos → guardar Ruta + Parada + PeajeRuta.
Si OSRM falla: guardar sin datos de distancia, incluir aviso en respuesta.
registrar_log acción 'ruta_creada'.

### GET /api/empresa/rutas/:id/
Retorna ruta completa con paradas, peajes, conductor, vehículo y costos.

### PUT /api/empresa/rutas/:id/
Permite editar: nombre, descripcion, conductor_id, vehiculo_id, fecha_programada, notas, paradas.
Si cambian paradas: recalcular ruta OSRM, peajes y costos.

### POST /api/empresa/rutas/:id/iniciar/
Body: {km_inicio}. Estado pendiente → activo. Registra fecha_inicio=now(). registrar_log.

### POST /api/empresa/rutas/:id/finalizar/
Body: {km_fin, costo_combustible_real, costo_peajes_real, notas}.
Estado activo → finalizado. Registra fecha_fin=now(). Calcula costo_total_real.
Crea GastoOperativo automáticamente:
- uno con categoria='combustible', monto=costo_combustible_real, descripcion=f"Combustible ruta {ruta.nombre}"
- si costo_peajes_real > 0: otro con categoria='peaje'
Actualiza vehiculo.km_actuales = km_fin.
registrar_log acción 'ruta_finalizada'.

### POST /api/empresa/rutas/:id/cancelar/
Body: {motivo}. Solo desde estado pendiente o activo. registrar_log.

### POST /api/empresa/rutas/calcular/
Igual que POST /rutas/ pero sin guardar. Retorna {distancia_km, duracion_min, costos, peajes_detectados, polyline}.

### GET /api/empresa/rutas/peajes/
Lista todos los peajes activos (para capa del mapa).

### GET/PUT /api/empresa/rutas/configuracion/
GET retorna ConfiguracionRuta de la empresa.
PUT actualiza precio_bencina, precio_diesel, radio_deteccion_peaje.

---

## URLS

```python
# Rutas específicas ANTES de las rutas con :id
path('api/empresa/rutas/calcular/',                RouteCalcularView.as_view()),
path('api/empresa/rutas/peajes/',                  PeajesListView.as_view()),
path('api/empresa/rutas/configuracion/',           RutaConfigView.as_view()),
path('api/empresa/rutas/',                         RutasListView.as_view()),
path('api/empresa/rutas/<int:ruta_id>/',           RutaDetailView.as_view()),
path('api/empresa/rutas/<int:ruta_id>/iniciar/',   RutaIniciarView.as_view()),
path('api/empresa/rutas/<int:ruta_id>/finalizar/', RutaFinalizarView.as_view()),
path('api/empresa/rutas/<int:ruta_id>/cancelar/',  RutaCancelarView.as_view()),
```

---

## COMPONENTE MapaRuta.vue

Crear src/web/rutas/MapaRuta.vue.
Props: paradas [{tipo, nombre, latitud, longitud}], polyline [[lat,lng],...], peajes [{nombre, latitud, longitud, tarifa}], mapId (string).

Cargar Leaflet dinámicamente desde unpkg.com si window.L no existe (CSS + JS).
Usar OpenStreetMap como tile layer.
Íconos SVG inline por tipo: origen=verde (#1D9E75), parada=azul (#378ADD), destino=rojo (#E24B4A), peaje=naranja (#EF9F27).
Dibujar polyline en azul (weight 4) si existe.
fitBounds a todos los puntos con padding [24,24].
Vista por defecto si no hay puntos: Santiago [-33.4489, -70.6693] zoom 7.
watch profundo en paradas/polyline/peajes para re-renderizar.
onUnmounted: limpiar instancia del mapa.

---

## VISTA Rutas.vue

Crear src/web/rutas/Rutas.vue.

Header: título "Rutas y trabajos" + botón "Nueva ruta".
Tabs: Todas | Activas | Pendientes | Finalizadas.
KPI cards: Rutas activas · Pendientes hoy · Km este mes · Costo estimado mes.

Tabla con columnas: Nombre, Tipo (badge), Origen→Destino, Conductor, Vehículo, Fecha, Km, Costo est., Estado (badge), Acciones.
Badges de estado: activo=verde con animate-pulse, pendiente=azul, finalizado=gris, cancelado=rojo, borrador=amarillo.
Acciones por estado: pendiente→[Iniciar, Editar, Ver, Cancelar] | activo→[Finalizar, Ver] | resto→[Ver].
Click en fila: abre panel lateral con detalle y mapa.

Panel lateral (detalle de ruta seleccionada):
Tabs: Detalle | Mapa | Costos.
Tab Mapa: MapaRuta.vue a 400px altura con polyline, paradas y peajes detectados. Toggle para mostrar/ocultar peajes.
Tab Costos: estimado vs real si está finalizada. Desglose combustible + peajes + total.

Modal crear/editar en 3 pasos:

Paso 1 — Datos generales:
tipo (radio Carga/Personas), nombre, conductor (select), vehículo (select, muestra combustible y consumo), fecha_programada, notas.

Paso 2 — Paradas:
Origen (fijo arriba) y Destino (fijo abajo). Botón "Agregar parada intermedia".
Cada parada: input con búsqueda Nominatim (debounce 500ms), guarda lat/lng al seleccionar.
Geocodificación: fetch a https://nominatim.openstreetmap.org/search?format=json&q={texto}&countrycodes=cl&limit=5

Paso 3 — Calcular y confirmar:
Al llegar: POST /api/empresa/rutas/calcular/ automáticamente.
Mostrar: mini mapa MapaRuta (250px), distancia, duración, card de costos (combustible + desglose peajes + total), toggle horario punta.
Si OSRM falla: aviso amarillo, permitir crear igual.
Botón "Crear ruta" → POST /api/empresa/rutas/.

Modal iniciar: campo km_inicio (pre-rellena con vehiculo.km_actuales).
Modal finalizar: km_fin, costo_combustible_real (pre-rellena con estimado), costo_peajes_real, notas. Aviso: "Se crearán gastos operativos automáticamente."
Modal cancelar: campo motivo.

Configuración de precios: botón "Configurar precios" abre panel con precio_bencina, precio_diesel → PUT /api/empresa/rutas/configuracion/.

---

## NAVEGACIÓN

Sidebar USUARIO: Ítem "Rutas y trabajos" · ícono ti-route · ruta /empresa/rutas.
router/index.js: { path: '/empresa/rutas', component: () => import('@/web/rutas/Rutas.vue'), meta: { requiresAuth: true, roles: ['USUARIO'] } }

---

## CONVENCIONES
- Montos CLP formato $X.XXX
- OSRM y Nominatim pueden fallar — siempre fail-graceful
- Nominatim: debounce 500ms obligatorio (rate limit)
- apiFetch siempre, excepto Nominatim y carga de Leaflet
- registrar_log en todas las acciones críticas
- Al finalizar ruta: actualizar vehiculo.km_actuales = km_fin
- Composition API <script setup>

---

## ARCHIVOS A ENTREGAR
1. models_patch.py — 5 modelos nuevos + campo consumo_l_100km en Vehiculo
2. ruta_calculator.py — módulo de cálculo completo
3. views_rutas_patch.py — 8 vistas con indicación de dónde van en views.py
4. urls_patch.py — 8 rutas
5. seed_peajes.py — management command completo
6. Rutas.vue — vista principal completa
7. MapaRuta.vue — componente de mapa completo
8. router_patch.js + nav_patch.md
9. MIGRACION.md — makemigrations → migrate → seed_peajes → verificar