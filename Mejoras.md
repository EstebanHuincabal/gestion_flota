## LO QUE DEBES IMPLEMENTAR

Módulo de gestión de documentos con dos funciones centrales:
- Repositorio: almacenar, consultar y descargar archivos adjuntos
- Alertas: detectar y notificar documentos próximos a vencer o ya vencidos

Documentos a gestionar:
- Vehículos: permiso de circulación, revisión técnica, seguro obligatorio (SOAP)
- Conductores: licencia de conducir, antecedentes comerciales

---

## MODELO NUEVO (agregar en models.py)

```python
class Documento(models.Model):
    TIPOS_VEHICULO = [
        ('permiso_circulacion', 'Permiso de circulación'),
        ('revision_tecnica',    'Revisión técnica'),
        ('seguro_soap',         'Seguro SOAP'),
    ]
    TIPOS_CONDUCTOR = [
        ('licencia',      'Licencia de conducir'),
        ('antecedentes',  'Antecedentes comerciales'),
    ]
    TODOS_TIPOS = TIPOS_VEHICULO + TIPOS_CONDUCTOR

    ENTIDADES = [
        ('vehiculo',   'Vehículo'),
        ('conductor',  'Conductor'),
    ]

    empresa       = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='documentos')
    entidad       = models.CharField(max_length=20, choices=ENTIDADES)
    tipo          = models.CharField(max_length=30, choices=TODOS_TIPOS)

    # Solo uno de estos dos tiene valor según la entidad
    vehiculo      = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, null=True, blank=True, related_name='documentos')
    conductor     = models.ForeignKey(Usuario,  on_delete=models.CASCADE, null=True, blank=True, related_name='documentos_conductor')

    fecha_emision   = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    archivo         = models.FileField(upload_to='documentos/%Y/%m/', null=True, blank=True)
    nombre_archivo  = models.CharField(max_length=200, blank=True, default='')

    # Quién subió el documento
    subido_por      = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='documentos_subidos')
    notas           = models.CharField(max_length=500, blank=True, default='')

    # Versionado: si es renovación, apunta al documento anterior
    version_anterior = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versiones_nuevas')

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Documento'

    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        from django.utils import timezone
        delta = self.fecha_vencimiento - timezone.now().date()
        return delta.days

    def estado(self):
        dias = self.dias_para_vencer()
        if dias is None:
            return 'sin_vencimiento'
        if dias < 0:
            return 'vencido'
        if dias <= 30:
            return 'por_vencer'
        return 'vigente'
```

Restricción a validar en la vista: si entidad='vehiculo', vehiculo no puede ser null. Si entidad='conductor', conductor no puede ser null. Nunca ambos con valor al mismo tiempo.

---

## ENDPOINTS (agregar en views.py)

### GET /api/empresa/documentos/
Parámetros opcionales: entidad (vehiculo|conductor), tipo, estado (vigente|por_vencer|vencido), vehiculo_id, conductor_id, buscar (texto libre sobre tipo y nombre_archivo)

Retorna:
```json
{
  "documentos": [
    {
      "id": 1,
      "entidad": "vehiculo",
      "tipo": "revision_tecnica",
      "tipo_display": "Revisión técnica",
      "vehiculo_id": 3,
      "vehiculo_patente": "PPU-4421",
      "conductor_id": null,
      "conductor_nombre": null,
      "fecha_emision": "2024-04-02",
      "fecha_vencimiento": "2025-04-02",
      "dias_para_vencer": -30,
      "estado": "vencido",
      "tiene_archivo": true,
      "nombre_archivo": "revision_ppu4421_2024.pdf",
      "subido_por_nombre": "Admin Empresa",
      "notas": "",
      "created_at": "..."
    }
  ],
  "resumen": {
    "total": 84,
    "vigentes": 71,
    "por_vencer": 9,
    "vencidos": 4,
    "alertas": [
      {
        "id": 1,
        "tipo_display": "Revisión técnica",
        "entidad_nombre": "PPU-4421",
        "fecha_vencimiento": "2025-04-02",
        "dias_para_vencer": -30,
        "estado": "vencido"
      }
    ],
    "por_vehiculo": [
      {
        "vehiculo_id": 3,
        "patente": "PPU-4421",
        "total": 3,
        "esperados": 3,
        "estado_peor": "vencido"
      }
    ],
    "por_conductor": [
      {
        "conductor_id": 5,
        "nombre": "Juan Muñoz",
        "total": 2,
        "esperados": 2,
        "estado_peor": "por_vencer"
      }
    ]
  }
}
```

El campo "alertas" incluye solo documentos con estado vencido o por_vencer, ordenados: primero vencidos, luego por días_para_vencer ascendente.

El campo "esperados" en por_vehiculo es 3 (permiso + revisión + seguro). En por_conductor es 2 (licencia + antecedentes). Si total < esperados, el vehículo/conductor tiene documentos faltantes.

El campo "estado_peor" sigue esta jerarquía: vencido > por_vencer > vigente > sin_vencimiento.

### POST /api/empresa/documentos/
Acepta multipart/form-data (puede venir con o sin archivo adjunto).
Body: entidad, tipo, vehiculo_id o conductor_id, fecha_emision, fecha_vencimiento, archivo (opcional), notas (opcional), version_anterior_id (opcional, para renovaciones).
Validar que el tipo sea coherente con la entidad (tipos de vehículo solo para vehículos, etc.).
Registrar con registrar_log() acción 'documento_subido'.
Notificar al admin de la empresa con notificar() si el documento está cargado por un conductor (subido_por.rol == 'CONDUCTOR').

### GET /api/empresa/documentos/:id/
Retorna el documento completo. No retorna la URL del archivo directamente — genera una URL firmada temporal.

### PUT /api/empresa/documentos/:id/
Permite editar: fecha_emision, fecha_vencimiento, notas, archivo (reemplazar).
No permite cambiar entidad, tipo, vehiculo, ni conductor.
Registrar con registrar_log() acción 'documento_editado'.

### DELETE /api/empresa/documentos/:id/
Eliminar el registro Y el archivo del filesystem (usar default_storage.delete()).
Solo puede eliminar el subido_por o un USUARIO admin de la empresa.
Registrar con registrar_log() acción 'documento_eliminado'.

### GET /api/empresa/documentos/:id/descargar/
Sirve el archivo como respuesta HTTP con Content-Disposition: attachment.
Verificar que el usuario tenga acceso a la empresa del documento.
Usar FileResponse con el archivo abierto en modo binario.

### POST /api/empresa/documentos/:id/renovar/
Crea un nuevo documento como renovación del actual.
Body: igual al POST normal más version_anterior_id (se rellena automáticamente con :id).
El documento anterior queda con su estado (vencido/por_vencer) — no se elimina.
Retorna el nuevo documento creado.

---

## TAREA PERIÓDICA — verificar_vencimientos()

Agregar función en views.py (o en un archivo tasks.py si el proyecto ya usa Celery o similar, verificar en contexto.md):

```python
def verificar_vencimientos():
    """
    Debe ejecutarse diariamente.
    Envía notificaciones por documentos próximos a vencer o ya vencidos.
    No envía la misma notificación dos veces en el mismo día.
    """
    from django.utils import timezone
    hoy = timezone.now().date()

    UMBRALES_DIAS = [30, 15, 7, 1]  # notificar cuando faltan estos días

    documentos = Documento.objects.filter(
        fecha_vencimiento__isnull=False,
        vehiculo__flota__empresa__estado='activa'  # solo empresas activas
    ).select_related('empresa', 'vehiculo', 'conductor')

    for doc in documentos:
        dias = doc.dias_para_vencer()
        if dias is None:
            continue

        if dias < 0:
            # Vencido: notificar solo si no se notificó hoy
            ya_notificado = Notificacion.objects.filter(
                tipo='DOCUMENTO_VENCIDO',
                extra__documento_id=doc.id,
                created_at__date=hoy
            ).exists()
            if not ya_notificado:
                notificar_admins_empresa(
                    empresa=doc.empresa,
                    tipo='DOCUMENTO_VENCIDO',
                    titulo=f'Documento vencido: {doc.get_tipo_display()}',
                    mensaje=(
                        f'El documento "{doc.get_tipo_display()}" de '
                        f'{"el vehículo " + doc.vehiculo.patente if doc.vehiculo else "el conductor " + descifrar(doc.conductor.nombre_cifrado)} '
                        f'venció hace {abs(dias)} días.'
                    ),
                    extra={'documento_id': doc.id, 'dias': dias}
                )

        elif dias in UMBRALES_DIAS:
            ya_notificado = Notificacion.objects.filter(
                tipo='DOCUMENTO_POR_VENCER',
                extra__documento_id=doc.id,
                extra__dias_umbral=dias,
            ).exists()
            if not ya_notificado:
                notificar_admins_empresa(
                    empresa=doc.empresa,
                    tipo='DOCUMENTO_POR_VENCER',
                    titulo=f'Documento por vencer: {doc.get_tipo_display()}',
                    mensaje=(
                        f'El documento "{doc.get_tipo_display()}" de '
                        f'{"el vehículo " + doc.vehiculo.patente if doc.vehiculo else "el conductor " + descifrar(doc.conductor.nombre_cifrado)} '
                        f'vence en {dias} días ({doc.fecha_vencimiento.strftime("%d/%m/%Y")}).'
                    ),
                    extra={'documento_id': doc.id, 'dias': dias, 'dias_umbral': dias}
                )
```

Si el proyecto ya tiene un mecanismo de tareas periódicas (manage.py command, cron, etc.), integrarlo ahí. Si no, crear un management command:
`gestion_backend/g_de_flota/management/commands/verificar_documentos.py`
con `python manage.py verificar_documentos` que llame a verificar_vencimientos().

---

## URLs a agregar en urls.py

```python
path('api/empresa/documentos/',                         DocumentosListView.as_view()),
path('api/empresa/documentos/<int:doc_id>/',            DocumentoDetailView.as_view()),
path('api/empresa/documentos/<int:doc_id>/descargar/',  DocumentoDescargarView.as_view()),
path('api/empresa/documentos/<int:doc_id>/renovar/',    DocumentoRenovarView.as_view()),
```

---

## FRONTEND — ARCHIVOS A CREAR

### src/web/documentos/Documentos.vue
Vista completa del módulo.

**Header:**
- Título "Gestión de documentos" + nombre de empresa
- Botón "Subir documento" abre el modal de carga

**KPI cards (fila de 4):**
Total documentos | Vigentes (verde) | Por vencer en 30 días (naranja) | Vencidos (rojo)

**Fila de dos columnas:**

Columna izquierda — "Alertas activas":
- Lista de documentos con estado vencido o por_vencer
- Cada fila: ícono según entidad (ti-car para vehículo, ti-id-badge para conductor), nombre del documento y entidad asociada, fecha de vencimiento, chip de días (rojo si vencido, naranja si por_vencer)
- Fondo de fila rojo suave si vencido, naranja suave si por_vencer
- Click en fila abre el detalle del documento

Columna derecha — dos tablas apiladas:
- "Estado por vehículo": patente, total/esperados de documentos, badge de estado peor
- "Estado por conductor": nombre, total/esperados, badge de estado peor
- Click en fila filtra la tabla principal por ese vehículo/conductor

**Tabla principal "Todos los documentos":**
Columnas: Tipo (badge azul=vehículo, púrpura=conductor), Documento (nombre display), Asociado a (patente o nombre conductor), Emisión, Vencimiento (resaltado según estado), Estado (badge), Archivo (botón descargar si tiene archivo)

Filtros sobre la tabla:
- Select tipo: Todos / Vehículos / Conductores
- Select estado: Todos / Vigente / Por vencer / Vencido
- Input búsqueda por texto

**Modal subir/editar documento:**
Campos:
1. Entidad (radio o select: Vehículo / Conductor) — al cambiar resetea el siguiente campo
2. Vehículo o Conductor (select dinámico según entidad)
3. Tipo de documento (select filtrado según entidad seleccionada)
4. Fecha de emisión (date input)
5. Fecha de vencimiento (date input)
6. Archivo adjunto (input type=file, acepta PDF e imágenes, máximo 10MB)
7. Notas (textarea opcional)

Validaciones en frontend:
- Fecha vencimiento > fecha emisión
- Archivo obligatorio solo si es primera vez (en edición es opcional)
- Tipo coherente con entidad

Al subir: usar FormData si hay archivo, JSON si no.
Mostrar preview del archivo si es imagen. Si es PDF mostrar ícono de PDF con nombre.

**Modal renovar documento:**
Pre-rellena tipo, entidad, vehículo/conductor del documento original.
Campos editables: nueva fecha de emisión, nueva fecha de vencimiento, nuevo archivo (obligatorio), notas.
Banner informativo: "Esta renovación no elimina el documento anterior. Ambos quedarán en el historial."

**Modal detalle documento:**
Muestra todos los campos del documento.
Botón descargar archivo (llama a /api/empresa/documentos/:id/descargar/).
Botón renovar (abre modal de renovación).
Botón eliminar (con ConfirmModal).
Si tiene version_anterior, link "Ver documento anterior".

**Comportamiento de carga:**
- Al montar: GET /api/empresa/documentos/ sin filtros
- Al cambiar filtros: GET con parámetros correspondientes
- Loading state con spinner mientras carga
- Fail-silent en los resúmenes (si falla la API no romper la vista)

### src/web/documentos/DocumentosBadge.vue
Componente pequeño reutilizable para mostrar en otras vistas (ej: ficha de vehículo, ficha de conductor):
- Recibe prop: entidad ('vehiculo'|'conductor') + id
- Llama a /api/empresa/documentos/?entidad=X&vehiculo_id=Y (o conductor_id)
- Muestra: chip verde "Docs al día", naranja "X por vencer", rojo "X vencidos / Faltan docs"
- Click abre un popover con la lista de documentos de esa entidad

---

## INTEGRACIÓN CON VISTAS EXISTENTES

En la vista de detalle de vehículo (si existe), agregar al final:
```vue
<DocumentosBadge entidad="vehiculo" :id="vehiculo.id" />
```

En la vista de detalle de conductor (si existe), agregar:
```vue
<DocumentosBadge entidad="conductor" :id="conductor.id" />
```

Buscar esas vistas en el contexto.md y agregar el import y el componente en el lugar apropiado.

---

## NAVEGACIÓN

Agregar en el sidebar del USUARIO (buscar el archivo de navegación en contexto.md):
Ítem: Documentos
Ícono: ti-files
Ruta: /empresa/documentos

Agregar en router/index.js:
```javascript
{
  path: '/empresa/documentos',
  component: () => import('@/web/documentos/Documentos.vue'),
  meta: { requiresAuth: true, roles: ['USUARIO'] }
}
```

---

## CONVENCIONES Y RESTRICCIONES

- Solo USUARIO admin de la empresa puede subir, editar, eliminar y descargar documentos de su empresa. No puede acceder a documentos de otras empresas.
- Un conductor (cuando tenga app) solo puede subir documentos propios (licencia y antecedentes). No puede ver ni tocar documentos de vehículos ni de otros conductores. Preparar el backend para esto aunque la app no exista aún: verificar subido_por.rol == 'CONDUCTOR' y que el conductor sea el mismo usuario autenticado.
- SUPERADMIN puede ver documentos de cualquier empresa (agregar parámetro empresa_id opcional al GET).
- Los archivos se sirven desde el backend, nunca exponer rutas directas del filesystem.
- Fechas en formato dd/mm/yyyy en la UI, ISO 8601 en la API.
- Montar el management command verificar_documentos como tarea diaria. Documentar en MIGRACION.md cómo configurarlo con cron: `0 8 * * * python manage.py verificar_documentos`
- registrar_log() en todas las acciones: subir, editar, eliminar, descargar, renovar.
- Todos los textos en español es-CL.
- Nunca usar fetch directo, siempre apiFetch.
- Composition API con <script setup>, nunca Options API.
- try/except en todas las vistas Django con respuestas JSON consistentes.
- Entregar cada archivo COMPLETO sin omitir código con "// resto igual".

---

## ARCHIVOS A ENTREGAR

1. models_patch.py — clase Documento completa
2. views_documentos_patch.py — todas las vistas nuevas (indicar que van en views.py y dónde insertar)
3. tasks_patch.py — función verificar_vencimientos() y management command (indicar ubicación exacta)
4. urls_patch.py — solo las rutas nuevas
5. Documentos.vue — completo
6. DocumentosBadge.vue — completo
7. router_patch.js — solo las rutas a agregar
8. nav_patch.md — instrucciones de qué línea agregar en el sidebar y dónde
9. MIGRACION.md — orden exacto: models → migrate → vistas → urls → frontend → cron