"use client";
import Link from "next/link";
import { useState } from "react";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Bell,
  Gauge,
  GitBranch,
  Layers,
  Menu,
  Plug,
  Radio,
  Settings,
  X,
} from "lucide-react";

const nav = [
  { href: "/connect", label: "Agents", icon: Plug },
  { href: "/traces", label: "Traces", icon: Radio },
  { href: "/monitoring", label: "Run Health", icon: Gauge },
  { href: "/violations", label: "Violations", icon: AlertTriangle },
  { href: "/behaviors", label: "Behaviors", icon: Layers },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/graph", label: "Service Graph", icon: GitBranch },
  { href: "/settings", label: "Settings", icon: Settings },
];

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <Activity size={18} className="text-cyan" />
      <span className="text-sm font-semibold tracking-widest text-cyan font-mono">
        AgentQ
      </span>
    </div>
  );
}

function Navigation({
  path,
  onNavigate,
}: {
  path: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 p-3 space-y-1" aria-label="Primary navigation">
      {nav.map(({ href, label, icon: Icon }) => {
        const active = path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              active
                ? "bg-cyan/10 text-cyan border border-cyan/20"
                : "text-muted hover:text-text hover:bg-border/40"
            }`}
          >
            <Icon size={15} aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function DocumentationLink({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="px-4 py-4 border-t border-border">
      <Link
        href="/docs"
        onClick={onNavigate}
        className="block text-xs text-muted hover:text-cyan transition-colors"
      >
        Documentation
      </Link>
    </div>
  );
}

function AttributeLink({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="px-4 py-4 border-t border-border">
      <Link
        href="https://www.mostofashakib.com"
        target="_blank"
        rel="noopener noreferrer"
        onClick={onNavigate}
        className="block text-xs text-muted hover:text-cyan transition-colors"
      >
        Developed by Mostofa Shakib
      </Link>
    </div>
  );
}

export function Sidebar() {
  const path = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <header className="md:hidden fixed inset-x-0 top-0 z-40 h-14 bg-surface border-b border-border flex items-center justify-between px-4">
        <Link href="/traces" onClick={() => setMobileOpen(false)}>
          <Brand />
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
          className="p-2 -mr-2 text-muted hover:text-cyan transition-colors"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-bg/80"
          onClick={() => setMobileOpen(false)}
        >
          <aside
            className="mt-14 w-64 h-[calc(100vh-3.5rem)] bg-surface border-r border-border flex flex-col"
            onClick={(event) => event.stopPropagation()}
          >
            <Navigation path={path} onNavigate={() => setMobileOpen(false)} />
            <DocumentationLink onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <aside className="hidden md:flex w-56 min-h-screen bg-surface border-r border-border flex-col shrink-0">
        <Link
          href="/traces"
          className="px-4 py-5 border-b border-border block hover:bg-border/20 transition-colors"
        >
          <Brand />
        </Link>
        <Navigation path={path} />
        <DocumentationLink />
        <AttributeLink />
      </aside>
    </>
  );
}
