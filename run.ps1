# ============================================================
# ABDM M2 Link Token Demo Quick-Start  (PowerShell)
# Credentials & URLs are loaded automatically from .env
# ============================================================

pip install -r requirements.txt

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  ABDM Link Token Demo starting on localhost:8000" -ForegroundColor Cyan
Write-Host "  Dashboard : http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host "  Swagger   : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
