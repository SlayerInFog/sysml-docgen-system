<template>
  <div>
    <h1 class="page-title">系统管理</h1>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <el-button @click="exportCsv">导出 CSV</el-button>
        </div>
      </template>
      <el-form class="filter-form" label-position="top">
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
        <el-form-item label="数量">
          <el-input-number v-model="filters.limit" :min="1" :max="1000" controls-position="right" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
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
import { auditApi } from '@/api'

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
const filters = reactive({
  action: '',
  target_type: '',
  user_id: undefined as number | undefined,
  keyword: '',
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
    limit: filters.limit,
  })
}

function resetFilters() {
  filters.action = ''
  filters.target_type = ''
  filters.user_id = undefined
  filters.keyword = ''
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

onMounted(loadLogs)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-form {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 12px;
  align-items: end;
  margin-bottom: 16px;
}
</style>
