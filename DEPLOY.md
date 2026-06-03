# Guía de despliegue en producción

Servidor: `157.180.85.17`  
Stack: Docker Compose · Django/Daphne (ASGI) · PostgreSQL 16 · Redis 7 · Nginx

---

## 1. Requisitos del servidor (una sola vez)

Conectarse por SSH y ejecutar:

```bash
# Actualizar paquetes
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose plugin (ya incluido en Docker moderno)
docker compose version   # debe mostrar v2.x
```

---

## 2. Subir el proyecto al servidor

Desde tu PC (en la raíz del proyecto):

```bash
# Primera vez: copiar todos los archivos al servidor
scp -r . usuario@157.180.85.17:/opt/gestion_flota

# Actualizaciones posteriores (más rápido):
rsync -avz --exclude='node_modules' --exclude='.git' \
  --exclude='db.sqlite3*' --exclude='media' \
  . usuario@157.180.85.17:/opt/gestion_flota
```

---

## 3. Crear el archivo de entorno en el servidor

```bash
ssh usuario@157.180.85.17
cd var/www/gestion_flota

# Crear .env.production a partir de la plantilla
cp .env.production.example .env.production
```

Editar `.env.production` y completar los tres valores marcados como `CAMBIAR_`:

```bash
nano .env.production
```

Los campos a rellenar:

| Variable | Qué poner |
|---|---|
| `SECRET_KEY` | Cadena aleatoria larga — genera con: `python3 -c "import secrets;print(secrets.token_urlsafe(64))"` |
| `ENCRYPTION_KEY` | Clave estable del cifrado de datos — **guárdala a buen recaudo, no la cambies** |
| `FERNET_KEY` | Genera con: `python3 -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `TRACCAR_USER` | Email del admin de Traccar (ej: `admin@tudominio.cl`). Se **crea solo** en el primer arranque. |
| `TRACCAR_PASSWORD` | Contraseña de ese admin. Con ella entras a la web de Traccar (`:8082`). |
| `GPS_WEBHOOK_KEY` | Opcional. Clave para proteger el webhook Traccar→backend (déjala vacía si no la usas). |

> ⚠️ Evita el carácter `|` en `POSTGRES_PASSWORD`: el `traccar.xml` se genera con `sed` y ese carácter es el delimitador.

Los demás valores ya están configurados (PostgreSQL, Redis, IP del servidor, `TRACCAR_URL`).

---

## 4. Arrancar (instala todo solo)

```bash
cd /opt/gestion_flota

# Construir imágenes y levantar todos los servicios en background
docker compose --env-file .env.production up --build -d
```

Al ejecutarse, automáticamente:
1. Arranca PostgreSQL, crea la base de Django y la base `traccar`, y espera a que esté listo (healthcheck).
2. Arranca Redis.
3. El backend instala las dependencias Python, ejecuta `migrate` y `collectstatic`, y levanta Daphne (HTTP + WebSockets).
4. **Traccar** (gateway GPS) genera su `traccar.xml` desde la plantilla, arranca y queda escuchando los protocolos GPS y su web/API en `:8082`.
5. **`traccar-init`** espera a Traccar, crea el usuario administrador (`TRACCAR_USER` / `TRACCAR_PASSWORD`) de forma idempotente y termina.
6. El frontend construye el SPA con Vite y Nginx lo sirve en el puerto 80.

El sistema queda disponible en: **http://157.180.85.17**

> El servicio `traccar-init` aparecerá como `Exited (0)` en `docker compose ps` cuando termina: es lo esperado, hizo su trabajo una sola vez.

---

## 5. Verificar que todo corre

```bash
# Ver estado de los contenedores
docker compose ps

# Ver logs del backend (migraciones, errores)
docker compose logs backend -f

# Ver logs de nginx
docker compose logs frontend -f
```

Todos los servicios deben tener estado `Up` o `healthy`.

---

## 6. Comandos de mantenimiento

```bash
# Reiniciar todo
docker compose restart

# Parar todo
docker compose down

# Actualizar tras subir cambios de código
docker compose --env-file .env.production up --build -d

# Ver logs en tiempo real
docker compose logs -f

# Abrir shell Django en el contenedor
docker compose exec backend python manage.py shell

# Ejecutar una migración manualmente
docker compose exec backend python manage.py migrate

# Entrar a la base de datos PostgreSQL
docker compose exec db psql -U gsdm_user -d Gestion_de_flota
```

---

## 7. Persistencia de datos

Los datos no se pierden al reconstruir las imágenes porque están en volúmenes Docker:

| Volumen | Contenido |
|---|---|
| `pgdata` | Base de datos PostgreSQL (Django **y** Traccar) |
| `media_volume` | Archivos subidos (documentos, fotos, comprobantes) |
| `static_volume` | Estáticos del admin de Django |
| `traccar_data` | Datos internos de Traccar (logs, archivos del gateway) |

Para hacer un backup de la base de datos:

```bash
docker compose exec db pg_dump -U gsdm_user Gestion_de_flota > backup_$(date +%Y%m%d).sql
```

Para restaurar:

```bash
cat backup_YYYYMMDD.sql | docker compose exec -T db psql -U gsdm_user -d Gestion_de_flota
```

---

## 8. Notas importantes

- El sistema arranca con base de datos **vacía**. El primer superusuario se crea desde el admin de Django en `/admin/` o vía `python manage.py createsuperuser` dentro del contenedor.
- Si cambias `ENCRYPTION_KEY`, los datos cifrados (RUT, email, patente, GPS, etc.) dejan de ser legibles. **No la cambies una vez en producción.**
- WebSockets (`/ws/`) funcionan sobre el mismo puerto 80 gracias al proxy de Nginx.
- El frontend en producción llama a `/api/` con rutas relativas → mismo origen, sin CORS.

---

## 9. Traccar (gateway GPS)

Traccar recibe a los dispositivos GPS físicos (~200 protocolos) y reenvía cada
posición al backend. **No requiere configuración manual**: el `traccar.xml` se
genera al arrancar desde `traccar.xml.template` con las credenciales de la base, y
el servicio `traccar-init` crea el administrador solo.

- **Web/API de Traccar:** `http://157.180.85.17:8082` — entra con `TRACCAR_USER` / `TRACCAR_PASSWORD`.
- **Alta automática de dispositivos:** al registrar un GPS en el panel (Flota → GPS),
  el backend lo crea también en Traccar vía su API REST (`traccar_client.py`).
- **Puertos GPS:** el rango `5000-5150` (TCP/UDP) y `5055/udp` (OsmAnd) quedan
  expuestos para que los dispositivos físicos se conecten. En cada GPS hay que
  configurar la IP pública del servidor y el puerto del protocolo que corresponda.

### Crear el admin a mano (si hiciera falta)

El `traccar-init` lo hace solo, pero si necesitas recrearlo (ej: olvidaste la
contraseña), el procedimiento manual es:

```bash
# 1. Habilitar el registro en la base de Traccar
docker compose exec db psql -U <POSTGRES_USER> -d traccar \
  -c "UPDATE tc_servers SET registration = TRUE;"

# 2. Crear el usuario (el primero se vuelve administrador)
curl -X POST http://localhost:8082/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Administrador","email":"admin@tudominio.cl","password":"TU_PASSWORD"}'

# 3. Volver a cerrar el registro
docker compose exec db psql -U <POSTGRES_USER> -d traccar \
  -c "UPDATE tc_servers SET registration = FALSE;"
```

### Base de datos de Traccar

Traccar usa la base `traccar` dentro del mismo PostgreSQL. Se crea sola en el
primer arranque (`docker/db-init/01-create-traccar-db.sql`). En un despliegue ya
existente (volumen `pgdata` no vacío) hay que crearla una vez a mano:

```bash
docker compose exec db psql -U <POSTGRES_USER> -c "CREATE DATABASE traccar;"
```
