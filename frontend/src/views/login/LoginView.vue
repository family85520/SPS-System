<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>{{ systemName }}</h1>
        <p v-if="orgName" class="org-name">{{ orgName }}</p>
      </div>
      <div class="login-form">
        <div class="form-item">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            clearable
          />
        </div>
        <div class="form-item">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </div>
        <div class="form-item">
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </div>
      </div>
    </div>

    <!-- 强制改密弹窗（纯 div 实现，避免 el-dialog 渲染冲突） -->
    <div v-if="showChangePwd" class="modal-overlay">
      <div class="modal-box">
        <div class="modal-header">修改初始密码</div>
        <div class="modal-body">
          <p class="modal-warning">您的账号使用的是初始密码，为保障安全，请先设置新密码。</p>
          <div class="modal-form-item">
            <label>新密码</label>
            <el-input
              v-model="pwdForm.new_password"
              type="password"
              show-password
              placeholder="请输入新密码（至少6位）"
            />
          </div>
          <div class="modal-form-item">
            <label>确认密码</label>
            <el-input
              v-model="pwdForm.confirm_password"
              type="password"
              show-password
              placeholder="请再次输入新密码"
            />
          </div>
        </div>
        <div class="modal-footer">
          <el-button
            type="primary"
            :loading="changePwdLoading"
            style="width: 100%"
            @click="handleForceChangePwd"
          >
            确认修改并登录
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { getPublicConfig } from '@/api/system'
import { forceChangePassword } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const systemName = ref(localStorage.getItem('systemName') || '排班管理系统')
const orgName = ref(localStorage.getItem('orgName') || '')

const showChangePwd = ref(false)
const changePwdLoading = ref(false)
const pwdForm = reactive({ new_password: '', confirm_password: '' })

const form = reactive({ username: '', password: '' })

onMounted(async () => {
  if (authStore.isAuthenticated && authStore.mustChangePassword) {
    showChangePwd.value = true
  }
  try {
    const res = await getPublicConfig()
    systemName.value = res.system_name
    orgName.value = res.org_name
    localStorage.setItem('systemName', res.system_name)
    localStorage.setItem('orgName', res.org_name)
  } catch (e) {
    // 使用 localStorage 中的值
  }
})

async function handleLogin() {
  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!form.password) {
    ElMessage.warning('请输入密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(form.username, form.password)

    if (authStore.mustChangePassword) {
      showChangePwd.value = true
      pwdForm.new_password = ''
      pwdForm.confirm_password = ''
      loading.value = false
      return
    }

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    const translateMap: Record<string, string> = {
      'String should have at least 4 characters': '内容不能少于4个字符',
      'String should have at least 2 characters': '内容不能少于2个字符',
      'Field required': '必填项不能为空',
    }
    let msg = '用户名或密码错误'
    if (Array.isArray(detail)) {
      msg = detail.map((d: any) => translateMap[d.msg] || d.msg || '输入有误').join('；')
    } else if (typeof detail === 'string') {
      msg = translateMap[detail] || detail
    }
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleForceChangePwd() {
  if (!pwdForm.new_password || pwdForm.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  changePwdLoading.value = true
  try {
    await forceChangePassword({ new_password: pwdForm.new_password })
    showChangePwd.value = false
    authStore.mustChangePassword = false
    localStorage.removeItem('mustChangePassword')
    await authStore.fetchUserInfo()
    ElMessage.success('密码修改成功')
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '密码修改失败')
  } finally {
    changePwdLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 24px;
  color: #333;
  margin-bottom: 8px;
}

.login-header .org-name {
  font-size: 14px;
  color: #999;
  margin-top: 4px;
}

.form-item {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-box {
  width: 420px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.modal-header {
  padding: 16px 24px;
  font-size: 16px;
  font-weight: 600;
  color: #1F2D3D;
  border-bottom: 1px solid #E6EAF0;
}

.modal-body {
  padding: 24px;
}

.modal-warning {
  margin: 0 0 20px 0;
  padding: 12px 16px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 4px;
  color: #e6a23c;
  font-size: 13px;
}

.modal-form-item {
  margin-bottom: 16px;
}

.modal-form-item label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #606266;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #E6EAF0;
}
</style>
