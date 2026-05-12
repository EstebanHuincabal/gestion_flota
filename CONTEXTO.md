# CONTEXTO DEL PROYECTO: GESTIÓN DE FLOTA

Este documento proporciona una visión detallada y técnica del proyecto de Gestión de Flota, abarcando su arquitectura, modelos de datos, seguridad, y estructura de frontend.

---

## 1. Arquitectura General
El sistema utiliza una arquitectura desacoplada:
- **Backend:** Django 5.x + Django REST Framework (DRF) actuando como una API REST.
- **Frontend:** Vue.js 3 con Vite y TailwindCSS.
- **Base de Datos:** SQLite (desarrollo).

---

## 2. Modelos de Datos (Backend)

### Seguridad y Usuarios
- **Usuario (`AbstractUser`):** Modelo de usuario personalizado.
  - **Roles:** `SUPERADMIN`, `USUARIO` (Admin de empresa), `CONDUCTOR`.
  - **Autenticación:** Sistema híbrido. `RutBackend` para login vía RUT/Password y `ModelBackend` estándar para el admin de Django.
  - **Seguridad:** Control de intentos fallidos (bloqueo automático tras 5 intentos) y registro de actividad.
  - **Cifrado:** Utiliza Fernet para cifrar datos sensibles como RUT, Nombres, Teléfonos y Licencias en la BD.
- **Permiso:** Sistema granular de permisos asignables a usuarios con rol `USUARIO`.

### Estructura Organizacional
- **PlanSuscripcion:** Define límites para las empresas (`max_flotas`, `max_vehiculos`, `max_conductores`).
- **Empresa:** Entidad principal. Almacena datos cifrados (RUT, Email, Dirección, etc.). Organizada por regiones de Chile.

### Gestión de Flota
- **Flota:** Agrupación lógica de vehículos dentro de una empresa.
- **Vehículo:** Almacena patente, marca, modelo, año, tipo de combustible y kilometraje.
- **Asignacion:** Vincula un `Conductor` con un `Vehiculo`. Mantiene historial de quién usó qué vehículo y cuándo.
- **DocumentoBase (Abstracto):** Lógica para `DocumentoConductor` y `DocumentoVehiculo`. Calcula estados automáticamente (`vigente`, `por_vencer`, `vencido`).

### Operaciones y Telemetría
- **Ubicacion:** Historial de latitud, longitud, velocidad y combustible por vehículo.
- **Evento:** Registro de hitos o alertas de vehículos.
- **Mantencion:** Gestión de servicios técnicos (programadas, realizadas, costos).

### Auditoría
- **LogAuditoria:** Registro detallado de seguridad y actividad (login, cambios de rol, creación de empresas, IPs de origen).

---

## 3. Seguridad y Backend

- **Cifrado de Datos:** Implementación personalizada en `models.py` usando `cryptography.fernet` con claves derivadas de `settings.ENCRYPTION_KEY`.
- **Middleware de Seguridad:** 
  - `ConfiguracionSeguridadMiddleware`: Controla el timeout por inactividad de sesión para la API.
- **RUT Chileno:** Utiliza funciones de normalización y hashing (`rut_hash` vía SHA-256) para búsquedas eficientes sin exponer el RUT plano en la BD.
- **CORS/CSRF:** Configurado específicamente para permitir la comunicación segura con el frontend en `localhost:7183`.

---

## 4. Estructura del Frontend (Vue.js)

### Tecnologías
- **Vue 3:** Composition API.
- **Vite:** Herramienta de construcción y dev server.
- **TailwindCSS:** Framework de estilos.
- **Chart.js:** Visualización de estadísticas en dashboards.

### Organización de Vistas (`src/web`)
- **`login.vue`:** Gestión de acceso centralizado.
- **`Dashboard.vue`:** Vista general con KPIs y gráficos.
- **`clientes/`:** CRUD de Empresas para el Superadmin.
- **`empresa/`:**
  - **`conductores/`:** Gestión de perfiles de conductor, licencias y documentos.
  - **`flota/`:** Gestión de vehículos, asignaciones y mantenimientos.
- **`usuarios/`:** Gestión de usuarios administrativos de la empresa.
- **`permisos/`:** Panel de asignación de permisos granulares.

### Utilidades
- **`api.js`:** Wrapper para `fetch` con gestión automática de headers y errores.
- **`empresaActiva.js`:** Gestión de la empresa seleccionada en la sesión actual.
- **`permisos.js`:** Lógica para verificar permisos granulares en los componentes.

---

## 5. Scripts de Ejecución
- `iniciar.bat` / `iniciar.ps1`: Facilitan el arranque simultáneo del backend y el frontend.
- `package.json` incluye un comando `dev` que limpia el puerto `7183` antes de iniciar para evitar colisiones.
