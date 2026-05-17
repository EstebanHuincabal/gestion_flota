Eres un desarrollador senior especializado en Django + Vue 3. Vas a implementar DOS cambios en un sistema de gestión de flota multiempresas. Lee TODO el contexto antes de escribir código.

---

## STACK TECNOLÓGICO
- Backend: Python / Django 5.x + Django REST Framework
- Frontend: Vue.js 3 (Composition API) + Vite
- Base de datos: SQLite3 (desarrollo)
- CSS: TailwindCSS 4.x
- Autenticación: Sesiones Django con backend RUT personalizado
- Cifrado: Fernet para datos sensibles
- Auditoría: registrar_log() en audit.py
- Notificaciones: notificar() y notificar_admins_empresa() en notificaciones.py
- apiFetch() centralizado en utils/api.js con CSRF automático
- Puertos: backend :8000 / frontend :7183

---

## ROLES DEL SISTEMA
- SUPERADMIN: administra todo, sin restricciones de plan
- USUARIO: administrador de una empresa contratante
- CONDUCTOR: rol operativo sin login activo

---

## ESTRUCTURA DE ARCHIVOS EXISTENTE
gestion_backend/g_de_flota/
├── models.py          ← modelos ORM (20+ modelos)
├── views.py           ← 40+ endpoints REST existentes
├── views_planes.py    ← vistas del módulo de planes (YA EXISTE)
├── serializers.py
├── audit.py           ← registrar_log()
├── notificaciones.py  ← notificar(), notificar_admins_empresa()
├── utils.py           ← cifrado Fernet
├── backends.py
└── middleware.py

REGLA CRÍTICA: NO crear nuevos archivos views_*.py.
- Todo lo del módulo de planes va en views_planes.py (ya existe)
- Todo lo demás va en views.py (ya existe)
- Indicar exactamente en qué archivo va cada función y dónde insertarla

---

## MODELOS RELEVANTES

### PlanSuscripcion
```python
class PlanSuscripcion(models.Model):
    nombre          = models.CharField(max_length=50, choices=[('basico','Básico'),('pro','Pro'),('enterprise','Enterprise')], unique=True)
    descripcion     = models.CharField(max_length=200, blank=True, default='')
    precio_mensual  = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    precio_anual    = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    max_flotas      = models.PositiveIntegerField(default=1)
    max_vehiculos   = models.PositiveIntegerField(default=5)
    max_conductores = models.PositiveIntegerField(default=10)
    max_usuarios    = models.PositiveIntegerField(default=3)
    modulos         = models.JSONField(default=list)
    activo          = models.BooleanField(default=True)
    orden           = models.PositiveSmallIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
```

### Empresa
```python
class Empresa(models.Model):
    nombre  = models.CharField(max_length=200)
    estado  = models.CharField(choices=[('activa','Activa'),('suspendida','Suspendida')])
    plan    = models.ForeignKey(PlanSuscripcion, null=True, blank=True, on_delete=models.SET_NULL)
```

### Usuario
```python
class Usuario(models.Model):
    rol      = models.CharField(choices=['SUPERADMIN','USUARIO','CONDUCTOR'])
    empresa  = models.ForeignKey(Empresa, null=True, blank=True)
    permisos = models.ManyToManyField('Permiso')
    is_active = models.BooleanField(default=True)
```

### Permiso
```python
class Permiso(models.Model):
    codigo    = models.CharField(max_length=100, unique=True)
    nombre    = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    # Categorías: flotas, vehiculos, conductores, mantenciones, usuarios, documentos, predictivo, dashboard
```

### Flota / Vehiculo
```python
class Flota(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

class Vehiculo(models.Model):
    flota  = models.ForeignKey(Flota, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)
```

---

## ENDPOINTS EXISTENTES RELEVANTES
POST   /api/login/                    ← login por RUT — MODIFICAR respuesta
GET    /api/empresa/flotas/           ← listar flotas
POST   /api/empresa/flotas/           ← crear flota — AGREGAR enforcement
POST   /api/empresa/vehiculos/        ← crear vehículo — AGREGAR enforcement
POST   /api/empresa/conductores/      ← crear conductor — AGREGAR enforcement
POST   /api/usuarios/crear/           ← crear usuario — AGREGAR enforcement
GET/PUT /api/usuarios/:id/permisos/   ← ver/editar permisos — MODIFICAR GET
GET    /api/permisos/                 ← listar permisos disponibles

Todos en views.py. Los de planes están en views_planes.py:
GET/POST        /api/configuracion/planes/
GET/PUT/DELETE  /api/configuracion/planes/:id/
POST            /api/configuracion/planes/:id/asignar/
GET             /api/empresa/plan-uso/   ← ya declarado, completar implementación

---

## CAMBIO 1 — REDISEÑO DE GESTIÓN DE PERMISOS (dos capas)

### Concepto central
Los permisos tienen DOS capas:
- Capa 1 (Plan): define qué MÓDULOS puede usar la empresa. No se edita aquí.
- Capa 2 (Usuario): dentro de los módulos habilitados, qué acciones puede hacer cada usuario.

### ARCHIVO: views.py — modificar GET de la vista de permisos de usuario

Buscar la vista que maneja GET /api/usuarios/:id/permisos/ y agregar en su respuesta:

```python
# Agregar al dict de respuesta existente:
plan_modulos = []
plan_nombre  = ''
if usuario.empresa and usuario.empresa.plan:
    plan_modulos = usuario.empresa.plan.modulos or []
    plan_nombre  = usuario.empresa.plan.get_nombre_display()

# En el return JsonResponse agregar:
'plan_modulos': plan_modulos,
'plan_nombre':  plan_nombre,
```

### ARCHIVO: views.py — modificar POST /api/login/

Buscar la vista de login y agregar en la respuesta de login exitoso:

```python
plan_modulos = []
plan_nombre  = ''
if user.empresa and user.empresa.plan:
    plan_modulos = user.empresa.plan.modulos or []
    plan_nombre  = user.empresa.plan.get_nombre_display()

# En el return JsonResponse del login exitoso agregar:
'plan_modulos': plan_modulos,
'plan_nombre':  plan_nombre,
```

### ARCHIVO: views_planes.py — completar PlanUsageView

La vista GET /api/empresa/plan-uso/ ya está declarada. Implementarla completamente:

```python
# Retornar:
{
    "plan": { ...campos del plan... },
    "uso": {
        "flotas":      { "actual": N, "limite": N, "pct": N },
        "vehiculos":   { "actual": N, "limite": N, "pct": N },
        "conductores": { "actual": N, "limite": N, "pct": N },
        "usuarios":    { "actual": N, "limite": N, "pct": N }
    },
    "alertas": [
        # Solo dimensiones con pct >= 80
        { "dimension": "vehiculos", "actual": 9, "limite": 10, "pct": 90, "nivel": "warning" }
        # nivel: "warning" si 80<=pct<100 | "danger" si pct>=100
    ]
}
```

---

## CAMBIO 2 — VALIDACIONES DE CAPACIDAD POR PLAN CON ALERTAS

### ARCHIVO: views_planes.py — agregar función helper verificar_limite_plan()

Agregar al inicio de views_planes.py (antes de las clases de vistas), después de los imports:

```python
def verificar_limite_plan(empresa, dimension):
    """
    Verifica si la empresa puede crear un nuevo recurso.
    dimension: 'flotas' | 'vehiculos' | 'conductores' | 'usuarios'
    Retorna: (puede: bool, error_response: JsonResponse | None, uso: int, limite: int, pct: int)
    Si puede crear → retorna (True, None, uso, limite, pct)
    Si no puede    → retorna (False, JsonResponse(403), uso, limite, pct)
    """
    if not empresa.plan:
        resp = JsonResponse({
            'error': 'La empresa no tiene un plan asignado. Contacta al administrador.',
            'codigo': 'SIN_PLAN',
        }, status=403)
        return False, resp, 0, 0, 0

    plan = empresa.plan

    conteos = {
        'flotas':      (Flota.objects.filter(empresa=empresa).count(),
                        plan.max_flotas),
        'vehiculos':   (Vehiculo.objects.filter(flota__empresa=empresa, activo=True).count(),
                        plan.max_vehiculos),
        'conductores': (Usuario.objects.filter(empresa=empresa, rol='CONDUCTOR', is_active=True).count(),
                        plan.max_conductores),
        'usuarios':    (Usuario.objects.filter(empresa=empresa, is_active=True).exclude(rol='CONDUCTOR').count(),
                        plan.max_usuarios),
    }

    uso, limite = conteos.get(dimension, (0, 0))
    pct = round((uso / limite * 100) if limite > 0 else 0)

    if uso >= limite:
        # Notificar UNA SOLA VEZ: solo si no hay notificación no leída del mismo tipo y dimensión
        ya_notificado = Notificacion.objects.filter(
            tipo='LIMITE_PLAN_ALCANZADO',
            leida=False,
            extra__dimension=dimension,
            usuario__empresa=empresa,
        ).exists()

        if not ya_notificado:
            notificar_admins_empresa(
                empresa=empresa,
                tipo='LIMITE_PLAN_ALCANZADO',
                titulo=f'Límite de {dimension} alcanzado',
                mensaje=(f'Tu empresa ha alcanzado el límite de {limite} {dimension} '
                         f'del plan {plan.get_nombre_display()}. '
                         f'Contacta al administrador para ampliar tu plan.'),
                extra={'dimension': dimension, 'uso': uso, 'limite': limite},
            )

        resp = JsonResponse({
            'error': (f'Has alcanzado el límite de {limite} {dimension} '
                      f'de tu plan {plan.get_nombre_display()}. '
                      f'Contacta al administrador para actualizar el plan.'),
            'codigo':     'LIMITE_PLAN',
            'dimension':  dimension,
            'uso':        uso,
            'limite':     limite,
            'porcentaje': pct,
            'plan':       plan.get_nombre_display(),
        }, status=403)
        return False, resp, uso, limite, pct

    return True, None, uso, limite, pct
```

### ARCHIVO: views.py — enforcement en las 4 vistas de creación

Para cada vista POST indicada, agregar al inicio del método (después de validar autenticación, antes de procesar el body):

#### Crear flota (POST /api/empresa/flotas/)
```python
# Insertar al inicio del método post(), después de obtener empresa:
puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'flotas')
if not puede:
    return error_resp
```

#### Crear vehículo (POST /api/empresa/vehiculos/)
```python
puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'vehiculos')
if not puede:
    return error_resp
```

#### Crear conductor (POST /api/empresa/conductores/)
```python
puede, error_resp, _, _, _ = verificar_limite_plan(empresa, 'conductores')
if not puede:
    return error_resp
```

#### Crear usuario (POST /api/usuarios/crear/)
```python
# Solo aplicar cuando el usuario creado tiene empresa asignada:
empresa_destino = Empresa.objects.get(id=body.get('empresa_id')) if body.get('empresa_id') else None
if empresa_destino:
    puede, error_resp, _, _, _ = verificar_limite_plan(empresa_destino, 'usuarios')
    if not puede:
        return error_resp
```

IMPORTANTE: verificar_limite_plan está en views_planes.py.
En views.py agregar al inicio del archivo:
```python
from .views_planes import verificar_limite_plan
```

---

## ARCHIVOS FRONTEND A ENTREGAR

### 1. GestionPermisos.vue — COMPLETO, reescrito

Layout de dos columnas:
- Izquierda (220px fija): lista de usuarios con buscador, avatar iniciales, nombre, empresa, badge contador. Selección activa resaltada.
- Derecha: panel del usuario seleccionado

Panel derecho contiene en orden:
1. Header con avatar grande, nombre, email, empresa, badge "N/M permisos activos"
2. Banner de plan: nombre del plan en pill morada, pastillas verdes para módulos incluidos y grises tachadas para los no incluidos, botón "Ver plan" → /planes
3. Barra rápida: "Seleccionar todos" / "Deseleccionar todos" + leyenda "Los módulos bloqueados requieren un plan superior" con ícono candado
4. Grid 3 columnas de tarjetas de permisos
5. Footer con "Cancelar" y "Guardar permisos"

Tarjetas de permisos:
- MÓDULO INCLUIDO en el plan: tarjeta interactiva normal, checkboxes funcionales, checkbox maestro de categoría
- MÓDULO NO INCLUIDO: tarjeta con opacity:0.5, pointer-events:none, badge con plan mínimo requerido
- Badge "N/M" morado si N===M, gris si N<M
- Checkbox maestro sincronizado con los individuales (indeterminate si parcial)

Plan mínimo requerido por módulo (para el badge de bloqueo):
- flotas, vehiculos, conductores, mantenciones, documentos, dashboard, usuarios → Básico
- mantencion_predictiva, notificaciones_avanzadas → Pro
- gps, geofencing, reportes, exportacion, api_access → Enterprise

Al cargar: GET /api/usuarios/:id/permisos/ → usa plan_modulos de la respuesta para determinar tarjetas bloqueadas.
Al guardar: PUT /api/usuarios/:id/permisos/ con solo los permisos de módulos desbloqueados.

### 2. LimitePlanModal.vue — COMPLETO, nuevo

Ubicación: src/web/planes/LimitePlanModal.vue

- Teleport to="body"
- Se activa con window.addEventListener('limite-plan', handler) en onMounted
- Se desactiva en onUnmounted

Contenido del modal:
- Ícono candado en círculo con fondo warning
- Título: "Límite del plan alcanzado"
- Mensaje: event.detail.error (texto del backend)
- Barra de progreso: muestra uso/limite con color según pct (verde <80, naranja 80-99, rojo 100)
  Ejemplo: [████████████] 10 / 10 vehículos
- Badge con nombre del plan actual: event.detail.plan
- Párrafo: "Contacta al administrador de tu sistema para actualizar el plan."
- Botón "Entendido" → cierra modal

SIN botón "Ver planes" (el rol USUARIO no administra planes).

### 3. PlanUsageBanner.vue — COMPLETO, nuevo

Ubicación: src/web/empresa/PlanUsageBanner.vue

- onMounted: GET /api/empresa/plan-uso/, fail-silent (try/catch sin mostrar error)
- No montar si usuario es SUPERADMIN (verificar sessionStorage)
- setInterval cada 5 minutos para refrescar
- clearInterval en onUnmounted
- Solo visible si alertas.length > 0

Una fila por alerta:
[ícono]  Vehículos: 9 de 10 usados   [barra progreso inline]   [pill "90%"]
- Fondo: naranja claro si warning (80-99%), rojo claro si danger (100%)
- Barra de progreso: div con width dinámico según pct
- Al hacer clic expande un panel con las 4 dimensiones completas (aunque no tengan alerta)

Panel expandido al hacer clic:
Flotas:      3 / 10   [███░░░░░░░]  30%
Vehículos:   9 / 10   [█████████░]  90%  ← naranja
Conductores: 5 / 80   [█░░░░░░░░░]   6%
Usuarios:    2 / 999  [░░░░░░░░░░]   0%

### 4. permisos_js_patch.js

Solo estas dos funciones completas para reemplazar/agregar en utils/permisos.js:

```javascript
// REEMPLAZAR tienePermiso existente:
export function tienePermiso(codigo) {
  // SUPERADMIN tiene acceso total
  const user = JSON.parse(sessionStorage.getItem('usuario') || '{}')
  if (user.rol === 'SUPERADMIN') return true

  // Verificar que el módulo esté en el plan (capa 1)
  const CATEGORIA_A_MODULO = {
    flotas:       'flotas',
    vehiculos:    'vehiculos',
    conductores:  'conductores',
    mantenciones: 'mantencion_correctiva',
    documentos:   'documentos',
    dashboard:    'dashboard',
    predictivo:   'mantencion_predictiva',
    gps:          'gps',
    reportes:     'reportes',
    usuarios:     null,  // siempre disponible para admin de empresa
  }
  const permisoData = JSON.parse(sessionStorage.getItem('permisos') || '[]')
  const permiso = permisoData.find(p => p.codigo === codigo)
  
  if (permiso) {
    const moduloRequerido = CATEGORIA_A_MODULO[permiso.categoria]
    if (moduloRequerido !== null && moduloRequerido !== undefined) {
      if (!tieneModulo(moduloRequerido)) return false
    }
  }

  // Verificar permiso individual (capa 2)
  return permisoData.some(p => p.codigo === codigo)
}

// AGREGAR función nueva:
export function tieneModulo(modulo) {
  const user = JSON.parse(sessionStorage.getItem('usuario') || '{}')
  if (user.rol === 'SUPERADMIN') return true
  const modulos = JSON.parse(sessionStorage.getItem('plan_modulos') || '[]')
  return modulos.includes(modulo)
}
```

### 5. api_js_patch.js

Solo el bloque a insertar en apiFetch, después del manejo de 401/403 existente:

```javascript
if (res.status === 403 && errorData.codigo === 'LIMITE_PLAN') {
  window.dispatchEvent(new CustomEvent('limite-plan', { detail: errorData }))
  throw new Error(errorData.error || 'Límite de plan alcanzado')
}
if (res.status === 403 && errorData.codigo === 'MODULO_NO_INCLUIDO') {
  window.dispatchEvent(new CustomEvent('modulo-bloqueado', { detail: errorData }))
  throw new Error(errorData.error || 'Módulo no disponible en tu plan')
}
```

### 6. login_vue_patch.js

Solo las líneas a agregar en el handler del login exitoso en login.vue:

```javascript
// Después de guardar los datos del usuario en sessionStorage (líneas existentes):
sessionStorage.setItem('plan_modulos', JSON.stringify(data.plan_modulos || []))
sessionStorage.setItem('plan_nombre', data.plan_nombre || '')
```

### 7. empresalayout_patch.vue

Solo el diff a aplicar en EmpresaLayout.vue:

```vue
<script setup>
// Agregar estos dos imports a los existentes:
import PlanUsageBanner from '@/web/empresa/PlanUsageBanner.vue'
import LimitePlanModal from '@/web/planes/LimitePlanModal.vue'
</script>

<template>
  <!-- Estructura existente del layout -->
  <!-- Agregar PlanUsageBanner justo después del navbar existente -->
  <PlanUsageBanner />
  
  <!-- router-view existente sin cambios -->
  <router-view />
  
  <!-- Agregar LimitePlanModal antes del cierre del template -->
  <LimitePlanModal />
</template>
```

---

## INSTRUCCIONES DE IMPLEMENTACIÓN (IMPLEMENTACION.md)

Entregar un archivo markdown con el orden exacto:

views_planes.py

Agregar import de Notificacion, notificar_admins_empresa al inicio
Agregar función verificar_limite_plan() antes de la primera clase
Completar implementación de PlanUsageView.get()


views.py

Agregar al inicio: from .views_planes import verificar_limite_plan
En la vista POST de flotas: agregar 2 líneas de enforcement
En la vista POST de vehículos: agregar 2 líneas de enforcement
En la vista POST de conductores: agregar 2 líneas de enforcement
En la vista POST de crear usuario: agregar 4 líneas de enforcement
En la vista GET de login: agregar plan_modulos y plan_nombre a la respuesta
En la vista GET de permisos de usuario: agregar plan_modulos y plan_nombre


Frontend

Reemplazar GestionPermisos.vue completo
Crear LimitePlanModal.vue en src/web/planes/
Crear PlanUsageBanner.vue en src/web/empresa/
Aplicar parche en utils/permisos.js (reemplazar tienePermiso, agregar tieneModulo)
Aplicar parche en utils/api.js (agregar 2 bloques if)
Aplicar parche en login.vue (2 líneas en el handler de login exitoso)
Aplicar parche en EmpresaLayout.vue (2 imports + 2 tags)




---

## CONVENCIONES OBLIGATORIAS
- Español es-CL en todos los textos de UI
- Nunca usar fetch directo, siempre apiFetch
- Composition API con <script setup>, nunca Options API
- try/except en todas las vistas Django
- CSRF en todas las mutaciones
- registrar_log() en acciones críticas
- Fail-silent en PlanUsageBanner (no romper layout si el endpoint falla)
- SUPERADMIN nunca ve el banner ni el modal de límite
- Entregar cada archivo COMPLETO, sin omitir código con "// resto igual"