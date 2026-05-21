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
import type { AgentRead, FactoryRead, SOPSourceType, UUID } from '@/lib/types'

type Mode = 'single' | 'portfolio'

export default function SopUploadPage() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>('single')

  // single mode state
  const [agentId, setAgentId] = useState<UUID | ''>('')
  const [strategy, setStrategy] = useState<'mining' | 'single'>('mining')

  // portfolio mode state
  const [factoryId, setFactoryId] = useState<UUID | ''>('')
  const [description, setDescription] = useState('')

  // shared
  const [files, setFiles] = useState<StagedFile[]>([])

  const agentsQ = useQuery({ queryKey: qk.agents(), queryFn: () => api.listAgents() })
  const factoriesQ = useQuery({
    queryKey: qk.factories(),
    queryFn: () => api.listFactories(),
  })
  const selectedAgent: AgentRead | undefined = agentsQ.data?.find((a) => a.id === agentId)
  const selectedFactory: FactoryRead | undefined = factoriesQ.data?.find((f) => f.id === factoryId)

  const submitSingle = useMutation({
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

  const submitPortfolio = useMutation({
    mutationFn: async () => {
      if (!selectedFactory) throw new Error('請先選擇 Factory')
      if (files.length === 0) throw new Error('請至少附一個 SOP 檔案')
      if (description.trim().length < 5) throw new Error('請填寫此工廠的範圍說明(至少 5 字)')
      const uploaded = await Promise.all(
        files.map(({ file }) =>
          api.uploadSOP(selectedFactory.id, file, inferType(file.name))
        )
      )
      const result = await api.generatePortfolio({
        factory_id: selectedFactory.id,
        sop_source_ids: uploaded.map((u) => u.id),
        description: description.trim(),
      })
      return result
    },
    onSuccess: (result) => {
      const totalSkills = result.agents.reduce((sum, a) => sum + a.skill_ids.length, 0)
      toast.success(`已產生 ${result.agents.length} 個 Agent · ${totalSkills} 個 Skill`)
      // Land on the factory detail page where the new agents will appear in the table.
      router.push(`/factories/${selectedFactory!.id}`)
    },
    onError: (err) => toast.error((err as Error).message),
  })

  const isPending = submitSingle.isPending || submitPortfolio.isPending
  const handleSubmit = () => {
    if (mode === 'single') submitSingle.mutate()
    else submitPortfolio.mutate()
  }

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'SOP Upload' }]} />
      <h1 className="text-xl font-semibold">上傳 SOP 產生技能 Upload SOPs</h1>

      {/* Mode toggle */}
      <section className="rounded border border-border bg-muted/40 p-3">
        <label className="mb-2 block text-xs font-medium uppercase text-muted-foreground">
          模式 Mode
        </label>
        <div className="flex flex-col gap-2 text-xs">
          <label className="flex items-start gap-2">
            <input
              type="radio"
              checked={mode === 'single'}
              onChange={() => setMode('single')}
              disabled={isPending}
              className="mt-0.5"
            />
            <div>
              <div className="font-medium">
                升級現有 Agent <span className="text-muted-foreground">(Single skill)</span>
              </div>
              <div className="text-muted-foreground">
                選一個既有 agent,從 SOP 挖出新版 skill 加進它的版本歷史。常用於日常技能擴充。
              </div>
            </div>
          </label>
          <label className="flex items-start gap-2">
            <input
              type="radio"
              checked={mode === 'portfolio'}
              onChange={() => setMode('portfolio')}
              disabled={isPending}
              className="mt-0.5"
            />
            <div>
              <div className="font-medium">
                從 SOP 自動造 Agent 群 <span className="text-muted-foreground">(Portfolio)</span>
              </div>
              <div className="text-muted-foreground">
                Gemini 分析 SOP 後自動決定要切成幾個 agent,每個 agent 各自挖出一套 skill。新場域初次上線時用。
              </div>
            </div>
          </label>
        </div>
      </section>

      {/* Mode-specific Step 1 */}
      {mode === 'single' ? (
        <section>
          <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
            步驟 1: 選擇 Agent
          </label>
          <Select value={agentId} onValueChange={(v) => setAgentId(v as UUID)} disabled={isPending}>
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
      ) : (
        <section>
          <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
            步驟 1: 選擇 Factory(新 agent 們會掛在這個工廠下)
          </label>
          <Select
            value={factoryId}
            onValueChange={(v) => setFactoryId(v as UUID)}
            disabled={isPending}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="選擇一個 Factory" />
            </SelectTrigger>
            <SelectContent>
              {factoriesQ.data?.map((f) => (
                <SelectItem key={f.id} value={f.id} className="text-xs">
                  {f.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </section>
      )}

      {/* Step 2 — SOP files */}
      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          步驟 2: SOP 檔案
        </label>
        <SopDropzone files={files} onChange={setFiles} disabled={isPending} />
      </section>

      {/* Step 3 — mode-specific */}
      {mode === 'single' ? (
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
                disabled={isPending}
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
                disabled={isPending}
              />
              <span>Single 單次</span>
            </label>
          </div>
        </section>
      ) : (
        <section>
          <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
            步驟 3: 工廠範圍說明(給 Gemini 切分用)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isPending}
            rows={3}
            placeholder="例:CNC 精密加工廠,涵蓋刀具壽命監控、熱變形補償、換班程式管理、材料批次差異。請依這幾個面向自動切分 agent。"
            className="w-full rounded border border-border bg-background p-2 text-xs"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            這段描述會跟 SOP 一起餵給 Gemini,讓它知道「這個工廠在做什麼」,才能合理切出 agent。
          </p>
        </section>
      )}

      <div className="flex flex-col gap-1">
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={
            isPending ||
            files.length === 0 ||
            (mode === 'single' ? !agentId : !factoryId || description.trim().length < 5)
          }
          data-testid="sop-submit"
        >
          {isPending
            ? mode === 'single'
              ? '產生中… (1-3 分鐘)'
              : '產生中… (5-10 分鐘)'
            : mode === 'single'
              ? '上傳並產生技能'
              : '上傳並產生 Agent 群'}
        </Button>
        {(() => {
          if (isPending) return null
          const missing: string[] = []
          if (mode === 'single') {
            if (!agentId) missing.push('選擇 Agent(步驟 1)')
            if (files.length === 0) missing.push('附至少 1 個 SOP 檔(步驟 2)')
          } else {
            if (!factoryId) missing.push('選擇 Factory(步驟 1)')
            if (files.length === 0) missing.push('附至少 1 個 SOP 檔(步驟 2)')
            if (description.trim().length < 5) missing.push('填工廠範圍說明(步驟 3)')
          }
          if (missing.length === 0) {
            return (
              <p className="text-xs text-muted-foreground">
                {mode === 'single'
                  ? '按下後 Gemini Pro 開始 mining,約 2-3 分鐘產出新版 skill,完成後自動跳轉技能版本演進頁'
                  : '按下後 Gemini Pro 開始分析,5-10 分鐘可能產出 2-5 個 agent + 對應 skill,完成後自動跳轉工廠詳情頁'}
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
