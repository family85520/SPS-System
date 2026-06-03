import api from './index'

export interface Role {
  id: number
  name: string
  code: string
  role_type: string
  permissions: Record<string, any> | null
  is_system: boolean
  created_at: string | null
}

export interface RoleCreate {
  name: string
  code: string
  role_type?: string
  permissions?: Record<string, any>
}

export interface RoleUpdate {
  name?: string
  role_type?: string
  permissions?: Record<string, any>
}

export interface UserRoleAssign {
  role_ids: number[]
}

export interface StaffTagInfo {
  id: number
  name: string
  code: string
  role_type: string
}

export function getPermissionSchema(): Promise<{
  modules: Array<{ key: string; label: string; actions: string[] }>
  actions: Array<{ key: string; label: string }>
}> {
  return api.get('/roles/permission-schema')
}

export function getRoles(): Promise<Role[]> {
  return api.get('/roles')
}

export function getRole(id: number): Promise<Role> {
  return api.get(`/roles/${id}`)
}

export function createRole(data: RoleCreate): Promise<Role> {
  return api.post('/roles', data)
}

export function updateRole(id: number, data: RoleUpdate): Promise<Role> {
  return api.put(`/roles/${id}`, data)
}

export function deleteRole(id: number): Promise<any> {
  return api.delete(`/roles/${id}`)
}

export function getUserRoles(userId: number): Promise<Role[]> {
  return api.get(`/roles/user/${userId}`)
}

export function assignUserRoles(userId: number, data: UserRoleAssign): Promise<any> {
  return api.post(`/roles/user/${userId}`, data)
}

export function getTagOptions(): Promise<{ code: number; data: StaffTagInfo[]; message: string }> {
  return api.get('/roles/options', { params: { type: 'tag' } })
}

export function getStaffTags(staffId: number): Promise<StaffTagInfo[]> {
  return api.get(`/roles/staff/${staffId}/tags`)
}

export function assignStaffTags(staffId: number, roleIds: number[]): Promise<any> {
  return api.post(`/roles/staff/${staffId}/tags`, { role_ids: roleIds })
}

export function removeStaffTag(staffId: number, roleId: number): Promise<any> {
  return api.delete(`/roles/staff/${staffId}/tags/${roleId}`)
}
