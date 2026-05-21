'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BreadcrumbNav } from '@/components/layout/breadcrumb-nav'
import { SopDropzone, type StagedFile } from '@/components/domain/sop-dropzone'
import { api } from '@/lib/api'
import { qk } from '@/lib/query-keys'
import type { AgentRead, SOPSourceType, UUID } from '@/lib/types'

export default function SopUploadPage() {
  const router = useRouter()
  const [agentId, setAgentId] = useState<UUID | ''>('')
  const [strategy, setStrategy] = useState<'mining' | 'single'>('mining')
  const [files, setFiles] = useState<StagedFile[]>([])

  const agentsQ = useQuery({ queryKey: qk.agents(), queryFn: () => api.listAgents() })
  const selectedAgent: AgentRead | undefined = agentsQ.data?.find((a) => a.id === agentId)

  const submit = useMutation({
    mutationFn: async () => {
      if (!selectedAgent) throw new Error('請先選擇 Agent')
      if (files.length === 0) throw new Error('請至少附一個 SOP 檔案')
      const uploaded = await Promise.all(
        files.map(({ file }) =>
          api.uploadSOP(selectedAgent.factory_id, file, inferType(file.name))
        )
      )
      const skill = await api.generateSkill({
        agent_id: selectedAgent.id,
        sop_source_ids: uploaded.map((u) => u.id),
        strategy,
      })
      return skill
    },
    onSuccess: (skill) => {
      toast.success(`已產生 Skill v${skill.version}`)
      router.push(`/skills/${skill.agent_id}`)
    },
    onError: (err) => toast.error((err as Error).message),
  })

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'SOP Upload' }]} />
      <h1 className="text-xl font-semibold">上傳 SOP 產生技能 Upload SOPs</h1>

      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          步驟 1: 選擇 Agent
        </label>
        <Select value={agentId} onValueChange={(v) => setAgentId(v as UUID)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="選擇一個 Agent" />
          </SelectTrigger>
          <SelectContent>
            {agentsQ.data?.map((a) => (
              <SelectItem key={a.id} value={a.id} className="text-xs">
                {a.name} ({a.purpose.slice(0, 40)})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </section>

      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          步驟 2: SOP 檔案
        </label>
        <SopDropzone files={files} onChange={setFiles} disabled={submit.isPending} />
      </section>

      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          步驟 3: 產生策略
        </label>
        <div className="flex items-center gap-4 text-xs">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={strategy === 'mining'}
              onChange={() => setStrategy('mining')}
              disabled={submit.isPending}
            />
            <span>
              Mining 探勘 <span className="text-muted-foreground">(推薦,可追溯)</span>
            </span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={strategy === 'single'}
              onChange={() => setStrategy('single')}
              disabled={submit.isPending}
            />
            <span>Single 單次</span>
          </label>
        </div>
      </section>

      <div className="flex flex-col gap-1">
        <Button
          type="button"
          onClick={() => submit.mutate()}
          disabled={submit.isPending || !agentId || files.length === 0}
          data-testid="sop-submit"
        >
          {submit.isPending ? '產生中… (1-3 分鐘)' : '上傳並產生技能'}
        </Button>
        {(() => {
          if (submit.isPending) return null
          const missing: string[] = []
          if (!agentId) missing.push('選擇 Agent(步驟 1)')
          if (files.length === 0) missing.push('附至少 1 個 SOP 檔(步驟 2)')
          if (missing.length === 0) {
            return (
              <p className="text-xs text-muted-foreground">
                按下後 Gemini Pro 開始 mining,約 2-3 分鐘產出新版 skill,完成後自動跳轉
              </p>
            )
          }
          return (
            <p className="text-xs text-amber-700 dark:text-amber-400">
              ⚠ 還需要:{missing.join(' + ')}
            </p>
          )
        })()}
      </div>
    </div>
  )
}

function inferType(name: string): SOPSourceType {
  const lower = name.toLowerCase()
  if (lower.endsWith('.pdf')) return 'pdf'
  if (lower.endsWith('.docx')) return 'transcript'
  if (lower.endsWith('.xlsx') || lower.endsWith('.csv')) return 'table'
  return 'case_library'
}
