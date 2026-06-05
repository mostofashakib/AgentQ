#!/usr/bin/env bash
# AgentQ — Local Development Runner
# Kills any existing processes on :8000/:3000, then starts backend + frontend.
# Ctrl+C gracefully stops everything.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT/frontend"

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'

log()  { echo -e "${BOLD}[agentq]${RESET} $*"; }
ok()   { echo -e "${GREEN}  ✓${RESET} $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET} $*"; }
err()  { echo -e "${RED}  ✗${RESET} $*"; }

backend_log()  { while IFS= read -r line; do echo -e "${CYAN}[backend] ${RESET}$line"; done; }
frontend_log() { while IFS= read -r line; do echo -e "${GREEN}[frontend]${RESET} $line"; done; }

kill_port() {
  local port="$1" label="$2"
  if ! nc -z 127.0.0.1 "$port" 2>/dev/null; then return; fi
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    sleep 0.4
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
    ok "Cleared $label (port $port)"
  fi
}

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  log "Shutting down..."
  [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

log "Clearing any running processes..."
kill_port 8000 "backend"
kill_port 3000 "frontend"

# ── Virtual environment ───────────────────────────────────────────────────────
if [[ ! -d "$ROOT/.venv" ]]; then
  warn "No .venv found — creating with uv..."
  uv venv --python 3.12 "$ROOT/.venv"
fi

if [[ ! -f "$ROOT/.venv/bin/uvicorn" ]]; then
  warn "Installing Python deps with uv..."
  uv pip install -e "$ROOT[dev]"
fi
ok "Python environment ready"

# ── .env ─────────────────────────────────────────────────────────────────────
if [[ ! -f "$ROOT/.env" ]]; then
  warn ".env not found — copying from .env.example"
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

# ── Frontend deps ─────────────────────────────────────────────────────────────
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  warn "node_modules missing — running npm install..."
  npm --prefix "$FRONTEND_DIR" install --silent
fi
ok "Frontend deps ready"

# ── Start backend ─────────────────────────────────────────────────────────────
log "Starting backend on ${CYAN}http://localhost:8000${RESET}"
(
  cd "$ROOT"
  set -a; [[ -f .env ]] && source .env; set +a
  "$ROOT/.venv/bin/uvicorn" agentq.api.app:app \
    --host 0.0.0.0 --port 8000 --reload \
    --reload-dir agentq \
    --reload-include "*.py" 2>&1
) | backend_log &
BACKEND_PID=$!

sleep 1

# ── Start frontend ─────────────────────────────────────────────────────────────
log "Starting frontend on ${GREEN}http://localhost:3000${RESET}"
(
  cd "$FRONTEND_DIR"
  NODE_OPTIONS="--no-deprecation" npm run dev 2>&1
) | frontend_log &
FRONTEND_PID=$!

echo ""
echo -e "  ${BOLD}AgentQ is running${RESET}"
echo -e "  ${CYAN}Backend${RESET}   → http://localhost:8000"
echo -e "  ${CYAN}API Docs${RESET}  → http://localhost:8000/docs"
echo -e "  ${CYAN}OTLP${RESET}      → http://localhost:8000/v1/traces"
echo -e "  ${GREEN}Frontend${RESET}  → http://localhost:3000"
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop all"
echo ""

wait "$BACKEND_PID" "$FRONTEND_PID"
