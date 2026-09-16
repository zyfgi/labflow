import client from './client'

export interface Skill {
  id: number
  name: string
  category: string
  description: string | null
  sort_order: number
  is_active: boolean
}

export interface MemberSkill {
  id: number
  skill_id: number
  level: number
  note: string | null
  updated_at: string
}

export interface LearningPlan {
  id: number
  member_id: number
  title: string
  description: string | null
  category: string
  start_date: string | null
  target_date: string | null
  status: string
  progress: number
  created_by: number | null
  created_at: string
  updated_at: string
}

export function listSkills() {
  return client.get<{ data: Skill[] }>('/skills').then((r) => r.data.data)
}

export function createSkill(payload: Record<string, unknown>) {
  return client.post<{ data: Skill }>('/skills', payload)
}

export function getMemberSkills(memberId: number) {
  return client
    .get<{ data: MemberSkill[] }>(`/members/${memberId}/skills`)
    .then((r) => r.data.data)
}

export function setMemberSkills(memberId: number, items: { skill_id: number; level: number; note?: string }[]) {
  return client.put<{ data: MemberSkill[] }>(`/members/${memberId}/skills`, items)
}

export function listPlans(params: { member_id?: number; status?: string } = {}) {
  return client.get<{ data: LearningPlan[] }>('/learning-plans', { params })
}

export function createPlan(payload: Record<string, unknown>) {
  return client.post<{ data: LearningPlan }>('/learning-plans', payload)
}

export function updatePlan(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: LearningPlan }>(`/learning-plans/${id}`, payload)
}

export function deletePlan(id: number) {
  return client.delete(`/learning-plans/${id}`)
}
