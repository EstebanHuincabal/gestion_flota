# Contexto del Proyecto — Sistema de Gestión de Flota

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Python / Django + Django REST Framework | Django 5.x |
| Frontend | Vue.js 3 (Composition API) + Vite | Vue 3.5.32 / Vite 8.x |
| Base de datos | SQLite3 (desarrollo) | — |
| CSS | TailwindCSS | 4.2.4 |
| Gráficos | Chart.js | 4.5.1 |
| Routing SPA | Vue Router | 4.6.4 |
| Cifrado | Fernet (cryptography) | — |
| Autenticación | Sesiones Django con backend RUT personalizado | — |

**Puertos:** Backend → `127.0.0.1:8000` / Frontend → `127.0.0.1:7183`
**Zona horaria:** America/Santiago | **Idioma:** es-cl | **Rama activa:** `test`

---

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| `SUPERADMIN` | Administra todo el sistema: empresas, usuarios, planes, logs globales |
| `USUARIO` | Administrador de una empresa: flota, conductores, mantenciones |
| `CONDUCTOR` | Rol operativo — el modelo existe pero no tiene flujo de login ni UI propia |

---

## Módulos integrados y funcionales

### 1. Autenticación y seguridad
- Login por **RUT + contraseña** (no por email ni username)
- Backend personalizado `RutBackend` que autentica por hash SHA-256 del RUT
- Bloqueo automático de cuenta tras 5 intentos fallidos (`intentos_fallidos`, `is_blocked`)
- Desbloqueo manual por SUPERADMIN (`POST /api/usuarios/:id/toggle-block/`)
- Reset de contraseña por SUPERADMIN (contraseña se resetea al RUT del usuario)
- Middleware de timeout de sesión por inactividad (`SESSION_IDLE_TIMEOUT`)
- CSRF protection en todas las mutaciones (POST/PUT/DELETE)
- Datos sensibles cifrados con Fernet: RUT, nombre, teléfono, licencia, email, dirección
- Hash SHA-256 del RUT para búsquedas eficientes sin exponer datos cifrados

### 2. Gestión de usuarios
- CRUD completo de usuarios (solo SUPERADMIN)
- Asignación de rol: `SUPERADMIN` / `USUARIO` / `CONDUCTOR`
- Historial de auditoría por usuario (últimas acciones)
- Bloqueo/desbloqueo de cuentas
- Reset de contraseña por SUPERADMIN
- Permisos granulares: asignar/revocar permisos individuales por código
- Frontend: `ListaUsuarios.vue`, `NuevoUsuario.vue`, `EditarUsuario.vue`

### 3. Permisos granulares
- Modelo `Permiso` con código único por acción (ej: `crear_flota`, `editar_vehiculo`)
- Permisos asignados a usuarios vía ManyToMany
- Categorías: `flotas`, `vehiculos`, `conductores`, `mantenciones`, `usuarios`, `documentos`
- SUPERADMIN tiene acceso total siempre; CONDUCTOR nunca tiene acceso
- `GestionPermisos.vue`: UI para asignar/revocar permisos
- `permisos.js` en frontend con `tienePermiso(codigo)` para verificación en tiempo real
- `PermisoToast.vue`: toast visual cuando se deniega acceso

### 4. Gestión de empresas (multitenancy)
- CRUD completo de empresas (solo SUPERADMIN)
- Datos cifrados: RUT, email, teléfono, dirección, comuna, ciudad
- 16 regiones de Chile incluidas
- Estados: **activa** / **suspendida**
- Asociación a plan de suscripción con límites
- Aislamiento total de datos entre empresas
- Frontend: `ListaEmpresas.vue`, `NuevaEmpresa.vue`, `DetalleEmpresa.vue`, `EditarEmpresa.vue`

### 5. Planes de suscripción
- CRUD de planes: Básico / Pro / Enterprise
- Límites configurables: `max_flotas`, `max_vehiculos`, `max_conductores`
- `Configuracion.vue`: UI de administración de planes

### 6. Gestión de flotas y vehículos
- CRUD de flotas (agrupaciones de vehículos dentro de una empresa)
- CRUD de vehículos: patente única, marca, modelo, año, tipo combustible, km actuales, estado
- Tipos de combustible: Bencina / Diésel / Eléctrico / Híbrido
- Estado activo/inactivo (soft-delete)
- Frontend: `ListaFlota.vue`, `NuevaFlota.vue`, `EditarFlota.vue`, `FormVehiculo.vue` (modo nuevo/editar)

### 7. Gestión de conductores
- CRUD de conductores dentro de cada empresa
- Asignación de vehículo: 1 conductor activo por vehículo, 1 vehículo activo por conductor
- Desasignación de vehículo
- Historial de asignaciones anteriores (modelo `Asignacion` con fechas desde/hasta)
- Documentos del conductor: licencia, certificado de salud, antecedentes, otro
- Frontend: `ListaConductores.vue`, `NuevoConductor.vue`, `EditarConductor.vue`, `DetalleConductor.vue`

### 8. Documentos con vencimiento
- **Documentos de vehículos:** Permiso de circulación, Seguro obligatorio (SOAP), Revisión técnica, Otro
- **Documentos de conductores:** Licencia de conducir, Certificado de salud, Antecedentes, Otro
- Estado calculado automáticamente en `save()`: `vigente` / `por_vencer` (≤ 30 días) / `vencido`
- Comando `evaluar_documentos_vencimiento` genera notificaciones automáticas a los admins

### 9. Mantenciones (correctivas y programadas)
- CRUD completo de mantenciones por vehículo
- Campos: tipo, descripción, taller/proveedor, presupuesto, costo final
- Programación: fecha programada, kilometraje programado
- Ejecución: fecha realizada, kilometraje realizado
- Estados: `PENDIENTE` / `EN_PROCESO` / `REALIZADA` / `CANCELADA`
- Endpoints: resumen de costos/conteos, vista calendario mensual, sugerencias
- Frontend: `MantencionesLista.vue`, `MantencionesCalendario.vue`, `MantencionesForm.vue`, `MantencionesHistorial.vue`, `MantencionesDetalle.vue`

### 10. Mantenimiento predictivo
- **Modelo `PlanMantenimiento`:** planes personalizados por empresa
- **Modelo `ReglaMantenimiento`:** tipo de servicio, intervalo en días, umbral de alerta, prioridad (alta/media/baja), costo estimado, canal notificación (email/push/whatsapp/sms), opciones de escalamiento y bloqueo de despacho
- **Modelo `VehiculoPlan`:** asignación de plan a vehículo
- **Modelo `MantencionProgramada`:** fecha última y próxima mantención por regla y vehículo
- **Modelo `AlertaMantencion`:** nivel (por_vencer/vencida), días restantes, % avance, estado atendida/pendiente
- Comando `evaluar_mantenciones_predictivas`: genera alertas automáticas, actualiza niveles, escala a supervisor si corresponde
- Frontend `MantencionPredictiva.vue` con 4 tabs: Alertas, Planes, Nuevo Plan, Simulador
- Simulador proyecta eventos y costos futuros por vehículo y período

### 11. Auditoría y logs
- Modelo `LogAuditoria` con dos categorías: `SEGURIDAD` y `ACTIVIDAD`
- Captura: usuario, IP real (maneja X-Forwarded-For), acción, detalle en JSON, timestamp
- `audit.py` con función `registrar_log()` usada en todas las vistas críticas
- `Logs.vue`: visor paginado con filtros por tipo, acción, email/IP y rango de fechas

### 12. Notificaciones
- Notificaciones in-app almacenadas en BD (modelo `Notificacion`)
- Tipos: `MANTENCION_POR_VENCER`, `MANTENCION_VENCIDA`, `DOCUMENTO_POR_VENCER`, `DOCUMENTO_VENCIDO`, `SEGURIDAD`, `ACTIVIDAD`
- Envío por email (SMTP configurable en `.env`)
- Preferencias por usuario: qué categorías recibir y por qué canal
- `NotificacionesBell.vue`: campana con contador de no leídas en navbar
- `Notificaciones.vue`: centro de notificaciones con marcar como leída
- `PreferenciasNotificaciones.vue`: configuración de preferencias
- `notificaciones.py` con `notificar()` y `notificar_admins_empresa()` (fail-silent)

### 13. Dashboard analítico
- **Dashboard SUPERADMIN** (`/dashboard`): KPIs globales — empresas activas/inactivas, usuarios, conductores, vehículos, crecimiento mensual. Gráficos: línea de crecimiento de empresas, torta de distribución por tamaño de flota, barras con top 5 empresas
- **Dashboard de empresa** (`/empresa/dashboard`): KPIs — flotas, vehículos, conductores, mantenciones pendientes, documentos por vencer (30 días). Gráficos: vehículos por flota, mantenciones por período

### 14. Infraestructura y utilidades frontend
- `api.js`: wrapper `apiFetch()` centralizado con CSRF automático, manejo 401→logout, 403→permiso-denegado, inyección de `empresa_id`
- `empresaActiva.js`: gestión de empresa activa en `sessionStorage`; `useEmpresaNav()` para navegar con prefijo correcto
- `useToast.js` + `AppToast.vue`: sistema de toasts globales (success/error/info) via CustomEvent
- `ConfirmModal.vue`: modal de confirmación reutilizable
- `PermisoToast.vue`: toast específico para acceso denegado

### 15. Scripts de inicio
- `iniciar.ps1`: lanza backend + frontend en paralelo (Windows Terminal o dos ventanas PowerShell)
- `iniciar.bat`: wrapper para ejecutar desde el explorador de archivos
- `gestion_backend/start.ps1`: instala dependencias y arranca Django en `:8000`
- `gestion-frontend/start.ps1`: instala dependencias y arranca Vite en `:7183`
- `crear_superusuario`: comando CLI interactivo para crear el primer SUPERADMIN

---

## Módulos pendientes / no integrados

### Incompletos (infraestructura parcialmente lista)

| Módulo | Estado actual | Qué falta |
|--------|--------------|-----------|
| **Rol CONDUCTOR (acceso al sistema)** | Modelo y rol definidos | Login, layout y vistas propias para conductores. No pueden ingresar al sistema actualmente. |
| **Simulador de vencimientos (UI)** | Endpoint backend listo: `GET /api/empresa/simulador-vencimientos/` | Página frontend que consuma el endpoint y muestre la proyección visualmente. |
| **Notificaciones por email (producción)** | Backend configurado en modo consola | Activar variables SMTP en `.env` (comentadas). Email backend debe cambiarse de `console` a `smtp`. |
| **Notificaciones WhatsApp/SMS** | Opciones en `ReglaMantenimiento` (campo `canal`) | Integración con servicio externo (Twilio, etc.). El comando de management tiene `pass` donde debería enviar. |
| **Job programado (cron)** | Comando `evaluar_mantenciones_predictivas` y `evaluar_documentos_vencimiento` listos | Configurar programación automática diaria (cron, Celery Beat, Windows Task Scheduler). |
| **Telemetría GPS** | Modelos `Ubicacion` y `Evento` en BD | Endpoints REST, integración con GPS/OBD, y UI de mapa en tiempo real. |
| **Módulo Documentos (UI completa)** | Modelos y backend funcionales | La ruta `/empresa/documentos` y `/documentos` están marcadas como "Próximamente" en el sidebar. |

### No implementados (funcionalidad nueva)

| Módulo | Descripción |
|--------|-------------|
| **Módulo de gastos operativos** | Registro de gastos: combustible, peajes, reparaciones no programadas por vehículo. No existe modelo ni API. |
| **Módulo de rutas/viajes** | Registro de viajes realizados: origen, destino, distancia, conductor, vehículo, fecha. No existe. |
| **Reportes y exportación** | Exportar datos a PDF/Excel/CSV: mantenciones, vehículos, conductores, logs. La ruta existe ("Próximamente"). |
| **Módulo de finanzas** | Costos operativos consolidados, análisis financiero de flota. La ruta existe ("Próximamente"). |
| **Historial de incidentes** | Registro de accidentes, multas, infracciones por conductor o vehículo. No existe. |
| **Agendamiento con talleres** | Agendar citas con talleres para mantenciones, con confirmación y seguimiento. No existe. |
| **Recuperación de contraseña autogestionada** | Solo el SUPERADMIN puede resetear contraseñas. No hay flujo de "olvidé mi contraseña" para el usuario. |
| **Autenticación 2FA** | No implementada. Capa extra de seguridad especialmente útil para SUPERADMIN. |
| **Aplicación móvil** | La API REST ya existe. No hay app iOS/Android. El rol CONDUCTOR la necesitaría. |
| **Integración SII (Chile)** | Validación de RUT empresarial en línea contra el Servicio de Impuestos Internos. |
| **Integración Registro Civil** | Verificación de licencias de conducir vigentes en tiempo real. |
| **Migración a PostgreSQL** | Actualmente SQLite3 (solo válido en desarrollo). Para producción se requiere PostgreSQL. |
| **Deployment / CI-CD** | No existe Dockerfile, configuración nginx/gunicorn, ni pipeline de despliegue. |

---

## Modelos de datos principales

### Usuario
```
id, email (único), password
rut_cifrado (Fernet), rut_hash (SHA256, indexed, único)
nombre_cifrado, telefono_cifrado, licencia_cifrada
rol (SUPERADMIN | USUARIO | CONDUCTOR)
empresa (FK → Empresa, nullable)
permisos (M2M → Permiso)
intentos_fallidos, is_blocked, is_active, is_superuser
preferencias_notificacion (JSONField)
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

### PlanMantenimiento
```
id, empresa (FK), nombre, descripcion, activo, created_at
```

### ReglaMantenimiento
```
id, plan (FK)
tipo (texto libre, ej: "Aceite", "Frenos")
prioridad (alta | media | baja)
intervalo_dias, umbral_alerta_dias
canal (email | push | whatsapp | sms)
escalar_sin_respuesta (bool), bloquear_despacho (bool)
costo_estimado (decimal)
```

### VehiculoPlan
```
id, vehiculo (FK), plan (FK), fecha_asignacion
[unique_together: vehiculo + plan]
```

### MantencionProgramada
```
id, vehiculo (FK), regla (FK → ReglaMantenimiento)
fecha_ultima (date), fecha_siguiente (date)
estado (activa | inactiva)
```

### AlertaMantencion
```
id, mantencion_programada (FK)
nivel (por_vencer | vencida)
dias_restantes (int — negativo si vencida)
pct_avance (float)
enviada (bool), atendida (bool)
fecha_creacion, fecha_atencion (nullable)
```

### Ubicacion (sin UI activa)
```
id, vehiculo (FK)
latitud, longitud, velocidad, combustible, timestamp
```

### LogAuditoria
```
id, tipo (SEGURIDAD | ACTIVIDAD), accion
usuario (FK, nullable), detalle (JSONField), ip, fecha (indexed)
```

### Notificacion
```
id, usuario (FK), tipo, titulo, mensaje
leida (bool), url_accion, extra (JSONField), fecha
```

---

## API REST — Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/login/` | Login por RUT |
| GET | `/api/dashboard/` | Dashboard SUPERADMIN |
| GET | `/api/empresa/dashboard/` | Dashboard de empresa |
| GET | `/api/empresas/` | Listar empresas |
| POST | `/api/empresas/crear/` | Crear empresa |
| GET/PUT/DELETE | `/api/empresas/:id/` | Ver / editar / suspender empresa |
| GET | `/api/usuarios/` | Listar usuarios |
| POST | `/api/usuarios/crear/` | Crear usuario |
| GET/PUT/DELETE | `/api/usuarios/:id/` | Ver / editar / desactivar usuario |
| POST | `/api/usuarios/:id/reset-password/` | Reset de contraseña |
| POST | `/api/usuarios/:id/toggle-block/` | Bloquear / desbloquear |
| GET | `/api/usuarios/:id/historial/` | Historial de auditoría del usuario |
| GET/PUT | `/api/usuarios/:id/permisos/` | Ver / modificar permisos |
| GET | `/api/permisos/` | Listar permisos disponibles |
| GET/POST | `/api/empresa/flotas/` | Listar / crear flotas |
| GET/PUT/DELETE | `/api/empresa/flotas/:id/` | CRUD de flota |
| GET | `/api/admin/flotas/` | Vista global de flotas (SUPERADMIN) |
| GET/POST | `/api/empresa/vehiculos/` | Listar / crear vehículos |
| GET/PUT/DELETE | `/api/empresa/vehiculos/:id/` | CRUD de vehículo |
| GET/POST | `/api/empresa/conductores/` | Listar / crear conductores |
| GET/PUT/DELETE | `/api/empresa/conductores/:id/` | CRUD de conductor |
| POST | `/api/empresa/conductores/:id/asignar/` | Asignar vehículo |
| POST | `/api/empresa/conductores/:id/desasignar/` | Desasignar vehículo |
| GET/POST | `/api/empresa/mantenciones/` | Listar / crear mantenciones |
| GET | `/api/empresa/mantenciones/resumen/` | Resumen: costos y conteos por estado |
| GET | `/api/empresa/mantenciones/calendario/` | Mantenciones por mes |
| GET/PUT/DELETE | `/api/empresa/mantenciones/:id/` | CRUD de mantención |
| GET/POST | `/api/empresa/planes-mantenimiento/` | Listar / crear planes predictivos |
| GET/PUT/PATCH/DELETE | `/api/empresa/planes-mantenimiento/:id/` | CRUD de plan predictivo |
| GET | `/api/empresa/alertas-mantenimiento/` | Listar alertas (filtros: nivel, estado) |
| POST | `/api/empresa/alertas-mantenimiento/:id/atender/` | Atender alerta |
| GET | `/api/empresa/simulador-vencimientos/` | Proyección futura (sin UI aún) |
| GET/POST | `/api/configuracion/planes/` | CRUD de planes de suscripción |
| GET/PUT/DELETE | `/api/configuracion/planes/:id/` | CRUD de plan de suscripción |
| GET | `/api/logs/` | Logs de auditoría (paginado, 50/página) |
| GET | `/api/notificaciones/` | Listar notificaciones del usuario |
| GET | `/api/notificaciones/no-leidas/` | Solo notificaciones no leídas |
| POST | `/api/notificaciones/leer/` | Marcar como leída |
| GET/PUT | `/api/notificaciones/preferencias/` | Preferencias de notificación |

---

## Rutas frontend (Vue Router)

### Panel SUPERADMIN (layout `Base.vue`)
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
/predictivo
/documentos, /finanzas, /reportes   ← "Próximamente"
```

### Panel EMPRESA (layout `EmpresaLayout.vue`, rol `USUARIO`)
```
/empresa/dashboard
/empresa/flota, /empresa/flota/nueva, /empresa/flota/:id/editar
/empresa/flota/:flotaId/nuevo-vehiculo, /empresa/vehiculos/:id/editar
/empresa/conductores, /empresa/conductores/nuevo
/empresa/conductores/:id, /empresa/conductores/:id/editar
/empresa/mantenciones, /empresa/mantenciones/calendario
/empresa/mantenciones/nueva, /empresa/mantenciones/:id/editar
/empresa/mantenciones/historial
/empresa/predictivo
/empresa/notificaciones
/empresa/preferencias-notificaciones
/empresa/documentos, /empresa/finanzas, /empresa/reportes   ← "Próximamente"
```

---

## Estado del proyecto (resumen)

| Módulo | Estado |
|--------|--------|
| Autenticación y seguridad | Completo |
| Gestión de usuarios | Completo |
| Permisos granulares | Completo |
| Gestión de empresas (multitenancy) | Completo |
| Planes de suscripción | Completo |
| Gestión de flotas y vehículos | Completo |
| Gestión de conductores | Completo |
| Documentos con vencimiento (backend + evaluación) | Completo |
| Documentos con vencimiento (UI dedicada) | **Pendiente** ("Próximamente") |
| Mantenciones correctivas | Completo |
| Mantenimiento predictivo | Completo |
| Simulador de vencimientos (backend) | Completo |
| Simulador de vencimientos (UI) | **Pendiente** |
| Auditoría y logs | Completo |
| Notificaciones in-app | Completo |
| Notificaciones por email (SMTP producción) | **Parcial** (requiere configurar `.env`) |
| Notificaciones WhatsApp/SMS | **Pendiente** (campo existe, integración no) |
| Job automático (cron) | **Pendiente** (comandos listos, sin programar) |
| Dashboard SUPERADMIN | Completo |
| Dashboard de empresa | Completo |
| Rol CONDUCTOR (login y UI) | **Pendiente** (solo modelo) |
| Telemetría GPS | **Pendiente** (solo modelo) |
| Módulo de gastos operativos | **No implementado** |
| Módulo de rutas/viajes | **No implementado** |
| Reportes y exportación (PDF/Excel) | **No implementado** ("Próximamente") |
| Módulo de finanzas | **No implementado** ("Próximamente") |
| Historial de incidentes | **No implementado** |
| Recuperación de contraseña autogestionada | **No implementado** |
| Autenticación 2FA | **No implementado** |
| Aplicación móvil | **No implementado** |
| Deployment a producción | **No implementado** |
| Migración a PostgreSQL | **No implementado** |

---

## Archivos clave

```
gestion_flota/
├── iniciar.ps1 / iniciar.bat
├── contexto.md                              ← Este archivo
├── docs/documentacion.md
├── gestion_backend/
│   ├── requirements.txt
│   ├── start.ps1
│   ├── .env                                 ← Claves secretas (no versionar)
│   ├── gestion_backend/
│   │   ├── settings.py
│   │   └── urls.py
│   └── g_de_flota/
│       ├── models.py                        ← 20+ modelos ORM
│       ├── views.py                         ← 40+ endpoints REST
│       ├── serializers.py
│       ├── audit.py                         ← registrar_log()
│       ├── notificaciones.py                ← notificar(), notificar_admins_empresa()
│       ├── middleware.py                    ← Timeout de sesión
│       ├── backends.py                      ← Autenticación por RUT
│       ├── utils.py                         ← Cifrado Fernet
│       └── management/commands/
│           ├── crear_superusuario.py
│           ├── evaluar_documentos_vencimiento.py
│           └── evaluar_mantenciones_predictivas.py
└── gestion-frontend/
    ├── start.ps1
    ├── vite.config.js                       ← Proxy /api → :8000, puerto 7183
    └── src/
        ├── router/index.js
        ├── utils/
        │   ├── api.js
        │   ├── empresaActiva.js
        │   ├── permisos.js
        │   └── useToast.js
        ├── components/
        │   ├── AppToast.vue
        │   ├── PermisoToast.vue
        │   ├── NotificacionesBell.vue
        │   └── ConfirmModal.vue
        └── web/
            ├── login.vue
            ├── Base.vue / Dashboard.vue     ← Layout + dashboard SUPERADMIN
            ├── EmpresaLayout.vue            ← Layout USUARIO
            ├── clientes/                    ← CRUD empresas
            ├── usuarios/                    ← CRUD usuarios
            ├── configuracion/              ← Planes suscripción
            ├── permisos/                   ← Permisos granulares
            ├── logs/                       ← Auditoría
            ├── notificaciones/             ← Centro notificaciones
            └── empresa/
                ├── flota/                  ← CRUD flotas y vehículos
                │   └── mantenciones/      ← CRUD mantenciones
                ├── conductores/            ← CRUD conductores
                └── predictivo/            ← Dashboard predictivo
```
