'use client'

import { HelpCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

/**
 * Small inline "?" icon that reveals an explanation on hover (or focus, for
 * keyboard users; or tap, for touch). Use next to technical labels —
 * "來源 SOURCE", "信心分數", status enum values — so non-technical viewers
 * (主管 / 政府評審 / 場域工廠) can self-serve definitions without asking.
 *
 * Pass JSX as `children` for multi-line explanations:
 *   <InfoHint>
 *     <ul className="text-xs">
 *       <li>Metric drift — 自動偵測指標偏離</li>
 *       ...
 *     </ul>
 *   </InfoHint>
 */
export function InfoHint({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="說明"
            className={
              'inline-flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-ring ' +
              (className ?? '')
            }
          >
            <HelpCircle size={12} aria-hidden />
          </button>
        </TooltipTrigger>
        <TooltipContent
          side="bottom"
          align="start"
          className="max-w-sm whitespace-normal text-left"
        >
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
