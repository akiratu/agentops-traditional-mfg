'use client'

import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { Fragment } from 'react'

export type Crumb = { href?: string; label: string }

export function BreadcrumbNav({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 text-xs text-zinc-500 dark:text-zinc-400"
    >
      {crumbs.map((c, idx) => (
        <Fragment key={`${c.label}-${idx}`}>
          {idx > 0 && <ChevronRight size={12} aria-hidden />}
          {c.href ? (
            <Link href={c.href} className="hover:text-zinc-900 dark:hover:text-zinc-100">
              {c.label}
            </Link>
          ) : (
            <span className="text-zinc-700 dark:text-zinc-200">{c.label}</span>
          )}
        </Fragment>
      ))}
    </nav>
  )
}
