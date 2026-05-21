import { Loader2 } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { AnomalyStatus, RCAFindingStatus, SkillStatus } from '@/lib/types'

type Status = AnomalyStatus | RCAFindingStatus | SkillStatus

const STYLES: Record<Status, string> = {
  // anomaly
  new: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  analyzing: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  dismissed: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
  // finding
  proposed: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  accepted: 'bg-green-200 text-green-900 dark:bg-green-900/40 dark:text-green-200',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  auto_applied: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  // skill
  draft: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  archived: 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-500',
}

const EXPLANATIONS: Record<Status, string> = {
  // anomaly status — 異常從進來到處理完
  new: '剛偵測到的異常,還沒分析。',
  analyzing: 'AI 正在跑根因分析(1-3 分鐘),分析完會自動轉到 resolved。',
  resolved: '分析完成,有 RCA finding 可以看。點異常卡片進去看內容。',
  dismissed: '主管判定不需處理 / 誤報,已關閉。',
  // RCAFinding status — 主管對 AI 分析結果的決策
  proposed: 'AI 已產出 finding,等主管 Accept(接受並啟動 Self-Evolve)或 Reject(拒絕)。',
  accepted: '主管已接受,系統正在跑或已跑完 Self-Evolve 產出新版 skill。',
  rejected: '主管判定這個 finding 不對,不採用。',
  auto_applied: '系統自動處理(配合自動化規則,非主流路徑)。',
  // Skill status — 技能版本生命週期
  draft: '草稿版本,還沒被升為 ACTIVE。Self-Evolve 剛產出的 v_next 預設都是 draft。',
  active: '當前生效版本,Agent runtime 用這個。同 agent 同時只有一個 ACTIVE。',
  archived: '已歸檔的舊版,被新版取代後保留作歷史記錄,不再使用。',
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            data-status={status}
            className={cn(
              'inline-flex cursor-help items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
              STYLES[status]
            )}
          >
            {status === 'analyzing' && <Loader2 size={10} className="animate-spin" aria-hidden />}
            {status}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="start" className="max-w-xs text-left">
          <p className="text-xs leading-relaxed">{EXPLANATIONS[status]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
