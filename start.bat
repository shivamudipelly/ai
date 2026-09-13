@echo off
echo ========================================================
echo        Financial AI Platform - Docker Startup
echo ========================================================
echo.

:: Check if Docker is installed and running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running or not installed!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

:: Copy .env.example to .env if .env does not exist
if not exist ".env" (
    echo [*] Creating .env from .env.example...
    copy .env.example .env >nul
)

echo [*] Building and launching containers via Docker Compose...
docker compose up --build -d

echo.
echo [*] Waiting for services to become healthy...
docker compose ps

echo.
echo ========================================================
echo  All services started!
echo  - Frontend Web UI:  http://localhost:3000
echo  - Backend API Docs: http://localhost:8000/docs
echo  - Backend Health:   http://localhost:8000/api/health
echo  - Ollama Engine:    http://localhost:11434
echo ========================================================
echo.
echo To view real-time logs, run:
echo   docker compose logs -f
echo.
pause
