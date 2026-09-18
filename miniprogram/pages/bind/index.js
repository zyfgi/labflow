// First-time WeChat binding: LabFlow username/password + PI one-time code.
// No auto-registration (manual §38).
const auth = require('../../utils/auth')

Page({
  data: {
    username: '',
    password: '',
    bindingCode: '',
    loading: false,
    error: '',
  },

  onInput(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value })
  },

  async onBind() {
    const { username, password, bindingCode } = this.data
    if (!username || !password || !bindingCode) {
      this.setData({ error: '请填写账号、密码和 PI 提供的绑定码' })
      return
    }
    this.setData({ loading: true, error: '' })
    try {
      await auth.bind(username, password, bindingCode)
      wx.reLaunch({ url: '/pages/home/index' })
    } catch (e) {
      this.setData({ error: e.message })
    } finally {
      this.setData({ loading: false })
    }
  },
})
