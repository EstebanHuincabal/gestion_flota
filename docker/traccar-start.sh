#!/bin/sh
# Genera traccar.xml desde la plantilla inyectando las credenciales de PostgreSQL,
# luego arranca Traccar. Las variables vienen del env_file de docker-compose.
set -e

sed \
  -e "s|__DB_USER__|${POSTGRES_USER}|g" \
  -e "s|__DB_PASS__|${POSTGRES_PASSWORD}|g" \
  /traccar.xml.template > /opt/traccar/conf/traccar.xml

exec java -jar /opt/traccar/tracker-server.jar conf/traccar.xml
