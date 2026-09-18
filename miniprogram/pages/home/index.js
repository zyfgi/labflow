// Home: notifications / recent activity / attention items first (manual §35, §37).
// There is deliberately no approval inbox.
const { get } = require('../../utils/request')

Page({
  data: {
    user: null,
    unread: 0,
    notifications: [],
    activity: [],
    loading: true,
  },

  onShow() {
    const app = getApp()
    this.setData({ user: app.getUser() })
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const notifications = await get('/notifications?page=1&page_size=5')
      const isStaff = ['PI', 'TEACHER'].includes(this.data.user && this.data.user.role)
      let activity = []
      let attention = { overdue_borrows: [] }
      if (isStaff) {
        const dash = await get('/dashboard/pi')
        activity = dash.activity || []
        attention = dash.attention || attention
      } else {
        const dash = await get('/dashboard/student')
        attention = dash.attention || attention
      }
      this.setData({
        unread: notifications.unread || 0,
        notifications: notifications.items || [],
        activity,
        attentionCounts: {
          borrows: (attention.overdue_borrows || []).length,
        },
        loading: false,
      })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  goNotifications() {
    wx.navigateTo({ url: '/pages/notifications/index' })
  },

  goItem(n) {
    const { related_type: t, related_id: id } = n.currentTarget.dataset
    if (t === 'task' || t === 'project') {
      wx.navigateTo({ url: `/pages/research/index?tab=${t === 'task' ? 'tasks' : 'projects'}` })
    } else if (t === 'equipment' || t === 'equipment_maintenance') {
      wx.navigateTo({ url: `/pages/equipment/index?id=${id}` })
    } else if (t === 'weekly_report') {
      wx.navigateTo({ url: '/pages/research/index?tab=reports' })
    }
  },
})
