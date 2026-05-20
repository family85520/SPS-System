import api from './index'

export interface Constraint {
  id: number
  rule_type: string
  rule_name: string
  params: Record<string, any>
  priority: number
  scope_type: string
  scope_ids: number[] | null
  enabled: boolean
  is_preset: boolean
  created_at: string | null
  updated_at: string | null
}

export interface ConstraintUpdate {
  rule_name?: string
  params?: Record<string, any>
  priority?: number
  scope_type?: string
  scope_ids?: number[] | null
  enabled?: boolean
}

export interface ConstraintCreate {
  rule_type: string
  rule_name: string
  params: Record<string, any>
  priority?: number
  scope_type?: string
  scope_ids?: number[] | null
  enabled?: boolean
}

export interface BatchPriorityItem {
  id: number
  priority: number
}

export function getConstraints(params?: { enabled?: boolean }): Promise<Constraint[]> {
  return api.get('/constraints', { params })
}

export function getConstraint(id: number): Promise<Constraint> {
  return api.get(`/constraints/${id}`)
}

export function createConstraint(data: ConstraintCreate): Promise<Constraint> {
  return api.post('/constraints', data)
}

export function updateConstraint(id: number, data: ConstraintUpdate): Promise<Constraint> {
  return api.put(`/constraints/${id}`, data)
}

export function deleteConstraint(id: number): Promise<any> {
  return api.delete(`/constraints/${id}`)
}

export function toggleConstraint(id: number): Promise<Constraint> {
  return api.put(`/constraints/${id}/toggle`)
}

export function batchUpdatePriority(items: BatchPriorityItem[]): Promise<any> {
  return api.put('/constraints/batch/priority', { items })
}
