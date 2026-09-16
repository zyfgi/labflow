import client from './client'

export interface Task {
  id: number
  project_id: number
  project_name?: string
  milestone_id: number | null
  parent_task_id: number | null
  title: string
  description: string | null
  assignee_id: number | null
  assignee_name?: string | null
  creator_id: number | null
  priority: string
  status: string
  start_date: string | null
  due_date: string | null
  completed_at: string | null
  progress: number
  created_at: string
  updated_at: string
  can_edit?: boolean
  is_overdue?: boolean
}

export interface TaskComment {
  id: number
  task_id: number
  user_id: number | null
  user_name?: string | null
  content: string
  created_at: string | null
}

export function listTasks(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: Task[]; total: number } }>('/tasks', { params })
}

export function getTask(id: number) {
  return client.get<{ data: Task }>(`/tasks/${id}`)
}

export function createTask(payload: Record<string, unknown>) {
  return client.post<{ data: Task }>('/tasks', payload)
}

export function updateTask(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: Task }>(`/tasks/${id}`, payload)
}

export function setTaskStatus(id: number, status: string, progress?: number) {
  return client.post<{ data: Task }>(`/tasks/${id}/status`, { status, progress })
}

export function deleteTask(id: number) {
  return client.delete(`/tasks/${id}`)
}

export function listTaskComments(id: number) {
  return client.get<{ data: TaskComment[] }>(`/tasks/${id}/comments`)
}

export function addTaskComment(id: number, content: string) {
  return client.post<{ data: TaskComment }>(`/tasks/${id}/comments`, { content })
}
