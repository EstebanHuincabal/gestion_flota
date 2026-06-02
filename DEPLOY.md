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

Los demás valores ya están configurados (PostgreSQL, Redis, IP del servidor).

---

## 4. Arrancar (instala todo solo)

```bash
cd /opt/gestion_flota

# Construir imágenes y levantar todos los servicios en background
docker compose --env-file .env.production up --build -d
```

Al ejecutarse, automáticamente:
1. Arranca PostgreSQL y espera a que esté listo (healthcheck).
2. Arranca Redis.
3. El backend instala las dependencias Python, ejecuta `migrate` y `collectstatic`, y levanta Daphne (HTTP + WebSockets).
4. El frontend construye el SPA con Vite y Nginx lo sirve en el puerto 80.

El sistema queda disponible en: **http://157.180.85.17**

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
| `pgdata` | Base de datos PostgreSQL |
| `media_volume` | Archivos subidos (documentos, fotos, comprobantes) |
| `static_volume` | Estáticos del admin de Django |

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
