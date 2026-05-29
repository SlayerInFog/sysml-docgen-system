<template>
  <el-container class="shell">
    <el-aside width="236px" class="aside">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div>
          <h2>SysMLDocGen</h2>
          <p>文档自动生成系统</p>
        </div>
      </div>
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
        <div class="header-title">基于 SysML 模型的文档自动生成系统</div>
        <div class="account">
          <span>{{ auth.user?.full_name || auth.user?.username }}</span>
          <el-tag>{{ roleLabel }}</el-tag>
          <el-button @click="logout">退出</el-button>
        </div>
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
  background: var(--bg);
}
.aside {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 22px 14px;
  background: linear-gradient(180deg, #0b3d45 0%, #123238 100%);
  color: #eef7f8;
  box-shadow: 8px 0 24px rgba(23, 33, 43, 0.12);
}
.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 4px 6px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  color: #0b3d45;
  background: #e8f4f5;
  font-weight: 900;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.16);
}
.aside h2 {
  margin: 0;
  font-size: 19px;
  line-height: 1.2;
}
.brand p {
  margin: 4px 0 0;
  color: #b7d3d6;
  font-size: 12px;
}
.menu {
  margin-top: 18px;
  border-right: 0;
  background: transparent;
}
:deep(.el-menu-item) {
  height: 44px;
  margin: 4px 0;
  color: #dcebec;
  border-radius: 8px;
  font-weight: 700;
}
:deep(.el-menu-item .el-icon) {
  color: #a9cdd1;
}
:deep(.el-menu-item:hover),
:deep(.el-menu-item:focus) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}
:deep(.el-menu-item:hover .el-icon),
:deep(.el-menu-item:focus .el-icon) {
  color: #ffffff;
}
:deep(.el-menu-item.is-active) {
  background: #edf7f7;
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active .el-icon) {
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active:hover),
:deep(.el-menu-item.is-active:focus) {
  background: #ffffff;
  color: var(--brand-dark);
}
:deep(.el-menu-item.is-active:hover .el-icon),
:deep(.el-menu-item.is-active:focus .el-icon) {
  color: var(--brand-dark);
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  height: 62px;
  background: rgba(255, 255, 255, 0.86);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(10px);
}
.header-title {
  color: #38505d;
  font-weight: 800;
}
.account {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}
.main {
  padding: 26px 30px 34px;
  min-width: 0;
}
</style>
