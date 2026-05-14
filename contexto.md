# Contexto del Proyecto: Sistema de Gestión de Flota

## Resumen General

Sistema web de gestión de flotas vehiculares con arquitectura desacoplada: frontend SPA en Vue 3 y backend API REST en Django 5. Diseñado para empresas que administran vehículos y conductores, con soporte multiempresa gestionado por un SUPERADMIN central.

- **Puerto frontend:** 7183
- **Puerto backend:** 8000
- **Base de datos:** SQLite3 (desarrollo)
- **Zona horaria:** America/Santiago (Chile)
- **Idioma:** Español de Chile (es-cl)
- **Rama activa:** `test` (rama `main` es la de producción)

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
│   │   ├── router/index.js        # Rutas Vue Router (SUPERADMIN + EMPRESA)
│   │   ├── utils/
│   │   │   ├── api.js             # Helper apiFetch centralizado
│   │   │   ├── permisos.js        # Helper tienePermiso()
│   │   │   └── empresaActiva.js   # Helper empresa activa
│   │   ├── components/
│   │   │   ├── AppToast.vue       # Notificaciones toast globales
│   │   │   ├── ConfirmModal.vue   # Modal de confirmación genérico
│   │   │   └── PermisoToast.vue   # Toast de permisos denegados
│   │   ├── assets/                # CSS y recursos estáticos
│   │   └── web/                   # Vistas de la aplicación
│   │       ├── login.vue
│   │       ├── Base.vue            # Layout SUPERADMIN
│   │       ├── Dashboard.vue       # Dashboard compartido (SUPERADMIN y EMPRESA)
│   │       ├── clientes/           # Gestión de empresas (SUPERADMIN)
│   │       │   ├── ListaEmpresas.vue
│   │       │   ├── NuevaEmpresa.vue
│   │       │   ├── DetalleEmpresa.vue
│   │       │   └── EditarEmpresa.vue
│   │       ├── usuarios/           # Gestión de usuarios (SUPERADMIN)
│   │       │   ├── ListaUsuarios.vue
│   │       │   ├── NuevoUsuario.vue
│   │       │   └── EditarUsuario.vue
│   │       ├── configuracion/
│   │       │   └── Configuracion.vue  # Gestión de planes de suscripción
│   │       ├── logs/
│   │       │   └── Logs.vue           # Logs de auditoría
│   │       ├── permisos/
│   │       │   └── GestionPermisos.vue
│   │       └── empresa/            # Vistas del panel de empresa
│   │           ├── EmpresaLayout.vue  # Sidebar + layout USUARIO
│   │           ├── conductores/
│   │           │   ├── ListaConductores.vue
│   │           │   ├── NuevoConductor.vue
│   │           │   ├── EditarConductor.vue
│   │           │   └── DetalleConductor.vue
│   │           ├── flota/
│   │           │   ├── ListaFlota.vue
│   │           │   ├── NuevaFlota.vue
│   │           │   ├── EditarFlota.vue
│   │           │   ├── FormVehiculo.vue  # Crear/editar vehículo (modo: nuevo|editar)
│   │           │   └── mantenciones/
│   │           │       ├── MantencionesLista.vue
│   │           │       ├── MantencionesCalendario.vue
│   │           │       ├── MantencionesForm.vue
│   │           │       └── MantencionesHistorial.vue
│   │           └── predictivo/
│   │               └── MantencionPredictiva.vue  # ★ NUEVO: Módulo predictivo completo
│
├── gestion_backend/               # Backend Django
│   ├── g_de_flota/                # App principal
│   │   ├── models.py              # Modelos de datos
│   │   ├── views.py               # Vistas/Controladores (~1.435 líneas)
│   │   ├── serializers.py         # Serializadores DRF (~761 líneas)
│   │   ├── admin.py               # Panel de administración
│   │   ├── middleware.py          # Timeout de sesión
│   │   ├── audit.py               # Sistema de auditoría
│   │   ├── backends.py            # Autenticación por RUT
│   │   └── migrations/            # 18 migraciones aplicadas
│   │       └── 0018_mantencionprogramada_alertamantencion_and_more.py  # ★ NUEVA
│   │   └── management/commands/
│   │       ├── crear_superusuario.py
│   │       └── evaluar_mantenciones_predictivas.py  # ★ NUEVO: Job diario
│   ├── gestion_backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py
│   ├── db.sqlite3
│   └── .env                       # Variables de entorno
│
├── docs/documentacion.md          # Documentación del proyecto
├── Mejoras.md                     # Especificación del módulo predictivo
├── contexto.md                    # Este archivo
├── iniciar.ps1                    # Script de inicio PowerShell
└── iniciar.bat                    # Script de inicio Batch
```

---

## Módulos y Funcionalidades

### 1. Autenticación
- Login por **RUT + contraseña** (no por username/email)
- Backend personalizado `RutBackend` para validar RUT chileno
- Bloqueo automático tras **5 intentos fallidos**
- Desbloqueo manual por SUPERADMIN
- Reset de contraseña (resetea al RUT del usuario)
- Timeout de sesión por inactividad (middleware)
- Logout con destrucción de sesión

### 2. Control de Acceso y Roles

Tres roles con permisos diferenciados:

| Rol | Descripción |
|---|---|
| `SUPERADMIN` | Acceso global a todas las empresas, configuración del sistema |
| `USUARIO` | Administrador dentro de una empresa específica |
| `CONDUCTOR` | Perfil operativo, asignación de vehículos (sin panel web) |

Sistema de **permisos granulares** M2M: cada usuario puede tener permisos individuales asignados por código y categoría. Los permisos se verifican con el helper `tiene_permiso(user, codigo)`.

Categorías de permisos existentes: `flotas`, `vehiculos`, `conductores`, `mantenciones`, `usuarios`, `documentos`.

### 3. Gestión de Empresas (Multitenancy)
- CRUD completo de empresas
- Planes de suscripción: **Básico**, **Pro**, **Enterprise**
- Límites por plan: número máximo de flotas, vehículos y conductores
- Estados: **Activa** / **Suspendida** (DELETE hace soft-delete)
- Encriptación de datos sensibles: RUT, email, teléfono, dirección (Fernet)
- Aislamiento total de datos por empresa
- 16 regiones de Chile disponibles

### 4. Gestión de Usuarios
- CRUD de usuarios con roles SUPERADMIN y USUARIO
- Asignación/revocación de permisos individuales (solo SUPERADMIN)
- Bloqueo y desbloqueo de cuentas
- Historial de logins del usuario (últimos 20)
- Reset de contraseña por SUPERADMIN (resetea a RUT del usuario)

### 5. Gestión de Conductores
- CRUD de conductores dentro de cada empresa
- Asignación y desasignación de vehículos (1 conductor ↔ 1 vehículo activo)
- Documentos del conductor: licencia, certificado de salud, antecedentes
- Control de vencimiento de documentos (vigente / por vencer / vencido)
- Historial de asignaciones de vehículos

### 6. Gestión de Flotas y Vehículos
- CRUD de flotas agrupadas por empresa
- CRUD de vehículos dentro de cada flota
- Tipos de combustible: Bencina, Diésel, Eléctrico, Híbrido
- Documentos de vehículos: permiso de circulación, seguro (SOAP), revisión técnica
- Tracking de kilometraje actual
- Estado activo/inactivo (DELETE hace soft-delete)

### 7. Sistema de Asignaciones
- Vincula Conductor ↔ Vehículo con registro temporal (desde/hasta)
- **Restricciones de integridad:**
  - Un vehículo solo puede tener 1 conductor activo
  - Un conductor solo puede tener 1 vehículo activo
- Historial completo de asignaciones

### 8. Gestión de Mantenciones (Manual)
- CRUD de mantenciones por vehículo
- Programación por fecha y/o kilometraje
- Registro de realización (fecha y km reales)
- Estados: `pendiente`, `en_proceso`, `realizada`, `cancelada`
- Registro de costo, presupuesto, taller/proveedor, descripción
- Vista de lista, historial y calendario mensual

### 9. ★ Módulo de Mantenimiento Predictivo (NUEVO)
Ubicación frontend: `/empresa/predictivo` y `/predictivo` (SUPERADMIN)

**Interfaz de 4 tabs:**

#### Tab Alertas
- Listado de alertas ordenadas por urgencia (vencidas primero)
- Filtros por nivel (`por_vencer` / `vencida`) y estado (`pendiente` / `atendida`)
- Por cada alerta: patente, tipo de mantención, nivel con badge de color, días restantes, barra de progreso del intervalo
- Acción inline "Registrar Mantención": abre modal, solicita fecha de realización y costo, cierra la alerta, crea registro en historial y recalcula próxima fecha

#### Tab Planes
- Listado de planes con sus reglas expandidas
- Botón para crear nuevo plan o eliminar existente

#### Tab Nuevo Plan
- Formulario de plan con reglas dinámicas (agregar/quitar sin recargar)
- Por cada regla: tipo de mantención, intervalo en días (con helper visual que muestra equivalencia en meses/años), umbral de alerta, prioridad, costo estimado, checkbox escalar (48h), checkbox bloquear despacho

#### Tab Simulador
- Selector de vehículo y período (3, 6 o 12 meses)
- Proyecta todos los eventos de mantención futuros con fecha exacta y costo estimado por evento
- Muestra totales: cantidad de eventos y presupuesto estimado total

**Motor de alertas automático:**
- Comando de management: `python manage.py evaluar_mantenciones_predictivas`
- Debe ejecutarse diariamente a las 07:00 (configurar con cron o Celery Beat)
- Evalúa todos los vehículos activos con plan asignado
- Crea `AlertaMantencion` si `dias_restantes <= umbral_alerta_dias` y no hay alerta pendiente
- Actualiza nivel de `por_vencer` a `vencida` si `dias_restantes <= 0`
- Lógica de escalamiento a supervisor si `escalar_sin_respuesta = True` y han pasado ≥ 2 días
- El envío real de notificaciones por canal (email/push/WhatsApp/SMS) está como `pass` — **pendiente de implementar**

### 10. Dashboard Analítico

**Panel SUPERADMIN (`/dashboard`):**
- KPIs: empresas activas/inactivas, total usuarios, conductores, vehículos, empresas nuevas del mes, usuarios activos hoy
- Gráfico de línea: crecimiento de empresas (configurable: 7d / 30d / 3m / 6m / 12m)
- Gráfico de torta: distribución por tamaño de flota (0 / 1-5 / 6-10 / +10 vehículos)
- Gráfico de barras: top 5 empresas por vehículos

**Panel EMPRESA (`/empresa/dashboard`):**
- KPIs: flotas, vehículos, conductores, mantenciones pendientes, documentos por vencer (próximos 30 días)
- Gráfico de barras: vehículos por flota
- Gráfico de línea: mantenciones programadas por período

### 11. Sistema de Auditoría
- Modelo `LogAuditoria` con dos categorías:
  - **SEGURIDAD:** logins, cambios de rol, reset de contraseña, bloqueos de cuenta, cambio de permisos
  - **ACTIVIDAD:** crear, modificar y eliminar recursos, atender alertas, crear/modificar/eliminar planes de mantenimiento
- Captura: usuario, IP, acción, detalle en JSON, timestamp
- Vista de logs paginada (50 por página) disponible solo para SUPERADMIN
- Filtros: tipo, acción, búsqueda por email/IP, rango de fechas

### 12. Telemetría (infraestructura lista, UI pendiente)
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
estado (vigente | por_vencer | vencido) — calculado automáticamente en save()
```

### Mantencion
```
id, vehiculo (FK), tipo_mantencion
descripcion, taller_proveedor, presupuesto
fecha_programada, kilometraje_programado
fecha_realizada, kilometraje_realizado
estado (pendiente | en_proceso | realizada | cancelada)
costo
```

### ★ PlanMantenimiento (NUEVO)
```
id, empresa (FK → Empresa), nombre, descripcion
activo, created_at
```

### ★ ReglaMantenimiento (NUEVO)
```
id, plan (FK → PlanMantenimiento)
tipo (texto libre, ej: "Aceite", "Frenos")
prioridad (alta | media | baja)
intervalo_dias (int)
umbral_alerta_dias (int)
canal (email | push | whatsapp | sms)
escalar_sin_respuesta (bool), bloquear_despacho (bool)
costo_estimado (decimal)
```

### ★ VehiculoPlan (NUEVO)
```
id, vehiculo (FK), plan (FK)
fecha_asignacion
[unique_together: vehiculo + plan]
```

### ★ MantencionProgramada (NUEVO)
```
id, vehiculo (FK), regla (FK → ReglaMantenimiento)
fecha_ultima (date), fecha_siguiente (date)
estado (activa | inactiva)
```

### ★ AlertaMantencion (NUEVO)
```
id, mantencion_programada (FK)
nivel (por_vencer | vencida)
dias_restantes (int — negativo si vencida)
pct_avance (float — dias_transcurridos / intervalo_dias * 100)
enviada (bool), atendida (bool)
fecha_creacion, fecha_atencion (nullable)
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

## API REST — Endpoints Completos

### Autenticación y Dashboard
| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/login/` | Autenticación por RUT |
| GET | `/api/dashboard/` | Dashboard SUPERADMIN |
| GET | `/api/empresa/dashboard/` | Dashboard de empresa |

### Empresas
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/empresas/` | Listar empresas (SUPERADMIN) |
| POST | `/api/empresas/crear/` | Crear empresa |
| GET/PUT/DELETE | `/api/empresas/:id/` | Ver / editar / suspender empresa |

### Usuarios
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/usuarios/` | Listar usuarios |
| POST | `/api/usuarios/crear/` | Crear usuario |
| GET/PUT/DELETE | `/api/usuarios/:id/` | Ver / editar / desactivar usuario |
| POST | `/api/usuarios/:id/reset-password/` | Reset de contraseña al RUT |
| POST | `/api/usuarios/:id/toggle-block/` | Bloquear / desbloquear usuario |
| GET | `/api/usuarios/:id/historial/` | Historial de logins |
| GET/PUT | `/api/usuarios/:id/permisos/` | Ver / modificar permisos |

### Flotas y Vehículos
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/admin/flotas/` | Vista global de flotas (SUPERADMIN) |
| GET/POST | `/api/empresa/flotas/` | Listar / crear flotas |
| GET/PUT/DELETE | `/api/empresa/flotas/:id/` | Ver / editar / eliminar flota |
| GET/POST | `/api/empresa/vehiculos/` | Listar / crear vehículos |
| GET/PUT/DELETE | `/api/empresa/vehiculos/:id/` | Ver / editar / desactivar vehículo |

### Conductores
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/empresa/conductores/` | Listar / crear conductores |
| GET/PUT/DELETE | `/api/empresa/conductores/:id/` | Ver / editar / desactivar conductor |
| POST | `/api/empresa/conductores/:id/asignar/` | Asignar vehículo |
| POST | `/api/empresa/conductores/:id/desasignar/` | Desasignar vehículo |

### Mantenciones Manuales
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/empresa/mantenciones/` | Listar / crear mantenciones |
| GET | `/api/empresa/mantenciones/resumen/` | Resumen: costos, conteos por estado |
| GET | `/api/empresa/mantenciones/calendario/` | Mantenciones por mes (año+mes en query) |
| GET/PUT/DELETE | `/api/empresa/mantenciones/:id/` | Ver / editar / eliminar mantención |

### ★ Mantenimiento Predictivo (NUEVO — via DRF Router)
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/empresa/planes-mantenimiento/` | Listar / crear planes |
| GET/PUT/PATCH/DELETE | `/api/empresa/planes-mantenimiento/:id/` | CRUD de plan |
| GET | `/api/empresa/alertas-mantenimiento/` | Listar alertas (filtros: nivel, estado) |
| POST | `/api/empresa/alertas-mantenimiento/:id/atender/` | Atender alerta: cierra y registra en historial |
| GET | `/api/empresa/simulador-vencimientos/` | Proyección futura (params: vehiculo_id, meses) |

### Configuración, Permisos y Logs
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/configuracion/planes/` | Listar / crear planes de suscripción |
| GET/PUT/DELETE | `/api/configuracion/planes/:id/` | Ver / editar / eliminar plan |
| GET | `/api/permisos/` | Listar permisos disponibles |
| GET | `/api/logs/` | Ver logs de auditoría (paginado, 50/página) |

---

## Rutas del Frontend (Vue Router)

Dos layouts paralelos con las mismas rutas de operación:

### Panel SUPERADMIN (layout: `Base.vue`)
```
/dashboard
/empresas, /empresas/nueva, /empresas/:id, /empresas/:id/editar
/usuarios, /usuarios/nuevo, /usuarios/:id/editar
/planes, /permisos, /logs
/flota, /flota/nueva, /flota/:id/editar
/flota/:flotaId/nuevo-vehiculo, /vehiculos/:id/editar
/conductores, /conductores/nuevo, /conductores/:id, /conductores/:id/editar
/mantenciones, /mantenciones/calendario, /mantenciones/nueva
/mantenciones/:id/editar, /mantenciones/historial
/predictivo        ← MantencionPredictiva.vue
/documentos, /finanzas, /reportes   (páginas "Próximamente")
```

### Panel EMPRESA (layout: `EmpresaLayout.vue`, solo rol `USUARIO`)
```
/empresa/dashboard
/empresa/flota, /empresa/flota/nueva, /empresa/flota/:id/editar
/empresa/flota/:flotaId/nuevo-vehiculo, /empresa/vehiculos/:id/editar
/empresa/conductores, /empresa/conductores/nuevo
/empresa/conductores/:id, /empresa/conductores/:id/editar
/empresa/mantenciones, /empresa/mantenciones/calendario
/empresa/mantenciones/nueva, /empresa/mantenciones/:id/editar
/empresa/mantenciones/historial
/empresa/predictivo  ← MantencionPredictiva.vue
/empresa/documentos, /empresa/finanzas, /empresa/reportes  (páginas "Próximamente")
```

### Sidebar EmpresaLayout — ítems de navegación
| Label | Ruta | Permiso requerido |
|---|---|---|
| Dashboard | `/empresa/dashboard` | — |
| Flota | `/empresa/flota` | `flotas.ver` |
| Conductores | `/empresa/conductores` | `conductores.ver` |
| Mantenciones | `/empresa/mantenciones` | `mantenciones.ver` |
| Predictivo | `/empresa/predictivo` | `mantenciones.ver` |
| Documentos | `/empresa/documentos` | `documentos.ver` |
| Finanzas | `/empresa/finanzas` | — |
| Reportes | `/empresa/reportes` | — |

---

## Seguridad

- **Encriptación Fernet** de todos los datos sensibles (RUT, nombre, teléfono, dirección, email, comuna, ciudad)
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
python manage.py runserver                            # Puerto 8000
python manage.py migrate
python manage.py createsuperuser                      # Comando personalizado
python manage.py evaluar_mantenciones_predictivas     # ★ NUEVO: Job predictivo
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
- Gestión de mantenciones (manual: lista, historial, calendario)
- Dashboards analíticos con Chart.js (SUPERADMIN y EMPRESA)
- Sistema de auditoría completo (seguridad + actividad)
- Encriptación Fernet para datos sensibles
- Bloqueos de cuenta y control de accesos
- Scripts de inicio del proyecto
- **★ Módulo de Mantenimiento Predictivo completo:**
  - Modelos: `PlanMantenimiento`, `ReglaMantenimiento`, `VehiculoPlan`, `MantencionProgramada`, `AlertaMantencion`
  - API REST via DRF ViewSets + endpoints de atención y simulación
  - Migración `0018` aplicada
  - Frontend `MantencionPredictiva.vue` con 4 tabs: Alertas, Planes, Nuevo Plan, Simulador
  - Comando de management `evaluar_mantenciones_predictivas` para ejecución programada

### Pendiente / En desarrollo
- Notificaciones reales por canal (email/push/WhatsApp/SMS): la lógica está marcada como `pass` en el comando de management
- Programación automática del job (cron, Celery Beat u otro scheduler)
- Módulo de Documentos (infraestructura lista, UI pendiente)
- Módulo de Finanzas (ruta definida, sin implementar)
- Módulo de Reportes (ruta definida, sin implementar)
- Sistema de telemetría GPS en tiempo real (modelos listos, sin UI)
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

### Migraciones
Se han aplicado 18 migraciones en total. La última (`0018`) agrega los modelos del módulo predictivo: `MantencionProgramada`, `AlertaMantencion`, y campos relacionados de `PlanMantenimiento`, `ReglaMantenimiento` y `VehiculoPlan`.
