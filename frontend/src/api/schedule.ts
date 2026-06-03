import api from './index'

// ==================== 类型定义 ====================

export interface Schedule {
  id: number
  date: string
  shift_id: number
  shift_name: string | null
  shift_color: string | null
  shift_start_time: string | null
  shift_end_time: string | null
  org_id: number
  org_name: string | null
  leader_staff_id: number | null
  leader_name: string | null
  status: number  // 0=草稿 1=已发布 2=已撤回
  source: string  // auto/manual/swap
  published_at: string | null
  published_by: number | null
  created_at: string | null
  updated_at: string | null
  details: ScheduleDetail[]
}

export interface ScheduleDetail {
  id: number
  schedule_id: number
  staff_id: number
  staff_name: string | null
  role_type: string  // leader/member
  is_substitute: boolean
  note: string | null
}

export interface StaffInfo {
  staff_id: number
  name: string
  role_type: string
  is_substitute?: boolean
  note?: string | null
}

export interface CalendarShift {
  schedule_id: number
  shift_template_id: number
  shift_name: string
  shift_color: string
  start_time: string
  end_time: string
  leader: StaffInfo | null
  members: StaffInfo[]
  status: number
  source: string
  conflicts: string[]
}

export interface CalendarDate {
  date: string
  shifts: CalendarShift[]
}

export interface CalendarResponse {
  dates: CalendarDate[]
}

export interface ScheduleListResponse {
  items: Schedule[]
  total: number
}

export interface ScheduleCreateForm {
  date: string
  shift_id: number
  org_id: number
  leader_staff_id?: number | null
  source?: string
}

export interface ScheduleUpdateForm {
  date?: string
  shift_id?: number
  org_id?: number
  leader_staff_id?: number | null
}

export interface AssignStaffForm {
  staff_id: number
  role_type?: string
  is_substitute?: boolean
  note?: string
}

export interface BatchPublishForm {
  schedule_ids: number[]
}

// ==================== API 函数 ====================

export function getSchedules(params?: {
  org_id?: number
  start_date?: string
  end_date?: string
  status?: number
  shift_id?: number
  page?: number
  page_size?: number
}): Promise<ScheduleListResponse> {
  return api.get('/schedules', { params })
}

export function getScheduleCalendar(params: {
  start_date: string
  end_date: string
  org_id?: number
  status?: number
}): Promise<CalendarResponse> {
  return api.get('/schedules/calendar', { params })
}

export function getSchedule(id: number): Promise<Schedule> {
  return api.get(`/schedules/${id}`)
}

export function createSchedule(data: ScheduleCreateForm): Promise<Schedule> {
  return api.post('/schedules', data)
}

export function updateSchedule(id: number, data: ScheduleUpdateForm): Promise<Schedule> {
  return api.put(`/schedules/${id}`, data)
}

export function deleteSchedule(id: number): Promise<any> {
  return api.delete(`/schedules/${id}`)
}

export function assignStaff(scheduleId: number, data: AssignStaffForm): Promise<any> {
  return api.post(`/schedules/${scheduleId}/assign-staff`, data)
}

export function removeStaff(scheduleId: number, staffId: number): Promise<any> {
  return api.post(`/schedules/${scheduleId}/remove-staff`, { staff_id: staffId })
}

export function publishSchedules(scheduleIds: number[]): Promise<any> {
  return api.post('/schedules/publish', { schedule_ids: scheduleIds })
}

export function recallSchedules(scheduleIds: number[]): Promise<any> {
  return api.post('/schedules/recall', { schedule_ids: scheduleIds })
}

export function recallSchedulesByMonth(orgId: number, year: number, month: number): Promise<any> {
  return api.post('/schedules/recall-month', null, { params: { org_id: orgId, year, month } })
}

export function approveSchedules(scheduleIds: number[]): Promise<any> {
  return api.post('/schedules/approve', { schedule_ids: scheduleIds })
}

export function rejectSchedules(scheduleIds: number[]): Promise<any> {
  return api.post('/schedules/reject', { schedule_ids: scheduleIds })
}

export function getStaffSummary(staffId: number, days?: number): Promise<any> {
  return api.get(`/schedules/staff-summary/${staffId}`, { params: { days } })
}

// ==================== 工作量统计 ====================

export interface ScheduleStatisticsItem {
  staff_id: number
  staff_name: string
  employee_no: string
  org_name: string
  total_shifts: number
  total_hours: number
  night_shifts: number
  weekend_shifts: number
  leader_shifts: number
  holiday_shifts: number
  weight_score: number
}

export interface ScheduleStatisticsSummary {
  total_staff: number
  total_shifts: number
  avg_shifts_per_person: number
  avg_hours_per_person: number
  total_night_shifts: number
  total_holiday_shifts: number
}

export interface ScheduleStatisticsResponse {
  period: { start: string; end: string }
  items: ScheduleStatisticsItem[]
  summary: ScheduleStatisticsSummary
}

export function getScheduleStatistics(params: {
  start_date: string
  end_date: string
  org_id?: number
  top?: number
}): Promise<ScheduleStatisticsResponse> {
  return api.get('/schedules/statistics', { params })
}
