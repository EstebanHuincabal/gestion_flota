Vas a mejorar el módulo de rutas existente en gestion-frontend/src/web/rutas/. NO crear modelos nuevos — todo usa los modelos existentes (Ruta, Parada, Vehiculo, ConfiguracionRuta).

---

## LO QUE DEBES IMPLEMENTAR

Tres mejoras al módulo de rutas existente en Rutas.vue y MapaRuta.vue:
1. Selector de ubicación con mapa interactivo al crear/editar paradas
2. Cálculo y display de gasto estimado de combustible
3. Modal de carga masiva de rutas por CSV/Excel

---

## MEJORA 1 — SELECTOR DE UBICACIÓN CON MAPA

### Componente nuevo: src/web/rutas/SelectorUbicacion.vue

Reemplaza los inputs de texto de origen/destino/paradas en el modal de creación de ruta.
Permite tres formas de ingresar una ubicación:
- Búsqueda por texto (Nominatim)
- Click en el mapa
- Ingreso manual de coordenadas

### Layout del componente
┌─────────────────────────────────────────┐
│  [🔍 Buscar dirección...]    [lat, lng] │  ← tab activo resaltado
│─────────────────────────────────────────│
│                                         │
│         MAPA LEAFLET (300px)            │
│   [marcador arrastrable en el centro]   │
│                                         │
│─────────────────────────────────────────│
│  📍 Av. Industrial 1234, Pudahuel       │  ← dirección detectada
│     -33.4489, -70.6693                  │
└─────────────────────────────────────────┘

### Props
```javascript
defineProps({
  modelValue: {
    type: Object,
    default: () => ({ nombre: '', latitud: null, longitud: null })
  },
  placeholder: { type: String, default: 'Buscar dirección...' },
  label:        { type: String, default: 'Ubicación' },
})
defineEmits(['update:modelValue'])
```

### Tabs del selector
**Tab "Buscar":**
- Input de texto con debounce 500ms
- Llama a: `https://nominatim.openstreetmap.org/search?format=json&q={texto}&countrycodes=cl&limit=5&accept-language=es`
- Muestra lista de resultados debajo del input
- Al seleccionar un resultado: centrar mapa, colocar marcador, emitir update

**Tab "Coordenadas":**
- Dos inputs numéricos: Latitud y Longitud
- Validar rango Chile: lat entre -56 y -17, lng entre -76 y -65
- Mensaje de error si están fuera de rango: "Las coordenadas no corresponden a Chile"
- Al ingresar coordenadas válidas: centrar mapa y colocar marcador

**Mapa interactivo:**
- Leaflet cargado dinámicamente (mismo patrón que MapaRuta.vue existente)
- Tile: OpenStreetMap
- Marcador arrastrable (draggable: true)
- Al arrastrar el marcador: hacer geocodificación inversa con Nominatim
  `https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&accept-language=es`
  y actualizar el nombre de la ubicación
- Al hacer click en el mapa: mover el marcador a esa posición y geocodificar
- Zoom inicial: 12 si hay coordenadas, 6 centrado en Chile (-33.4, -70.6) si no

**Geocodificación inversa:**
```javascript
async function geocodificarInverso(lat, lng) {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=es`
    const res  = await fetch(url)
    const data = await res.json()
    return data.display_name?.split(',').slice(0, 3).join(',').trim() || `${lat}, ${lng}`
  } catch {
    return `${lat.toFixed(6)}, ${lng.toFixed(6)}`
  }
}
```

**Emitir al padre:**
```javascript
// Cada vez que cambia la ubicación (búsqueda, drag, coordenadas):
emit('update:modelValue', {
  nombre:   nombreDireccion,
  latitud:  lat,
  longitud: lng,
})
```

### Integración en el modal de creación de ruta (Rutas.vue)

En el modal de crear/editar ruta, Paso 2 (Paradas), reemplazar los inputs de texto actuales por SelectorUbicacion:

```vue
<!-- Para origen -->
<SelectorUbicacion
  v-model="parada.ubicacion"
  label="Punto de origen"
  placeholder="Buscar dirección de origen..."
/>

<!-- Para destino -->
<SelectorUbicacion
  v-model="parada.ubicacion"
  label="Punto de destino"
  placeholder="Buscar dirección de destino..."
/>

<!-- Para paradas intermedias -->
<SelectorUbicacion
  v-model="parada.ubicacion"
  :label="`Parada ${index}`"
  placeholder="Buscar dirección de parada..."
/>
```

Cada SelectorUbicacion tiene altura fija de 300px para el mapa.
En mobile (ancho < 640px) colapsar el mapa a 200px.

---

## MEJORA 2 — GASTO ESTIMADO DE COMBUSTIBLE

### Dónde mostrarlo

Tres lugares:
1. Paso 3 del modal de creación (Calcular y confirmar) — ya existe el card de costos, agregar línea de combustible con desglose
2. Card de ruta activa en ListaRutas — agregar bajo la distancia
3. Panel lateral de detalle de ruta — tab Costos

### Lógica de cálculo (solo frontend, sin endpoint nuevo)

```javascript
function calcularCombustible(distanciaKm, vehiculo, configRuta) {
  if (!distanciaKm || !vehiculo) return null

  const consumo     = vehiculo.consumo_l_100km || 10
  const litros      = (distanciaKm / 100) * consumo
  const precioLitro = vehiculo.tipo_combustible === 'diesel'
    ? (configRuta?.precio_diesel  || 1250)
    : (configRuta?.precio_bencina || 1380)

  return {
    litros:       Math.round(litros * 10) / 10,
    precioLitro,
    total:        Math.round(litros * precioLitro),
    combustible:  vehiculo.tipo_combustible,
    consumo_l100: consumo,
  }
}
```

### Display en el modal (Paso 3 — Calcular y confirmar)

Reemplazar/ampliar el card de costos existente:
┌─────────────────────────────────────────┐
│  Costos estimados                        │
│─────────────────────────────────────────│
│  ⛽ Combustible          $71.000        │
│     17.0 L × $1.380/L (bencina)         │
│                                          │
│  🛣 Peajes               $14.400        │
│     3 peajes — Ruta 68                  │
│                                          │
│  ─────────────────────────────────────  │
│  Total estimado          $85.400        │
│                                          │
│  📍 142 km  ·  2h 45min                 │
└─────────────────────────────────────────┘

Si el vehículo no tiene consumo configurado (consumo_l_100km es null o 0):
⛽ Combustible          Sin datos
Configura el consumo del vehículo para ver el estimado
[Ir a vehículo ↗]

### Display en la tabla de rutas

En cada fila de la tabla, columna "Costo est." mostrar el total (combustible + peajes).
Si solo hay combustible (sin peajes calculados): mostrar igual con prefijo "~$".

### Cargar configRuta al montar Rutas.vue

```javascript
// Al montar la vista, cargar la configuración de precios:
const configRuta = ref(null)

onMounted(async () => {
  try {
    const data = await apiFetch('/api/empresa/rutas/configuracion/')
    configRuta.value = data
  } catch { /* fail silent */ }
})
```

Pasar configRuta como prop o proveer con provide/inject a los componentes que lo necesiten.

---

## MEJORA 3 — CARGA MASIVA DE RUTAS POR CSV/EXCEL

### Botón en Rutas.vue

Junto al botón "Nueva ruta" agregar:
[Nueva ruta]  [↑ Carga masiva]

### Modal: ModalCargaMasiva (componente interno de Rutas.vue)

Bottom sheet o modal centrado de 600px de ancho.

**Paso 1 — Descargar plantilla**
┌─────────────────────────────────────────┐
│  Carga masiva de rutas                  │
│─────────────────────────────────────────│
│  1. Descarga la plantilla               │
│     [⬇ Descargar plantilla CSV]         │
│     [⬇ Descargar plantilla Excel]       │
│                                         │
│  2. Completa los datos y sube el archivo│
│     [  📂 Seleccionar archivo  ]        │
│     Acepta: .csv · .xlsx · máx 5MB      │
│                                         │
│  [Cancelar]                             │
└─────────────────────────────────────────┘

**Plantilla CSV/Excel — columnas exactas:**
nombre,tipo,conductor_rut,vehiculo_patente,fecha_programada,origen_nombre,origen_lat,origen_lng,destino_nombre,destino_lat,destino_lng,notas
STG → VAL #090,carga,12345678-9,PPU-4421,2025-06-01 08:30,Bodega Central,-33.4489,-70.6693,Puerto Valparaíso,-33.0456,-71.6234,
STG → RAN #091,carga,12345678-9,PPU-4421,2025-06-02 09:00,Bodega Central,-33.4489,-70.6693,Rancagua Centro,-34.1708,-70.7444,Carga frágil

**Generar plantilla en el frontend (sin backend):**
```javascript
function descargarPlantillaCSV() {
  const header  = 'nombre,tipo,conductor_rut,vehiculo_patente,fecha_programada,origen_nombre,origen_lat,origen_lng,destino_nombre,destino_lat,destino_lng,notas'
  const ejemplo = 'STG → VAL #090,carga,12345678-9,PPU-4421,2025-06-01 08:30,Bodega Central,-33.4489,-70.6693,Puerto Valparaíso,-33.0456,-71.6234,'
  const csv     = `${header}\n${ejemplo}`
  const blob    = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url     = URL.createObjectURL(blob)
  const a       = document.createElement('a')
  a.href        = url
  a.download    = 'plantilla_rutas.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function descargarPlantillaExcel() {
  // Usar SheetJS (xlsx) que ya está disponible en el stack:
  import * as XLSX from 'xlsx'
  const datos = [
    ['nombre','tipo','conductor_rut','vehiculo_patente','fecha_programada','origen_nombre','origen_lat','origen_lng','destino_nombre','destino_lat','destino_lng','notas'],
    ['STG → VAL #090','carga','12345678-9','PPU-4421','2025-06-01 08:30','Bodega Central',-33.4489,-70.6693,'Puerto Valparaíso',-33.0456,-71.6234,''],
  ]
  const ws  = XLSX.utils.aoa_to_sheet(datos)
  const wb  = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Rutas')
  XLSX.writeFile(wb, 'plantilla_rutas.xlsx')
}
```

**Paso 2 — Vista previa y validación (al subir el archivo)**

Parsear el archivo en el frontend antes de enviarlo al backend:

```javascript
async function parsearArchivo(file) {
  if (file.name.endsWith('.csv')) {
    return parsearCSV(await file.text())
  } else {
    import * as XLSX from 'xlsx'
    const buffer = await file.arrayBuffer()
    const wb     = XLSX.read(buffer)
    const ws     = wb.Sheets[wb.SheetNames[0]]
    return XLSX.utils.sheet_to_json(ws, { header: 1 })
      .slice(1)
      .map(fila => ({
        nombre:            fila[0],
        tipo:              fila[1],
        conductor_rut:     fila[2],
        vehiculo_patente:  fila[3],
        fecha_programada:  fila[4],
        origen_nombre:     fila[5],
        origen_lat:        parseFloat(fila[6]),
        origen_lng:        parseFloat(fila[7]),
        destino_nombre:    fila[8],
        destino_lat:       parseFloat(fila[9]),
        destino_lng:       parseFloat(fila[10]),
        notas:             fila[11] || '',
      }))
  }
}
```

**Validaciones en el frontend antes de enviar:**
- nombre: requerido, no vacío
- tipo: debe ser 'carga' o 'personas'
- origen_lat, origen_lng, destino_lat, destino_lng: números válidos, rango Chile
- fecha_programada: formato YYYY-MM-DD HH:mm, fecha futura
- vehiculo_patente: formato válido (letras y números)

Mostrar tabla de vista previa con las filas parseadas:
┌────────┬────────┬──────────┬───────────┬──────────────┬────────┐
│ Fila   │ Nombre │ Tipo     │ Patente   │ Fecha        │ Estado │
├────────┼────────┼──────────┼───────────┼──────────────┼────────┤
│ 1      │ STG→VAL│ Carga    │ PPU-4421  │ 01/06 08:30  │ ✓ OK  │
│ 2      │ STG→RAN│ Carga    │ PPU-4421  │ 02/06 09:00  │ ✓ OK  │
│ 3      │        │ carga    │ INVALIDA  │ 2025-06-03   │ ✗ Error│
└────────┴────────┴──────────┴───────────┴──────────────┴────────┘

Filas con error: fondo rojo suave, no se envían.
Resumen: "3 rutas válidas · 1 con errores (no se crearán)"

**Botón "Importar X rutas válidas"** — activo solo si hay al menos una fila válida.

**Paso 3 — Envío al backend**

```javascript
async function importarRutas() {
  const rutasValidas = filasParseadas.value.filter(f => f.valida)
  importando.value   = true

  const resultados = []
  for (const ruta of rutasValidas) {
    try {
      await apiFetch('/api/empresa/rutas/', {
        method: 'POST',
        body: JSON.stringify({
          nombre:           ruta.nombre,
          tipo:             ruta.tipo,
          vehiculo_patente: ruta.vehiculo_patente,
          conductor_rut:    ruta.conductor_rut,
          fecha_programada: ruta.fecha_programada,
          notas:            ruta.notas,
          paradas: [
            { tipo: 'origen',  orden: 1, nombre: ruta.origen_nombre,  latitud: ruta.origen_lat,  longitud: ruta.origen_lng },
            { tipo: 'destino', orden: 2, nombre: ruta.destino_nombre, latitud: ruta.destino_lat, longitud: ruta.destino_lng },
          ],
        }),
      })
      resultados.push({ fila: ruta._fila, ok: true })
    } catch (e) {
      resultados.push({ fila: ruta._fila, ok: false, error: e.message })
    }
  }

  // Mostrar resumen de importación
  const exitosas = resultados.filter(r => r.ok).length
  const fallidas = resultados.filter(r => !r.ok).length
  showToast(`${exitosas} rutas importadas${fallidas ? ` · ${fallidas} fallidas` : ''}`, exitosas > 0 ? 'exito' : 'error')

  if (exitosas > 0) {
    cerrarModal()
    await cargarRutas()
  }
}
```

Mostrar barra de progreso durante la importación:
Importando... 2 / 3 rutas
[████████████░░░░░░░░] 66%

**Manejo de campos opcionales en el backend:**
El endpoint POST /api/empresa/rutas/ ya existe. Solo debe aceptar adicionalmente `vehiculo_patente` y `conductor_rut` como alternativa a `vehiculo_id` y `conductor_id` — buscar el vehículo/conductor por esos campos antes de crear.

Agregar en la vista POST /api/empresa/rutas/ de views.py:
```python
# Si viene vehiculo_patente en lugar de vehiculo_id:
if not body.get('vehiculo_id') and body.get('vehiculo_patente'):
    try:
        v = Vehiculo.objects.get(patente=body['vehiculo_patente'].upper(), flota__empresa=empresa)
        body['vehiculo_id'] = v.id
    except Vehiculo.DoesNotExist:
        pass  # crear ruta sin vehículo asignado

# Si viene conductor_rut en lugar de conductor_id:
if not body.get('conductor_id') and body.get('conductor_rut'):
    from .models import normalizar_rut
    import hashlib
    rut_hash = hashlib.sha256(normalizar_rut(body['conductor_rut']).encode()).hexdigest()
    try:
        c = Usuario.objects.get(rut_hash=rut_hash, empresa=empresa, rol='CONDUCTOR')
        body['conductor_id'] = c.id
    except Usuario.DoesNotExist:
        pass
```

---

## CONVENCIONES

- Composition API <script setup> siempre
- apiFetch siempre, nunca fetch directo (excepto Nominatim que es externo)
- Nominatim: debounce 500ms obligatorio — rate limit estricto
- useAsync para todas las llamadas a apiFetch
- showToast usando window.dispatchEvent con CustomEvent 'app-toast' (patrón existente del sistema)
- Leaflet cargado dinámicamente si window.L no existe (mismo patrón que MapaRuta.vue)
- onUnmounted: destruir instancias de Leaflet para evitar memory leaks
- SheetJS (xlsx) importado dinámicamente solo cuando se necesita
- Montos en CLP formato $X.XXX con función formatCLP existente
- Sin modelos nuevos — todo usa modelos existentes

---

## ARCHIVOS A ENTREGAR

Frontend:
1. src/web/rutas/SelectorUbicacion.vue — completo
2. src/web/rutas/Rutas.vue — indicar exactamente qué secciones reemplazar/agregar (no reescribir todo si es muy largo — indicar los diffs claros)
3. src/web/rutas/MapaRuta.vue — solo si necesita cambios (indicar qué)

Backend:
4. views_rutas_patch.py — solo el fragmento de vehiculo_patente/conductor_rut a agregar en la vista POST existente, con indicación de línea aproximada

Sin "# resto igual".
