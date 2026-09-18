// Me: profile, wechat unbind (with confirm), notifications entry.
const auth = require('../../utils/auth')
const { del } = require('../../utils/request')

Page({
  data: { user: null },

  onShow() {
    this.setData({ user: getApp().getUser() })
  },

  goNotifications() {
    wx.navigateTo({ url: '/pages/notifications/index' })
  },

  unbind() {
    wx.showModal({
      title: '解除微信绑定',
      content: '解绑后将无法用微信登录，需要重新绑定。确认解除？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await del('/wechat/bind')
          wx.showToast({ title: '已解绑' })
        } catch (e) {
          wx.showToast({ title: e.message, icon: 'none' })
        }
      },
    })
  },

  logout() {
    auth.logout()
    wx.reLaunch({ url: '/pages/login/index' })
  },
})
