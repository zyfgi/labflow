// Research: projects / tasks / experiments / weekly reports, full parity for
// teachers and students. Weekly reports support publish + comment (light
// process — there is no review step).
const { get, post } = require('../../utils/request')

const TABS = ['projects', 'tasks', 'experiments', 'reports']

Page({
  data: {
    tab: 'projects',
    tabs: TABS,
    projects: [],
    tasks: [],
    experiments: [],
    reports: [],
    loading: false,
  },

  onLoad(query) {
    if (query.tab && TABS.includes(query.tab)) this.setData({ tab: query.tab })
  },

  onShow() {
    this.load()
  },

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
    this.load()
  },

  async load() {
    const { tab } = this.data
    this.setData({ loading: true })
    try {
      if (tab === 'projects') {
        const d = await get('/projects?page_size=50')
        this.setData({ projects: d.items || [] })
      } else if (tab === 'tasks') {
        const d = await get('/tasks?page_size=50')
        this.setData({ tasks: d.items || [] })
      } else if (tab === 'experiments') {
        const d = await get('/experiments?page_size=50')
        this.setData({ experiments: d.items || [] })
      } else {
        const d = await get('/weekly-reports?page_size=50')
        this.setData({ reports: d.items || [] })
      }
      this.setData({ loading: false })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: e.message, icon: 'none' })
    }
  },

  publishReport(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '发布周报',
      content: '发布后实验室成员可见，之后仍可继续修改。',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await post(`/weekly-reports/${id}/publish`)
          wx.showToast({ title: '已发布，相关老师已收到通知' })
          this.load()
        } catch (err) {
          wx.showToast({ title: err.message, icon: 'none' })
        }
      },
    })
  },

  commentReport(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '评论周报',
      editable: true,
      placeholderText: '写下你的建议或提醒',
      success: async (res) => {
        if (!res.confirm || !res.content) return
        try {
          await post(`/weekly-reports/${id}/comments`, { content: res.content })
          wx.showToast({ title: '评论已添加' })
        } catch (err) {
          wx.showToast({ title: err.message, icon: 'none' })
        }
      },
    })
  },
})
