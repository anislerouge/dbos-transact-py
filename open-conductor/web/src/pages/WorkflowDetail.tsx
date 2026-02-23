import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Workflow, WorkflowStep } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import StepTimeline from '../components/StepTimeline'
import { formatEpoch, formatDuration } from '../utils/time'
import { parseWorkflowInput } from '../utils/parse'

export default function WorkflowDetail() {
  const { appName, workflowId } = useParams<{ appName: string; workflowId: string }>()
  const navigate = useNavigate()
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [steps, setSteps] = useState<WorkflowStep[]>([])
  const [error, setError] = useState('')

  const [showRestartModal, setShowRestartModal] = useState(false)
  const [restartArgs, setRestartArgs] = useState('[]')
  const [restartKwargs, setRestartKwargs] = useState('{}')
  const [restartLoading, setRestartLoading] = useState(false)
  const [restartError, setRestartError] = useState('')

  useEffect(() => {
    if (!appName || !workflowId) return
    api.getWorkflow(appName, workflowId).then(setWorkflow).catch(e => setError(String(e)))
    api.getSteps(appName, workflowId).then(setSteps).catch(console.error)
  }, [appName, workflowId])

  const openRestartModal = () => {
    const { args, kwargs } = parseWorkflowInput(workflow?.Input ?? null)
    setRestartArgs(JSON.stringify(args, null, 2))
    setRestartKwargs(JSON.stringify(kwargs, null, 2))
    setRestartError('')
    setShowRestartModal(true)
  }

  const handleRestart = async () => {
    if (!appName || !workflow?.WorkflowName) return
    setRestartLoading(true)
    setRestartError('')
    try {
      const args = JSON.parse(restartArgs)
      const kwargs = JSON.parse(restartKwargs)
      if (!Array.isArray(args)) throw new Error('args must be a JSON array')
      if (typeof kwargs !== 'object' || Array.isArray(kwargs)) throw new Error('kwargs must be a JSON object')
      const result = await api.startWorkflow(appName, workflow.WorkflowName, args, kwargs)
      if (result.error_message) {
        setRestartError(result.error_message)
      } else if (result.workflow_id) {
        setShowRestartModal(false)
        navigate(`/apps/${appName}/workflows/${result.workflow_id}`)
      }
    } catch (e) {
      setRestartError(String(e))
    } finally {
      setRestartLoading(false)
    }
  }

  if (error) return <p style={{ color: '#dc3545' }}>{error}</p>
  if (!workflow) return <p>Loading...</p>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 style={{ margin: 0 }}>Workflow Detail</h1>
        {workflow.WorkflowName && (
          <button
            onClick={openRestartModal}
            style={{
              padding: '8px 16px', background: '#0d6efd', color: '#fff', border: 'none',
              borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600,
            }}
          >
            Restart with params
          </button>
        )}
      </div>
      <p style={{ fontFamily: 'monospace', fontSize: 13, color: '#666', marginBottom: 16 }}>
        {workflow.WorkflowUUID}
      </p>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 12, marginBottom: 24,
      }}>
        <InfoCard label="Name" value={workflow.WorkflowName || '-'} />
        <InfoCard label="Status" value={<StatusBadge status={workflow.Status} />} />
        <InfoCard label="Started" value={formatEpoch(workflow.CreatedAt)} />
        <InfoCard label="Ended" value={formatEpoch(workflow.UpdatedAt)} />
        <InfoCard label="Duration" value={formatDuration(workflow.CreatedAt, workflow.UpdatedAt)} />
        <InfoCard label="Queue" value={workflow.QueueName || '-'} />
        <InfoCard label="Executor" value={workflow.ExecutorID || '-'} />
      </div>

      {workflow.Input && (
        <div style={{ padding: 12, background: '#f0f4ff', border: '1px solid #b8d0ff', borderRadius: 6, marginBottom: 12 }}>
          <strong>Input:</strong>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 4, maxHeight: 200, overflow: 'auto' }}>{workflow.Input}</pre>
        </div>
      )}

      {workflow.Output && (
        <div style={{ padding: 12, background: '#f0fff4', border: '1px solid #c3e6cb', borderRadius: 6, marginBottom: 12 }}>
          <strong>Output:</strong>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 4, maxHeight: 200, overflow: 'auto' }}>{workflow.Output}</pre>
        </div>
      )}

      {workflow.Error && (
        <div style={{ padding: 12, background: '#fff5f5', border: '1px solid #f5c6cb', borderRadius: 6, marginBottom: 16 }}>
          <strong>Error:</strong>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 4 }}>{workflow.Error}</pre>
        </div>
      )}

      <h2 style={{ marginBottom: 12 }}>Steps</h2>
      <StepTimeline steps={steps} appName={appName} />

      {/* Restart Modal */}
      {showRestartModal && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setShowRestartModal(false)}
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
              Start a new <strong>{workflow.WorkflowName}</strong> with modified parameters.
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
                onClick={() => setShowRestartModal(false)}
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

function InfoCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ padding: 12, background: '#fff', border: '1px solid #ddd', borderRadius: 6 }}>
      <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14 }}>{value}</div>
    </div>
  )
}
