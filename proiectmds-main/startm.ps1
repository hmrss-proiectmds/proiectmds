# ── AI Game Simulation Platform — Start Script (PowerShell) ──
# Usage: Right-click → "Run with PowerShell" or run from terminal: .\start.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  AI Game Simulation Platform" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Docker containers ──
Write-Host "[1/4] Starting Docker containers (PostgreSQL + Redis)..." -ForegroundColor Yellow
docker compose up -d postgres redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Compose failed. Make sure Docker Desktop is running." -ForegroundColor Red
    exit 1
}
Write-Host "  -> PostgreSQL on localhost:5432, Redis on localhost:6379" -ForegroundColor Green

# ── 2. Wait for PostgreSQL to be ready ──
Write-Host "[2/4] Waiting for PostgreSQL to accept connections..." -ForegroundColor Yellow
$retries = 0
do {
    $retries++
    Start-Sleep -Seconds 1
    $ready = docker exec gameplatform-postgres pg_isready -U postgres 2>$null
} while ($LASTEXITCODE -ne 0 -and $retries -lt 15)

if ($retries -ge 15) {
    Write-Host "ERROR: PostgreSQL did not become ready in time." -ForegroundColor Red
    exit 1
}
Write-Host "  -> PostgreSQL is ready" -ForegroundColor Green

# ── 3. Backend ──
Write-Host "[3/4] Starting backend (FastAPI + Uvicorn)..." -ForegroundColor Yellow

# Use the venv Python directly (works regardless of execution policy)
$venvPython = "C:\Users\maram\Downloads\proiectmds-main\.venv\Scripts\python.exe"
$backendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
    "cd '$PSScriptRoot\backend'; " +
    "Write-Host 'Running Alembic migrations...' -ForegroundColor Yellow; " +
    "& '$venvPython' -m alembic upgrade head; " +
    "Write-Host 'Starting Uvicorn...' -ForegroundColor Green; " +
    "& '$venvPython' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
) -PassThru

Write-Host "  -> Backend starting on http://localhost:8000" -ForegroundColor Green
Write-Host "  -> API docs at http://localhost:8000/docs" -ForegroundColor Green

# ── 4. Frontend ──
Write-Host "[4/4] Starting frontend (Vite dev server)..." -ForegroundColor Yellow

$frontendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$PSScriptRoot\frontend'; " +
    "npm run dev"
) -PassThru

Write-Host "  -> Frontend starting on http://localhost:5173" -ForegroundColor Green

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  All services starting!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Close the spawned terminal windows to stop individual services." -ForegroundColor DarkGray
Write-Host "Run 'docker compose down' to stop PostgreSQL and Redis." -ForegroundColor DarkGray
