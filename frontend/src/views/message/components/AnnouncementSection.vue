<template>
  <div class="announcement-section">
    <!-- 头部 -->
    <div class="announcement-header">
      <span class="announcement-title">
        <el-icon :size="20"><Bell /></el-icon>
        公告通知
      </span>
      <el-button
        v-if="isAdmin"
        class="btn-neo-primary btn-neo-sm"
        @click="showPublishDialog = true"
      >
        <el-icon><Plus /></el-icon>
        <span>发布公告</span>
      </el-button>
    </div>

    <!-- 公告列表 -->
    <div class="announcement-list" v-loading="loading" element-loading-text="加载中...">
      <div
        v-for="(ann, index) in announcements"
        :key="ann.id"
        :style="{ animationDelay: `${index * 0.05}s` }"
        :class="[
          'announcement-item',
          { 'is-highlighted': highlightedId === ann.id },
          'neo-list-item',
          'neo-list-item--clickable',
        ]"
        @click="handleViewAnnouncement(ann)"
      >
        <div class="announcement-item__title">
          <el-icon :size="16"><Document /></el-icon>
          <span class="announcement-item__text">{{ ann.title }}</span>
          <el-tag
            v-if="!ann.is_active"
            type="warning"
            size="small"
            effect="dark"
            class="withdrawn-tag"
          >
            已撤回
          </el-tag>
        </div>
        <div class="announcement-item__meta">
          <span class="announcement-item__publisher">{{ ann.publisher_name }}</span>
          <span class="announcement-item__time">{{ ann.created_at }}</span>
        </div>
      </div>
      <div v-if="!loading && announcements.length === 0" class="empty-state">
        <el-icon :size="48"><Bell /></el-icon>
        <p>暂无公告</p>
      </div>
    </div>

    <!-- 公告详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="currentAnnouncement?.title || '公告详情'"
      width="600px"
      class="neo-dialog"
      @closed="currentAnnouncement = null"
    >
      <div class="announcement-detail" v-if="currentAnnouncement">
        <div class="announcement-detail__meta">
          <div class="announcement-detail__publisher">
            <el-icon><User /></el-icon>
            <span>发布人：{{ currentAnnouncement.publisher_name }}</span>
          </div>
          <span class="announcement-detail__time">{{ currentAnnouncement.created_at }}</span>
          <el-tag
            v-if="!currentAnnouncement.is_active"
            type="warning"
            size="small"
            effect="dark"
            class="withdrawn-tag"
          >
            已撤回
          </el-tag>
        </div>
        <div class="announcement-detail__content">
          {{ currentAnnouncement.content }}
        </div>
      </div>
      <template #footer>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="showDetailDialog = false">
          关闭
        </el-button>
        <el-button
          v-if="isAdmin && currentAnnouncement?.is_active"
          class="btn-neo-warning btn-neo-sm"
          @click="handleWithdraw"
        >
          <el-icon><RefreshLeft /></el-icon>
          <span>撤回公告</span>
        </el-button>
        <el-button
          v-if="isAdmin && currentAnnouncement && !currentAnnouncement.is_active"
          class="btn-neo-danger btn-neo-sm"
          @click="handlePermanentDelete"
        >
          <el-icon><Delete /></el-icon>
          <span>删除公告</span>
        </el-button>
      </template>
    </el-dialog>

    <!-- 发布公告对话框 -->
    <el-dialog
      v-model="showPublishDialog"
      title="发布公告"
      width="640px"
      class="neo-dialog"
      @closed="resetForm"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required>
          <el-input
            v-model="form.title"
            placeholder="请输入公告标题"
            maxlength="200"
            show-word-limit
            class="neo-input-form"
          />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="请输入公告内容"
            class="neo-textarea"
          />
        </el-form-item>
        <el-form-item label="发送范围">
          <el-select v-model="form.target_scope" class="neo-input-form" @change="onScopeChange">
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
            class="neo-input-form"
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
            class="neo-input-form"
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
            class="neo-input-form"
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

      <!-- 提示卡片 -->
      <div class="alert-card">
        <span class="alert-card__icon">ℹ</span>
        <span class="alert-card__content">公告发布后将即时通知相关人员，请确认内容无误后再发布。</span>
      </div>

      <template #footer>
        <el-button class="btn-neo-ghost btn-neo-sm" @click="showPublishDialog = false">
          取消
        </el-button>
        <el-button class="btn-neo-primary btn-neo-sm" :loading="publishing" @click="handlePublish">
          <el-icon><Upload /></el-icon>
          <span>发布</span>
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { Document, Bell, User, RefreshLeft, Delete, Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
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
import { useConfirm } from '@/composables/useConfirm'
import type { AnnouncementItem } from '@/api/message'

const authStore = useAuthStore()
const { confirmWarning, confirmDanger } = useConfirm()
const isAdmin = computed(() => {
  return authStore.hasRole('admin') || authStore.hasRole('scheduler')
})

const props = defineProps<{
  highlightId?: number
}>()

const announcements = ref<AnnouncementItem[]>([])
const loading = ref(false)
const showDetailDialog = ref(false)
const showPublishDialog = ref(false)
const publishing = ref(false)
const currentAnnouncement = ref<AnnouncementItem | null>(null)
const highlightedId = ref<number | null>(null)

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

// ── 获取公告列表 ──
const fetchAnnouncements = async () => {
  loading.value = true
  try {
    const { data: res } = await getAnnouncements({ size: 50 })
    if (res.code === 200) {
      announcements.value = res.data.list
      if (props.highlightId != null) {
        doHighlight(props.highlightId)
      }
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
    await confirmWarning(
      '确认撤回此公告？撤回后公告将标记为"已撤回"，相关人员将收到通知。',
      '撤回公告',
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

// ── 永久删除公告 ──
const handlePermanentDelete = async () => {
  if (!currentAnnouncement.value) return
  try {
    await confirmDanger(
      '删除后该公告将从前端完全隐藏，仅数据库保留历史记录。确认删除？',
      '删除公告',
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

watch(showPublishDialog, (val) => {
  if (val) {
    fetchOrgList()
    fetchRoleList()
  }
})

watch(
  () => props.highlightId,
  (newId) => {
    if (newId != null && announcements.value.length > 0) {
      doHighlight(newId)
    }
  },
)

function doHighlight(id: number) {
  highlightedId.value = id
  const ann = announcements.value.find((a) => a.id === id)
  if (ann) {
    setTimeout(() => {
      handleViewAnnouncement(ann)
      highlightedId.value = null
    }, 500)
  } else {
    setTimeout(() => { highlightedId.value = null }, 2000)
  }
}

onMounted(() => {
  fetchAnnouncements()
  if (props.highlightId != null && announcements.value.length > 0) {
    doHighlight(props.highlightId)
  }
})
</script>

<style scoped>
.announcement-section {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ========== 头部 ========== */
.announcement-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--neo-color-bg-primary);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  box-shadow: var(--neo-shadow-md);
}

.announcement-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 900;
  color: var(--neo-color-text-primary);
}

.announcement-title .el-icon {
  color: var(--neo-color-accent-blue);
}

/* ========== 公告列表 ========== */
.announcement-list {
  flex: 1;
  max-height: 500px;
  overflow-y: auto;
  padding: 8px;
}

.announcement-item {
  padding: 12px 14px;
  margin-bottom: 6px;
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  background: var(--neo-color-bg-card);
  box-shadow: var(--neo-shadow-active);
  transition: all 0.15s ease;
  animation: slide-in-left 0.3s ease both;
}

.announcement-item:hover {
  background: var(--neo-color-bg-primary);
  box-shadow: var(--neo-shadow-default);
  transform: translate(var(--neo-translate-hover), var(--neo-translate-hover));
}

.announcement-item.is-highlighted {
  background: var(--neo-color-accent-yellow);
  border-color: var(--neo-color-border);
  box-shadow: var(--neo-shadow-default);
  animation: pulse-highlight 1s ease-in-out 3, slide-in-left 0.3s ease both;
}

@keyframes pulse-highlight {
  0%, 100% { box-shadow: var(--neo-shadow-default); }
  50%      { box-shadow: var(--neo-shadow-lg); }
}

.announcement-item__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
  margin-bottom: 4px;
}

.announcement-item__title .el-icon {
  color: var(--neo-color-accent-blue);
  flex-shrink: 0;
}

.withdrawn-tag {
  flex-shrink: 0;
  margin-left: 4px;
}

.announcement-item__meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--neo-color-text-secondary);
  font-weight: 600;
}

/* ========== 详情弹窗内容 ========== */
.announcement-detail__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--neo-color-text-secondary);
  margin-bottom: 16px;
  flex-wrap: wrap;
  font-weight: 600;
}

.announcement-detail__publisher {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
  color: var(--neo-color-text-primary);
}

.announcement-detail__publisher .el-icon {
  color: var(--neo-color-accent-blue);
}

.announcement-detail__content {
  font-size: 14px;
  color: var(--neo-color-text-primary);
  line-height: 1.8;
  white-space: pre-wrap;
  padding: 16px;
  background: var(--neo-color-bg-primary);
  border: var(--neo-border-thick) solid var(--neo-color-border);
  border-radius: var(--neo-radius-md);
  font-weight: 500;
  box-shadow: var(--neo-shadow-active);
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--neo-color-text-muted);
  gap: 12px;
}

.empty-state .el-icon {
  color: #CCCCCC;
  border: 2px solid #E0E0E0;
  border-radius: var(--neo-radius-md);
  padding: 8px;
  box-shadow: 2px 2px 0px 0px #E0E0E0;
}

.empty-state p {
  font-size: 14px;
  font-weight: 600;
  color: var(--neo-color-text-muted);
}

.empty-tip {
  font-size: 12px;
  color: var(--neo-color-text-muted);
  margin-top: 4px;
  font-weight: 600;
}

/* ========== 表单输入增强 ========== */
.neo-input-form :deep(.el-input__wrapper),
.neo-input-form :deep(.el-select__wrapper) {
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  box-shadow: var(--neo-shadow-md) !important;
  border-radius: var(--neo-radius-md) !important;
  background: var(--neo-color-bg-card) !important;
  font-weight: 600 !important;
  transition: all 0.1s ease !important;
}

.neo-input-form :deep(.el-input__wrapper):hover,
.neo-input-form :deep(.el-select__wrapper):hover {
  box-shadow: var(--neo-shadow-default) !important;
}

.neo-input-form :deep(.el-input__wrapper.is-focus),
.neo-input-form :deep(.el-select__wrapper.is-focused) {
  box-shadow: var(--neo-shadow-default) !important;
  border-color: var(--neo-color-border) !important;
}

.neo-input-form :deep(.el-input__inner),
.neo-input-form :deep(.el-select__selection .el-select__selected-item) {
  font-weight: 600 !important;
  color: var(--neo-color-text-primary) !important;
}

.neo-textarea :deep(.el-textarea__inner) {
  border: var(--neo-border-thick) solid var(--neo-color-border) !important;
  box-shadow: var(--neo-shadow-md) !important;
  border-radius: var(--neo-radius-md) !important;
  background: var(--neo-color-bg-card) !important;
  font-weight: 600 !important;
  font-family: inherit !important;
  transition: all 0.1s ease !important;
}

.neo-textarea :deep(.el-textarea__inner):focus {
  box-shadow: 4px 4px 0px 0px var(--neo-color-accent-blue) !important;
}
</style>
