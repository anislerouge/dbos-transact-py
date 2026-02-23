const colors: Record<string, { bg: string; fg: string }> = {
  SUCCESS: { bg: '#d4edda', fg: '#155724' },
  ERROR: { bg: '#f8d7da', fg: '#721c24' },
  PENDING: { bg: '#fff3cd', fg: '#856404' },
  RETRIES_EXCEEDED: { bg: '#f8d7da', fg: '#721c24' },
  CANCELLED: { bg: '#e2e3e5', fg: '#383d41' },
  ENQUEUED: { bg: '#cce5ff', fg: '#004085' },
}

export default function StatusBadge({ status }: { status: string | null }) {
  const s = status || 'UNKNOWN'
  const c = colors[s] || { bg: '#e2e3e5', fg: '#383d41' }
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 12, fontWeight: 600, background: c.bg, color: c.fg,
    }}>
      {s}
    </span>
  )
}
