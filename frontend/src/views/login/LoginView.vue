<template>
  <div class="login-container">
    <div class="login-decorator-left"></div>
    <div class="login-decorator-right"></div>
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <i class="fas fa-calendar-alt"></i>
        </div>
        <h1 class="login-title">{{ systemName }}</h1>
        <p v-if="orgName" class="org-name">{{ orgName }}</p>
      </div>
      <div class="login-form">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            clearable
            @keyup.enter="handleLogin"
          />
        </div>
        <div class="form-item">
          <label class="form-label">密码</label>
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
            size="large"
            class="login-btn"
            @click="handleLogin"
            :loading="loading"
          >
            登 录
          </el-button>
        </div>
      </div>
    </div>

    <!-- 强制改密弹窗 -->
    <div v-if="showChangePwd" class="modal-overlay">
      <div class="modal-box">
        <div class="modal-header">
          <span class="modal-icon">⚠</span>
          修改初始密码
        </div>
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
            size="large"
            class="modal-btn"
            :loading="changePwdLoading"
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
  background: #FFFDF5;
  position: relative;
  overflow: hidden;
}

/* 装饰背景元素 */
.login-decorator-left,
.login-decorator-right {
  position: absolute;
  border: 4px solid #000000;
  z-index: 0;
}
.login-decorator-left {
  width: 200px;
  height: 200px;
  background: #FFD93D;
  top: -60px;
  left: -60px;
  box-shadow: 6px 6px 0px 0px #3B82F6;
}
.login-decorator-right {
  width: 160px;
  height: 160px;
  background: #3B82F6;
  bottom: -40px;
  right: -40px;
  box-shadow: -6px 6px 0px 0px #FFD93D;
}

/* 登录卡片 */
.login-card {
  width: 420px;
  background: #FFFFFF;
  border: 4px solid #000000;
  border-radius: 4px;
  box-shadow: 8px 8px 0px 0px #000000;
  position: relative;
  z-index: 1;
  overflow: hidden;
}

.login-header {
  padding: 32px 32px 24px;
  text-align: center;
  border-bottom: 3px solid #000000;
  background: #FFFDF5;
}

.login-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  background: #3B82F6;
  border: 3px solid #000000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 4px 4px 0px 0px #000000;
}
.login-logo i {
  font-size: 28px;
  color: #FFFFFF;
}

.login-title {
  font-size: 24px;
  font-weight: 900;
  color: #000000;
  margin: 0 0 4px;
  letter-spacing: 1px;
}

.org-name {
  font-size: 13px;
  color: #666666;
  margin: 0;
  font-weight: 500;
}

/* 表单 */
.login-form {
  padding: 32px;
}

.form-item {
  margin-bottom: 20px;
}
.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #000000;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 4px;
  background: #3B82F6;
  border-color: #000000;
  box-shadow: 4px 4px 0px 0px #000000;
  transition: all 0.1s ease;
}
.login-btn:hover {
  box-shadow: 6px 6px 0px 0px #000000;
  transform: translate(-2px, -2px);
}
.login-btn:active {
  box-shadow: 2px 2px 0px 0px #000000;
  transform: translate(2px, 2px);
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.modal-box {
  width: 440px;
  background: #FFFFFF;
  border: 4px solid #000000;
  border-radius: 4px;
  box-shadow: 10px 10px 0px 0px #000000;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 24px;
  font-size: 18px;
  font-weight: 900;
  color: #000000;
  border-bottom: 3px solid #000000;
  background: #FFFDF5;
}
.modal-icon {
  font-size: 20px;
}

.modal-body {
  padding: 24px;
}

.modal-warning {
  margin: 0 0 20px;
  padding: 12px 16px;
  background: #FFD93D;
  border: 2px solid #000000;
  border-radius: 4px;
  color: #000000;
  font-size: 13px;
  font-weight: 600;
}

.modal-form-item {
  margin-bottom: 16px;
}
.modal-form-item label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #000000;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 3px solid #000000;
  display: flex;
  justify-content: flex-end;
}

.modal-btn {
  background: #3B82F6;
  border-color: #000000;
  box-shadow: 4px 4px 0px 0px #000000;
  font-weight: 900;
  transition: all 0.1s ease;
}
.modal-btn:hover {
  box-shadow: 6px 6px 0px 0px #000000;
  transform: translate(-2px, -2px);
}
</style>
