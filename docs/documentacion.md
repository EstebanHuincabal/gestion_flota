# Sistema de Gestión de Flota — Documentación Técnica

> **Versión:** 2.9 · **Última actualización:** Mayo 2026  
> **Stack:** Django 5 · Vue 3 · Capacitor 8 · SQLite · JWT

---

## Tabla de contenidos

1. [Visión general](#1-visión-general)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Estructura del repositorio](#3-estructura-del-repositorio)
4. [Puesta en marcha (entorno de desarrollo)](#4-puesta-en-marcha-entorno-de-desarrollo)
5. [Seguridad y cifrado de datos](#5-seguridad-y-cifrado-de-datos)
6. [Autenticación JWT](#6-autenticación-jwt)
7. [Roles y sistema de permisos](#7-roles-y-sistema-de-permisos)
8. [Planes de suscripción](#8-planes-de-suscripción)
9. [Módulos del sistema](#9-módulos-del-sistema)
    - 9.13 [Rutas y Trabajos](#913-rutas-y-trabajos)
    - 9.14 [App Móvil de Conductores](#914-app-móvil-de-conductores)
    - 9.15 [Solicitudes de Conductores (USUARIO + SUPERADMIN)](#915-solicitudes-de-conductores-panel-web)
10. [Referencia de la API REST](#10-referencia-de-la-api-rest)
11. [Modelo de datos](#11-modelo-de-datos)
12. [Frontend — Estructura de vistas](#12-frontend--estructura-de-vistas)
13. [Sistema de notificaciones](#13-sistema-de-notificaciones)
14. [Alertas de interfaz (Toasts)](#14-alertas-de-interfaz-toasts)
15. [Variables de entorno](#15-variables-de-entorno)
16. [Manejo de errores (v2.5)](#16-manejo-de-errores-v25)

---

## 1. Visión general

El **Sistema de Gestión de Flota** es una aplicación SaaS multiempresa orientada a la administración integral de flotas vehiculares en Chile. Permite a cada empresa cliente gestionar sus vehículos, conductores, mantenciones, documentos legales y finanzas operativas desde un panel privado y aislado.

Un usuario **Superadmin** opera a nivel global: administra las empresas cliente, sus planes de suscripción y tiene acceso a métricas y reportes consolidados de toda la plataforma.

### Capacidades principales

| Área | Funcionalidad |
|---|---|
| **Flota** | Gestión de flotas, vehículos y asignación conductor-vehículo |
| **Mantenciones** | Registro correctivo + mantenimiento predictivo basado en reglas |
| **Documentos** | Control de vigencia para permisos, revisión técnica, SOAP y licencias |
| **Finanzas** | Gastos operativos categorizados, presupuesto mensual y dashboard SaaS |
| **Reportes** | Exportación XLSX y visualizaciones Chart.js por módulo |
| **Rutas y Trabajos** | Planificación de rutas con mapa Leaflet, cálculo OSRM (distancia/duración/polyline), checklist pre-viaje, registro de km y notas al finalizar, historial de eventos y comentarios por ruta |
| **Notificaciones** | Alertas in-app en tiempo real (WebSocket) + preferencias de canal |
| **Permisos** | Una capa basada en el plan: módulos visibles y acciones disponibles se definen a nivel de plan de suscripción |
| **App Conductores** | Aplicación móvil (Vue 3 + Capacitor 8) para conductores: consulta de rutas asignadas, inicio/finalización con km y costos reales, mapa Leaflet, solicitudes de mantención/combustible/incidencia/documento con foto, soporte offline con SQLite |

---

## 2. Arquitectura del sistema

El proyecto sigue una arquitectura **desacoplada** (API REST + SPA):

```
┌─────────────────────────┐  ┌─────────────────────────┐
│   Panel Web (Navegador)  │  │  App Conductores (móvil) │
│  Vue 3 · Chart.js        │  │  Vue 3 · Capacitor 8     │
│  http://localhost:7183   │  │  http://localhost:5174   │
└────────────┬────────────┘  └──────┬──────────┬────────┘
             │ HTTP/JSON (JWT)       │ HTTP/JSON │ WebSocket
             │ WebSocket (ws://)     │ + WS      │ ws/conductor/
┌────────────▼───────────────────────▼───────────▼───────┐
│                Backend (Django 5 / ASGI)                │
│   Django REST Framework · SimpleJWT · Channels          │
│                 http://localhost:8000                   │
└────────────────────────┬───────────────────────┬────────┘
                         │ ORM                    │ Firebase Admin SDK
┌────────────────────────▼───────┐   ┌────────────▼────────────────────┐
│           Base de datos         │   │   Firebase Cloud Messaging (FCM) │
│         SQLite (desarrollo)     │   │   Push notifications → dispositivos│
└─────────────────────────────────┘   └──────────────────────────────────┘
```

### Tecnologías

**Backend**

| Tecnología | Versión | Propósito |
|---|---|---|
| Python / Django | 5.x | Framework web y ORM |
| Django REST Framework | — | API RESTful |
| djangorestframework-simplejwt | — | Autenticación JWT |
| Django Channels + Daphne | — | WebSockets (notificaciones en tiempo real) |
| cryptography (Fernet) | — | Cifrado simétrico de datos sensibles |
| openpyxl | — | Exportación de reportes a XLSX |
| python-dotenv | — | Gestión de variables de entorno |
| firebase-admin | 7.4.x | Envío de notificaciones push mediante Firebase Cloud Messaging |

**Frontend web**

| Tecnología | Versión | Propósito |
|---|---|---|
| Vue.js 3 (Composition API) | — | Framework SPA |
| Vite | — | Bundler y servidor de desarrollo |
| Vue Router | — | Navegación entre vistas |
| TailwindCSS | — | Estilos utilitarios |
| Chart.js | — | Visualizaciones y gráficos |

**App móvil de conductores**

| Tecnología | Versión | Propósito |
|---|---|---|
| Vue.js 3 (Composition API) | — | Framework SPA |
| Vite + Capacitor 8 | — | Bundler + empaquetado Android/iOS |
| Pinia | — | Gestión de estado global |
| @capacitor/preferences | — | Almacenamiento seguro de tokens (Keychain/EncryptedSharedPreferences) |
| @capacitor-community/sqlite | — | Base de datos local para modo offline |
| @capacitor/network | — | Detección de conectividad |
| @capacitor/push-notifications | — | Registro de token FCM y recepción de notificaciones push nativas |
| Leaflet.js | — | Mapas interactivos con paradas y polilínea |

---

## 3. Estructura del repositorio

```
gestion_flota/
├── iniciar.ps1                   # Script de arranque conjunto (3 servicios)
├── .env                          # Variables de entorno centralizadas (no commitear)
├── docs/
│   └── documentacion.md          # Este archivo
│
├── gestion-frontend/             # Panel web — Vue 3 SPA
│   ├── src/
│   │   ├── App.vue               # Raíz de la aplicación
│   │   ├── router/               # Definición de rutas del SPA
│   │   ├── utils/
│   │   │   └── api.js            # Cliente HTTP con auto-refresh JWT
│   │   ├── components/           # Componentes reutilizables
│   │   │   ├── AppToast.vue      # Sistema de toasts global
│   │   │   ├── ConfirmModal.vue  # Modal de confirmación genérico
│   │   │   ├── LimitePlanModal.vue
│   │   │   ├── NotificacionesBell.vue
│   │   │   ├── PermisoToast.vue  # Aviso de permiso denegado
│   │   │   └── PlanUsageBanner.vue
│   │   └── web/                  # Vistas de la aplicación
│   │       ├── login.vue
│   │       ├── Base.vue          # Layout SUPERADMIN
│   │       ├── Dashboard.vue     # Dashboards empresa y superadmin
│   │       ├── clientes/         # Gestión de empresas (SUPERADMIN)
│   │       ├── configuracion/    # Perfil, notificaciones, mi plan
│   │       ├── documentos/       # Gestión documental
│   │       ├── empresa/          # Layout y submódulos de empresa
│   │       │   ├── EmpresaLayout.vue
│   │       │   ├── conductores/
│   │       │   ├── flota/
│   │       │   │   └── mantenciones/
│   │       │   └── predictivo/
│   │       ├── finanzas/         # Gastos, presupuesto y SaaS
│   │       ├── logs/             # Auditoría
│   │       ├── notificaciones/
│   │       ├── permisos/
│   │       ├── planes/
│   │       ├── reportes/         # Reportes empresa y superadmin
│   │       ├── rutas/            # Rutas y trabajos
│   │       │   ├── Rutas.vue     # Vista principal con tabla, panel y modales
│   │       │   └── MapaRuta.vue  # Componente Leaflet reutilizable
│   │       ├── solicitudes/      # Solicitudes de conductores (panel web)
│   │       │   └── SolicitudesConductores.vue  # Tabla + modales + badge WS
│   │       └── usuarios/
│   └── package.json
│
├── app_conductor/                # App móvil conductores — Vue 3 + Capacitor 8
│   ├── src/
│   │   ├── main.js               # Punto de entrada
│   │   ├── router/
│   │   │   └── index.js          # Rutas + guard de autenticación
│   │   ├── stores/
│   │   │   ├── auth.js           # Sesión: login con RUT, tokens en Preferences
│   │   │   ├── rutas.js          # Estado de rutas + offline optimista
│   │   │   ├── solicitudes.js    # Estado de solicitudes + WebSocket + tipos permitidos por plan
│   │   │   └── mantenciones.js   # Mantenciones del vehículo asignado (urgente, bloqueado)
│   │   ├── services/
│   │   │   ├── api.js            # Cliente HTTP con auto-refresh JWT
│   │   │   ├── db.js             # SQLite (nativo) / Map en memoria (navegador)
│   │   │   ├── sync.js           # Sincronización offline → online
│   │   │   └── websocket.js      # Singleton WebSocket con backoff exponencial (WS conductor)
│   │   ├── views/
│   │   │   ├── Login.vue         # Login con RUT chileno + validación módulo 11
│   │   │   ├── Rutas/
│   │   │   │   ├── ListaRutas.vue   # Lista activa, pendientes e historial
│   │   │   │   └── DetalleRuta.vue  # Mapa Leaflet + acción iniciar/finalizar
│   │   │   ├── Solicitudes/
│   │   │   │   └── ListaSolicitudes.vue
│   │   │   ├── Mantenciones/
│   │   │   │   └── MiMantencion.vue  # Mantenciones pendientes/en proceso del vehículo
│   │   │   ├── Ajustes/
│   │   │   │   └── Ajustes.vue
│   │   │   └── Onboarding/
│   │   │       └── SubirDocumentos.vue
│   │   ├── components/
│   │   │   ├── BottomNav.vue     # Barra de navegación inferior (4 tabs: Rutas/Solicitudes/Mantención/Ajustes)
│   │   │   └── RutaCard.vue      # Tarjeta de ruta (variantes: activa/pendiente/finalizada)
│   │   ├── utils/
│   │   │   └── formato.js        # formatCLP, formatDuracion, formatFechaRuta, iniciales
│   │   └── assets/
│   │       └── main.css          # Tailwind + variables CSS --color-acento
│   ├── vite.config.js            # Puerto 5174 · envDir '..' · proxy /api → :8000
│   └── package.json
│
└── gestion_backend/              # Backend Django
    ├── manage.py
    ├── requirements.txt
    ├── serviceAccountKey.json    # Credenciales Firebase Admin SDK (no commitear — local/server)
    ├── g_de_flota/               # App principal
    │   ├── models.py             # Modelos ORM (incluye Vehiculo.en_mantencion)
    │   ├── views.py              # Endpoints principales (incluye login con vehiculo_asignado)
    │   ├── views_gastos.py       # Endpoints de finanzas
    │   ├── views_reportes.py     # Endpoints de reportes
    │   ├── views_documentos.py   # Endpoints de documentos (logs enriquecidos)
    │   ├── views_planes.py       # Endpoints de planes
    │   ├── views_config.py       # Perfil y configuración
    │   ├── views_rutas.py        # Endpoints de rutas y trabajos (panel web)
    │   ├── views_conductor.py    # Endpoints exclusivos app móvil conductores (rutas, solicitudes, mantenciones, push-token)
    │   ├── views_solicitudes.py  # Endpoints panel web: gestión solicitudes + push FCM + WS conductor
    │   ├── firebase_push.py      # Envío push FCM (inicialización lazy, falla silenciosamente si no configurado)
    │   ├── consumers.py          # WS consumers: NotificacionesConsumer, SolicitudesConsumer, ConductorConsumer
    │   ├── routing.py            # Rutas WebSocket (ws/solicitudes/, ws/conductor/)
    │   ├── ruta_calculator.py    # Motor de cálculo OSRM (distancia, duración, polyline — sin costos ni peajes)
    │   ├── audit.py              # registrar_log() + _parse_navegador/so() + _diff_campos()
    │   ├── serializers.py        # Serializadores DRF (LogAuditoria incluye navegador/so)
    │   ├── backends.py           # Backend de autenticación por RUT
    │   └── middleware.py         # Middleware de seguridad
    └── gestion_backend/
        ├── settings.py           # load_dotenv desde raíz del monorepo; FIREBASE_CREDENTIALS
        ├── urls.py               # Router principal (84+ endpoints)
        ├── asgi.py               # Configuración ASGI / Channels
        └── wsgi.py
```

---

## 4. Puesta en marcha (entorno de desarrollo)

### Requisitos previos

- Python 3.11+
- Node.js 18+ / npm
- Git

### Arranque rápido (recomendado)

Desde la raíz del proyecto ejecutar el script PowerShell que levanta los **3 servicios** simultáneamente en pestañas separadas de Windows Terminal:

```powershell
.\iniciar.ps1
```

Los tres servicios que se inician son:
- **Backend Django** → `http://localhost:8000`
- **Panel web** → `http://localhost:7183`
- **App conductores** → `http://localhost:5174`

### Arranque manual

**Backend (terminal 1)**

```bash
cd gestion_backend
# Crear y activar entorno virtual (primera vez)
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows

# Instalar dependencias (primera vez)
pip install -r requirements.txt

# Aplicar migraciones (primera vez)
python manage.py migrate

# Iniciar servidor ASGI
python manage.py runserver
# → API disponible en http://localhost:8000
```

**Panel web (terminal 2)**

```bash
cd gestion-frontend

# Instalar dependencias (primera vez)
npm install

# Iniciar servidor de desarrollo
npm run dev
# → Interfaz disponible en http://localhost:7183
```

**App conductores (terminal 3)**

```bash
cd app_conductor

# Instalar dependencias (primera vez)
npm install

# Iniciar servidor de desarrollo (web/browser)
npm run dev
# → App disponible en http://localhost:5174
```

### Variables de entorno necesarias

Existe **un único `.env`** en la raíz del monorepo (`gestion_flota/.env`) que es leído por Django y por Vite de ambos frontends (ver sección 15 para detalle completo):

```ini
SECRET_KEY=<clave-django-aleatoria>
ENCRYPTION_KEY=<clave-cifrado-fernet>
FERNET_KEY=<clave-fernet-base64>
DEBUG=True
VITE_API_URL=
```

---

## 5. Seguridad y cifrado de datos

### Cifrado Fernet de campos sensibles

Los datos personales se almacenan **cifrados en la base de datos** usando el algoritmo simétrico AES-128-CBC a través de la librería `cryptography.fernet`. La clave derivada se obtiene aplicando SHA-256 a `settings.ENCRYPTION_KEY`.

Los campos cifrados son:

| Modelo | Campos cifrados |
|---|---|
| `Usuario` | `rut_cifrado`, `nombre_cifrado`, `telefono_cifrado`, `licencia_cifrada` |
| `Empresa` | `rut_cifrado`, `email_cifrado`, `telefono_cifrado`, `direccion_cifrada`, `comuna_cifrada`, `ciudad_cifrada` |

Para búsquedas por RUT (login, deduplicación) se almacena adicionalmente el hash SHA-256 del RUT normalizado (`rut_hash`), permitiendo comparación sin descifrar.

### Normalización del RUT

Antes de cifrar o hashear, el RUT se normaliza eliminando puntos y convirtiendo a minúsculas:

```
12.345.678-9  →  12345678-9
```

### Backend de autenticación personalizado

El inicio de sesión se realiza con **RUT + contraseña** (no email). El backend `RutBackend` busca al usuario por `rut_hash` y valida la contraseña con el sistema de Django.

### Bloqueo de cuenta

Tras intentos fallidos consecutivos, la cuenta puede ser bloqueada (`is_blocked=True`). El desbloqueo lo realiza un administrador desde el panel de usuarios.

---

## 6. Autenticación JWT

El sistema utiliza autenticación **stateless** mediante JSON Web Tokens, implementada con `djangorestframework-simplejwt`.

### Flujo de autenticación

```
[Cliente]  POST /api/login/ {rut, password}
                    ↓
[Backend]  Valida credenciales → devuelve {access, refresh}
                    ↓
[Cliente]  Almacena tokens en localStorage
           Incluye header en cada petición:
           Authorization: Bearer <access_token>
```

### Configuración de tokens

| Parámetro | Valor |
|---|---|
| Duración `access_token` | 60 minutos |
| Duración `refresh_token` | 7 días |
| Rotación de refresh | Habilitada (`ROTATE_REFRESH_TOKENS = True`) |
| Tipo de cabecera | `Bearer` |

### Renovación automática (auto-refresh)

La función `apiFetch` en `src/utils/api.js` intercepta respuestas `401` automáticamente:

1. Llama a `POST /api/token/refresh/` con el `refresh_token` almacenado.
2. Si la renovación es exitosa, guarda los nuevos tokens y reintenta la petición original de forma transparente.
3. Si el refresh está expirado o es inválido, limpia el storage y redirige al login.

### Endpoints de autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/login/` | Login por RUT — devuelve `access` + `refresh` |
| `POST` | `/api/token/refresh/` | Renueva el `access_token` usando el `refresh_token` |

---

## 7. Roles y sistema de permisos

### Roles (jerarquía)

| Rol | Descripción |
|---|---|
| `SUPERADMIN` | Administrador global de la plataforma. Gestiona empresas, planes y tiene acceso a métricas SaaS. Tiene todos los permisos sin restricción. |
| `USUARIO` | Administrador de una empresa cliente. Sus módulos y permisos disponibles están determinados íntegramente por el plan de suscripción de su empresa. |
| `CONDUCTOR` | Perfil operativo. Sin acceso a módulos de gestión — accede únicamente a la información de su vehículo asignado. |

### Sistema de permisos (una capa — basado en el plan)

Los permisos **no se configuran por usuario individualmente**. Todo lo que un usuario de tipo `USUARIO` puede ver y hacer está determinado exclusivamente por el **plan de suscripción** de su empresa. El plan define dos conjuntos:

**`modulos` — Secciones habilitadas:**  
JSON array almacenado en `PlanSuscripcion.modulos`. Controla qué secciones aparecen en el menú de navegación. Si un módulo no está en el plan, la vista muestra una pantalla de bloqueo.

```json
["conductores", "documentos", "finanzas", "reportes", "predictivo"]
```

**`permisos` — Acciones disponibles:**  
Relación M2M entre `PlanSuscripcion` y `Permiso`. Define qué operaciones (crear, editar, eliminar, exportar, etc.) están disponibles dentro de los módulos habilitados.

Ejemplo de códigos de permiso:

```
flota.ver            flota.crear          flota.editar         flota.eliminar
mantencion.ver       mantencion.crear     mantencion.editar
conductores.ver      conductores.asignar
finanzas.ver         finanzas.crear       finanzas.exportar
reportes.ver         reportes.exportar
documentos.ver       documentos.subir
```

### Cómo fluyen los permisos al frontend

Al iniciar sesión (y periódicamente cada 15 segundos), el frontend obtiene los permisos y módulos vigentes:

1. **Login** (`POST /api/login/`): el backend incluye `plan_modulos` y `plan_permisos` en la respuesta. Se guardan en `sessionStorage`.
2. **Refresco** (`GET /api/usuario/perfil/`): `EmpresaLayout.vue` llama a este endpoint al montar y cada 15 s, actualizando `sessionStorage` si el plan cambia.
3. **Verificación** (`src/utils/permisos.js`):
   - `tieneModulo(modulo)` → consulta `sessionStorage['plan_modulos']`
   - `tienePermiso(codigo)` → consulta `sessionStorage['plan_permisos']`
   - Para `SUPERADMIN`, ambas funciones retornan `true` siempre.
   - Para `CONDUCTOR`, ambas retornan `false` siempre.

### Verificación de permisos en el frontend

El componente `PermisoToast.vue` muestra una notificación de acceso denegado cuando un usuario intenta realizar una acción sin el permiso correspondiente. El componente `PlanUsageBanner.vue` avisa cuando la empresa se acerca a los límites cuantitativos del plan (vehículos, flotas, conductores, usuarios).

---

## 8. Planes de suscripción

### Planes disponibles

| Plan | Flotas | Vehículos | Conductores | Usuarios |
|---|---|---|---|---|
| `basico` | 1 | 10 | 10 | 5 |
| `pro` | configurable | configurable | configurable | configurable |
| `enterprise` | configurable | configurable | configurable | configurable |

Además de los límites cuantitativos, cada plan define:
- **`modulos`**: qué secciones del sistema son visibles para las empresas suscritas.
- **`permisos`**: qué acciones (crear, editar, eliminar, exportar, etc.) están disponibles dentro de esos módulos.

Todos los usuarios de una empresa comparten los mismos módulos y permisos — ambos determinados exclusivamente por el plan. No existe configuración de permisos por usuario individual.

#### Permisos de solicitudes de conductores (por tipo)

Desde la migración `0042`, cada tipo de solicitud de conductor tiene su propio permiso granular:

| Código de permiso | Tipo de solicitud |
|---|---|
| `solicitudes.mantencion` | Solicitar mantención del vehículo |
| `solicitudes.combustible` | Solicitar combustible |
| `solicitudes.incidencia` | Reportar incidencia o accidente |
| `solicitudes.documento` | Subir o renovar documentos |

Por defecto todos los planes tienen los cuatro tipos habilitados. El Superadmin puede quitar permisos específicos de un plan desde el panel de administración Django. Cuando un tipo no está en el plan:
- El backend rechaza el POST con `403` y `codigo: "plan_sin_permiso"`.
- La app móvil muestra el tipo en gris con candado y el texto "No disponible en tu plan".
- Se muestra un aviso informativo indicando que el administrador de la empresa puede gestionar el plan.

### Asignación de plan

El Superadmin asigna o cambia el plan de una empresa directamente desde los formularios de creación y edición de empresa. Cada cambio queda registrado en `CambioPlan` con el motivo, el usuario responsable y los planes anterior y posterior.

### Uso del plan

El endpoint `GET /api/empresa/plan-uso/` devuelve el consumo actual vs. los límites del plan activo (flotas, vehículos, conductores, usuarios). Este dato alimenta el banner de advertencia en la interfaz.

---

## 9. Módulos del sistema

### 9.1 Gestión de Empresas (SUPERADMIN)

Permite al Superadmin crear, editar, suspender y eliminar empresas cliente. Incluye asignación de plan, visualización de KPIs por empresa y acceso a su historial de cambios de plan.

**Vistas:** `ListaEmpresas.vue` · `NuevaEmpresa.vue` · `EditarEmpresa.vue` · `DetalleEmpresa.vue`

El **nombre de la empresa** admite un máximo de **30 caracteres** (mínimo 2) y la **dirección** un máximo de **40 caracteres**. Ambos límites se aplican en el modelo/serializer (`Empresa.nombre` con `max_length=30`; `direccion` con `max_length=40` en `EmpresaSerializer`), en la validación del registro público (`views_publico.py`) y en los formularios web (`NuevaEmpresa.vue`, `EditarEmpresa.vue`, `RegistroPublico.vue`).

### 9.2 Usuarios y Permisos

Gestión de usuarios dentro de cada empresa: creación, edición, cambio de contraseña, bloqueo/desbloqueo y asignación de permisos granulares.

**Vistas:** `ListaUsuarios.vue` · `NuevoUsuario.vue` · `EditarUsuario.vue` · `GestionPermisos.vue`

### 9.3 Conductores

Gestión de conductores (usuarios con rol `CONDUCTOR`). Incluye asignación y desasignación de vehículo, visualización del vehículo actualmente asignado y datos de licencia.

**Vistas:** `ListaConductores.vue` · `NuevoConductor.vue` · `EditarConductor.vue` · `DetalleConductor.vue`

### 9.4 Flota y Vehículos

Organización jerárquica: **Empresa → Flotas → Vehículos**. Cada vehículo registra patente, marca, modelo, año, tipo de combustible y kilometraje actual.

**Vistas:** `ListaFlota.vue` · `NuevaFlota.vue` · `EditarFlota.vue` · `FormVehiculo.vue`

### 9.5 Mantenciones Correctivas

Registro de mantenciones por vehículo con soporte de estados (`pendiente`, `en_proceso`, `realizada`, `cancelada`). Incluye vista de calendario y panel de sugerencias.

**Vistas:** `MantencionesLista.vue` · `MantencionesForm.vue` · `MantencionesDetalle.vue` · `MantencionesHistorial.vue` · `MantencionesCalendario.vue`

### 9.6 Mantenimiento Predictivo

Sistema basado en reglas para programar mantenciones preventivas. Cada empresa crea **Planes de Mantenimiento** con **Reglas** (tipo, intervalo en días, umbral de alerta, prioridad, canal de notificación). Los vehículos se asignan a planes, generando `MantencionProgramada` con fechas calculadas automáticamente.

Un proceso de generación de alertas evalúa las fechas próximas y crea `AlertaMantencion` para notificar a los responsables.

**Vista:** `MantencionPredictiva.vue`  
**Endpoints clave:** `GET /api/empresa/predictivo/resumen/` · `POST /api/empresa/predictivo/generar-alertas/`

### 9.7 Documentos

Gestión de documentos legales asociados a vehículos y conductores, con control automático de vigencia.

**Tipos de documento — Vehículo:**
- Permiso de circulación
- Revisión técnica
- Seguro SOAP

**Tipos de documento — Conductor:**
- Licencia de conducir
- Antecedentes comerciales

El método `Documento.estado()` devuelve `vigente`, `por_vencer` (≤ 30 días) o `vencido` según la `fecha_vencimiento`. Los documentos pueden ser renovados (nueva versión vinculada a la anterior).

**Vistas:** `Documentos.vue` · `DocumentosBadge.vue`

### 9.8 Finanzas Operativas

**Para USUARIO (empresa):**
- **Gastos operativos:** registro de gastos categorizados (combustible, mantención, multa, peaje, seguro, otro) con adjunto de comprobante.
- **Presupuesto mensual:** definición de presupuesto por mes/año y comparativa gráfica con el gasto real.
- **Pago de servicio:** tab dedicado con historial de pagos de la suscripción SaaS (Webpay Plus y transferencia manual), filtrados por mes/año. KPI card en el resumen con el total del período. Datos servidos desde `GastosListView` vía `pagos_servicio` / `total_servicio` en el response (modelo `PagoTransbank` estado `aprobado`).
- **Exportación:** descarga de gastos filtrados en formato XLSX.

**Vista:** `FinanzasEmpresa.vue`

**Para SUPERADMIN:**
- **Dashboard SaaS:** MRR, total de suscripciones activas, ingresos por plan, proyección lineal de MRR.

**Vista:** `FinanzasSuperAdmin.vue`

### 9.9 Reportes

**Para USUARIO (empresa):** Módulo con tabs por área:

| Tab | Contenido |
|---|---|
| Mantenciones | Costos por mes (línea dual), tabla detalle + barras presupuesto vs. real |
| Costo Total (TCO) | Barras horizontales comparativas por vehículo + tabla TCO |
| Conductores | Estadísticas y asignaciones por conductor |
| Documentos | Semáforo documental por vehículo + timeline de vencimientos próximos (60 días) |
| Combustible | KPIs, top-5 vehículos por gasto, evolución mensual (12 meses) |

Exportación disponible en XLSX para estado de flota, mantenciones y conductores.

**Vista:** `ReportesEmpresa.vue`

**Para SUPERADMIN:** Métricas de empresas, distribución de planes (gráfico dona) y resumen de plataforma.

**Vista:** `ReportesSuperAdmin.vue`

### 9.13 Rutas y Trabajos

Módulo de planificación y seguimiento de rutas vehiculares. Permite crear rutas con conductor, vehículo y paradas, calcular el trayecto óptimo con OSRM, registrar km al iniciar y finalizar, y mantener un historial de eventos automáticos y comentarios manuales por ruta.

> **Cambio v2.4 (Mayo 2026):** Se eliminaron por completo los modelos `Peaje`, `PeajeRuta` y `ConfiguracionRuta`, así como todos los campos de costos (`costo_combustible_est/real`, `costo_peajes_est/real`, `costo_total_est/real`) en `Ruta` y los campos `consumo_l_100km` y `categoria_peaje` en `Vehiculo`. Se reemplazó la lógica de costos y peajes por el modelo `EventoRuta` (historial de la ruta).

#### Flujo de una ruta

```
BORRADOR → PENDIENTE → ACTIVO → FINALIZADO
                   ↘               ↘
                  CANCELADO      CANCELADO
```

| Estado | Descripción |
|---|---|
| `borrador` | Guardado sin validar |
| `pendiente` | Lista para ser ejecutada — conductor asignado, paradas definidas |
| `activo` | En tránsito — se registra `km_inicio` |
| `finalizado` | Completada — se registra `km_fin` y notas |
| `cancelado` | Cancelada con motivo registrado |

#### Cálculo de ruta

Al crear o calcular una ruta, el sistema:

1. **Geocodificación:** Nominatim (`nominatim.openstreetmap.org`) resuelve cada dirección a coordenadas (debounce 500 ms).
2. **Trazado OSRM:** El motor de enrutamiento `router.project-osrm.org` calcula la polilínea óptima entre todas las paradas y devuelve `distancia_km`, `duracion_min` y `polyline`. Si OSRM no está disponible, se aplica el **cálculo fallback Haversine**: distancia en línea recta × 1.3 (factor de sinuosidad) y velocidad media de 60 km/h para la duración.

#### Al iniciar / finalizar

- **Iniciar:** se registra `km_inicio`, se actualiza `km_actuales` del vehículo y se crea un `EventoRuta` automático.
- **Finalizar:** solo acepta `km_fin` y `notas`. Se actualiza `vehiculo.km_actuales`. Se crea un `EventoRuta` automático.
- No se generan gastos operativos de combustible ni peajes automáticamente.

#### Historial (`EventoRuta`)

Cada ruta mantiene una lista cronológica de eventos:

| Campo | Descripción |
|---|---|
| `tipo` | `auto` (generado por el sistema) o `comentario` (escrito por admin o conductor) |
| `texto` | Texto descriptivo del evento |
| `autor` | FK a `Usuario` (nulo en eventos automáticos) |
| `created_at` | Timestamp automático |

Eventos automáticos creados en: creación de ruta, inicio, finalización y cancelación.

#### Campo `hora_programada`

La ruta acepta un campo opcional `hora_programada` (`TimeField`, formato `HH:MM`) que indica la hora de inicio prevista. Se muestra en:
- La tabla del panel web (junto a la fecha, en color índigo)
- El panel lateral de detalle de la ruta
- El chip de resumen en la app móvil
- La sección "Salida programada" del origen en el detalle de la app

#### Validaciones al crear/editar una ruta

El sistema aplica validaciones en dos momentos: un **pre-vuelo** (`POST /api/empresa/rutas/validar/`) antes de guardar y una validación definitiva al guardar.

**Errores bloqueantes** (impiden guardar):

| Validación | Regla |
|---|---|
| **Fecha no pasada** | `fecha_programada` debe ser ≥ hoy |
| **Conflicto de conductor (activo)** | El conductor tiene una ruta actualmente en curso |
| **Conflicto de conductor (pendiente)** | El conductor ya tiene una ruta pendiente en un margen de ±1 día respecto a la fecha solicitada |
| **Conflicto de vehículo (activo)** | El vehículo está asignado a una ruta en curso |
| **Conflicto de vehículo (pendiente)** | El vehículo está asignado a otra ruta pendiente dentro del margen de ±1 día |
| **Vehículo inactivo** | `vehiculo.activo = False` |
| **Vehículo en mantención** | `vehiculo.en_mantencion = True` |
| **Conductor inactivo** | `conductor.is_active = False` |
| **Conductor bloqueado** | `conductor.is_blocked = True` |

**Advertencias (warnings)** — permiten continuar con "Programar de todas formas":

| Advertencia | Regla |
|---|---|
| Mantención predictiva vencida | Existe `AlertaMantencion` con `nivel='vencida'` y `atendida=False` para el vehículo |
| Mantención correctiva pendiente | Existe `Mantencion` activa sin fecha de fin para el vehículo |
| Próxima mantención predictiva | `AlertaMantencion` con `nivel='por_vencer'` y ≤7 días |
| SOAP vencido / por vencer | `Documento` tipo `seguro_soap` vencido o con ≤15 días de vigencia |
| Revisión técnica vencida / por vencer | `Documento` tipo `revision_tecnica` con la misma lógica |
| Permiso de circulación vencido / por vencer | `Documento` tipo `permiso_circulacion` con la misma lógica |
| Licencia vencida / por vencer | `Documento` tipo `licencia` del conductor con ≤30 días de vigencia |

Las rutas en estado `cancelado` o `finalizado` **no** cuentan como conflicto. Al editar, la ruta se excluye de su propio chequeo. Sin `fecha_programada`, no se aplican conflictos de fecha.

**Frontend (panel web):** el paso 1 del asistente llama al endpoint `/validar/` al avanzar al paso 2; los errores se muestran en rojo (bloquean avanzar), las advertencias en amarillo (se puede continuar con "Programar de todas formas").

#### Restricción de inicio por hora

Si la ruta tiene `hora_programada`, **solo puede iniciarse con hasta 30 minutos de anticipación**. Si se intenta iniciar antes de ese margen:

- **Backend (`RutaIniciarView`):** retorna HTTP 400 con el mensaje de tiempo restante.
- **App móvil (`DetalleRuta.vue`):** el botón "Iniciar ruta" se reemplaza por un banner ámbar con el tiempo restante (calculado en el cliente). Al llegar al margen, el banner desaparece y el botón aparece sin necesidad de recargar.
- **Panel web (`Rutas.vue`):** aplica la misma validación server-side; si el admin intenta iniciar prematuramente, recibe el error con el tiempo restante.

**Vistas:** `Rutas.vue` · `MapaRuta.vue`  
**Backend:** `views_rutas.py`  
**Modelos:** `Ruta` · `Parada` · `EventoRuta`  
**Permiso requerido:** `rutas.ver` (ver lista y detalle), `rutas.crear` (crear, editar, cambiar estado)

---

### 9.14 App Móvil de Conductores

Aplicación Vue 3 + Capacitor 8 orientada exclusivamente al rol `CONDUCTOR`. Accede al mismo backend Django mediante JWT, con soporte **offline-first** usando `@capacitor-community/sqlite`.

#### Compatibilidad cross-device (optimizado Mayo 2026)

La app está optimizada para todos los tamaños de pantalla y modelos de teléfono:

| Problema | Solución aplicada |
|---|---|
| `100vh` incluye la barra de dirección en iOS Safari | `100dvh` + fallback `-webkit-fill-available` en `main.css` |
| Notch, Dynamic Island y home indicator | `viewport-fit=cover` en `index.html` + `env(safe-area-inset-*)` en todos los elementos fijos |
| `pb-24` (96px fijo) no cubre el home indicator | Variable CSS `--nav-total: calc(60px + env(safe-area-inset-bottom))` usada con `.pb-nav` |
| Toast en DetalleRuta quedaba detrás del notch | `top: max(1rem, env(safe-area-inset-top) + 0.5rem)` |
| Botón "Iniciar/Finalizar ruta" quedaba debajo del BottomNav en iPhone X+ | `bottom: var(--nav-total)` en lugar de `bottom: 64px` fijo |
| Modales con `height: 80vh` desbordaban en pantallas pequeñas | `min(80vh, 80dvh)` que respeta la altura dinámica |
| Login con `min-height: 60vh` cortaba en iPhone SE | Card con `max-height: 72vh` y scroll interno |
| Barra de estado fija en color púrpura aunque el tema cambie | `inicializarStatusBar()` en `App.vue` usa `@capacitor/status-bar` para fijar color en runtime desde `themeStore.temaActual.colorGrad[0]`; `watch(temaActualId)` lo actualiza al cambiar tema |

#### Pantallas

| Pantalla | Ruta | Descripción |
|---|---|---|
| `Login.vue` | `/login` | Autenticación por RUT chileno + contraseña. Validación módulo 11 en el cliente. |
| `ListaRutas.vue` | `/rutas` | Muestra ruta activa (en curso), próximas rutas pendientes e historial colapsable. Pull-to-refresh. Banner offline. |
| `DetalleRuta.vue` | `/rutas/:id` | 3 tabs (Ruta / Detalles / Historial). Mapa Leaflet (carga dinámica desde CDN). Lista de paradas con tipo e ícono. Bottom-sheet modales con validación para iniciar (km_inicio) y finalizar (km_fin + notas). Tab Historial con lista de `EventoRuta` e input para agregar comentarios. Toast de confirmación. **Para rutas pendientes**, si el checklist pre-viaje no está completo muestra un botón morado "Completar checklist antes de iniciar"; una vez completado aparece el botón verde "Iniciar ruta". |
| `ChecklistPreviaje.vue` | `/rutas/:id/checklist` | Checklist pre-viaje de 12 ítems agrupados (Documentos, Mecánica, Seguridad). Barra de progreso animada, ítems con estado visual (pendiente/ok/falla), documentos vigentes pre-marcados automáticamente, textarea de observación para fallas, firma digital por canvas (touch). Botón de envío deshabilitado hasta completar todos los ítems obligatorios y firmar. |
| `ListaSolicitudes.vue` | `/solicitudes` | Módulo de solicitudes del conductor. Tipos: mantención, combustible, incidencia, documento. FAB para crear nueva solicitud (2 pasos: elegir tipo → formulario). Sección "En proceso" y "Historial" colapsable. ModalDetalleSolicitud de solo lectura. Pull-to-refresh. Soporte offline con SQLite. Captura de foto con `@capacitor/camera`. **Validación de plan:** tipos bloqueados por el plan aparecen en gris con candado e ícono "No disponible en tu plan". El backend rechaza con 403 si se intenta crear un tipo no permitido. |
| `MiMantencion.vue` | `/mantencion` | Mantenciones pendientes y en proceso del vehículo asignado. Muestra fecha programada, taller, presupuesto, días restantes, chips de urgencia. Alerta roja si el vehículo está fuera de servicio. Pull-to-refresh. Al tocar una tarjeta se abre `ModalDetalleMantencion` con la acción correspondiente al estado. Toast de feedback tras iniciar o completar. |
| `MisDocumentos.vue` | `/documentos` | Documentación del conductor y del vehículo asignado. **Sección conductor:** Licencia de conducir. **Sección vehículo:** Permiso de circulación, Revisión técnica y Seguro SOAP (vinculados al vehículo asignado vía `Asignacion`). Cada tarjeta muestra estado (Vigente/Por vencer/Vencido/Sin documento), fechas e historial de versiones. Sheet modal con Cámara/Galería/Archivo, fechas y notas. Los documentos quedan registrados en el módulo de Documentos del panel web. Pull-to-refresh. |
| `SubirDocumentos.vue` | `/onboarding` | Pantalla de onboarding (primer login). Muestra las mismas tarjetas de documentación (conductor + vehículo) con encabezado "Completa tu documentación". Botón **Continuar** al pie que redirige al primer módulo disponible según el plan. Comparte el mismo store `documentos.js`. |
| `Ajustes.vue` | `/ajustes` | Perfil del conductor (nombre, RUT, email, empresa). Tarjeta de vehículo asignado. **Sección Apariencia** con selector de 6 temas de color. **Botón "Cerrar sesión"** como botón destacado rojo autónomo (no dentro de un grupo iOS) con bottom-sheet de confirmación. |

#### Rediseño visual (Mayo 2026)

Se realizó un rediseño completo de la UI de la app móvil (`v2.3`). Cambios principales:

| Archivo | Cambio |
|---|---|
| `assets/main.css` | Nuevos tokens CSS: `--gradient-primary/hero/success/card`, `--shadow-xs/sm/md/lg/acento`, clases utilitarias `.card`, `.card-hero`, `.glass`, `.btn-primary`, `.skeleton`, `.badge` |
| `BottomNav.vue` | Glassmorphism (`backdrop-filter: blur(20px)`), pill de indicador activo con sombra púrpura, íconos rellenos vs. contorno para estado activo/inactivo, altura nav aumentada a 64px (`--nav-h: 64px`) |
| `RutaCard.vue` | Variante `activa`: tarjeta hero con gradiente verde + pulso animado. Variante `pendiente`: acento izquierdo con gradiente, fecha, distancia y duración. Variante `finalizada`: chip de check verde con km recorridos |
| `ListaRutas.vue` | Header con gradiente `--gradient-hero` (azul-morado profundo), avatar con borde translúcido, stats row con chips de estado, botón sync e íconos ghost |
| `ListaSolicitudes.vue` | Header hero con título grande, chips de resumen (activas/resueltas), FAB rediseñado con gradiente y sombra `var(--shadow-acento)`, sección labels estilo uppercase |
| `MiMantencion.vue` | Header hero con ícono de llave decorativo, chip de información del vehículo, skeleton mejorado |
| `HistorialMantenciones.vue` | Header con gradiente, botón volver circular translúcido, lista convertida a **timeline visual** con eje punteado, puntos de color y tarjetas flotantes |
| `Ajustes.vue` | Header hero tipo "profile card" con avatar grande con anillo, chips de datos del conductor, tarjeta de vehículo rediseñada, grupos de ajustes estilo iOS (íconos de colores + chevrons) |

#### Componentes

| Componente | Descripción |
|---|---|
| `BottomNav.vue` | Barra inferior con glassmorphism, pill activo con sombra `--shadow-acento`, íconos filled/outline según estado. Badge rojo `!` si hay mantención urgente; badge azul con cantidad si hay activas. Altura total: 64px + safe area. |
| `RutaCard.vue` | Tarjeta de ruta con 3 variantes: `activa` (hero gradient verde + pulso animado), `pendiente` (borde izquierdo gradiente, fecha y distancia), `finalizada` (compacta con chip de check y km recorridos) |
| `MapaRuta.vue` | Mapa Leaflet cargado dinámicamente desde unpkg CDN. Marcadores SVG por tipo (origen/parada/destino). Polyline OSRM o punteada de fallback. Mensaje offline si no carga. |
| `ModalDetalleMantencion.vue` | Bottom-sheet con el detalle completo de una mantención y las acciones disponibles por estado: **pendiente** → mini-confirm + botón azul "Iniciar mantención"; **en_proceso** → botón verde "Marcar como realizada" que abre `ModalCompletarMantencion`; **realizada** → solo lectura (precio, foto, quién la completó). |
| `ModalCompletarMantencion.vue` | Bottom-sheet formulario para registrar la finalización de una mantención: costo final en CLP (con formato automático), fecha de realización, foto del recibo (captura de cámara con `capture="environment"`, opcional) y notas. Envía `multipart/FormData` al endpoint `/completar/`. |

#### Servicios

| Store | Archivo | Descripción |
|---|---|---|
| Temas | `stores/theme.js` | Store Pinia con 6 temas de color (Índigo, Océano, Esmeralda, Carmesí, Cobre, Pizarra). Aplica variables CSS en `:root` de forma reactiva. Persiste la elección en `@capacitor/preferences` (clave `tema_app`). Personal por conductor y por dispositivo. |
| Documentos | `stores/documentos.js` | Store Pinia para la documentación del conductor y su vehículo. `cargarDocumentos()` → `GET /api/empresa/documentos/`. `subirDocumento(formData)` → `POST /api/empresa/documentos/`. Computed `docPorTipo` devuelve el doc más reciente por tipo. Exporta `TIPOS_CONDUCTOR` (`licencia`) y `TIPOS_VEHICULO` (`permiso_circulacion`, `revision_tecnica`, `seguro_soap`) con metadatos visuales. |

| Servicio | Archivo | Descripción |
|---|---|---|
| API HTTP | `services/api.js` | `apiFetch()` con auto-refresh JWT en 401. Tokens en `@capacitor/preferences`. |
| Base de datos local | `services/db.js` | SQLite en dispositivo nativo; Map en memoria en navegador. Guarda rutas, solicitudes y acciones pendientes. |
| Sincronización | `services/sync.js` | Detecta reconexión (`@capacitor/network`) y envía acciones encoladas durante el modo offline. |
| WebSocket | `services/websocket.js` | Singleton que mantiene conexión persistente a `ws/conductor/`. Reconexión automática con backoff exponencial (máx. 30 s). Notifica al store cuando cambia el estado de una solicitud. |

#### Sistema de permisos por plan (Mayo 2026 — actualizado)

La app aplica restricciones de acceso según los módulos que el plan de la empresa tiene habilitados. La fuente de verdad es `PlanSuscripcion.permisos` (M2M), no el campo `modulos` JSONField. El backend deriva los módulos visibles comprobando si el plan tiene **algún permiso** con el prefijo del módulo (`rutas.`, `solicitudes.`, `mantenciones.`).

##### Endpoint de módulos activos

```
GET /api/conductor/mi-plan/
→ { "plan_modulos": ["rutas", "solicitudes", "mantenciones"], "plan_nombre": "Premium" }
```

**Función auxiliar en backend** (`views_conductor.py`):

```python
_MODULO_A_PREFIJO = {
    'rutas':        'rutas.',
    'solicitudes':  'solicitudes.',
    'mantenciones': 'mantenciones.',
}

def _modulos_desde_permisos(plan) -> list:
    codigos = set(plan.permisos.values_list('codigo', flat=True))
    return [m for m, p in _MODULO_A_PREFIJO.items()
            if any(c.startswith(p) for c in codigos)]
```

##### Flujo de sincronización

1. **Al iniciar la app:** `usePermisos()` carga Preferences (caché instantánea), luego llama a `/api/conductor/mi-plan/` y establece el estado reactivo. `cargando = false` solo después de que responde el servidor, para evitar parpadeos.
2. **Polling automático:** cada 15 segundos `usePermisos` refresca los módulos. Si cambian, actualiza Preferences y los refs reactivos → todos los componentes se actualizan sin recargar.
3. **Vuelta al primer plano:** `App.addListener('appStateChange', ...)` dispara un refresco inmediato al volver desde background.
4. **Router guard:** antes de cada navegación lee `plan_modulos` desde Preferences. Si la ruta tiene `meta.modulo` y no está en el array, redirige silenciosamente al primer módulo disponible (rutas → solicitudes → mantenciones → ajustes).
5. **Guard pasivo:** el router guard evalúa los módulos en cada cambio de ruta. Si el conductor está en pantalla cuando se le quita un módulo, el cambio se refleja sin redirección abrupta — la tab del BottomNav desaparece y el usuario puede navegar a otra sección libremente.
6. **Logout:** `resetearPermisos()` limpia el singleton (interval + listener), luego `limpiarSesion()` borra Preferences.

##### Módulos de la app y lo que controlan

| Módulo clave | Tab visible | Rutas protegidas | Redirect si removido |
|---|---|---|---|
| `rutas` | Rutas (BottomNav) | `/rutas`, `/rutas/:id`, `/rutas/:id/checklist` | Redirect al primer módulo disponible (guard de ruta) |
| `solicitudes` | Solicitudes (BottomNav) | `/solicitudes` | Redirect al primer módulo disponible (guard de ruta) |
| `mantenciones` | Mantención (BottomNav) | `/mantencion`, `/mantencion/historial` | Redirect al primer módulo disponible (guard de ruta) |
| — | Ajustes (BottomNav) | `/ajustes` | Siempre visible |

##### Singleton `usePermisos`

Estado a nivel de módulo JS (compartido entre todos los componentes):

```javascript
// Un solo intervalo y listener para toda la app
const modulos    = ref([])
const planNombre = ref('')
const cargando   = ref(true)
let _inicializado = false

export function usePermisos() {
  _inicializar()   // no-op si ya fue llamado
  return { modulos, planNombre, tieneModulo, cargando }
}
export async function resetearPermisos() { /* limpia al hacer logout */ }
```

##### Archivos del sistema de permisos

| Archivo | Descripción |
|---|---|
| `src/composables/usePermisos.js` | Singleton reactivo: polling 15 s + `appStateChange`. Expone `modulos`, `planNombre`, `tieneModulo()`, `cargando` |
| `src/router/index.js` | Guard + `_primerModuloDisponible()` para redirigir al módulo correcto según el plan |
| `src/components/BottomNav.vue` | `itemsVisibles` computed: filtra los 4 tabs según el plan (`rutas`, `solicitudes`, `mantenciones` requieren módulo; `ajustes` siempre visible) |
| `src/views/Rutas/ListaRutas.vue` | Watch auto-redirect si módulo `rutas` es removido |
| `src/views/Solicitudes/ListaSolicitudes.vue` | Watch auto-redirect si módulo `solicitudes` es removido |
| `src/views/Mantenciones/MiMantencion.vue` | Watch auto-redirect si módulo `mantenciones` es removido |
| `src/views/Mantenciones/HistorialMantenciones.vue` | Watch auto-redirect si módulo `mantenciones` es removido |
| `src/stores/auth.js` | `logout()` llama `resetearPermisos()` antes de limpiar sesión |
| `src/views/Ajustes/Ajustes.vue` | Sección "Plan de la empresa" con nombre del plan y chips de módulos activos |

#### Autenticación con RUT chileno

1. El usuario ingresa el RUT en formato `12.345.678-9` (formato display).
2. El frontend normaliza a `12345678-9` (igual que `normalizar_rut()` del backend).
3. Valida dígito verificador con algoritmo módulo 11 antes de llamar a la API.
4. Si `primer_login = true`, redirige a la pantalla de onboarding; si no, a la lista de rutas.

#### Actualizaciones en tiempo real (WebSocket)

La app conecta automáticamente a `ws://<backend>/ws/conductor/?token=<JWT>` al cargar las solicitudes. El backend (Django Channels, `ConductorConsumer`) envía eventos cuando un administrador aprueba o rechaza una solicitud:

```json
{ "type": "solicitud_actualizada", "solicitud_id": 42, "estado": "aprobado", "respuesta": "..." }
```

El store actualiza la solicitud en el array reactivo de forma inmediata, lo que provoca:
- La tarjeta de la solicitud se resalta brevemente (borde índigo).
- Un toast informa al conductor: *"✓ Tu solicitud fue aprobada"* o *"✗ Tu solicitud fue rechazada"*.

La conexión se reconecta automáticamente si se cae (backoff 1 s → 2 s → 4 s → … máx. 30 s). Al cerrar sesión, el WebSocket se desconecta limpiamente.

#### Modo offline

1. Al cargar rutas, si hay conexión se descarga desde la API y se persiste en SQLite.
2. Sin conexión, se sirven los datos almacenados localmente y se muestra el banner naranja.
3. Las acciones de inicio/fin de ruta se encolan en `acciones_pendientes` y se sincronizan automáticamente al recuperar la conexión.

#### Endpoints exclusivos (app conductores)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/conductor/rutas/` | Lista rutas del conductor autenticado (pendiente, activo, finalizado). Retorna `403` si el plan de la empresa no incluye el módulo `rutas`. |
| `GET` | `/api/conductor/rutas/:id/` | Detalle completo: paradas, vehículo con `km_actuales` |
| `POST` | `/api/conductor/rutas/:id/iniciar/` | Marca la ruta como activa, registra `km_inicio` y actualiza `km_actuales` del vehículo. Crea `EventoRuta` automático. |
| `POST` | `/api/conductor/rutas/:id/finalizar/` | Marca la ruta como finalizada, registra `km_fin` y `notas`. Actualiza `km_actuales`. Crea `EventoRuta` automático. |
| `GET` | `/api/conductor/rutas/:id/comentarios/` | Lista los `EventoRuta` de la ruta (historial) |
| `POST` | `/api/conductor/rutas/:id/comentario/` | Agrega un comentario a la ruta. Body: `{ texto }` |
| `GET` | `/api/conductor/solicitudes/` | Lista las solicitudes del conductor + campo `tipos_permitidos` (lista de tipos habilitados por el plan de la empresa) |
| `POST` | `/api/conductor/solicitudes/` | Crea una solicitud. Acepta `multipart/form-data` si hay foto, JSON si no. Campos: `tipo`, `titulo`, `descripcion`, `prioridad`, `foto` (opcional). Retorna `403` con `codigo: "plan_sin_permiso"` si el tipo no está habilitado por el plan |
| `GET` | `/api/conductor/mantenciones/` | Mantenciones `pendiente` y `en_proceso` del vehículo asignado. Incluye `dias_restantes`, `urgente` (bool), `vehiculo_en_mantencion`. Las `realizadas` ya no se muestran aquí. |
| `GET` | `/api/conductor/mantenciones/:id/` | Detalle completo de una mantención (incluye `foto_comprobante_url` con URL absoluta). |
| `POST` | `/api/conductor/mantenciones/:id/iniciar/` | Transición `pendiente → en_proceso`. Setea `vehiculo.en_mantencion = True`. |
| `POST` | `/api/conductor/mantenciones/:id/completar/` | Transición `en_proceso → realizada`. Acepta `multipart/form-data`: `costo_final` (requerido), `foto_comprobante` (opcional), `fecha_realizada` (opcional), `notas` (opcional). Crea automáticamente un `GastoOperativo` en finanzas (categoría `mantencion`). Setea `vehiculo.en_mantencion = False`. |
| `POST` | `/api/conductor/push-token/` | Registra o actualiza el token FCM del dispositivo. Body: `{ "token": "..." }` |
| `GET` | `/api/conductor/checklist/:id/` | Devuelve los 12 ítems del checklist pre-viaje con estado de documentos pre-cargado (documentos vigentes llegan pre-marcados como OK) y borrador si existe |
| `POST` | `/api/conductor/checklist/:id/` | Guarda el resultado del checklist. Body: `{ respuestas: { item_id: { resultado, observacion } }, firma_base64 }`. Crea/actualiza una `SolicitudConductor` tipo `mantencion` y notifica a los admins |
| `GET` | `/api/notificaciones/` | Notificaciones del conductor paginadas (20/página); filtros `leida`, `tipo` |
| `POST` | `/api/notificaciones/leer/` | Marca notificaciones como leídas (`ids: []` o `todas: true`) |

#### Flujo de mantenciones (conductor → finanzas)

```
Admin (panel web)
  └─ Crea mantención en estado "pendiente"
         │
Conductor (app)
  └─ Ve la mantención en MiMantencion.vue
  └─ Toca → ModalDetalleMantencion → botón "Iniciar mantención"
         │  POST /api/conductor/mantenciones/:id/iniciar/
         │  vehiculo.en_mantencion = True
         │
  └─ Hace el servicio en el taller
         │
  └─ Toca → ModalDetalleMantencion → botón "Marcar como realizada"
         │  → abre ModalCompletarMantencion (costo + foto + fecha + notas)
         │  POST /api/conductor/mantenciones/:id/completar/ (multipart/form-data)
         │  mantencion.estado = "realizada"
         │  mantencion.confirmado_conductor = True
         │  mantencion.fecha_confirmacion = now()
         │  vehiculo.en_mantencion = False
         └─ Crea GastoOperativo (categoria="mantencion", monto=costo_final)
                                  └─ aparece en módulo de Finanzas del panel web
```

El admin puede anular o cambiar el estado manualmente desde el panel web en cualquier momento; los botones de acción del panel **no se eliminaron** (override administrativo). Los campos `Mantencion.confirmado_conductor` (Bool) y `Mantencion.fecha_confirmacion` (DateTime) registran si fue el conductor quien completó el ciclo.

**Backend:** `views_conductor.py`  
**Puerto de desarrollo:** `http://localhost:5174`  
**CORS configurado:** `http://localhost:5174`, `capacitor://localhost`, `http://localhost`

#### Push Notifications (Firebase Cloud Messaging)

El backend usa `firebase-admin` para enviar notificaciones push a dispositivos iOS y Android.

**Configuración (una sola vez):**
1. Crear proyecto en [Firebase Console](https://console.firebase.google.com)
2. Agregar app Android/iOS → descargar `google-services.json` / `GoogleService-Info.plist` al proyecto Capacitor
3. Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada → guardar como `gestion_backend/serviceAccountKey.json`
4. Instalar dependencia: `pip install firebase-admin`

**Flujo:**
1. Al abrir la app, `App.vue` solicita permiso de notificaciones y obtiene el token FCM.
2. El token se registra en `POST /api/conductor/push-token/` y se guarda en `usuario.notif_prefs['push_token']`.
3. Cuando un admin aprueba o rechaza una solicitud, `firebase_push.enviar_push()` envía la notificación al token del conductor.
4. Si la app está en primer plano → toast visual en pantalla. Si está en segundo plano/cerrada → notificación del sistema.

**Módulo:** `g_de_flota/firebase_push.py` — falla silenciosamente si Firebase no está configurado.

---

### 9.15 Solicitudes de Conductores (panel web)

Módulo del panel web que gestiona las solicitudes enviadas por los conductores desde la app móvil. Existen dos vistas según el rol del usuario.

#### Vista USUARIO — `SolicitudesConductores.vue`

Accesible en `/empresa/solicitudes`. Muestra las solicitudes de la propia empresa del usuario.

- **KPI cards** superiores: Pendientes · En revisión · Aprobadas hoy · Total mes
- **Filtros combinados:** buscar por título, estado, tipo, rango de fechas
- **Tabla paginada** (20 registros/página): Conductor · Tipo · Título · Prioridad · Estado · Vehículo · Fecha · Acciones
- **Acciones inline:** ver detalle (👁), aprobar (✓), rechazar (✕)
- **Modal de detalle:** badges de estado/prioridad, grid de info, descripción, respuesta, foto adjunta, botones de acción directa
- **Modal de rechazo:** campo de motivo con validación mínimo 10 caracteres
- **Badge en tiempo real** en el sidebar de `EmpresaLayout.vue`: conteo de pendientes vía WebSocket; polling de 30 s como respaldo
- **Toasts:** confirmación visual de cada acción

#### Vista SUPERADMIN — `SolicitudesAdmin.vue`

Accesible en `/solicitudes`. Permite al Superadmin revisar y gestionar las solicitudes de **cualquier empresa** de la plataforma.

- **Selector de empresa** en la parte superior:
  - Dropdown buscable con las empresas del sistema (cargadas de `/api/empresas/`)
  - Búsqueda local por nombre
  - Avatar con inicial de la empresa, nombre y RUT
  - Botón de limpieza (✕) para cambiar de empresa
  - Al seleccionar empresa: guarda `empresaActiva` en sessionStorage y conecta WebSocket
- **Estado vacío:** cuando no hay empresa seleccionada se muestra un estado placeholder orientativo
- **Mismo conjunto de KPIs, filtros, tabla, modales y toasts** que la vista USUARIO
- **WebSocket por empresa:** al cambiar la empresa seleccionada se desconecta el WS anterior y se conecta uno nuevo a `ws/solicitudes/{nuevaEmpresa_id}/`
- **Badge en sidebar** de `Base.vue`: ítem "Solicitudes" muestra el conteo de pendientes de la empresa activa; se actualiza vía evento `solicitudes-admin-badge` (disparado por la vista) y por polling cada 60 s como respaldo

#### Acciones disponibles (ambas vistas)

| Acción | Endpoint | Descripción |
|---|---|---|
| Marcar "En revisión" | `PUT /api/empresa/solicitudes/:id/` | Cambia estado a `en_revision` |
| Aprobar | `PUT /api/empresa/solicitudes/:id/aprobar/` | Cambia a `aprobado`, crea entidades derivadas (Mantención/Documento según tipo), notifica al conductor |
| Rechazar | `PUT /api/empresa/solicitudes/:id/rechazar/` | Cambia a `rechazado`, requiere motivo ≥10 chars, notifica al conductor |

> Para SUPERADMIN todos los endpoints reciben el parámetro `?empresa_id=X` que es leído por `_get_empresa()` en `views_solicitudes.py`.

#### Creación automática de entidades al aprobar

| Tipo de solicitud | Entidad creada |
|---|---|
| `mantencion` | `Mantencion` en estado `pendiente` con el título/descripción de la solicitud |
| `documento` | `Documento` tipo `revision_tecnica` con el archivo foto adjunto si existe |
| `combustible` / `incidencia` | Sin entidad derivada (solo cambio de estado + notificación) |

#### WebSocket en tiempo real

Ambas vistas se conectan a `ws://host/ws/solicitudes/{empresa_id}/?token=<access_token>`.  
Al recibir `nueva_solicitud`, incrementa el conteo de pendientes y recarga la tabla.  
Si el WebSocket cae, reconecta automáticamente cada 5 s.

#### Permiso de plan

| Código | Categoría | Planes |
|---|---|---|
| `solicitudes.ver` | solicitudes | básico · pro · enterprise |

Migración: `0040_solicitudes_permisos.py`

**Backend:** `views_solicitudes.py` · `consumers.SolicitudesConsumer`  
**Modelo:** `SolicitudConductor`  
**Rutas WS:** `ws/solicitudes/<empresa_id>/`

---

### 9.10 Notificaciones

Sistema de notificaciones in-app con soporte de WebSocket (Django Channels). Tipos: `mantencion_por_vencer`, `mantencion_vencida`, `documento_por_vencer`, `documento_vencido`, `seguridad`, `actividad`, `limite_plan`.

Cada usuario configura sus preferencias de canal (in-app, email) por categoría desde su perfil.

**Vistas:** `Notificaciones.vue` · `PreferenciasNotificaciones.vue`  
**Componente:** `NotificacionesBell.vue` (campana en la barra de navegación)

### 9.11 Auditoría (Logs)

Registro de eventos de seguridad y actividad del sistema. Accesible únicamente por SUPERADMIN.

**Vista:** `Logs.vue`

**Campos almacenados por evento:**

| Campo | Descripción |
|---|---|
| `tipo` | `SEGURIDAD` o `ACTIVIDAD` |
| `accion` | Código del evento (`login_exitoso`, `documento_subido`, etc.) |
| `usuario` | FK al usuario que generó la acción |
| `ip` | IP del cliente (soporta proxy `X-Forwarded-For`) |
| `user_agent` | User-Agent completo del navegador |
| `so` | Sistema operativo detectado (Windows 10/11, macOS, Android, iOS, Linux) |
| `metodo` | Método HTTP de la request (GET, POST, PUT, DELETE) |
| `endpoint` | URL path que generó el evento (ej: `/api/empresa/documentos/`) |
| `detalle` | JSON con contexto específico — incluye `cambios` en ediciones |
| `fecha` | Timestamp con auto_now_add |

**Campos calculados en el serializer** (no almacenados en BD):
- `navegador` — nombre del browser extraído del `user_agent` (Chrome, Edge, Firefox, Opera, Safari, Internet Explorer, Otro)
- `descripcion` — oración legible en español que resume el evento (ej: "Juan subió Permiso de circulación para ABC-123")

**Diff antes/después en ediciones** — los eventos de edición de vehículo, conductor, flota, mantención y documento incluyen en `detalle.cambios` una lista de campos modificados con valor anterior y nuevo:
```json
{ "cambios": [{"campo": "marca", "antes": "Toyota", "despues": "Ford"}] }
```

**Detalles enriquecidos de documentos** — todos los eventos de documentos registran: ID, tipo, entidad, nombre del archivo, patente del vehículo o nombre del conductor, fechas de emisión/vencimiento y notas.

**Helpers en `audit.py`:** `registrar_log()`, `_parse_navegador(ua)`, `_parse_so(ua)`, `_diff_campos(antes, despues)`, `_snap(obj, campos)`.

**Filtros disponibles en la UI:** tipo, acción, usuario/IP, rango de fechas. Paginación de 50 registros.

### 9.12 Configuración de Cuenta

Panel de configuración personal con cuatro secciones:

| Tab | Contenido |
|---|---|
| Perfil | Edición de nombre, email y contraseña |
| Notificaciones | Preferencias de canal por categoría |
| Mi Plan | Uso actual del plan y solicitud de cambio |
| Apariencia | Preferencias visuales de la interfaz |

**Vista:** `ConfiguracionPage.vue` + tabs: `PerfilTab.vue` · `NotificacionesTab.vue` · `MiPlanTab.vue` · `AparienciaTab.vue`

---

## 10. Referencia de la API REST

Todos los endpoints (excepto `/api/login/` y `/api/token/refresh/`) requieren el header:

```
Authorization: Bearer <access_token>
```

### Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/login/` | Inicio de sesión por RUT |
| `POST` | `/api/token/refresh/` | Renovación de access token |

### Dashboard

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/dashboard/` | SUPERADMIN | Dashboard global de plataforma |
| `GET` | `/api/empresa/dashboard/` | USUARIO | Dashboard de la empresa activa |

### Empresas

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/empresas/` | Listar empresas |
| `POST` | `/api/empresas/crear/` | Crear empresa |
| `GET/PUT/DELETE` | `/api/empresas/<id>/` | Detalle, editar, eliminar |

### Usuarios

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/usuarios/` | Listar usuarios |
| `POST` | `/api/usuarios/crear/` | Crear usuario |
| `GET/PUT/DELETE` | `/api/usuarios/<id>/` | Detalle, editar, eliminar |
| `POST` | `/api/usuarios/<id>/reset-password/` | Restablecer contraseña |
| `POST` | `/api/usuarios/<id>/toggle-block/` | Bloquear / desbloquear |
| `GET` | `/api/usuarios/<id>/historial/` | Historial de actividad |
| `GET/PUT` | `/api/usuarios/<id>/permisos/` | Ver / asignar permisos |

### Conductores

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/conductores/` | Listar / crear conductores |
| `GET/PUT/DELETE` | `/api/empresa/conductores/<id>/` | Detalle, editar, eliminar |
| `POST` | `/api/empresa/conductores/<id>/asignar/` | Asignar vehículo |
| `POST` | `/api/empresa/conductores/<id>/desasignar/` | Desasignar vehículo |

### Flota y Vehículos

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/admin/flotas/` | Todas las flotas (SUPERADMIN) |
| `GET/POST` | `/api/empresa/flotas/` | Listar / crear flotas |
| `GET/PUT/DELETE` | `/api/empresa/flotas/<id>/` | Detalle, editar, eliminar |
| `GET/POST` | `/api/empresa/vehiculos/` | Listar / crear vehículos |
| `GET/PUT/DELETE` | `/api/empresa/vehiculos/<id>/` | Detalle, editar, eliminar |

### Mantenciones

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/mantenciones/` | Listar / crear mantenciones |
| `GET/PUT/DELETE` | `/api/empresa/mantenciones/<id>/` | Detalle, editar, eliminar |
| `GET` | `/api/empresa/mantenciones/resumen/` | KPIs de mantenciones |
| `GET` | `/api/empresa/mantenciones/calendario/` | Vista calendario |
| `GET` | `/api/empresa/mantenciones/sugerencias/` | Sugerencias predictivas |

### Mantenimiento Predictivo

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/planes-mantenimiento/` | Planes (ViewSet) |
| `GET/POST` | `/api/empresa/alertas-mantenimiento/` | Alertas (ViewSet) |
| `GET/POST` | `/api/empresa/vehiculo-planes/` | Asignar vehículo a plan |
| `GET/PUT/DELETE` | `/api/empresa/vehiculo-planes/<id>/` | Detalle de asignación |
| `GET` | `/api/empresa/predictivo/resumen/` | Resumen de estado predictivo |
| `POST` | `/api/empresa/predictivo/generar-alertas/` | Generar alertas pendientes |
| `GET` | `/api/empresa/simulador-vencimientos/` | Simulador de fechas |

### Documentos

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/documentos/` | Listar / subir documentos |
| `GET/PUT/DELETE` | `/api/empresa/documentos/<id>/` | Detalle, editar, eliminar |
| `GET` | `/api/empresa/documentos/<id>/descargar/` | Descarga del archivo |
| `POST` | `/api/empresa/documentos/<id>/renovar/` | Crear nueva versión |

### Finanzas

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/gastos/` | Listar / registrar gastos |
| `GET/PUT/DELETE` | `/api/empresa/gastos/<id>/` | Detalle, editar, eliminar |
| `GET` | `/api/empresa/gastos/exportar/` | Exportar a XLSX |
| `GET/POST` | `/api/empresa/presupuesto/` | Listar / crear presupuestos |
| `GET/PUT/DELETE` | `/api/empresa/presupuesto/<id>/` | Detalle de presupuesto |
| `GET` | `/api/admin/finanzas/` | Dashboard SaaS (SUPERADMIN) |
| `GET` | `/api/admin/finanzas/historico/` | Histórico MRR (SUPERADMIN) |

### Reportes

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/empresa/reportes/mantencion/` | Reporte de mantenciones |
| `GET` | `/api/empresa/reportes/flota/` | Estado de la flota |
| `GET` | `/api/empresa/reportes/tco/` | Costo Total de Operación |
| `GET` | `/api/empresa/reportes/conductores/` | Estadísticas de conductores |
| `GET` | `/api/empresa/reportes/presupuesto/` | Presupuesto vs. gasto real por mes |
| `GET` | `/api/empresa/reportes/documentos/` | Estado documental y vencimientos |
| `GET` | `/api/empresa/reportes/combustible/` | Gasto en combustible |
| `GET` | `/api/empresa/reportes/exportar/` | Exportación XLSX (param: `tipo`) |
| `GET` | `/api/admin/reportes/empresas/` | Reporte global (SUPERADMIN) |

### Rutas y Trabajos

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/empresa/rutas/` | Listar / crear rutas. GET incluye `resumen` con `finalizadas_mes`. |
| `GET/PUT/DELETE` | `/api/empresa/rutas/<id>/` | Detalle, editar, eliminar |
| `POST` | `/api/empresa/rutas/<id>/iniciar/` | Iniciar ruta (registra km_inicio, crea EventoRuta auto) |
| `POST` | `/api/empresa/rutas/<id>/finalizar/` | Finalizar ruta (registra km_fin + notas, actualiza vehículo, crea EventoRuta auto) |
| `POST` | `/api/empresa/rutas/<id>/cancelar/` | Cancelar ruta con motivo (crea EventoRuta auto) |
| `POST` | `/api/empresa/rutas/calcular/` | Calcular trayecto OSRM — devuelve solo `distancia_km`, `duracion_min`, `polyline` |
| `GET/POST` | `/api/empresa/rutas/<id>/comentarios/` | GET lista eventos de la ruta; POST crea comentario manual del admin |

### App conductores (endpoints exclusivos)

> Requieren `rol = CONDUCTOR`. Usan el mismo JWT que el resto de la API.

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/conductor/rutas/` | Rutas asignadas al conductor (pendiente / activo / finalizado) |
| `GET` | `/api/conductor/rutas/<id>/` | Detalle completo: paradas, vehículo |
| `POST` | `/api/conductor/rutas/<id>/iniciar/` | Inicia la ruta — registra `km_inicio`, crea `EventoRuta` auto |
| `POST` | `/api/conductor/rutas/<id>/finalizar/` | Finaliza la ruta — registra `km_fin` y `notas`, crea `EventoRuta` auto |
| `GET` | `/api/conductor/rutas/<id>/comentarios/` | Historial de `EventoRuta` de la ruta |
| `POST` | `/api/conductor/rutas/<id>/comentario/` | Agrega comentario manual. Body: `{ texto }` |
| `GET` | `/api/conductor/solicitudes/` | Lista solicitudes del conductor, ordenadas por fecha desc |
| `POST` | `/api/conductor/solicitudes/` | Crea solicitud — `multipart/form-data` si incluye foto, JSON si no |

**Backend:** `views_conductor.py`

### Solicitudes de Conductores (panel web — USUARIO)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/empresa/solicitudes/` | Lista paginada con filtros: `estado`, `tipo`, `conductor_id`, `fecha_desde`, `fecha_hasta`, `buscar`, `page`, `page_size`. Incluye `resumen` con contadores |
| `GET` | `/api/empresa/solicitudes/conteo/` | Retorna `{ pendientes: N }` — lightweight para badge del sidebar |
| `GET` | `/api/empresa/solicitudes/<id>/` | Detalle de una solicitud con datos del conductor, vehículo y respondido_por |
| `PUT` | `/api/empresa/solicitudes/<id>/` | Cambia estado a `en_revision` |
| `PUT` | `/api/empresa/solicitudes/<id>/aprobar/` | Aprueba la solicitud; crea `Mantencion` o `Documento` automáticamente; notifica al conductor |
| `PUT` | `/api/empresa/solicitudes/<id>/rechazar/` | Rechaza la solicitud; requiere `respuesta` ≥10 caracteres; notifica al conductor |

**Backend:** `views_solicitudes.py` · `SolicitudConductorSerializer`  
**Autenticación:** `IsAuthenticated` (USUARIO ve solo su empresa; SUPERADMIN pasa `?empresa_id=`)

### Notificaciones

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/notificaciones/` | Listar notificaciones del usuario |
| `GET` | `/api/notificaciones/no-leidas/` | Contador de no leídas |
| `POST` | `/api/notificaciones/leer/` | Marcar como leídas |
| `GET/PUT` | `/api/notificaciones/preferencias/` | Preferencias de canal |

### Planes de Suscripción (SUPERADMIN)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/POST` | `/api/configuracion/planes/` | Listar / crear planes |
| `GET/PUT/DELETE` | `/api/configuracion/planes/<id>/` | Detalle, editar, eliminar |
| `POST` | `/api/configuracion/planes/<id>/asignar/` | Asignar plan a empresa |
| `GET/PUT` | `/api/configuracion/planes/<id>/permisos/` | Permisos por defecto del plan |
| `GET` | `/api/empresa/plan-uso/` | Uso actual del plan (USUARIO) |
| `POST` | `/api/empresa/solicitar-cambio-plan/` | Solicitar cambio de plan |

### Configuración

| Método | Endpoint | Descripción |
|---|---|---|
| `GET/PUT` | `/api/usuario/perfil/` | Perfil del usuario autenticado |
| `POST` | `/api/usuario/cambiar-password/` | Cambio de contraseña |
| `GET` | `/api/empresa/plan-historial/` | Historial de cambios de plan |
| `GET` | `/api/permisos/` | Catálogo de permisos disponibles |
| `GET` | `/api/logs/` | Logs de auditoría (SUPERADMIN) |

---

## 11. Modelo de datos

### Diagrama de relaciones principales

```
PlanSuscripcion ──< Permiso (M2M)
      │
      └──< Empresa ──< CambioPlan
                │
                │
                ├──< Usuario ──< Permiso (M2M)
                │       └──< Asignacion
                │
                ├──< Flota ──< Vehiculo
                │                 ├──< Mantencion
                │                 ├──< Documento (docs_v)
                │                 ├──< GastoOperativo
                │                 ├──< MantencionProgramada ──< AlertaMantencion
                │                 ├──< VehiculoPlan ──> PlanMantenimiento
                │                 └──< Ruta (conductor, vehiculo)
                │                           ├──< Parada
                │                           └──< EventoRuta
                │
                ├──< PlanMantenimiento ──< ReglaMantenimiento
                ├──< GastoOperativo
                ├──< PresupuestoMensual
                ├──< Ruta
                └──< Documento (empresa)

Usuario (CONDUCTOR) ──< Documento (docs_c)
                    └──< SolicitudConductor
```

### Modelos principales

| Modelo | Descripción |
|---|---|
| `PlanSuscripcion` | Planes SaaS con límites y módulos habilitados |
| `Empresa` | Empresa cliente con datos cifrados |
| `CambioPlan` | Auditoría de cambios de plan |
| `Usuario` | Usuario del sistema (hereda de `AbstractUser`) |
| `Permiso` | Permiso granular identificado por `codigo` |
| `Flota` | Agrupación de vehículos dentro de una empresa |
| `Vehiculo` | Vehículo con patente, datos técnicos y km actuales |
| `Asignacion` | Relación activa conductor ↔ vehículo |
| `Mantencion` | Registro correctivo de mantención |
| `Documento` | Documento legal con control de vigencia |
| `GastoOperativo` | Gasto categorizado vinculado a empresa/vehículo |
| `PresupuestoMensual` | Presupuesto mensual por empresa |
| `PlanMantenimiento` | Plan predictivo con conjunto de reglas |
| `ReglaMantenimiento` | Regla de mantenimiento periódico |
| `VehiculoPlan` | Asignación de vehículo a plan de mantenimiento |
| `MantencionProgramada` | Instancia programada de una regla sobre un vehículo |
| `AlertaMantencion` | Alerta generada por proximidad de vencimiento |
| `Notificacion` | Notificación in-app por usuario |
| `LogAuditoria` | Registro de eventos de seguridad y actividad — campos: tipo, accion, usuario (FK), detalle (JSON), ip, **user_agent**, fecha |
| `Ruta` | Ruta planificada con conductor, vehículo, estado, distancia, duración, polyline, km inicio/fin y notas |
| `Parada` | Punto de parada de una ruta (origen, intermedia, destino) con coordenadas |
| `EventoRuta` | Evento de historial de una ruta: tipo (`auto`/`comentario`), texto, autor opcional y timestamp |
| `SolicitudConductor` | Solicitud creada por un conductor: tipo (`mantencion`, `combustible`, `incidencia`, `documento`), título, descripción, prioridad (`baja`, `media`, `alta`), estado (`pendiente`, `en_revision`, `aprobado`, `rechazado`), foto opcional (ImageField), respuesta del administrador |

---

## 12. Frontend — Estructura de vistas

### Layout por rol

**SUPERADMIN** utiliza `Base.vue` como layout principal con navegación lateral que incluye: Empresas, Usuarios, Planes, Permisos, Finanzas, Reportes y Logs.

**USUARIO** utiliza `EmpresaLayout.vue` con navegación que incluye: Dashboard, Flota, Conductores, Mantenciones, Predictivo, Documentos, Rutas, Finanzas, Reportes, Notificaciones y Configuración.

**CONDUCTOR** accede a una vista simplificada con información de su vehículo y asignación actual.

### Dashboards

`Dashboard.vue` detecta el rol del usuario y renderiza la vista correspondiente:

**Dashboard USUARIO:**
- KPIs: vehículos activos, mantenciones pendientes, gastos del mes, presupuesto disponible
- Gráfico dona: distribución del estado de la flota (activos / docs por vencer / en mantención)
- Gráfico de barras: vehículos por flota
- Gráfico de línea: mantenciones por mes (últimos 12 meses)
- Barra de progreso: cumplimiento del presupuesto mensual
- Barra de progreso: cumplimiento predictivo (al día vs. vencidas)
- Widget: próximas mantenciones (7 días)

**Dashboard SUPERADMIN:**
- KPIs: empresas activas, total vehículos, MRR, suscripciones activas
- Gráfico de línea: crecimiento de empresas
- Gráfico dona: distribución de flotas por empresa
- Gráfico dona: distribución de empresas por plan

### Componentes globales

| Componente | Descripción |
|---|---|
| `AppToast.vue` | Notificaciones no intrusivas (top-right, z-index 9999) |
| `ConfirmModal.vue` | Modal de confirmación genérico reutilizable |
| `NotificacionesBell.vue` | Campana con contador de no leídas en la navbar |
| `PermisoToast.vue` | Aviso de permiso denegado |
| `PlanUsageBanner.vue` | Banner de advertencia de límite de plan |
| `LimitePlanModal.vue` | Modal bloqueante al alcanzar el límite del plan |
| `MapaRuta.vue` | Mapa Leaflet reutilizable — renderiza polilínea y marcadores de paradas (origen/parada/destino) |

---

## 13. Sistema de notificaciones

### In-app (tiempo real)

Las notificaciones se reciben a través de una conexión **WebSocket** (Django Channels con `InMemoryChannelLayer`). El componente `NotificacionesBell.vue` mantiene la conexión abierta y actualiza el contador en tiempo real.

### Preferencias de canal

Cada usuario configura desde su perfil qué tipos de notificaciones recibe por cada canal:

```json
{
  "inapp": ["mantencion", "documentos", "seguridad"],
  "email": ["mantencion", "documentos"],
  "push_token": ""
}
```

Las categorías de notificación son: `mantencion`, `documentos`, `seguridad`, `actividad`.

### Tipos de notificación

| Tipo | Categoría | Disparado por |
|---|---|---|
| `mantencion_por_vencer` | mantencion | Regla predictiva próxima a vencer |
| `mantencion_vencida` | mantencion | Regla predictiva vencida |
| `documento_por_vencer` | documentos | Documento ≤ 30 días para vencer |
| `documento_vencido` | documentos | Documento con fecha pasada |
| `seguridad` | seguridad | Bloqueo de cuenta, cambio de contraseña |
| `actividad` | actividad | Asignaciones, cambios de estado |
| `limite_plan` | seguridad | Empresa cerca del límite del plan |

---

## 14. Alertas de interfaz (Toasts)

Para mostrar una notificación desde cualquier vista Vue, emitir un `CustomEvent` en el objeto `window`:

```javascript
window.dispatchEvent(new CustomEvent('app-toast', {
  detail: {
    tipo:    'exito',              // 'exito' | 'error' | 'info' | 'advertencia'
    mensaje: 'Operación completada exitosamente.',
  }
}))
```

El componente `AppToast.vue` escucha este evento globalmente y muestra la alerta en la esquina superior derecha durante 4 segundos.

---

## 16. Sistema de emails transaccionales

### Arquitectura

La configuración SMTP es **dinámica** — se almacena cifrada en la base de datos (modelo `ConfiguracionSistema`) y se administra desde el panel del SUPERADMIN en **Configuración → Email**. No requiere reiniciar el servidor al cambiar credenciales.

### Archivo principal
`g_de_flota/email_service.py`

### Funciones disponibles

| Función | Trigger |
|---|---|
| `email_bienvenida()` | Crear usuario nuevo |
| `email_pago_aprobado()` | Pago Webpay / OneClick aprobado |
| `email_pago_rechazado()` | Pago rechazado por Transbank |
| `email_suscripcion_vence()` | Cron: 30/15/7/1 días antes del vencimiento |
| `email_suscripcion_gracia()` | Cron: suscripción pasa a estado "gracia" |
| `email_suscripcion_bloqueada()` | Cron: empresa suspendida |
| `email_documento_vence()` | Cron: documento vencido o por vencer |
| `email_mantencion_vence()` | Futuro hook en gestión de mantenciones |
| `email_solicitud_nueva()` | Conductor crea solicitud |
| `email_solicitud_resuelta()` | Admin aprueba o rechaza solicitud |
| `email_ruta_asignada()` | Ruta asignada a conductor |
| `email_checklist_fallas()` | Conductor reporta fallas en checklist pre-viaje |

### Reglas de uso
- Todas las llamadas están envueltas en `try/except` — nunca interrumpen el flujo HTTP.
- La contraseña SMTP se cifra con Fernet antes de guardar; nunca se retorna en texto plano.
- Cada evento tiene su toggle individual en `ConfiguracionSistema` (ej: `notif_pago_aprobado`).
- Si `email_activo = False`, no se envía ningún email.

### Endpoints
| Método | URL | Descripción |
|---|---|---|
| `GET/PUT` | `/api/admin/email/` | Leer/actualizar configuración SMTP y toggles |
| `POST` | `/api/admin/email/test/` | Enviar email de prueba (body: `{ email_destino }`) |

---

## 15. Variables de entorno

### Archivo centralizado

Existe **un único `.env`** en la raíz del monorepo (`gestion_flota/.env`). No debe commitearse al repositorio.

- **Django** lo lee con `python-dotenv`: `load_dotenv(BASE_DIR.parent / '.env')` (en `settings.py`).
- **Vite** (panel web y app conductores) lo lee con `envDir: '..'` en `vite.config.js`.

| Variable | Requerida | Leída por | Descripción |
|---|---|---|---|
| `SECRET_KEY` | Sí | Django | Clave secreta de Django |
| `ENCRYPTION_KEY` | Sí | Django | Clave base para derivar la clave Fernet |
| `FERNET_KEY` | Sí | Django | Clave Fernet en formato base64-url |
| `DEBUG` | No | Django | `True` para desarrollo, `False` para producción |
| `ALLOWED_HOSTS` | No | Django | Hosts permitidos (separados por coma) |
| `VITE_API_URL` | No | Vite | URL base de la API; vacío = peticiones relativas (proxy Vite) |
| `EMAIL_BACKEND` | No | Django | Backend de email (por defecto: consola; en producción no se usa — la config es dinámica en BD) |
| `FRONTEND_URL` | No | Django | URL pública del frontend para links en emails (por defecto: `http://localhost:7183`) |
| `TRANSBANK_ENVIRONMENT` | No | Django | `integration` (por defecto) o `production` |
| `TRANSBANK_COMMERCE_CODE` | No | Django | Código de comercio Webpay Plus |
| `TRANSBANK_API_KEY` | No | Django | API key de Transbank |

### Configuración CORS

En desarrollo, el backend acepta peticiones desde:
- `http://localhost:7183` (panel web)
- `http://localhost:5174` (app conductores en navegador)
- `capacitor://localhost` y `http://localhost` (app conductores en dispositivo)

En producción, configurar `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` en `settings.py` con los dominios reales.

---

## 16. Manejo de errores (v2.5)

Sistema profesional de manejo de errores implementado para garantizar estabilidad en pruebas QA y producción.

### Backend

#### `error_helpers.py` — Helpers centralizados

Ubicación: `gestion_backend/g_de_flota/error_helpers.py`

| Función | Descripción |
|---|---|
| `error_response(mensaje, codigo, status, detalle)` | Retorna `JsonResponse` estandarizado con `error`, `codigo` y `detalle` opcionales |
| `validar_campos(body, requeridos)` | Verifica campos obligatorios y retorna `(valido: bool, msg: str)` |
| `vista_segura` | Decorador para métodos de vistas-clase: captura `json.JSONDecodeError`, `PermissionError` y cualquier excepción no controlada; registra log SEGURIDAD en errores 500 |

**Códigos de error estándar:**

| Código | HTTP | Significado |
|---|---|---|
| `SIN_AUTENTICACION` | 401 | Token inválido o expirado |
| `SIN_PERMISO` | 403 | Rol insuficiente |
| `NO_ENCONTRADO` | 404 | Recurso inexistente |
| `VALIDACION` | 400 | Campo faltante o mal formado |
| `LIMITE_PLAN` | 403 | Límite del plan alcanzado |
| `MODULO_NO_INCLUIDO` | 403 | Módulo no disponible en el plan |
| `SUSCRIPCION_BLOQUEADA` | 402 | Empresa sin suscripción activa |
| `ERROR_INTERNO` | 500 | Error no controlado del servidor |

#### `ErrorHandlerMiddleware` — Captura global Django

Agregado en `gestion_backend/g_de_flota/middleware.py` y registrado en `settings.py` antes de `ConfiguracionSeguridadMiddleware`.

Captura excepciones que escapan a las vistas (Django normalmente retornaría HTML de error) y las convierte en JSON `{'error': ..., 'codigo': 'ERROR_INTERNO'}` con status 500. Adicionalmente registra el traceback en `LogAuditoria`.

### Frontend

#### `apiFetch` mejorado — `src/utils/api.js`

- **Timeout de 15 segundos** con `AbortController`; lanza `ApiError` con código `TIMEOUT`
- **`ApiError`** — clase de error exportable con campos `status` y `codigo`
- **Parseo seguro de JSON**: solo parsea si `Content-Type: application/json`; no rompe con respuestas no-JSON
- **`safeJsonParse`** interno: todos los `JSON.parse` de `localStorage`/`sessionStorage` están protegidos
- **Sin conexión** → `ApiError` código `SIN_CONEXION`
- Mantiene la misma lógica de inyección de `empresa_id`, refresh de JWT y eventos globales de plan/suscripción

#### `useAsync` — `src/composables/useAsync.js`

Composable reutilizable que evita repetir el patrón `cargando / error / try-catch` en cada componente:

```js
const { cargando, error, ejecutar } = useAsync()

async function guardar() {
  await ejecutar(
    () => apiFetch('/api/...', { method: 'POST', body: datos }),
    { mensajeError: 'Error al guardar. Intenta nuevamente.' }
  )
}
```

Opciones: `mensajeError`, `mostrarToast` (default `true`), `onError` (callback).

#### `ErrorBoundary.vue` — `src/components/ErrorBoundary.vue`

Componente que captura errores de renderizado de Vue (`onErrorCaptured`) y muestra una pantalla de recuperación con botón "Reintentar" en lugar de una pantalla en blanco.

Está envuelto en `App.vue`:
```vue
<ErrorBoundary>
  <RouterView />
</ErrorBoundary>
```

#### `router/index.js` — Guards seguros

Todos los accesos a `localStorage`/`sessionStorage` del router guard usan `safeJsonParse`, previniendo que un JSON corrupto bloquee la navegación silenciosamente.

---

