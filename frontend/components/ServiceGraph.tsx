// frontend/components/ServiceGraph.tsx
'use client'
import { useEffect, useState } from 'react'
import type { GraphNode, GraphEdge } from '@/lib/api'

interface NodePos { id: string; x: number; y: number; vx: number; vy: number; node: GraphNode }

function useForceLayout(nodes: GraphNode[], edges: GraphEdge[], w: number, h: number) {
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(() => {
    const map = new Map<string, { x: number; y: number }>()
    nodes.forEach((n, i) => {
      const angle = (i / Math.max(nodes.length, 1)) * 2 * Math.PI
      map.set(n.id, { x: w / 2 + Math.cos(angle) * 160, y: h / 2 + Math.sin(angle) * 120 })
    })
    return map
  })

  useEffect(() => {
    if (!nodes.length) return
    const state: NodePos[] = nodes.map((n, i) => {
      const angle = (i / Math.max(nodes.length, 1)) * 2 * Math.PI
      const existing = positions.get(n.id)
      return {
        id: n.id,
        x: existing?.x ?? w / 2 + Math.cos(angle) * 160,
        y: existing?.y ?? h / 2 + Math.sin(angle) * 120,
        vx: 0, vy: 0,
        node: n,
      }
    })

    let frame: number
    const ITERATIONS = 120
    let tick = 0

    function step() {
      tick++
      const alpha = Math.max(0.01, 1 - tick / ITERATIONS)

      // Repulsion
      for (let i = 0; i < state.length; i++) {
        for (let j = i + 1; j < state.length; j++) {
          const dx = state[i].x - state[j].x
          const dy = state[i].y - state[j].y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = (3000 / (dist * dist)) * alpha
          state[i].vx += (dx / dist) * force
          state[i].vy += (dy / dist) * force
          state[j].vx -= (dx / dist) * force
          state[j].vy -= (dy / dist) * force
        }
      }

      // Attraction along edges
      const idxMap = new Map(state.map((n, i) => [n.id, i]))
      for (const e of edges) {
        const a = state[idxMap.get(e.source) ?? 0]
        const b = state[idxMap.get(e.target) ?? 0]
        if (!a || !b) continue
        const dx = b.x - a.x
        const dy = b.y - a.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = ((dist - 120) / dist) * 0.4 * alpha
        a.vx += dx * force; a.vy += dy * force
        b.vx -= dx * force; b.vy -= dy * force
      }

      // Center gravity
      for (const n of state) {
        n.vx += (w / 2 - n.x) * 0.02 * alpha
        n.vy += (h / 2 - n.y) * 0.02 * alpha
        n.x += n.vx * 0.9
        n.y += n.vy * 0.9
        n.vx *= 0.7
        n.vy *= 0.7
        n.x = Math.max(40, Math.min(w - 40, n.x))
        n.y = Math.max(30, Math.min(h - 30, n.y))
      }

      const map = new Map(state.map(n => [n.id, { x: n.x, y: n.y }]))
      setPositions(new Map(map))

      if (tick < ITERATIONS) frame = requestAnimationFrame(step)
    }

    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length, edges.length, w, h])

  return positions
}

export function ServiceGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const W = 700
  const H = 440
  const positions = useForceLayout(nodes, edges, W, H)
  const maxCount = Math.max(...nodes.map(n => n.span_count), 1)
  const maxCalls = Math.max(...edges.map(e => e.call_count), 1)

  if (!nodes.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: H, color: 'var(--color-muted)', fontSize: 13 }}>
        No trace data yet. Send spans to see the service graph.
      </div>
    )
  }

  return (
    <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
      {/* Edges */}
      {edges.map(e => {
        const src = positions.get(e.source)
        const dst = positions.get(e.target)
        if (!src || !dst) return null
        const thickness = 1 + (e.call_count / maxCalls) * 3
        return (
          <line
            key={`${e.source}-${e.target}`}
            x1={src.x} y1={src.y} x2={dst.x} y2={dst.y}
            stroke="rgba(0,212,255,0.25)" strokeWidth={thickness}
          />
        )
      })}

      {/* Nodes */}
      {nodes.map(n => {
        const pos = positions.get(n.id)
        if (!pos) return null
        const r = 12 + (n.span_count / maxCount) * 16
        const label = n.operation.length > 16 ? n.operation.slice(0, 15) + '…' : n.operation
        return (
          <g key={n.id}>
            <circle cx={pos.x} cy={pos.y} r={r} fill="#0D1526" stroke="#00D4FF" strokeWidth={1.5} opacity={0.9} />
            <text x={pos.x} y={pos.y + 4} textAnchor="middle" fontSize={9} fontFamily="monospace" fill="#00D4FF">
              {label}
            </text>
            <text x={pos.x} y={pos.y + r + 12} textAnchor="middle" fontSize={9} fontFamily="monospace" fill="var(--color-muted)">
              {n.service_name}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
