<template>
  <main class="login-page">
    <section class="login-intro" aria-label="系统介绍">
      <div class="brand-lockup">
        <div class="brand-mark">S</div>
        <div>
          <p class="eyebrow">Model Based Document Generation</p>
          <h1>SysMLDocGen</h1>
        </div>
      </div>
      <p class="intro-copy">以 SysML 模型为可信数据源，统一完成模型管理、模板维护、文档生成与导出。</p>
      <div class="capability-grid">
        <div class="capability-item">
          <el-icon><Folder /></el-icon>
          <span>项目协同</span>
        </div>
        <div class="capability-item">
          <el-icon><Share /></el-icon>
          <span>模型版本</span>
        </div>
        <div class="capability-item">
          <el-icon><Memo /></el-icon>
          <span>模板追踪</span>
        </div>
        <div class="capability-item">
          <el-icon><DocumentChecked /></el-icon>
          <span>文档导出</span>
        </div>
      </div>
      <div class="intro-footer">
        <span>Vue 3</span>
        <span>FastAPI</span>
        <span>MySQL</span>
      </div>
    </section>

    <section class="auth-panel" aria-label="登录注册">
      <div class="auth-header">
        <h2>{{ tab === 'login' ? '欢迎回来' : '创建账号' }}</h2>
        <p>{{ tab === 'login' ? '登录后进入工作台继续管理项目资产。' : '注册后可按角色参与项目协作。' }}</p>
      </div>

      <el-tabs v-model="tab" stretch class="auth-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" @keyup.enter="handleLogin">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" @keyup.enter="handleLogin">
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-button type="primary" class="wide primary-action" :loading="loading" @click="handleLogin">
              登录
              <el-icon><Right /></el-icon>
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" placeholder="至少 3 个字符">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="name@example.com">
                <template #prefix><el-icon><Message /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item label="姓名" prop="full_name">
              <el-input v-model="registerForm.full_name" placeholder="用于系统内显示">
                <template #prefix><el-icon><Postcard /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" type="password" show-password placeholder="至少 6 个字符">
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item label="角色" prop="role">
              <el-select v-model="registerForm.role" class="wide">
                <el-option label="编辑者" value="author" />
                <el-option label="读者" value="reader" />
              </el-select>
            </el-form-item>
            <el-button type="primary" class="wide primary-action" :loading="loading" @click="handleRegister">
              注册
              <el-icon><Right /></el-icon>
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DocumentChecked, Folder, Lock, Memo, Message, Postcard, Right, Share, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { apiError } from '@/api/http'

const auth = useAuthStore()
const router = useRouter()
const tab = ref('login')
const loading = ref(false)
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', full_name: '', password: '', role: 'reader' })

const loginRules: FormRules<typeof loginForm> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const registerRules: FormRules<typeof registerForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// 统一转换接口错误提示。
function normalizeErrorMessage(error: unknown, fallback: string) {
  const message = apiError(error, fallback)
  if (Array.isArray(message)) {
    return message.map((item) => item?.msg ?? fallback).join('；')
  }
  if (typeof message === 'string') {
    return message
  }
  return fallback
}

// 处理登录表单提交。
async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error(normalizeErrorMessage(error, '登录失败'))
  } finally {
    loading.value = false
  }
}

// 处理注册表单提交。
async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.register(registerForm)
    ElMessage.success('注册成功，请登录')
    tab.value = 'login'
    loginForm.username = registerForm.username
    registerFormRef.value?.resetFields()
  } catch (error) {
    ElMessage.error(normalizeErrorMessage(error, '注册失败'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(420px, 1fr) 430px;
  gap: 44px;
  align-items: center;
  padding: 48px clamp(28px, 5vw, 72px);
  background:
    linear-gradient(135deg, rgba(15, 102, 112, 0.08) 0%, rgba(183, 101, 59, 0.05) 46%, rgba(255, 255, 255, 0) 100%),
    linear-gradient(180deg, #eef3f6 0%, var(--bg) 100%);
}
.login-intro {
  max-width: 760px;
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 26px;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 62px;
  height: 62px;
  border-radius: 8px;
  color: #ffffff;
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-dark) 100%);
  font-size: 30px;
  font-weight: 900;
  box-shadow: 0 18px 36px rgba(10, 63, 71, 0.24);
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1,
h2 {
  margin: 0;
  color: #10222b;
}
h1 {
  font-size: clamp(44px, 7vw, 78px);
  line-height: 0.98;
  font-weight: 900;
}
.intro-copy {
  max-width: 620px;
  margin: 0 0 28px;
  color: #41535f;
  font-size: 20px;
  line-height: 1.8;
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 132px));
  gap: 12px;
  margin-bottom: 28px;
}
.capability-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: #2c4652;
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}
.capability-item .el-icon {
  color: var(--brand);
}
.intro-footer {
  display: flex;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}
.intro-footer span {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.58);
}
.auth-panel {
  width: 100%;
  padding: 30px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 24px 70px rgba(23, 33, 43, 0.14);
  backdrop-filter: blur(12px);
}
.auth-header {
  margin-bottom: 18px;
}
.auth-header h2 {
  font-size: 26px;
  line-height: 1.2;
}
.auth-header p {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.6;
}
.auth-tabs {
  --el-tabs-header-height: 48px;
}
.auth-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--line);
}
.auth-tabs :deep(.el-tabs__content) {
  padding-top: 18px;
}
.auth-tabs :deep(.el-form-item) {
  margin-bottom: 18px;
}
.auth-tabs :deep(.el-input__wrapper),
.auth-tabs :deep(.el-select__wrapper) {
  min-height: 42px;
}
.primary-action {
  min-height: 42px;
  margin-top: 4px;
}
.wide {
  width: 100%;
}
@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
    padding: 24px;
  }
  .capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 520px) {
  .brand-lockup {
    align-items: flex-start;
  }
  .brand-mark {
    width: 48px;
    height: 48px;
    font-size: 24px;
  }
  h1 {
    font-size: 40px;
  }
  .intro-copy {
    font-size: 16px;
  }
  .auth-panel {
    padding: 22px;
  }
}
</style>
