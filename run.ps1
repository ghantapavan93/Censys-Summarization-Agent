# run.ps1 - Quick start script for Censys Summarization Agent
$ErrorActionPreference = "Stop"

Write-Host "Starting Censys Summarization Agent..." -ForegroundColor Green

# Check if virtual environment exists, create if not
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r backend\requirements.txt | Out-Null

# Start server from repo root so 'backend' package imports resolve
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Swagger UI available at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Magenta

# Ensure current repo path is on PYTHONPATH so 'backend' package can be imported
$env:PYTHONPATH = (Get-Location).Path

uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000