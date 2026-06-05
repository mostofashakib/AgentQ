'use client'
import { useState, useEffect, useRef, ReactNode } from 'react'
import Link from 'next/link'
import {
  Activity, ChevronLeft, ChevronRight, Copy, Check, Terminal,
  Info, AlertTriangle, Zap, Shield, BarChart3, Monitor,
  BookOpen, ArrowUpRight,
} from 'lucide-react'

// ─── Nav data ─────────────────────────────────────────────────────────────────

const NAV_GROUPS = [
  {
    label: 'Getting Started',
    items: [
      { id: 'overview',   label: 'Overview' },
      { id: 'quickstart', label: 'Quick Start' },
      { id: 'connecting', label: 'Connecting an Agent' },
    ],
  },
  {
    label: 'Core Features',
    items: [
      { id: 'traces',     label: 'Traces & Spans' },
      { id: 'guardrails', label: 'Guardrail Rules' },
      { id: 'evals',      label: 'Eval Scoring' },
      { id: 'alerts',     label: 'Alerts & Webhooks' },
    ],
  },
  {
    label: 'Reference',
    items: [
      { id: 'api', label: 'API Reference' },
      { id: 'env', label: 'Environment Variables' },
    ],
  },
]

const ALL_SECTIONS = NAV_GROUPS.flatMap(g => g.items)

// ─── Design tokens ────────────────────────────────────────────────────────────

const BG         = '#0C1220'
const SIDEBAR    = '#080D1A'
const SURFACE    = '#0E1729'
const BORDER     = '#1B2A3D'
const BORDER_DIM = 'rgba(27,42,61,0.7)'
const TEXT       = '#F1F5F9'
const BODY       = '#94A3B8'
const MUTED      = '#475569'
const ACCENT     = '#00D4FF'
const ACCENT_BG  = 'rgba(0,212,255,0.07)'
const CODE_BG    = '#060B18'

// ─── Primitives ────────────────────────────────────────────────────────────────

function InlineCode({ children }: { children: ReactNode }) {
  return (
    <code style={{
      padding: '2px 7px', borderRadius: 4,
      background: SURFACE, border: `1px solid ${BORDER}`,
      fontFamily: '"IBM Plex Mono", monospace', fontSize: 12.5,
      color: ACCENT, lineHeight: 1,
    }}>
      {children}
    </code>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: MUTED, cursor: 'pointer', background: 'none', border: 'none', padding: 0, transition: 'color 0.15s' }}
      className="hover:text-slate-300"
    >
      {copied ? <Check size={12} color="#22C55E" /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock({ lang = 'shell', children }: { lang?: string; children: string }) {
  return (
    <div style={{ margin: '20px 0', borderRadius: 10, overflow: 'hidden', border: `1px solid ${BORDER}`, boxShadow: '0 4px 24px rgba(0,0,0,0.35)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 16px', background: SURFACE, borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Terminal size={12} color={MUTED} />
          <span style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 11, color: MUTED, textTransform: 'uppercase' as const, letterSpacing: '0.06em' }}>{lang}</span>
        </div>
        <CopyButton text={children} />
      </div>
      <pre style={{ padding: '18px 20px', background: CODE_BG, fontFamily: '"IBM Plex Mono", monospace', fontSize: 13, color: '#CBD5E1', overflowX: 'auto', lineHeight: 1.75, margin: 0, whiteSpace: 'pre' }}>
        {children}
      </pre>
    </div>
  )
}

type CalloutKind = 'note' | 'warning' | 'tip'
const CALLOUT = {
  note:    { border: '#00D4FF', bg: 'rgba(0,212,255,0.06)',    icon: <Info size={15} color="#00D4FF" style={{ marginTop: 1, flexShrink: 0 }} />,         title: '#00D4FF' },
  warning: { border: '#F59E0B', bg: 'rgba(245,158,11,0.06)',   icon: <AlertTriangle size={15} color="#F59E0B" style={{ marginTop: 1, flexShrink: 0 }} />, title: '#F59E0B' },
  tip:     { border: '#22C55E', bg: 'rgba(34,197,94,0.06)',    icon: <Check size={15} color="#22C55E" style={{ marginTop: 1, flexShrink: 0 }} />,          title: '#22C55E' },
}

function Callout({ kind = 'note', title, children }: { kind?: CalloutKind; title?: string; children: ReactNode }) {
  const s = CALLOUT[kind]
  return (
    <div style={{ margin: '20px 0', display: 'flex', gap: 12, padding: '14px 18px', borderRadius: 8, background: s.bg, borderLeft: `3px solid ${s.border}` }}>
      {s.icon}
      <div style={{ fontSize: 14.5, lineHeight: 1.7, color: BODY }}>
        {title && <span style={{ fontWeight: 600, color: s.title, marginRight: 6 }}>{title}</span>}
        {children}
      </div>
    </div>
  )
}

function SectionHeading({ id, title }: { id: string; title: string }) {
  return (
    <div id={id} style={{ scrollMarginTop: 40, display: 'flex', alignItems: 'center', gap: 16, marginTop: 60, marginBottom: 28 }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: TEXT, flexShrink: 0, letterSpacing: '-0.015em', margin: 0 }}>{title}</h2>
      <div style={{ flex: 1, height: 1, background: `linear-gradient(to right, ${BORDER}, transparent)` }} />
    </div>
  )
}

function Prose({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontSize: 15, color: BODY, lineHeight: 1.8, marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {children}
    </div>
  )
}

function Steps({ children }: { children: ReactNode }) {
  return <div style={{ margin: '20px 0', display: 'flex', flexDirection: 'column', gap: 28 }}>{children}</div>
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: 18 }}>
      <div style={{
        flexShrink: 0, width: 32, height: 32, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace',
        color: ACCENT, border: `1.5px solid rgba(0,212,255,0.3)`, background: 'rgba(0,212,255,0.07)',
      }}>
        {n}
      </div>
      <div style={{ flex: 1, paddingTop: 4 }}>
        <p style={{ fontSize: 15.5, fontWeight: 600, color: TEXT, marginBottom: 10, marginTop: 0 }}>{title}</p>
        <div style={{ fontSize: 14.5, color: BODY, lineHeight: 1.75 }}>{children}</div>
      </div>
    </div>
  )
}

// ─── Tables ───────────────────────────────────────────────────────────────────

function DataTable({ headers, children }: { headers: string[]; children: ReactNode }) {
  return (
    <div style={{ margin: '20px 0', borderRadius: 10, border: `1px solid ${BORDER}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
        <thead>
          <tr style={{ background: SURFACE, borderBottom: `1px solid ${BORDER}` }}>
            {headers.map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '11px 16px', fontFamily: '"IBM Plex Mono", monospace', fontSize: 11.5, color: MUTED, fontWeight: 500, textTransform: 'uppercase' as const, letterSpacing: '0.06em' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

function TR({ children, last = false }: { children: ReactNode; last?: boolean }) {
  return (
    <tr style={{ borderBottom: last ? 'none' : `1px solid ${BORDER_DIM}` }} className="hover:bg-[#0D1829] transition-colors">
      {children}
    </tr>
  )
}

function TD({ children, mono, color, small }: { children: ReactNode; mono?: boolean; color?: string; small?: boolean }) {
  return (
    <td style={{ padding: '13px 16px', color: color ?? BODY, fontFamily: mono ? '"IBM Plex Mono", monospace' : undefined, fontSize: small ? 12 : 13.5, lineHeight: 1.5 }}>
      {children}
    </td>
  )
}

const SEV: Record<string, { bg: string; color: string; border: string }> = {
  critical: { bg: 'rgba(239,68,68,0.1)',   color: '#EF4444', border: 'rgba(239,68,68,0.3)' },
  high:     { bg: 'rgba(249,115,22,0.1)',  color: '#F97316', border: 'rgba(249,115,22,0.3)' },
  medium:   { bg: 'rgba(245,158,11,0.1)',  color: '#F59E0B', border: 'rgba(245,158,11,0.3)' },
  low:      { bg: 'rgba(100,116,139,0.1)', color: '#94A3B8', border: 'rgba(100,116,139,0.3)' },
}
const THREAT_COLOR: Record<string, string> = {
  injection: '#C084FC', scope: '#F59E0B', exfiltration: '#EF4444', behavioral: '#60A5FA', integrity: MUTED,
}

function SeverityBadge({ s }: { s: string }) {
  const st = SEV[s] ?? SEV.low
  return (
    <span style={{ display: 'inline-block', padding: '2px 9px', borderRadius: 20, background: st.bg, color: st.color, border: `1px solid ${st.border}`, fontSize: 11, fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: '0.04em' }}>
      {s}
    </span>
  )
}

function MethodBadge({ m }: { m: string }) {
  const post = m === 'POST'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 9px', borderRadius: 5, fontSize: 11,
      fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700,
      background: post ? 'rgba(245,158,11,0.1)' : 'rgba(34,197,94,0.1)',
      color: post ? '#F59E0B' : '#22C55E',
      border: `1px solid ${post ? 'rgba(245,158,11,0.3)' : 'rgba(34,197,94,0.3)'}`,
    }}>
      {m}
    </span>
  )
}

// ─── Feature cards ────────────────────────────────────────────────────────────

const CARDS = [
  { icon: Zap,       color: '#00D4FF', title: 'OTLP Ingest',    desc: 'Drop-in OTel receiver. Zero SDK changes required.' },
  { icon: Shield,    color: '#EF4444', title: '21 Guardrails',  desc: 'Injection, scope, exfiltration, behavioral & integrity.' },
  { icon: BarChart3, color: '#22C55E', title: 'Eval Engine',    desc: 'ROUGE-1 F1, tool accuracy, efficiency, LLM-as-judge.' },
  { icon: Monitor,   color: '#F59E0B', title: 'Live Dashboard', desc: 'SSE-driven trace feed, DAG viewer, replay timeline.' },
]

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DocsPage() {
  const [activeId, setActiveId] = useState('overview')
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    const ids = ALL_SECTIONS.map(s => s.id)
    const onScroll = () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame(() => {
        for (const id of ids) {
          const el = document.getElementById(id)
          if (!el) continue
          if (el.getBoundingClientRect().top <= 120) setActiveId(id)
        }
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: BG, color: TEXT, fontFamily: '"IBM Plex Sans", system-ui, -apple-system, sans-serif' }}>

      {/* ─── Left sidebar ──────────────────────────────────────────────── */}
      <aside style={{ width: 256, flexShrink: 0, display: 'flex', flexDirection: 'column', position: 'sticky', top: 0, height: '100vh', background: SIDEBAR, borderRight: `1px solid ${BORDER}`, overflowY: 'auto' }}>

        {/* Back to dashboard */}
        <Link href="/traces"
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '14px 18px', fontSize: 13, color: MUTED, borderBottom: `1px solid ${BORDER}`, textDecoration: 'none', transition: 'color 0.15s' }}
          className="hover:text-cyan">
          <ChevronLeft size={14} />
          Back to Dashboard
        </Link>

        {/* Brand */}
        <div style={{ padding: '20px 18px', borderBottom: `1px solid ${BORDER}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Activity size={16} color={ACCENT} />
            <span style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 13, fontWeight: 700, color: ACCENT, letterSpacing: '0.1em' }}>AGENTQ</span>
          </div>
          <span style={{ fontSize: 12, color: MUTED }}>Documentation</span>
        </div>

        {/* Nav groups */}
        <nav style={{ flex: 1, padding: '20px 12px', display: 'flex', flexDirection: 'column', gap: 28 }}>
          {NAV_GROUPS.map(group => (
            <div key={group.label}>
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: MUTED, marginBottom: 8, paddingLeft: 8 }}>
                {group.label}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {group.items.map(item => {
                  const active = activeId === item.id
                  return (
                    <a key={item.id} href={`#${item.id}`} onClick={() => setActiveId(item.id)}
                      style={{
                        position: 'relative', display: 'block',
                        padding: '8px 12px', paddingLeft: active ? 14 : 12,
                        fontSize: 14, color: active ? ACCENT : BODY,
                        background: active ? ACCENT_BG : 'transparent',
                        borderRadius: 6, textDecoration: 'none', fontWeight: active ? 500 : 400,
                        borderLeft: `2px solid ${active ? ACCENT : 'transparent'}`,
                        transition: 'all 0.15s',
                      }}
                      className={active ? '' : 'hover:text-slate-200 hover:bg-white/4'}
                    >
                      {item.label}
                    </a>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Version */}
        <div style={{ padding: '14px 18px', borderTop: `1px solid ${BORDER}` }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: BORDER, fontSize: 11, fontFamily: '"IBM Plex Mono", monospace', color: MUTED }}>
            <BookOpen size={10} /> v0.1.0
          </span>
        </div>
      </aside>

      {/* ─── Main content ──────────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ maxWidth: 740, margin: '0 auto', padding: '56px 56px' }}>

          {/* Breadcrumb */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 36, fontSize: 13, color: MUTED, fontFamily: '"IBM Plex Mono", monospace' }}>
            <span>Docs</span><ChevronRight size={11} /><span>Getting Started</span><ChevronRight size={11} />
            <span style={{ color: BODY }}>Overview</span>
          </div>

          {/* ── Hero ─────────────────────────────────────────────────── */}
          <div style={{ marginBottom: 60 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 20, background: SURFACE, border: `1px solid ${BORDER}`, fontSize: 12, color: MUTED, fontFamily: '"IBM Plex Mono", monospace', marginBottom: 24 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: ACCENT, boxShadow: `0 0 8px ${ACCENT}` }} />
              AI Agent Observability Platform
            </div>
            <h1 style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.2, marginBottom: 18, letterSpacing: '-0.025em' }}>
              <span style={{ color: TEXT }}>AgentQ </span>
              <span style={{ background: 'linear-gradient(135deg, #00D4FF 0%, #3B82F6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Documentation
              </span>
            </h1>
            <p style={{ fontSize: 17, color: BODY, lineHeight: 1.75, maxWidth: 580, margin: 0 }}>
              Reliability, evaluation &amp; observability control plane for AI agents — from OTLP ingest to real-time guardrails and eval scoring.
            </p>
          </div>

          {/* ── Overview ─────────────────────────────────────────────── */}
          <SectionHeading id="overview" title="Overview" />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 32 }}>
            {CARDS.map(({ icon: Icon, color, title, desc }) => (
              <div key={title} style={{ padding: '18px 20px', borderRadius: 10, background: SURFACE, border: `1px solid ${BORDER}`, borderTop: `2px solid ${color}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <Icon size={16} color={color} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: TEXT }}>{title}</span>
                </div>
                <p style={{ fontSize: 14, color: BODY, lineHeight: 1.65, margin: 0 }}>{desc}</p>
              </div>
            ))}
          </div>

          <Prose>
            <p>AgentQ is a lightweight observability and safety layer for AI agents. It receives OpenTelemetry spans from any agent — regardless of framework or language — evaluates them against 21 guardrail rules and eval metrics, and surfaces everything in a real-time dashboard.</p>
            <p><strong style={{ color: TEXT }}>How it works:</strong></p>
            <ol style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <li>Your agent emits standard OTel spans to <InlineCode>POST /v1/traces</InlineCode></li>
              <li>AgentQ parses and stores spans, normalizing MCP, GenAI, and custom attributes</li>
              <li>The guardrail engine runs all 21 rules on every span asynchronously</li>
              <li>Violations are stored, streamed via SSE, and optionally sent to a webhook</li>
              <li>Eval metrics are computed per-trace and shown in the Eval Score Board</li>
            </ol>
          </Prose>

          {/* ── Quick Start ──────────────────────────────────────────── */}
          <SectionHeading id="quickstart" title="Quick Start" />

          <Prose>
            <p><strong style={{ color: TEXT }}>Prerequisites:</strong> Python 3.12+, Node.js 18+, <InlineCode>uv</InlineCode> installed globally.</p>
          </Prose>

          <Steps>
            <Step n={1} title="Clone and configure">
              <CodeBlock lang="shell">{`git clone <repo-url> agentq
cd agentq
cp .env.example .env
# Set ANTHROPIC_API_KEY (or another judge provider) in .env`}</CodeBlock>
            </Step>
            <Step n={2} title="Start AgentQ">
              <CodeBlock lang="shell">{`./run.sh`}</CodeBlock>
              <p style={{ marginTop: 8 }}>This starts the FastAPI backend on port <InlineCode>8000</InlineCode> and the Next.js dashboard on port <InlineCode>3000</InlineCode>.</p>
            </Step>
            <Step n={3} title="Connect your agent">
              <p>Point any OTel-compatible agent at your backend&rsquo;s <InlineCode>/v1/traces</InlineCode> endpoint. See <a href="#connecting" style={{ color: ACCENT, textDecoration: 'none' }} className="hover:underline">Connecting an Agent</a>.</p>
            </Step>
            <Step n={4} title="Open the dashboard">
              <p>Spans appear in the Live Traces feed as soon as your agent runs. Click any trace to open the DAG viewer.</p>
            </Step>
          </Steps>

          <Callout kind="tip" title="Stopping the servers">
            Run <InlineCode>./kill.sh</InlineCode> to terminate both the backend and frontend processes.
          </Callout>

          {/* ── Connecting ───────────────────────────────────────────── */}
          <SectionHeading id="connecting" title="Connecting an Agent" />

          <Prose>
            <p>AgentQ accepts standard OTLP/HTTP JSON spans. Set two environment variables before running your agent — replacing <InlineCode>your-agentq-host</InlineCode> with your deployment address:</p>
          </Prose>

          <CodeBlock lang="shell">{`export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-agentq-host:8000
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json`}</CodeBlock>

          <Callout kind="warning" title="JSON only">
            AgentQ only supports <InlineCode>http/json</InlineCode> encoding. Protobuf (<InlineCode>http/protobuf</InlineCode>) is rejected with HTTP&nbsp;415.
          </Callout>

          <Prose><p><strong style={{ color: TEXT }}>Python — opentelemetry-sdk</strong></p></Prose>
          <CodeBlock lang="python">{`pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
import os

os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/json"
provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://your-agentq-host:8000/v1/traces")
    )
)
trace.set_tracer_provider(provider)`}</CodeBlock>

          <Prose><p><strong style={{ color: TEXT }}>Python — openlit (recommended)</strong></p></Prose>
          <CodeBlock lang="python">{`pip install openlit
import openlit
openlit.init(otlp_endpoint="http://your-agentq-host:8000/v1/traces")`}</CodeBlock>

          <Prose>
            <p><strong style={{ color: TEXT }}>MCP agents</strong></p>
            <p>Spans with any <InlineCode>mcp.*</InlineCode> attribute are automatically normalized to GenAI equivalents — no configuration needed. <InlineCode>mcp.server.name</InlineCode> → <InlineCode>gen_ai.system</InlineCode>, <InlineCode>mcp.tool.name</InlineCode> → <InlineCode>gen_ai.tool.name</InlineCode>.</p>
            <p><strong style={{ color: TEXT }}>Custom AgentQ attributes</strong></p>
          </Prose>
          <CodeBlock lang="python">{`span.set_attribute("agentq.original_goal", "Book a flight to NYC")
span.set_attribute("agentq.current_task", "Send email to user")    # triggers goal_drift
span.set_attribute("agentq.allowed_tools", ["search", "calendar"]) # enables scope check
span.set_attribute("agentq.declared_tools", ["search"])             # enables hallucination check
span.set_attribute("agentq.user_confirmed", True)                   # suppresses destructive check
span.set_attribute("agentq.trace_tool_call_count", 15)              # enables loop detection`}</CodeBlock>

          <Prose><p><strong style={{ color: TEXT }}>Pre-execution intercept</strong></p></Prose>
          <CodeBlock lang="python">{`import httpx

resp = httpx.post("http://your-agentq-host:8000/api/intercept", json={
    "trace_id": current_trace_id,
    "span_id": new_span_id,
    "tool_name": "send_email",
    "attributes": {"agentq.user_confirmed": False}
})
if not resp.json()["allowed"]:
    raise RuntimeError(resp.json()["reason"])`}</CodeBlock>

          {/* ── Traces ───────────────────────────────────────────────── */}
          <SectionHeading id="traces" title="Traces & Spans" />

          <Prose>
            <p>AgentQ follows <strong style={{ color: TEXT }}>OTel GenAI Semantic Conventions v1.41+</strong>. Spans are organized in a three-level hierarchy:</p>
          </Prose>

          <DataTable headers={['Level', 'Kind', 'Description']}>
            <TR><TD mono color={ACCENT}>ROOT</TD><TD mono color={TEXT}>SERVER</TD><TD>Top-level agent invocation — one per user request</TD></TR>
            <TR><TD mono color={ACCENT}>AgentCycle</TD><TD mono color={TEXT}>INTERNAL</TD><TD>A single think → act loop iteration</TD></TR>
            <TR last><TD mono color={ACCENT}>ToolCall</TD><TD mono color={TEXT}>CLIENT</TD><TD>Individual LLM call or tool invocation</TD></TR>
          </DataTable>

          <Prose><p><strong style={{ color: TEXT }}>Key OTel GenAI attributes AgentQ reads:</strong></p></Prose>
          <CodeBlock lang="text">{`gen_ai.system                  # "anthropic" | "openai" | "ollama" | ...
gen_ai.operation.name          # "chat" | "embeddings" | ...
gen_ai.usage.input_tokens      # integer
gen_ai.usage.output_tokens     # integer
gen_ai.response.finish_reasons # array: ["stop"] | ["tool_use"] | ...
gen_ai.tool.name               # name of the tool called
gen_ai.prompt                  # user / system message (injection checks)
gen_ai.completion              # model output (exfiltration checks)
gen_ai.tool.result             # tool response (injection via retrieval)
gen_ai.tool.call.arguments     # tool call arguments dict`}</CodeBlock>

          {/* ── Guardrails ───────────────────────────────────────────── */}
          <SectionHeading id="guardrails" title="Guardrail Rules" />

          <Prose>
            <p>AgentQ ships <strong style={{ color: TEXT }}>21 guardrail rules</strong> across 5 threat classes. Rules run automatically on every ingested span — no configuration required.</p>
          </Prose>

          <DataTable headers={['Rule ID', 'Threat', 'Sev', 'Description']}>
            {([
              ['injection.user_content',               'injection',    'high',     'User message contains prompt injection pattern'],
              ['injection.system_prompt_override',     'injection',    'critical', 'Tool output attempts to override system prompt'],
              ['injection.indirect_via_retrieval',     'injection',    'high',     'Retrieved content (RAG/search) contains injection'],
              ['injection.role_confusion',             'injection',    'medium',   'Prompt contains role confusion / persona hijack'],
              ['scope.high_risk_tool',                 'scope',        'high',     'High-risk tool invoked (send_email, delete_file…)'],
              ['scope.unsanctioned_tool',              'scope',        'medium',   'Tool not in the declared agentq.allowed_tools list'],
              ['scope.excessive_tool_calls',           'scope',        'medium',   'Trace has more than 20 tool calls'],
              ['scope.destructive_without_confirmation','scope',       'critical', 'Destructive tool invoked without user confirmation'],
              ['exfiltration.url_in_output',           'exfiltration', 'medium',   'Model output contains a URL'],
              ['exfiltration.base64_in_output',        'exfiltration', 'high',     'Model output contains base64-encoded data'],
              ['exfiltration.sensitive_key_in_output', 'exfiltration', 'critical', 'Model output contains an API key or credential'],
              ['exfiltration.pii_in_output',           'exfiltration', 'critical', 'Model output contains PII (SSN, card, email, IP)'],
              ['exfiltration.outbound_http',           'exfiltration', 'high',     'Agent made an outbound HTTP call via a tool'],
              ['behavioral.goal_drift',                'behavioral',   'medium',   'Agent task has drifted from the original goal'],
              ['behavioral.infinite_loop',             'behavioral',   'high',     'Same span name repeated 5+ times in a trace'],
              ['behavioral.hallucinated_tool',         'behavioral',   'high',     'Agent called a tool not in the declared schema'],
              ['behavioral.token_explosion',           'behavioral',   'medium',   'Span used more than 8,000 tokens'],
              ['integrity.time_inversion',             'integrity',    'low',      'Span end time is before start time'],
              ['integrity.missing_service_name',       'integrity',    'low',      'Span missing service.name resource attribute'],
              ['integrity.missing_gen_ai_attrs',       'integrity',    'low',      'CLIENT span missing gen_ai.system and operation'],
              ['integrity.empty_trace_id',             'integrity',    'medium',   'Span has an empty or missing trace_id'],
            ] as const).map(([id, threat, sev, desc], i, arr) => (
              <TR key={id} last={i === arr.length - 1}>
                <TD mono small color={TEXT}>{id}</TD>
                <TD mono small color={THREAT_COLOR[threat] ?? BODY}>{threat}</TD>
                <TD><SeverityBadge s={sev} /></TD>
                <TD>{desc}</TD>
              </TR>
            ))}
          </DataTable>

          {/* ── Evals ────────────────────────────────────────────────── */}
          <SectionHeading id="evals" title="Eval Scoring" />

          <Prose>
            <p>Every completed trace is automatically scored on three deterministic metrics plus an optional LLM judge:</p>
          </Prose>

          <DataTable headers={['Metric', 'Range', 'How it works']}>
            <TR><TD mono color={ACCENT}>task_completion</TD><TD color={TEXT}>0–1</TD><TD>ROUGE-1 F1 between actual output and expected_output</TD></TR>
            <TR><TD mono color={ACCENT}>tool_accuracy</TD><TD color={TEXT}>0–1</TD><TD>Ratio of successful tool calls to total tool calls</TD></TR>
            <TR><TD mono color={ACCENT}>efficiency</TD><TD color={TEXT}>0–1</TD><TD>optimal_steps / actual_steps, capped at 1.0</TD></TR>
            <TR last><TD mono color={ACCENT}>judge_score</TD><TD color={TEXT}>0–1</TD><TD>LLM-as-judge — requires JUDGE_PROVIDER and a goal on the root span</TD></TR>
          </DataTable>

          <Prose><p><strong style={{ color: TEXT }}>Configuring the LLM judge:</strong></p></Prose>
          <CodeBlock lang="env">{`JUDGE_PROVIDER=anthropic          # anthropic | openai | ollama | openrouter
JUDGE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...`}</CodeBlock>

          <Callout kind="note">
            To trigger judge scoring, attach <InlineCode>agentq.goal</InlineCode> to the root span. The judge receives the goal, full transcript, and final output, then returns a 0–1 score with a one-sentence rationale.
          </Callout>

          {/* ── Alerts ───────────────────────────────────────────────── */}
          <SectionHeading id="alerts" title="Alerts & Webhooks" />

          <Prose>
            <p>Configure AgentQ to POST a JSON payload to any endpoint when a guardrail violation fires:</p>
          </Prose>

          <CodeBlock lang="env">{`WEBHOOK_ENABLED=true
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK`}</CodeBlock>

          <Prose><p><strong style={{ color: TEXT }}>Webhook payload shape:</strong></p></Prose>
          <CodeBlock lang="json">{`{
  "type": "violation",
  "rule_id": "injection.user_content",
  "threat_class": "injection",
  "severity": "high",
  "blocked": true,
  "description": "User message contains prompt injection pattern",
  "trace_id": "abc123...",
  "span_id": "span001...",
  "evidence": "ignore all previous instructions"
}`}</CodeBlock>

          <Callout kind="tip" title="Live stream">
            The dashboard streams violations via SSE — the red violation counter in Live Traces updates in real time without polling.
          </Callout>

          {/* ── API Reference ────────────────────────────────────────── */}
          <SectionHeading id="api" title="API Reference" />

          <Prose>
            <p>Full interactive Swagger UI is available at <InlineCode>/docs</InlineCode> on your AgentQ backend.</p>
          </Prose>

          <DataTable headers={['Method', 'Path', 'Description']}>
            {([
              ['POST', '/v1/traces',             'Ingest OTLP/HTTP JSON spans'],
              ['POST', '/api/intercept',         'Pre-execution tool check — allow/deny before side effects'],
              ['GET',  '/api/traces',            'List spans (limit, offset, service filter)'],
              ['GET',  '/api/traces/{trace_id}', 'All spans for a specific trace'],
              ['GET',  '/api/violations',        'List violations (threat_class, severity, trace_id)'],
              ['GET',  '/api/evals',             'List eval results'],
              ['GET',  '/api/evals/{trace_id}',  'Eval result for a specific trace'],
              ['GET',  '/api/stream',            'SSE stream — real-time span and violation events'],
              ['GET',  '/health',                'Health check'],
            ] as const).map(([method, path, desc], i, arr) => (
              <TR key={path} last={i === arr.length - 1}>
                <TD><MethodBadge m={method} /></TD>
                <TD mono small color={ACCENT}>{path}</TD>
                <TD>{desc}</TD>
              </TR>
            ))}
          </DataTable>

          {/* ── Environment Variables ────────────────────────────────── */}
          <SectionHeading id="env" title="Environment Variables" />

          <CodeBlock lang="env">{`# Database
DATABASE_URL=sqlite+aiosqlite:///./agentq.db
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/agentq

# LLM Judge
JUDGE_PROVIDER=anthropic          # anthropic | openai | ollama | openrouter
JUDGE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=

# Webhooks
WEBHOOK_ENABLED=false
WEBHOOK_URL=`}</CodeBlock>

          {/* Footer */}
          <div style={{ marginTop: 80, paddingTop: 32, borderTop: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 13, color: MUTED }}>AgentQ v0.1.0</span>
            <a href="https://www.mostofashakib.com" target="_blank" rel="noopener noreferrer"
              style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, color: MUTED, textDecoration: 'none', transition: 'color 0.15s' }}
              className="hover:text-cyan">
              Developed by Mostofa Shakib <ArrowUpRight size={12} />
            </a>
          </div>

        </div>
      </div>

      {/* ─── Right TOC ───────────────────────────────────────────────── */}
      <aside className="hidden xl:flex flex-col" style={{ width: 196, flexShrink: 0, position: 'sticky', top: 0, height: '100vh', borderLeft: `1px solid ${BORDER}`, padding: '48px 20px', overflowY: 'auto' }}>
        <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' as const, color: MUTED, marginBottom: 16 }}>
          On This Page
        </p>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {ALL_SECTIONS.map(item => {
            const active = activeId === item.id
            return (
              <a key={item.id} href={`#${item.id}`} onClick={() => setActiveId(item.id)}
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', fontSize: 13, color: active ? ACCENT : BODY, textDecoration: 'none', transition: 'color 0.15s' }}
                className={active ? '' : 'hover:text-slate-200'}
              >
                <span style={{ width: 5, height: 5, borderRadius: '50%', flexShrink: 0, background: active ? ACCENT : MUTED, boxShadow: active ? `0 0 6px ${ACCENT}` : 'none', transition: 'all 0.15s' }} />
                {item.label}
              </a>
            )
          })}
        </nav>
      </aside>

    </div>
  )
}
