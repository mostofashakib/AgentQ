'use client'
import { useEffect, useState } from 'react'
import { api, type Agent } from '@/lib/api'
import { Check, Copy } from 'lucide-react'
import Link from 'next/link'

type FrameworkId = 'openclaw' | 'otel' | 'mcp' | 'curl'

const FRAMEWORKS: { id: FrameworkId; label: string; lang: string; snippet: (name: string) => string }[] = [
  {
    id: 'openclaw',
    label: 'OpenClaw',
    lang: 'json5',
    snippet: (name) => `{
  plugins: { entries: { "diagnostics-otel": { enabled: true } } },
  diagnostics: {
    otel: {
      enabled: true,
      tracesEndpoint: "http://localhost:8000/v1/traces",
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
    snippet: (name) => `pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=Resource.create({"service.name": "${name}"}))
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:8000/v1/traces"))
)
trace.set_tracer_provider(provider)`,
  },
  {
    id: 'mcp',
    label: 'MCP Agent',
    lang: 'shell',
    snippet: (name) => `# Spans with any mcp.* attribute are auto-normalized — no extra config needed.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_SERVICE_NAME=${name}`,
  },
  {
    id: 'curl',
    label: 'cURL (manual test)',
    lang: 'shell',
    snippet: (name) => `curl -X POST http://localhost:8000/v1/traces \\
  -H "Content-Type: application/json" \\
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

  useEffect(() => {
    const poll = () => api.agents.list().then(setAgents).catch(() => {})
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [])

  const framework = FRAMEWORKS.find(f => f.id === frameworkId)!
  const connected = agents.find(a => a.service_name === agentName.trim())

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
        <p className="text-xs text-muted font-mono mb-2">3. CONFIG</p>
        <div className="rounded border border-border overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 bg-surface/50 border-b border-border">
            <span className="text-xs text-muted font-mono uppercase">{framework.lang}</span>
            <CopyButton text={framework.snippet(agentName.trim() || 'my-agent')} />
          </div>
          <pre className="p-4 text-xs font-mono overflow-x-auto whitespace-pre text-text bg-surface/20">
            {framework.snippet(agentName.trim() || 'my-agent')}
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
    </div>
  )
}
