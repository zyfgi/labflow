import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  chat as chatApi,
  deleteConversation as deleteConversationApi,
  getConversation,
  listConversations,
  type AIConversationSummary,
  type AIMessageRow,
  type AISource,
} from '@/api/ai'
import { useAuthStore } from '@/stores/auth'

export interface ChatDisplayMessage {
  role: 'user' | 'assistant'
  content: string
  sources: AISource[]
  model?: string | null
}

export const useAiStore = defineStore('ai', () => {
  const conversations = ref<AIConversationSummary[]>([])
  const conversationId = ref<number | null>(null)
  const messages = ref<ChatDisplayMessage[]>([])
  const sending = ref(false)
  const loadingHistory = ref(false)
  const aiEnabled = ref(true)

  const hasMessages = computed(() => messages.value.length > 0)

  async function refreshConversations() {
    const { data } = await listConversations()
    conversations.value = data.data.items
  }

  async function loadStatus() {
    try {
      const { data } = await import('@/api/ai').then((m) => m.aiStatus())
      aiEnabled.value = data.data.ai_enabled
    } catch {
      aiEnabled.value = true // backend < flag absent: keep UI usable
    }
  }

  async function openConversation(id: number) {
    loadingHistory.value = true
    try {
      const { data } = await getConversation(id)
      conversationId.value = data.data.id
      messages.value = data.data.messages.map((m: AIMessageRow) => ({
        role: m.role,
        content: m.content,
        sources: m.sources ?? [],
        model: m.model,
      }))
    } finally {
      loadingHistory.value = false
    }
  }

  function newConversation() {
    conversationId.value = null
    messages.value = []
  }

  async function removeConversation(id: number) {
    await deleteConversationApi(id)
    if (conversationId.value === id) newConversation()
    await refreshConversations()
  }

  async function send(question: string) {
    if (!question.trim() || sending.value) return
    sending.value = true
    messages.value.push({ role: 'user', content: question.trim(), sources: [] })
    try {
      const { data } = await chatApi(question.trim(), conversationId.value ?? undefined)
      conversationId.value = data.data.conversation_id
      messages.value.push({
        role: 'assistant',
        content: data.data.answer,
        sources: data.data.sources,
        model: data.data.model,
      })
      await refreshConversations()
    } catch (e) {
      messages.value.push({
        role: 'assistant',
        content: (e as { response?: { data?: { detail?: { message?: string } } } })
          ?.response?.data?.detail?.message ?? 'AI 服务暂时不可用，请稍后重试。',
        sources: [],
      })
    } finally {
      sending.value = false
    }
  }

  const recommendedQuestions = computed(() => {
    const auth = useAuthStore()
    if (auth.canManage) {
      return [
        '最近有哪些项目存在逾期任务？',
        '总结本周实验室科研进展',
        '最近有哪些实验遇到了问题？',
        '哪些项目临近里程碑？',
      ]
    }
    return [
      '我有哪些未完成任务？',
      '我最近一个月做了哪些实验？',
      '总结我最近三周的研究进展',
      '我有哪些逾期任务？',
    ]
  })

  return {
    conversations,
    conversationId,
    messages,
    sending,
    loadingHistory,
    aiEnabled,
    hasMessages,
    refreshConversations,
    loadStatus,
    openConversation,
    newConversation,
    removeConversation,
    send,
    recommendedQuestions,
  }
})
