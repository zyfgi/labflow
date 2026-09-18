// LabFlow miniprogram entry. All business data comes from the LabFlow API;
// there is no approval inbox anywhere in this client (notifications only).
const { TOKEN_KEY, USER_KEY } = require('./utils/store')

App({
  globalData: {
    // point this at your deployment (must be HTTPS with a valid certificate)
    apiBase: 'https://lab.example.edu/api/v1',
  },

  onLaunch() {
    const token = wx.getStorageSync(TOKEN_KEY)
    if (token) this.checkSession()
  },

  checkSession() {
    wx.checkSession({
      fail: () => {
        // WeChat session expired; the LabFlow token may still be valid,
        // so only clear the wx-side marker
      },
    })
  },

  getUser() {
    try {
      return JSON.parse(wx.getStorageSync(USER_KEY) || 'null')
    } catch {
      return null
    }
  },

  isLoggedIn() {
    return Boolean(wx.getStorageSync(TOKEN_KEY))
  },
})
