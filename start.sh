#!/bin/bash
set -e

echo "========================================================"
echo "       Financial AI Platform - Docker Startup"
echo "========================================================"

if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running or not installed!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "[*] Creating .env from .env.example..."
    cp .env.example .env
fi

echo "[*] Launching containers via Docker Compose..."
docker compose up --build -d

echo ""
echo "[*] Container Status:"
docker compose ps

echo ""
echo "========================================================"
echo " All services started!"
echo " - Frontend Web UI:  http://localhost:3000"
echo " - Backend API Docs: http://localhost:8000/docs"
echo " - Backend Health:   http://localhost:8000/api/health"
echo " - Ollama Engine:    http://localhost:11434"
echo "========================================================"
