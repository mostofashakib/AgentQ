# AgentQ

AI Agent Observability Control Plane.

AgentQ is a lightweight backend + dashboard that sits between your AI agents and production. It ingests OpenTelemetry spans, runs 21 guardrail rules in real time, clusters similar agent behaviors, and surfaces everything in a live dashboard with configurable multi-channel alerts.

---

## Architecture

```
┌─────────────────────────────┐            ┌──────────────────────────────────────┐
│     1. INGESTION & GATEWAY  │            │     2. REAL-TIME GUARDRAILS          │
│                             │            │                                      │
│ • OpenTelemetry GenAI       │            │ • Policy Verification Engine         │
│   Processor (OTLP/HTTP JSON)│            │ • Real-time PII & Leak Extractor     │
│ • Model Context Protocol    ├───────────>│ • Tool Execution Interceptor         │
│   Tracer (mcp.* attributes) │            │   (POST /api/intercept — observe     │
│ • Normalized State Capture  │            │    pre-execution tool violations)    │
└──────────────┬──────────────┘            │ • 21 rules across 5 threat classes   │
               │                           └──────────┬───────────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                       3. BEHAVIORS & ALERTS                                      │
│                                                                                  │
│ • Composite embedding (structural + semantic, all-MiniLM-L6-v2)                 │
│ • Nearest-neighbour trace clustering (configurable cosine threshold)             │
│ • LLM rubric generation (auto-triggered at 10 traces per cluster)                │
│ • Rule-based alert dispatch (webhook / Slack / SMTP email)                       │
└──────────────┬───────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          4. USER ANALYTICS UI                                    │
│                                                                                  │
│ • Live Traces feed (SSE)   • Waterfall Timeline (depth-indented span tree)      │
│ • Span Inspector           • Service Graph (SVG force-directed, live physics)   │
│ • Violation Dashboard      • Behaviors (cluster list, rubric chips, traces)     │
│ • Alerts (rule CRUD, history, multi-channel config)                              │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Capabilities

### Ingestion & Gateway
| Capability | Detail |
|---|---|
| OTel GenAI Processor | Parses OTLP/HTTP JSON spans with GenAI semantic conventions v1.41+ |
| MCP Tracer | Normalizes `mcp.*` span attributes to GenAI equivalents automatically |
| Normalized State Capture | `SpanRecord` Pydantic model — uniform schema for all downstream modules |

### Real-Time Guardrails (21 rules)

| Rule ID | Threat | Severity |
|---|---|---|
| `injection.user_content` | injection | high |
| `injection.system_prompt_override` | injection | critical |
| `injection.indirect_via_retrieval` | injection | high |
| `injection.role_confusion` | injection | medium |
| `scope.high_risk_tool` | scope | high |
| `scope.unsanctioned_tool` | scope | medium |
| `scope.excessive_tool_calls` | scope | medium |
| `scope.destructive_without_confirmation` | scope | critical |
| `exfiltration.url_in_output` | exfiltration | medium |
| `exfiltration.base64_in_output` | exfiltration | high |
| `exfiltration.sensitive_key_in_output` | exfiltration | critical |
| `exfiltration.pii_in_output` | exfiltration | critical |
| `exfiltration.outbound_http` | exfiltration | high |
| `behavioral.goal_drift` | behavioral | medium |
| `behavioral.infinite_loop` | behavioral | high |
| `behavioral.hallucinated_tool` | behavioral | high |
| `behavioral.token_explosion` | behavioral | medium |
| `integrity.time_inversion` | integrity | low |
| `integrity.missing_service_name` | integrity | low |
| `integrity.missing_gen_ai_attrs` | integrity | low |
| `integrity.empty_trace_id` | integrity | medium |

**Tool Execution Interceptor** — call `POST /api/intercept` before executing a tool to observe pre-execution violations in real time. The endpoint always returns `allowed=true`; violations are surfaced in the `violations` list for the caller to inspect.

### Tracing
| Feature | Detail |
|---|---|
| Waterfall Timeline | `GET /api/traces/{id}/waterfall` — depth-indented span tree, fully rendered in the dashboard |
| Service Graph | `GET /api/graph` — aggregated service nodes + call edges; SVG force-directed layout, no D3 |

### Behaviors
| Feature | Detail |
|---|---|
| Composite Embedding | 0.4 × structural (op:tool sequence) + 0.6 × semantic (prompt+completion), L2-normalized, dim=384 |
| Nearest-Neighbour Clustering | Cosine similarity vs all cluster centroids; configurable threshold (`BEHAVIOR_SIMILARITY_THRESHOLD`, default 0.82) |
| LLM Rubric Generation | Auto-triggered at 10 traces per cluster; generates 3–5 classification criteria and a short name via Anthropic |
| Dashboard | Accordion cluster list with rubric chips, trace count, "Generate Rubric" button, member trace drill-down |

### Alerts
| Feature | Detail |
|---|---|
| Rule-Based Matching | Conditions on `severity`, `threat_class`, `rule_id` (violations) or `cluster_id` (behaviors); empty = wildcard |
| Rate Limiting | Per-rule frequency limit (max fires/hour) + cooldown window (min minutes between fires) |
| Webhook Channel | HTTP POST with violation or behavior payload to any URL |
| Slack Channel | Block Kit message via Slack incoming webhook; severity emoji badges |
| Email Channel | Async SMTP via `aiosmtplib`; plain-text + HTML; configured via `SMTP_*` env vars |
| Dashboard | Two-tab UI: Rules CRUD (inline form, enable/disable toggle) + History table |

### User Analytics UI
| View | Detail |
|---|---|
| Live Traces | SSE-driven real-time feed with AnimatePresence, violation counter |
| DAG Trace Graph | SVG tree layout with cubic bezier edges, node colors, violation badges |
| Span Inspector | OTel attribute table + per-span violation detail |
| Episode Replay Timeline | Horizontal scrubber — spans highlight as playhead advances; Play/Pause/Reset |
| Waterfall Timeline | Depth-indented span tree derived from `parent_span_id` chain |
| Service Graph | SVG force-directed graph; node size = span count, edge thickness = call count |
| Violation Dashboard | Stat cards (total / critical / injections), threat + severity filters |
| Behaviors | Cluster list with rubric chips, trace count, member traces |
| Alerts | Rule CRUD with inline form + alert history table |

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 18+, [`uv`](https://github.com/astral-sh/uv)

```bash
git clone <repo-url> agentq
cd agentq
cp .env.example .env          # add ANTHROPIC_API_KEY (used for rubric generation)
./run.sh                      # starts backend :8000 + dashboard :3000
```

To stop: `./kill.sh`

---

## Demo Mode

Demo mode seeds the dashboard with realistic sample data on first launch — 6 agent traces, 10 guardrail violations across all threat classes, 3 behavior clusters with rubrics, and 2 alert rules. No real agent required.

```bash
./demo.sh           # start with demo data pre-loaded
./demo.sh --reset   # wipe demo data and re-seed (useful after schema changes)
```

**What's included in the demo dataset:**

| Trace | Service | Scenario | Violations |
|---|---|---|---|
| `demo-research-001` | research-agent | Web search + summarize | None |
| `demo-code-001` | code-assistant | File read + exec_command | `scope.high_risk_tool` |
| `demo-injection-001` | customer-chatbot | Jailbreak attempt | `injection.user_content` |
| `demo-exfil-001` | data-pipeline | API key in output | `exfiltration.sensitive_key_in_output` |
| `demo-pii-001` | support-bot | SSN + email in response | `exfiltration.pii_in_output` |
| `demo-loop-001` | automation-agent | Repeated delete_file calls | `behavioral.infinite_loop` + `scope.destructive_without_confirmation` |

The demo API endpoints (`POST /api/demo/seed`, `POST /api/demo/reset`) are only mounted when `DEMO_MODE=true`.

All demo data has trace IDs prefixed with `demo-` and can be cleared at any time with `POST /api/demo/reset`.

**OTLP endpoint:** `http://<your-agentq-host>:8000/v1/traces`  
**Dashboard:** `http://<your-agentq-host>:3000`  
**API docs:** `http://<your-agentq-host>:8000/docs`  
**Docs page:** `http://<your-agentq-host>:3000/docs`

---

## Connecting an Agent

Set two env vars before running your agent:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://<your-agentq-host>:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

Or use [openlit](https://github.com/openlit/openlit) (recommended):

```python
import openlit
openlit.init(otlp_endpoint="http://<your-agentq-host>:8000/v1/traces")
```

For MCP agents, spans with any `mcp.*` attribute are automatically normalized — no extra configuration needed.

**Pre-execution intercept (observability):**

```python
import httpx

resp = httpx.post("http://<your-agentq-host>:8000/api/intercept", json={
    "trace_id": current_trace_id,
    "span_id": new_span_id,
    "tool_name": "send_email",
    "attributes": {"agentq.user_confirmed": False}
})
# Always returns allowed=true; violations list contains any guardrail hits
violations = resp.json()["violations"]
```

---

## Environment Variables

```env
DATABASE_URL=sqlite+aiosqlite:///./agentq.db

# Demo mode — seeds realistic sample data on startup (use ./demo.sh to activate)
DEMO_MODE=false

JUDGE_MODEL=claude-sonnet-4-6     # used for LLM rubric generation
ANTHROPIC_API_KEY=

# Legacy webhook (always fires on violations)
WEBHOOK_ENABLED=false
WEBHOOK_URL=

# Behavior clustering
BEHAVIOR_SIMILARITY_THRESHOLD=0.82   # cosine similarity threshold (0–1)

# Slack alerts
SLACK_WEBHOOK_URL=

# Email alerts (aiosmtplib)
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
| `POST` | `/api/intercept` | Pre-execution tool check (allow/deny) |
| `GET` | `/api/traces` | List spans (limit, offset, service filter) |
| `GET` | `/api/traces/{trace_id}` | All spans for a specific trace |
| `GET` | `/api/traces/{trace_id}/waterfall` | Span tree for waterfall visualization |
| `GET` | `/api/graph` | Service graph (nodes + edges) |
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
| `GET` | `/api/stream` | SSE stream — real-time span and violation events |
| `GET` | `/health` | Health check |
| `POST` | `/api/demo/seed` | Seed demo data (only when `DEMO_MODE=true`) |
| `POST` | `/api/demo/reset` | Clear and re-seed demo data (only when `DEMO_MODE=true`) |

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, aiosqlite / asyncpg, Pydantic v2, sentence-transformers (all-MiniLM-L6-v2), aiosmtplib, httpx, sse-starlette, uv

**Frontend:** Next.js 16 App Router, Tailwind CSS v4, Framer Motion, Lucide icons

**Testing:** pytest-asyncio (AUTO mode), in-memory SQLite fixtures

---

Developed by [Mostofa Shakib](https://www.mostofashakib.com)
