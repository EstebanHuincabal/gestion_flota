# Contexto del Proyecto: Sistema de Gestión de Flota

## Resumen General

Sistema web de gestión de flotas vehiculares con arquitectura desacoplada: frontend SPA en Vue 3 y backend API REST en Django 5. Diseñado para empresas que administran vehículos y conductores, con soporte multiempresa gestionado por un SUPERADMIN central.

- **Puerto frontend:** 7183
- **Puerto backend:** 8000
- **Base de datos:** SQLite3 (desarrollo)
- **Zona horaria:** America/Santiago (Chile)
- **Idioma:** Español de Chile (es-cl)

---

## Stack Tecnológico

### Frontend
| Tecnología | Versión | Uso |
|---|---|---|
| Vue.js 3 | 3.5.32 | Framework principal (Composition API) |
| Vite | 8.0.8 | Bundler y servidor de desarrollo |
| Vue Router | 4.6.4 | Enrutamiento SPA |
| TailwindCSS | 4.2.4 | Framework CSS utilitario |
| Chart.js | 4.5.1 | Gráficos y visualizaciones |
| PostCSS | 8.5.14 | Procesador CSS |
| Autoprefixer | 10.5.0 | Prefijos CSS automáticos |

### Backend
| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.x | Lenguaje principal |
| Django | 5.x | Framework web |
| Django REST Framework | — | API RESTful |
| Django CORS Headers | — | Gestión de CORS |
| Cryptography (Fernet) | — | Encriptación de datos sensibles |
| SQLite3 | — | Base de datos (desarrollo) |

---

## Estructura de Carpetas

```
gestion-de-flota/
├── gestion-frontend/              # Aplicación Vue 3
│   ├── src/
│   │   ├── router/                # Rutas Vue Router
│   │   ├── utils/                 # Utilidades (api.js, permisos.js, empresaActiva.js)
│   │   ├── components/            # Componentes reutilizables
│   │   │   ├── AppToast.vue
│   │   │   ├── ConfirmModal.vue
│   │   │   └── PermisoToast.vue
│   │   ├── stores/                # Almacenes de estado (vacío)
│   │   ├── assets/                # CSS y recursos estáticos
│   │   └── web/                   # Vistas de la aplicación
│   │       ├── login.vue
│   │       ├── Base.vue            # Layout SUPERADMIN
│   │       ├── Dashboard.vue
│   │       ├── clientes/           # Gestión de empresas
│   │       ├── usuarios/           # Gestión de usuarios
│   │       └── empresa/            # Vistas del panel de empresa
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── gestion_backend/               # Backend Django
│   ├── g_de_flota/                # App principal
│   │   ├── models.py              # Modelos de datos
│   │   ├── views.py               # Vistas/Controladores (1.227 líneas)
│   │   ├── serializers.py         # Serializadores DRF (761 líneas)
│   │   ├── urls.py                # Rutas de la API
│   │   ├── admin.py               # Panel de administración
│   │   ├── middleware.py          # Timeout de sesión
│   │   ├── audit.py               # Sistema de auditoría
│   │   ├── backends.py            # Autenticación por RUT
│   │   └── migrations/            # 15 migraciones aplicadas
│   ├── gestion_backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py
│   ├── db.sqlite3                 # Base de datos (315 KB)
│   └── .env                       # Variables de entorno
│
├── docs/                          # Documentación del proyecto
├── iniciar.ps1                    # Script de inicio PowerShell
├── iniciar.bat                    # Script de inicio Batch
└── .gitignore
```

---

## Módulos y Funcionalidades

### 1. Autenticación
- Login por **RUT + contraseña** (no por username/email)
- Backend personalizado `RutBackend` para validar RUT chileno
- Bloqueo automático tras **5 intentos fallidos**
- Desbloqueo manual por SUPERADMIN
- Reset de contraseña
- Timeout de sesión por inactividad (middleware)
- Logout con destrucción de sesión

### 2. Control de Acceso y Roles

Tres roles con permisos diferenciados:

| Rol | Descripción |
|---|---|
| `SUPERADMIN` | Acceso global a todas las empresas, configuración del sistema |
| `USUARIO` | Administrador dentro de una empresa específica |
| `CONDUCTOR` | Perfil operativo, asignación de vehículos |

Sistema de **permisos granulares** M2M: cada usuario puede tener permisos individuales asignados por código y categoría, verificados mediante decoradores `@permission_classes`.

### 3. Gestión de Empresas (Multitenancy)
- CRUD completo de empresas
- Planes de suscripción: **Básico**, **Pro**, **Enterprise**
- Límites por plan: número máximo de flotas, vehículos y conductores
- Estados: **Activa** / **Suspendida**
- Encriptación de datos sensibles: RUT, email, teléfono, dirección (Fernet)
- Aislamiento total de datos por empresa
- 16 regiones de Chile disponibles

### 4. Gestión de Usuarios
- CRUD de usuarios con roles SUPERADMIN y USUARIO
- Asignación/revocación de permisos individuales
- Bloqueo y desbloqueo de cuentas
- Historial de logins del usuario (últimos 20)
- Reset de contraseña por SUPERADMIN

### 5. Gestión de Conductores
- CRUD de conductores dentro de cada empresa
- Asignación y desasignación de vehículos
- Documentos del conductor: licencia, certificado de salud, antecedentes
- Control de vencimiento de documentos (vigente / por vencer / vencido)
- Historial de asignaciones de vehículos

### 6. Gestión de Flotas y Vehículos
- CRUD de flotas agrupadas por empresa
- CRUD de vehículos dentro de cada flota
- Tipos de combustible: Bencina, Diésel, Eléctrico, Híbrido
- Documentos de vehículos: permiso de circulación, seguro, revisión técnica
- Tracking de kilometraje actual
- Estado activo/inactivo

### 7. Sistema de Asignaciones
- Vincula Conductor ↔ Vehículo con registro temporal (desde/hasta)
- **Restricciones de integridad:**
  - Un vehículo solo puede tener 1 conductor activo
  - Un conductor solo puede tener 1 vehículo activo
- Historial completo de asignaciones

### 8. Gestión de Mantenciones
- CRUD de mantenciones por vehículo
- Programación por fecha y/o kilometraje
- Registro de realización (fecha y km reales)
- Estado de la mantención (pendiente, completada, etc.)
- Registro de costo

### 9. Dashboard Analítico

**Panel SUPERADMIN:**
- KPIs: empresas activas/inactivas, total usuarios, conductores, vehículos
- Gráfico de línea: crecimiento de empresas (configurable: 7d / 30d / 3m / 6m / 12m)
- Gráfico de torta: distribución por tamaño de flota
- Gráfico de barras: top 5 empresas por vehículos

**Panel EMPRESA:**
- KPIs: flotas, vehículos, conductores, mantenciones pendientes, documentos por vencer
- Gráfico de barras: vehículos por flota
- Gráfico de línea: mantenciones programadas por período

### 10. Sistema de Auditoría
- Modelo `LogAuditoria` con dos categorías:
  - **SEGURIDAD:** logins, cambios de rol, reset de contraseña, bloqueos de cuenta
  - **ACTIVIDAD:** crear, modificar y eliminar recursos
- Captura: usuario, IP, acción, detalle en JSON, timestamp
- Vista de logs disponible para SUPERADMIN

### 11. Telemetría (infraestructura lista, UI pendiente)
- Modelo `Ubicacion`: coordenadas GPS, velocidad, nivel de combustible
- Modelo `Evento`: eventos del vehículo con descripción

---

## Modelos de Datos

### Usuario
```
id, email (único), password
rut_cifrado (Fernet), rut_hash (SHA256, indexed, único)
nombre_cifrado, telefono_cifrado, licencia_cifrada
rol (SUPERADMIN | USUARIO | CONDUCTOR)
empresa (FK → Empresa, nullable)
permisos (M2M → Permiso)
intentos_fallidos, is_blocked, is_active, is_superuser
last_login, date_joined
```

### Empresa
```
id, nombre
rut_cifrado, rut_hash (único, indexed)
email_cifrado, telefono_cifrado, direccion_cifrada, comuna_cifrada, ciudad_cifrada
region (16 regiones Chile), pais
estado (activa | suspendida)
plan (FK → PlanSuscripcion, nullable)
created_at
```

### PlanSuscripcion
```
id, nombre (basico | pro | enterprise)
max_flotas, max_vehiculos, max_conductores
```

### Permiso
```
id, codigo (único), nombre, categoria (indexed)
```

### Flota
```
id, empresa (FK), nombre
```

### Vehiculo
```
id, flota (FK), patente (única)
marca, modelo, anio
tipo_combustible (bencina | diesel | electrico | hibrido)
km_actuales, activo
```

### Asignacion
```
id, conductor (FK → Usuario, nullable), vehiculo (FK)
activo, desde, hasta
[unique: vehículo activo solo con 1 conductor]
[unique: conductor activo solo con 1 vehículo]
```

### DocumentoConductor / DocumentoVehiculo
```
id, conductor/vehiculo (FK), tipo (choice)
numero, fecha_vencimiento
estado (vigente | por_vencer | vencido)
```

### Mantencion
```
id, vehiculo (FK), tipo_mantencion
fecha_programada, kilometraje_programado
fecha_realizada, kilometraje_realizado
estado, costo
```

### Ubicacion
```
id, vehiculo (FK)
latitud, longitud, velocidad, combustible, timestamp
```

### Evento
```
id, vehiculo (FK), tipo, descripcion, fecha
```

### LogAuditoria
```
id, tipo (SEGURIDAD | ACTIVIDAD), accion
usuario (FK, nullable), detalle (JSONField), ip, fecha (indexed)
```

---

## API REST — Endpoints Principales

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/login/` | Autenticación por RUT |
| GET | `/api/dashboard/` | Dashboard SUPERADMIN |
| GET | `/api/empresa/dashboard/` | Dashboard de empresa |
| GET/POST | `/api/empresas/` | Listar / crear empresas |
| GET/PUT/DELETE | `/api/empresas/:id/` | Ver / editar / suspender empresa |
| GET/POST | `/api/usuarios/` | Listar / crear usuarios |
| GET/PUT/DELETE | `/api/usuarios/:id/` | Ver / editar / desactivar usuario |
| POST | `/api/usuarios/:id/reset-password/` | Reset de contraseña |
| POST | `/api/usuarios/:id/toggle-block/` | Bloquear / desbloquear usuario |
| GET | `/api/usuarios/:id/historial/` | Historial de logins |
| GET/PUT | `/api/usuarios/:id/permisos/` | Ver / modificar permisos |
| GET/POST | `/api/empresa/flotas/` | Listar / crear flotas |
| GET/PUT/DELETE | `/api/empresa/flotas/:id/` | Ver / editar / eliminar flota |
| GET/POST | `/api/empresa/vehiculos/` | Listar / crear vehículos |
| GET/PUT/DELETE | `/api/empresa/vehiculos/:id/` | Ver / editar / eliminar vehículo |
| GET/POST | `/api/empresa/conductores/` | Listar / crear conductores |
| GET/PUT/DELETE | `/api/empresa/conductores/:id/` | Ver / editar / eliminar conductor |
| POST | `/api/empresa/conductores/:id/asignar/` | Asignar vehículo |
| POST | `/api/empresa/conductores/:id/desasignar/` | Desasignar vehículo |
| GET/POST | `/api/empresa/mantenciones/` | Listar / crear mantenciones |
| GET | `/api/empresa/mantenciones/resumen/` | Resumen de mantenciones |
| PUT | `/api/empresa/mantenciones/:id/` | Editar mantenimiento |
| GET | `/api/permisos/` | Listar permisos disponibles |
| GET | `/api/logs/` | Ver logs de auditoría |
| GET/POST | `/api/configuracion/planes/` | Listar / crear planes |
| GET/PUT | `/api/configuracion/planes/:id/` | Ver / editar plan |

---

## Seguridad

- **Encriptación Fernet** de todos los datos sensibles (RUT, nombre, teléfono, dirección)
- **Hash SHA256** de RUT para búsquedas sin exponer datos cifrados
- **CSRF protection** con tokens en headers
- **CORS** restringido a `localhost:7183` y `127.0.0.1:7183`
- **Autenticación por sesión** con middleware de timeout por inactividad
- **Bloqueo de cuentas** tras 5 intentos fallidos
- **Auditoría completa** de acciones de seguridad y actividad
- Variables secretas en `.env` (SECRET_KEY, FERNET_KEY, ENCRYPTION_KEY)

---

## Scripts de Inicio

```powershell
# Iniciar todo el proyecto (abre backend + frontend en paralelo)
./iniciar.ps1       # PowerShell — abre 2 tabs en Windows Terminal
./iniciar.bat       # Batch — abre 2 ventanas PowerShell
```

```bash
# Frontend
cd gestion-frontend
npm run dev         # Puerto 7183
npm run build       # Build de producción
npm run preview     # Preview del build

# Backend
cd gestion_backend
python manage.py runserver          # Puerto 8000
python manage.py migrate
python manage.py createsuperuser    # Comando personalizado
```

---

## Estado del Desarrollo

### Completado y funcional
- Sistema de autenticación por RUT chileno
- Gestión completa de empresas con planes y límites
- Gestión de usuarios con permisos granulares
- Gestión de conductores con documentos
- Gestión de flotas y vehículos con documentos
- Sistema de asignaciones conductor-vehículo
- Gestión de mantenciones
- Dashboards analíticos con Chart.js (SUPERADMIN y EMPRESA)
- Sistema de auditoría completo (seguridad + actividad)
- Encriptación Fernet para datos sensibles
- Bloqueos de cuenta y control de accesos
- Scripts de inicio del proyecto

### Pendiente / En desarrollo
- Módulo de Documentos (infraestructura lista, UI completa pendiente)
- Módulo de Finanzas (ruta definida, sin implementar)
- Módulo de Reportes (ruta definida, sin implementar)
- Sistema de telemetría GPS en tiempo real (modelos listos, sin UI)
- Sistema de notificaciones (infraestructura presente, sin implementar)
- Migración a PostgreSQL para producción

---

## Configuración del Entorno

### Variables de entorno requeridas (`.env`)
```
SECRET_KEY=...
FERNET_KEY=...
ENCRYPTION_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### CORS permitido
```
http://localhost:7183
http://127.0.0.1:7183
```

### Autenticación backends
```python
AUTHENTICATION_BACKENDS = [
    'g_de_flota.backends.RutBackend',  # Primario: login por RUT
    'django.contrib.auth.backends.ModelBackend',  # Fallback
]
AUTH_USER_MODEL = 'g_de_flota.Usuario'
```
