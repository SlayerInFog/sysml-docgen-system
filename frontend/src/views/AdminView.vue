<template>
  <div>
    <h1 class="page-title">系统管理</h1>
    <el-card>
      <template #header>操作日志</template>
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
import { onMounted, ref } from 'vue'
import { auditApi } from '@/api'

const logs = ref<any[]>([])
onMounted(async () => {
  logs.value = await auditApi.logs()
})
</script>
