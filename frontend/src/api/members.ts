import client from './client'
import type { Page, User } from '@/types'

export interface Member {
  id: number
  user_id: number
  user: User
  student_no: string | null
  member_type: string
  grade_year: string | null
  research_direction: string | null
  join_date: string | null
  expected_leave_date: string | null
  supervisor_id: number | null
  office_location: string | null
  bio: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface MemberOverview {
  member: Member
  user: User
  current_projects: { id: number; name: string; status: string; progress: number }[]
  in_progress_tasks: number
  overdue_tasks: number
  this_week_report_status: string | null
  latest_experiment_date: string | null
}

export interface MemberQuery {
  page?: number
  page_size?: number
  member_type?: string
  status?: string
  keyword?: string
}

export function listMembers(query: MemberQuery = {}) {
  return client.get<{ data: Page<Member> }>('/members', { params: query })
}

export function getMember(id: number) {
  return client.get<{ data: Member }>(`/members/${id}`)
}

export function getMemberOverview(id: number) {
  return client.get<{ data: MemberOverview }>(`/members/${id}/overview`)
}

export function updateMember(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: Member }>(`/members/${id}`, payload)
}
