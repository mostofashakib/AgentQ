'use client'
import { useEffect, useState } from 'react'
import { api, type Violation } from '@/lib/api'
import { SeverityBadge, ThreatBadge } from '@/components/StatusBadge'
import Link from 'next/link'

const THREATS = ['injection', 'scope', 'exfiltration', 'behavioral', 'integrity']
const SEVERITIES = ['low', 'medium', 'high', 'critical']

export default function ViolationsPage() {
  const [violations, setViolations] = useState<Violation[]>([])
  const [threatFilter, setThreatFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')

  useEffect(() => {
    api.violations.list({
      limit: 200,
      threat_class: threatFilter || undefined,
      severity: severityFilter || undefined,
    }).then(setViolations)
  }, [threatFilter, severityFilter])

  const stats = {
    total: violations.length,
    critical: violations.filter(v => v.severity === 'critical').length,
    blocked: violations.filter(v => v.blocked).length,
    injection: violations.filter(v => v.threat_class === 'injection').length,
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Violation Audit Log</h1>
        <p className="text-sm text-muted mt-0.5">Guardrail violations across all agent traces</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total', value: stats.total, color: 'text-text' },
          { label: 'Critical', value: stats.critical, color: 'text-red' },
          { label: 'Blocked', value: stats.blocked, color: 'text-amber' },
          { label: 'Injections', value: stats.injection, color: 'text-purple-300' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-surface rounded border border-border p-4">
            <p className="text-xs text-muted font-mono">{label.toUpperCase()}</p>
            <p className={`text-2xl font-semibold font-mono mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mb-4">
        <select value={threatFilter} onChange={e => setThreatFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text focus:outline-none focus:border-cyan">
          <option value="">All threats</option>
          {THREATS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text focus:outline-none focus:border-cyan">
          <option value="">All severities</option>
          {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="rounded border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface/50">
              {['RULE', 'THREAT', 'SEVERITY', 'BLOCKED', 'TRACE', 'DESCRIPTION', 'TIME'].map(h => (
                <th key={h} className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {violations.map(v => (
              <tr key={v.id} className="border-b border-border/50 hover:bg-surface/60">
                <td className="px-4 py-2.5 font-mono text-xs text-text">{v.rule_id}</td>
                <td className="px-4 py-2.5"><ThreatBadge threat={v.threat_class} /></td>
                <td className="px-4 py-2.5"><SeverityBadge severity={v.severity} /></td>
                <td className="px-4 py-2.5">
                  {v.blocked ? (
                    <span className="text-xs font-mono text-red">BLOCKED</span>
                  ) : (
                    <span className="text-xs font-mono text-muted">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <Link href={`/traces/${v.trace_id}`} className="font-mono text-xs text-cyan hover:underline">
                    {v.trace_id?.slice(0, 10)}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-xs text-muted max-w-64 truncate">{v.description}</td>
                <td className="px-4 py-2.5 text-xs text-muted font-mono">
                  {new Date(v.created_at).toLocaleTimeString()}
                </td>
              </tr>
            ))}
            {violations.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-muted text-sm">No violations found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
