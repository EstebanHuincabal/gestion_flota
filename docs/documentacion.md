# Documentación General: Gestión de Flota

¡Bienvenido/a al proyecto de **Gestión de Flota**! Esta guía está diseñada para brindarte una introducción rápida, clara y profesional sobre la estructura, tecnologías y funcionamiento principal del sistema. Si acabas de unirte al equipo, este es el lugar ideal para empezar.

## 📌 1. Visión General
Este sistema está diseñado para administrar de manera eficiente la flota de vehículos, conductores, asignaciones y mantenimientos de múltiples empresas. Funciona a través de un modelo de subscripciones, gestionado por un "Superadmin", donde cada empresa tiene su propio panel aislado.

## 🏗️ 2. Arquitectura y Tecnologías
El sistema utiliza una arquitectura **desacoplada**, separando completamente el frontend del backend.

*   **Frontend (La interfaz de usuario):**
    *   **Vue.js 3:** Usando la moderna Composition API.
    *   **Vite:** Herramienta de compilación ultra rápida.
    *   **TailwindCSS:** Para un diseño rápido y responsivo.
    *   **Vue Router:** Para la navegación interna.
    *   **Chart.js:** Para la visualización de datos estadísticos.

*   **Backend (El motor y la API):**
    *   **Python con Django 5.x:** Framework principal robusto y seguro.
    *   **Django REST Framework (DRF):** Para construir la API RESTful que comunica los datos con el frontend.
    *   **Base de Datos:** SQLite (actualmente configurado para el entorno de desarrollo).

## 📁 3. Estructura del Proyecto

El repositorio principal está dividido en dos grandes bloques:

```text
gestion-de-flota/
├── gestion-frontend/    <-- Todo el código de Vue.js (Interfaz visual)
│   ├── src/             <-- Código fuente principal
│   │   ├── components/  <-- Componentes reutilizables (Botones, Modales, etc.)
│   │   ├── router/      <-- Configuración de rutas
│   │   ├── utils/       <-- Funciones auxiliares (Llamadas a la API, validaciones)
│   │   └── web/         <-- Vistas principales de la aplicación (Páginas)
│   └── package.json     <-- Dependencias de Node.js
│
├── gestion_backend/     <-- Todo el código de Python/Django (Lógica y BD)
│   ├── g_de_flota/      <-- La "App" principal de Django
│   │   ├── models.py    <-- Definición de las tablas de la base de datos
│   │   ├── views.py     <-- Lógica que responde a las peticiones del frontend
│   │   ├── serializers.py<- Convierte datos complejos a formato JSON
│   │   └── urls.py      <-- Rutas de la API (Endpoints)
│   ├── manage.py        <-- Script de comandos de Django
│   └── .env             <-- Variables de entorno (Contraseñas y claves)
│
└── CONTEXTO.md          <-- Documentación técnica más profunda y detallada
```

## 🚀 4. Cómo empezar (Entorno de Desarrollo)

Para levantar el proyecto en tu máquina local de forma sencilla, puedes utilizar los scripts preparados.

### Scripts de inicio rápido
El proyecto cuenta con scripts que levantan tanto el servidor del backend como el frontend de manera simultánea:
*   En Windows: Ejecuta el archivo `iniciar.bat` o `iniciar.ps1` ubicados en la raíz del proyecto.

### Arranque Manual (Paso a paso)
Si prefieres tener más control, puedes levantar cada entorno en terminales separadas:

**Para el Backend (API en Python):**
1. Abre una terminal y navega hasta la carpeta `gestion_backend`.
2. Activa tu entorno virtual (si tienes uno configurado).
3. Ejecuta el servidor de Django: `python manage.py runserver`

**Para el Frontend (Interfaz en Node.js):**
1. Abre una nueva terminal en la carpeta `gestion-frontend`.
2. Si es tu primera vez, instala las dependencias con: `npm install`
3. Inicia el servidor de desarrollo: `npm run dev` (La aplicación estará disponible en `http://localhost:7183`).

## 🔒 5. Aspectos Claves a tener en cuenta

*   **Seguridad y Privacidad:** Los datos sensibles en la base de datos (como RUTs, números de teléfono y licencias) se almacenan **encriptados**. Se utiliza una librería avanzada (Fernet) para proteger esta información.
*   **Autenticación JWT:** El acceso al panel se realiza mediante el RUT del usuario y su contraseña. Desde mayo 2026, la autenticación usa **JSON Web Tokens (JWT)** en lugar de sesiones de Django. Ver sección 7 para más detalles.
*   **Tipos de Usuarios (Roles):** El sistema reconoce 3 jerarquías:
    *   `SUPERADMIN`: Administra a nivel global, gestiona las empresas cliente.
    *   `USUARIO`: Es el administrador o responsable dentro de una empresa específica.
    *   `CONDUCTOR`: Perfil operativo asociado directamente a un vehículo de la flota.
*   **Aislamiento de Datos:** Todo en el frontend gira en torno a la "empresa activa". El código asegura que cada usuario solo vea e interactúe con la información que pertenece a su propia organización.
*   **Sistema de Permisos en dos capas:**
    *   Capa 1 — **Módulos del plan:** Qué secciones puede ver/usar la empresa según su plan de suscripción.
    *   Capa 2 — **Permisos individuales:** Qué acciones puede realizar cada usuario dentro de esos módulos (ver, crear, editar, eliminar).

## 🔑 7. Autenticación JWT (JSON Web Tokens)

A partir de mayo 2026 el sistema migró de sesiones Django + cookies CSRF a autenticación stateless con JWT, usando la librería `djangorestframework-simplejwt`.

### Flujo de autenticación

1. El usuario inicia sesión con su RUT y contraseña en `/login`.
2. El backend valida las credenciales y devuelve un par de tokens:
   - **`access_token`**: vida útil de 60 minutos. Se incluye en cada petición como header `Authorization: Bearer <token>`.
   - **`refresh_token`**: vida útil de 7 días. Solo se usa para renovar el access token.
3. Ambos tokens se guardan en `localStorage` del navegador.
4. Al cerrar sesión, ambos tokens se eliminan del `localStorage` y del `sessionStorage`.

### Renovación automática (auto-refresh)

La función `apiFetch` en `src/utils/api.js` intercepta automáticamente las respuestas con código `401`. Cuando esto ocurre:
1. Llama a `/api/token/refresh/` con el `refresh_token` almacenado.
2. Si la renovación es exitosa, guarda el nuevo `access_token` (y el nuevo `refresh_token` si fue rotado) y reintenta la petición original de forma transparente.
3. Si la renovación falla (refresh expirado o inválido), limpia la sesión y redirige al login.

### Configuración relevante (backend)

```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'AUTH_HEADER_TYPES':      ('Bearer',),
}
```

### Endpoints de tokens

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/login/` | Login — devuelve `access` + `refresh` |
| POST | `/api/token/refresh/` | Renueva el `access_token` usando el `refresh_token` |

### Archivos involucrados

| Archivo | Cambio |
|---------|--------|
| `gestion_backend/requirements.txt` | Agregado `djangorestframework-simplejwt` |
| `gestion_backend/gestion_backend/settings.py` | Config `REST_FRAMEWORK` y `SIMPLE_JWT` |
| `gestion_backend/gestion_backend/urls.py` | Endpoint `/api/token/refresh/` |
| `gestion_backend/g_de_flota/views.py` | `login_view` genera tokens con `RefreshToken.for_user(user)` |
| `gestion-frontend/src/utils/api.js` | `apiFetch` con Bearer token + auto-refresh |
| `gestion-frontend/src/web/login.vue` | Guarda tokens en `localStorage` al iniciar sesión |
| `gestion-frontend/src/web/Base.vue` | `cerrarSesion` elimina tokens del storage |
| `gestion-frontend/src/web/empresa/EmpresaLayout.vue` | `cerrarSesion` elimina tokens del storage |

---

## 🏢 8. Gestión de Planes de Suscripción

### Asignación de plan al crear/editar una empresa

El SUPERADMIN puede seleccionar el plan de suscripción directamente desde los formularios de creación y edición de empresa, sin necesidad de ir al módulo de Planes por separado.

**Cómo funciona:**
- Al crear una empresa, se muestra un selector "Suscripción" con todos los planes disponibles. Si no se selecciona ninguno, la empresa queda sin plan.
- Al editar una empresa, el plan actual aparece preseleccionado. El SUPERADMIN puede cambiarlo o quitarlo.
- Cada cambio de plan queda registrado en el modelo `CambioPlan` con el motivo, el usuario que realizó el cambio y los planes anterior y posterior.

**Archivos involucrados:**

| Archivo | Cambio |
|---------|--------|
| `gestion_backend/g_de_flota/serializers.py` | `EmpresaSerializer` expone `plan_id` (escritura) y `plan_nombre` (lectura) |
| `gestion_backend/g_de_flota/views.py` | `empresas_crear` y `empresas_detalle` manejan la asignación de plan y crean registros `CambioPlan` |
| `gestion-frontend/src/web/clientes/NuevaEmpresa.vue` | Select de plan en sección "Suscripción" |
| `gestion-frontend/src/web/clientes/EditarEmpresa.vue` | Select de plan con preselección del plan actual |

---

## 🔔 9. Sistema de Alertas (Toasts)

El sistema cuenta con un componente global `AppToast.vue` que muestra notificaciones no intrusivas en la esquina superior derecha de la pantalla.

**Cómo emitir una alerta desde cualquier vista:**

```javascript
window.dispatchEvent(new CustomEvent('app-toast', {
  detail: {
    tipo:    'exito',   // 'exito' | 'error' | 'info' | 'advertencia'
    mensaje: 'Operación realizada con éxito.',
  }
}))
```

**Nota técnica:** El componente tiene `z-index: 9999` para asegurarse de que las alertas aparezcan por encima de modales y otros overlays.

---

## 📚 10. ¿Dónde aprender más?
Una vez que te familiarices con este documento, te sugerimos revisar directamente los archivos fuente del proyecto. La estructura de carpetas descrita en la sección 3 te guiará hacia cada módulo del sistema.
