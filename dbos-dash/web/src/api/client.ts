const BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  return resp.json()
}

export interface Workflow {
  WorkflowUUID: string
  Status: string | null
  WorkflowName: string | null
  CreatedAt: string | null
  UpdatedAt: string | null
  QueueName: string | null
  ExecutorID: string | null
  Error: string | null
  Input: string | null
  Output: string | null
}

export interface WorkflowStep {
  function_id: number
  function_name: string
  output: string | null
  error: string | null
  child_workflow_id: string | null
  started_at_epoch_ms: string | null
  completed_at_epoch_ms: string | null
}

export interface ParamSchema {
  type?: string
  items?: ParamSchema
  additionalProperties?: ParamSchema
}

export interface WorkflowParam {
  name: string
  type?: ParamSchema
  type_hint?: string
  default?: unknown
  variadic?: 'args' | 'kwargs'
}

export interface RegisteredWorkflow {
  name: string
  params: WorkflowParam[]
}

export const api = {
  getWorkflows: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<Workflow[]>(`/workflows${qs}`)
  },
  getWorkflow: (id: string) => request<Workflow>(`/workflows/${id}`),
  getSteps: (id: string) => request<WorkflowStep[]>(`/workflows/${id}/steps`),
  cancelWorkflow: (id: string) =>
    request<{ success: boolean }>(`/workflows/${id}/cancel`, { method: 'POST' }),
  resumeWorkflow: (id: string) =>
    request<{ success: boolean }>(`/workflows/${id}/resume`, { method: 'POST' }),
  restartWorkflow: (id: string) =>
    request<{ success: boolean }>(`/workflows/${id}/restart`, { method: 'POST' }),
  getQueuedWorkflows: () => request<Workflow[]>('/workflows/queued'),
  getRegistry: () => request<RegisteredWorkflow[]>('/workflows/registry'),
  startWorkflow: (workflowName: string, args: unknown[], kwargs: Record<string, unknown>) =>
    request<{ workflow_id: string | null; error_message: string | null }>('/workflows/start', {
      method: 'POST',
      body: JSON.stringify({ workflow_name: workflowName, args, kwargs }),
    }),
  getHealth: () => fetch('/health').then(r => r.json()),
}
