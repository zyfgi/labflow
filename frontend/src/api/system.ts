import client from './client'

export interface AppNotification {
  id: number
  type: string
  title: string
  content: string | null
  related_type: string | null
  related_id: string | null
  is_read: boolean
  created_at: string | null
}

export interface SearchResult {
  members: { id: number; name: string; member_type: string }[]
  projects: { id: number; name: string; code: string; status: string }[]
  tasks: { id: number; title: string; status: string; project_id: number }[]
  experiments: { id: number; experiment_no: string; title: string; status: string }[]
  equipment: { id: number; name: string; asset_no: string; status: string }[]
}

export function listNotifications(params: { page?: number; page_size?: number; unread_only?: boolean } = {}) {
  return client.get<{ data: { items: AppNotification[]; total: number; unread: number } }>(
    '/notifications',
    { params },
  )
}

export function markRead(id: number) {
  return client.post(`/notifications/${id}/read`)
}

export function readAll() {
  return client.post('/notifications/read-all')
}

export function globalSearch(q: string) {
  return client.get<{ data: SearchResult }>('/search', { params: { q } })
}

export async function downloadExport(kind: string, format: 'csv' | 'xlsx') {
  const resp = await client.get(`/exports/${kind}`, {
    params: { format },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([resp.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `labflow_${kind}_${new Date().toISOString().slice(0, 10)}.${format}`
  link.click()
  window.URL.revokeObjectURL(url)
}
