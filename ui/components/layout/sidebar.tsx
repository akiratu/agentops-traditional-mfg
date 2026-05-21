'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  AlertTriangle,
  Bot,
  Factory,
  FileUp,
  GitCompare,
  ListChecks,
  Workflow,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const items = [
  { href: '/factories', label: 'Factories', icon: Factory },
  { href: '/anomalies', label: 'Anomalies', icon: AlertTriangle },
  { href: '/regression-runs', label: 'Regression Runs', icon: GitCompare },
  { href: '/sop-upload', label: 'SOP Upload', icon: FileUp },
] as const

const drillDownHints = [
  { href: '/agents', label: 'Agents (via Factory)', icon: Bot },
  { href: '/skills', label: 'Skills (via Agent)', icon: Workflow },
  { href: '/findings', label: 'Findings (via Anomaly)', icon: ListChecks },
] as const

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-muted/40 px-3 py-4">
      <div className="mb-4 px-2 text-base font-semibold">AgentOps</div>
      <nav className="flex flex-col gap-0.5" aria-label="Primary">
        {items.map((it) => {
          const isActive = pathname === it.href || pathname.startsWith(`${it.href}/`)
          const Icon = it.icon
          return (
            <Link
              key={it.href}
              href={it.href}
              className={cn(
                'flex items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-accent font-medium text-accent-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <Icon size={16} aria-hidden />
              {it.label}
            </Link>
          )
        })}
      </nav>

      <div className="mt-6 px-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Drill-down only
      </div>
      <div className="mt-1 flex flex-col gap-0.5">
        {drillDownHints.map((it) => {
          const Icon = it.icon
          return (
            <div
              key={it.href}
              className="flex cursor-not-allowed items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground opacity-60"
              title="Reachable from parent page"
            >
              <Icon size={16} aria-hidden />
              <span>{it.label}</span>
              <span className="sr-only"> — reachable only from parent page</span>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
