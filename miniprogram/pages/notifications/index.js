// Notifications: list + unread badge + tap-through. Read/unread only —
// no confirm/acknowledge interactions (manual §27, §61).
const { get, post } = require('../../utils/request')

Page({
  data: { items: [], unread: 0, loading: true },

  onShow() {
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const data = await get('/notifications?page=1&page_size=50')
      this.setData({ items: data.items || [], unread: data.unread || 0, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  async open(e) {
    const { index, type, related } = e.currentTarget.dataset
    const item = this.data.items[index]
    if (item && !item.is_read) {
      try {
        await post(`/notifications/${item.id}/read`)
      } catch {}
    }
    if (related) {
      wx.navigateTo({ url: `/pages/equipment/index?id=${related}` })
    } else {
      this.load()
    }
    void type
  },

  async readAll() {
    try {
      await post('/notifications/read-all')
      this.load()
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },
})
