# Una imagen para todo el banco de pruebas: gestor, API protegida, atacante y proxy.
#   docker compose -f docker/compose.yml up -d --build
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git: herramienta `git` del proxy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias primero, para aprovechar la caché de capas.
COPY contracts/requirements.txt contracts/requirements.txt
COPY services/requirements.txt services/requirements.txt
COPY proxy/requirements.txt proxy/requirements.txt
COPY proxy/agent/requirements.txt proxy/agent/requirements.txt
COPY engine/requirements.txt engine/requirements.txt
COPY engine/graph/requirements.txt engine/graph/requirements.txt
RUN pip install \
    -r contracts/requirements.txt \
    -r services/requirements.txt \
    -r proxy/requirements.txt \
    -r proxy/agent/requirements.txt \
    -r engine/requirements.txt \
    -r engine/graph/requirements.txt

COPY . .

ENV LOG_DIR=/logs \
    SECRETS_MANIFEST=demo/secrets_manifest.json

CMD ["sleep", "infinity"]
