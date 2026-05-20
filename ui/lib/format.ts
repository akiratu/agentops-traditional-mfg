import { formatDistanceToNow, formatRelative } from 'date-fns'

export function relativeTime(iso: string): string {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true })
  } catch {
    return iso
  }
}

export function absoluteTime(iso: string): string {
  try {
    return formatRelative(new Date(iso), new Date())
  } catch {
    return iso
  }
}

export function shortId(id: string, len = 8): string {
  return id.length > len ? `${id.slice(0, len)}…` : id
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}
