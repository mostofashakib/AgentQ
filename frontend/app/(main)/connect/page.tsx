'use client'
import { useEffect, useState } from 'react'
import { api, type Agent } from '@/lib/api'
import { Check, Copy } from 'lucide-react'
import Link from 'next/link'

type FrameworkId = 'openclaw' | 'otel' | 'mcp' | 'curl'

const FRAMEWORKS: { id: FrameworkId; label: string; lang: string; snippet: (name: string, token: string) => string }[] = [
  {
    id: 'openclaw',
    label: 'OpenClaw',
    lang: 'json5',
    snippet: (name, token) => `{
  plugins: { entries: { "diagnostics-otel": { enabled: true } } },
  diagnostics: {
    otel: {
      enabled: true,
      tracesEndpoint: "http://localhost:8000/v1/traces",
      headers: { "X-AgentQ-Agent-Token": "${token || '<connection-token>'}" },
      protocol: "http/protobuf",
      serviceName: "${name}",
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
}`,
  },
  {
    id: 'otel',
    label: 'Generic OTel SDK (Python)',
    lang: 'python',
    snippet: (name, token) => `pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=Resource.create({"service.name": "${name}"}))
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(
        endpoint="http://localhost:8000/v1/traces",
        headers={"X-AgentQ-Agent-Token": "${token || '<connection-token>'}"},
    ))
)
trace.set_tracer_provider(provider)`,
  },
  {
    id: 'mcp',
    label: 'MCP Agent',
    lang: 'shell',
    snippet: (name, token) => `# Spans with any mcp.* attribute are auto-normalized — no extra config needed.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_HEADERS="X-AgentQ-Agent-Token=${token || '<connection-token>'}"
export OTEL_SERVICE_NAME=${name}`,
  },
  {
    id: 'curl',
    label: 'cURL (manual test)',
    lang: 'shell',
    snippet: (name, token) => `curl -X POST http://localhost:8000/v1/traces \\
  -H "Content-Type: application/json" \\
  -H "X-AgentQ-Agent-Token: ${token || '<connection-token>'}" \\
  -d '{
    "resourceSpans": [{
      "resource": { "attributes": [
        { "key": "service.name", "value": { "stringValue": "${name}" } }
      ]},
      "scopeSpans": [{ "spans": [{
        "traceId": "manualtest0000000000000000000001",
        "spanId": "manualtest00000001",
        "name": "agent.run",
        "kind": 2,
        "startTimeUnixNano": "1000000000",
        "endTimeUnixNano": "1050000000",
        "attributes": [
          { "key": "gen_ai.system", "value": { "stringValue": "test" } }
        ],
        "status": { "code": "STATUS_CODE_OK" }
      }]}]
    }]
  }'`,
  },
]

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="flex items-center gap-1.5 text-xs text-muted hover:text-cyan transition-colors"
    >
      {copied ? <Check size={12} className="text-green" /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function ConnectPage() {
  const [frameworkId, setFrameworkId] = useState<FrameworkId>('openclaw')
  const [agentName, setAgentName] = useState('my-agent')
  const [agents, setAgents] = useState<Agent[]>([])
  const [captureTraces, setCaptureTraces] = useState(true)
  const [connectionToken, setConnectionToken] = useState('')

  useEffect(() => {
    const poll = () => api.agents.list().then(setAgents).catch(() => {})
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [])

  const framework = FRAMEWORKS.find(f => f.id === frameworkId)!
  const connected = agents.find(a => a.service_name === agentName.trim())

  async function connectAgent() {
    const serviceName = agentName.trim()
    if (!serviceName) return
    const connection = await api.agents.connect({
      service_name: serviceName, capture_traces: captureTraces,
    })
    setConnectionToken(connection.connection_token)
    setAgents(await api.agents.list())
  }

  async function disconnectAgent(serviceName: string) {
    await api.agents.disconnect(serviceName)
    setAgents(await api.agents.list())
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Connect an Agent</h1>
        <p className="text-sm text-muted mt-0.5">Speak AOP/1 — the AgentQ Observability Protocol — from any agent framework</p>
      </div>

      <div className="mb-6">
        <p className="text-xs text-muted font-mono mb-2">1. FRAMEWORK</p>
        <div className="flex gap-2 flex-wrap">
          {FRAMEWORKS.map(f => (
            <button
              key={f.id}
              onClick={() => setFrameworkId(f.id)}
              className={`px-3 py-1.5 rounded text-sm border transition-colors ${
                frameworkId === f.id ? 'bg-cyan/10 text-cyan border-cyan/30' : 'text-muted border-border hover:text-text hover:bg-border/40'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <p className="text-xs text-muted font-mono mb-2">2. AGENT NAME</p>
        <input
          value={agentName}
          onChange={e => setAgentName(e.target.value)}
          placeholder="my-agent"
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text font-mono focus:outline-none focus:border-cyan w-64"
        />
        <p className="text-xs text-muted mt-1.5">Becomes the <code className="text-cyan">service.name</code> AgentQ uses to identify this agent.</p>
      </div>

      <div className="mb-6">
        <p className="text-xs text-muted font-mono mb-2">3. MONITORING</p>
        <div className="flex gap-5 mb-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={captureTraces} onChange={e => setCaptureTraces(e.target.checked)} />
            Observe traces
          </label>
        </div>
        <button type="button" onClick={connectAgent}
          disabled={!agentName.trim()}
          className="text-xs font-mono px-3 py-1.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 disabled:opacity-40">
          Connect and authorize agent
        </button>
        <p className="text-xs text-muted mt-2">Behavior analysis is always enabled for connected agents. Trace metadata required for clustering is retained.</p>
      </div>

      <div className="mb-6">
        <p className="text-xs text-muted font-mono mb-2">4. CONFIG</p>
        <div className="rounded border border-border overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 bg-surface/50 border-b border-border">
            <span className="text-xs text-muted font-mono uppercase">{framework.lang}</span>
            <CopyButton text={framework.snippet(agentName.trim() || 'my-agent', connectionToken)} />
          </div>
          <pre className="p-4 text-xs font-mono overflow-x-auto whitespace-pre text-text bg-surface/20">
            {framework.snippet(agentName.trim() || 'my-agent', connectionToken)}
          </pre>
        </div>
      </div>

      <div className="rounded border border-border p-4">
        {connected ? (
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-green" />
            <div>
              <p className="text-sm text-green font-mono">Connected — {connected.span_count} spans, {connected.violation_count} violations</p>
              <Link href={`/traces?service=${connected.service_name}`} className="text-xs text-cyan hover:underline">
                View traces for {connected.service_name}
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-muted animate-pulse" />
            <p className="text-sm text-muted font-mono">Waiting for spans from &ldquo;{agentName.trim() || 'my-agent'}&rdquo;…</p>
          </div>
        )}
      </div>

      <div className="mt-6">
        <p className="text-xs text-muted font-mono mb-2">CONNECTED AGENTS</p>
        <div className="space-y-2">
          {agents.map(agent => (
            <div key={agent.service_name} className="rounded border border-border px-4 py-3 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm text-cyan font-mono truncate">{agent.service_name}</p>
                <p className="text-xs text-muted">{agent.span_count} spans · {agent.violation_count} violations · behavior active</p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <Link href={`/traces?service=${encodeURIComponent(agent.service_name)}`} className="text-xs text-cyan hover:underline">Observe</Link>
                <button type="button" onClick={() => disconnectAgent(agent.service_name)}
                  className="text-xs text-muted hover:text-red-400 transition-colors">Disconnect</button>
              </div>
            </div>
          ))}
          {agents.length === 0 && <p className="text-sm text-muted">No agents connected.</p>}
        </div>
      </div>
    </div>
  )
}
