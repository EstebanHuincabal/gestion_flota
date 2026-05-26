Implementa el checklist pre-viaje sin tablas nuevas — reutiliza SolicitudConductor y agrega un JSONField en Ruta.

---

## CAMBIO EN models.py

Agregar en la clase Ruta después del campo notas:
```python
extra = models.JSONField(default=dict, blank=True)
```

Luego: python manage.py makemigrations && python manage.py migrate

---

## ARCHIVO NUEVO: g_de_flota/checklist_items.py

```python
CHECKLIST_ITEMS = [
    ('doc_permiso',   'documentos', 'Permiso de circulación',   'Vigente y en el vehículo',  True),
    ('doc_revision',  'documentos', 'Revisión técnica',         'Vigente y en el vehículo',  True),
    ('doc_soap',      'documentos', 'Seguro SOAP',              'Vigente y en el vehículo',  True),
    ('doc_licencia',  'documentos', 'Licencia de conducir',     'Vigente y clase correcta',  True),
    ('mec_frenos',    'mecanica',   'Frenos',                   'Freno de pie y de mano',    True),
    ('mec_neumaticos','mecanica',   'Neumáticos',               'Estado y presión correcta', True),
    ('mec_aceite',    'mecanica',   'Nivel de aceite',          'En rango normal',           True),
    ('mec_combustible','mecanica',  'Nivel de combustible',     'Suficiente para la ruta',   True),
    ('mec_luces',     'mecanica',   'Luces y señalización',     'Todas funcionando',         True),
    ('seg_extintor',  'seguridad',  'Extintor',                 'Vigente y accesible',       True),
    ('seg_botiquin',  'seguridad',  'Botiquín',                 'Completo y accesible',      True),
    ('seg_triangulos','seguridad',  'Triángulos de emergencia', 'Presentes en el vehículo',  True),
]

def get_items():
    return [
        {'id': i[0], 'categoria': i[1], 'nombre': i[2], 'descripcion': i[3], 'obligatorio': i[4]}
        for i in CHECKLIST_ITEMS
    ]

ITEMS_MAP = {i[0]: i[2] for i in CHECKLIST_ITEMS}

MAP_DOC_ITEM = {
    'permiso_circulacion': 'doc_permiso',
    'revision_tecnica':    'doc_revision',
    'seguro_soap':         'doc_soap',
}
```

---

## VISTA ChecklistView (agregar en views.py)

Importar al inicio de views.py:
```python
from .checklist_items import get_items, ITEMS_MAP, MAP_DOC_ITEM
```

### GET /api/conductor/checklist/:ruta_id/
- Obtener ruta verificando que conductor == request.user
- Cargar ítems con get_items()
- Para cada ítem de documentos, buscar en Documento el estado real del vehículo de la ruta
  Usar MAP_DOC_ITEM para mapear tipo_doc → item_id
  Agregar al ítem: estado_documento (vigente/por_vencer/vencido/None) y pre_resultado ('ok' si vigente, None si no)
- Buscar borrador: SolicitudConductor con tipo='mantencion', extra__ruta_id=ruta.id, extra__es_checklist=True, estado='pendiente'
  Si existe, retornar sus respuestas guardadas en extra.respuestas
- Retornar: { items, respuestas_guardadas, ruta: {id, nombre}, vehiculo: {patente, marca} }

### POST /api/conductor/checklist/:ruta_id/
Body: { respuestas: { item_id: { resultado, observacion } }, firma_base64 }

1. Validar que todos los ítems obligatorios tienen resultado. Si faltan → 400 con mensaje.

2. Detectar fallas: items donde resultado == 'falla'

3. Construir resumen_fallas: lista de strings "NombreItem: observacion"

4. Crear o actualizar SolicitudConductor con update_or_create filtrando por
   conductor=request.user, tipo='mantencion', extra__ruta_id=ruta.id, extra__es_checklist=True
   Campos:
   - empresa, vehiculo de la ruta
   - titulo: f'Checklist pre-viaje — {ruta.nombre}'
   - descripcion: 'Vehículo en orden.' si sin fallas, o 'Fallas:\n' + fallas si hay
   - estado: 'aprobado' si sin fallas, 'pendiente' si hay fallas
   - prioridad: 'baja' si sin fallas, 'alta' si hay fallas
   - extra: { ruta_id, es_checklist: True, respuestas, firma_b64, tiene_fallas, fallas_detalle }

5. Notificar con notificar_admins_empresa():
   - Sin fallas: tipo='actividad', titulo='✓ Vehículo en orden — {patente}',
     mensaje='{conductor} completó el checklist. Vehículo listo para partir en {ruta.nombre}.'
   - Con fallas: tipo='solicitud_conductor', titulo='⚠ Checklist con fallas — {patente}',
     mensaje='{conductor} detectó fallas antes de partir: {resumen_fallas}'
   - En ambos casos: url_accion='/empresa/solicitudes/{sol.id}'

6. Actualizar ruta.extra: { checklist_completo: True, checklist_id: sol.id } → ruta.save()

7. Push al conductor con push_conductor():
   - Sin fallas: 'Todo en orden. Ya puedes iniciar la ruta.'
   - Con fallas: 'Se notificó al administrador sobre las fallas.'

8. registrar_log acción 'checklist_completado' con { ruta_id, tiene_fallas, fallas }

9. Retornar: { ok: True, tiene_fallas, solicitud_id, mensaje }

---

## URL (agregar en urls.py)

```python
path('api/conductor/checklist/<int:ruta_id>/', ChecklistView.as_view()),
```

---

## FRONTEND: src/views/Rutas/ChecklistPreviaje.vue (crear completo)

### Layout
- Header: botón ← + título "Checklist pre-viaje" + subtítulo "{ruta.nombre} · {patente}"
- Barra de progreso (completados / total obligatorios × 100%)
- Badge "X / Y" con conteo
- Lista de ítems agrupados por categoría
- Sección de firma digital al final
- Botón de envío fijo al fondo

### Ítem del checklist
Cada ítem tiene tres estados visuales:
- pendiente: borde gris, círculo vacío — toque abre opciones
- ok: borde verde, fondo verde suave, círculo verde con check
- falla: borde rojo, fondo rojo suave, círculo rojo con X + textarea de observación

Al tocar un ítem pendiente: mostrar dos botones inline "✓ OK" y "✗ Falla"
Al tocar un ítem ya marcado: toggle que lo devuelve a pendiente
Los ítems de documentos con estado_documento='vigente' llegan pre-marcados como ok y muestran la fecha de vencimiento como subtítulo

### Firma digital
Componente canvas con eventos touch (touchstart, touchmove, touchend)
Botón "Limpiar" bajo el canvas
Al dibujar: emitir el base64 del canvas al padre

```javascript
// En el componente de firma:
function terminar() {
  emit('update:firma', canvas.value.toDataURL('image/png'))
}
```

### Botón de envío
Deshabilitado mientras haya ítems obligatorios sin respuesta o sin firma
Texto dinámico:
- Si faltan ítems: "Completa todos los ítems ({N} pendientes)"
- Si falta firma: "Firma para continuar"
- Si todo listo: "Enviar checklist"
Color: gris si deshabilitado, verde si listo

### Al enviar
- POST /api/conductor/checklist/:ruta_id/
- Si éxito sin fallas: showToast "Todo en orden. Puedes iniciar la ruta." → router.push(`/rutas/${rutaId}`)
- Si éxito con fallas: showToast "Checklist enviado con fallas. El admin fue notificado." → router.push(`/rutas/${rutaId}`)
- Si error: showToast con el mensaje del backend, no navegar

### Store (si aplica)
No necesita store propio — usar apiFetch directo en la vista con estado local ref()

---

## MODIFICAR DetalleRuta.vue

Agregar computed:
```javascript
const checklistCompleto = computed(() =>
  ruta.value?.extra?.checklist_completo === true
)
```

En el botón de acción para estado 'pendiente', reemplazar por lógica condicional:
- Si !checklistCompleto: mostrar botón morado "Completar checklist antes de iniciar"
  que navega a `/rutas/${ruta.id}/checklist`
- Si checklistCompleto: mostrar botón verde "Iniciar ruta" que abre el modal existente

---

## MODIFICAR router/index.js

```javascript
{
  path: '/rutas/:id/checklist',
  component: () => import('@/views/Rutas/ChecklistPreviaje.vue'),
  meta: { requiresAuth: true }
}
```

---

## CONVENCIONES
- Composition API <script setup>
- apiFetch siempre, nunca fetch directo
- Touch targets mínimo 44px
- safe-area-inset-bottom en el botón fijo del fondo
- Textos en español
- Si OSRM o push_conductor falla: fail-silent con registrar_log

---

## ARCHIVOS A ENTREGAR
1. checklist_items.py — completo
2. views_checklist_patch.py — ChecklistView completa con indicación de dónde va en views.py
3. urls_patch.py — la ruta nueva
4. models_patch.py — solo la línea extra = JSONField a agregar en Ruta
5. ChecklistPreviaje.vue — completo
6. detalleruta_patch.vue — solo el fragmento del botón de acción modificado
7. router_patch.js — solo la ruta nueva

Sin "# resto igual".