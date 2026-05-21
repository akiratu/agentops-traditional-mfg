'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { StatusBadge } from './status-badge'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import { relativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { SkillRead, UUID } from '@/lib/types'

type Props = {
  agentId: UUID
  skills: SkillRead[]
  selectedIds: Set<UUID>
  onToggle: (id: UUID) => void
}

export function SkillTimeline({ agentId, skills, selectedIds, onToggle }: Props) {
  const qc = useQueryClient()
  const promote = useMutation({
    mutationFn: (id: UUID) => api.patchSkillStatus(id, { status: 'active' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.skills(agentId) })
      void qc.invalidateQueries({ queryKey: qk.agent(agentId) })
      toast.success('Promoted to ACTIVE — prior active will archive shortly')
    },
    onError: (err) => toast.error(`Promote failed: ${(err as Error).message}`),
  })

  return (
    <ol className="flex flex-col gap-2">
      {[...skills]
        .sort((a, b) => b.version - a.version)
        .map((s) => {
          const isSelected = selectedIds.has(s.id)
          const disabledForSelect = !isSelected && selectedIds.size >= 2
          return (
            <li
              key={s.id}
              className={cn(
                'flex flex-col gap-1.5 rounded border bg-background p-3',
                s.status === 'active'
                  ? 'border-green-400 ring-1 ring-green-200'
                  : 'border-border',
                isSelected && 'ring-2 ring-blue-300'
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    aria-label={`Select v${s.version} for diff`}
                    checked={isSelected}
                    disabled={disabledForSelect}
                    onChange={() => onToggle(s.id)}
                    className="h-3.5 w-3.5"
                  />
                  <span className="text-sm font-medium">v{s.version}</span>
                  <StatusBadge status={s.status} />
                  {s.status === 'active' && (
                    <span className="text-[11px] font-medium text-green-700">current</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-muted-foreground">
                    {relativeTime(s.created_at)}
                  </span>
                  {s.status === 'draft' && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 px-2 text-[11px]"
                      onClick={() => promote.mutate(s.id)}
                      disabled={promote.isPending}
                      data-testid={`promote-${s.version}`}
                    >
                      Promote to ACTIVE
                    </Button>
                  )}
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground">
                set: {s.sop_source_set_id} · run: {s.generated_by_run_id ?? '—'}
              </div>
              <pre className="line-clamp-2 whitespace-pre-wrap text-[11px] text-muted-foreground">
                {s.prompt.slice(0, 160)}
                {s.prompt.length > 160 && '…'}
              </pre>
            </li>
          )
        })}
    </ol>
  )
}
