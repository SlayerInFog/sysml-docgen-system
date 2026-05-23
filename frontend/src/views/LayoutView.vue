<template>
  <el-container class="shell">
    <el-aside width="236px" class="aside">
      <h2>SysMLDocGen</h2>
      <p class="muted">文档自动生成系统</p>
      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon>工作台</el-menu-item>
        <el-menu-item index="/projects"><el-icon><Folder /></el-icon>项目管理</el-menu-item>
        <el-menu-item index="/models"><el-icon><Share /></el-icon>模型管理</el-menu-item>
        <el-menu-item index="/templates"><el-icon><Memo /></el-icon>模板管理</el-menu-item>
        <el-menu-item index="/documents"><el-icon><Document /></el-icon>文档生成</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin"><el-icon><Setting /></el-icon>系统管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ auth.user?.full_name || auth.user?.username }}</span>
        <el-tag>{{ roleLabel }}</el-tag>
        <el-button @click="logout">退出</el-button>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const roleLabel = computed(() => ({ admin: '管理员', author: '编辑者', reader: '读者' }[auth.user?.role || 'reader']))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell {
  min-height: 100vh;
}
.aside {
  padding: 24px 14px;
  background: #102f35;
  color: #f8f3e9;
}
.aside h2 {
  margin: 0;
}
.menu {
  margin-top: 24px;
  border-right: 0;
  background: transparent;
}
:deep(.el-menu-item) {
  color: #e7efed;
  border-radius: 12px;
}
:deep(.el-menu-item:hover),
:deep(.el-menu-item:focus) {
  background: #1d4b52;
  color: #ffffff;
}
:deep(.el-menu-item:hover .el-icon),
:deep(.el-menu-item:focus .el-icon) {
  color: #ffffff;
}
:deep(.el-menu-item.is-active) {
  background: #f8f3e9;
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active .el-icon) {
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active:hover),
:deep(.el-menu-item.is-active:focus) {
  background: #fffaf0;
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active:hover .el-icon),
:deep(.el-menu-item.is-active:focus .el-icon) {
  color: var(--brand-dark);
}
.header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 14px;
  background: rgba(255, 250, 240, 0.78);
  border-bottom: 1px solid var(--line);
}
.main {
  padding: 28px;
}
</style>
