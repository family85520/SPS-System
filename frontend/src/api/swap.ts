import request from '@/utils/request'

export interface SwapRequestItem {
  id: number
  request_no: string
  swap_type: string
  requester_id: number
  requester_name: string | null
  requester_schedule_id: number
  requester_schedule_date: string | null
  requester_shift_name: string | null
  target_id: number | null
  target_name: string | null
  target_schedule_id: number | null
  target_schedule_date: string | null
  target_shift_name: string | null
  claimer_id: number | null
  claimer_name: string | null
  reason: string | null
  status: string
  approved_by: number | null
  approver_name: string | null
  approved_at: string | null
  approve_comment: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SwapCreateParams {
  swap_type: string
  requester_schedule_id: number
  target_id?: number
  target_schedule_id?: number
  reason?: string
}

export function getSwapList(params: {
  role?: string
  status?: string
  swap_type?: string
  page?: number
  page_size?: number
}) {
  return request.get('/api/swaps', { params })
}

export function getAllSwapList(params: {
  status?: string
  swap_type?: string
  page?: number
  page_size?: number
}) {
  return request.get('/api/swaps/all', { params })
}

export function getSwapDetail(id: number) {
  return request.get(`/api/swaps/${id}`)
}

export function createSwap(data: SwapCreateParams) {
  return request.post('/api/swaps', data)
}

export function confirmSwap(id: number) {
  return request.put(`/api/swaps/${id}/confirm`)
}

export function claimSwap(id: number) {
  return request.put(`/api/swaps/${id}/claim`)
}

export function approveSwap(id: number, comment?: string) {
  return request.put(`/api/swaps/${id}/approve`, { approve_comment: comment })
}

export function rejectSwap(id: number, comment?: string) {
  return request.put(`/api/swaps/${id}/reject`, { approve_comment: comment })
}

export function cancelSwap(id: number) {
  return request.put(`/api/swaps/${id}/cancel`)
}

export function getMySchedules(params: { start_date?: string; end_date?: string }) {
  return request.get('/api/schedules', { params })
}
