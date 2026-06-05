'use client'

interface Props {
  label: string
  value: number | null
  color?: string
}

export function EvalGauge({ label, value, color = '#00D4FF' }: Props) {
  const pct = value ?? 0
  const r = 36
  const circ = 2 * Math.PI * r
  const arc = circ * 0.75
  const offset = arc - arc * pct
  const rotate = -225

  const statusColor = pct >= 0.8 ? '#22C55E' : pct >= 0.5 ? '#F59E0B' : '#EF4444'
  const displayColor = value === null ? '#1E2A3A' : statusColor

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={100} height={80} viewBox="0 0 100 80">
        <circle cx={50} cy={55} r={r} fill="none" stroke="#1E2A3A" strokeWidth={6}
          strokeDasharray={`${arc} ${circ}`} strokeLinecap="round"
          style={{ transform: `rotate(${rotate}deg)`, transformOrigin: '50px 55px' }} />
        <circle cx={50} cy={55} r={r} fill="none" stroke={displayColor} strokeWidth={6}
          strokeDasharray={`${arc - offset} ${circ}`} strokeLinecap="round"
          style={{ transform: `rotate(${rotate}deg)`, transformOrigin: '50px 55px', transition: 'stroke-dasharray 0.6s ease' }} />
        <text x={50} y={52} textAnchor="middle" fill={value === null ? '#64748B' : displayColor}
          fontSize={16} fontFamily="IBM Plex Mono" fontWeight={500}>
          {value === null ? 'N/A' : `${Math.round(pct * 100)}%`}
        </text>
      </svg>
      <span className="text-xs text-muted font-mono">{label}</span>
    </div>
  )
}
