# LabFlow 微信小程序

原生微信小程序（无第三方框架），覆盖主要业务：首页（通知/动态/需关注）、成员、科研（项目/任务/实验/周报）、设备扫码（预约/借用/归还/故障上报）、AI 助手、我的。

**没有审批收件箱** — 系统采用轻流程协同：操作立即生效，相关人员收到站内通知，全程留痕。

## 目录结构

```
miniprogram/
├── app.js / app.json / app.wxss     # 入口与全局样式
├── utils/
│   ├── request.js                   # 带 JWT 的 API 客户端
│   ├── auth.js                      # wx.login -> code2Session -> 绑定/登录
│   └── store.js                     # token / user 存储 key
└── pages/
    ├── home/          # 通知 + 最近动态 + 需关注
    ├── members/       # 成员列表（read collaboration）
    ├── research/      # 项目/任务/实验/周报（周报可发布/评论）
    ├── scan/          # 扫设备二维码 -> 预约/借用/归还/故障
    ├── ai/            # AI 问答（只读检索）
    ├── me/            # 个人 + 解绑微信
    ├── login/         # 微信登录入口
    ├── bind/          # 首次绑定（账号密码 + PI 一次性绑定码）
    ├── notifications/ # 通知中心
    └── equipment/     # 设备详情（扫码/通知跳转进入）
```

## 接入步骤

1. `app.js` 中把 `globalData.apiBase` 改成你的部署地址（必须 HTTPS 且证书有效），
   例如 `https://lab.example.edu/api/v1`。
2. 微信公众平台注册小程序，将 `AppID` 填入 `project.config.json`（用微信开发者工具导入本目录时生成）。
3. 服务端 `.env` 配置：
   ```
   LABFLOW_WECHAT_APPID=wx1234567890
   LABFLOW_WECHAT_SECRET=your-secret
   ```
   并在 Web 端「系统设置 → 基础设置」打开「微信小程序入口」。
4. 成员首次使用：PI 在「系统设置 → 微信绑定码」生成一次性绑定码（30 分钟有效），
   成员在小程序「绑定账号」页输入 LabFlow 账号密码 + 绑定码完成绑定。
   **禁止自动注册。**

## tab 图标

`app.json` 引用了 `assets/tab-*.png`（81×81 px）。可用任意 5 组图标补齐
（首页/成员/科研/扫码/我的，普通+选中各一张），或在开发者工具中临时删除
tabBar 的 iconPath 字段（仅文字 tab）。

## 安全说明

- 所有请求携带 LabFlow JWT，服务端 RBAC 与 Web 端完全一致。
- 二维码只是"指针"不是凭证：扫码后仍需登录，按角色鉴权。
- 绑定码一次性、短时效、用后即焚；审计日志不记录其明文。
