// frontend/app/(main)/graph/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { api, type ServiceGraph } from '@/lib/api'
import { ServiceGraph as ServiceGraphComponent } from '@/components/ServiceGraph'

export default function GraphPage() {
  const [graph, setGraph] = useState<ServiceGraph>({ nodes: [], edges: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.graph.get().then(data => { setGraph(data); setLoading(false) })
  }, [])

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-wide">Service Graph</h1>
        <p className="text-sm text-muted mt-0.5">Cross-trace call relationships between services and operations</p>
      </div>

      <div className="flex gap-4 mb-4 text-xs font-mono text-muted">
        <span>{graph.nodes.length} nodes</span>
        <span>{graph.edges.length} edges</span>
      </div>

      <div className="rounded border border-border bg-surface/30 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-96 text-muted text-sm">Loading…</div>
        ) : (
          <ServiceGraphComponent nodes={graph.nodes} edges={graph.edges} />
        )}
      </div>

      {graph.nodes.length > 0 && (
        <div className="mt-4 rounded border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface/50">
                <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">SERVICE</th>
                <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">OPERATION</th>
                <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">SPANS</th>
                <th className="text-left px-4 py-2 text-xs text-muted font-mono font-normal">AVG DURATION</th>
              </tr>
            </thead>
            <tbody>
              {graph.nodes.map(n => (
                <tr key={n.id} className="border-b border-border/50">
                  <td className="px-4 py-2 text-xs font-mono text-cyan">{n.service_name}</td>
                  <td className="px-4 py-2 text-xs text-muted">{n.operation}</td>
                  <td className="px-4 py-2 text-xs font-mono">{n.span_count}</td>
                  <td className="px-4 py-2 text-xs font-mono text-muted">{n.avg_duration_ms.toFixed(1)}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
