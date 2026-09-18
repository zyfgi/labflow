// Minimal API client. Every request carries the LabFlow JWT; the server
// enforces the same RBAC as the web client.
const { TOKEN_KEY } = require('./store')

function request(method, path, data) {
  const app = getApp()
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method,
      data,
      header: {
        Authorization: 'Bearer ' + (wx.getStorageSync(TOKEN_KEY) || ''),
        'Content-Type': 'application/json',
      },
      success(res) {
        if (res.statusCode === 401) {
          wx.removeStorageSync(TOKEN_KEY)
          wx.reLaunch({ url: '/pages/login/index' })
          reject(new Error('未登录或登录已过期'))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data && res.data.data !== undefined ? res.data.data : res.data)
        } else {
          const detail = res.data && res.data.detail ? res.data.detail : '请求失败'
          reject(new Error(detail))
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络错误'))
      },
    })
  })
}

module.exports = {
  get: (path) => request('GET', path),
  post: (path, data) => request('POST', path, data),
  patch: (path, data) => request('PATCH', path, data),
  del: (path) => request('DELETE', path),
}
