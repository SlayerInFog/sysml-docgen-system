<template>
  <div>
    <h1 class="page-title">工作台</h1>
    <el-row :gutter="18">
      <el-col :span="6"><el-card><el-statistic title="项目数量" :value="projects.length" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="模型数量" :value="models.length" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="模板数量" :value="templates.length" /></el-card></el-col>
      <el-col :span="6"><el-card><el-statistic title="文档数量" :value="documents.length" /></el-card></el-col>
    </el-row>
    <el-card style="margin-top: 18px">
      <template #header>推荐流程</template>
      <el-steps :active="4" finish-status="success" align-center>
        <el-step title="创建项目" />
        <el-step title="上传模型" />
        <el-step title="检查元素" />
        <el-step title="选择模板" />
        <el-step title="生成导出" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { documentApi, modelApi, projectApi, type GeneratedDocument, type Project, type SysMLModel, type Template } from '@/api'

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const templates = ref<Template[]>([])
const documents = ref<GeneratedDocument[]>([])

onMounted(async () => {
  projects.value = await projectApi.list()
  models.value = await modelApi.list()
  templates.value = await documentApi.templates()
  documents.value = await documentApi.list()
})
</script>
