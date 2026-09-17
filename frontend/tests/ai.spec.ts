import { describe, expect, it, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// vi.mock factories are hoisted: declare mocks through vi.hoisted
const {
  chatMock,
  listConversationsMock,
  getConversationMock,
  deleteConversationMock,
  aiStatusMock,
} = vi.hoisted(() => ({
  chatMock: vi.fn(),
  listConversationsMock: vi.fn(),
  getConversationMock: vi.fn(),
  deleteConversationMock: vi.fn(),
  aiStatusMock: vi.fn(),
}))

vi.mock('@/api/ai', () => ({
  chat: chatMock,
  listConversations: listConversationsMock,
  getConversation: getConversationMock,
  deleteConversation: deleteConversationMock,
  createConversation: vi.fn(),
  retrieveDebug: vi.fn(),
  aiStatus: aiStatusMock,
  SOURCE_TYPE_LABELS: {
    project: '项目',
    task: '任务',
    experiment: '实验',
    weekly_report: '周报',
    equipment: '设备',
  },
}))

import { useAiStore } from '@/stores/ai'
import { SOURCE_TYPE_LABELS, type AISource } from '@/api/ai'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('SOURCE_TYPE_LABELS rendering', () => {
  it('maps known source types to Chinese labels', () => {
    expect(SOURCE_TYPE_LABELS.experiment).toBe('实验')
    expect(SOURCE_TYPE_LABELS.task).toBe('任务')
    expect(SOURCE_TYPE_LABELS.weekly_report).toBe('周报')
  })

  it('builds clickable labels for sources', () => {
    const source: AISource = { type: 'experiment', id: 52, title: 'EXP-001 PINN 辨识', url: '/experiments/52' }
    const label = `${SOURCE_TYPE_LABELS[source.type] ?? source.type} · ${source.title}`
    expect(label).toBe('实验 · EXP-001 PINN 辨识')
    expect(source.url).toMatch(/^\/experiments\//)
  })
})

describe('ai store conversation state', () => {
  it('send() appends user + assistant messages with sources and updates conversation id', async () => {
    chatMock.mockResolvedValue({
      data: {
        data: {
          conversation_id: 12,
          answer: '根据任务记录……',
          sources: [{ type: 'task', id: 3, title: '整理数据', url: '/tasks/3' }],
          model: 'fake-model',
          usage: { input_tokens: 1, output_tokens: 2 },
        },
      },
    })
    listConversationsMock.mockResolvedValue({ data: { data: { items: [], total: 0 } } })

    const store = useAiStore()
    await store.send('我有哪些未完成的任务？')

    expect(store.conversationId).toBe(12)
    expect(store.messages).toHaveLength(2)
    expect(store.messages[0]).toMatchObject({ role: 'user', content: '我有哪些未完成的任务？' })
    expect(store.messages[1]?.role).toBe('assistant')
    expect(store.messages[1]?.sources[0]?.url).toBe('/tasks/3')
    expect(store.sending).toBe(false)
  })

  it('send() ignores empty input', async () => {
    const store = useAiStore()
    await store.send('   ')
    expect(chatMock).not.toHaveBeenCalled()
    expect(store.messages).toHaveLength(0)
  })

  it('send() shows a friendly error message without leaking internals', async () => {
    chatMock.mockRejectedValue({
      response: { data: { detail: { code: 'AI_PROVIDER_TIMEOUT', message: 'AI 服务响应超时，请稍后重试。' } } },
    })
    listConversationsMock.mockResolvedValue({ data: { data: { items: [], total: 0 } } })

    const store = useAiStore()
    await store.send('你好')

    const last = store.messages[store.messages.length - 1]
    expect(last?.role).toBe('assistant')
    expect(last?.content).toContain('超时')
    expect(last?.content).not.toContain('AI_PROVIDER_TIMEOUT')
  })

  it('removeConversation clears the active view when it was open', async () => {
    deleteConversationMock.mockResolvedValue({ data: null })
    listConversationsMock.mockResolvedValue({ data: { data: { items: [], total: 0 } } })
    getConversationMock.mockResolvedValue({
      data: {
        data: {
          id: 7,
          title: 't',
          messages: [{ id: 1, role: 'user', content: 'hi', sources: [], model: null, created_at: null }],
        },
      },
    })

    const store = useAiStore()
    await store.openConversation(7)
    expect(store.conversationId).toBe(7)
    await store.removeConversation(7)
    expect(store.conversationId).toBeNull()
    expect(store.hasMessages).toBe(false)
  })
})
