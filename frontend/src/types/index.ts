export interface User {
  id: number
  username: string
  name: string
  email: string
  phone: string | null
  avatar_url: string | null
  role: string
  status: string
  must_change_password: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  must_change_password: boolean
  user: User
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface UserOption {
  id: number
  username: string
  name: string
  role: string
}
