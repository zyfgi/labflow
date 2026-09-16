import client from './client'

export interface Experiment {
  id: number
  experiment_no: string
  project_id: number
  project_name?: string
  task_id: number | null
  title: string
  objective: string | null
  background: string | null
  owner_id: number | null
  owner_name?: string | null
  experiment_date: string | null
  status: string
  environment: string | null
  method: string | null
  parameters: string | null
  result_summary: string | null
  conclusion: string | null
  problems: string | null
  next_step: string | null
  code_repo_url: string | null
  git_commit: string | null
  dataset_path: string | null
  software_version: string | null
  is_locked: boolean
  locked_at: string | null
  created_at: string
  updated_at: string
  can_edit?: boolean
  can_lock?: boolean
  attachments?: ExperimentAttachment[]
}

export interface ExperimentAttachment {
  id: number
  experiment_id: number
  file_name: string
  file_type: string
  file_size: number
  uploaded_at: string | null
}

export function listExperiments(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: Experiment[]; total: number } }>('/experiments', { params })
}

export function getExperiment(id: number) {
  return client.get<{ data: Experiment }>(`/experiments/${id}`)
}

export function createExperiment(payload: Record<string, unknown>) {
  return client.post<{ data: Experiment }>('/experiments', payload)
}

export function updateExperiment(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: Experiment }>(`/experiments/${id}`, payload)
}

export function lockExperiment(id: number) {
  return client.post(`/experiments/${id}/lock`)
}

export function unlockExperiment(id: number) {
  return client.post(`/experiments/${id}/unlock`)
}

export function uploadAttachment(id: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return client.post(`/experiments/${id}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteAttachment(id: number) {
  return client.delete(`/experiment-attachments/${id}`)
}

export function attachmentDownloadUrl(id: number): string {
  return `/api/v1/experiment-attachments/${id}/download`
}
