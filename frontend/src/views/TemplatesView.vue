<template>
  <div>
    <h1 class="page-title">模板管理</h1>
    <div class="toolbar">
      <el-button type="primary" @click="createDefault">生成默认模板</el-button>
      <el-button @click="openCreate">新建模板</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="templates" stripe>
      <el-table-column prop="name" label="模板名称" />
      <el-table-column prop="description" label="说明" />
      <el-table-column label="范围" width="110">
        <template #default="{ row }">{{ row.project_id ? '项目模板' : '全局模板' }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button text type="primary" @click="edit(row)">编辑</el-button>
          <el-button text @click="preview(row)">预览</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑模板' : '新建模板'" width="920px" @closed="resetForm">
      <el-form label-position="top">
        <el-form-item label="所属项目">
          <el-select v-model="form.project_id" clearable placeholder="不选择则作为全局模板">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
        <el-alert
          class="variable-hint"
          type="info"
          :closable="false"
          title="可用变量：{{ title }}、{{ model.name }}、{{ model.version }}、{{ stats.total_elements }}、{{ stats.total_relations }}、elements、relations、element_names"
        />
        <el-form-item label="Jinja2 HTML 模板内容">
          <el-input v-model="form.content" type="textarea" :rows="14" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialog">取消</el-button>
        <el-button @click="previewCurrent">预览</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialog" title="模板预览" width="900px">
      <iframe class="html-preview" :srcdoc="previewHtml"></iframe>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { documentApi, projectApi, type Project, type Template } from '@/api'

const templates = ref<Template[]>([])
const projects = ref<Project[]>([])
const dialog = ref(false)
const previewDialog = ref(false)
const previewHtml = ref('')
const editingId = ref<number>()
const form = reactive({
  project_id: undefined as number | undefined,
  name: '',
  description: '',
  content: '<h1>{{ title }}</h1><p>模型：{{ model.name }}</p>{% for element in elements %}<p>{{ element.name }} - {{ element.type }}</p>{% endfor %}',
})

async function load() {
  projects.value = await projectApi.list()
  templates.value = await documentApi.templates()
}
function openCreate() {
  resetForm()
  dialog.value = true
}
async function createDefault() {
  try {
    await documentApi.createDefaultTemplate()
    ElMessage.success('默认模板已创建')
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '创建默认模板失败'))
  }
}
function edit(template: Template) {
  editingId.value = template.id
  Object.assign(form, {
    project_id: template.project_id,
    name: template.name,
    description: template.description || '',
    content: template.content,
  })
  dialog.value = true
}
async function preview(template: Template) {
  await renderPreview(template.content)
}
async function previewCurrent() {
  await renderPreview(form.content)
}
async function renderPreview(content: string) {
  try {
    const result = await documentApi.previewTemplate({ content })
    previewHtml.value = result.html
    previewDialog.value = true
  } catch (error) {
    ElMessage.error(apiError(error, '模板预览失败'))
  }
}
function resetForm() {
  editingId.value = undefined
  Object.assign(form, {
    project_id: undefined,
    name: '',
    description: '',
    content: '<h1>{{ title }}</h1><p>模型：{{ model.name }}</p>{% for element in elements %}<p>{{ element.name }} - {{ element.type }}</p>{% endfor %}',
  })
}
function cancelDialog() {
  dialog.value = false
  resetForm()
}
async function save() {
  try {
    if (editingId.value) {
      await documentApi.updateTemplate(editingId.value, form)
      ElMessage.success('模板已更新')
    } else {
      await documentApi.createTemplate(form)
      ElMessage.success('模板已创建')
    }
    dialog.value = false
    resetForm()
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '保存模板失败'))
  }
}
onMounted(load)
</script>

<style scoped>
.variable-hint {
  margin-bottom: 12px;
}
.html-preview {
  width: 100%;
  min-height: 360px;
  height: 620px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
</style>
