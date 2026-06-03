import api from './index'

export interface SystemConfig {
  system_name: string
  org_name: string
  swap_approval_enabled: boolean
  schedule_approval_enabled: boolean
  admin_receive_all_notifications: string
  [key: string]: any
}

export interface SystemConfigUpdate {
  system_name?: string
  org_name?: string
  swap_approval_enabled?: boolean
  schedule_approval_enabled?: boolean
  admin_receive_all_notifications?: string
  [key: string]: any
}

export function getSystemConfig(): Promise<SystemConfig> {
  return api.get('/system/config')
}

export function getPublicConfig(): Promise<{ system_name: string; org_name: string }> {
  return api.get('/system/config/public')
}

export function updateSystemConfig(data: SystemConfigUpdate): Promise<SystemConfig> {
  return api.put('/system/config', data)
}
