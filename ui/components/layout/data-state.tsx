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
      <div className="flex items-center gap-2 p-card text-zinc-500" role="status">
        {loading ?? (
          <>
            <Loader2 className="animate-spin" size={16} />
            Loading…
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
      <div className="flex items-start gap-2 p-card text-red-700 dark:text-red-400" role="alert">
        {error ? (
          error(query.error, retry)
        ) : (
          <>
            <AlertCircle size={16} className="mt-0.5" />
            <div>
              <div className="font-medium">Failed to load: {msg}</div>
              <button
                onClick={retry}
                className="mt-1 text-xs underline hover:text-red-900"
                type="button"
              >
                Retry
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
      <div className="flex items-center gap-2 p-card text-zinc-500">
        {empty ?? (
          <>
            <Inbox size={16} />
            No data yet.
          </>
        )}
      </div>
    )
  }
  return <>{children(data)}</>
}
