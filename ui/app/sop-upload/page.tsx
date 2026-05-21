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
      if (!selectedAgent) throw new Error('Select an agent first')
      if (files.length === 0) throw new Error('Attach at least one SOP file')
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
      toast.success(`Skill v${skill.version} generated`)
      router.push(`/skills/${skill.agent_id}`)
    },
    onError: (err) => toast.error((err as Error).message),
  })

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <BreadcrumbNav crumbs={[{ label: 'SOP Upload' }]} />
      <h1 className="text-xl font-semibold">Upload SOPs → Generate Skill</h1>

      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          Step 1: Pick Agent
        </label>
        <Select value={agentId} onValueChange={(v) => setAgentId(v as UUID)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="Select an agent" />
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
          Step 2: SOP files
        </label>
        <SopDropzone files={files} onChange={setFiles} disabled={submit.isPending} />
      </section>

      <section>
        <label className="mb-1 block text-xs font-medium uppercase text-muted-foreground">
          Step 3: Strategy
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
              Mining <span className="text-muted-foreground">(recommended, traceable)</span>
            </span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={strategy === 'single'}
              onChange={() => setStrategy('single')}
              disabled={submit.isPending}
            />
            <span>Single</span>
          </label>
        </div>
      </section>

      <div>
        <Button
          type="button"
          onClick={() => submit.mutate()}
          disabled={submit.isPending || !agentId || files.length === 0}
          data-testid="sop-submit"
        >
          {submit.isPending ? 'Generating… (1–3 min)' : 'Upload + Generate Skill'}
        </Button>
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
