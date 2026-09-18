// Equipment detail (entry from QR / notifications): book / borrow / return /
// fault report. Immediate effect everywhere, notifications handle the rest.
const { get, post } = require('../../utils/request')

Page({
  data: { eq: null, loading: true },

  onLoad(query) {
    this.eqId = Number(query.id)
  },

  onShow() {
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const data = await get(`/equipment/${this.eqId}`)
      this.setData({ eq: data, loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  async book() {
    const start = new Date(Date.now() + 3600 * 1000)
    const end = new Date(Date.now() + 3 * 3600 * 1000)
    const fmt = (d) => d.toISOString().slice(0, 19)
    try {
      await post('/equipment-bookings', {
        equipment_id: this.eqId,
        start_time: fmt(start),
        end_time: fmt(end),
      })
      wx.showToast({ title: '已预约下一小时（立即生效）' })
      this.load()
    } catch (e) {
      wx.showModal({ title: '预约失败', content: e.message, showCancel: false })
    }
  },

  async borrow() {
    const expected = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 19)
    try {
      await post('/equipment-borrows', { equipment_id: this.eqId, expected_return_time: expected })
      wx.showToast({ title: '借出成功' })
      this.load()
    } catch (e) {
      wx.showModal({ title: '借用失败', content: e.message, showCancel: false })
    }
  },

  reportFault() {
    wx.showModal({
      title: '上报故障',
      editable: true,
      placeholderText: '描述故障现象（上报后立即生效）',
      success: async (res) => {
        if (!res.confirm || !res.content) return
        try {
          await post('/equipment-maintenance', {
            equipment_id: this.eqId,
            type: 'fault',
            description: res.content,
          })
          wx.showToast({ title: '已上报' })
          this.load()
        } catch (err) {
          wx.showToast({ title: err.message, icon: 'none' })
        }
      },
    })
  },
})
