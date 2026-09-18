// Login: delegates to the shared bind flow (credentials + one-time code).
const auth = require('../../utils/auth')

Page({
  data: { loading: false, error: '' },

  async onLogin() {
    this.setData({ loading: true, error: '' })
    try {
      const s = await auth.session()
      if (s.bound && s.token) {
        auth.saveSession(s)
        wx.reLaunch({ url: '/pages/home/index' })
        return
      }

    } catch (e) {
      this.setData({ error: e.message })
    } finally {
      this.setData({ loading: false })
    }
  },
})
