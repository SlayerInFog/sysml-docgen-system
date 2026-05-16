<template>
  <div>
    <h1 class="page-title">模型管理</h1>
    <el-card>
      <template #header>上传 SysML / XMI / JSON 模型</template>
      <el-form label-position="top" class="upload-form">
        <el-form-item label="所属项目">
          <el-select v-model="upload.project_id" placeholder="选择项目">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称"><el-input v-model="upload.name" /></el-form-item>
        <el-form-item label="模型说明"><el-input v-model="upload.description" /></el-form-item>
        <el-form-item label="模型文件">
          <input type="file" accept=".xmi,.xml,.json,.uml,.sysml,.mms" @change="onFile" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit">上传并解析</el-button>
      </el-form>
    </el-card>

    <el-card style="margin-top: 18px">
      <template #header>模型列表</template>
      <el-table :data="models" stripe @row-click="selectModel">
        <el-table-column prop="name" label="模型名称" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="source_filename" label="源文件" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="created_at" label="上传时间" />
      </el-table>
    </el-card>

    <el-row v-if="selected" :gutter="18" style="margin-top: 18px">
      <el-col :span="14">
        <el-card>
          <template #header>模型元素：{{ selected.name }}</template>
          <el-table :data="elements" height="460" stripe @row-click="editElement">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="type" label="类型" width="140" />
            <el-table-column prop="documentation" label="说明" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>元素关系</template>
          <el-table :data="relations" height="460" stripe>
            <el-table-column prop="source_uid" label="源" />
            <el-table-column prop="relation_type" label="关系" width="120" />
            <el-table-column prop="target_uid" label="目标" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="editDialog" title="轻量编辑模型元素" width="560px">
      <el-form v-if="editing" label-position="top">
        <el-form-item label="名称"><el-input v-model="editing.name" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="editing.documentation" type="textarea" :rows="5" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="saveElement">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { modelApi, projectApi, type ModelElement, type ModelRelation, type Project, type SysMLModel } from '@/api'

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const elements = ref<ModelElement[]>([])
const relations = ref<ModelRelation[]>([])
const selected = ref<SysMLModel | null>(null)
const loading = ref(false)
const file = ref<File | null>(null)
const upload = reactive({ project_id: undefined as number | undefined, name: '', description: '' })
const editDialog = ref(false)
const editing = ref<ModelElement | null>(null)

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
}
async function load() {
  projects.value = await projectApi.list()
  models.value = await modelApi.list()
}
async function submit() {
  if (!upload.project_id || !upload.name || !file.value) {
    ElMessage.warning('请填写项目、模型名称并选择文件')
    return
  }
  loading.value = true
  try {
    const form = new FormData()
    form.append('project_id', String(upload.project_id))
    form.append('name', upload.name)
    form.append('description', upload.description)
    form.append('file', file.value)
    await modelApi.upload(form)
    ElMessage.success('上传解析成功')
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '上传失败'))
  } finally {
    loading.value = false
  }
}
async function selectModel(row: SysMLModel) {
  selected.value = row
  elements.value = await modelApi.elements(row.id)
  relations.value = (await modelApi.graph(row.id)).relations
}
function editElement(row: ModelElement) {
  editing.value = { ...row }
  editDialog.value = true
}
async function saveElement() {
  if (!editing.value) return
  const updated = await modelApi.updateElement(editing.value.id, {
    name: editing.value.name,
    documentation: editing.value.documentation,
  })
  const index = elements.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) elements.value[index] = updated
  editDialog.value = false
  ElMessage.success('元素已更新')
}
onMounted(load)
</script>

<style scoped>
.upload-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 12px;
  align-items: end;
}
</style>
