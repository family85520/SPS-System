import api from './index'

export interface OrgNode {
  id: number
  name: string
  parent_id: number | null
  level: number
  sort_order: number
  status: number
  created_at: string
  updated_at: string
  children: OrgNode[]
}

export interface OrgCreateForm {
  name: string
  parent_id: number | null
  sort_order?: number
}

export interface OrgUpdateForm {
  name?: string
  sort_order?: number
  status?: number
}

export function getOrgTree(include_disabled?: boolean): Promise<OrgNode[]> {
  return api.get('/organizations/tree', { params: { include_disabled } })
}

export function getOrgList(params?: {
  parent_id?: number
  include_disabled?: boolean
}): Promise<OrgNode[]> {
  return api.get('/organizations', { params })
}

export function createOrg(data: OrgCreateForm): Promise<OrgNode> {
  return api.post('/organizations', data)
}

export function updateOrg(id: number, data: OrgUpdateForm): Promise<OrgNode> {
  return api.put(`/organizations/${id}`, data)
}

export function deleteOrg(id: number): Promise<any> {
  return api.delete(`/organizations/${id}`)
}
