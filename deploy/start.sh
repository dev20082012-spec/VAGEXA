#!/bin/sh
# Start local PostgreSQL from the persistent disk, migrate, seed, then serve.
# This script does not drop databases, truncate tables, or downgrade migrations.
set -eu

PGDATA=/data/pg
PORT="${PORT:-8000}"
mkdir -p /data/storage "$PGDATA"
chown postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

if [ ! -f "$PGDATA/PG_VERSION" ]; then
  PASSWORD=$(openssl rand -hex 24)
  umask 077
  printf '%s' "$PASSWORD" > /data/db_password
  printf '%s\n' "$PASSWORD" > /tmp/pgpw
  chown postgres:postgres /tmp/pgpw
  chmod 600 /tmp/pgpw
  su -s /bin/sh postgres -c "/usr/lib/postgresql/16/bin/initdb -D $PGDATA --username=vagexa --pwfile=/tmp/pgpw --auth=scram-sha-256"
  rm -f /tmp/pgpw
elif [ ! -f /data/db_password ]; then
  echo "Database files exist but /data/db_password is missing. Refusing to reset the database." >&2
  exit 1
else
  PASSWORD=$(cat /data/db_password)
fi

su -s /bin/sh postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $PGDATA -w -l /tmp/postgres.log start -o '-c listen_addresses=127.0.0.1 -c port=5432 -c shared_buffers=128MB -c max_connections=20'"

umask 077
printf '127.0.0.1:5432:*:vagexa:%s\n' "$PASSWORD" > /data/.pgpass
chmod 600 /data/.pgpass
export PGPASSFILE=/data/.pgpass
if ! psql -h 127.0.0.1 -U vagexa -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='vagexa'" | grep -q 1; then
  createdb -h 127.0.0.1 -U vagexa vagexa
fi

export VAGEXA_DATABASE_URL="postgresql+psycopg://vagexa:${PASSWORD}@127.0.0.1:5432/vagexa"
export VAGEXA_DATA_MODE="${VAGEXA_DATA_MODE:-synthetic}"
export VAGEXA_COOKIE_SECURE="${VAGEXA_COOKIE_SECURE:-true}"
export VAGEXA_ENVIRONMENT="${VAGEXA_ENVIRONMENT:-production}"
export VAGEXA_REQUIRE_DEMO="${VAGEXA_REQUIRE_DEMO:-true}"
export VAGEXA_STATIC_DIR="${VAGEXA_STATIC_DIR:-/app/static}"
export VAGEXA_STORAGE_DIR="${VAGEXA_STORAGE_DIR:-/data/storage}"
export VAGEXA_PASSIVE_INTEL="${VAGEXA_PASSIVE_INTEL:-false}"
if [ -z "${VAGEXA_CORS_ORIGINS:-}" ] && [ -n "${FLY_APP_NAME:-}" ]; then
  export VAGEXA_CORS_ORIGINS="https://${FLY_APP_NAME}.fly.dev"
fi

cd /app/backend
python -m alembic upgrade head
python -m vagexa.deploy_boot

stop_database() {
  su -s /bin/sh postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $PGDATA -w -m fast stop" || true
}
trap 'kill -TERM "$SERVER" 2>/dev/null || true; wait "$SERVER" 2>/dev/null || true; stop_database' TERM INT

python -m uvicorn vagexa.api.main:create_app --factory --host 0.0.0.0 --port "$PORT" &
SERVER=$!
wait "$SERVER"
stop_database
