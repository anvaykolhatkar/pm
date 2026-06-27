@echo off
set ROOT_DIR=%~dp0..

docker compose -f "%ROOT_DIR%\docker-compose.yml" down --remove-orphans
if errorlevel 1 exit /b 1

echo PM app stopped
