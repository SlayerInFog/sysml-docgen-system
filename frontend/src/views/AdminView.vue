<template>
  <div>
    <h1 class="page-title">系统管理</h1>
    <el-card class="admin-card">
      <template #header>用户管理</template>
      <el-table :data="users" stripe>
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="full_name" label="姓名" width="140" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-select
              v-model="row.role"
              size="small"
              :disabled="isProtectedAdmin(row) || savingUserId === row.id"
              @change="updateUser(row, { role: row.role })"
            >
              <el-option label="管理员" value="admin" disabled />
              <el-option label="编辑者" value="author" />
              <el-option label="阅读者" value="reader" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="isProtectedAdmin(row) || savingUserId === row.id"
              @change="updateUser(row, { is_active: row.is_active })"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="210" />
      </el-table>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <el-button @click="exportCsv">导出 CSV</el-button>
        </div>
      </template>
      <el-form class="filter-form" label-position="top">
        <div class="filter-fields">
          <el-form-item label="动作">
            <el-select v-model="filters.action" clearable placeholder="全部动作">
              <el-option v-for="action in actions" :key="action" :label="action" :value="action" />
            </el-select>
          </el-form-item>
          <el-form-item label="对象类型">
            <el-select v-model="filters.target_type" clearable placeholder="全部对象">
              <el-option v-for="type in targetTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item label="用户 ID">
            <el-input-number v-model="filters.user_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="关键字">
            <el-input v-model="filters.keyword" clearable placeholder="动作、对象或说明" />
          </el-form-item>
          <el-form-item label="开始时间">
            <el-date-picker v-model="filters.start_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker v-model="filters.end_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number v-model="filters.limit" :min="1" :max="1000" controls-position="right" />
          </el-form-item>
        </div>
        <div class="filter-actions">
          <el-button type="primary" @click="loadLogs">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </el-form>
      <el-table :data="logs" stripe>
        <el-table-column prop="created_at" label="时间" width="210" />
        <el-table-column prop="user_id" label="用户ID" width="90" />
        <el-table-column prop="action" label="动作" width="180" />
        <el-table-column prop="target_type" label="对象类型" width="120" />
        <el-table-column prop="target_id" label="对象ID" width="100" />
        <el-table-column prop="message" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { auditApi, authApi, type User } from '@/api'
import { useAuthStore } from '@/stores/auth'

interface AuditLog {
  id: number
  user_id?: number
  action: string
  target_type?: string
  target_id?: string
  message?: string
  created_at: string
}

const logs = ref<AuditLog[]>([])
const users = ref<User[]>([])
const savingUserId = ref<number>()
const auth = useAuthStore()
const filters = reactive({
  action: '',
  target_type: '',
  user_id: undefined as number | undefined,
  keyword: '',
  start_time: '',
  end_time: '',
  limit: 200,
})

const actions = computed(() => [...new Set(logs.value.map((item) => item.action).filter(Boolean))])
const targetTypes = computed(() => [...new Set(logs.value.map((item) => item.target_type).filter(Boolean))])

async function loadLogs() {
  logs.value = await auditApi.logs({
    action: filters.action || undefined,
    target_type: filters.target_type || undefined,
    user_id: filters.user_id,
    keyword: filters.keyword || undefined,
    start_time: filters.start_time || undefined,
    end_time: filters.end_time || undefined,
    limit: filters.limit,
  })
}

async function loadUsers() {
  users.value = await authApi.users()
}

async function updateUser(user: User, data: { role?: User['role']; is_active?: boolean }) {
  if (isProtectedAdmin(user)) {
    ElMessage.warning('管理员身份账户不可修改角色或启用状态')
    await loadUsers()
    return
  }
  if (user.id === auth.user?.id && (data.role !== undefined || data.is_active === false)) {
    ElMessage.warning('不能修改当前登录管理员的角色或停用当前账号')
    await loadUsers()
    return
  }
  const previous = await authApi.users()
  savingUserId.value = user.id
  try {
    const updated = await authApi.updateUser(user.id, data)
    const index = users.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) users.value[index] = updated
    ElMessage.success('用户已更新')
  } catch (error) {
    users.value = previous
    ElMessage.error(apiError(error, '更新失败'))
  } finally {
    savingUserId.value = undefined
  }
}

function isProtectedAdmin(user: User) {
  return user.role === 'admin'
}

function resetFilters() {
  filters.action = ''
  filters.target_type = ''
  filters.user_id = undefined
  filters.keyword = ''
  filters.start_time = ''
  filters.end_time = ''
  filters.limit = 200
  loadLogs()
}

function exportCsv() {
  if (!logs.value.length) {
    ElMessage.warning('暂无可导出的日志')
    return
  }
  const header = ['时间', '用户ID', '动作', '对象类型', '对象ID', '说明']
  const rows = logs.value.map((item) => [
    item.created_at,
    item.user_id ?? '',
    item.action,
    item.target_type ?? '',
    item.target_id ?? '',
    item.message ?? '',
  ])
  const csv = [header, ...rows].map((row) => row.map(escapeCsv).join(',')).join('\n')
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function escapeCsv(value: unknown) {
  const text = String(value).replace(/"/g, '""')
  return `"${text}"`
}

onMounted(() => {
  loadUsers()
  loadLogs()
})
</script>

<style scoped>
.admin-card {
  margin-bottom: 18px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.filter-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.filter-actions {
  display: flex;
  gap: 8px;
  padding-bottom: 18px;
  white-space: nowrap;
}
.filter-form :deep(.el-input),
.filter-form :deep(.el-select),
.filter-form :deep(.el-date-editor),
.filter-form :deep(.el-input-number) {
  width: 100%;
}
@media (max-width: 1180px) {
  .filter-fields {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
  }
}
@media (max-width: 720px) {
  .filter-fields {
    grid-template-columns: 1fr;
  }
  .filter-actions {
    width: 100%;
    justify-content: flex-end;
    padding-bottom: 0;
  }
}
</style>
