#!/usr/bin/env bash
# AgentQ — Stop all running backend and frontend processes
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'

ok()  { echo -e "${GREEN}  ✓${RESET} $*"; }
err() { echo -e "${RED}  ✗${RESET} $*"; }
log() { echo -e "${BOLD}[agentq]${RESET} $*"; }

kill_port() {
  local port="$1" label="$2"
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    sleep 0.4
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
    ok "Stopped $label (port $port)"
  else
    echo -e "  — $label (port $port) not running"
  fi
}

log "Stopping AgentQ services..."
kill_port 8000 "FastAPI backend"
kill_port 3000 "Next.js frontend"
echo ""
echo -e "  ${CYAN}AgentQ stopped.${RESET}"
