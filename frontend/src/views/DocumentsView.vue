<template>
  <div>
    <h1 class="page-title">文档生成</h1>
    <el-card>
      <template #header>生成配置</template>
      <el-form class="generate-form" label-position="top">
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
        <el-button type="primary" @click="generate">生成文档</el-button>
      </el-form>
    </el-card>

    <el-card style="margin-top: 18px">
      <template #header>生成历史</template>
      <el-table :data="documents" stripe @row-click="selectDocument">
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="生成时间" />
        <el-table-column label="导出" width="260">
          <template #default="{ row }">
            <el-button size="small" @click.stop="download(row.id, 'html')">HTML</el-button>
            <el-button size="small" @click.stop="download(row.id, 'docx')">DOCX</el-button>
            <el-button size="small" @click.stop="download(row.id, 'pdf')">PDF</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selected" style="margin-top: 18px">
      <template #header>在线预览：{{ selected.title }}</template>
      <div class="html-preview" v-html="selected.html_content"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { documentApi, modelApi, projectApi, type GeneratedDocument, type Project, type SysMLModel, type Template } from '@/api'

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const templates = ref<Template[]>([])
const documents = ref<GeneratedDocument[]>([])
const selected = ref<GeneratedDocument | null>(null)
const form = reactive({ project_id: undefined as number | undefined, model_id: undefined as number | undefined, template_id: undefined as number | undefined, title: '' })

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
}
async function generate() {
  if (!form.project_id || !form.model_id || !form.template_id || !form.title) {
    ElMessage.warning('请完整选择项目、模型、模板并填写标题')
    return
  }
  try {
    selected.value = await documentApi.generate({
      project_id: form.project_id,
      model_id: form.model_id,
      template_id: form.template_id,
      title: form.title,
    })
    ElMessage.success('文档生成成功')
    documents.value = await documentApi.list(form.project_id)
  } catch (error) {
    ElMessage.error(apiError(error, '生成失败'))
  }
}
function selectDocument(row: GeneratedDocument) {
  selected.value = row
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
  display: grid;
  grid-template-columns: repeat(5, minmax(150px, 1fr));
  gap: 12px;
  align-items: end;
}
</style>
