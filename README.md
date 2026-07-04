# AgentQ

**AI Agent Observability**

Autonomous agents take actions in production with no one watching until something breaks. AgentQ sits between your agents and production, ingesting every action as an OpenTelemetry span so you can see — in real time — what they're actually doing.
It intercepts risky tool calls before they execute, clusters similar agent behaviors into reviewable patterns, and dispatches multi-channel alerts the moment something goes wrong — all surfaced in a live dashboard.

---

## What AgentQ Does

| Capability | What it gives you |
|---|---|
| **Authorized Span Ingestion** | OTel/MCP receiver restricted to agents explicitly connected by the user |
| **21 Guardrail Rules** | Detects injection, scope creep, data exfiltration, behavioral anomalies, and integrity violations in real time |
| **Tool Execution Interceptor** | Pre-execution policy, circuit-breaker, and human-approval enforcement |
| **Behavior Clustering** | Groups traces by composite embedding similarity; auto-generates LLM rubrics at 10 traces per cluster |
| **Multi-Channel Alerts** | Fires webhook, Slack, or email when a rule matches — with per-rule rate limiting and cooldown |
| **Agent Run Monitoring** | Tracks latency, tokens, cost, errors, tool outcomes, retries, evaluations, and terminal status |
| **Live Dashboard** | SSE-driven trace feed, run health, waterfall timeline, DAG viewer, episode replay, violations, and service graph |
| **Demo Mode** | One-command seed of realistic traces, violations, clusters, and alert rules — no real agent required |

---

## Architecture

```
┌─────────────────────────────┐            ┌──────────────────────────────────────┐
│     1. INGESTION & GATEWAY  │            │     2. REAL-TIME GUARDRAILS          │
│                             │            │                                      │
│ • OpenTelemetry GenAI       │            │ • 21 rules across 5 threat classes   │
│   Processor (OTLP/HTTP JSON)│            │ • Pattern Matching Engine            │
│ • MCP Tracer (mcp.* attrs   │            │ • Tool Execution Interceptor         │
│   normalized automatically) ├───────────>│   (POST /api/intercept — observe     │
│ • Normalized SpanRecord     │            │    pre-execution violations)         │
│   Pydantic model            │            │ • Async worker queue (no hot-path    │
└──────────────┬──────────────┘            │    latency on ingest)                │
               │                           └──────────┬───────────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       3. BEHAVIORS & ALERTS                                      │
│                                                                                  │
│ • Composite embedding (0.4 × structural + 0.6 × semantic, dim=384)              │
│ • Nearest-neighbour trace clustering (cosine threshold, default 0.82)           │
│ • LLM rubric generation via Anthropic (auto-triggered at 10 traces/cluster)     │
│ • Rule-based alert dispatch — webhook / Slack / SMTP email                      │
│ • Per-rule frequency cap + cooldown window                                       │
└──────────────┬───────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          4. DASHBOARD                                            │
│                                                                                  │
│ • Live Traces (SSE)         • Waterfall Timeline      • Episode Replay           │
│ • DAG Trace Graph           • Service Graph (SVG)     • Span Inspector           │
│ • Violation Dashboard       • Behaviors & Rubrics     • Alert Rules + History    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Guardrail Rules (21)

AgentQ ships 21 rules across 5 threat classes, evaluated on every ingested span and on every `POST /api/intercept` call.

| Rule ID | Threat | Severity | What it detects |
|---|---|---|---|
| `injection.user_content` | injection | high | Prompt injection patterns in user messages |
| `injection.system_prompt_override` | injection | critical | Attempts to override system instructions |
| `injection.indirect_via_retrieval` | injection | high | Injected content arriving via retrieved context |
| `injection.role_confusion` | injection | medium | Agent confusing its role or identity |
| `scope.high_risk_tool` | scope | high | Use of dangerous tools (shell exec, file write, etc.) |
| `scope.unsanctioned_tool` | scope | medium | Tool call not in the agent's allowed set |
| `scope.excessive_tool_calls` | scope | medium | Abnormally high tool call volume in one trace |
| `scope.destructive_without_confirmation` | scope | critical | Destructive action taken without user confirmation |
| `exfiltration.url_in_output` | exfiltration | medium | Suspicious URL embedded in agent output |
| `exfiltration.base64_in_output` | exfiltration | high | Base64-encoded data in output |
| `exfiltration.sensitive_key_in_output` | exfiltration | critical | API keys or secrets in agent output |
| `exfiltration.pii_in_output` | exfiltration | critical | PII (SSN, email, credit card) in agent output |
| `exfiltration.outbound_http` | exfiltration | high | Unexpected outbound HTTP call from agent |
| `behavioral.goal_drift` | behavioral | medium | Agent pursuing goals outside its original intent |
| `behavioral.infinite_loop` | behavioral | high | Repeated identical tool calls with no progress |
| `behavioral.hallucinated_tool` | behavioral | high | Agent referencing a tool that doesn't exist |
| `behavioral.token_explosion` | behavioral | medium | Abnormally large token usage |
| `integrity.time_inversion` | integrity | low | Span end time before start time |
| `integrity.missing_service_name` | integrity | low | `service.name` resource attribute absent |
| `integrity.missing_gen_ai_attrs` | integrity | low | CLIENT span missing `gen_ai.system` / operation |
| `integrity.empty_trace_id` | integrity | medium | Empty or missing `trace_id` |

**Tool Execution Interceptor** — call `POST /api/intercept` before executing a tool. Circuit breakers, selected security violations, and pending or rejected approvals return `allowed: false`; other findings remain available in the `violations` array.

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 18+, [`uv`](https://github.com/astral-sh/uv)

```bash
git clone <repo-url> agentq
cd agentq
cp .env.example .env          # set ANTHROPIC_API_KEY for LLM rubric generation
./run.sh                      # starts backend :8000 + dashboard :3000
```

To stop: `./kill.sh`

---

## Demo Mode

Start with a fully seeded dataset — 6 agent traces, 10 guardrail violations across all threat classes, 3 behavior clusters with rubrics, and 2 alert rules. No real agent required.

```bash
./demo.sh           # start with demo data pre-loaded
./demo.sh --reset   # wipe demo data and re-seed
```

**Demo dataset:**

| Trace | Service | Scenario | Violations |
|---|---|---|---|
| `demo-research-001` | research-agent | Web search + summarize | None |
| `demo-code-001` | code-assistant | File read + exec_command | `scope.high_risk_tool` |
| `demo-injection-001` | customer-chatbot | Jailbreak attempt | `injection.user_content` |
| `demo-exfil-001` | data-pipeline | API key in output | `exfiltration.sensitive_key_in_output` |
| `demo-pii-001` | support-bot | SSN + email in response | `exfiltration.pii_in_output` |
| `demo-loop-001` | automation-agent | Repeated delete_file calls | `behavioral.infinite_loop` + `scope.destructive_without_confirmation` |

Demo endpoints (`POST /api/demo/seed`, `POST /api/demo/reset`) are only mounted when `DEMO_MODE=true`.

---

## Deploying with Docker

```bash
git clone <repo-url> agentq
cd agentq
cp .env.example .env
```

Edit `.env` and set:
- `ADMIN_API_KEY`, `VIEWER_API_KEY`, `INGEST_API_KEY` — generate each with `openssl rand -hex 32`. Required: the container defaults to `ENVIRONMENT=production`, which rejects all requests until these are set.
- `NEXT_PUBLIC_API_KEY` — an API key used by the dashboard. It is embedded in the browser build, so only use this setup for a trusted, operator-only deployment. Put a server-side authentication proxy in front of AgentQ before exposing the dashboard publicly.
- `ANTHROPIC_API_KEY` (or configure a provider later via the Settings page) — optional, entirely your own key and cost. Rubric generation is skipped without one; nothing else is affected.

```bash
docker compose up --build
```

Backend: `http://localhost:8000` (`/health`, `/docs`). Dashboard: `http://localhost:3000`. The SQLite database persists in a named Docker volume across restarts.

To run without auth (e.g. testing on a private LAN only), override `ENVIRONMENT: local` for the `backend` service in `docker-compose.yml`.

---

## Connecting an Agent

AgentQ speaks **AOP/1** — the AgentQ Observability Protocol: OTLP/HTTP spans (JSON or protobuf), `service.name` as agent identity, OTel GenAI semantic conventions as the action schema, automatic MCP normalization, and a pre-execution intercept hook. First authorize each service on **Connect Agent**. Behavior analysis is always enabled; trace visibility can be selected separately. Multiple connected agents can be observed together. AgentQ shows each generated connection token once and rejects telemetry whose service name and token do not match.

Set two env vars before running your agent:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json   # or http/protobuf — both accepted
export OTEL_EXPORTER_OTLP_HEADERS="X-AgentQ-Agent-Token=<connection-token>"
```

Or use [openlit](https://github.com/openlit/openlit) (recommended):

```python
import openlit
openlit.init(otlp_endpoint="http://localhost:8000/v1/traces")
```

**OpenClaw:**

```bash
openclaw plugins install clawhub:@openclaw/diagnostics-otel
openclaw plugins enable diagnostics-otel
```

```json5
{
  plugins: { entries: { "diagnostics-otel": { enabled: true } } },
  diagnostics: {
    otel: {
      enabled: true,
      tracesEndpoint: "http://localhost:8000/v1/traces",
      protocol: "http/protobuf",
      serviceName: "openclaw-prod",
      traces: true,
      metrics: false,
      logs: false,
      captureContent: {
        enabled: true,
        inputMessages: true,
        outputMessages: true,
        toolInputs: true,
        toolOutputs: true,
      },
    },
  },
}
```

> `captureContent` defaults to all-`false` in OpenClaw for privacy — spans carry no prompt/response/tool text unless you opt in above. Without it, AgentQ's content-scanning guardrails (injection, PII, exfiltration) receive spans but find nothing to scan.

MCP agents — spans with any `mcp.*` attribute are automatically normalized to GenAI conventions.

**Pre-execution intercept:**

```python
import httpx

resp = httpx.post("http://localhost:8000/api/intercept", json={
    "trace_id": current_trace_id,
    "span_id": new_span_id,
    "tool_name": "send_email",
    "attributes": {"agentq.user_confirmed": False}
}, headers={"X-AgentQ-Agent-Token": connection_token})
# Execute only when allowed=true. Pending approvals and policy blocks return allowed=false.
decision = resp.json()
```

**MCP server:** AgentQ is itself reachable as an MCP server at `http://localhost:8000/mcp`, exposing 3 tools for any MCP client (Claude Desktop, a custom agent, etc.):

| Tool | What it does |
|---|---|
| `report_action(agent_name, tool_name, connection_token, input, output)` | Logs an authorized completed action through the same monitoring pipeline as OTLP |
| `check_action(agent_name, tool_name, attributes)` | Advisory guardrail check that returns detected violations; use `POST /api/intercept` when enforcement is required |
| `get_violations(agent_name, connection_token, limit)` | Recent violations for an authorized agent |

**Simple report API:** for agents that don't want to touch OTel at all:

```bash
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -H "X-AgentQ-Agent-Token: <connection-token>" \
  -d '{"agent_name": "my-agent", "tool_name": "send_email", "input": "to: a@b.com", "output": "sent"}'
```

---

## Dashboard Views

| View | What you can do |
|---|---|
| **Connect Agent** | Wizard: pick a framework (OpenClaw, generic OTel, MCP, cURL), name your agent, get a ready-to-paste config snippet, watch connection status flip live |
| **Live Traces** | SSE-driven real-time feed; violation counter per trace |
| **Trace Detail** | DAG graph, waterfall timeline, episode replay scrubber, span inspector with OTel attributes |
| **Violations** | Filter by threat class and severity; stat cards for totals and criticals |
| **Behaviors** | Cluster list with rubric chips, trace count, member trace drill-down; "Generate Rubric" button |
| **Service Graph** | SVG force-directed graph; node size = span count, edge width = call frequency |
| **Alerts** | Rule CRUD with structured condition/channel pickers, rate limits, alert history table |
| **Settings** | Tune guardrail thresholds at runtime, set a default alert channel, view MCP/API connection info |
| **Docs** | Built-in API and configuration reference |

---

## Behaviors & Clustering

Every completed trace is embedded using a composite vector (0.4 × structural op-sequence + 0.6 × semantic prompt/completion, all-MiniLM-L6-v2, dim=384). It is then compared against all cluster centroids via cosine similarity.

- **New cluster** — created when similarity falls below `BEHAVIOR_SIMILARITY_THRESHOLD` (default 0.82)
- **Existing cluster** — centroid updated as a running average; trace assigned
- **Rubric generation** — auto-triggered when a cluster reaches 10 traces; calls your configured LLM provider to produce 3–5 classification criteria and a short cluster name. Bring-your-own-key: set a provider and API key via the Settings page, or `ANTHROPIC_API_KEY`/`JUDGE_MODEL` in `.env`. AgentQ never holds or uses its own LLM key — without one configured, cluster naming is skipped with a visible status message; clustering itself (which doesn't require an LLM call) is unaffected.
- **Provider choice** — Anthropic and OpenAI are supported directly. OpenRouter and Hugging Face use their OpenAI-compatible endpoints. Local Ollama, LM Studio, vLLM, and similar servers can be configured with a custom OpenAI-compatible base URL.

---

## Alerts

Rules match on `severity`, `threat_class`, or `rule_id` for violations, and on `cluster_id` for behavior events. Empty conditions act as a wildcard.

| Channel | How to configure |
|---|---|
| **Webhook** | Any HTTP POST endpoint; `WEBHOOK_URL` + `WEBHOOK_ENABLED=true` |
| **Slack** | Incoming webhook with Block Kit formatting; `SLACK_WEBHOOK_URL` |
| **Email** | Async SMTP via aiosmtplib; `SMTP_*` env vars |

Per-rule controls: `frequency_limit` (max fires/hour) and `cooldown_minutes` (min gap between fires).

---

## Agent Monitoring

Every ingested trace produces an `AgentRun` record keyed by `trace_id` and a stable `agent_run_id`. A producer can attach `session.id` or `agentq.session_id`. Parent span IDs remain unchanged, including across queued workers, so the waterfall reconstructs the original execution timeline.

Run aggregation records total and per-span latency, input/output tokens, model and tool counts, failures, retries, estimated provider cost, agent type, environment, and terminal status. `/api/monitoring/metrics` exports aggregate run volume, success/error rates, average and p95 latency, tokens, cost, tool success, evaluations, and safety events. The **Run Health** dashboard displays these signals.

Stored span attributes are sanitized inside the application process. Prompt and output content is omitted by default. Enabling raw content requires an explicit flag and is still disabled in production; passwords, credentials, tokens, cookies, email addresses, phone numbers, payment data, and government IDs are recursively redacted. Hidden reasoning is never required or stored.

The pre-execution interceptor enforces configurable limits for steps, model calls, tool calls, retries, runtime, tokens, cost, and repeated tool calls. Unauthorized calls are blocked. Configured side-effect tools create a pending approval request; retry the same intercept after an authorized reviewer approves it through `/api/approvals/{id}/decision`.

Five deterministic quality results are attached to runs: faithfulness, relevancy, completeness, hallucination risk, and policy adherence. Missing producer signals return `warn` instead of inventing a score. Anomaly records flag latency, cost, output size, repeated failures, and retries. Monitoring records are retained for `TELEMETRY_RETENTION_DAYS` and pruned on startup.

To debug a failed run, open its trace in the dashboard or call `GET /api/monitoring/runs/{trace_id}`. The response combines run metrics, evaluation reasons, anomalies, security events, circuit-breaker reasons, and approval decisions. Then inspect `GET /api/traces/{trace_id}/waterfall` for the exact failing child span.

## Environment Variables

```env
DATABASE_URL=sqlite+aiosqlite:///./agentq.db
ENVIRONMENT=local
TRACING_ENABLED=true
TRACE_SAMPLING_RATE=1.0
RAW_PROMPT_LOGGING_ENABLED=false
RAW_OUTPUT_LOGGING_ENABLED=false
STRUCTURED_LOGGING_ENABLED=true
TELEMETRY_RETENTION_DAYS=30

# API security — fail-closed by default: required whenever ENVIRONMENT is
# not "local" (the Docker deployment sets ENVIRONMENT=production). With auth
# required and no keys configured, every request is rejected — set at least
# one of these. This gate covers dashboard APIs, telemetry ingestion, the
# /mcp mount, and report/intercept endpoints. /health remains public.
# API_AUTH_ENABLED=true  # optional locally; defaults to true outside local
VIEWER_API_KEY=
ADMIN_API_KEY=
INGEST_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Rate limiting — in-memory, per-process, keyed by API key (or client IP
# when auth is disabled). Single self-hosted instance only; does not
# synchronize across multiple replicas.
RATE_LIMIT_PER_MINUTE=120

# Circuit breakers and anomaly thresholds
MAX_AGENT_STEPS=50
MAX_MODEL_CALLS=20
MAX_TOOL_CALLS=30
MAX_RETRIES=5
MAX_RUNTIME_SECONDS=300
MAX_TOKENS_PER_RUN=100000
MAX_COST_USD_PER_RUN=10
MAX_SIMILAR_TOOL_CALLS=5
UNUSUAL_COST_USD=5
UNUSUAL_LATENCY_MS=30000
UNUSUAL_OUTPUT_TOKENS=8000
APPROVAL_REQUIRED_TOOLS=send_email,delete,delete_file,drop_table,update_production,make_purchase,publish,change_permissions,privileged_exec

# Demo mode — seeds realistic sample data on startup
DEMO_MODE=false

# LLM rubric generation (Behaviors)
JUDGE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=

# Behavior clustering
BEHAVIOR_SIMILARITY_THRESHOLD=0.82

# Legacy webhook (fires on all violations)
WEBHOOK_ENABLED=false
WEBHOOK_URL=

# Slack alerts
SLACK_WEBHOOK_URL=

# Email alerts
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TO=
```

API clients send credentials in `X-AgentQ-API-Key`. In staging and production,
use distinct random keys for read-only access, administrative actions, and
telemetry ingestion. If authentication is enabled without a matching key, the
API denies the request. Never expose these keys in browser-delivered code; use
an authenticated backend or trusted proxy for the dashboard.

Development standards, including the required red-green-refactor workflow, are
documented in [`ENGINEERING.md`](ENGINEERING.md).

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/traces` | Ingest OTLP/HTTP JSON spans |
| `POST` | `/api/intercept` | Enforce pre-execution policy, limits, and approvals |
| `GET` | `/api/monitoring/runs` | Filterable run records |
| `GET` | `/api/monitoring/runs/{trace_id}` | Run metrics, evaluations, and safety events |
| `DELETE` | `/api/monitoring/runs/{trace_id}` | Delete all retained monitoring data for a trace |
| `GET` | `/api/monitoring/metrics` | Aggregate health, latency, cost, and quality metrics |
| `GET` | `/api/monitoring/events` | Security, anomaly, approval, and circuit-breaker events |
| `GET` | `/api/approvals` | List approval requests |
| `POST` | `/api/approvals/{id}/decision` | Approve or reject a high-risk action |
| `GET` | `/api/traces` | List spans (limit, offset, service filter) |
| `GET` | `/api/traces/{trace_id}` | All spans for a trace |
| `GET` | `/api/traces/{trace_id}/waterfall` | Depth-indented span tree |
| `GET` | `/api/graph` | Service graph (nodes + call edges) |
| `GET` | `/api/agents` | List connected agents (span/violation counts, first/last seen) |
| `POST` | `/api/agents` | Explicitly authorize an agent; behavior analysis is always enabled |
| `DELETE` | `/api/agents/{service_name}` | Disconnect an agent and reject future telemetry |
| `POST` | `/api/report` | Simple non-OTel action reporting (`agent_name`, `tool_name`, `input`, `output`) |
| `GET` | `/api/settings` | Current guardrail thresholds and default alert channel |
| `PUT` | `/api/settings` | Update any subset of guardrail thresholds or the default alert channel |
| — | `/mcp` | AgentQ's MCP server endpoint (`report_action`, `check_action`, `get_violations` tools) |
| `GET` | `/api/violations` | List violations (threat_class, severity, trace_id filters) |
| `GET` | `/api/behaviors` | List behavior clusters |
| `GET` | `/api/behaviors/{id}` | Cluster detail + member trace IDs |
| `POST` | `/api/behaviors/{id}/rubric` | Trigger LLM rubric generation |
| `GET` | `/api/behaviors/{id}/traces` | Paginated assigned traces |
| `GET` | `/api/alerts/rules` | List alert rules |
| `POST` | `/api/alerts/rules` | Create alert rule |
| `PUT` | `/api/alerts/rules/{id}` | Update alert rule |
| `DELETE` | `/api/alerts/rules/{id}` | Delete alert rule |
| `GET` | `/api/alerts/history` | Paginated alert history |
| `GET` | `/api/stream` | SSE — real-time span and violation events |
| `GET` | `/health` | Health check |
| `POST` | `/api/demo/seed` | Seed demo data (`DEMO_MODE=true` only) |
| `POST` | `/api/demo/reset` | Clear and re-seed demo data (`DEMO_MODE=true` only) |

Full interactive Swagger UI: `http://localhost:8000/docs`

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, aiosqlite / asyncpg, Pydantic v2, sentence-transformers (all-MiniLM-L6-v2), aiosmtplib, httpx, sse-starlette, uv

**Frontend:** Next.js 16 App Router, Tailwind CSS v4, Framer Motion, Lucide icons

**Testing:** pytest-asyncio (AUTO mode), in-memory SQLite fixtures

---

Developed by [Mostofa Shakib](https://www.mostofashakib.com)
