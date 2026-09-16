import client from './client'
import type { Page, User } from '@/types'

export interface UserQuery {
  page?: number
  page_size?: number
  role?: string
  status?: string
  keyword?: string
}

export function listUsers(query: UserQuery = {}) {
  return client.get<{ data: Page<User> }>('/users', { params: query })
}

export function createUser(payload: Record<string, unknown>) {
  return client.post<{ data: User }>('/users', payload)
}

export function updateUser(id: number, payload: Record<string, unknown>) {
  return client.patch<{ data: User }>(`/users/${id}`, payload)
}
