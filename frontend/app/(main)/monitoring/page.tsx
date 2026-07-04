'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type AgentRun, type MonitoringMetrics } from '@/lib/api'

const percent = (value: number) => `${(value * 100).toFixed(1)}%`

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])

  useEffect(() => {
    Promise.all([api.monitoring.metrics(), api.monitoring.runs()]).then(([summary, recent]) => {
      setMetrics(summary)
      setRuns(recent)
    })
  }, [])

  const cards = metrics ? [
    ['RUNS', metrics.run_volume.toLocaleString()],
    ['SUCCESS', percent(metrics.success_rate)],
    ['P95 LATENCY', `${metrics.p95_latency_ms.toFixed(0)}ms`],
    ['TOKENS', metrics.total_tokens.toLocaleString()],
    ['EST. COST', `$${metrics.estimated_cost_usd.toFixed(4)}`],
    ['TOOL SUCCESS', percent(metrics.tool_success_rate)],
  ] : []

  return <div className="p-6">
    <div className="mb-6">
      <h1 className="text-lg font-semibold tracking-wide">Agent Run Health</h1>
      <p className="text-sm text-muted mt-0.5">Reliability, cost, quality, and safety signals by trace</p>
    </div>
    <div className="grid grid-cols-3 gap-3 mb-6">
      {cards.map(([label, value]) => <div key={label} className="border border-border rounded bg-surface/40 p-4">
        <div className="font-mono text-[10px] tracking-widest text-muted">{label}</div>
        <div className="font-mono text-xl text-cyan mt-2">{value}</div>
      </div>)}
    </div>
    {metrics && <div className="flex gap-6 mb-6 text-xs font-mono text-muted">
      <span>evaluations: {Object.entries(metrics.evaluation_counts).map(([k, v]) => `${k} ${v}`).join(' · ') || 'none'}</span>
      <span>events: {Object.entries(metrics.event_counts).map(([k, v]) => `${k} ${v}`).join(' · ') || 'none'}</span>
    </div>}
    <div className="border border-border rounded overflow-hidden">
      <table className="w-full text-sm"><thead className="bg-surface/50"><tr>
        {['TRACE', 'AGENT', 'STATUS', 'LATENCY', 'TOKENS', 'COST', 'TOOLS'].map(h => <th key={h} className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">{h}</th>)}
      </tr></thead><tbody>{runs.map(run => <tr key={run.agent_run_id} className="border-t border-border/60">
        <td className="px-4 py-2.5"><Link className="font-mono text-xs text-cyan hover:underline" href={`/traces/${run.trace_id}`}>{run.trace_id.slice(0, 12)}</Link></td>
        <td className="px-4 py-2.5 text-muted">{run.agent_type}</td>
        <td className={`px-4 py-2.5 font-mono text-xs ${run.status === 'success' ? 'text-green' : 'text-red'}`}>{run.status}</td>
        <td className="px-4 py-2.5 font-mono text-xs">{run.total_latency_ms.toFixed(0)}ms</td>
        <td className="px-4 py-2.5 font-mono text-xs">{(run.input_tokens + run.output_tokens).toLocaleString()}</td>
        <td className="px-4 py-2.5 font-mono text-xs">${run.estimated_cost_usd.toFixed(4)}</td>
        <td className="px-4 py-2.5 font-mono text-xs">{run.tool_call_count}</td>
      </tr>)}</tbody></table>
    </div>
  </div>
}
