import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Workflow, RegisteredWorkflow, WorkflowParam } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import { formatEpoch, formatDuration } from '../utils/time'
import { parseWorkflowInput } from '../utils/parse'

/** Return a default value string for a parameter (stored as raw user input). */
function defaultForParam(p: WorkflowParam): string {
  if (p.default !== undefined) {
    // For strings, store the raw string (not JSON-quoted)
    if (p.type?.type === 'string' && typeof p.default === 'string') return p.default
    return JSON.stringify(p.default)
  }
  const t = p.type?.type
  if (t === 'string') return ''
  if (t === 'integer' || t === 'number') return '0'
  if (t === 'boolean') return 'false'
  if (t === 'array') return '[]'
  if (t === 'object') return '{}'
  return ''
}

/** Convert a raw param value to a JS value for the args array. */
function parseParamValue(p: WorkflowParam, raw: string): unknown {
  const t = p.type?.type
  // String fields are stored as raw text — no JSON.parse needed
  if (t === 'string') return raw
  return JSON.parse(raw)
}

export default function WorkflowList() {
  const navigate = useNavigate()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)

  // Registry (available workflows with signatures)
  const [registry, setRegistry] = useState<RegisteredWorkflow[]>([])
  const [startTarget, setStartTarget] = useState<RegisteredWorkflow | null>(null)
  const [paramValues, setParamValues] = useState<Record<string, string>>({})

  // Restart modal state (raw JSON for existing workflows)
  const [restartTarget, setRestartTarget] = useState<Workflow | null>(null)
  const [restartArgs, setRestartArgs] = useState('[]')
  const [restartKwargs, setRestartKwargs] = useState('{}')

  // Shared modal state
  const [modalLoading, setModalLoading] = useState(false)
  const [modalError, setModalError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { limit: '50', sort_desc: 'true', load_input: 'true', load_output: 'true' }
      if (statusFilter) params.status = statusFilter
      const wfs = await api.getWorkflows(params)
      setWorkflows(wfs)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [statusFilter])
  useEffect(() => { api.getRegistry().then(setRegistry).catch(console.error) }, [])

  const handleAction = async (id: string, action: 'cancel' | 'resume') => {
    try {
      if (action === 'cancel') await api.cancelWorkflow(id)
      else await api.resumeWorkflow(id)
      load()
    } catch (e) {
      alert(`Action failed: ${e}`)
    }
  }

  // --- Start workflow from registry (typed fields) ---

  const openStartModal = (wf: RegisteredWorkflow) => {
    setStartTarget(wf)
    const defaults: Record<string, string> = {}
    for (const p of wf.params) {
      defaults[p.name] = defaultForParam(p)
    }
    setParamValues(defaults)
    setModalError('')
  }

  const handleStart = async () => {
    if (!startTarget) return
    setModalLoading(true)
    setModalError('')
    try {
      // Build args array from positional params
      const args: unknown[] = []
      for (const p of startTarget.params) {
        if (p.variadic) continue
        const raw = paramValues[p.name] ?? ''
        if (raw === '' && p.default === undefined) {
          throw new Error(`Parameter "${p.name}" is required`)
        }
        if (raw === '' && p.type?.type !== 'string') continue
        args.push(parseParamValue(p, raw))
      }
      const result = await api.startWorkflow(startTarget.name, args, {})
      if (result.error_message) {
        setModalError(result.error_message)
      } else if (result.workflow_id) {
        setStartTarget(null)
        load()
        navigate(`/workflows/${result.workflow_id}`)
      }
    } catch (e) {
      setModalError(String(e))
    } finally {
      setModalLoading(false)
    }
  }

  // --- Restart workflow (raw JSON) ---

  const openRestartModal = async (wf: Workflow) => {
    setModalError('')
    setRestartTarget(wf)
    let input = wf.Input
    if (!input) {
      try {
        const detail = await api.getWorkflow(wf.WorkflowUUID)
        input = detail.Input
      } catch {
        // ignore
      }
    }
    const { args, kwargs } = parseWorkflowInput(input)
    setRestartArgs(JSON.stringify(args, null, 2))
    setRestartKwargs(JSON.stringify(kwargs, null, 2))
  }

  const handleRestart = async () => {
    if (!restartTarget?.WorkflowName) return
    setModalLoading(true)
    setModalError('')
    try {
      const args = JSON.parse(restartArgs)
      const kwargs = JSON.parse(restartKwargs)
      if (!Array.isArray(args)) throw new Error('args must be a JSON array')
      if (typeof kwargs !== 'object' || Array.isArray(kwargs)) throw new Error('kwargs must be a JSON object')
      const result = await api.startWorkflow(restartTarget.WorkflowName, args, kwargs)
      if (result.error_message) {
        setModalError(result.error_message)
      } else if (result.workflow_id) {
        setRestartTarget(null)
        navigate(`/workflows/${result.workflow_id}`)
      }
    } catch (e) {
      setModalError(String(e))
    } finally {
      setModalLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Workflows</h1>

      {/* Registered workflows */}
      {registry.length > 0 && (
        <div style={{
          padding: 12, background: '#fff', border: '1px solid #ddd', borderRadius: 8,
          marginBottom: 16,
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Registered Workflows</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {registry.map(wf => (
              <button
                key={wf.name}
                onClick={() => openStartModal(wf)}
                title={wf.params.map(p => `${p.name}: ${p.type_hint || '?'}`).join(', ')}
                style={{
                  padding: '4px 10px', fontSize: 12, borderRadius: 4,
                  border: '1px solid #b8d0ff', background: '#e7f1ff',
                  cursor: 'pointer', fontFamily: 'monospace',
                }}
              >
                {wf.name}({wf.params.map(p => p.name).join(', ')})
              </button>
            ))}
          </div>
        </div>
      )}

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
                  <Link to={`/workflows/${wf.WorkflowUUID}`}>
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

      {/* Restart Modal (raw JSON) */}
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
              style={textareaStyle}
            />

            <label style={{ display: 'block', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
              kwargs <span style={{ fontWeight: 400, color: '#888' }}>(JSON object)</span>
            </label>
            <textarea
              value={restartKwargs}
              onChange={e => setRestartKwargs(e.target.value)}
              rows={5}
              style={{ ...textareaStyle, marginBottom: 16 }}
            />

            {modalError && <ErrorBox message={modalError} />}

            <ModalButtons
              onCancel={() => setRestartTarget(null)}
              onSubmit={handleRestart}
              loading={modalLoading}
            />
          </div>
        </div>
      )}

      {/* Start Workflow Modal (typed fields) */}
      {startTarget && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setStartTarget(null)}
        >
          <div
            style={{
              background: '#fff', borderRadius: 10, padding: 24, width: 560,
              maxHeight: '80vh', overflow: 'auto', boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0, marginBottom: 4 }}>Start Workflow</h2>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 16 }}>
              <strong style={{ fontFamily: 'monospace' }}>{startTarget.name}</strong>
            </p>

            {startTarget.params.length === 0 && (
              <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>This workflow takes no parameters.</p>
            )}

            {startTarget.params.filter(p => !p.variadic).map(p => (
              <div key={p.name} style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                  {p.name}
                  {p.type_hint && (
                    <span style={{ fontWeight: 400, color: '#888', marginLeft: 6, fontFamily: 'monospace', fontSize: 12 }}>
                      {p.type_hint}
                    </span>
                  )}
                  {p.default !== undefined && (
                    <span style={{ fontWeight: 400, color: '#aaa', marginLeft: 6, fontSize: 11 }}>
                      = {JSON.stringify(p.default)}
                    </span>
                  )}
                </label>
                {p.type?.type === 'string' ? (
                  <input
                    type="text"
                    value={paramValues[p.name] ?? ''}
                    onChange={e => setParamValues(v => ({ ...v, [p.name]: e.target.value }))}
                    placeholder={p.type_hint || 'string'}
                    style={inputStyle}
                  />
                ) : p.type?.type === 'boolean' ? (
                  <select
                    value={paramValues[p.name] ?? 'false'}
                    onChange={e => setParamValues(v => ({ ...v, [p.name]: e.target.value }))}
                    style={inputStyle}
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : p.type?.type === 'integer' || p.type?.type === 'number' ? (
                  <input
                    type="number"
                    value={paramValues[p.name] ?? '0'}
                    onChange={e => setParamValues(v => ({ ...v, [p.name]: e.target.value || '0' }))}
                    step={p.type?.type === 'integer' ? 1 : 'any'}
                    style={inputStyle}
                  />
                ) : (
                  <textarea
                    value={paramValues[p.name] ?? ''}
                    onChange={e => setParamValues(v => ({ ...v, [p.name]: e.target.value }))}
                    rows={3}
                    placeholder={`JSON value (${p.type_hint || 'any'})`}
                    style={textareaStyle}
                  />
                )}
              </div>
            ))}

            {modalError && <ErrorBox message={modalError} />}

            <ModalButtons
              onCancel={() => setStartTarget(null)}
              onSubmit={handleStart}
              loading={modalLoading}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div style={{
      padding: 10, background: '#fff5f5', border: '1px solid #f5c6cb',
      borderRadius: 6, color: '#721c24', fontSize: 13, marginBottom: 12,
    }}>
      {message}
    </div>
  )
}

function ModalButtons({ onCancel, onSubmit, loading }: {
  onCancel: () => void
  onSubmit: () => void
  loading: boolean
}) {
  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
      <button
        onClick={onCancel}
        style={{
          padding: '8px 16px', background: '#f0f0f0', border: '1px solid #ccc',
          borderRadius: 6, cursor: 'pointer', fontSize: 14,
        }}
      >
        Cancel
      </button>
      <button
        onClick={onSubmit}
        disabled={loading}
        style={{
          padding: '8px 20px', background: loading ? '#6c9bd2' : '#0d6efd',
          color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'default' : 'pointer',
          fontSize: 14, fontWeight: 600,
        }}
      >
        {loading ? 'Starting...' : 'Start Workflow'}
      </button>
    </div>
  )
}

const actionBtn: React.CSSProperties = {
  padding: '2px 8px', border: '1px solid #ddd', borderRadius: 3,
  background: '#f8f9fa', cursor: 'pointer', fontSize: 12,
}

const inputStyle: React.CSSProperties = {
  width: '100%', fontFamily: 'monospace', fontSize: 13, padding: '8px 10px',
  border: '1px solid #ccc', borderRadius: 6, boxSizing: 'border-box',
}

const textareaStyle: React.CSSProperties = {
  width: '100%', fontFamily: 'monospace', fontSize: 13, padding: 10,
  border: '1px solid #ccc', borderRadius: 6, resize: 'vertical',
  boxSizing: 'border-box', marginBottom: 12,
}
