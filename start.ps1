# Financial AI Platform - PowerShell Startup Script

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       Financial AI Platform - Docker Startup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker status
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running"
    }
} catch {
    Write-Host "[ERROR] Docker is not running or not installed!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}

# 2. Check or create .env file
if (-not (Test-Path ".env")) {
    Write-Host "[*] Creating .env from .env.example..." -ForegroundColor Green
    Copy-Item ".env.example" ".env"
}

# 3. Start Docker Compose
Write-Host "[*] Starting containers via Docker Compose..." -ForegroundColor Green
docker compose up --build -d

# 4. Display service status
Write-Host ""
Write-Host "[*] Container Status:" -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " All services started!" -ForegroundColor Green
Write-Host " - Frontend Web UI:  http://localhost:3000" -ForegroundColor White
Write-Host " - Backend API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host " - Backend Health:   http://localhost:8000/api/health" -ForegroundColor White
Write-Host " - Ollama Engine:    http://localhost:11434" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To follow logs in real-time:" -ForegroundColor Yellow
Write-Host "  docker compose logs -f" -ForegroundColor White
