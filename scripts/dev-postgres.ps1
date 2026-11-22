# Starts a synthetic-only PostgreSQL cluster on 127.0.0.1:5433 with trust authentication.
# The data directory is var/pgdata and is gitignored. Do not use this for official records.

$ErrorActionPreference = "Stop"
$bin = "C:\Program Files\PostgreSQL\18\bin"
$pg = Join-Path $PSScriptRoot "..\var\pgdata"
$log = Join-Path $PSScriptRoot "..\var\pg.log"
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "..\var") | Out-Null
if (-not (Test-Path (Join-Path $pg "PG_VERSION"))) {
  & "$bin\initdb.exe" -D $pg -U vagexa --auth=trust --encoding=UTF8 --locale=C
}
& "$bin\pg_ctl.exe" -D $pg -l $log -o "-p 5433 -h 127.0.0.1" start
& "$bin\psql.exe" -h 127.0.0.1 -p 5433 -U vagexa -d postgres --no-password -c "SELECT 1 FROM pg_database WHERE datname = 'vagexa'" | Out-Null
& "$bin\psql.exe" -h 127.0.0.1 -p 5433 -U vagexa -d postgres --no-password -c "CREATE DATABASE vagexa" 2>$null
& "$bin\psql.exe" -h 127.0.0.1 -p 5433 -U vagexa -d postgres --no-password -c "CREATE DATABASE vagexa_test" 2>$null
Write-Output "PostgreSQL is ready on 127.0.0.1:5433"
