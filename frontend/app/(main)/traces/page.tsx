'use client'
import { Suspense, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api, type Span } from '@/lib/api'
import { KindBadge } from '@/components/StatusBadge'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

interface LiveEvent { type: string; data: Record<string, unknown> }

function TracesContent() {
  const [spans, setSpans] = useState<Span[]>([])
  const [live, setLive] = useState(false)
  const [alertCount, setAlertCount] = useState(0)
  const searchParams = useSearchParams()
  const service = searchParams.get('service') ?? undefined

  useEffect(() => {
    api.traces.list({ limit: 50, service }).then(setSpans)
  }, [service])

  useEffect(() => {
    const es = new EventSource(api.streamUrl())
    es.onopen = () => setLive(true)
    es.onerror = () => setLive(false)
    es.onmessage = (e) => {
      try {
        const event: LiveEvent = JSON.parse(e.data)
        if (event.type === 'span') {
          const s = event.data as unknown as Span
          setSpans(prev => [s, ...prev].slice(0, 200))
          if ((event.data.violation_count as number) > 0) {
            setAlertCount(n => n + 1)
          }
        }
      } catch {}
    }
    return () => es.close()
  }, [])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Live Trace Feed</h1>
          <p className="text-sm text-muted mt-0.5">
            Real-time span stream from connected agents
            {service && <> &middot; filtered by <span className="text-cyan">{service}</span></>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {alertCount > 0 && (
            <span className="px-3 py-1 rounded bg-red/10 border border-red/20 text-red text-xs font-mono">
              {alertCount} violation{alertCount !== 1 ? 's' : ''}
            </span>
          )}
          <div className={`flex items-center gap-2 px-3 py-1 rounded border text-xs font-mono ${
            live ? 'bg-green/10 border-green/20 text-green' : 'bg-muted/10 border-border text-muted'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${live ? 'bg-green animate-pulse' : 'bg-muted'}`} />
            {!live && 'CONNECTING'}
          </div>
        </div>
      </div>

      <div className="rounded border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface/50">
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">TRACE ID</th>
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">SPAN</th>
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">KIND</th>
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">SERVICE</th>
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">DURATION</th>
              <th className="text-left px-4 py-2.5 text-xs text-muted font-mono font-normal">STATUS</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {spans.map((span) => (
                <motion.tr
                  key={span.id ?? span.span_id}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-b border-border/50 hover:bg-surface/60 cursor-pointer"
                >
                  <td className="px-4 py-2.5">
                    <Link href={`/traces/${span.trace_id}`} className="font-mono text-xs text-cyan hover:underline">
                      {span.trace_id?.slice(0, 12) ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-xs max-w-48 truncate">{span.name}</td>
                  <td className="px-4 py-2.5"><KindBadge kind={span.span_kind} /></td>
                  <td className="px-4 py-2.5 text-xs text-muted">{span.service_name}</td>
                  <td className="px-4 py-2.5 text-xs font-mono text-muted">
                    {span.duration_ms != null ? `${span.duration_ms.toFixed(1)}ms` : '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs font-mono ${
                      span.status_code === 'STATUS_CODE_OK' ? 'text-green' :
                      span.status_code === 'STATUS_CODE_ERROR' ? 'text-red' : 'text-muted'
                    }`}>
                      {span.status_code?.replace('STATUS_CODE_', '') ?? 'UNSET'}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {spans.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-muted text-sm">
                No spans yet. Connect an agent with OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function TracesPage() {
  return (
    <Suspense fallback={null}>
      <TracesContent />
    </Suspense>
  )
}
