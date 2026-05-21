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
  { href: '/factories', label: '工廠 Factories', icon: Factory },
  { href: '/anomalies', label: '異常 Anomalies', icon: AlertTriangle },
  { href: '/regression-runs', label: '回歸測試 Regression Runs', icon: GitCompare },
  { href: '/sop-upload', label: 'SOP 上傳', icon: FileUp },
] as const

const drillDownHints = [
  { href: '/agents', label: 'Agent(從工廠進入)', icon: Bot },
  { href: '/skills', label: 'Skill(從 Agent 進入)', icon: Workflow },
  { href: '/findings', label: 'Finding(從異常進入)', icon: ListChecks },
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
        下層需從上層進入
      </div>
      <div className="mt-1 flex flex-col gap-0.5">
        {drillDownHints.map((it) => {
          const Icon = it.icon
          return (
            <div
              key={it.href}
              className="flex cursor-not-allowed items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground opacity-60"
              title="從上層頁面進入"
            >
              <Icon size={16} aria-hidden />
              <span>{it.label}</span>
              <span className="sr-only"> — 僅能從上層頁面進入</span>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
