# One image: the built investigator app, the API, and PostgreSQL 16.
# Node is used only while building the static files.

FROM node:22-bookworm-slim AS web
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg openssl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/ /app/backend/
RUN pip install --no-cache-dir .
COPY --from=web /src/frontend/dist /app/static
COPY deploy/start.sh /app/start.sh
RUN chmod 755 /app/start.sh

ENV PYTHONUNBUFFERED=1 \
    VAGEXA_STATIC_DIR=/app/static \
    VAGEXA_STORAGE_DIR=/data/storage
EXPOSE 8000
CMD ["/app/start.sh"]
