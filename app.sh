#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT/frontend"
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'

BACKEND_PID=""
FRONTEND_PID=""
E2E_BACKEND_PID=""
OLLAMA_PID=""
E2E_MODEL=""
E2E_TMP_DIR=""

log() { echo -e "${BOLD}[agentq]${RESET} $*"; }
ok() { echo -e "${GREEN}  ✓${RESET} $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET} $*"; }
fail() { echo -e "${RED}  ✗${RESET} $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: ./app.sh <mode> [options]

Modes:
  run                         Start the backend and frontend
  kill                        Stop services on ports 8000 and 3000
  demo [--reset]              Start demo mode; optionally reset demo data
  test                        Run backend tests and the frontend production build
  agent <integration> <name> <token> <prompt>
                              Run the local Gemma test agent
  e2e [integration] [model]   Run real Gemma tests; defaults to all integrations
  help                        Show this help

Integrations: openclaw, otel, otel-protobuf, mcp, curl
EOF
}

kill_port() {
  local port="$1" label="$2" pids
  pids="$(lsof -ti:"$port" 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    echo "  — $label (port $port) not running"
    return
  fi
  echo "$pids" | xargs kill -TERM 2>/dev/null || true
  sleep 0.4
  pids="$(lsof -ti:"$port" 2>/dev/null || true)"
  [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
  ok "Stopped $label (port $port)"
}

load_environment() {
  cd "$ROOT"
  if [[ -f .env ]]; then
    set -a
    source .env
    set +a
  fi
}

require_runtime() {
  [[ -x "$ROOT/.venv/bin/uvicorn" ]] || fail "Python environment missing. Run: uv sync --extra dev"
  [[ -d "$FRONTEND_DIR/node_modules" ]] || fail "Frontend dependencies missing. Run: npm --prefix frontend install"
}

cleanup_services() {
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}

cleanup_e2e() {
  if [[ -n "$E2E_BACKEND_PID" ]]; then
    kill "$E2E_BACKEND_PID" 2>/dev/null || true
    wait "$E2E_BACKEND_PID" 2>/dev/null || true
  fi
  [[ -n "$OLLAMA_PID" ]] && kill "$OLLAMA_PID" 2>/dev/null || true
  if [[ -n "$E2E_TMP_DIR" && -d "$E2E_TMP_DIR" ]]; then
    rm -rf "$E2E_TMP_DIR"
    ok "Removed isolated test database, logs, and telemetry"
  fi
}

start_stack() {
  local demo_mode="$1"
  require_runtime
  load_environment
  kill_port 8000 "backend"
  kill_port 3000 "frontend"

  trap cleanup_services INT TERM EXIT
  log "Starting backend on http://localhost:8000"
  (
    cd "$ROOT"
    DEMO_MODE="$demo_mode" "$ROOT/.venv/bin/uvicorn" agentq.api.app:app \
      --host 0.0.0.0 --port 8000 --reload --reload-dir agentq --reload-include "*.py"
  ) 2>&1 | while IFS= read -r line; do echo -e "${CYAN}[backend]${RESET} $line"; done &
  BACKEND_PID=$!

  log "Starting frontend on http://localhost:3000"
  (
    cd "$FRONTEND_DIR"
    NODE_OPTIONS="--no-deprecation" npm run dev
  ) 2>&1 | while IFS= read -r line; do echo -e "${GREEN}[frontend]${RESET} $line"; done &
  FRONTEND_PID=$!

  echo -e "\n  ${BOLD}AgentQ is running${RESET}"
  echo "  Backend  → http://localhost:8000"
  echo "  Frontend → http://localhost:3000"
  echo "  Stop     → ./app.sh kill"
  wait "$BACKEND_PID" "$FRONTEND_PID"
}

reset_demo() {
  load_environment
  DEMO_MODE=true uv run python -c '
import asyncio
from agentq.db.engine import create_tables, async_session
from agentq.demo.seed import clear_demo, seed_demo

async def main():
    await create_tables()
    async with async_session() as session:
        await clear_demo(session)
    async with async_session() as session:
        print(await seed_demo(session))

asyncio.run(main())
'
  ok "Demo data reset"
}

run_tests() {
  cd "$ROOT"
  uv run pytest -q
  npm --prefix frontend run build
}

run_agent() {
  [[ $# -ge 4 ]] || fail "Usage: ./app.sh agent <integration> <service-name> <token> <prompt>"
  cd "$ROOT"
  uv run python -m examples.test_agents.gemma_agent \
    --integration "$1" --service-name "$2" --token "$3" "${4}"
}

wait_for_backend() {
  local health_url="$1"
  for _ in {1..30}; do
    curl -fsS --max-time 1 "$health_url" >/dev/null 2>&1 && return
    sleep 0.25
  done
  fail "AgentQ backend did not become healthy"
}

ensure_ollama() {
  local model="$1" ollama_url="$2"
  if ! command -v ollama >/dev/null 2>&1; then
    warn "Ollama is missing; installing it for the live Gemma tests"
    case "$(uname -s)" in
      Darwin)
        command -v brew >/dev/null 2>&1 || fail "Homebrew is required to install Ollama on macOS"
        brew install ollama
        ;;
      Linux)
        local installer="${TMPDIR:-/tmp}/ollama-install.sh"
        curl -fsSL https://ollama.com/install.sh -o "$installer"
        bash "$installer"
        ;;
      *) fail "Automatic Ollama installation is unsupported on $(uname -s)" ;;
    esac
  fi

  if ! curl -fsS --max-time 2 "$ollama_url/api/tags" >/dev/null 2>&1; then
    log "Starting Ollama for the live tests"
    ollama serve >"${TMPDIR:-/tmp}/agentq-ollama.log" 2>&1 &
    OLLAMA_PID=$!
    for _ in {1..60}; do
      curl -fsS --max-time 1 "$ollama_url/api/tags" >/dev/null 2>&1 && break
      sleep 0.5
    done
  fi
  curl -fsS --max-time 2 "$ollama_url/api/tags" >/dev/null || fail "Ollama is not reachable at $ollama_url"

  if [[ "$model" == "auto" ]]; then
    local tags
    tags="$(curl -fsS "$ollama_url/api/tags")"
    model="$(uv run python -c 'import json,sys; names=[m["name"] for m in json.load(sys.stdin).get("models", []) if m["name"].lower().startswith("gemma")]; print(names[0] if names else "gemma3:1b")' <<<"$tags")"
  fi

  if ! ollama show "$model" >/dev/null 2>&1; then
    warn "Gemma model $model is missing; pulling it for the live tests"
    ollama pull "$model"
  fi
  E2E_MODEL="$model"
}

run_e2e_profile() {
  local integration="$1" model="$2" prompt="$3" expected_tool="$4"
  local agentq_url="$5" ollama_url="$6"
  local service_name="gemma-e2e-${integration//[^a-zA-Z0-9._-]/-}"
  local api_key_header=()
  if [[ -n "${ADMIN_API_KEY:-}" ]]; then
    api_key_header=(-H "X-AgentQ-API-Key: $ADMIN_API_KEY")
  fi

  local registration token agents status
  registration="$(curl -fsS -X POST "$agentq_url/api/agents" \
    "${api_key_header[@]}" -H "Content-Type: application/json" \
    -d "{\"service_name\":\"$service_name\",\"integration_type\":\"${integration/otel-protobuf/otel}\"}")"
  token="$(uv run python -c 'import json,sys; print(json.load(sys.stdin)["connection_token"])' <<<"$registration")"

  log "Running $model through the $integration integration"
  uv run python -m examples.test_agents.gemma_agent \
    --agentq-url "$agentq_url" --ollama-url "$ollama_url" --model "$model" \
    --integration "$integration" --service-name "$service_name" --token "$token" \
    --required-tool "$expected_tool" \
    "$prompt"

  agents="$(curl -fsS "$agentq_url/api/agents" "${api_key_header[@]}")"
  status="$(uv run python -c 'import json,sys; data=json.load(sys.stdin); name=sys.argv[1]; print(next(a["connection_status"] for a in data if a["service_name"] == name))' "$service_name" <<<"$agents")"
  [[ "$status" == "connected" ]] || fail "Telemetry verification failed; status is $status"
  local traces tool_seen
  traces="$(curl -fsS "$agentq_url/api/traces?service=$service_name" "${api_key_header[@]}")"
  tool_seen="$(uv run python -c 'import json,sys; data=json.load(sys.stdin); expected=sys.argv[1]; print(any(span.get("gen_ai_tool_name") == expected for span in data))' "$expected_tool" <<<"$traces")"
  [[ "$tool_seen" == "True" ]] || fail "Gemma did not execute the required $expected_tool tool"
  ok "End-to-end verified: Gemma → $integration → $expected_tool → AOP/1 → AgentQ ($status)"
}

run_e2e() {
  local integration="${1:-all}" model="${2:-${AGENTQ_TEST_MODEL:-auto}}"
  local ollama_url="${OLLAMA_URL:-http://localhost:11434}"
  local e2e_port agentq_url

  load_environment
  trap cleanup_e2e EXIT
  E2E_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agentq-e2e.XXXXXX")"
  e2e_port="$(uv run python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
  agentq_url="http://127.0.0.1:$e2e_port"
  ensure_ollama "$model" "$ollama_url"
  model="$E2E_MODEL"
  require_runtime
  log "Starting an isolated temporary backend for the end-to-end test"
  DATABASE_URL="sqlite+aiosqlite:///$E2E_TMP_DIR/agentq.db" \
    DEMO_MODE=false ENVIRONMENT=local \
    "$ROOT/.venv/bin/uvicorn" agentq.api.app:app --host 127.0.0.1 --port "$e2e_port" \
    >"$E2E_TMP_DIR/backend.log" 2>&1 &
  E2E_BACKEND_PID=$!
  wait_for_backend "$agentq_url/health"

  uv run python -m examples.test_agents.negative_checks --agentq-url "$agentq_url"

  if [[ "$integration" == "all" ]]; then
    run_e2e_profile openclaw "$model" "You must use the calculator tool to calculate 17 * 23, then return the result." calculate "$agentq_url" "$ollama_url"
    run_e2e_profile otel "$model" "You must use web_search to search for OpenTelemetry, then summarize the result." web_search "$agentq_url" "$ollama_url"
    run_e2e_profile otel-protobuf "$model" "You must use current_time to get the current UTC time, then return it." current_time "$agentq_url" "$ollama_url"
    run_e2e_profile mcp "$model" "You must use the calculator tool to calculate 144 / 12, then return the result." calculate "$agentq_url" "$ollama_url"
    run_e2e_profile curl "$model" "You must use current_time to get the current UTC time, then return it." current_time "$agentq_url" "$ollama_url"
  else
    run_e2e_profile "$integration" "$model" "You must use the calculator tool to calculate 17 * 23, then return the result." calculate "$agentq_url" "$ollama_url"
  fi
}

mode="${1:-help}"
shift || true
case "$mode" in
  run) start_stack false ;;
  kill) kill_port 8000 "backend"; kill_port 3000 "frontend" ;;
  demo)
    [[ "${1:-}" == "--reset" ]] && reset_demo
    start_stack true
    ;;
  test) run_tests ;;
  agent) run_agent "$@" ;;
  e2e) run_e2e "$@" ;;
  help|-h|--help) usage ;;
  *) echo "Unknown mode: $mode" >&2; usage >&2; exit 2 ;;
esac
