Vas a implementar la pantalla "Detalle de Ruta" de la app móvil de conductores. El login y ListaRutas ya están implementados.

---

## CONTEXTO

- Stack: Vue 3 + Capacitor + TailwindCSS 4 + Pinia
- apiFetch en src/services/api.js (ya existe)
- Store auth en src/stores/auth.js (ya existe)
- Store rutas en src/stores/rutas.js (ya existe, con iniciarRuta y finalizarRuta)
- sync.js y db.js ya existen
- Ruta del router: /rutas/:id → DetalleRuta.vue
- BottomNav.vue ya existe
- formatCLP, formatDuracion, formatFechaRuta en src/utils/formato.js ya existen

---

## ENDPOINT

GET /api/conductor/rutas/:id/
Retorna el objeto ruta completo igual al listado pero con paradas detalladas y peajes:
```json
{
  "id": 1,
  "nombre": "STG → VAL #084",
  "tipo": "carga",
  "estado": "pendiente",
  "origen": "Bodega Central, Pudahuel",
  "destino": "Puerto Valparaíso, Muelle 5",
  "fecha_programada": "2025-05-20T08:30:00",
  "fecha_inicio": null,
  "fecha_fin": null,
  "km_inicio": null,
  "km_fin": null,
  "distancia_km": 142.5,
  "duracion_min": 165,
  "costo_combustible_est": 71000,
  "costo_peajes_est": 14400,
  "costo_total_est": 85400,
  "costo_combustible_real": null,
  "costo_peajes_real": null,
  "costo_total_real": null,
  "polyline": [[-33.4489, -70.6693], [-33.4234, -71.0123], [-33.0456, -71.6234]],
  "paradas": [
    { "id": 1, "orden": 1, "tipo": "origen",  "nombre": "Bodega Central", "direccion": "Av. Industrial 1234", "latitud": -33.4489, "longitud": -70.6693, "notas": "" },
    { "id": 2, "orden": 2, "tipo": "parada",  "nombre": "Planta Lo Prado","direccion": "Ruta 68 km 8",      "latitud": -33.4234, "longitud": -71.0123, "notas": "Entrega parcial" },
    { "id": 3, "orden": 3, "tipo": "destino", "nombre": "Puerto Valparaíso","direccion": "Av. Errázuriz 25", "latitud": -33.0456, "longitud": -71.6234, "notas": "" }
  ],
  "peajes_ruta": [
    { "id": 1, "nombre": "Zapata",     "ruta": "Ruta 68", "tarifa": 2700, "latitud": -33.4456, "longitud": -70.9789 },
    { "id": 2, "nombre": "Lo Prado",   "ruta": "Ruta 68", "tarifa": 4800, "latitud": -33.4012, "longitud": -71.1234 },
    { "id": 3, "nombre": "Casablanca", "ruta": "Ruta 68", "tarifa": 2700, "latitud": -33.3234, "longitud": -71.4123 }
  ],
  "notas": "",
  "vehiculo": { "id": 3, "patente": "PPU-4421", "marca": "Mercedes", "modelo": "Actros", "tipo_combustible": "diesel" },
  "conductor": { "id": 5, "nombre": "Juan Muñoz" }
}
```

---

## VISTA: src/views/Rutas/DetalleRuta.vue

### Estructura general
- Header con botón atrás + título de la ruta + badge de estado
- Contenido scrolleable
- Botón de acción fijo al fondo (según estado)
- BottomNav debajo del botón de acción

### Header
[←]  STG → VAL #084          [• En curso]
- Botón atrás: router.back()
- Badge de estado con colores: pendiente=azul, activo=verde animado, finalizado=gris, cancelado=rojo

### Tabs de contenido
Tres tabs: Ruta | Costos | Detalles
Tabs en pills horizontales, desplazables si no caben.
El tab activo usa el color de acento.

---

## TAB 1 — RUTA

### Mapa (componente MapaRuta)
Altura fija 220px.
Cargar Leaflet dinámicamente desde unpkg si window.L no existe.
Mostrar:
- Polyline azul (weight 4, opacity 0.8) con los puntos de la ruta
- Marcadores por tipo:
  - origen: verde (#1D9E75), ícono pin SVG inline
  - parada: azul (#378ADD)
  - destino: rojo (#E24B4A)
  - peaje: naranja (#EF9F27), ícono más pequeño
- fitBounds a todos los puntos con padding [20,20]
- Tile layer OpenStreetMap

Para modo offline: intentar cargar tiles desde cache del filesystem.
Si Leaflet no carga (sin conexión) mostrar placeholder gris con mensaje "Mapa no disponible sin conexión".

### Lista de paradas
Debajo del mapa, conectadas con línea vertical punteada:
●  Bodega Central                    Origen
Av. Industrial 1234, Pudahuel
Salida programada: Hoy 08:30
┆
●  Planta Lo Prado                   Parada 1
Ruta 68 km 8
Entrega parcial
┆
◆  Zapata                            Peaje
Ruta 68 · $2.700
┆
●  Puerto Valparaíso                 Destino
Av. Errázuriz 25

Línea vertical punteada entre paradas (border-left dashed en el contenedor).
Puntos de colores según tipo (mismo esquema que el mapa).
Peajes aparecen entre paradas según su orden geográfico en la ruta.

### Datos de la ruta
Debajo de las paradas, fila de chips informativos:
[🗺 142 km]  [⏱ 2h 45min]  [📅 Hoy 08:30]

---

## TAB 2 — COSTOS

### Estimados vs reales
Si la ruta no está finalizada: solo columna de estimados.
Si está finalizada: dos columnas (Estimado | Real) con diferencia coloreada.
                Estimado      Real      Diferencia
Combustible         $71.000      $68.500      -$2.500 ✓
Peajes              $14.400      $14.400         $0   =
─────────────────────────────────────────────────────
Total               $85.400      $82.900      -$2.500 ✓

Verde si el real fue menor al estimado.
Rojo si el real fue mayor.
Gris si son iguales.

### Desglose de peajes
Lista de peajes detectados en la ruta:
Zapata         Ruta 68      $2.700
Lo Prado       Ruta 68      $4.800
Casablanca     Ruta 68      $2.700
────────────────────────────────
Total peajes               $10.200

### Datos de combustible
Distancia:        142 km
Consumo est.:     12 L/100km
Litros est.:      17.0 L
Precio/litro:     $1.250 (diésel)
Total est.:       $71.000

---

## TAB 3 — DETALLES

Información completa de la ruta:
- Tipo: badge Carga / Personas
- Vehículo: patente + marca + modelo + combustible
- Conductor: nombre
- Fecha programada
- Fecha inicio real (si aplica)
- Fecha fin real (si aplica)
- Km inicio / km fin / km recorridos reales (si aplica)
- Notas (si hay)

---

## BOTÓN DE ACCIÓN FIJO

Según el estado de la ruta, mostrar un botón diferente fijo al fondo
(sobre el BottomNav, con padding-bottom adecuado):

### Estado: pendiente
[▶  Iniciar ruta]   ← verde, grande
Al tocar → abre ModalIniciarRuta

### Estado: activo
[✓  Finalizar ruta]   ← morado/acento, grande
Al tocar → abre ModalFinalizarRuta

### Estado: finalizado o cancelado
Sin botón de acción. Solo mostrar un banner informativo:
Estado: Finalizado · 19/05/2025 14:32

---

## MODAL: ModalIniciarRuta (componente interno)

Sheet modal que sube desde abajo (bottom sheet, no modal centrado).
Altura: 40% de la pantalla.
──────────────────────
▬▬▬           ← handle para arrastrar
Iniciar ruta
Odómetro actual
[    142.580    km]   ← input numérico, pre-rellena con vehiculo.km_actuales
[Cancelar]  [Iniciar ▶]
──────────────────────

Al confirmar:
1. Llamar rutasStore.iniciarRuta(ruta.id, { km_inicio: kmInicio })
2. Si online: POST directo → mostrar éxito → actualizar estado local
3. Si offline: encolar acción → mostrar "Se registrará cuando haya conexión" → actualizar estado local optimistamente
4. Cerrar modal y actualizar vista

---

## MODAL: ModalFinalizarRuta (componente interno)

Sheet modal más alto: 65% de la pantalla.
────────────────────────
▬▬▬
Finalizar ruta
Odómetro final
[    143.000    km]   ← input numérico obligatorio
Costo combustible real
[     68.500    CLP]  ← pre-rellena con costo_combustible_est, editable
Costo peajes real
[     14.400    CLP]  ← pre-rellena con costo_peajes_est, editable
Notas (opcional)
[                  ]
⚠ Se crearán gastos operativos automáticamente
[Cancelar]   [Finalizar ✓]
────────────────────────

Validaciones:
- km_fin > km_inicio (si km_inicio existe)
- km_fin obligatorio
- costos >= 0

Al confirmar:
1. Llamar rutasStore.finalizarRuta(ruta.id, datos)
2. Mismo comportamiento online/offline que iniciar
3. Mostrar toast de éxito: "Ruta finalizada. Se registraron los gastos."
4. router.push('/rutas')

---

## COMPONENTE: src/components/MapaRuta.vue (crear)

Props:
```javascript
{
  paradas:  Array,   // [{tipo, nombre, latitud, longitud}]
  polyline: Array,   // [[lat, lng], ...]
  peajes:   Array,   // [{nombre, ruta, tarifa, latitud, longitud}]
  altura:   String,  // default '220px'
}
```

Cargar Leaflet desde unpkg.com con script dinámico.
Si window.L ya existe no cargarlo de nuevo.
onUnmounted: limpiar instancia del mapa.
watch profundo en paradas y polyline para re-renderizar.

Íconos SVG inline por tipo (sin dependencias externas):
```javascript
function crearIcono(tipo) {
  const colores = {
    origen:  '#1D9E75',
    parada:  '#378ADD',
    destino: '#E24B4A',
    peaje:   '#EF9F27',
  }
  const color = colores[tipo] || '#378ADD'
  const size  = tipo === 'peaje' ? 20 : 26
  const svg = `<svg width="${size}" height="${size*1.3}" viewBox="0 0 24 32"
    xmlns="http://www.w3.org/2000/svg">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20S24 21 24 12C24 5.4 18.6 0 12 0z"
      fill="${color}"/>
    <circle cx="12" cy="12" r="5" fill="white"/>
  </svg>`
  return L.divIcon({
    html: svg, className: '',
    iconSize: [size, size*1.3],
    iconAnchor: [size/2, size*1.3],
    popupAnchor: [0, -size*1.3],
  })
}
```

---

## ANIMACIONES Y UX

Bottom sheet modal:
```css
.bottom-sheet {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  border-radius: 20px 20px 0 0;
  background: white;
  transform: translateY(100%);
  transition: transform 0.3s ease;
}
.bottom-sheet.visible {
  transform: translateY(0);
}
```

Overlay oscuro detrás del modal con transition de opacity.
Al tocar el overlay → cerrar modal.
Handle drag: al arrastrar el handle hacia abajo cierra el modal.

Tab activo: transición suave con underline animado usando transition-all.

Skeleton loader mientras carga el detalle:
- Placeholder gris del mapa (220px, border-radius 12px)
- 3 líneas grises animadas para las paradas

---

## MANEJO DE ERRORES

- Si el id de la ruta no existe → mostrar "Ruta no encontrada" con botón volver
- Si falla la carga → mostrar "Error al cargar la ruta" con botón reintentar
- Si no hay conexión y no hay cache → mostrar "Sin conexión y sin datos guardados"
- Si OSRM no cargó el polyline → mostrar mapa solo con marcadores (sin línea de ruta)

---

## CONVENCIONES

- Composition API <script setup> siempre
- Nunca fetch directo — siempre apiFetch
- Nunca localStorage — siempre @capacitor/preferences o SQLite
- Textos en español
- Touch targets mínimo 44px
- Bottom sheets con safe-area para iPhone X+:
  padding-bottom: calc(16px + env(safe-area-inset-bottom))
- El handle del bottom sheet debe ser arrastrable con touch events
- Montos siempre con formatCLP()
- Duraciones siempre con formatDuracion()

---

## ARCHIVOS A ENTREGAR

1. src/views/Rutas/DetalleRuta.vue — completo
2. src/components/MapaRuta.vue — completo

Sin "// resto igual".