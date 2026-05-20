/**
 * 首页看板 API
 */
import request from '@/utils/request'

export interface DashboardOverview {
  org_count: number
  staff_count: number
  active_rules_count: number
  pending_swap_count: number
  today_duty: Array<{
    shift_name: string
    leader: string
    members: string[]
  }>
  unread_messages: number
  recent_notices: Array<{
    id: number
    title: string
    created_at: string | null
  }>
  constraint_warnings: number
  schedule_status: string
}

/** 获取首页看板数据 */
export function getDashboardOverview() {
  return request.get('/api/dashboard/overview')
}
