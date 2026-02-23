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

export interface AppInfo {
  name: string
  executor_count: number
}

export interface ExecutorInfo {
  executor_id: string
  app_name: string
  hostname: string | null
  language: string | null
  application_version: string | null
  dbos_version: string | null
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

export const api = {
  getApps: () => request<AppInfo[]>('/apps'),
  getExecutors: (app: string) => request<ExecutorInfo[]>(`/apps/${app}/executors`),
  getWorkflows: (app: string, params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<Workflow[]>(`/apps/${app}/workflows${qs}`)
  },
  getWorkflow: (app: string, id: string) => request<Workflow>(`/apps/${app}/workflows/${id}`),
  getSteps: (app: string, id: string) => request<WorkflowStep[]>(`/apps/${app}/workflows/${id}/steps`),
  cancelWorkflow: (app: string, id: string) =>
    request<{ success: boolean }>(`/apps/${app}/workflows/${id}/cancel`, { method: 'POST' }),
  resumeWorkflow: (app: string, id: string) =>
    request<{ success: boolean }>(`/apps/${app}/workflows/${id}/resume`, { method: 'POST' }),
  restartWorkflow: (app: string, id: string) =>
    request<{ success: boolean }>(`/apps/${app}/workflows/${id}/restart`, { method: 'POST' }),
  getQueuedWorkflows: (app: string) => request<Workflow[]>(`/apps/${app}/queued-workflows`),
  startWorkflow: (app: string, workflowName: string, args: unknown[], kwargs: Record<string, unknown>) =>
    request<{ workflow_id: string | null; error_message: string | null }>(`/apps/${app}/workflows/start`, {
      method: 'POST',
      body: JSON.stringify({ workflow_name: workflowName, args, kwargs }),
    }),
  getHealth: () => fetch('/health').then(r => r.json()),
}
