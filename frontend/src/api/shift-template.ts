import api from './index'

export interface ShiftTemplate {
  id: number
  name: string
  org_id: number | null
  start_time: string
  end_time: string
  duration_hours: number
  color: string
  leader_min: number
  leader_max: number
  leader_pool: number[] | null
  member_min: number
  member_max: number
  apply_days: number[]
  status: number
  created_at: string | null
  updated_at: string | null
  allow_multi_template: boolean
  leader_enabled: boolean
  leader_rotation_frequency: string
  leader_count: number
  leader_use_tag: boolean
  leader_tag_name: string | null
  member_enabled: boolean
  member_rotation_frequency: string
  special_enabled: boolean
  special_rotation_frequency: string
  special_count: number
  special_pool: number[] | null
  special_exclude_from_member: boolean
  constraint_ids: number[] | null
}

export interface ShiftTemplateForm {
  name: string
  org_id: number | null
  start_time: string
  end_time: string
  color: string
  leader_min: number
  leader_max: number
  leader_pool: number[] | null
  member_min: number
  member_max: number
  apply_days: number[]
  allow_multi_template?: boolean
  leader_enabled?: boolean
  leader_rotation_frequency?: string
  leader_count?: number
  leader_use_tag?: boolean
  leader_tag_name?: string | null
  member_enabled?: boolean
  member_rotation_frequency?: string
  special_enabled?: boolean
  special_rotation_frequency?: string
  special_count?: number
  special_pool?: number[] | null
  special_exclude_from_member?: boolean
  constraint_ids?: number[] | null
}

export function getShiftTemplates(params?: {
  org_id?: number
  status?: number
  keyword?: string
}): Promise<ShiftTemplate[]> {
  return api.get('/shift-templates', { params })
}

export function getShiftTemplate(id: number): Promise<ShiftTemplate> {
  return api.get(`/shift-templates/${id}`)
}

export function createShiftTemplate(data: ShiftTemplateForm): Promise<ShiftTemplate> {
  return api.post('/shift-templates', data)
}

export function updateShiftTemplate(id: number, data: Partial<ShiftTemplateForm>): Promise<ShiftTemplate> {
  return api.put(`/shift-templates/${id}`, data)
}

export function deleteShiftTemplate(id: number): Promise<any> {
  return api.delete(`/shift-templates/${id}`)
}

export function copyShiftTemplate(id: number): Promise<ShiftTemplate> {
  return api.post(`/shift-templates/${id}/copy`)
}

export function toggleShiftTemplateStatus(id: number): Promise<ShiftTemplate> {
  return api.put(`/shift-templates/${id}/status`)
}
