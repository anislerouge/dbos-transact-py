import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Workflow } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function QueueView() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.getQueuedWorkflows()
      .then(setWorkflows)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>Queued Workflows</h1>

      {loading ? <p>Loading...</p> : (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
              <th style={{ padding: 10 }}>ID</th>
              <th style={{ padding: 10 }}>Name</th>
              <th style={{ padding: 10 }}>Status</th>
              <th style={{ padding: 10 }}>Queue</th>
              <th style={{ padding: 10 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map(wf => (
              <tr key={wf.WorkflowUUID} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 10, fontFamily: 'monospace', fontSize: 12 }}>
                  <Link to={`/workflows/${wf.WorkflowUUID}`}>
                    {wf.WorkflowUUID.slice(0, 12)}...
                  </Link>
                </td>
                <td style={{ padding: 10 }}>{wf.WorkflowName || '-'}</td>
                <td style={{ padding: 10 }}><StatusBadge status={wf.Status} /></td>
                <td style={{ padding: 10 }}>{wf.QueueName || '-'}</td>
                <td style={{ padding: 10 }}>{wf.CreatedAt || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && workflows.length === 0 && <p style={{ color: '#666' }}>No queued workflows.</p>}
    </div>
  )
}
