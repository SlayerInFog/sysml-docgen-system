<template>
  <div>
    <h1 class="page-title">文档生成</h1>
    <el-card>
      <template #header>生成配置</template>
      <el-form v-if="canWrite" class="generate-form" label-position="top">
        <div class="generate-fields">
          <el-form-item label="项目">
            <el-select v-model="form.project_id" @change="loadRelated">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型版本">
            <el-select v-model="form.model_id">
              <el-option v-for="m in models" :key="m.id" :label="`${m.name} V${m.version}`" :value="m.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="模板">
            <el-select v-model="form.template_id">
              <el-option v-for="t in templates" :key="t.id" :label="`${t.name} V${t.version}`" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="文档标题"><el-input v-model="form.title" /></el-form-item>
        </div>
        <div class="generate-actions">
          <el-button type="primary" :loading="generating" @click="generate">生成文档</el-button>
        </div>
      </el-form>
      <el-empty v-else description="读者角色仅可查看和导出已生成文档" />
    </el-card>

    <el-card style="margin-top: 18px">
      <template #header>生成历史</template>
      <el-table :data="documents" stripe>
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="生成时间" width="210" />
        <el-table-column label="导出" width="230">
          <template #default="{ row }">
            <div class="table-export-actions">
              <el-button size="small" @click="download(row.id, 'html')">HTML</el-button>
              <el-button size="small" @click="download(row.id, 'docx')">DOCX</el-button>
              <el-button size="small" @click="download(row.id, 'pdf')">PDF</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" class-name="table-actions-cell">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" type="primary" text @click="preview(row)">预览</el-button>
              <el-button v-if="canWrite" size="small" type="danger" text @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selected" style="margin-top: 18px">
      <template #header>在线预览：{{ selected.title }}</template>
      <iframe class="html-preview" :srcdoc="selected.html_content"></iframe>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { documentApi, modelApi, projectApi, type GeneratedDocument, type Project, type SysMLModel, type Template } from '@/api'

const auth = useAuthStore()
const canWrite = computed(() => auth.canEdit)

function ensureWriteAccess() {
  if (canWrite.value) return true
  ElMessage.warning('读者角色仅可查看，不能执行写操作')
  return false
}

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const templates = ref<Template[]>([])
const documents = ref<GeneratedDocument[]>([])
const selected = ref<GeneratedDocument | null>(null)
const generating = ref(false)
const form = reactive({
  project_id: undefined as number | undefined,
  model_id: undefined as number | undefined,
  template_id: undefined as number | undefined,
  title: '',
})

async function load() {
  projects.value = await projectApi.list()
  documents.value = await documentApi.list()
  templates.value = await documentApi.templates()
  models.value = await modelApi.list()
}

async function loadRelated() {
  models.value = await modelApi.list(form.project_id)
  templates.value = await documentApi.templates(form.project_id)
  documents.value = await documentApi.list(form.project_id)
  selected.value = null
  if (!models.value.some((item) => item.id === form.model_id)) {
    form.model_id = undefined
  }
  if (!templates.value.some((item) => item.id === form.template_id)) {
    form.template_id = undefined
  }
}

async function generate() {
  if (!ensureWriteAccess()) return
  if (!form.project_id || !form.model_id || !form.template_id || !form.title) {
    ElMessage.warning('请完整选择项目、模型、模板并填写标题')
    return
  }
  generating.value = true
  try {
    const doc = await documentApi.generate({
      project_id: form.project_id,
      model_id: form.model_id,
      template_id: form.template_id,
      title: form.title,
    })
    selected.value = doc
    ElMessage.success('文档生成成功')
    documents.value = await documentApi.list(form.project_id)
  } catch (error) {
    ElMessage.error(apiError(error, '生成失败'))
  } finally {
    generating.value = false
  }
}

function preview(row: GeneratedDocument) {
  selected.value = row
}

async function remove(row: GeneratedDocument) {
  if (!ensureWriteAccess()) return
  try {
    await ElMessageBox.confirm(`删除文档“${row.title}”？`, '确认删除', { type: 'warning' })
    await documentApi.remove(row.id)
    ElMessage.success('文档已删除')
    if (selected.value?.id === row.id) {
      selected.value = null
    }
    documents.value = await documentApi.list(form.project_id)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除失败'))
    }
  }
}

async function download(id: number, fmt: 'html' | 'docx' | 'pdf') {
  try {
    const blob = await documentApi.export(id, fmt)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `sysml-document-${id}.${fmt}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(apiError(error, '导出失败'))
  }
}

onMounted(load)
</script>

<style scoped>
.generate-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
}
.generate-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.generate-actions {
  padding-bottom: 18px;
  white-space: nowrap;
}
.generate-form :deep(.el-select),
.generate-form :deep(.el-input) {
  width: 100%;
}
.html-preview {
  width: 100%;
  min-height: 480px;
  height: 680px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
@media (max-width: 900px) {
  .generate-fields {
    grid-template-columns: 1fr;
  }
}
</style>
