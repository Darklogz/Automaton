@echo off
cd /d "%~dp0"

REM 1) Asegurar que Docker Desktop esté corriendo
docker info >nul 2>&1
if not errorlevel 1 goto docker_listo

echo Iniciando Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

set intentos=0
:esperar_docker
set /a intentos+=1
if %intentos% gtr 40 (
    echo Docker no inicio. Abrelo manualmente y vuelve a intentar.
    pause
    exit /b 1
)
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto esperar_docker

:docker_listo
REM 2) Levantar el Nucleo IA
docker compose up -d
if errorlevel 1 (
    echo No se pudo iniciar el Nucleo IA.
    pause
    exit /b 1
)

REM 3) Abrir la mascota (pythonw = sin ventana de consola)
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0src\host\main.py"
exit /b 0