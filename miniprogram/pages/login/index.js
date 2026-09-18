// Login: delegates to the shared bind flow (credentials + one-time code).
const auth = require('../../utils/auth')

Page({
  data: { loading: false, error: '' },

  async onLogin() {
    this.setData({ loading: true, error: '' })
    try {
      const s = await auth.session()
      if (s.bound && s.token) {
        require('../../utils/auth').saveSession(s)
        wx.reLaunch({ url: '/pages/home/index' })
        return
      }
      // not bound: the openid must be attached to an existing account
      wx.setStorageSync('pending_openid_code', s.openid ? 'needs-bind' : 'needs-bind')
      wx.navigateTo({ url: '/pages/bind/index' })
    } catch (e) {
      this.setData({ error: e.message })
    } finally {
      this.setData({ loading: false })
    }
  },
})
