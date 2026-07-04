'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, AlertTriangle, Bell, GitBranch, Layers, Plug, Radio } from 'lucide-react'

const nav = [
  { href: '/connect', label: 'Connect Agent', icon: Plug },
  { href: '/traces', label: 'Live Traces', icon: Radio },
  { href: '/violations', label: 'Violations', icon: AlertTriangle },
  { href: '/behaviors', label: 'Behaviors', icon: Layers },
  { href: '/alerts', label: 'Alerts', icon: Bell },
  { href: '/graph', label: 'Service Graph', icon: GitBranch },
]

export function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-56 min-h-screen bg-surface border-r border-border flex flex-col">
      <Link href="/traces" className="px-4 py-5 border-b border-border block hover:bg-border/20 transition-colors">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-cyan" />
          <span className="text-sm font-semibold tracking-widest text-cyan font-mono">AGENTQ</span>
        </div>
        <p className="text-xs text-muted mt-1">Observability Platform</p>
      </Link>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path.startsWith(href)
          return (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                active ? 'bg-cyan/10 text-cyan border border-cyan/20' : 'text-muted hover:text-text hover:bg-border/40'
              }`}>
              <Icon size={15} />
              {label}
            </Link>
          )
        })}
      </nav>
      <div className="px-4 py-4 border-t border-border space-y-1.5">
        <Link href="/docs" className="block text-xs text-muted hover:text-cyan transition-colors">
          Documentation
        </Link>
        <a href="https://www.mostofashakib.com" target="_blank" rel="noopener noreferrer"
          className="block text-xs text-muted hover:text-cyan transition-colors">
          Developed by Mostofa Shakib
        </a>
      </div>
    </aside>
  )
}
