<template>
  <div>
    <h1 class="page-title">项目管理</h1>
    <div class="toolbar">
      <el-button type="primary" @click="dialog = true">新建项目</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="projects" stripe>
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="code" label="项目编码" />
      <el-table-column prop="description" label="说明" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>

    <el-dialog v-model="dialog" title="新建项目" width="520px">
      <el-form label-position="top">
        <el-form-item label="项目名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="项目编码"><el-input v-model="form.code" placeholder="例如 UAV-DOC-001" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { projectApi, type Project } from '@/api'

const projects = ref<Project[]>([])
const dialog = ref(false)
const form = reactive({ name: '', code: '', description: '' })

async function load() {
  projects.value = await projectApi.list()
}
async function create() {
  try {
    await projectApi.create(form)
    ElMessage.success('项目创建成功')
    dialog.value = false
    Object.assign(form, { name: '', code: '', description: '' })
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '创建失败'))
  }
}
onMounted(load)
</script>
