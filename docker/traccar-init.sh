#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# traccar-init — Crea el usuario administrador de Traccar de forma automática.
#
# Traccar 6.x no trae cuenta admin por defecto y el registro de usuarios viene
# deshabilitado (campo 'registration' en la tabla tc_servers). Este script, que
# corre UNA vez al levantar el stack:
#   1. Espera a que Traccar responda.
#   2. Habilita el registro por SQL (posible porque Traccar usa PostgreSQL).
#   3. Crea el admin por la API (el primer usuario se vuelve administrador).
#   4. Vuelve a cerrar el registro.
#
# Es idempotente: si el admin ya existe, el POST falla y se ignora.
# Credenciales tomadas de .env.production (TRACCAR_USER / TRACCAR_PASSWORD y
# POSTGRES_USER / POSTGRES_PASSWORD).
# ─────────────────────────────────────────────────────────────────────────────
set -e

apk add --no-cache postgresql-client curl >/dev/null

echo "[traccar-init] Esperando a que Traccar responda..."
until curl -sf http://traccar:8082/api/server >/dev/null 2>&1; do
    sleep 3
done

echo "[traccar-init] Habilitando el registro temporalmente..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d traccar \
    -c "UPDATE tc_servers SET registration = TRUE;"

echo "[traccar-init] Creando usuario administrador ($TRACCAR_USER)..."
if curl -sf -X POST http://traccar:8082/api/users \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"Administrador\",\"email\":\"$TRACCAR_USER\",\"password\":\"$TRACCAR_PASSWORD\"}" \
        >/dev/null; then
    echo "[traccar-init] Administrador creado correctamente."
else
    echo "[traccar-init] El administrador ya existía (o no se pudo crear); se continúa."
fi

echo "[traccar-init] Cerrando el registro de usuarios..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U "$POSTGRES_USER" -d traccar \
    -c "UPDATE tc_servers SET registration = FALSE;"

echo "[traccar-init] Listo. Traccar quedó con su administrador configurado."
