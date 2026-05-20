/**
 * 消息系统 API
 */
import request from '@/utils/request'

export interface MessageItem {
  id: number
  receiver_id: number
  sender_id: number | null
  sender_name: string | null
  title: string
  content: string | null
  msg_type: string
  is_read: boolean
  read_time: string | null
  relation_type: string | null
  relation_id: number | null
  created_at: string | null
}

export interface AnnouncementItem {
  id: number
  title: string
  content: string
  publisher_id: number
  publisher_name: string | null
  target_scope: string
  target_ids: string | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface MessageListParams {
  msg_type?: string
  is_read?: boolean
  keyword?: string
  page?: number
  size?: number
}

// ========== 消息 API ==========

/** 获取消息列表 */
export function getMessages(params: MessageListParams) {
  return request.get('/api/messages', { params })
}

/** 获取未读消息数量 */
export function getUnreadCount() {
  return request.get('/api/messages/unread-count')
}

/** 标记单条消息已读 */
export function markMessageRead(messageId: number) {
  return request.put(`/api/messages/${messageId}/read`)
}

/** 全部标记已读 */
export function markAllMessagesRead() {
  return request.put('/api/messages/read-all')
}

// ========== 公告 API ==========

/** 获取公告列表 */
export function getAnnouncements(params?: { page?: number; size?: number; is_active?: boolean }) {
  return request.get('/api/announcements', { params })
}

/** 发布公告 */
export function createAnnouncement(data: {
  title: string
  content: string
  target_scope?: string
  target_ids?: string
}) {
  return request.post('/api/announcements', data)
}

/** 编辑公告 */
export function updateAnnouncement(annId: number, data: {
  title?: string
  content?: string
  is_active?: boolean
}) {
  return request.put(`/api/announcements/${annId}`, data)
}

/** 撤回公告 */
export function withdrawAnnouncement(annId: number) {
  return request.post(`/api/announcements/${annId}/withdraw`)
}

/** 永久隐藏公告（仅已撤回的可操作） */
export function deleteAnnouncement(annId: number) {
  return request.delete(`/api/announcements/${annId}`)
}

// ========== 选项数据 API ==========

/** 获取组织选项列表 */
export function getOrgOptions() {
  return request.get('/api/options/organizations')
}

/** 获取角色选项列表 */
export function getRoleOptions() {
  return request.get('/api/options/roles')
}

/** 搜索人员选项 */
export function searchStaffOptions(keyword: string) {
  return request.get('/api/options/staffs', { params: { keyword } })
}
