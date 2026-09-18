// WeChat login helpers: wx.login -> backend code2Session -> bind or JWT.
// Auto-registration is forbidden: first-time use requires an existing
// LabFlow account plus a one-time PI binding code.
const { TOKEN_KEY, USER_KEY } = require('./store')

function wxLoginCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => (res.code ? resolve(res.code) : reject(new Error('wx.login 失败'))),
      fail: () => reject(new Error('wx.login 失败')),
    })
  })
}

async function session() {
  const code = await wxLoginCode()
  const { request } = require('./request')
  return request('POST', '/wechat/session', { code })
}

async function bind(username, password, bindingCode) {
  const code = await wxLoginCode()
  const { request } = require('./request')
  const data = await request('POST', '/wechat/bind', {
    code,
    username,
    password,
    binding_code: bindingCode,
  })
  wx.setStorageSync(TOKEN_KEY, data.token)
  wx.setStorageSync(USER_KEY, JSON.stringify(data.user))
  return data.user
}

function saveSession(data) {
  wx.setStorageSync(TOKEN_KEY, data.token)
  wx.setStorageSync(USER_KEY, JSON.stringify(data.user))
}

function logout() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(USER_KEY)
}

module.exports = { session, bind, saveSession, logout, wxLoginCode }
