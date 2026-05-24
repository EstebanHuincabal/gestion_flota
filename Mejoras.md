Vas a implementar la pantalla de Login para la app móvil de conductores construida con Vue 3 + Capacitor.

---

## CONTEXTO DE LA APP

- Stack: Vue 3 Composition API + Vite + TailwindCSS 4 + Capacitor
- Estado global: Pinia
- Navegación: Vue Router
- La app es SOLO para conductores (rol='CONDUCTOR')
- El backend es Django con autenticación JWT (mismo backend del sistema web)
- Puerto backend desarrollo: http://localhost:8000
- Los datos sensibles (nombre, RUT) vienen cifrados con Fernet — el backend los descifra y retorna en texto plano en la respuesta del login

---

## FLUJO DE LOGIN

1. Conductor ingresa RUT y contraseña
2. POST /api/login/ con { rut, password }
3. Backend retorna:
```json
{
  "access": "jwt_token",
  "refresh": "refresh_token",
  "usuario": {
    "id": 1,
    "nombre": "Juan Muñoz",
    "email": "juan@email.com",
    "rol": "CONDUCTOR",
    "primer_login": true,
    "empresa": { "id": 1, "nombre": "Transportes del Norte" },
    "vehiculo_asignado": { "id": 3, "patente": "PPU-4421", "marca": "Mercedes", "modelo": "Actros" }
  }
}
```
4. Si primer_login === true → navegar a /onboarding
5. Si primer_login === false → navegar a /rutas (pantalla principal)
6. Si el rol no es 'CONDUCTOR' → mostrar error "Esta app es solo para conductores"

---

## ALMACENAMIENTO DE TOKENS

Usar @capacitor/preferences (NO localStorage ni sessionStorage — no son confiables en Capacitor):

```javascript
import { Preferences } from '@capacitor/preferences'

// Guardar
await Preferences.set({ key: 'access_token', value: token })
await Preferences.set({ key: 'refresh_token', value: refreshToken })
await Preferences.set({ key: 'usuario', value: JSON.stringify(usuario) })

// Leer
const { value } = await Preferences.get({ key: 'access_token' })

// Eliminar (logout)
await Preferences.remove({ key: 'access_token' })
```

---

## ARCHIVOS A CREAR

### 1. src/services/api.js
Servicio centralizado de HTTP. Todas las llamadas al backend pasan por aquí.

```javascript
import { Preferences } from '@capacitor/preferences'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function apiFetch(url, options = {}) {
  const { value: token } = await Preferences.get({ key: 'access_token' })

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(`${BASE_URL}${url}`, { ...options, headers })

  if (res.status === 401) {
    // Intentar refresh automático
    const refreshed = await intentarRefresh()
    if (refreshed) {
      // Reintentar la llamada original con el nuevo token
      const { value: newToken } = await Preferences.get({ key: 'access_token' })
      const retryRes = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers: { ...headers, Authorization: `Bearer ${newToken}` },
      })
      if (!retryRes.ok) throw new Error('Sesión expirada')
      return retryRes.json()
    }
    // Refresh falló — limpiar sesión
    await limpiarSesion()
    throw new Error('SESION_EXPIRADA')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.error || error.detail || 'Error del servidor')
  }

  return res.json()
}

async function intentarRefresh() {
  try {
    const { value: refresh } = await Preferences.get({ key: 'refresh_token' })
    if (!refresh) return false
    const res = await fetch(`${BASE_URL}/api/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
    await Preferences.set({ key: 'access_token', value: data.access })
    return true
  } catch {
    return false
  }
}

export async function limpiarSesion() {
  await Preferences.remove({ key: 'access_token' })
  await Preferences.remove({ key: 'refresh_token' })
  await Preferences.remove({ key: 'usuario' })
}
```

### 2. src/stores/auth.js
Store Pinia de autenticación.

Estado:
- usuario: null | objeto usuario
- cargando: false
- error: null

Acciones:
- login(rut, password): llama POST /api/login/, guarda tokens y usuario en Preferences, retorna { success, primerLogin }
- logout(): limpia Preferences y resetea estado
- cargarSesion(): al iniciar la app, lee Preferences y restaura el estado si hay sesión guardada
- get estaAutenticado(): boolean
- get esConductor(): boolean

### 3. src/views/Login.vue
Pantalla de login completa.

DISEÑO:
- Fondo con color de acento suave (usando variable CSS --color-acento, default #534AB7)
- Logo o ícono de la app centrado arriba (ti-truck grande)
- Nombre de la app: "Conductor" en texto blanco grande
- Card blanca redondeada (border-radius 20px) en la parte inferior
  que ocupa 60% de la pantalla
- Dentro del card:
  - Título "Iniciar sesión"
  - Input RUT con formato automático (12.345.678-9 mientras escribe)
  - Input contraseña con toggle mostrar/ocultar (ícono ti-eye / ti-eye-off)
  - Mensaje de error en rojo si falla
  - Botón "Ingresar" grande con color de acento
  - Loading spinner dentro del botón mientras carga

FORMATO DE RUT:
```javascript
function formatearRut(valor) {
  // Eliminar todo excepto números y K
  let rut = valor.replace(/[^0-9kK]/g, '').toUpperCase()
  if (rut.length < 2) return rut
  // Separar dígito verificador
  const dv = rut.slice(-1)
  let cuerpo = rut.slice(0, -1)
  // Agregar puntos cada 3 dígitos
  cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${dv}`
}
```

VALIDACIONES FRONTEND:
- RUT no puede estar vacío
- Contraseña mínimo 4 caracteres
- Mostrar errores bajo cada campo

COMPORTAMIENTO:
- Al montar: verificar si ya hay sesión guardada con cargarSesion()
  Si hay sesión válida → redirigir directo sin mostrar el login
- Al hacer submit: llamar store.login(rut, password)
  Si éxito y primerLogin → router.push('/onboarding')
  Si éxito y no primerLogin → router.push('/rutas')
  Si error → mostrar mensaje bajo el formulario
- Teclado numérico para el campo RUT (inputmode="numeric")
- Al presionar "Siguiente" en el teclado del RUT → focus al campo contraseña
- Al presionar "Enter/Listo" en contraseña → submit del formulario
- Botón deshabilitado mientras carga

### 4. src/router/index.js
Configuración completa del router con guards de navegación.

Rutas:
```javascript
const routes = [
  { path: '/',           redirect: '/login' },
  { path: '/login',      component: () => import('@/views/Login.vue'),      meta: { publica: true } },
  { path: '/onboarding', component: () => import('@/views/Onboarding/SubirDocumentos.vue'), meta: { requiereAuth: true } },
  { path: '/rutas',      component: () => import('@/views/Rutas/ListaRutas.vue'),           meta: { requiereAuth: true } },
  { path: '/rutas/:id',  component: () => import('@/views/Rutas/DetalleRuta.vue'),          meta: { requiereAuth: true } },
  { path: '/solicitudes',component: () => import('@/views/Solicitudes/ListaSolicitudes.vue'),meta: { requiereAuth: true } },
  { path: '/ajustes',    component: () => import('@/views/Ajustes/Ajustes.vue'),            meta: { requiereAuth: true } },
]
```

Guard de navegación:
- Si la ruta requiere auth y no hay sesión → redirigir a /login
- Si la ruta es /login y ya hay sesión → redirigir a /rutas
- El guard lee la sesión desde el store de auth (cargarSesion si no está cargado)

### 5. src/App.vue
Componente raíz limpio.
- Cargar el tema guardado en Preferences al montar (color acento + modo oscuro/claro)
- Aplicar tema al :root con CSS variables
- Solo mostrar <router-view />

### 6. .env
VITE_API_URL=http://localhost:8000

### 7. src/assets/main.css
```css
@import "tailwindcss";

:root {
  --color-acento: #534AB7;
  --color-acento-suave: #EEEDFE;
}

* { -webkit-tap-highlight-color: transparent; }

input, button { outline: none; }

body {
  overscroll-behavior: none;
  user-select: none;
  -webkit-user-select: none;
}
```

---

## VISTAS VACÍAS A CREAR (solo el archivo, sin lógica aún)

Crear estos archivos con un template mínimo para que el router no rompa:
- src/views/Onboarding/SubirDocumentos.vue
- src/views/Rutas/ListaRutas.vue
- src/views/Rutas/DetalleRuta.vue
- src/views/Solicitudes/ListaSolicitudes.vue
- src/views/Ajustes/Ajustes.vue

Cada uno con:
```vue
<template>
  <div class="p-4">
    <p>{{ nombre de la vista }}</p>
  </div>
</template>

<script setup>
</script>
```

---

## CONVENCIONES

- Composition API con <script setup> siempre
- Nunca usar localStorage ni sessionStorage — siempre @capacitor/preferences
- Nunca usar fetch directo — siempre apiFetch de services/api.js
- Todos los textos en español
- El RUT se envía al backend normalizado (sin puntos, con guión): "12345678-9"
- Manejar siempre el caso de red caída con mensaje amigable: "Sin conexión. Verifica tu red."
- El botón de submit nunca debe quedar en estado de carga si hay error — resetear cargando a false en el catch

---

## ARCHIVOS A ENTREGAR

1. src/services/api.js — completo
2. src/stores/auth.js — completo
3. src/views/Login.vue — completo
4. src/router/index.js — completo
5. src/App.vue — completo
6. src/assets/main.css — completo
7. .env — completo
8. Las 5 vistas vacías

Cada archivo completo. Sin "// resto igual".