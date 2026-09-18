import client from './client'

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

export function wechatSession(code: string) {
  return client.post<{ data: { openid: string; bound: boolean; token: string | null } }>(
    '/wechat/session',
    { code },
  )
}

export function wechatBind(payload: { code: string; username: string; password: string; binding_code: string }) {
  return client.post<{ data: { token: string } }>('/wechat/bind', payload)
}

export function wechatUnbind() {
  return client.delete('/wechat/bind')
}
