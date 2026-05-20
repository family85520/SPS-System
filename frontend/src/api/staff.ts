import api from './index'

export interface Staff {
  id: number
  name: string
  employee_no: string
  phone: string
  org_id: number
  org_name?: string
  status: number
  tags: string[]
}

export function getStaffs(params?: {
  org_id?: number
  status?: number
  keyword?: string
}): Promise<Staff[]> {
  return api.get('/staffs', { params })
}
