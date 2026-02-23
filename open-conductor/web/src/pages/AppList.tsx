import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, AppInfo, ExecutorInfo } from '../api/client'

export default function AppList() {
  const [apps, setApps] = useState<AppInfo[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [executors, setExecutors] = useState<ExecutorInfo[]>([])

  useEffect(() => {
    api.getApps().then(setApps).catch(console.error)
  }, [])

  const toggleApp = async (name: string) => {
    if (expanded === name) {
      setExpanded(null)
      return
    }
    setExpanded(name)
    try {
      const execs = await api.getExecutors(name)
      setExecutors(execs)
    } catch {
      setExecutors([])
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>Applications</h1>
      {apps.length === 0 ? (
        <p style={{ color: '#666' }}>No applications connected.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
              <th style={{ padding: 12 }}>Name</th>
              <th style={{ padding: 12 }}>Executors</th>
              <th style={{ padding: 12 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {apps.map(app => (
              <>
                <tr key={app.name} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: 12, fontWeight: 600 }}>{app.name}</td>
                  <td style={{ padding: 12 }}>{app.executor_count}</td>
                  <td style={{ padding: 12, display: 'flex', gap: 8 }}>
                    <button onClick={() => toggleApp(app.name)} style={btnStyle}>
                      {expanded === app.name ? 'Hide' : 'Executors'}
                    </button>
                    <Link to={`/apps/${app.name}/workflows`} style={{ ...btnStyle, textDecoration: 'none', textAlign: 'center' }}>
                      Workflows
                    </Link>
                    <Link to={`/apps/${app.name}/queues`} style={{ ...btnStyle, textDecoration: 'none', textAlign: 'center' }}>
                      Queues
                    </Link>
                  </td>
                </tr>
                {expanded === app.name && (
                  <tr key={`${app.name}-exec`}>
                    <td colSpan={3} style={{ padding: '0 12px 12px' }}>
                      {executors.length === 0 ? (
                        <p style={{ color: '#666', fontSize: 13 }}>No executor details available.</p>
                      ) : (
                        <table style={{ width: '100%', fontSize: 13 }}>
                          <thead>
                            <tr style={{ textAlign: 'left', color: '#666' }}>
                              <th style={{ padding: 4 }}>ID</th>
                              <th style={{ padding: 4 }}>Host</th>
                              <th style={{ padding: 4 }}>Version</th>
                              <th style={{ padding: 4 }}>Language</th>
                            </tr>
                          </thead>
                          <tbody>
                            {executors.map(ex => (
                              <tr key={ex.executor_id}>
                                <td style={{ padding: 4, fontFamily: 'monospace' }}>{ex.executor_id}</td>
                                <td style={{ padding: 4 }}>{ex.hostname}</td>
                                <td style={{ padding: 4 }}>{ex.application_version}</td>
                                <td style={{ padding: 4 }}>{ex.language}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '4px 12px', border: '1px solid #ddd', borderRadius: 4,
  background: '#f8f9fa', cursor: 'pointer', fontSize: 13, color: '#333',
}
