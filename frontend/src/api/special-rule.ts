import api from './index'

export interface SpecialRule {
  id: number
  staff_id: number
  rule_type: string
  params: Record<string, any> | null
  effective_from: string | null
  effective_to: string | null
  reason: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SpecialRuleCreate {
  staff_id: number
  rule_type: string
  params?: Record<string, any>
  effective_from?: string | null
  effective_to?: string | null
  reason?: string | null
}

export interface SpecialRuleUpdate {
  rule_type?: string
  params?: Record<string, any>
  effective_from?: string | null
  effective_to?: string | null
  reason?: string | null
}

export function getSpecialRules(params?: { staff_id?: number }): Promise<SpecialRule[]> {
  return api.get('/special-rules', { params })
}

export function getSpecialRule(id: number): Promise<SpecialRule> {
  return api.get(`/special-rules/${id}`)
}

export function createSpecialRule(data: SpecialRuleCreate): Promise<SpecialRule> {
  return api.post('/special-rules', data)
}

export function updateSpecialRule(id: number, data: SpecialRuleUpdate): Promise<SpecialRule> {
  return api.put(`/special-rules/${id}`, data)
}

export function deleteSpecialRule(id: number): Promise<any> {
  return api.delete(`/special-rules/${id}`)
}
