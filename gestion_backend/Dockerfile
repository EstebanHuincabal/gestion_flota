FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# psycopg[binary] incluye wheels precompilados → no requiere libpq-dev.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# El comando de arranque (migrate + collectstatic + daphne) se define en docker-compose.yml.
