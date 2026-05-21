export type NotebookSection = 'found' | 'hypothesis' | 'todo' | 'excluded'

// Maps the literal markdown heading prefix → section key.
// Agent always uses these emoji-prefixed headers per trace_analyzer/notebook.py.
const HEADERS: Array<[string, NotebookSection]> = [
  ['## 🔍', 'found'],
  ['## 💡', 'hypothesis'],
  ['## ❓', 'todo'],
  ['## 🚫', 'excluded'],
]

export function parseNotebook(markdown: string): Record<NotebookSection, string> {
  const result: Record<NotebookSection, string> = {
    found: '',
    hypothesis: '',
    todo: '',
    excluded: '',
  }
  if (!markdown) return result

  // Find header positions in order of appearance.
  const positions: Array<{ section: NotebookSection; start: number }> = []
  for (const [prefix, section] of HEADERS) {
    const idx = markdown.indexOf(prefix)
    if (idx >= 0) positions.push({ section, start: idx })
  }
  positions.sort((a, b) => a.start - b.start)

  for (let i = 0; i < positions.length; i++) {
    const cur = positions[i]
    const next = positions[i + 1]
    if (!cur) continue
    const slice = markdown.slice(cur.start, next?.start ?? markdown.length)
    // Drop the first line (the heading itself).
    const newline = slice.indexOf('\n')
    const body = newline >= 0 ? slice.slice(newline + 1).trim() : ''
    result[cur.section] = body
  }
  return result
}
