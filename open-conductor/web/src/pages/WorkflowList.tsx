import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { api, Workflow } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import { formatEpoch, formatDuration } from '../utils/time'
import { parseWorkflowInput } from '../utils/parse'

export default function WorkflowList() {
  const { appName } = useParams<{ appName: string }>()
  const navigate = useNavigate()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)

  // Restart modal state
  const [restartTarget, setRestartTarget] = useState<Workflow | null>(null)
  const [restartArgs, setRestartArgs] = useState('[]')
  const [restartKwargs, setRestartKwargs] = useState('{}')
  const [restartLoading, setRestartLoading] = useState(false)
  const [restartError, setRestartError] = useState('')

  const load = async () => {
    if (!appName) return
    setLoading(true)
    try {
      const params: Record<string, string> = { limit: '50', sort_desc: 'true', load_input: 'true', load_output: 'true' }
      if (statusFilter) params.status = statusFilter
      const wfs = await api.getWorkflows(appName, params)
      setWorkflows(wfs)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [appName, statusFilter])

  const handleAction = async (id: string, action: 'cancel' | 'resume') => {
    if (!appName) return
    try {
      if (action === 'cancel') await api.cancelWorkflow(appName, id)
      else await api.resumeWorkflow(appName, id)
      load()
    } catch (e) {
      alert(`Action failed: ${e}`)
    }
  }

  const openRestartModal = async (wf: Workflow) => {
    setRestartError('')
    setRestartTarget(wf)
    // Fetch full detail to get Input (list view often has null Input)
    let input = wf.Input
    if (!input && appName) {
      try {
        const detail = await api.getWorkflow(appName, wf.WorkflowUUID)
        input = detail.Input
      } catch {
        // ignore, we'll just start with empty args
      }
    }
    const { args, kwargs } = parseWorkflowInput(input)
    setRestartArgs(JSON.stringify(args, null, 2))
    setRestartKwargs(JSON.stringify(kwargs, null, 2))
  }

  const handleRestart = async () => {
    if (!appName || !restartTarget?.WorkflowName) return
    setRestartLoading(true)
    setRestartError('')
    try {
      const args = JSON.parse(restartArgs)
      const kwargs = JSON.parse(restartKwargs)
      if (!Array.isArray(args)) throw new Error('args must be a JSON array')
      if (typeof kwargs !== 'object' || Array.isArray(kwargs)) throw new Error('kwargs must be a JSON object')
      const result = await api.startWorkflow(appName, restartTarget.WorkflowName, args, kwargs)
      if (result.error_message) {
        setRestartError(result.error_message)
      } else if (result.workflow_id) {
        setRestartTarget(null)
        navigate(`/apps/${appName}/workflows/${result.workflow_id}`)
      }
    } catch (e) {
      setRestartError(String(e))
    } finally {
      setRestartLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Workflows: {appName}</h1>

      <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
        <label style={{ fontSize: 13 }}>Status:</label>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #ccc' }}>
          <option value="">All</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="ERROR">ERROR</option>
          <option value="PENDING">PENDING</option>
          <option value="CANCELLED">CANCELLED</option>
          <option value="ENQUEUED">ENQUEUED</option>
        </select>
        <button onClick={load} style={{ padding: '4px 12px', borderRadius: 4, border: '1px solid #ccc', cursor: 'pointer' }}>
          Refresh
        </button>
      </div>

      {loading ? <p>Loading...</p> : (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
              <th style={{ padding: 10 }}>ID</th>
              <th style={{ padding: 10 }}>Name</th>
              <th style={{ padding: 10 }}>Status</th>
              <th style={{ padding: 10 }}>Input</th>
              <th style={{ padding: 10 }}>Output</th>
              <th style={{ padding: 10 }}>Started</th>
              <th style={{ padding: 10 }}>Ended</th>
              <th style={{ padding: 10 }}>Duration</th>
              <th style={{ padding: 10 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map(wf => (
              <tr key={wf.WorkflowUUID} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 10, fontFamily: 'monospace', fontSize: 12 }}>
                  <Link to={`/apps/${appName}/workflows/${wf.WorkflowUUID}`}>
                    {wf.WorkflowUUID.slice(0, 12)}...
                  </Link>
                </td>
                <td style={{ padding: 10 }}>{wf.WorkflowName || '-'}</td>
                <td style={{ padding: 10 }}><StatusBadge status={wf.Status} /></td>
                <td style={{ padding: 10, fontFamily: 'monospace', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={wf.Input || ''}>{wf.Input || '-'}</td>
                <td style={{ padding: 10, fontFamily: 'monospace', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={wf.Output || ''}>{wf.Output || '-'}</td>
                <td style={{ padding: 10, fontSize: 11 }}>{formatEpoch(wf.CreatedAt)}</td>
                <td style={{ padding: 10, fontSize: 11 }}>{formatEpoch(wf.UpdatedAt)}</td>
                <td style={{ padding: 10, fontSize: 11, fontFamily: 'monospace' }}>{formatDuration(wf.CreatedAt, wf.UpdatedAt)}</td>
                <td style={{ padding: 10, display: 'flex', gap: 4 }}>
                  <button onClick={() => handleAction(wf.WorkflowUUID, 'cancel')} style={actionBtn}>Cancel</button>
                  <button onClick={() => handleAction(wf.WorkflowUUID, 'resume')} style={actionBtn}>Resume</button>
                  <button
                    onClick={() => openRestartModal(wf)}
                    style={{ ...actionBtn, background: '#e7f1ff', borderColor: '#b8d0ff' }}
                    disabled={!wf.WorkflowName}
                    title={wf.WorkflowName ? 'Restart with modified params' : 'No workflow name'}
                  >
                    Restart
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && workflows.length === 0 && <p style={{ color: '#666' }}>No workflows found.</p>}

      {/* Restart Modal */}
      {restartTarget && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setRestartTarget(null)}
        >
          <div
            style={{
              background: '#fff', borderRadius: 10, padding: 24, width: 560,
              maxHeight: '80vh', overflow: 'auto', boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0, marginBottom: 4 }}>Restart Workflow</h2>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 16 }}>
              Start a new <strong>{restartTarget.WorkflowName}</strong> with modified parameters.
            </p>

            <label style={{ display: 'block', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
              args <span style={{ fontWeight: 400, color: '#888' }}>(JSON array)</span>
            </label>
            <textarea
              value={restartArgs}
              onChange={e => setRestartArgs(e.target.value)}
              rows={5}
              style={{
                width: '100%', fontFamily: 'monospace', fontSize: 13, padding: 10,
                border: '1px solid #ccc', borderRadius: 6, resize: 'vertical',
                boxSizing: 'border-box', marginBottom: 12,
              }}
            />

            <label style={{ display: 'block', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
              kwargs <span style={{ fontWeight: 400, color: '#888' }}>(JSON object)</span>
            </label>
            <textarea
              value={restartKwargs}
              onChange={e => setRestartKwargs(e.target.value)}
              rows={5}
              style={{
                width: '100%', fontFamily: 'monospace', fontSize: 13, padding: 10,
                border: '1px solid #ccc', borderRadius: 6, resize: 'vertical',
                boxSizing: 'border-box', marginBottom: 16,
              }}
            />

            {restartError && (
              <div style={{
                padding: 10, background: '#fff5f5', border: '1px solid #f5c6cb',
                borderRadius: 6, color: '#721c24', fontSize: 13, marginBottom: 12,
              }}>
                {restartError}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setRestartTarget(null)}
                style={{
                  padding: '8px 16px', background: '#f0f0f0', border: '1px solid #ccc',
                  borderRadius: 6, cursor: 'pointer', fontSize: 14,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleRestart}
                disabled={restartLoading}
                style={{
                  padding: '8px 20px', background: restartLoading ? '#6c9bd2' : '#0d6efd',
                  color: '#fff', border: 'none', borderRadius: 6, cursor: restartLoading ? 'default' : 'pointer',
                  fontSize: 14, fontWeight: 600,
                }}
              >
                {restartLoading ? 'Starting...' : 'Start Workflow'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const actionBtn: React.CSSProperties = {
  padding: '2px 8px', border: '1px solid #ddd', borderRadius: 3,
  background: '#f8f9fa', cursor: 'pointer', fontSize: 12,
}
