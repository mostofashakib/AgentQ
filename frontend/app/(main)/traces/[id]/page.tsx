'use client'
import { use, useEffect, useRef, useState, useCallback } from 'react'
import { api, type Span, type Violation } from '@/lib/api'
import { KindBadge } from '@/components/StatusBadge'

// ─── DAG layout helpers ───────────────────────────────────────────────────────

const NODE_W = 180
const NODE_H = 36
const H_GAP = 24
const V_GAP = 60

interface LayoutNode {
  span: Span
  x: number
  y: number
  subtreeW: number
}

function buildLayout(spans: Span[]): LayoutNode[] {
  if (!spans.length) return []

  const childMap = new Map<string, Span[]>()
  const spanIds = new Set(spans.map(s => s.span_id))
  const roots: Span[] = []

  for (const s of spans) {
    if (s.parent_span_id === null || !spanIds.has(s.parent_span_id)) {
      roots.push(s)
    } else {
      if (!childMap.has(s.parent_span_id)) childMap.set(s.parent_span_id, [])
      childMap.get(s.parent_span_id)!.push(s)
    }
  }

  const nodes: LayoutNode[] = []

  function subtreeWidth(span: Span): number {
    const children = childMap.get(span.span_id) ?? []
    if (!children.length) return NODE_W
    const totalChildW = children.reduce((sum, c) => sum + subtreeWidth(c), 0)
    const gaps = (children.length - 1) * H_GAP
    return Math.max(NODE_W, totalChildW + gaps)
  }

  function place(span: Span, depth: number, left: number) {
    const sw = subtreeWidth(span)
    const cx = left + sw / 2
    nodes.push({ span, x: cx - NODE_W / 2, y: depth * (NODE_H + V_GAP), subtreeW: sw })
    const children = childMap.get(span.span_id) ?? []
    let childLeft = left
    for (const child of children) {
      const csw = subtreeWidth(child)
      place(child, depth + 1, childLeft)
      childLeft += csw + H_GAP
    }
  }

  let left = 0
  for (const root of roots) {
    const sw = subtreeWidth(root)
    place(root, 0, left)
    left += sw + H_GAP
  }

  return nodes
}

// ─── DAG SVG component ────────────────────────────────────────────────────────

function DagGraph({
  spans,
  selected,
  violations,
  onSelect,
}: {
  spans: Span[]
  selected: Span | null
  violations: Violation[]
  onSelect: (s: Span) => void
}) {
  const nodes = buildLayout(spans)

  if (!nodes.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-muted)', fontSize: 13 }}>
        No spans
      </div>
    )
  }

  const nodeMap = new Map(nodes.map(n => [n.span.span_id, n]))

  const violMap = new Map<string, Violation[]>()
  for (const v of violations) {
    if (!violMap.has(v.span_id)) violMap.set(v.span_id, [])
    violMap.get(v.span_id)!.push(v)
  }

  const padX = 32
  const padY = 32
  const maxX = Math.max(...nodes.map(n => n.x + NODE_W)) + padX * 2
  const maxY = Math.max(...nodes.map(n => n.y + NODE_H)) + padY * 2
  const svgW = maxX
  const svgH = maxY

  interface Edge { px: number; py: number; cx: number; cy: number; toSelected: boolean }
  const edges: Edge[] = []
  for (const n of nodes) {
    const parentId = n.span.parent_span_id
    if (parentId && nodeMap.has(parentId)) {
      const p = nodeMap.get(parentId)!
      edges.push({
        px: p.x + padX + NODE_W / 2,
        py: p.y + padY + NODE_H,
        cx: n.x + padX + NODE_W / 2,
        cy: n.y + padY,
        toSelected: selected?.span_id === n.span.span_id,
      })
    }
  }

  return (
    <div style={{ overflow: 'auto', width: '100%', height: '100%' }}>
      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {/* Edges */}
        {edges.map((e, i) => {
          const mid = Math.max((e.cy - e.py) / 2, 20)
          const d = `M${e.px},${e.py} C${e.px},${e.py + mid} ${e.cx},${e.cy - mid} ${e.cx},${e.cy}`
          return (
            <path
              key={i}
              d={d}
              fill="none"
              stroke="#00D4FF"
              strokeWidth={1.5}
              opacity={e.toSelected ? 0.5 : 0.25}
            />
          )
        })}

        {/* Nodes */}
        {nodes.map(({ span, x, y }) => {
          const nx = x + padX
          const ny = y + padY
          const viols = violMap.get(span.span_id) ?? []
          const isBlocked = viols.some(v => v.blocked)
          const isSelected = selected?.span_id === span.span_id

          let nodeStroke = '#1E2D4A'
          if (isSelected) nodeStroke = '#00D4FF'
          else if (isBlocked) nodeStroke = '#ef4444'

          const fill = isSelected ? '#001E30' : '#0D1526'
          const truncName = span.name.length > 20 ? span.name.slice(0, 19) + '…' : span.name
          const durLabel = `${span.duration_ms.toFixed(1)}ms`
          const kindColor =
            span.span_kind === 'CLIENT' ? '#68D391' :
            span.span_kind === 'SERVER' ? '#00D4FF' :
            '#F6AD55'

          return (
            <g key={span.span_id} onClick={() => onSelect(span)} style={{ cursor: 'pointer' }}>
              {/* Drop shadow */}
              <rect x={nx + 2} y={ny + 2} width={NODE_W} height={NODE_H} rx={6} fill="black" opacity={0.3} />
              {/* Node rect */}
              <rect
                x={nx} y={ny} width={NODE_W} height={NODE_H} rx={6}
                fill={fill} stroke={nodeStroke} strokeWidth={isSelected ? 1.5 : 1}
              />
              {/* Span name */}
              <text x={nx + 8} y={ny + 14} fontSize={10} fill={isBlocked ? '#FC8181' : '#E8EDF5'} fontFamily="monospace">
                {truncName}
              </text>
              {/* Kind label */}
              <text x={nx + 8} y={ny + 27} fontSize={9} fill={kindColor} fontFamily="monospace">
                {span.span_kind}
              </text>
              {/* Duration */}
              <text x={nx + NODE_W - 8} y={ny + 27} fontSize={9} fill="#4A5568" fontFamily="monospace" textAnchor="end">
                {durLabel}
              </text>
              {/* Violation badge */}
              {viols.length > 0 && (
                <>
                  <circle cx={nx + NODE_W - 7} cy={ny + 7} r={7} fill="#ef4444" />
                  <text x={nx + NODE_W - 7} y={ny + 11} fontSize={8} fill="white" fontFamily="sans-serif" textAnchor="middle">
                    {viols.length}
                  </text>
                </>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// ─── Episode Replay Timeline ──────────────────────────────────────────────────

const KIND_COLORS: Record<string, string> = {
  CLIENT: '#00D4FF',
  SERVER: '#68D391',
  INTERNAL: '#4A6FA5',
}

function formatNs(ns: number): string {
  const ms = ns / 1_000_000
  return ms < 1000 ? `${ms.toFixed(0)}ms` : `${(ms / 1000).toFixed(2)}s`
}

function computeDepth(spans: Span[]): Map<string, number> {
  const spanIds = new Set(spans.map(s => s.span_id))
  const depthCache = new Map<string, number>()

  function getDepth(spanId: string): number {
    if (depthCache.has(spanId)) return depthCache.get(spanId)!
    const span = spans.find(s => s.span_id === spanId)
    const parentId = span?.parent_span_id
    if (!parentId || !spanIds.has(parentId)) {
      depthCache.set(spanId, 0)
      return 0
    }
    const d = getDepth(parentId) + 1
    depthCache.set(spanId, d)
    return d
  }

  for (const s of spans) getDepth(s.span_id)
  return depthCache
}

function EpisodeTimeline({ spans }: { spans: Span[] }) {
  const [playhead, setPlayhead] = useState(0)
  const [playing, setPlaying] = useState(false)
  const rafRef = useRef<number | null>(null)
  const startRef = useRef<number | null>(null)
  const playheadAtStart = useRef(0)
  const trackRef = useRef<HTMLDivElement>(null)
  const PLAY_DURATION_MS = 5000

  const sorted = [...spans].sort((a, b) => Number(a.start_time_unix_nano) - Number(b.start_time_unix_nano))
  const depthMap = computeDepth(sorted)
  const traceStartNs = sorted.length ? Number(sorted[0].start_time_unix_nano) : 0
  const traceEndNs = sorted.length ? Math.max(...sorted.map(s => Number(s.end_time_unix_nano))) : 1
  const totalNs = Math.max(traceEndNs - traceStartNs, 1)

  const animate = useCallback((ts: number) => {
    if (startRef.current === null) startRef.current = ts
    const elapsed = ts - startRef.current
    const remaining = PLAY_DURATION_MS * (1 - playheadAtStart.current)
    const t = Math.min(playheadAtStart.current + (elapsed / remaining) * (1 - playheadAtStart.current), 1)
    setPlayhead(t)
    if (t < 1) {
      rafRef.current = requestAnimationFrame(animate)
    } else {
      setPlaying(false)
      startRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (playing) {
      playheadAtStart.current = playhead >= 1 ? 0 : playhead
      if (playhead >= 1) setPlayhead(0)
      startRef.current = null
      rafRef.current = requestAnimationFrame(animate)
    } else {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
    }
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing])

  function posFromEvent(e: React.MouseEvent | MouseEvent) {
    if (!trackRef.current) return
    const rect = trackRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
    setPlayhead(x / rect.width)
  }

  function onTrackMouseDown(e: React.MouseEvent) {
    e.preventDefault()
    setPlaying(false)
    posFromEvent(e)
    function onMove(ev: MouseEvent) { posFromEvent(ev) }
    function onUp() {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  if (!sorted.length) return null

  const LABEL_W = 90
  const ROW_H = 20
  const currentNs = playhead * totalNs

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
        borderBottom: '1px solid var(--color-border)', flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--color-muted)', fontWeight: 600, letterSpacing: 1 }}>
          EPISODE REPLAY
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#00D4FF' }}>
          {formatNs(currentNs)} / {formatNs(totalNs)}
        </span>
        <button
          onClick={() => setPlaying(p => !p)}
          style={{
            padding: '3px 10px', borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
            background: playing ? 'rgba(0,212,255,0.15)' : 'rgba(0,212,255,0.08)',
            border: '1px solid rgba(0,212,255,0.3)', color: '#00D4FF', cursor: 'pointer',
          }}
        >
          {playing ? '⏸ PAUSE' : '▶ PLAY'}
        </button>
        <button
          onClick={() => { setPlaying(false); setPlayhead(0) }}
          style={{
            padding: '3px 10px', borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
            background: 'rgba(74,85,104,0.15)', border: '1px solid rgba(74,85,104,0.3)',
            color: 'var(--color-muted)', cursor: 'pointer',
          }}
        >
          ↺ RESET
        </button>
      </div>

      {/* Span rows */}
      <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
        {sorted.map((span) => {
          const spanStartNs = Number(span.start_time_unix_nano) - traceStartNs
          const spanDurNs = Number(span.end_time_unix_nano) - Number(span.start_time_unix_nano)
          const leftPct = (spanStartNs / totalNs) * 100
          const widthPct = (spanDurNs / totalNs) * 100
          const reached = currentNs >= spanStartNs
          const color = KIND_COLORS[span.span_kind] ?? '#4A5568'
          const truncLabel = span.name.length > 14 ? span.name.slice(0, 13) + '…' : span.name

          return (
            <div key={span.span_id} style={{
              display: 'flex', alignItems: 'center', height: ROW_H,
              opacity: reached ? 1 : 0.3, transition: 'opacity 0.15s',
            }}>
              <div style={{
                width: LABEL_W, flexShrink: 0, paddingLeft: 8 + (depthMap.get(span.span_id) ?? 0) * 10, paddingRight: 6,
                fontSize: 10, fontFamily: 'monospace', color: 'var(--color-muted)',
                overflow: 'hidden', whiteSpace: 'nowrap', textAlign: 'right',
              }}>
                {truncLabel}
              </div>
              <div style={{ flex: 1, position: 'relative', height: '100%' }}>
                <div style={{
                  position: 'absolute',
                  left: `${leftPct}%`,
                  width: `max(${widthPct}%, 2px)`,
                  top: '25%', height: '50%',
                  background: color,
                  borderRadius: 2,
                  opacity: 0.75,
                }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Scrubber */}
      <div style={{ padding: '8px 12px', borderTop: '1px solid var(--color-border)', flexShrink: 0 }}>
        <div
          ref={trackRef}
          onMouseDown={onTrackMouseDown}
          style={{
            position: 'relative', height: 12, borderRadius: 6,
            background: 'rgba(255,255,255,0.05)', cursor: 'crosshair',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{
            position: 'absolute', left: 0, top: 0, bottom: 0,
            width: `${playhead * 100}%`,
            background: 'linear-gradient(90deg, rgba(0,212,255,0.3), rgba(0,212,255,0.1))',
            borderRadius: 6,
          }} />
          <div style={{
            position: 'absolute', top: '50%', left: `${playhead * 100}%`,
            transform: 'translate(-50%, -50%)',
            width: 14, height: 14, borderRadius: '50%',
            background: '#00D4FF',
            boxShadow: '0 0 8px rgba(0,212,255,0.6)',
            cursor: 'grab', pointerEvents: 'none',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          {[0, 0.25, 0.5, 0.75, 1].map(t => (
            <span key={t} style={{ fontSize: 9, fontFamily: 'monospace', color: 'var(--color-muted)' }}>
              {formatNs(t * totalNs)}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TraceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [spans, setSpans] = useState<Span[]>([])
  const [violations, setViolations] = useState<Violation[]>([])
  const [selected, setSelected] = useState<Span | null>(null)

  useEffect(() => {
    api.traces.get(id).then(data => {
      setSpans(data)
      if (data.length) setSelected(data[0])
    })
    api.violations.list({ limit: 100 }).then(all =>
      setViolations(all.filter(v => v.trace_id === id))
    )
  }, [id])

  const spanViolations = (spanId: string) => violations.filter(v => v.span_id === spanId)

  return (
    <div style={{
      padding: '16px 24px', height: '100vh', display: 'flex', flexDirection: 'column',
      boxSizing: 'border-box', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{ marginBottom: 12, flexShrink: 0 }}>
        <h1 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>Trace</h1>
        <p style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--color-cyan)', margin: '2px 0 0' }}>{id}</p>
      </div>

      {/* Main 3-panel layout */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>

        {/* Left 45%: DAG */}
        <div style={{
          width: '45%', flexShrink: 0,
          border: '1px solid var(--color-border)', borderRadius: 8,
          background: 'rgba(13,21,38,0.3)', display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
            <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--color-muted)', fontWeight: 600, letterSpacing: 1 }}>
              {spans.length} SPANS — DAG VIEW
            </span>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <DagGraph spans={spans} selected={selected} violations={violations} onSelect={setSelected} />
          </div>
        </div>

        {/* Right 55%: inspector + timeline */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* Attribute inspector: top 55% */}
          <div style={{
            flex: '0 0 55%', minHeight: 0,
            border: '1px solid var(--color-border)', borderRadius: 8,
            background: 'rgba(13,21,38,0.3)', overflow: 'auto',
          }}>
            {selected ? (
              <div style={{ padding: 16 }}>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <KindBadge kind={selected.span_kind} />
                    <h2 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>{selected.name}</h2>
                  </div>
                  <p style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--color-muted)', margin: 0 }}>
                    {selected.span_id}
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
                  {(
                    [
                      ['trace_id', selected.trace_id],
                      ['span_kind', selected.span_kind],
                      ['service', selected.service_name],
                      ['duration', `${selected.duration_ms.toFixed(2)}ms`],
                      ['status', selected.status_code],
                      ['gen_ai.system', selected.gen_ai_system],
                      ['gen_ai.operation', selected.gen_ai_operation],
                      ['input_tokens', selected.gen_ai_input_tokens],
                      ['output_tokens', selected.gen_ai_output_tokens],
                      ['tool', selected.gen_ai_tool_name],
                    ] as [string, unknown][]
                  ).filter(([, v]) => v !== null && v !== undefined).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', gap: 12, fontSize: 11 }}>
                      <span style={{ fontFamily: 'monospace', color: 'var(--color-muted)', width: 120, flexShrink: 0 }}>{k}</span>
                      <span style={{ fontFamily: 'monospace', color: 'var(--color-text)', wordBreak: 'break-all' }}>{String(v)}</span>
                    </div>
                  ))}
                </div>

                {spanViolations(selected.span_id).map(v => (
                  <div key={v.id} style={{
                    border: '1px solid rgba(252,129,129,0.3)', background: 'rgba(252,129,129,0.05)',
                    borderRadius: 6, padding: '10px 12px', marginBottom: 8,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--color-red)' }}>{v.rule_id}</span>
                      {v.blocked && (
                        <span style={{
                          fontSize: 10, background: 'rgba(252,129,129,0.2)',
                          color: 'var(--color-red)', padding: '1px 6px', borderRadius: 3, fontFamily: 'monospace',
                        }}>
                          BLOCKED
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: 11, color: 'var(--color-muted)', margin: '0 0 4px' }}>{v.description}</p>
                    {v.evidence && (
                      <p style={{
                        fontSize: 10, fontFamily: 'monospace', color: 'var(--color-muted)',
                        background: 'rgba(8,12,24,0.5)', padding: '4px 6px', borderRadius: 3,
                        margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {v.evidence}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-muted)', fontSize: 13 }}>
                Select a span to inspect
              </div>
            )}
          </div>

          {/* Episode Replay Timeline: bottom 45% */}
          <div style={{
            flex: 1, minHeight: 0,
            border: '1px solid var(--color-border)', borderRadius: 8,
            background: 'rgba(13,21,38,0.3)', overflow: 'hidden',
          }}>
            <EpisodeTimeline spans={spans} />
          </div>
        </div>
      </div>
    </div>
  )
}
