import client from './client'
import type { LoginResult, User, UserOption } from '@/types'

export function login(username: string, password: string) {
  return client.post<{ data: LoginResult; message: string }>('/auth/login', { username, password })
}

export function logout() {
  return client.post('/auth/logout')
}

export function me() {
  return client.get<{ data: User; message: string }>('/auth/me')
}

export function changePassword(oldPassword: string, newPassword: string) {
  return client.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export function userOptions(): Promise<UserOption[]> {
  return client.get('/users/options').then((r) => r.data.data)
}
