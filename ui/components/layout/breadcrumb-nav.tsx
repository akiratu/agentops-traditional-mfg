'use client'

import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { Fragment } from 'react'

export type Crumb = { href?: string; label: string }

export function BreadcrumbNav({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 text-xs text-muted-foreground"
    >
      {crumbs.map((c, idx) => (
        <Fragment key={`${c.label}-${idx}`}>
          {idx > 0 && <ChevronRight size={12} aria-hidden />}
          {c.href ? (
            <Link href={c.href} className="hover:text-foreground">
              {c.label}
            </Link>
          ) : (
            <span className="text-foreground">{c.label}</span>
          )}
        </Fragment>
      ))}
    </nav>
  )
}
