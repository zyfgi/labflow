import client from './client'
import type { Page } from '@/types'

export interface WeeklyReport {
  id: number
  member_id: number
  member_name?: string
  week_start: string
  week_end: string
  work_summary: string | null
  learning_summary: string | null
  experiment_summary: string | null
  problems: string | null
  next_week_plan: string | null
  need_help: string | null
  self_progress: number
  status: string
  submitted_at: string | null
  reviewed_at: string | null
  reviewer_id: number | null
  review_comment: string | null
  created_at: string
  updated_at: string
}

export interface ReportPayload {
  week_start: string
  work_summary?: string
  learning_summary?: string
  experiment_summary?: string
  problems?: string
  next_week_plan?: string
  need_help?: string
  self_progress?: number
}

export function listReports(params: {
  member_id?: number
  status?: string
  page?: number
  page_size?: number
} = {}) {
  return client.get<{ data: Page<WeeklyReport> }>('/weekly-reports', { params })
}

export function createReport(payload: ReportPayload) {
  return client.post<{ data: WeeklyReport }>('/weekly-reports', payload)
}

export function updateReport(id: number, payload: Partial<ReportPayload>) {
  return client.patch<{ data: WeeklyReport }>(`/weekly-reports/${id}`, payload)
}

export function submitReport(id: number) {
  return client.post<{ data: WeeklyReport }>(`/weekly-reports/${id}/submit`)
}

export function reviewReport(id: number, comment?: string) {
  return client.post<{ data: WeeklyReport }>(`/weekly-reports/${id}/review`, { comment })
}

export function returnReport(id: number, comment?: string) {
  return client.post<{ data: WeeklyReport }>(`/weekly-reports/${id}/return`, { comment })
}

export function myCurrentWeekReport() {
  return client.get<{ data: WeeklyReport | null }>('/weekly-reports/me/current')
}
