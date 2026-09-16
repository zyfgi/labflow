import client from './client'

export interface Project {
  id: number
  name: string
  code: string
  description: string | null
  research_direction: string | null
  owner_id: number | null
  owner_name?: string | null
  status: string
  priority: string
  start_date: string | null
  expected_end_date: string | null
  actual_end_date: string | null
  progress: number
  visibility: string
  my_role?: string
  task_total?: number
  task_done?: number
  task_overdue?: number
  milestone_count?: number
  created_at: string
  updated_at: string
}

export interface ProjectMemberRow {
  id: number
  user_id: number
  name: string
  username: string
  project_role: string
  joined_at: string | null
  left_at: string | null
}

export interface Milestone {
  id: number
  project_id: number
  title: string
  description: string | null
  due_date: string | null
  status: string
  progress: number
  completed_at: string | null
  created_at: string
  updated_at: string
}

export function listProjects(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: Project[]; total: number } }>('/projects', { params })
}

export function getProject(id: number) {
  return client.get<{ data: Project }>(`/projects/${id}`)
}

export function createProject(payload: Record<string, unknown>) {
  return client.post<{ data: Project }>('/projects', payload)
}

export function updateProject(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: Project }>(`/projects/${id}`, payload)
}

export function deleteProject(id: number) {
  return client.delete(`/projects/${id}`)
}

export function listProjectMembers(id: number) {
  return client.get<{ data: ProjectMemberRow[] }>(`/projects/${id}/members`)
}

export function addProjectMember(id: number, payload: { user_id: number; project_role: string }) {
  return client.post(`/projects/${id}/members`, payload)
}

export function removeProjectMember(id: number, userId: number) {
  return client.delete(`/projects/${id}/members/${userId}`)
}

export function listMilestones(projectId: number) {
  return client.get<{ data: Milestone[] }>(`/projects/${projectId}/milestones`)
}

export function createMilestone(projectId: number, payload: Record<string, unknown>) {
  return client.post(`/projects/${projectId}/milestones`, payload)
}

export function updateMilestone(id: number, payload: Record<string, unknown>) {
  return client.patch(`/milestones/${id}`, payload)
}

export function deleteMilestone(id: number) {
  return client.delete(`/milestones/${id}`)
}
