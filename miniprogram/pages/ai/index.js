// AI assistant (read-only): retrieval + summary over data the caller can
// already see in the normal UI. The AI never approves or executes anything.
const { post } = require('../../utils/request')

Page({
  data: { messages: [], input: '', loading: false },

  onInput(e) {
    this.setData({ input: e.detail.value })
  },

  async send() {
    const q = this.data.input.trim()
    if (!q || this.data.loading) return
    const messages = [...this.data.messages, { role: 'user', content: q }]
    this.setData({ messages, input: '', loading: true })
    try {
      const data = await post('/ai/chat', { question: q })
      this.setData({
        messages: [
          ...messages,
          { role: 'assistant', content: data.answer || data.content || '(空回复)' },
        ],
        loading: false,
      })
    } catch (e) {
      this.setData({
        messages: [...messages, { role: 'assistant', content: '出错了：' + e.message }],
        loading: false,
      })
    }
  },
})
