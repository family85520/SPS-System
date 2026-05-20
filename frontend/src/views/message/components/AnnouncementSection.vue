<template>
  <div class="announcement-section">
    <div class="announcement-header">
      <span class="announcement-title">公告通知</span>
      <el-button
        v-if="isAdmin"
        type="primary"
        size="small"
        @click="showPublishDialog = true"
      >
        发布公告
      </el-button>
    </div>

    <!-- 公告列表 -->
    <div class="announcement-list" v-loading="loading">
      <div
        v-for="ann in announcements"
        :key="ann.id"
        class="announcement-item"
        @click="handleViewAnnouncement(ann)"
      >
        <div class="announcement-item__title">
          <el-icon><Document /></el-icon>
          {{ ann.title }}
          <el-tag
            v-if="!ann.is_active"
            type="warning"
            size="small"
            class="withdrawn-tag"
          >
            已撤回
          </el-tag>
        </div>
        <div class="announcement-item__meta">
          <span>{{ ann.publisher_name }}</span>
          <span>{{ ann.created_at }}</span>
        </div>
      </div>
      <el-empty v-if="!loading && announcements.length === 0" description="暂无公告" />
    </div>

    <!-- 公告详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="currentAnnouncement?.title || '公告详情'"
      width="600px"
    >
      <div class="announcement-detail" v-if="currentAnnouncement">
        <div class="announcement-detail__meta">
          发布人：{{ currentAnnouncement.publisher_name }}
          &nbsp;&nbsp;|&nbsp;&nbsp;
          {{ currentAnnouncement.created_at }}
          <el-tag
            v-if="!currentAnnouncement.is_active"
            type="warning"
            size="small"
            style="margin-left: 8px"
          >
            已撤回
          </el-tag>
        </div>
        <div class="announcement-detail__content">
          {{ currentAnnouncement.content }}
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button
          v-if="isAdmin && currentAnnouncement?.is_active"
          type="warning"
          @click="handleWithdraw"
        >
          撤回公告
        </el-button>
        <el-button
          v-if="isAdmin && currentAnnouncement && !currentAnnouncement.is_active"
          type="danger"
          @click="handlePermanentDelete"
        >
          删除公告
        </el-button>
      </template>
    </el-dialog>

    <!-- 发布公告对话框 -->
    <el-dialog
      v-model="showPublishDialog"
      title="发布公告"
      width="600px"
      @closed="resetForm"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="请输入公告标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="请输入公告内容"
          />
        </el-form-item>
        <el-form-item label="发送范围">
          <el-select v-model="form.target_scope" style="width: 100%" @change="onScopeChange">
            <el-option label="全部人员" value="all" />
            <el-option label="指定组织" value="org" />
            <el-option label="指定角色" value="role" />
            <el-option label="指定人员" value="staff" />
          </el-select>
        </el-form-item>

        <!-- 指定组织 -->
        <el-form-item v-if="form.target_scope === 'org'" label="选择组织" required>
          <el-select
            v-model="selectedOrgIds"
            multiple
            filterable
            placeholder="请选择组织"
            style="width: 100%"
            :loading="orgLoading"
          >
            <el-option
              v-for="org in orgList"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
          <div v-if="!orgLoading && orgList.length === 0" class="empty-tip">
            暂无可用组织数据
          </div>
        </el-form-item>

        <!-- 指定角色 -->
        <el-form-item v-if="form.target_scope === 'role'" label="选择角色" required>
          <el-select
            v-model="selectedRoleIds"
            multiple
            filterable
            placeholder="请选择角色"
            style="width: 100%"
            :loading="roleLoading"
          >
            <el-option
              v-for="role in roleList"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
          <div v-if="!roleLoading && roleList.length === 0" class="empty-tip">
            暂无可用角色数据
          </div>
        </el-form-item>

        <!-- 指定人员 -->
        <el-form-item v-if="form.target_scope === 'staff'" label="选择人员" required>
          <el-select
            v-model="selectedStaffIds"
            multiple
            filterable
            remote
            :remote-method="searchStaff"
            placeholder="输入姓名搜索人员"
            style="width: 100%"
            :loading="staffLoading"
            reserve-keyword
          >
            <el-option
              v-for="s in staffList"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            >
              <span>{{ s.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 12px">{{ s.org_name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPublishDialog = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="handlePublish">
          发布
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getAnnouncements,
  createAnnouncement,
  withdrawAnnouncement,
  deleteAnnouncement,
  getOrgOptions,
  getRoleOptions,
  searchStaffOptions,
} from '@/api/message'
import type { AnnouncementItem } from '@/api/message'

const authStore = useAuthStore()
const isAdmin = computed(() => {
  return authStore.hasRole('admin') || authStore.hasRole('scheduler')
})

const announcements = ref<AnnouncementItem[]>([])
const loading = ref(false)
const showDetailDialog = ref(false)
const showPublishDialog = ref(false)
const publishing = ref(false)
const currentAnnouncement = ref<AnnouncementItem | null>(null)

const form = ref({
  title: '',
  content: '',
  target_scope: 'all',
})

// ── 范围选择器 ──
const selectedOrgIds = ref<number[]>([])
const selectedRoleIds = ref<number[]>([])
const selectedStaffIds = ref<number[]>([])

const orgList = ref<Array<{ id: number; name: string }>>([])
const roleList = ref<Array<{ id: number; name: string }>>([])
const staffList = ref<Array<{ id: number; name: string; org_name: string }>>([])

const orgLoading = ref(false)
const roleLoading = ref(false)
const staffLoading = ref(false)

// ── 加载组织选项 ──
const fetchOrgList = async () => {
  orgLoading.value = true
  try {
    const { data: res } = await getOrgOptions()
    if (res.code === 200) {
      orgList.value = res.data || []
    }
  } catch {
    orgList.value = []
  } finally {
    orgLoading.value = false
  }
}

// ── 加载角色选项 ──
const fetchRoleList = async () => {
  roleLoading.value = true
  try {
    const { data: res } = await getRoleOptions()
    if (res.code === 200) {
      roleList.value = res.data || []
    }
  } catch {
    roleList.value = []
  } finally {
    roleLoading.value = false
  }
}

// ── 搜索人员选项 ──
const searchStaff = async (keyword: string) => {
  if (!keyword || keyword.length < 1) {
    staffList.value = []
    return
  }
  staffLoading.value = true
  try {
    const { data: res } = await searchStaffOptions(keyword)
    if (res.code === 200) {
      staffList.value = res.data || []
    }
  } catch {
    staffList.value = []
  } finally {
    staffLoading.value = false
  }
}

// ── 切换范围时清空已选 ──
const onScopeChange = () => {
  selectedOrgIds.value = []
  selectedRoleIds.value = []
  selectedStaffIds.value = []
}

// ── 构建 target_ids ──
const buildTargetIds = (): string | null => {
  if (form.value.target_scope === 'org' && selectedOrgIds.value.length > 0) {
    return JSON.stringify(selectedOrgIds.value)
  }
  if (form.value.target_scope === 'role' && selectedRoleIds.value.length > 0) {
    return JSON.stringify(selectedRoleIds.value)
  }
  if (form.value.target_scope === 'staff' && selectedStaffIds.value.length > 0) {
    return JSON.stringify(selectedStaffIds.value)
  }
  return null
}

// ── 获取公告列表（不传 is_active，显示全部未删除的） ──
const fetchAnnouncements = async () => {
  loading.value = true
  try {
    const { data: res } = await getAnnouncements({ size: 50 })
    if (res.code === 200) {
      announcements.value = res.data.list
    }
  } catch {
    ElMessage.error('获取公告列表失败')
  } finally {
    loading.value = false
  }
}

const handleViewAnnouncement = (ann: AnnouncementItem) => {
  currentAnnouncement.value = ann
  showDetailDialog.value = true
}

// ── 发布公告 ──
const handlePublish = async () => {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  if (form.value.target_scope === 'org' && selectedOrgIds.value.length === 0) {
    ElMessage.warning('请至少选择一个组织')
    return
  }
  if (form.value.target_scope === 'role' && selectedRoleIds.value.length === 0) {
    ElMessage.warning('请至少选择一个角色')
    return
  }
  if (form.value.target_scope === 'staff' && selectedStaffIds.value.length === 0) {
    ElMessage.warning('请至少选择一个人员')
    return
  }

  publishing.value = true
  try {
    const payload = {
      title: form.value.title,
      content: form.value.content,
      target_scope: form.value.target_scope,
      target_ids: buildTargetIds(),
    }
    const { data: res } = await createAnnouncement(payload)
    if (res.code === 200) {
      ElMessage.success('公告发布成功')
      showPublishDialog.value = false
      fetchAnnouncements()
    }
  } catch {
    ElMessage.error('发布失败')
  } finally {
    publishing.value = false
  }
}

// ── 撤回公告 ──
const handleWithdraw = async () => {
  if (!currentAnnouncement.value) return
  try {
    await ElMessageBox.confirm(
      '确认撤回此公告？撤回后公告将标记为"已撤回"，相关人员将收到通知。',
      '撤回公告',
      { confirmButtonText: '确认撤回', cancelButtonText: '取消', type: 'warning' }
    )
    const { data: res } = await withdrawAnnouncement(currentAnnouncement.value.id)
    if (res.code === 200) {
      ElMessage.success('公告已撤回')
      showDetailDialog.value = false
      fetchAnnouncements()
    }
  } catch {
    // 用户取消
  }
}

// ── 永久隐藏公告（仅已撤回的可操作） ──
const handlePermanentDelete = async () => {
  if (!currentAnnouncement.value) return
  try {
    await ElMessageBox.confirm(
      '删除后该公告将从前端完全隐藏，仅数据库保留历史记录。确认删除？',
      '删除公告',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'error' }
    )
    const { data: res } = await deleteAnnouncement(currentAnnouncement.value.id)
    if (res.code === 200) {
      ElMessage.success('公告已删除')
      showDetailDialog.value = false
      fetchAnnouncements()
    }
  } catch {
    // 用户取消
  }
}

const resetForm = () => {
  form.value = { title: '', content: '', target_scope: 'all' }
  selectedOrgIds.value = []
  selectedRoleIds.value = []
  selectedStaffIds.value = []
  staffList.value = []
}

// 打开发布对话框时加载选项数据
watch(showPublishDialog, (val) => {
  if (val) {
    fetchOrgList()
    fetchRoleList()
  }
})

onMounted(fetchAnnouncements)
</script>

<style scoped>
.announcement-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.announcement-title {
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
}

.announcement-list {
  max-height: 500px;
  overflow-y: auto;
}

.announcement-item {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 4px;
}

.announcement-item:hover {
  background: #f5f7fa;
}

.announcement-item__title {
  font-size: 14px;
  font-weight: 500;
  color: #1F2D3D;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.withdrawn-tag {
  flex-shrink: 0;
}

.announcement-item__meta {
  font-size: 12px;
  color: #8492a6;
  display: flex;
  gap: 12px;
}

.announcement-detail__meta {
  font-size: 13px;
  color: #8492a6;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
}

.announcement-detail__content {
  font-size: 14px;
  color: #556173;
  line-height: 1.8;
  white-space: pre-wrap;
  padding: 16px;
  background: #f9fafb;
  border-radius: 6px;
}

.empty-tip {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 4px;
}
</style>
