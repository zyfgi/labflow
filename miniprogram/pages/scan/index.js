// Scan: wx.scanCode -> QR token -> resolve -> equipment page with
// book/borrow/return/fault actions. The QR is a pointer, not a credential;
// auth and RBAC apply as usual.
const { get, post } = require('../../utils/request')

Page({
  data: {
    equipment: null,
    loading: false,
    booking: { startDate: '', startTime: '', endDate: '', endTime: '' },
  },

  onShow() {
    if (!this.data.equipment) this.scan()
  },

  scan() {
    wx.scanCode({
      success: (res) => this.resolve(res.result),
      fail: () => {},
    })
  },

  async resolve(url) {
    // accept both PUBLIC_BASE_URL/q/{token} and a raw token
    const match = /\/q\/([A-Za-z0-9_-]+)/.exec(url)
    const token = match ? match[1] : url.trim()
    this.setData({ loading: true })
    try {
      const data = await get(`/qr/${token}`)
      this.setData({ equipment: data })
      await this.detail(data.equipment_id)
    } catch (e) {
      wx.showModal({ title: '扫码失败', content: e.message, showCancel: false })
    } finally {
      this.setData({ loading: false })
    }
  },

  async detail(id) {
    try {
      const data = await get(`/equipment/${id}`)
      this.setData({ equipment: data })
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  onBookingDate(e) {
    this.setData({ booking: { ...this.data.booking, [e.currentTarget.dataset.field]: e.detail.value } })
  },

  onBookingTime(e) {
    this.setData({ booking: { ...this.data.booking, [e.currentTarget.dataset.field]: e.detail.value } })
  },

  async book() {
    const { equipment, booking } = this.data
    const start = booking.startDate && booking.startTime && `${booking.startDate}T${booking.startTime}`
    const end = booking.endDate && booking.endTime && `${booking.endDate}T${booking.endTime}`
    if (!start || !end) {
      wx.showToast({ title: '请选择开始与结束时间', icon: 'none' })
      return
    }
    try {
      await post('/equipment-bookings', {
        equipment_id: equipment.id,
        start_time: start,
        end_time: end,
      })
      wx.showToast({ title: '预约成功，已生效' })
      this.detail(equipment.id)
    } catch (e) {
      wx.showModal({ title: '预约失败', content: e.message, showCancel: false })
    }
  },

  async borrow() {
    const { equipment } = this.data
    // default borrow window: 24 hours
    const expected = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 19)
    try {
      await post('/equipment-borrows', {
        equipment_id: equipment.id,
        expected_return_time: expected,
      })
      wx.showToast({ title: '借出成功' })
      this.detail(equipment.id)
    } catch (e) {
      wx.showModal({ title: '借用失败', content: e.message, showCancel: false })
    }
  },

  async returnBorrow() {
    const { equipment } = this.data
    try {
      // find my open borrow for this equipment, then return it
      const data = await get('/equipment-borrows?mine=true&page_size=50')
      const borrow = (data.items || []).find(
        (b) => b.equipment_id === equipment.id && (b.status === 'borrowed' || b.status === 'overdue'),
      )
      if (!borrow) {
        wx.showToast({ title: '当前账号没有该设备的借用', icon: 'none' })
        return
      }
      await post(`/equipment-borrows/${borrow.id}/return`)
      wx.showToast({ title: '已归还' })
      this.detail(equipment.id)
    } catch (e) {
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  reportFault() {
    const { equipment } = this.data
    wx.showModal({
      title: '上报故障',
      editable: true,
      placeholderText: '描述故障现象（上报后立即生效）',
      success: async (res) => {
        if (!res.confirm || !res.content) return
        try {
          await post('/equipment-maintenance', {
            equipment_id: equipment.id,
            type: 'fault',
            description: res.content,
          })
          wx.showToast({ title: '已上报，设备管理员会收到通知' })
          this.detail(equipment.id)
        } catch (err) {
          wx.showToast({ title: err.message, icon: 'none' })
        }
      },
    })
  },
})
