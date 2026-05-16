<template>
  <main class="login-page">
    <section class="brand-card">
      <p class="eyebrow">Model Based Document Generation</p>
      <h1>SysMLDocGen</h1>
      <p>以 SysML 模型为单一可信源，自动生成结构化工程文档。</p>
    </section>

    <el-card class="login-card">
      <el-tabs v-model="tab">
        <el-tab-pane label="登录" name="login">
          <el-form label-position="top">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" @keyup.enter="handleLogin" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" show-password @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button type="primary" class="wide" :loading="loading" @click="handleLogin">登录</el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form label-position="top">
            <el-form-item label="用户名"><el-input v-model="registerForm.username" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="registerForm.email" /></el-form-item>
            <el-form-item label="姓名"><el-input v-model="registerForm.full_name" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="registerForm.password" type="password" show-password /></el-form-item>
            <el-form-item label="角色">
              <el-select v-model="registerForm.role" class="wide">
                <el-option label="管理员" value="admin" />
                <el-option label="编辑者" value="author" />
                <el-option label="读者" value="reader" />
              </el-select>
            </el-form-item>
            <el-button type="primary" class="wide" :loading="loading" @click="handleRegister">注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { apiError } from '@/api/http'

const auth = useAuthStore()
const router = useRouter()
const tab = ref('login')
const loading = ref(false)
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', full_name: '', password: '', role: 'reader' })

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error(apiError(error, '登录失败'))
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await auth.register(registerForm)
    ElMessage.success('注册成功，请登录')
    tab.value = 'login'
    loginForm.username = registerForm.username
  } catch (error) {
    ElMessage.error(apiError(error, '注册失败'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 420px;
  gap: 40px;
  align-items: center;
  padding: 48px;
}
.brand-card {
  max-width: 780px;
  padding: 56px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: rgba(255, 250, 240, 0.72);
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
}
.eyebrow {
  color: var(--accent);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 800;
}
h1 {
  font-size: clamp(48px, 8vw, 92px);
  margin: 10px 0;
  line-height: 0.95;
}
.brand-card p:last-child {
  font-size: 20px;
  color: var(--muted);
}
.login-card {
  border-radius: 22px;
}
.wide {
  width: 100%;
}
@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
    padding: 24px;
  }
}
</style>
