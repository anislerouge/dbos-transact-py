/** Format an epoch-ms string or number to a readable local datetime. */
export function formatEpoch(value: string | number | null | undefined): string {
  if (value == null || value === '') return '-'
  const ms = typeof value === 'string' ? Number(value) : value
  if (isNaN(ms) || ms <= 0) return '-'
  return new Date(ms).toLocaleString()
}

/** Compute human-readable duration between two epoch-ms values. */
export function formatDuration(
  startMs: string | number | null | undefined,
  endMs: string | number | null | undefined,
): string {
  if (startMs == null || endMs == null) return '-'
  const s = typeof startMs === 'string' ? Number(startMs) : startMs
  const e = typeof endMs === 'string' ? Number(endMs) : endMs
  if (isNaN(s) || isNaN(e)) return '-'
  const diff = e - s
  if (diff < 1000) return `${diff}ms`
  if (diff < 60_000) return `${(diff / 1000).toFixed(1)}s`
  return `${(diff / 60_000).toFixed(1)}min`
}
