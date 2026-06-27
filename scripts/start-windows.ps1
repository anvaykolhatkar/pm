$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot

docker compose -f "$rootDir\docker-compose.yml" up --build -d
Write-Host "PM app started at http://localhost:8000"
