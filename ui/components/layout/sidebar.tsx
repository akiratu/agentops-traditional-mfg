'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AlertTriangle, Factory, FileUp, GitCompare } from 'lucide-react'
import { cn } from '@/lib/utils'

const items = [
  { href: '/factories', label: '工廠 Factories', icon: Factory },
  { href: '/anomalies', label: '異常 Anomalies', icon: AlertTriangle },
  { href: '/regression-runs', label: '回歸測試 Regression Runs', icon: GitCompare },
  { href: '/sop-upload', label: 'SOP 上傳', icon: FileUp },
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
    </aside>
  )
}
