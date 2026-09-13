# Stop Financial AI Platform Containers
Write-Host "Stopping all Financial AI Platform containers..." -ForegroundColor Yellow
docker compose down
Write-Host "All containers stopped cleanly." -ForegroundColor Green
