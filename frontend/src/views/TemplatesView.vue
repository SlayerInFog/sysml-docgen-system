<template>
  <div>
    <h1 class="page-title">模板管理</h1>
    <div class="toolbar">
      <el-button type="primary" @click="createDefault">生成默认模板</el-button>
      <el-button @click="dialog = true">新建模板</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="templates" stripe>
      <el-table-column prop="name" label="模板名称" />
      <el-table-column prop="description" label="说明" />
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>

    <el-dialog v-model="dialog" title="新建模板" width="760px">
      <el-form label-position="top">
        <el-form-item label="模板名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="Jinja2 HTML 模板内容">
          <el-input v-model="form.content" type="textarea" :rows="14" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import { documentApi, type Template } from '@/api'

const templates = ref<Template[]>([])
const dialog = ref(false)
const form = reactive({
  name: '',
  description: '',
  content: '<h1>{{ title }}</h1><p>模型：{{ model.name }}</p>{% for element in elements %}<p>{{ element.name }} - {{ element.type }}</p>{% endfor %}',
})

async function load() {
  templates.value = await documentApi.templates()
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
async function create() {
  try {
    await documentApi.createTemplate(form)
    ElMessage.success('模板已创建')
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '创建模板失败'))
  }
}
onMounted(load)
</script>
