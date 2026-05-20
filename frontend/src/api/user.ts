import api from './index'

export interface UserItem {
  id: number
  username: string
  staff_id: number | null
  staff_name: string | null
  status: number
  roles: string[]
  role_ids: number[]
  created_at: string | null
  updated_at: string | null
  last_login_at: string | null
}

export interface UserCreateParams {
  username: string
  password: string
  staff_id?: number | null
  status?: number
  role_ids?: number[]
  must_change_password?: boolean
  // 同步创建人员
  create_staff?: boolean
  staff_name?: string
  employee_no?: string
  phone?: string
  org_id?: number
  staff_tags?: string[]
}

export interface UserUpdateParams {
  staff_id?: number | null
  status?: number
  role_ids?: number[]
}

export function getUserList(params: {
  keyword?: string
  status?: number
  role_id?: number
  page?: number
  page_size?: number
}) {
  return api.get('/users', { params })
}

export function getUserDetail(id: number) {
  return api.get(`/users/${id}`)
}

export function createUser(data: UserCreateParams) {
  return api.post('/users', data)
}

export function updateUser(id: number, data: UserUpdateParams) {
  return api.put(`/users/${id}`, data)
}

export function resetPassword(id: number, new_password: string) {
  return api.put(`/users/${id}/password`, { new_password })
}

export function deleteUser(id: number) {
  return api.delete(`/users/${id}`)
}

export function getStaffOptions(keyword?: string) {
  return api.get('/options/staffs', { params: { keyword } })
}
