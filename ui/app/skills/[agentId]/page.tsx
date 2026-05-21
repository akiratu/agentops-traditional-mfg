'use client'

import { use, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { DataState } from '@/components/layout/data-state'
import { SkillTimeline } from '@/components/domain/skill-timeline'
import { SkillDiff } from '@/components/domain/skill-diff'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import type { SkillRead, UUID } from '@/lib/types'

export default function SkillTimelinePage({
  params,
}: {
  params: Promise<{ agentId: string }>
}) {
  const { agentId } = use(params)
  const [selected, setSelected] = useState<Set<UUID>>(new Set())

  const skillsQ = useQuery({
    queryKey: qk.skills(agentId),
    queryFn: () => api.listSkills(agentId),
    refetchInterval: 10_000,
  })

  // Auto-select latest two on first load.
  useEffect(() => {
    if (selected.size > 0) return
    if (!skillsQ.data) return
    const sorted = [...skillsQ.data].sort((a, b) => b.version - a.version)
    const top = sorted.slice(0, 2).map((s) => s.id)
    if (top.length === 2) setSelected(new Set(top))
  }, [skillsQ.data, selected.size])

  const toggle = (id: UUID) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else if (next.size < 2) next.add(id)
      return next
    })
  }

  const selectedSkills =
    skillsQ.data?.filter((s) => selected.has(s.id)).sort((a, b) => a.version - b.version) ?? []
  const [older, newer] = selectedSkills as [SkillRead | undefined, SkillRead | undefined]

  return (
    <div className="flex flex-col gap-4">
      <BreadcrumbNav
        crumbs={[
          { href: '/factories', label: 'Factories' },
          { href: `/agents/${agentId}`, label: 'Agent' },
          { label: 'Skills' },
        ]}
      />
      <h1 className="text-xl font-semibold">Skill Timeline</h1>
      <DataState query={skillsQ} isEmpty={(d) => d.length === 0}>
        {(skills) => (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
            <SkillTimeline
              agentId={agentId}
              skills={skills}
              selectedIds={selected}
              onToggle={toggle}
            />
            <div className="rounded border border-border">
              <div className="border-b border-border px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Diff {older && newer ? `v${older.version} → v${newer.version}` : '(select 2 versions)'}
              </div>
              {older && newer ? (
                <SkillDiff
                  oldPrompt={older.prompt}
                  newPrompt={newer.prompt}
                  oldLabel={`v${older.version} (${older.status})`}
                  newLabel={`v${newer.version} (${newer.status})`}
                />
              ) : (
                <p className="p-card text-xs text-muted-foreground">
                  Tick the checkbox on two versions on the left to compare.
                </p>
              )}
            </div>
          </div>
        )}
      </DataState>
    </div>
  )
}
