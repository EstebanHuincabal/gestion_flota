Vas a implementar el módulo de Carta Gantt para el sistema de gestión de flota. Es una vista nueva en el panel web que visualiza rutas y mantenciones en una línea de tiempo interactiva, con indicadores de atraso y estado. Sin modelos nuevos — usa Ruta, Mantencion, Vehiculo, Conductor (Usuario) existentes.

---

## CONTEXTO DEL SISTEMA

Modelos relevantes ya existentes:
- Ruta: id, nombre, tipo, estado, conductor FK, vehiculo FK, fecha_programada, hora_programada, fecha_inicio, fecha_fin, distancia_km, duracion_min
- Parada: ruta FK, tipo (origen/parada/destino), orden, nombre, latitud, longitud
- EventoRuta: ruta FK, tipo (auto/comentario), texto, autor FK, created_at
- Mantencion: vehiculo FK, tipo_mantencion, estado, fecha_programada, fecha_realizada, costo, descripcion, taller_proveedor
- Vehiculo: patente, marca, modelo, activo, flota FK
- Usuario (conductor): nombre_cifrado, rol='CONDUCTOR'

Estados de Ruta: borrador | pendiente | activo | finalizado | cancelado
Estados de Mantencion: pendiente | en_proceso | realizada | cancelada

---

## ENDPOINT NUEVO (agregar en views_rutas.py)

### GET /api/empresa/gantt/

Parámetros:
- fecha_desde: YYYY-MM-DD (default: primer día del mes actual)
- fecha_hasta: YYYY-MM-DD (default: último día del mes actual)
- tipo: 'rutas' | 'mantenciones' | 'todo' (default: 'todo')
- vehiculo_id: filtrar por vehículo (opcional)
- conductor_id: filtrar por conductor (opcional)

Retorna:
```json
{
  "periodo": {
    "desde": "2025-05-01",
    "hasta": "2025-05-31"
  },
  "filas": [
    {
      "id": "vehiculo_3",
      "tipo_fila": "vehiculo",
      "etiqueta": "PPU-4421",
      "subtitulo": "Mercedes Actros · Flota Norte",
      "items": [
        {
          "id": 84,
          "tipo_item": "ruta",
          "nombre": "STG → VAL #084",
          "estado": "finalizado",
          "fecha_inicio_plan": "2025-05-20",
          "hora_inicio_plan": "08:30",
          "fecha_fin_plan": "2025-05-20",
          "hora_fin_plan": "11:15",
          "fecha_inicio_real": "2025-05-20",
          "hora_inicio_real": "08:45",
          "fecha_fin_real": "2025-05-20",
          "hora_fin_real": "11:50",
          "atrasado": true,
          "minutos_atraso": 35,
          "conductor": "Juan Muñoz",
          "origen": "Bodega Central",
          "destino": "Puerto Valparaíso",
          "distancia_km": 142.5
        },
        {
          "id": 12,
          "tipo_item": "mantencion",
          "nombre": "Cambio de aceite",
          "estado": "pendiente",
          "fecha_inicio_plan": "2025-05-25",
          "hora_inicio_plan": null,
          "fecha_fin_plan": "2025-05-25",
          "hora_fin_plan": null,
          "fecha_inicio_real": null,
          "hora_inicio_real": null,
          "fecha_fin_real": null,
          "hora_fin_real": null,
          "atrasado": true,
          "minutos_atraso": null,
          "taller": "Taller Mecánico Pérez",
          "tipo_mantencion": "Mantención preventiva"
        }
      ]
    }
  ],
  "resumen": {
    "total_rutas": 18,
    "rutas_a_tiempo": 12,
    "rutas_atrasadas": 4,
    "rutas_canceladas": 2,
    "total_mantenciones": 8,
    "mantenciones_pendientes": 3,
    "mantenciones_vencidas": 1
  }
}
```

### Lógica de cálculo de atraso:

**Para rutas:**
- Una ruta está ATRASADA si:
  - Estado `activo` y han pasado más de `duracion_min` minutos desde `fecha_inicio`
  - Estado `finalizado` y `fecha_fin` fue más de 15 minutos después de la hora estimada (`fecha_inicio + duracion_min`)
  - Estado `pendiente` y la `fecha_programada` + `hora_programada` ya pasó
- `minutos_atraso`: diferencia en minutos entre lo real y lo planificado (solo si hay datos reales)

**Para mantenciones:**
- Una mantención está ATRASADA si:
  - Estado `pendiente` o `en_proceso` y `fecha_programada` < hoy
  - `minutos_atraso` no aplica — solo días de atraso

```python
# En views_rutas.py, función helper:
from django.utils import timezone
from datetime import datetime, timedelta, date

def calcular_estado_gantt(item_tipo, item):
    """
    Calcula si un item está atrasado y cuánto.
    Retorna: { atrasado: bool, minutos_atraso: int|None, dias_atraso: int|None }
    """
    hoy = timezone.now()

    if item_tipo == 'ruta':
        if item.estado == 'pendiente' and item.fecha_programada:
            hora = item.hora_programada or time(8, 0)
            dt_programado = datetime.combine(item.fecha_programada, hora)
            dt_programado = timezone.make_aware(dt_programado)
            if hoy > dt_programado:
                diff = hoy - dt_programado
                return {
                    'atrasado':       True,
                    'minutos_atraso': int(diff.total_seconds() / 60),
                    'dias_atraso':    diff.days,
                }

        elif item.estado == 'activo' and item.fecha_inicio and item.duracion_min:
            fin_estimado = item.fecha_inicio + timedelta(minutes=item.duracion_min)
            if hoy > fin_estimado + timedelta(minutes=15):
                diff = hoy - fin_estimado
                return {
                    'atrasado':       True,
                    'minutos_atraso': int(diff.total_seconds() / 60),
                    'dias_atraso':    None,
                }

        elif item.estado == 'finalizado' and item.fecha_fin and item.fecha_inicio and item.duracion_min:
            fin_estimado = item.fecha_inicio + timedelta(minutes=item.duracion_min)
            if item.fecha_fin > fin_estimado + timedelta(minutes=15):
                diff = item.fecha_fin - fin_estimado
                return {
                    'atrasado':       True,
                    'minutos_atraso': int(diff.total_seconds() / 60),
                    'dias_atraso':    None,
                }

    elif item_tipo == 'mantencion':
        if item.estado in ('pendiente', 'en_proceso') and item.fecha_programada:
            if item.fecha_programada < date.today():
                diff = date.today() - item.fecha_programada
                return {
                    'atrasado':    True,
                    'minutos_atraso': None,
                    'dias_atraso': diff.days,
                }

    return {'atrasado': False, 'minutos_atraso': None, 'dias_atraso': None}
```

---

## URL

```python
path('api/empresa/gantt/', GanttView.as_view()),
```

---

## FRONTEND: src/web/rutas/Gantt.vue

Vista completa del módulo. Sin librerías externas de Gantt — construida con divs CSS y cálculos propios de posición y ancho. Solo usa lo que ya tiene el proyecto.

### Layout general
Header: "Carta Gantt"  [Exportar PDF]
Controles: [◀ Mes anterior] [Mayo 2025 ▶]  [Hoy]
Filtros:   [Todo ▼] [Todos los vehículos ▼] [Todos los conductores ▼]
Tabs:      [Rutas y Mantenciones] [Solo Rutas] [Solo Mantenciones]
Leyenda:   [■ Pendiente] [■ Activo] [■ Finalizado] [■ Atrasado] [■ Cancelado] [■ Mantención]
┌──────────────────────────────────────────────────────────────────────┐
│ Vehículo/Conductor │ L1 M2 M3 J4 V5 S6 D7 ... V31                    │
│────────────────────┼──────────────────────────────────────────────────│
│ PPU-4421           │ [══ruta══]      [═══ruta atrasada═══]             │
│ Mercedes Actros    │          [■man]                                   │
│────────────────────┼──────────────────────────────────────────────────│
│ BBTF-12            │        [══ruta══]        [══ruta══]               │
│ Conductor: C.Rojas │                   [══════mantención══════]        │
└──────────────────────────────────────────────────────────────────────┘

### Cabecera de días (eje X)

Generar todos los días del período visible.
Cada día tiene un ancho fijo: `--dia-ancho: 36px`
Hoy destacado con fondo morado suave y línea vertical punteada que cruza todas las filas.
Los días muestran: nombre del día abreviado arriba (L M M J V S D), número del día abajo.
Fines de semana (S y D) con fondo ligeramente diferente.

```javascript
// Calcular posición y ancho de un item en el Gantt:
function calcularBarra(item, fechaDesde, anchoDia) {
  const inicio = new Date(item.fecha_inicio_plan || item.fecha_inicio_real)
  const fin    = new Date(item.fecha_fin_plan   || item.fecha_fin_real   || item.fecha_inicio_plan)

  const diasDesdeInicio = Math.floor(
    (inicio - new Date(fechaDesde)) / (1000 * 60 * 60 * 24)
  )
  const duracionDias = Math.max(
    (fin - inicio) / (1000 * 60 * 60 * 24),
    0.15  // mínimo 15% de un día para que sea visible
  )

  return {
    left:  `${diasDesdeInicio * anchoDia}px`,
    width: `${duracionDias * anchoDia}px`,
  }
}
```

### Barras del Gantt

Cada item es un div absolutamente posicionado dentro de su fila.

**Colores por estado:**
```javascript
const COLORES = {
  // Rutas
  ruta_pendiente:  { bg: '#E6F1FB', border: '#378ADD', text: '#0C447C' },
  ruta_activo:     { bg: '#E1F5EE', border: '#1D9E75', text: '#085041', pulsar: true },
  ruta_finalizado: { bg: '#F0F0F0', border: '#9CA3AF', text: '#4B5563' },
  ruta_cancelado:  { bg: '#FEF3C7', border: '#D97706', text: '#92400E', rayado: true },
  ruta_atrasado:   { bg: '#FCEBEB', border: '#E24B4A', text: '#791F1F' },
  // Mantenciones
  mant_pendiente:  { bg: '#EEEDFE', border: '#534AB7', text: '#3C3489' },
  mant_en_proceso: { bg: '#DCFCE7', border: '#16A34A', text: '#14532D' },
  mant_realizada:  { bg: '#F0F0F0', border: '#9CA3AF', text: '#4B5563' },
  mant_cancelada:  { bg: '#FEF3C7', border: '#D97706', text: '#92400E', rayado: true },
  mant_atrasado:   { bg: '#FCEBEB', border: '#E24B4A', text: '#791F1F' },
}
```

**Contenido de cada barra:**
- Si el ancho da espacio (> 60px): mostrar nombre truncado dentro de la barra
- Si el ancho es pequeño (< 60px): solo mostrar ícono (ti-truck para rutas, ti-tool para mantenciones)
- Tooltip al hacer hover con todos los datos completos
- Punto pulsante verde si estado='activo'
- Banda diagonal roja si está atrasado (::after con pattern CSS)
- Ícono de reloj ⏱ si atrasado, con badge del tiempo de atraso

**Doble barra para items con datos reales:**
Si un item tiene tanto fecha planificada como fecha real, mostrar:
- Barra superior (60% de alto): tiempo planificado — color normal
- Barra inferior (40% de alto): tiempo real — color más intenso si hay atraso, igual si fue puntual
[═══ Planificado ════════]        ← barra superior, color normal
[════ Real ═══════════════]     ← barra inferior, desplazada si arrancó tarde

### Fila del Gantt

Cada fila representa un vehículo. Dentro puede tener rutas Y mantenciones en sublíneas separadas:
┌────────────────────────────────────────────────────┐
│ PPU-4421                                            │
│ Mercedes Actros · Flota Norte                       │  ← header de fila (40px)
├───── Rutas ─────────────────────────────────────────│  ← sublínea rutas (44px)
│         [══ruta══]      [══ruta══]                  │
├───── Mantenciones ──────────────────────────────────│  ← sublínea mantenciones (si tiene)
│                   [■man]                            │
└────────────────────────────────────────────────────┘

Si un vehículo no tiene mantenciones en el período, no mostrar la sublínea de mantenciones.

### Tooltip al hacer hover

Al pasar el mouse sobre una barra, mostrar un tooltip flotante con:

**Para rutas:**
┌─────────────────────────────────┐
│ STG → VAL #084          [Estado]│
│ ─────────────────────────────── │
│ Conductor:  Juan Muñoz          │
│ Origen:     Bodega Central      │
│ Destino:    Puerto Valparaíso   │
│ Distancia:  142 km              │
│ Planificado: 20/05 08:30 → 11:15│
│ Real:        20/05 08:45 → 11:50│
│ Atraso:      ⚠ 35 min           │
└─────────────────────────────────┘

**Para mantenciones:**
┌─────────────────────────────────┐
│ Cambio de aceite        [Estado]│
│ ─────────────────────────────── │
│ Tipo:    Mantención preventiva  │
│ Taller:  Taller Mecánico Pérez  │
│ Fecha:   25/05/2025             │
│ Atraso:  ⚠ 5 días vencida       │
└─────────────────────────────────┘

El tooltip aparece a la derecha de la barra si hay espacio, si no a la izquierda.
Desaparece al mover el mouse fuera. No usar librerías externas — div posicionado con JS.

### Click en una barra

Al hacer click en una ruta → abrir el panel lateral de detalle existente de Rutas.vue (misma lógica, emit evento 'ver-ruta' con el id).
Al hacer click en una mantención → abrir modal de detalle de la mantención.

### Indicador de hoy

Línea vertical punteada que cruza todo el Gantt en la posición del día actual.
Badge flotante encima: "Hoy" con fondo morado.
Si el período no incluye hoy → no mostrar la línea.

```javascript
function posicionHoy(fechaDesde, anchoDia) {
  const hoy  = new Date()
  const desde = new Date(fechaDesde)
  const dias  = Math.floor((hoy - desde) / (1000 * 60 * 60 * 24))
  if (dias < 0) return null
  return `${dias * anchoDia + anchoDia / 2}px`
}
```

### Navegación de período

Selector de período con tres modos:
- **Mes:** ver el mes completo (30-31 días). Botones ◀ ▶ para mes anterior/siguiente.
- **Semana:** ver 7 días. Botones ◀ ▶ para semana anterior/siguiente.
- **Personalizado:** date pickers de fecha desde/hasta (máximo 90 días).

Al cambiar el período → llamar al endpoint con los nuevos parámetros.

```javascript
const modo       = ref('mes')   // 'mes' | 'semana' | 'personalizado'
const fechaBase  = ref(new Date())

const fechaDesde = computed(() => {
  if (modo.value === 'mes')
    return new Date(fechaBase.value.getFullYear(), fechaBase.value.getMonth(), 1)
  if (modo.value === 'semana') {
    const d = new Date(fechaBase.value)
    d.setDate(d.getDate() - d.getDay() + 1)  // lunes
    return d
  }
  return fechaPersonalizadaDesde.value
})

const fechaHasta = computed(() => {
  if (modo.value === 'mes')
    return new Date(fechaBase.value.getFullYear(), fechaBase.value.getMonth() + 1, 0)
  if (modo.value === 'semana') {
    const d = new Date(fechaDesde.value)
    d.setDate(d.getDate() + 6)
    return d
  }
  return fechaPersonalizadaHasta.value
})
```

### KPI cards sobre el Gantt
[18 rutas]  [12 a tiempo ✓]  [4 atrasadas ⚠]  [2 canceladas ✗]  [8 mantenciones]  [1 vencida 🔴]
Cargados desde `resumen` del endpoint.
Click en "4 atrasadas" → filtrar el Gantt para mostrar solo items atrasados.

### Skeleton loader

Mientras carga el endpoint, mostrar:
- 4 filas con barras grises animadas de ancho aleatorio
- Cabecera de días normal (se puede calcular sin datos)

### Estado vacío

Si no hay datos para el período:
[ícono ti-calendar-off, gris, grande]
Sin rutas ni mantenciones en este período
Ajusta el rango de fechas o crea rutas desde el módulo de Rutas
[Ir a Rutas →]

### Scroll horizontal

El Gantt debe ser horizontalmente scrolleable si los días no caben en pantalla.
La columna de etiquetas (vehículo/conductor) queda fija a la izquierda:

```css
.gantt-container {
  display: grid;
  grid-template-columns: 200px 1fr;
  overflow: hidden;
}

.gantt-etiquetas {
  position: sticky;
  left: 0;
  z-index: 10;
  background: var(--color-background-primary);
  border-right: 1px solid var(--color-border-tertiary);
}

.gantt-scroll {
  overflow-x: auto;
  overflow-y: hidden;
}
```

---

## EXPORTAR A PDF

Botón "Exportar PDF" en el header.
Usar `window.print()` con estilos CSS de impresión:

```javascript
function exportarPDF() {
  window.print()
}
```

Agregar en el CSS del componente:
```css
@media print {
  /* Ocultar todo excepto el Gantt */
  .sidebar, .navbar, .filters-bar, .kpi-cards { display: none !important; }

  /* El Gantt ocupa toda la página */
  .gantt-wrapper { width: 100%; overflow: visible; }

  /* Expandir todo el contenido sin scroll */
  .gantt-scroll { overflow: visible; width: max-content; }

  /* Forzar colores de impresión */
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  /* Título de impresión */
  .gantt-print-header { display: block; }
}
```

---

## NAVEGACIÓN

Agregar en el sidebar del USUARIO (buscar en el proyecto):
Ítem: Carta Gantt
Ícono: ti-chart-gantt
Ruta: /empresa/gantt

Agregar en router/index.js:
```javascript
{
  path: '/empresa/gantt',
  component: () => import('@/web/rutas/Gantt.vue'),
  meta: { requiresAuth: true, roles: ['USUARIO'] }
}
```

---

## CONVENCIONES

- Composition API <script setup> siempre
- apiFetch siempre, nunca fetch directo
- useAsync para la llamada al endpoint
- Sin librerías externas de Gantt — todo construido con divs y CSS
- Colores consistentes con el design system del proyecto (variables CSS existentes)
- Tooltip sin librerías externas — div posicionado con JS
- Scroll horizontal con columna de etiquetas sticky
- formatFechaRuta de utils/formato.js existente para fechas
- formatCLP de utils/formato.js para costos
- Textos en español es-CL
- Sin modelos nuevos

---

## ARCHIVOS A ENTREGAR

Backend:
1. views_gantt_patch.py — GanttView completa + helper calcular_estado_gantt, con indicación de dónde van en views_rutas.py
2. urls_patch.py — la ruta nueva

Frontend:
3. src/web/rutas/Gantt.vue — completo
4. router_patch.js — la ruta nueva
5. nav_patch.md — ítem a agregar en el sidebar

Sin "# resto igual".