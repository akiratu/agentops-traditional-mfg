import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import { parseNotebook, type NotebookSection } from '@/lib/parse-notebook'

const CELLS: Array<{
  key: NotebookSection
  title: string
  emoji: string
  border: string
  text: string
}> = [
  { key: 'found', title: '已查到什麼', emoji: '🔍', border: 'border-blue-500', text: 'text-blue-800' },
  { key: 'hypothesis', title: '目前推論', emoji: '💡', border: 'border-amber-500', text: 'text-amber-800' },
  { key: 'todo', title: '還需驗證', emoji: '❓', border: 'border-violet-500', text: 'text-violet-800' },
  { key: 'excluded', title: '已排除', emoji: '🚫', border: 'border-zinc-500', text: 'text-zinc-700' },
]

export function NotebookViewer({ markdown }: { markdown: string }) {
  const sections = parseNotebook(markdown)
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2" data-testid="notebook-viewer">
      {CELLS.map((cell) => {
        const body = sections[cell.key] || '—'
        return (
          <div
            key={cell.key}
            data-testid={`notebook-cell-${cell.key}`}
            className={`border-l-4 ${cell.border} bg-muted/40 p-3`}
          >
            <div className={`text-[11px] font-semibold uppercase tracking-wide ${cell.text}`}>
              {cell.emoji} {cell.title}
            </div>
            <div className="prose prose-sm mt-1 max-w-none text-xs leading-relaxed dark:prose-invert">
              <ReactMarkdown rehypePlugins={[rehypeHighlight]}>{body}</ReactMarkdown>
            </div>
          </div>
        )
      })}
    </div>
  )
}
