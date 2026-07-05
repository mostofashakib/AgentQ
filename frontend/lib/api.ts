const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? ''

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  return { 'X-AgentQ-API-Key': API_KEY, ...extra }
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API}${path}`, {
    ...init,
    headers: authHeaders(init.headers as Record<string, string> | undefined),
  })
}

export interface Span {
  id: string
  trace_id: string
  span_id: string
  parent_span_id: string | null
  name: string
  span_kind: string
  service_name: string
  start_time_unix_nano: number
  end_time_unix_nano: number
  duration_ms: number
  status_code: string
  gen_ai_system: string | null
  gen_ai_operation: string | null
  gen_ai_input_tokens: number | null
  gen_ai_output_tokens: number | null
  gen_ai_tool_name: string | null
  attributes: Record<string, unknown>
  created_at: string
}

export interface Violation {
  id: string
  trace_id: string
  span_id: string
  rule_id: string
  threat_class: 'injection' | 'scope' | 'exfiltration' | 'behavioral' | 'integrity'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  evidence: string | null
  chain_span_ids: string[]
  created_at: string
}

export interface WaterfallNode {
  id: string
  trace_id: string
  span_id: string
  parent_span_id: string | null
  name: string
  span_kind: string
  service_name: string
  duration_ms: number
  start_time_unix_nano: number
  end_time_unix_nano: number
  status_code: string
  gen_ai_system: string | null
  gen_ai_operation: string | null
  gen_ai_tool_name: string | null
  depth: number
  children: WaterfallNode[]
  attributes: Record<string, unknown>
  created_at: string | null
}

export interface GraphNode {
  id: string
  service_name: string
  operation: string
  span_count: number
  avg_duration_ms: number
}

export interface GraphEdge {
  source: string
  target: string
  call_count: number
}

export interface ServiceGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface BehaviorCluster {
  id: string
  name: string
  description: string | null
  rubric: string[]
  trace_count: number
  created_at: string | null
}

export interface BehaviorTrace {
  trace_id: string
  similarity_score: number
  assigned_at: string
}

export interface AlertRule {
  id: string
  name: string
  conditions: Record<string, string>
  channels: Array<{ type: string; url?: string; [key: string]: unknown }>
  frequency_limit: number
  cooldown_minutes: number
  enabled: boolean
  created_at: string
}

export interface AlertHistory {
  id: string
  rule_id: string
  trace_id: string
  span_id: string | null
  channel: string
  fired_at: string
}

export interface Agent {
  service_name: string
  span_count: number
  first_seen: string | null
  last_seen: string | null
  violation_count: number
  capture_traces: boolean
  analyze_behavior: boolean
}

export interface AgentConnection {
  service_name: string
  capture_traces: boolean
  analyze_behavior: boolean
  connection_token: string
}

export interface AppSettings {
  token_explosion_threshold: number
  excessive_tool_calls_threshold: number
  infinite_loop_repeat_threshold: number
  behavior_similarity_threshold: number
  default_alert_channel: Record<string, unknown> | null
  llm_provider: string
  llm_model: string
  llm_api_key_set: boolean
  llm_base_url: string | null
}

export interface MonitoringMetrics {
  run_volume: number
  success_rate: number
  error_rate: number
  average_latency_ms: number
  p95_latency_ms: number
  total_tokens: number
  estimated_cost_usd: number
  tool_success_rate: number
  error_count: number
  evaluation_counts: Record<string, number>
  event_counts: Record<string, number>
}

export interface AgentRun {
  trace_id: string
  agent_run_id: string
  session_id: string | null
  agent_type: string
  environment: string
  status: string
  total_latency_ms: number
  input_tokens: number
  output_tokens: number
  estimated_cost_usd: number
  tool_call_count: number
  error_count: number
}

export interface SessionCost {
  session_id: string
  run_count: number
  total_tokens: number
  estimated_cost_usd: number
  error_count: number
  tool_call_count: number
}

export interface QualityTrends {
  days: { date: string; evaluators: Record<string, { pass: number; warn: number; fail: number }> }[]
  totals: Record<string, { pass: number; warn: number; fail: number }>
}

export function subscribeToStream(
  onEvent: (event: { type: string; data: Record<string, unknown> }) => void,
  onStatusChange: (live: boolean) => void,
): () => void {
  let stopped = false
  const controller = new AbortController()

  async function connect() {
    while (!stopped) {
      try {
        const res = await fetch(`${API}/api/stream`, {
          headers: authHeaders({ Accept: 'text/event-stream' }),
          signal: controller.signal,
        })
        if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`)
        onStatusChange(true)
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (!stopped) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split(/\r?\n\r?\n/)
          buffer = parts.pop() ?? ''
          for (const part of parts) {
            const line = part.split(/\r?\n/).find(l => l.trim().startsWith('data: '))
            if (!line) continue
            try {
              onEvent(JSON.parse(line.trim().slice(6)))
            } catch {
              // ignore malformed event payloads
            }
          }
        }
      } catch {
        // connection failed or stream ended — fall through to retry below
      }
      if (stopped) break
      onStatusChange(false)
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
  }

  connect()
  return () => {
    stopped = true
    controller.abort()
  }
}

export const api = {
  traces: {
    list: (params?: { limit?: number; service?: string }) =>
      apiFetch(`/api/traces?limit=${params?.limit ?? 50}${params?.service ? `&service=${params.service}` : ''}`).then(r => r.json() as Promise<Span[]>),
    get: (traceId: string) =>
      apiFetch(`/api/traces/${traceId}`).then(r => r.json() as Promise<Span[]>),
  },
  violations: {
    list: (params?: { limit?: number; threat_class?: string; severity?: string }) => {
      const q = new URLSearchParams()
      if (params?.limit) q.set('limit', String(params.limit))
      if (params?.threat_class) q.set('threat_class', params.threat_class)
      if (params?.severity) q.set('severity', params.severity)
      return apiFetch(`/api/violations?${q}`).then(r => r.json() as Promise<Violation[]>)
    },
  },
  waterfall: {
    get: (traceId: string) =>
      apiFetch(`/api/traces/${traceId}/waterfall`).then(r => r.json() as Promise<WaterfallNode[]>),
  },
  graph: {
    get: () =>
      apiFetch(`/api/graph`).then(r => r.json() as Promise<ServiceGraph>),
  },
  behaviors: {
    list: () =>
      apiFetch(`/api/behaviors`).then(r => r.json() as Promise<BehaviorCluster[]>),
    get: (id: string) =>
      apiFetch(`/api/behaviors/${id}`).then(r => r.json()),
    generateRubric: (id: string) =>
      apiFetch(`/api/behaviors/${id}/rubric`, { method: 'POST' }).then(r => r.json()),
    traces: (id: string, params?: { limit?: number }) => {
      const q = new URLSearchParams()
      if (params?.limit) q.set('limit', String(params.limit))
      return apiFetch(`/api/behaviors/${id}/traces?${q}`)
        .then(r => r.json() as Promise<BehaviorTrace[]>)
    },
  },
  alerts: {
    rules: {
      list: (): Promise<AlertRule[]> =>
        apiFetch(`/api/alerts/rules`).then(r => r.json()),
      create: (body: Omit<AlertRule, 'id' | 'created_at'>): Promise<AlertRule> =>
        apiFetch(`/api/alerts/rules`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }).then(r => r.json()),
      update: (id: string, body: Omit<AlertRule, 'id' | 'created_at'>): Promise<AlertRule> =>
        apiFetch(`/api/alerts/rules/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }).then(r => r.json()),
      delete: (id: string): Promise<{ deleted: string }> =>
        apiFetch(`/api/alerts/rules/${id}`, { method: 'DELETE' }).then(r => r.json()),
    },
    history: {
      list: (limit = 100): Promise<AlertHistory[]> =>
        apiFetch(`/api/alerts/history?limit=${limit}`).then(r => r.json()),
    },
  },
  agents: {
    list: (): Promise<Agent[]> =>
      apiFetch(`/api/agents`).then(r => r.json()),
    connect: (body: { service_name: string; capture_traces: boolean }): Promise<AgentConnection> =>
      apiFetch(`/api/agents`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      }).then(r => r.json()),
    disconnect: (serviceName: string) =>
      apiFetch(`/api/agents/${encodeURIComponent(serviceName)}`, { method: 'DELETE' }).then(r => r.json()),
  },
  settings: {
    get: (): Promise<AppSettings> =>
      apiFetch(`/api/settings`).then(r => r.json()),
    update: (body: Partial<AppSettings> & { llm_api_key?: string }): Promise<AppSettings> =>
      apiFetch(`/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(r => r.json()),
  },
  monitoring: {
    metrics: (): Promise<MonitoringMetrics> =>
      apiFetch(`/api/monitoring/metrics`).then(r => r.json()),
    runs: (): Promise<AgentRun[]> =>
      apiFetch(`/api/monitoring/runs`).then(r => r.json()),
    sessions: () =>
      apiFetch(`/api/monitoring/sessions`).then(r => r.json() as Promise<SessionCost[]>),
    qualityTrends: (days = 7) =>
      apiFetch(`/api/monitoring/quality-trends?days=${days}`).then(r => r.json() as Promise<QualityTrends>),
  },
}
