const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

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
  first_seen: string
  last_seen: string
  violation_count: number
}

export interface AppSettings {
  token_explosion_threshold: number
  excessive_tool_calls_threshold: number
  infinite_loop_repeat_threshold: number
  behavior_similarity_threshold: number
  default_alert_channel: Record<string, unknown> | null
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

export const api = {
  traces: {
    list: (params?: { limit?: number; service?: string }) =>
      fetch(`${API}/api/traces?limit=${params?.limit ?? 50}${params?.service ? `&service=${params.service}` : ''}`).then(r => r.json() as Promise<Span[]>),
    get: (traceId: string) =>
      fetch(`${API}/api/traces/${traceId}`).then(r => r.json() as Promise<Span[]>),
  },
  violations: {
    list: (params?: { limit?: number; threat_class?: string; severity?: string }) => {
      const q = new URLSearchParams()
      if (params?.limit) q.set('limit', String(params.limit))
      if (params?.threat_class) q.set('threat_class', params.threat_class)
      if (params?.severity) q.set('severity', params.severity)
      return fetch(`${API}/api/violations?${q}`).then(r => r.json() as Promise<Violation[]>)
    },
  },
  waterfall: {
    get: (traceId: string) =>
      fetch(`${API}/api/traces/${traceId}/waterfall`).then(r => r.json() as Promise<WaterfallNode[]>),
  },
  graph: {
    get: () =>
      fetch(`${API}/api/graph`).then(r => r.json() as Promise<ServiceGraph>),
  },
  behaviors: {
    list: () =>
      fetch(`${API}/api/behaviors`).then(r => r.json() as Promise<BehaviorCluster[]>),
    get: (id: string) =>
      fetch(`${API}/api/behaviors/${id}`).then(r => r.json()),
    generateRubric: (id: string) =>
      fetch(`${API}/api/behaviors/${id}/rubric`, { method: 'POST' }).then(r => r.json()),
    traces: (id: string, params?: { limit?: number }) => {
      const q = new URLSearchParams()
      if (params?.limit) q.set('limit', String(params.limit))
      return fetch(`${API}/api/behaviors/${id}/traces?${q}`)
        .then(r => r.json() as Promise<BehaviorTrace[]>)
    },
  },
  alerts: {
    rules: {
      list: (): Promise<AlertRule[]> =>
        fetch(`${API}/api/alerts/rules`).then(r => r.json()),
      create: (body: Omit<AlertRule, 'id' | 'created_at'>): Promise<AlertRule> =>
        fetch(`${API}/api/alerts/rules`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }).then(r => r.json()),
      update: (id: string, body: Omit<AlertRule, 'id' | 'created_at'>): Promise<AlertRule> =>
        fetch(`${API}/api/alerts/rules/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }).then(r => r.json()),
      delete: (id: string): Promise<{ deleted: string }> =>
        fetch(`${API}/api/alerts/rules/${id}`, { method: 'DELETE' }).then(r => r.json()),
    },
    history: {
      list: (limit = 100): Promise<AlertHistory[]> =>
        fetch(`${API}/api/alerts/history?limit=${limit}`).then(r => r.json()),
    },
  },
  agents: {
    list: (): Promise<Agent[]> =>
      fetch(`${API}/api/agents`).then(r => r.json()),
  },
  settings: {
    get: (): Promise<AppSettings> =>
      fetch(`${API}/api/settings`).then(r => r.json()),
    update: (body: Partial<AppSettings>): Promise<AppSettings> =>
      fetch(`${API}/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(r => r.json()),
  },
  monitoring: {
    metrics: (): Promise<MonitoringMetrics> =>
      fetch(`${API}/api/monitoring/metrics`).then(r => r.json()),
    runs: (): Promise<AgentRun[]> =>
      fetch(`${API}/api/monitoring/runs`).then(r => r.json()),
  },
  streamUrl: () => `${API}/api/stream`,
}
