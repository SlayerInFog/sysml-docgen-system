<template>
  <div>
    <h1 class="page-title">模板管理</h1>
    <div class="toolbar">
      <el-button type="primary" @click="createDefault">生成默认模板</el-button>
      <el-button @click="openCreate">新建模板</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table :data="templates" stripe>
      <el-table-column prop="name" label="模板名称" min-width="180" />
      <el-table-column prop="description" label="说明" min-width="220" />
      <el-table-column label="范围" width="110">
        <template #default="{ row }">{{ row.project_id ? '项目模板' : '全局模板' }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="created_at" label="创建时间" width="210" />
      <el-table-column label="操作" width="320" fixed="right" class-name="table-actions-cell">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="edit(row)">编辑</el-button>
            <el-button text @click="preview(row)">预览</el-button>
            <el-button text @click="openHistory(row)">历史</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
          </div>
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
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialog" title="模板预览" width="900px">
      <iframe class="html-preview" :srcdoc="previewHtml"></iframe>
    </el-dialog>

    <el-dialog v-model="historyDialog" :title="historyTitle" width="960px">
      <el-table :data="versions" stripe>
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column prop="name" label="模板名称" min-width="160" />
        <el-table-column prop="description" label="说明" min-width="180" />
        <el-table-column prop="created_by" label="修改人" width="100" />
        <el-table-column prop="created_at" label="修改时间" width="210" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button text @click="previewVersion(row)">预览</el-button>
              <el-tag v-if="isCurrentVersion(row)" size="small" type="success">当前版本</el-tag>
              <el-button v-else text type="primary" @click="rollback(row)">回滚</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiError } from '@/api/http'
import { documentApi, projectApi, type Project, type Template, type TemplateVersion } from '@/api'

const DEFAULT_CONTENT =
  '<h1>{{ title }}</h1><p>模型：{{ model.name }}</p>{% for element in elements %}<p>{{ element.name }} - {{ element.type }}</p>{% endfor %}'

const templates = ref<Template[]>([])
const projects = ref<Project[]>([])
const versions = ref<TemplateVersion[]>([])
const dialog = ref(false)
const previewDialog = ref(false)
const historyDialog = ref(false)
const saving = ref(false)
const previewHtml = ref('')
const editingId = ref<number>()
const selectedTemplate = ref<Template>()
const form = reactive({
  project_id: undefined as number | undefined,
  name: '',
  description: '',
  content: DEFAULT_CONTENT,
})

const historyTitle = computed(() => (selectedTemplate.value ? `版本历史 - ${selectedTemplate.value.name}` : '版本历史'))

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

async function openHistory(template: Template) {
  selectedTemplate.value = template
  try {
    versions.value = await documentApi.templateVersions(template.id)
    historyDialog.value = true
  } catch (error) {
    ElMessage.error(apiError(error, '加载版本历史失败'))
  }
}

async function previewVersion(version: TemplateVersion) {
  await renderPreview(version.content)
}

async function rollback(version: TemplateVersion) {
  if (!selectedTemplate.value || isCurrentVersion(version)) return
  try {
    await ElMessageBox.confirm(`回滚到版本 ${version.version}？当前内容会作为新版本保留。`, '确认回滚', {
      type: 'warning',
    })
    await documentApi.rollbackTemplate(selectedTemplate.value.id, version.id)
    ElMessage.success('模板已回滚')
    historyDialog.value = false
    await load()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '回滚失败'))
    }
  }
}

function isCurrentVersion(version: TemplateVersion) {
  return Boolean(selectedTemplate.value && version.version === selectedTemplate.value.version)
}

async function remove(template: Template) {
  try {
    await ElMessageBox.confirm(`删除模板“${template.name}”？历史版本会一并删除。`, '确认删除', { type: 'warning' })
    await documentApi.removeTemplate(template.id)
    ElMessage.success('模板已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除模板失败'))
    }
  }
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
    content: DEFAULT_CONTENT,
  })
}

function cancelDialog() {
  dialog.value = false
  resetForm()
}

async function save() {
  saving.value = true
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
  } finally {
    saving.value = false
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
