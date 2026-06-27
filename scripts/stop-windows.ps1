$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot

docker compose -f "$rootDir\docker-compose.yml" down --remove-orphans
Write-Host "PM app stopped"
