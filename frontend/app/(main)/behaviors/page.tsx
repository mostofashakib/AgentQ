// frontend/app/(main)/behaviors/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { api, type BehaviorCluster, type BehaviorTrace } from '@/lib/api'
import Link from 'next/link'

export default function BehaviorsPage() {
  const [clusters, setClusters] = useState<BehaviorCluster[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [traces, setTraces] = useState<BehaviorTrace[]>([])
  const [generatingRubric, setGeneratingRubric] = useState<string | null>(null)

  useEffect(() => {
    api.behaviors.list().then(setClusters)
  }, [])

  async function expand(id: string) {
    if (expanded === id) { setExpanded(null); return }
    setExpanded(id)
    const t = await api.behaviors.traces(id, { limit: 10 })
    setTraces(t)
  }

  async function generateRubric(id: string) {
    setGeneratingRubric(id)
    await api.behaviors.generateRubric(id)
    const updated = await api.behaviors.list()
    setClusters(updated)
    setGeneratingRubric(null)
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-wide">Behaviors</h1>
        <p className="text-sm text-muted mt-0.5">Automatically grouped trace patterns from connected agents</p>
      </div>

      {clusters.length === 0 ? (
        <div className="rounded border border-border p-12 text-center text-muted text-sm">
          No behaviors yet. <Link href="/connect" className="text-cyan hover:underline">Connect an agent</Link>
        </div>
      ) : (
        <div className="space-y-2">
          {clusters.map(cluster => (
            <div key={cluster.id} className="rounded border border-border overflow-hidden">
              {/* Cluster header row */}
              <div className="w-full flex items-center hover:bg-surface/60 transition-colors">
                <button
                  type="button"
                  onClick={() => expand(cluster.id)}
                  aria-expanded={expanded === cluster.id}
                  className="min-w-0 flex-1 flex items-center gap-4 px-4 py-3 text-left"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-cyan font-mono">{cluster.name}</span>
                      <span className="text-xs font-mono text-muted px-2 py-0.5 rounded bg-border/40">
                        {cluster.trace_count} traces
                      </span>
                    </div>
                    {cluster.description && (
                      <p className="text-xs text-muted mt-0.5 truncate">{cluster.description}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1 max-w-xs">
                    {(cluster.rubric ?? []).slice(0, 3).map((criterion, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded border border-cyan/20 bg-cyan/5 text-cyan font-mono">
                        {criterion.length > 30 ? criterion.slice(0, 29) + '…' : criterion}
                      </span>
                    ))}
                    {!cluster.rubric?.length && (
                      <span className="text-xs text-muted font-mono italic">no rubric yet</span>
                    )}
                  </div>

                  <span className="text-muted text-xs">{expanded === cluster.id ? '▲' : '▼'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => generateRubric(cluster.id)}
                  aria-label={`Generate rubric for ${cluster.name}`}
                  disabled={generatingRubric === cluster.id}
                  className="mr-4 shrink-0 text-xs font-mono px-3 py-1 rounded border border-border hover:border-cyan/40 text-muted hover:text-cyan transition-colors disabled:opacity-50"
                >
                  {generatingRubric === cluster.id ? 'Generating…' : 'Gen Rubric'}
                </button>
              </div>

              {/* Expanded: recent traces */}
              {expanded === cluster.id && (
                <div className="border-t border-border bg-surface/20">
                  {/* Full rubric */}
                  {cluster.rubric?.length > 0 && (
                    <div className="px-4 py-3 border-b border-border/50">
                      <p className="text-xs text-muted font-mono font-semibold mb-1.5">RUBRIC</p>
                      <ul className="space-y-1">
                        {cluster.rubric.map((c, i) => (
                          <li key={i} className="text-xs text-muted flex gap-2">
                            <span className="text-cyan">&bull;</span> {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recent traces */}
                  <div className="px-4 py-3">
                    <p className="text-xs text-muted font-mono font-semibold mb-2">RECENT TRACES</p>
                    {traces.length === 0 ? (
                      <p className="text-xs text-muted">No traces</p>
                    ) : (
                      <div className="space-y-1">
                        {traces.map(t => (
                          <div key={t.trace_id} className="flex items-center gap-4 text-xs font-mono">
                            <a href={`/traces/${t.trace_id}`} className="text-cyan hover:underline truncate max-w-xs">
                              {t.trace_id.slice(0, 20)}&hellip;
                            </a>
                            <span className="text-muted">sim {(t.similarity_score * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
