import api from '@/api/index'

export interface ExportScheduleParams {
  start_date: string
  end_date: string
  org_id?: number
  dimension?: 'org' | 'person'
}

export interface ExportStatisticsParams {
  start_date: string
  end_date: string
  org_id?: number
}

/** 通用 blob 下载 */
function triggerDownload(response: any, filename: string) {
  const blob = response?.data ?? response
  if (!(blob instanceof Blob)) return

  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/** 导出排班表 Excel */
export async function downloadScheduleExcel(params: ExportScheduleParams) {
  const res = await api.get('/export/schedule/excel', {
    params,
    responseType: 'blob',
    timeout: 60000,
  })
  const suffix = params.dimension === 'person' ? '按人员' : '按组织'
  triggerDownload(res, `排班表(${suffix})_${params.start_date}_${params.end_date}.xlsx`)
}

/** 导出排班表 PDF */
export async function downloadSchedulePdf(params: ExportScheduleParams) {
  const res = await api.get('/export/schedule/pdf', {
    params,
    responseType: 'blob',
    timeout: 60000,
  })
  const suffix = params.dimension === 'person' ? '按人员' : '按组织'
  triggerDownload(res, `排班表(${suffix})_${params.start_date}_${params.end_date}.pdf`)
}

/** 导出统计报表 Excel */
export async function downloadStatisticsExcel(params: ExportStatisticsParams) {
  const res = await api.get('/export/statistics/excel', {
    params,
    responseType: 'blob',
    timeout: 60000,
  })
  triggerDownload(res, `排班统计_${params.start_date}_${params.end_date}.xlsx`)
}

/** 导出统计报表 PDF */
export async function downloadStatisticsPdf(params: ExportStatisticsParams) {
  const res = await api.get('/export/statistics/pdf', {
    params,
    responseType: 'blob',
    timeout: 60000,
  })
  triggerDownload(res, `排班统计_${params.start_date}_${params.end_date}.pdf`)
}

// ==================== 导出模板管理 ====================

export interface ExportTemplateItem {
  id: number
  name: string
  is_default: boolean
  description: string | null
  created_at: string
}

export async function listTemplates(): Promise<ExportTemplateItem[]> {
  const res = await api.get('/export/templates')
  return (res as any).templates ?? []
}

export async function uploadTemplate(file: File, name: string, isDefault: boolean, desc?: string): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  form.append('name', name)
  form.append('is_default', String(isDefault))
  if (desc) form.append('description', desc)
  return api.post('/export/templates/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function deleteTemplate(id: number): Promise<any> {
  return api.delete(`/export/templates/${id}`)
}

export async function setDefaultTemplate(id: number): Promise<any> {
  return api.post(`/export/templates/${id}/set-default`)
}
