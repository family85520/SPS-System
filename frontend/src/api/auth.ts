import api from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: number
  username: string
  roles: string[]
  must_change_password: boolean
}

export interface UserInfo {
  id: number
  username: string
  staff_id: number | null
  staff_name: string | null
  status: number
  roles: string[]
  permissions: Record<string, any>
  last_login_at: string | null
}

export function login(data: LoginRequest): Promise<TokenResponse> {
  return api.post('/auth/login', data)
}

export function getUserInfo(): Promise<UserInfo> {
  return api.get('/auth/me')
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return api.post('/auth/change-password', data)
}

export function forceChangePassword(data: { new_password: string }) {
  return api.post('/auth/force-change-password', data)
}
