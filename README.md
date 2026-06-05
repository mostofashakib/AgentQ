# AgentQ

AI Agent Reliability, Evaluation & Observability Control Plane.

AgentQ is a lightweight backend + dashboard that sits between your AI agents and production. It ingests OpenTelemetry spans, runs 21 guardrail rules in real time, scores every trace automatically, and surfaces everything in a live dashboard.

---

## Architecture

```
┌─────────────────────────────┐            ┌──────────────────────────────────────┐
│     1. INGESTION & GATEWAY  │            │     2. REAL-TIME GUARDRAILS          │
│                             │            │                                      │
│ • OpenTelemetry GenAI       │            │ • Policy Verification Engine         │
│   Processor (OTLP/HTTP JSON)│            │ • Real-time PII & Leak Extractor     │
│ • Model Context Protocol    ├───────────>│ • Tool Execution Interceptor         │
│   Tracer (mcp.* attributes) │            │   (POST /api/intercept)              │
│ • Normalized State Capture  │            │ • 21 rules across 5 threat classes   │
└──────────────┬──────────────┘            └──────────┬───────────────────────────┘
               │                                      │
               ▼                                      ▼
┌─────────────────────────────┐            ┌──────────────────────────────────────┐
│    3. DYNAMIC EVAL ENGINE   │            │     4. ALERTS & WEBHOOKS             │
│                             │            │                                      │
│ • Tiered Reward Engine      │            │ • HTTP POST on every violation       │
│ • N-Gram Semantic Evaluator │            │ • Configurable external endpoint     │
│   (ROUGE-1 F1)              │            │ • Payload: rule_id, severity,        │
│ • Asynchronous LLM-as-Judge │            │   blocked, evidence, trace_id        │
│   (Anthropic/OpenAI/Ollama/ │            └──────────────────────────────────────┘
│    OpenRouter)              │
└──────────────┬──────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          5. USER ANALYTICS UI                                    │
│                                                                                  │
│ • Live Traces feed (SSE)   • DAG Trace Graph (SVG, bezier edges, click-select)  │
│ • Span Inspector           • Episode Replay Timeline (scrubber, Play/Pause)     │
│ • Violation Dashboard      • Eval Score Board (gauges + judge rationale)        │
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

**Tool Execution Interceptor** — call `POST /api/intercept` before executing a tool to get a real-time allow/deny decision before any side effects occur.

### Dynamic Eval Engine
| Metric | How |
|---|---|
| `task_completion` | ROUGE-1 F1 between actual and expected output |
| `tool_accuracy` | Successful tool calls / total tool calls |
| `efficiency` | `optimal_steps / actual_steps`, capped at 1.0 |
| `judge_score` | LLM-as-judge (0–1) with rationale; providers: Anthropic, OpenAI, Ollama, OpenRouter |

### Alerts & Webhooks
| Feature | Detail |
|---|---|
| Violation Webhook | HTTP POST fired on every detected violation — configurable endpoint via `WEBHOOK_URL` |
| Payload | Includes `rule_id`, `threat_class`, `severity`, `blocked`, `description`, `trace_id`, `span_id`, `evidence` |
| Enable | Set `WEBHOOK_ENABLED=true` and `WEBHOOK_URL=<your-endpoint>` in `.env` |

### User Analytics UI
| View | Detail |
|---|---|
| Live Traces | SSE-driven real-time feed with AnimatePresence, violation counter |
| DAG Trace Graph | SVG tree layout with cubic bezier edges, node colors, violation badges |
| Span Inspector | OTel attribute table + per-span violation detail with BLOCKED indicator |
| Episode Replay Timeline | Horizontal scrubber — spans highlight as playhead advances; Play/Pause/Reset |
| Violation Dashboard | Stat cards (total / critical / blocked / injections), threat + severity filters |
| Eval Score Board | ROUGE/accuracy/efficiency gauges, expandable judge rationale |

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 18+, [`uv`](https://github.com/astral-sh/uv)

```bash
git clone <repo-url> agentq
cd agentq
cp .env.example .env          # add ANTHROPIC_API_KEY (or other judge provider)
./run.sh                      # starts backend :8000 + dashboard :3000
```

To stop: `./kill.sh`

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

**Pre-execution intercept:**

```python
import httpx

resp = httpx.post("http://<your-agentq-host>:8000/api/intercept", json={
    "trace_id": current_trace_id,
    "span_id": new_span_id,
    "tool_name": "send_email",
    "attributes": {"agentq.user_confirmed": False}
})
if not resp.json()["allowed"]:
    raise RuntimeError(resp.json()["reason"])
```

---

## Environment Variables

```env
DATABASE_URL=sqlite+aiosqlite:///./agentq.db

JUDGE_PROVIDER=anthropic          # anthropic | openai | ollama | openrouter
JUDGE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=

WEBHOOK_ENABLED=false
WEBHOOK_URL=
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/traces` | Ingest OTLP/HTTP JSON spans |
| `POST` | `/api/intercept` | Pre-execution tool check (allow/deny) |
| `GET` | `/api/traces` | List spans (limit, offset, service filter) |
| `GET` | `/api/traces/{trace_id}` | All spans for a specific trace |
| `GET` | `/api/violations` | List violations (threat_class, severity, trace_id filters) |
| `GET` | `/api/evals` | List eval results |
| `GET` | `/api/evals/{trace_id}` | Eval result for a specific trace |
| `GET` | `/api/stream` | SSE stream — real-time span and violation events |
| `GET` | `/health` | Health check |

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, aiosqlite / asyncpg, Pydantic v2, ROUGE-score, httpx, sse-starlette, uv

**Frontend:** Next.js 16 App Router, Tailwind CSS v4, Framer Motion, Lucide icons

**Testing:** pytest-asyncio (AUTO mode), in-memory SQLite fixtures

---

Developed by [Mostofa Shakib](https://www.mostofashakib.com)
