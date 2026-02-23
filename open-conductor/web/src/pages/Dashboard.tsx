import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, AppInfo } from '../api/client'

export default function Dashboard() {
  const [apps, setApps] = useState<AppInfo[]>([])
  const [health, setHealth] = useState<{ status: string; connected_apps: number } | null>(null)

  useEffect(() => {
    api.getApps().then(setApps).catch(console.error)
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
            {health.connected_apps} app(s) connected
          </div>
        </div>
      )}

      <h2 style={{ marginBottom: 12 }}>Connected Applications</h2>
      {apps.length === 0 ? (
        <p style={{ color: '#666' }}>No applications connected. Start a DBOS app with <code>conductor_url</code> pointing here.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {apps.map(app => (
            <div key={app.name} style={{
              padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #ddd',
            }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{app.name}</div>
              <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>
                {app.executor_count} executor(s)
              </div>
              <Link to={`/apps/${app.name}/workflows`} style={{ fontSize: 13, color: '#007bff' }}>
                View Workflows
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
