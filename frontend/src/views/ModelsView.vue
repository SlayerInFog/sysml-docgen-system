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
      <el-table :data="models" stripe highlight-current-row @row-click="selectModel">
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

    <el-row v-if="selected" :gutter="18" style="margin-top: 18px">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>图形化关系视图</span>
              <span class="muted">展示前 {{ graphNodes.length }} 个元素、{{ graphEdges.length }} 条关系</span>
            </div>
          </template>
          <div class="graph-panel">
            <svg viewBox="0 0 760 430" role="img" aria-label="模型关系图">
              <defs>
                <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L9,3 z" fill="#6b7280" />
                </marker>
              </defs>
              <line
                v-for="edge in graphEdges"
                :key="edge.key"
                :x1="edge.source.x"
                :y1="edge.source.y"
                :x2="edge.target.x"
                :y2="edge.target.y"
                class="graph-edge"
                marker-end="url(#arrow)"
              />
              <g v-for="node in graphNodes" :key="node.uid" class="graph-node" @click="editElement(node.element)">
                <circle :cx="node.x" :cy="node.y" r="30" />
                <text :x="node.x" :y="node.y - 3" text-anchor="middle">{{ compactName(node.element.name) }}</text>
                <text :x="node.x" :y="node.y + 13" text-anchor="middle" class="node-type">{{ node.element.type }}</text>
              </g>
            </svg>
            <el-empty v-if="!graphNodes.length" description="暂无可展示的模型元素" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>模型版本对比</template>
          <div class="compare-toolbar">
            <el-select v-model="targetModelId" placeholder="选择对比版本" style="flex: 1">
              <el-option
                v-for="item in comparableModels"
                :key="item.id"
                :label="`${item.name} v${item.version}`"
                :value="item.id"
              />
            </el-select>
            <el-button type="primary" :disabled="!targetModelId" @click="loadCompare">对比</el-button>
          </div>
          <div v-if="compareResult" class="compare-result">
            <div class="stats-grid">
              <div><strong>{{ compareResult.added_elements.length }}</strong><span>新增元素</span></div>
              <div><strong>{{ compareResult.removed_elements.length }}</strong><span>删除元素</span></div>
              <div><strong>{{ compareResult.changed_elements.length }}</strong><span>变更元素</span></div>
              <div><strong>{{ compareResult.added_relations.length + compareResult.removed_relations.length }}</strong><span>关系变化</span></div>
            </div>
            <el-tabs>
              <el-tab-pane label="新增">
                <el-table :data="compareResult.added_elements" height="210" size="small">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="type" label="类型" width="120" />
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="删除">
                <el-table :data="compareResult.removed_elements" height="210" size="small">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="type" label="类型" width="120" />
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="变更">
                <el-table :data="compareResult.changed_elements" height="210" size="small">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column label="字段">
                    <template #default="{ row }">{{ row.change_fields.join(', ') }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </div>
          <el-empty v-else description="选择同项目模型版本后可查看差异" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiError } from '@/api/http'
import {
  modelApi,
  projectApi,
  type ModelCompare,
  type ModelElement,
  type ModelRelation,
  type Project,
  type SysMLModel,
} from '@/api'

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
const targetModelId = ref<number>()
const compareResult = ref<ModelCompare | null>(null)

const graphNodes = computed(() => {
  const centerX = 380
  const centerY = 215
  const radius = 150
  const visible = elements.value.slice(0, 36)
  return visible.map((element, index) => {
    const angle = (2 * Math.PI * index) / Math.max(visible.length, 1)
    return {
      uid: element.element_uid,
      element,
      x: Math.round(centerX + radius * Math.cos(angle)),
      y: Math.round(centerY + radius * Math.sin(angle)),
    }
  })
})

const graphEdges = computed(() => {
  const nodeMap = new Map(graphNodes.value.map((node) => [node.uid, node]))
  return relations.value
    .filter((relation) => nodeMap.has(relation.source_uid) && nodeMap.has(relation.target_uid))
    .slice(0, 80)
    .map((relation) => ({
      key: relation.id,
      source: nodeMap.get(relation.source_uid)!,
      target: nodeMap.get(relation.target_uid)!,
    }))
})

const comparableModels = computed(() =>
  models.value.filter((item) => item.id !== selected.value?.id && item.project_id === selected.value?.project_id),
)

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
  targetModelId.value = undefined
  compareResult.value = null
  const graph = await modelApi.graph(row.id)
  elements.value = graph.elements
  relations.value = graph.relations
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
async function loadCompare() {
  if (!selected.value || !targetModelId.value) return
  try {
    compareResult.value = await modelApi.compare(selected.value.id, targetModelId.value)
  } catch (error) {
    ElMessage.error(apiError(error, '版本对比失败'))
  }
}
function compactName(value: string) {
  return value.length > 8 ? `${value.slice(0, 7)}...` : value
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
.card-header,
.compare-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.graph-panel {
  height: 460px;
  overflow: hidden;
}
.graph-panel svg {
  width: 100%;
  height: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfb;
}
.graph-edge {
  stroke: #6b7280;
  stroke-width: 1.4;
  opacity: 0.62;
}
.graph-node {
  cursor: pointer;
}
.graph-node circle {
  fill: #e7efed;
  stroke: var(--brand);
  stroke-width: 2;
}
.graph-node text {
  fill: var(--ink);
  font-size: 11px;
  pointer-events: none;
}
.graph-node .node-type {
  fill: var(--muted);
  font-size: 9px;
}
.compare-result {
  margin-top: 14px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.stats-grid div {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.stats-grid strong {
  display: block;
  font-size: 22px;
  color: var(--brand-dark);
}
.stats-grid span {
  color: var(--muted);
  font-size: 13px;
}
</style>
