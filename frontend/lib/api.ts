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
  blocked: boolean
  description: string
  evidence: string | null
  chain_span_ids: string[]
  created_at: string
}

export interface EvalResult {
  id: string
  trace_id: string
  task_completion: number | null
  tool_accuracy: number | null
  efficiency: number | null
  judge_score: number | null
  judge_rationale: string | null
  judge_flagged: boolean
  created_at: string
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
  evals: {
    list: () => fetch(`${API}/api/evals`).then(r => r.json() as Promise<EvalResult[]>),
  },
  streamUrl: () => `${API}/api/stream`,
}
