#!/usr/bin/env bash
# ── AI Game Simulation Platform — Start Script (Bash) ──
# Usage: chmod +x start.sh && ./start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "====================================="
echo "  AI Game Simulation Platform"
echo "====================================="
echo ""

# ── 1. Docker containers ──
echo "[1/4] Starting Docker containers (PostgreSQL + Redis)..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d postgres redis
echo "  -> PostgreSQL on localhost:5432, Redis on localhost:6379"

# ── 2. Wait for PostgreSQL ──
echo "[2/4] Waiting for PostgreSQL to accept connections..."
retries=0
until docker exec gameplatform-postgres pg_isready -U postgres > /dev/null 2>&1 || [ $retries -ge 15 ]; do
  retries=$((retries + 1))
  sleep 1
done

if [ $retries -ge 15 ]; then
  echo "ERROR: PostgreSQL did not become ready in time."
  exit 1
fi
echo "  -> PostgreSQL is ready"

# ── 3. Backend ──
echo "[3/4] Starting backend (FastAPI + Uvicorn)..."
(
  cd "$SCRIPT_DIR/backend"
  source .venv/bin/activate
  echo "Running Alembic migrations..."
  alembic upgrade head
  echo "Starting Uvicorn..."
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &

echo "  -> Backend starting on http://localhost:8000"
echo "  -> API docs at http://localhost:8000/docs"

# ── 4. Frontend ──
echo "[4/4] Starting frontend (Vite dev server)..."
(
  cd "$SCRIPT_DIR/frontend"
  npm run dev
) &

echo "  -> Frontend starting on http://localhost:5173"
echo ""
echo "====================================="
echo "  All services starting!"
echo "====================================="
echo ""
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for background processes
wait
