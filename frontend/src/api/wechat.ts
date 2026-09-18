import client from './client'

// Web 端只用到 PI 的绑定码管理；登录/绑定/解绑在微信小程序内完成
// （见 miniprogram/），Web 前端不提供扫码登录入口。
export interface BindingCode {
  id: number
  code: string
  remark: string | null
  created_at: string | null
  expires_at: string
  state: 'valid' | 'used' | 'expired'
}

export function listBindingCodes() {
  return client.get<{ data: BindingCode[] }>('/wechat/binding-codes')
}

export function createBindingCode(payload: { remark?: string; ttl_minutes?: number }) {
  return client.post<{ data: { code: string; expires_at: string } }>(
    '/wechat/binding-codes',
    payload,
  )
}
