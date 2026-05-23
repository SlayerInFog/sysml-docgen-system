<template>
  <div>
    <h1 class="page-title">项目管理</h1>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建项目</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="projects" stripe>
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="code" label="项目编码" />
      <el-table-column prop="description" label="说明" />
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button text type="primary" @click="edit(row)">编辑</el-button>
          <el-button text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑项目' : '新建项目'" width="520px" @closed="resetForm">
      <el-form label-position="top">
        <el-form-item label="项目名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="项目编码"><el-input v-model="form.code" :disabled="Boolean(editingId)" placeholder="例如 UAV-DOC-001" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialog">取消</el-button>
        <el-button type="primary" @click="save">{{ editingId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiError } from '@/api/http'
import { projectApi, type Project } from '@/api'

const projects = ref<Project[]>([])
const dialog = ref(false)
const editingId = ref<number>()
const form = reactive({ name: '', code: '', description: '' })

async function load() {
  projects.value = await projectApi.list()
}
function openCreate() {
  resetForm()
  dialog.value = true
}
function edit(project: Project) {
  editingId.value = project.id
  Object.assign(form, {
    name: project.name,
    code: project.code,
    description: project.description || '',
  })
  dialog.value = true
}
function resetForm() {
  editingId.value = undefined
  Object.assign(form, { name: '', code: '', description: '' })
}
function cancelDialog() {
  dialog.value = false
  resetForm()
}
async function save() {
  try {
    if (editingId.value) {
      await projectApi.update(editingId.value, { name: form.name, description: form.description })
      ElMessage.success('项目已更新')
    } else {
      await projectApi.create(form)
      ElMessage.success('项目创建成功')
    }
    dialog.value = false
    resetForm()
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '保存失败'))
  }
}
async function remove(project: Project) {
  try {
    await ElMessageBox.confirm(`删除项目「${project.name}」会同时删除其模型、模板和生成文档，是否继续？`, '确认删除', {
      type: 'warning',
    })
    await projectApi.remove(project.id)
    ElMessage.success('项目已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除失败'))
    }
  }
}
onMounted(load)
</script>
