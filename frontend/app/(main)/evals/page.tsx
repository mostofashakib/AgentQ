'use client'
import { useEffect, useState } from 'react'
import { api, type EvalResult } from '@/lib/api'
import { EvalGauge } from '@/components/EvalGauge'
import Link from 'next/link'

export default function EvalsPage() {
  const [evals, setEvals] = useState<EvalResult[]>([])
  const [selected, setSelected] = useState<EvalResult | null>(null)

  useEffect(() => { api.evals.list().then(setEvals) }, [])

  const avg = (key: keyof EvalResult) => {
    const vals = evals.map(e => e[key] as number | null).filter(v => v !== null) as number[]
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Eval Score Board</h1>
        <p className="text-sm text-muted mt-0.5">Automated evaluation scores for agent traces</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Task Completion', key: 'task_completion' as const },
          { label: 'Tool Accuracy', key: 'tool_accuracy' as const },
          { label: 'Efficiency', key: 'efficiency' as const },
        ].map(({ label, key }) => (
          <div key={key} className="bg-surface rounded border border-border p-6 flex flex-col items-center gap-2">
            <EvalGauge label={label} value={avg(key)} />
            <p className="text-xs text-muted">avg across {evals.length} traces</p>
          </div>
        ))}
      </div>

      <div className="flex gap-4 min-h-0">
        <div className="flex-1 rounded border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface/50">
                {['TRACE', 'COMPLETION', 'TOOL ACC', 'EFFICIENCY', 'JUDGE', 'FLAGGED'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {evals.map(e => (
                <tr key={e.id} onClick={() => setSelected(e === selected ? null : e)}
                  className={`border-b border-border/50 cursor-pointer transition-colors ${
                    selected?.id === e.id ? 'bg-cyan/5 border-l-2 border-l-cyan' : 'hover:bg-surface/60'
                  }`}>
                  <td className="px-4 py-2.5">
                    <Link href={`/traces/${e.trace_id}`} className="font-mono text-xs text-cyan hover:underline" onClick={ev => ev.stopPropagation()}>
                      {e.trace_id?.slice(0, 12)}
                    </Link>
                  </td>
                  {['task_completion', 'tool_accuracy', 'efficiency'].map(k => {
                    const v = e[k as keyof EvalResult] as number | null
                    return (
                      <td key={k} className={`px-4 py-2.5 text-xs font-mono ${
                        v === null ? 'text-muted' : v >= 0.8 ? 'text-green' : v >= 0.5 ? 'text-amber' : 'text-red'
                      }`}>
                        {v === null ? '—' : `${Math.round(v * 100)}%`}
                      </td>
                    )
                  })}
                  <td className={`px-4 py-2.5 text-xs font-mono ${
                    e.judge_score === null ? 'text-muted' : e.judge_score >= 0.8 ? 'text-green' : e.judge_score >= 0.5 ? 'text-amber' : 'text-red'
                  }`}>
                    {e.judge_score === null ? '—' : `${Math.round(e.judge_score * 100)}%`}
                  </td>
                  <td className="px-4 py-2.5">
                    {e.judge_flagged
                      ? <span className="text-xs font-mono text-red">⚑ FLAGGED</span>
                      : <span className="text-xs text-muted">—</span>}
                  </td>
                </tr>
              ))}
              {evals.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-12 text-center text-muted text-sm">
                  No eval results yet. Traces are scored automatically after ingestion.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>

        {selected && (
          <div className="w-72 rounded border border-border bg-surface/30 p-4 space-y-3 shrink-0">
            <div className="border-l-2 border-cyan pl-3">
              <h3 className="text-sm font-semibold">Judge Rationale</h3>
              <p className="text-xs font-mono text-muted mt-0.5">{selected.trace_id?.slice(0, 16)}</p>
            </div>
            {selected.judge_rationale ? (
              <p className="text-xs text-muted leading-relaxed">{selected.judge_rationale}</p>
            ) : (
              <p className="text-xs text-muted italic">No judge rationale available</p>
            )}
            <div className="space-y-1.5 pt-2 border-t border-border">
              {[
                { label: 'Task Completion', value: selected.task_completion },
                { label: 'Tool Accuracy', value: selected.tool_accuracy },
                { label: 'Efficiency', value: selected.efficiency },
                { label: 'Judge Score', value: selected.judge_score },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between text-xs">
                  <span className="text-muted">{label}</span>
                  <span className="font-mono">{value === null ? '—' : `${Math.round(value * 100)}%`}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
