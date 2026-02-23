import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Dashboard() {
  const [health, setHealth] = useState<{ status: string; app_name: string } | null>(null)

  useEffect(() => {
    api.getHealth().then(setHealth).catch(console.error)
  }, [])

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>Dashboard</h1>

      {health && (
        <div style={{
          padding: 16, background: '#fff', borderRadius: 8, marginBottom: 24,
          border: '1px solid #ddd', display: 'inline-block',
        }}>
          <div style={{ fontSize: 14, color: '#666' }}>Server Status</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: health.status === 'ok' ? '#28a745' : '#dc3545' }}>
            {health.status.toUpperCase()}
          </div>
          <div style={{ fontSize: 14, color: '#666', marginTop: 4 }}>
            App: {health.app_name}
          </div>
        </div>
      )}

      <h2 style={{ marginBottom: 12 }}>Quick Links</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
        <div style={{ padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #ddd' }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Workflows</div>
          <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>
            View and manage all workflows
          </div>
          <Link to="/workflows" style={{ fontSize: 13, color: '#007bff' }}>
            View Workflows
          </Link>
        </div>
        <div style={{ padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #ddd' }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Queues</div>
          <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>
            View queued workflows
          </div>
          <Link to="/queues" style={{ fontSize: 13, color: '#007bff' }}>
            View Queues
          </Link>
        </div>
      </div>
    </div>
  )
}
