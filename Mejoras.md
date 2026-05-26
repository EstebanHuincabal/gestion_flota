Vas a implementar el sistema de permisos por plan en la app móvil de conductores (Vue 3 + Capacitor) y ajustar el dashboard para que muestre solo lo que el plan permite.

---

## CONTEXTO

El sistema de permisos funciona así:
- El plan de la empresa define qué módulos están habilitados (campo modulos JSONField en PlanSuscripcion)
- El backend retorna plan_modulos en la respuesta del login
- La app guarda plan_modulos en @capacitor/preferences
- Cada vista verifica si su módulo está habilitado antes de mostrarse
- SUPERADMIN siempre tiene acceso total (no aplica en la app — solo conductores)

Módulos posibles que afectan la app del conductor:
- 'rutas'                  → pantalla Mis Rutas + tab en bottom nav
- 'mantencion_correctiva'  → solicitud de mantención en panel de solicitudes
- 'mantencion_predictiva'  → alertas de mantención en solicitudes
- 'documentos'             → pantalla Mis Documentos + solicitud de documento
- 'combustible'            → solicitud de combustible en solicitudes (GastoOperativo)
- 'finanzas'               → registro de gastos desde la app

---

## PARTE 1 — BACKEND

### Modificar vista de login (views.py)
Buscar la vista que maneja POST /api/login/ y agregar en la respuesta de login exitoso para conductores:

```python
plan_modulos = []
plan_nombre  = ''
if user.empresa and user.empresa.plan:
    plan_modulos = user.empresa.plan.modulos or []
    plan_nombre  = user.empresa.plan.get_nombre_display()

# Agregar al JsonResponse:
'plan_modulos': plan_modulos,
'plan_nombre':  plan_nombre,
```

### Modificar GET /api/conductor/rutas/ (views.py)
Si el plan no incluye 'rutas' → retornar 403:
```python
if 'rutas' not in request.user.empresa.plan.modulos:
    return JsonResponse({'error': 'Tu plan no incluye el módulo de rutas.'}, status=403)
```

### Modificar POST /api/conductor/solicitudes/ (views.py)
Validar que el tipo de solicitud esté permitido por el plan:

```python
MODULO_REQUERIDO = {
    'mantencion':  'mantencion_correctiva',
    'combustible': 'combustible',
    'documento':   'documentos',
    'incidencia':  None,  # siempre disponible
}
modulo = MODULO_REQUERIDO.get(tipo)
if modulo and modulo not in request.user.empresa.plan.modulos:
    return JsonResponse({
        'error': f'Tu plan no incluye este tipo de solicitud.',
        'codigo': 'MODULO_NO_INCLUIDO',
        'modulo': modulo,
    }, status=403)
```

### Modificar GET /api/conductor/documentos/ (views.py)
```python
if 'documentos' not in request.user.empresa.plan.modulos:
    return JsonResponse({'error': 'Tu plan no incluye el módulo de documentos.'}, status=403)
```

---

## PARTE 2 — SERVICIO DE PERMISOS EN LA APP

### Crear src/services/permisos.js (nuevo archivo)

```javascript
import { Preferences } from '@capacitor/preferences'

export async function cargarModulos() {
  const { value } = await Preferences.get({ key: 'plan_modulos' })
  return JSON.parse(value || '[]')
}

export async function tieneModulo(modulo) {
  const modulos = await cargarModulos()
  return modulos.includes(modulo)
}

export async function getModulos() {
  return await cargarModulos()
}
```

### Crear src/composables/usePermisos.js (nuevo archivo)
Composable reactivo para usar en cualquier componente Vue:

```javascript
import { ref, onMounted } from 'vue'
import { Preferences } from '@capacitor/preferences'

export function usePermisos() {
  const modulos    = ref([])
  const planNombre = ref('')
  const cargando   = ref(true)

  onMounted(async () => {
    const { value: m } = await Preferences.get({ key: 'plan_modulos' })
    const { value: p } = await Preferences.get({ key: 'plan_nombre' })
    modulos.value    = JSON.parse(m || '[]')
    planNombre.value = p || ''
    cargando.value   = false
  })

  function tieneModulo(modulo) {
    return modulos.value.includes(modulo)
  }

  return { modulos, planNombre, tieneModulo, cargando }
}
```

---

## PARTE 3 — GUARDAR MÓDULOS AL HACER LOGIN

### Modificar src/stores/auth.js
En la acción login(), después de guardar access_token, refresh_token y usuario, agregar:

```javascript
await Preferences.set({
  key: 'plan_modulos',
  value: JSON.stringify(data.plan_modulos || [])
})
await Preferences.set({
  key: 'plan_nombre',
  value: data.plan_nombre || ''
})
```

En la acción logout(), agregar:
```javascript
await Preferences.remove({ key: 'plan_modulos' })
await Preferences.remove({ key: 'plan_nombre' })
```

En la acción cargarSesion(), agregar:
```javascript
const { value: modulos } = await Preferences.get({ key: 'plan_modulos' })
// No necesita guardarse en el store — se lee directo desde Preferences cuando se necesita
```

---

## PARTE 4 — BOTTOM NAVIGATION

### Modificar src/components/BottomNav.vue
Usar usePermisos() para mostrar solo los tabs habilitados.

El tab "Rutas" solo aparece si tieneModulo('rutas').
El tab "Solicitudes" siempre aparece (incidencias no requieren módulo).
El tab "Ajustes" siempre aparece.

Si 'rutas' no está en el plan, la pantalla de inicio al abrir la app debe ser /solicitudes.

```vue
<script setup>
import { usePermisos } from '@/composables/usePermisos.js'
const { tieneModulo } = usePermisos()
</script>

<template>
  <nav class="fixed bottom-0 left-0 right-0 bg-white border-t"
       style="padding-bottom: env(safe-area-inset-bottom)">
    <div class="flex justify-around py-2">
      <button v-if="tieneModulo('rutas')"
        @click="router.push('/rutas')"
        :class="['nav-item', esActivo('/rutas') ? 'activo' : '']">
        <i class="ti ti-route text-xl"></i>
        <span>Rutas</span>
      </button>
      <button @click="router.push('/solicitudes')"
        :class="['nav-item', esActivo('/solicitudes') ? 'activo' : '']">
        <i class="ti ti-bell text-xl"></i>
        <span>Solicitudes</span>
      </button>
      <button @click="router.push('/ajustes')"
        :class="['nav-item', esActivo('/ajustes') ? 'activo' : '']">
        <i class="ti ti-settings text-xl"></i>
        <span>Ajustes</span>
      </button>
    </div>
  </nav>
</template>
```

---

## PARTE 5 — ROUTER GUARD

### Modificar src/router/index.js
Agregar meta con el módulo requerido en las rutas protegidas:

```javascript
const routes = [
  { path: '/login',       component: () => import('@/views/Login.vue'),       meta: { publica: true } },
  { path: '/onboarding',  component: () => import('@/views/Onboarding/SubirDocumentos.vue'), meta: { requiereAuth: true } },
  {
    path: '/rutas',
    component: () => import('@/views/Rutas/ListaRutas.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' }
  },
  {
    path: '/rutas/:id',
    component: () => import('@/views/Rutas/DetalleRuta.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' }
  },
  {
    path: '/rutas/:id/checklist',
    component: () => import('@/views/Rutas/ChecklistPreviaje.vue'),
    meta: { requiereAuth: true, modulo: 'rutas' }
  },
  {
    path: '/documentos',
    component: () => import('@/views/Documentos/MisDocumentos.vue'),
    meta: { requiereAuth: true, modulo: 'documentos' }
  },
  { path: '/solicitudes', component: () => import('@/views/Solicitudes/ListaSolicitudes.vue'), meta: { requiereAuth: true } },
  { path: '/ajustes',     component: () => import('@/views/Ajustes/Ajustes.vue'),             meta: { requiereAuth: true } },
]

router.beforeEach(async (to) => {
  const { value: token   } = await Preferences.get({ key: 'access_token' })
  const { value: modulos } = await Preferences.get({ key: 'plan_modulos' })
  const modulosArray = JSON.parse(modulos || '[]')

  if (!to.meta.publica && !token) return '/login'
  if (to.path === '/login' && token) {
    // Redirigir a la pantalla correcta según el plan
    return modulosArray.includes('rutas') ? '/rutas' : '/solicitudes'
  }

  // Verificar módulo requerido
  if (to.meta.modulo && !modulosArray.includes(to.meta.modulo)) {
    return '/modulo-no-disponible'
  }
})
```

Agregar ruta para módulo no disponible:
```javascript
{
  path: '/modulo-no-disponible',
  component: () => import('@/views/ModuloNoDisponible.vue'),
  meta: { requiereAuth: true }
}
```

---

## PARTE 6 — VISTA ModuloNoDisponible.vue (crear)

Pantalla simple que se muestra cuando el conductor intenta acceder a un módulo que su plan no incluye:

```vue
<template>
  <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; padding:24px; text-align:center;">
    <div style="width:64px; height:64px; border-radius:50%; background:var(--color-background-secondary); display:flex; align-items:center; justify-content:center; margin-bottom:16px;">
      <i class="ti ti-lock" style="font-size:28px; color:var(--color-text-tertiary);"></i>
    </div>
    <p style="font-size:17px; font-weight:500; margin:0 0 8px; color:var(--color-text-primary);">
      Módulo no disponible
    </p>
    <p style="font-size:14px; color:var(--color-text-secondary); margin:0 0 24px; max-width:260px; line-height:1.5;">
      Tu empresa no tiene acceso a este módulo en el plan actual.
      Contacta al administrador para más información.
    </p>
    <p style="font-size:12px; color:var(--color-text-tertiary); margin:0 0 24px;">
      Plan actual: <strong>{{ planNombre || '—' }}</strong>
    </p>
    <button @click="router.back()"
      style="padding:12px 24px; border-radius:12px; background:var(--color-background-secondary); border:0.5px solid var(--color-border-secondary); font-size:14px; cursor:pointer; color:var(--color-text-primary);">
      Volver
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Preferences } from '@capacitor/preferences'

const router     = useRouter()
const planNombre = ref('')

onMounted(async () => {
  const { value } = await Preferences.get({ key: 'plan_nombre' })
  planNombre.value = value || ''
})
</script>
```

---

## PARTE 7 — PANEL DE SOLICITUDES (filtrar por módulo)

### Modificar src/views/Solicitudes/ListaSolicitudes.vue
El grid de tipos de solicitud debe mostrar solo los habilitados por el plan.

```vue
<script setup>
import { usePermisos } from '@/composables/usePermisos.js'
const { tieneModulo } = usePermisos()

const TIPOS_SOLICITUD = [
  {
    value:    'mantencion',
    label:    'Mantención',
    icono:    'ti-tool',
    color:    '#534AB7',
    bg:       '#EEEDFE',
    modulo:   'mantencion_correctiva',
    desc:     'Falla mecánica o revisión',
  },
  {
    value:    'combustible',
    label:    'Combustible',
    icono:    'ti-gas-station',
    color:    '#B45309',
    bg:       '#FEF3C7',
    modulo:   'combustible',
    desc:     'Solicitar recarga',
  },
  {
    value:    'incidencia',
    label:    'Incidencia',
    icono:    'ti-alert-triangle',
    color:    '#A32D2D',
    bg:       '#FCEBEB',
    modulo:   null,  // siempre disponible
    desc:     'Accidente u otro problema',
  },
  {
    value:    'documento',
    label:    'Documento',
    icono:    'ti-file-plus',
    color:    '#16A34A',
    bg:       '#DCFCE7',
    modulo:   'documentos',
    desc:     'Subir o renovar documento',
  },
]

// Solo mostrar tipos habilitados por el plan
const tiposDisponibles = computed(() =>
  TIPOS_SOLICITUD.filter(t => !t.modulo || tieneModulo(t.modulo))
)
</script>

<template>
  <!-- Reemplazar el grid estático por: -->
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:16px;">
    <div
      v-for="tipo in tiposDisponibles"
      :key="tipo.value"
      @click="seleccionarTipo(tipo)"
      style="...estilos existentes..."
    >
      <!-- card del tipo -->
    </div>
  </div>

  <!-- Si solo hay un tipo disponible, mostrar en columna completa -->
  <!-- Si no hay ninguno disponible, mostrar mensaje -->
  <div v-if="tiposDisponibles.length === 0"
    style="text-align:center; padding:24px; color:var(--color-text-secondary);">
    <i class="ti ti-clipboard-off" style="font-size:28px; display:block; margin-bottom:8px;"></i>
    <p style="font-size:13px; margin:0;">No hay tipos de solicitud disponibles en tu plan.</p>
  </div>
</template>
```

---

## PARTE 8 — PANTALLA INICIO SEGÚN PLAN

### Modificar src/views/Rutas/ListaRutas.vue
Si el módulo de rutas no está disponible y el conductor llega a esta pantalla
(por si acaso el guard falla), mostrar la pantalla de módulo no disponible inline:

```vue
<script setup>
import { usePermisos } from '@/composables/usePermisos.js'
const { tieneModulo, cargando } = usePermisos()
</script>

<template>
  <div v-if="cargando"><!-- skeleton --></div>
  <div v-else-if="!tieneModulo('rutas')">
    <!-- Redirigir al router guard — esto es solo fallback -->
    <p style="padding:24px; color:var(--color-text-secondary);">Redirigiendo...</p>
  </div>
  <div v-else>
    <!-- Contenido normal de ListaRutas -->
  </div>
</template>
```

---

## PARTE 9 — AJUSTES: mostrar plan actual

### Modificar src/views/Ajustes/Ajustes.vue
Agregar en la sección "Mi cuenta" el plan actual con sus módulos:

```vue
<script setup>
import { usePermisos } from '@/composables/usePermisos.js'
const { modulos, planNombre } = usePermisos()

const MODULO_LABELS = {
  rutas:                 'Rutas y trabajos',
  mantencion_correctiva: 'Mantención',
  mantencion_predictiva: 'Mantención predictiva',
  documentos:            'Documentos',
  combustible:           'Combustible',
  finanzas:              'Finanzas',
}
</script>

<template>
  <!-- Agregar esta sección en Ajustes, después del perfil: -->
  <p class="section-label">Plan de la empresa</p>
  <div style="background:var(--color-background-secondary); border-radius:12px; padding:12px 14px; margin-bottom:16px;">
    <p style="font-size:13px; font-weight:500; margin:0 0 8px; color:var(--color-text-primary);">
      {{ planNombre || 'Sin plan asignado' }}
    </p>
    <div style="display:flex; flex-wrap:wrap; gap:6px;">
      <span
        v-for="mod in modulos"
        :key="mod"
        style="font-size:11px; padding:2px 8px; border-radius:99px; background:#E1F5EE; color:#085041;"
      >
        {{ MODULO_LABELS[mod] || mod }}
      </span>
      <span v-if="modulos.length === 0"
        style="font-size:12px; color:var(--color-text-tertiary);">
        Sin módulos activos
      </span>
    </div>
  </div>
</template>
```

---

## CONVENCIONES
- Composition API <script setup> siempre
- Nunca localStorage — siempre @capacitor/preferences
- El guard del router es la primera línea de defensa — las vistas tienen solo fallback visual
- Si tieneModulo() devuelve false para una ruta → redirigir a /modulo-no-disponible
- Los módulos se leen de Preferences, no del store — son datos persistentes del dispositivo
- Textos en español
- Sin "// resto igual"

---

## ARCHIVOS A ENTREGAR

Backend:
1. views_login_patch.py — solo las líneas a agregar en la respuesta del login
2. views_solicitudes_patch.py — solo la validación de módulo en POST /api/conductor/solicitudes/
3. views_documentos_patch.py — solo la validación en GET /api/conductor/documentos/
4. views_rutas_patch.py — solo la validación en GET /api/conductor/rutas/

Frontend:
5. src/services/permisos.js — completo
6. src/composables/usePermisos.js — completo
7. src/stores/auth_patch.js — solo las líneas a agregar en login() y logout()
8. src/router/index_patch.js — router completo con guards y meta modulos
9. src/components/BottomNav.vue — completo reescrito
10. src/views/ModuloNoDisponible.vue — completo
11. src/views/Solicitudes/solicitudes_patch.vue — solo el grid de tipos modificado
12. src/views/Ajustes/ajustes_patch.vue — solo la sección de plan a agregar
13. src/views/Rutas/listarutas_patch.vue — solo el v-if de módulo

Sin "# resto igual".