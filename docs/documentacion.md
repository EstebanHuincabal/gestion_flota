# Sistema de Gestión de Flota — Documentación Técnica

> **Versión:** 2.1 · **Última actualización:** Mayo 2026  
> **Stack:** Django 5 · Vue 3 · SQLite · JWT

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
10. [Referencia de la API REST](#10-referencia-de-la-api-rest)
11. [Modelo de datos](#11-modelo-de-datos)
12. [Frontend — Estructura de vistas](#12-frontend--estructura-de-vistas)
13. [Sistema de notificaciones](#13-sistema-de-notificaciones)
14. [Alertas de interfaz (Toasts)](#14-alertas-de-interfaz-toasts)
15. [Variables de entorno](#15-variables-de-entorno)

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
| **Rutas y Trabajos** | Planificación de rutas con mapa Leaflet, cálculo OSRM, detección de peajes y liquidación automática de costos |
| **Notificaciones** | Alertas in-app en tiempo real (WebSocket) + preferencias de canal |
| **Permisos** | Una capa basada en el plan: módulos visibles y acciones disponibles se definen a nivel de plan de suscripción |

---

## 2. Arquitectura del sistema

El proyecto sigue una arquitectura **desacoplada** (API REST + SPA):

```
┌─────────────────────────────────────────────────┐
│              Cliente (Navegador)                 │
│   Vue 3 SPA · Vite · TailwindCSS · Chart.js      │
│              http://localhost:7183               │
└────────────────────┬────────────────────────────┘
                     │ HTTP/JSON (JWT Bearer)
                     │ WebSocket (ws://)
┌────────────────────▼────────────────────────────┐
│             Backend (Django 5 / ASGI)            │
│   Django REST Framework · SimpleJWT · Channels   │
│              http://localhost:8000               │
└────────────────────┬────────────────────────────┘
                     │ ORM
┌────────────────────▼────────────────────────────┐
│              Base de datos                       │
│              SQLite (desarrollo)                 │
└─────────────────────────────────────────────────┘
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

**Frontend**

| Tecnología | Versión | Propósito |
|---|---|---|
| Vue.js 3 (Composition API) | — | Framework SPA |
| Vite | — | Bundler y servidor de desarrollo |
| Vue Router | — | Navegación entre vistas |
| TailwindCSS | — | Estilos utilitarios |
| Chart.js | — | Visualizaciones y gráficos |

---

## 3. Estructura del repositorio

```
gestion_flota/
├── iniciar.ps1                   # Script de arranque conjunto (Windows)
├── docs/
│   └── documentacion.md          # Este archivo
│
├── gestion-frontend/             # Aplicación Vue 3
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
│   │       └── usuarios/
│   └── package.json
│
└── gestion_backend/              # Backend Django
    ├── manage.py
    ├── .env                      # Variables de entorno (no commitear)
    ├── requirements.txt
    ├── g_de_flota/               # App principal
    │   ├── models.py             # Modelos ORM
    │   ├── views.py              # Endpoints principales
    │   ├── views_gastos.py       # Endpoints de finanzas
    │   ├── views_reportes.py     # Endpoints de reportes
    │   ├── views_documentos.py   # Endpoints de documentos
    │   ├── views_planes.py       # Endpoints de planes
    │   ├── views_config.py       # Perfil y configuración
    │   ├── views_rutas.py        # Endpoints de rutas y trabajos
    │   ├── ruta_calculator.py    # Motor de cálculo (OSRM, peajes, costos)
    │   ├── serializers.py        # Serializadores DRF
    │   ├── backends.py           # Backend de autenticación por RUT
    │   ├── middleware.py         # Middleware de seguridad
    │   └── management/
    │       └── commands/
    │           └── seed_peajes.py  # Carga inicial de peajes de Chile
    └── gestion_backend/
        ├── settings.py
        ├── urls.py               # Router principal (79 endpoints)
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

Desde la raíz del proyecto ejecutar el script PowerShell que levanta ambos servidores simultáneamente:

```powershell
.\iniciar.ps1
```

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

# Cargar datos iniciales de peajes (primera vez)
python manage.py seed_peajes

# Iniciar servidor ASGI
python manage.py runserver
# → API disponible en http://localhost:8000
```

**Frontend (terminal 2)**

```bash
cd gestion-frontend

# Instalar dependencias (primera vez)
npm install

# Iniciar servidor de desarrollo
npm run dev
# → Interfaz disponible en http://localhost:7183
```

### Variables de entorno necesarias

Crear `gestion_backend/.env` con el siguiente contenido mínimo (ver sección 15 para detalle completo):

```ini
SECRET_KEY=<clave-django-aleatoria>
ENCRYPTION_KEY=<clave-cifrado-fernet>
FERNET_KEY=<clave-fernet-base64>
DEBUG=True
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

### Asignación de plan

El Superadmin asigna o cambia el plan de una empresa directamente desde los formularios de creación y edición de empresa. Cada cambio queda registrado en `CambioPlan` con el motivo, el usuario responsable y los planes anterior y posterior.

### Uso del plan

El endpoint `GET /api/empresa/plan-uso/` devuelve el consumo actual vs. los límites del plan activo (flotas, vehículos, conductores, usuarios). Este dato alimenta el banner de advertencia en la interfaz.

---

## 9. Módulos del sistema

### 9.1 Gestión de Empresas (SUPERADMIN)

Permite al Superadmin crear, editar, suspender y eliminar empresas cliente. Incluye asignación de plan, visualización de KPIs por empresa y acceso a su historial de cambios de plan.

**Vistas:** `ListaEmpresas.vue` · `NuevaEmpresa.vue` · `EditarEmpresa.vue` · `DetalleEmpresa.vue`

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

Módulo de planificación y seguimiento de rutas vehiculares. Permite crear rutas con conductor, vehículo y paradas, calcular el trayecto óptimo, detectar peajes en la ruta y liquidar los costos operativos asociados al finalizar.

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
| `finalizado` | Completada — se registra `km_fin`, se crean gastos automáticos |
| `cancelado` | Cancelada con motivo registrado |

#### Cálculo de ruta

Al crear o calcular una ruta, el sistema:

1. **Geocodificación:** Nominatim (`nominatim.openstreetmap.org`) resuelve cada dirección a coordenadas (debounce 500 ms).
2. **Trazado OSRM:** El motor de enrutamiento `router.project-osrm.org` calcula el polilínea óptimo entre todas las paradas. Si el servicio no está disponible, la ruta se guarda sin distancia estimada.
3. **Detección de peajes:** Se filtran los peajes activos en la base de datos que estén dentro del radio de detección configurado (por defecto 500 m) de cualquier punto del polilínea.
4. **Estimación de costos:**
   - Combustible: `(km / 100) × consumo_l_100km × precio_litro`
   - Peajes: suma de tarifas detectadas según la categoría del vehículo
   - Se usan los precios configurados en `ConfiguracionRuta` de la empresa.

#### Liquidación al finalizar

Al marcar una ruta como finalizada:
- Se actualiza `vehiculo.km_actuales = km_fin`.
- Se crea automáticamente un `GastoOperativo` de categoría `combustible`.
- Si hubo peajes, se crea un segundo `GastoOperativo` de categoría `peaje`.

#### Gestión de peajes

Los peajes se cargan con el comando de gestión `seed_peajes` (21 puntos de cobro en rutas principales de Chile: Ruta 5 Norte/Sur, Ruta 68, Ruta 78, Ruta 60 CH, Ruta 57). Cada peaje tiene 5 registros por ubicación (liviano, moto, camión 2 ejes, camión 3+ ejes, bus), con tarifas aproximadas del MOP.

La empresa puede ajustar el radio de detección y los precios de combustible desde el panel de configuración.

**Vistas:** `Rutas.vue` · `MapaRuta.vue`  
**Backend:** `views_rutas.py` · `ruta_calculator.py`  
**Modelos:** `Ruta` · `Parada` · `Peaje` · `PeajeRuta` · `ConfiguracionRuta`  
**Permiso requerido:** `rutas.ver` (ver lista y detalle), `rutas.crear` (crear, editar, cambiar estado)

---

### 9.10 Notificaciones

Sistema de notificaciones in-app con soporte de WebSocket (Django Channels). Tipos: `mantencion_por_vencer`, `mantencion_vencida`, `documento_por_vencer`, `documento_vencido`, `seguridad`, `actividad`, `limite_plan`.

Cada usuario configura sus preferencias de canal (in-app, email) por categoría desde su perfil.

**Vistas:** `Notificaciones.vue` · `PreferenciasNotificaciones.vue`  
**Componente:** `NotificacionesBell.vue` (campana en la barra de navegación)

### 9.11 Auditoría (Logs)

Registro de eventos de seguridad y actividad del sistema. Accesible únicamente por SUPERADMIN.

**Vista:** `Logs.vue`

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
| `GET/POST` | `/api/empresa/rutas/` | Listar / crear rutas |
| `GET/PUT/DELETE` | `/api/empresa/rutas/<id>/` | Detalle, editar, eliminar |
| `POST` | `/api/empresa/rutas/<id>/iniciar/` | Iniciar ruta (registra km_inicio, cambia a activo) |
| `POST` | `/api/empresa/rutas/<id>/finalizar/` | Finalizar ruta (registra km_fin, crea gastos, actualiza vehículo) |
| `POST` | `/api/empresa/rutas/<id>/cancelar/` | Cancelar ruta con motivo |
| `POST` | `/api/empresa/rutas/calcular/` | Calcular trayecto (OSRM), detectar peajes y estimar costos |
| `GET` | `/api/empresa/rutas/peajes/` | Listar peajes activos (filtrable por ruta/categoría) |
| `GET/PUT` | `/api/empresa/rutas/configuracion/` | Configuración de precios y radio de detección |

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
                │       └──── ConfiguracionRuta (1:1)
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
                │                           └──< PeajeRuta ──> Peaje
                │
                ├──< PlanMantenimiento ──< ReglaMantenimiento
                ├──< GastoOperativo
                ├──< PresupuestoMensual
                ├──< Ruta
                └──< Documento (empresa)

Usuario (CONDUCTOR) ──< Documento (docs_c)
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
| `LogAuditoria` | Registro de eventos de seguridad y actividad |
| `Peaje` | Punto de cobro de peaje con coordenadas, tarifa y categoría vehicular |
| `ConfiguracionRuta` | Precios de combustible y radio de detección de peajes por empresa (1:1) |
| `Ruta` | Ruta planificada con conductor, vehículo, estado, costos estimados y reales |
| `Parada` | Punto de parada de una ruta (origen, intermedia, destino) con coordenadas |
| `PeajeRuta` | Peaje detectado en una ruta específica con la tarifa aplicada |

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
| `MapaRuta.vue` | Mapa Leaflet reutilizable — renderiza polilínea, paradas y peajes |

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

## 15. Variables de entorno

El archivo `gestion_backend/.env` no debe commitearse al repositorio. Contiene:

| Variable | Requerida | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí | Clave secreta de Django |
| `ENCRYPTION_KEY` | Sí | Clave base para derivar la clave Fernet |
| `FERNET_KEY` | Sí | Clave Fernet en formato base64-url |
| `DEBUG` | No | `True` para desarrollo, `False` para producción |
| `ALLOWED_HOSTS` | No | Hosts permitidos (separados por coma) |
| `EMAIL_BACKEND` | No | Backend de email (por defecto: consola) |
| `EMAIL_HOST` | No | Servidor SMTP |
| `EMAIL_PORT` | No | Puerto SMTP (por defecto: 587) |
| `EMAIL_USE_TLS` | No | Usar TLS (por defecto: `True`) |
| `EMAIL_HOST_USER` | No | Usuario SMTP |
| `EMAIL_HOST_PASSWORD` | No | Contraseña SMTP |
| `DEFAULT_FROM_EMAIL` | No | Dirección remitente de emails |

### Configuración CORS

En desarrollo, el backend acepta peticiones desde `http://localhost:7183`. En producción, configurar `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` en `settings.py` con los dominios reales.

---

*Documentación generada para el equipo de desarrollo. Para contribuir a este documento, editar `docs/documentacion.md` en el repositorio.*
