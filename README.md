# AgentQ

AI Agent Safety, Observability & Guardrail Platform.

AgentQ sits between your AI agents and production. It ingests OpenTelemetry spans, runs 21 real-time guardrail rules across 5 threat classes, clusters similar agent behaviors with LLM-generated rubrics, and dispatches multi-channel alerts — all surfaced in a live dashboard.

---

## What AgentQ Does

| Capability | What it gives you |
|---|---|
| **Span Ingestion** | Drop-in OTel/MCP receiver — no SDK changes required |
| **21 Guardrail Rules** | Detects injection, scope creep, data exfiltration, behavioral anomalies, and integrity violations in real time |
| **Tool Execution Interceptor** | Pre-execution hook: observe guardrail hits before a tool fires, without blocking the agent |
| **Behavior Clustering** | Groups traces by composite embedding similarity; auto-generates LLM rubrics at 10 traces per cluster |
| **Multi-Channel Alerts** | Fires webhook, Slack, or email when a rule matches — with per-rule rate limiting and cooldown |
| **Live Dashboard** | SSE-driven trace feed, waterfall timeline, DAG viewer, episode replay, violation dashboard, service graph |
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

**Tool Execution Interceptor** — call `POST /api/intercept` before executing a tool to surface guardrail violations before any side effects occur. The endpoint always returns `allowed: true`; violations are in the `violations` array for you to inspect and act on.

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

## Connecting an Agent

Set two env vars before running your agent:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

Or use [openlit](https://github.com/openlit/openlit) (recommended):

```python
import openlit
openlit.init(otlp_endpoint="http://localhost:8000/v1/traces")
```

MCP agents — spans with any `mcp.*` attribute are automatically normalized to GenAI conventions.

**Pre-execution intercept:**

```python
import httpx

resp = httpx.post("http://localhost:8000/api/intercept", json={
    "trace_id": current_trace_id,
    "span_id": new_span_id,
    "tool_name": "send_email",
    "attributes": {"agentq.user_confirmed": False}
})
# always allowed=true; inspect violations before executing
violations = resp.json()["violations"]
```

---

## Dashboard Views

| View | What you can do |
|---|---|
| **Live Traces** | SSE-driven real-time feed; violation counter per trace |
| **Trace Detail** | DAG graph, waterfall timeline, episode replay scrubber, span inspector with OTel attributes |
| **Violations** | Filter by threat class and severity; stat cards for totals and criticals |
| **Behaviors** | Cluster list with rubric chips, trace count, member trace drill-down; "Generate Rubric" button |
| **Service Graph** | SVG force-directed graph; node size = span count, edge width = call frequency |
| **Alerts** | Rule CRUD (conditions, channels, rate limits), alert history table |
| **Docs** | Built-in API and configuration reference |

---

## Behaviors & Clustering

Every completed trace is embedded using a composite vector (0.4 × structural op-sequence + 0.6 × semantic prompt/completion, all-MiniLM-L6-v2, dim=384). It is then compared against all cluster centroids via cosine similarity.

- **New cluster** — created when similarity falls below `BEHAVIOR_SIMILARITY_THRESHOLD` (default 0.82)
- **Existing cluster** — centroid updated as a running average; trace assigned
- **Rubric generation** — auto-triggered when a cluster reaches 10 traces; calls Anthropic to produce 3–5 classification criteria and a short cluster name

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

## Environment Variables

```env
DATABASE_URL=sqlite+aiosqlite:///./agentq.db

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

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/traces` | Ingest OTLP/HTTP JSON spans |
| `POST` | `/api/intercept` | Pre-execution tool observation (always `allowed: true`) |
| `GET` | `/api/traces` | List spans (limit, offset, service filter) |
| `GET` | `/api/traces/{trace_id}` | All spans for a trace |
| `GET` | `/api/traces/{trace_id}/waterfall` | Depth-indented span tree |
| `GET` | `/api/graph` | Service graph (nodes + call edges) |
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
