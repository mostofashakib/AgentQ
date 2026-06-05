const severity_colors: Record<string, string> = {
  critical: 'bg-red/20 text-red border-red/30',
  high: 'bg-red/10 text-red/80 border-red/20',
  medium: 'bg-amber/10 text-amber border-amber/20',
  low: 'bg-muted/10 text-muted border-muted/20',
}

const threat_colors: Record<string, string> = {
  injection: 'bg-purple-900/30 text-purple-300 border-purple-700/30',
  exfiltration: 'bg-red/10 text-red border-red/20',
  scope: 'bg-amber/10 text-amber border-amber/20',
  behavioral: 'bg-blue-900/30 text-blue-300 border-blue-700/30',
  integrity: 'bg-muted/10 text-muted border-muted/20',
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono border ${severity_colors[severity] ?? 'bg-muted/10 text-muted'}`}>
      {severity}
    </span>
  )
}

export function ThreatBadge({ threat }: { threat: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono border ${threat_colors[threat] ?? 'bg-muted/10 text-muted'}`}>
      {threat}
    </span>
  )
}

export function KindBadge({ kind }: { kind: string }) {
  const colors: Record<string, string> = {
    SERVER: 'text-cyan border-cyan/20 bg-cyan/5',
    INTERNAL: 'text-amber border-amber/20 bg-amber/5',
    CLIENT: 'text-green border-green/20 bg-green/5',
  }
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono border ${colors[kind] ?? 'text-muted border-border'}`}>
      {kind}
    </span>
  )
}
