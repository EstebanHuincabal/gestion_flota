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
*   **Autenticación Híbrida:** El acceso al panel principal se realiza mediante el RUT del usuario y su contraseña.
*   **Tipos de Usuarios (Roles):** El sistema reconoce 3 jerarquías:
    *   `SUPERADMIN`: Administra a nivel global, gestiona las empresas cliente.
    *   `USUARIO`: Es el administrador o responsable dentro de una empresa específica.
    *   `CONDUCTOR`: Perfil operativo asociado directamente a un vehículo de la flota.
*   **Aislamiento de Datos:** Todo en el frontend gira en torno a la "empresa activa". El código asegura que cada usuario solo vea e interactúe con la información que pertenece a su propia organización.

## 📚 6. ¿Dónde aprender más?
Una vez que te familiarices con este documento, te sugerimos leer el archivo `CONTEXTO.md` ubicado en la raíz del proyecto. Ese documento contiene detalles técnicos más profundos sobre los modelos de datos, arquitectura de seguridad y reglas de negocio.
