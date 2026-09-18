// Members: read collaboration — every active member can see the roster and
// each member's research progress (manual §3, §4).
const { get } = require('../../utils/request')

Page({
  data: { members: [], loading: true },

  onShow() {
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const data = await get('/members?page_size=100')
      this.setData({ members: data.items || [], loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },
})
