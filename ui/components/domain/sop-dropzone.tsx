'use client'

import { useState, type DragEvent, type ChangeEvent } from 'react'
import { Upload, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatBytes } from '@/lib/format'

export type StagedFile = {
  file: File
  id: string // local-only uuid
}

export function SopDropzone({
  files,
  onChange,
  disabled,
}: {
  files: StagedFile[]
  onChange: (files: StagedFile[]) => void
  disabled?: boolean
}) {
  const [dragging, setDragging] = useState(false)

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const incoming = Array.from(e.dataTransfer.files).map((f) => ({
      file: f,
      id: `${f.name}-${f.size}-${f.lastModified}`,
    }))
    onChange([...files, ...incoming])
  }

  const handleSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return
    const incoming = Array.from(e.target.files).map((f) => ({
      file: f,
      id: `${f.name}-${f.size}-${f.lastModified}`,
    }))
    onChange([...files, ...incoming])
    e.target.value = '' // allow re-selecting same file
  }

  const remove = (id: string) => onChange(files.filter((f) => f.id !== id))

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'flex flex-col items-center justify-center gap-2 rounded border border-dashed p-6 text-center text-xs',
          dragging ? 'border-primary bg-primary/5' : 'border-border',
          disabled && 'opacity-50'
        )}
      >
        <Upload size={20} className="text-muted-foreground" />
        <p>拖放 SOP 檔案至此,或點擊選擇</p>
        <label className="cursor-pointer text-primary underline-offset-4 hover:underline">
          選擇檔案
          <input
            type="file"
            multiple
            accept=".md,.markdown,.pdf,.docx,.xlsx,.txt"
            className="hidden"
            onChange={handleSelect}
            disabled={disabled}
            data-testid="sop-file-input"
          />
        </label>
      </div>
      {files.length > 0 && (
        <ul className="flex flex-col gap-1">
          {files.map((f) => (
            <li
              key={f.id}
              className="flex items-center justify-between rounded border border-border px-2 py-1 text-xs"
            >
              <span className="truncate">
                {f.file.name}{' '}
                <span className="text-muted-foreground">({formatBytes(f.file.size)})</span>
              </span>
              <button
                type="button"
                onClick={() => remove(f.id)}
                className="text-muted-foreground hover:text-destructive"
                disabled={disabled}
                aria-label={`Remove ${f.file.name}`}
              >
                <X size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
