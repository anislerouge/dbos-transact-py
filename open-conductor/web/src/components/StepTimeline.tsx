import { Link } from 'react-router-dom'
import { WorkflowStep } from '../api/client'
import { formatEpoch, formatDuration } from '../utils/time'

const stepStyle = {
  padding: 12, borderRadius: 6,
}

const tagStyle = (bg: string, fg: string): React.CSSProperties => ({
  display: 'inline-block', padding: '1px 6px', borderRadius: 3,
  fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
  background: bg, color: fg, marginLeft: 8, verticalAlign: 'middle',
})

export default function StepTimeline({ steps, appName }: { steps: WorkflowStep[]; appName?: string }) {
  if (steps.length === 0) return <p>No steps recorded.</p>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {steps.map((step) => {
        const hasError = !!step.error
        const isChild = !!step.child_workflow_id

        const borderColor = hasError ? '#f5c6cb' : isChild ? '#b8d0ff' : '#c3e6cb'
        const bgColor = hasError ? '#fff5f5' : isChild ? '#f0f4ff' : '#f0fff4'

        return (
          <div key={step.function_id} style={{ ...stepStyle, border: `1px solid ${borderColor}`, background: bgColor }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div>
                <strong>#{step.function_id} {step.function_name}</strong>
                {isChild
                  ? <span style={tagStyle('#cce5ff', '#004085')}>WORKFLOW</span>
                  : <span style={tagStyle('#d4edda', '#155724')}>STEP</span>
                }
              </div>
              <span style={{ fontSize: 12, color: '#666', fontFamily: 'monospace' }}>
                {formatDuration(step.started_at_epoch_ms, step.completed_at_epoch_ms)}
              </span>
            </div>

            {/* Timestamps */}
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4, display: 'flex', gap: 16 }}>
              <span>Start: {formatEpoch(step.started_at_epoch_ms)}</span>
              <span>End: {formatEpoch(step.completed_at_epoch_ms)}</span>
            </div>

            {/* Child workflow link */}
            {isChild && (
              <div style={{ fontSize: 12, marginBottom: 4, padding: '4px 8px', background: '#e3ecff', borderRadius: 4, display: 'inline-block' }}>
                <span style={{ color: '#666' }}>Child workflow: </span>
                {appName ? (
                  <Link to={`/apps/${appName}/workflows/${step.child_workflow_id}`}
                    style={{ fontFamily: 'monospace', color: '#004085' }}>
                    {step.child_workflow_id}
                  </Link>
                ) : (
                  <code style={{ color: '#004085' }}>{step.child_workflow_id}</code>
                )}
              </div>
            )}

            {/* Output */}
            {step.output && (
              <div style={{ fontSize: 12, color: '#155724', marginBottom: 4 }}>
                <span style={{ color: '#666' }}>Output: </span>
                <code style={{ background: '#e8f5e9', padding: '1px 4px', borderRadius: 3, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {step.output}
                </code>
              </div>
            )}

            {/* Error */}
            {step.error && (
              <div style={{ fontSize: 12, color: '#721c24', marginBottom: 4 }}>
                <span style={{ color: '#666' }}>Error: </span>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{step.error}</pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
