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
  rotation_frequency: string
  schedule_mode: string
  status: number
  created_at: string | null
  updated_at: string | null
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
  rotation_frequency: string
  schedule_mode: string
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
