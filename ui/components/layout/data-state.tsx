'use client'

import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { AlertCircle, Inbox, Loader2 } from 'lucide-react'

export interface DataStateProps<T> {
  query: UseQueryResult<T, unknown>
  loading?: ReactNode
  empty?: ReactNode
  isEmpty?: (data: T) => boolean
  error?: (err: unknown, retry: () => void) => ReactNode
  children: (data: T) => ReactNode
}

export function DataState<T>({
  query,
  loading,
  empty,
  isEmpty,
  error,
  children,
}: DataStateProps<T>) {
  if (query.isPending) {
    return (
      <div className="flex items-center gap-2 p-card text-muted-foreground" role="status">
        {loading ?? (
          <>
            <Loader2 className="animate-spin" size={16} />
            載入中…
          </>
        )}
      </div>
    )
  }
  if (query.isError) {
    const retry = () => {
      void query.refetch()
    }
    const msg = query.error instanceof Error ? query.error.message : 'Unknown error'
    return (
      <div className="flex items-start gap-2 p-card text-destructive" role="alert">
        {error ? (
          error(query.error, retry)
        ) : (
          <>
            <AlertCircle size={16} className="mt-0.5" />
            <div>
              <div className="font-medium">載入失敗: {msg}</div>
              <button
                onClick={retry}
                className="mt-1 text-xs underline hover:opacity-80"
                type="button"
              >
                重試
              </button>
            </div>
          </>
        )}
      </div>
    )
  }
  const data = query.data as T
  if (isEmpty?.(data)) {
    return (
      <div className="flex items-center gap-2 p-card text-muted-foreground">
        {empty ?? (
          <>
            <Inbox size={16} />
            尚無資料
          </>
        )}
      </div>
    )
  }
  return <>{children(data)}</>
}
