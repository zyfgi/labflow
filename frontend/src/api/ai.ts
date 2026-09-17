import client from './client'

export interface AISource {
  type: string
  id: number
  title: string
  url: string | null
}

export interface AIChatResult {
  conversation_id: number
  answer: string
  sources: AISource[]
  model: string | null
  usage: { input_tokens: number | null; output_tokens: number | null } | null
  source_labels?: string[]
}

export interface AIConversationSummary {
  id: number
  title: string
  updated_at: string
}

export interface AIMessageRow {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources: AISource[]
  model: string | null
  created_at: string | null
}

export interface AIConversationDetail {
  id: number
  title: string
  messages: AIMessageRow[]
}

export function chat(message: string, conversationId?: number) {
  return client.post<{ data: AIChatResult }>('/ai/chat', {
    message,
    conversation_id: conversationId ?? null,
  })
}

export function listConversations(page = 1) {
  return client.get<{ data: { items: AIConversationSummary[]; total: number } }>(
    '/ai/conversations',
    { params: { page, page_size: 50 } },
  )
}

export function getConversation(id: number) {
  return client.get<{ data: AIConversationDetail }>(`/ai/conversations/${id}`)
}

export function deleteConversation(id: number) {
  return client.delete(`/ai/conversations/${id}`)
}

export function aiStatus() {
  return client.get<{ data: { ai_enabled: boolean; model: string | null; api_key: string } }>(
    '/ai/status',
  )
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  project: '项目',
  task: '任务',
  experiment: '实验',
  weekly_report: '周报',
  equipment: '设备',
  maintenance: '维修',
  booking: '预约',
  member: '成员',
  learning_plan: '学习计划',
}
