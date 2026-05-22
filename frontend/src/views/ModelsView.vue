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
          <template #header>
            <div class="card-header">
              <span>模型元素：{{ selected.name }}</span>
              <span class="muted">{{ filteredElements.length }} / {{ elements.length }}</span>
            </div>
          </template>
          <div class="filter-bar">
            <el-input v-model="elementKeyword" clearable placeholder="按名称、类型或说明过滤" />
            <el-select v-model="elementType" clearable placeholder="全部类型">
              <el-option v-for="type in elementTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </div>
          <el-table :data="filteredElements" height="420" stripe highlight-current-row @row-click="focusElement">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="type" label="类型" width="140" />
            <el-table-column prop="documentation" label="说明" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button text type="primary" @click.stop="editElement(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>元素关系</template>
          <el-table :data="visibleRelations" height="480" stripe @row-click="focusRelation">
            <el-table-column prop="source_uid" label="源" />
            <el-table-column prop="relation_type" label="关系" width="120" />
            <el-table-column prop="target_uid" label="目标" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row v-if="selected" :gutter="18" class="viewer-row">
      <el-col :span="6" class="viewer-col">
        <el-card class="viewer-card">
          <template #header>层级导航</template>
          <div class="tree-scroll">
            <el-tree
              ref="modelTreeRef"
              class="model-tree"
              :data="elementTree"
              node-key="uid"
              :props="{ label: 'label', children: 'children' }"
              highlight-current
              @node-click="focusTreeNode"
            />
          </div>
        </el-card>
      </el-col>
      <el-col :span="10" class="viewer-col">
        <el-card class="viewer-card">
          <template #header>
            <div class="card-header">
              <span>图形化关系视图</span>
              <span class="muted">展示 {{ graphNodes.length }} 个元素、{{ graphEdges.length }} 条关系</span>
            </div>
          </template>
          <div class="graph-legend">
            <span><i class="legend-dot current-dot"></i>当前节点</span>
            <span><i class="legend-dot parent-dot"></i>当前节点的父节点</span>
            <span><i class="legend-dot child-dot"></i>当前节点的子节点</span>
          </div>
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
              <g
                v-for="node in graphNodes"
                :key="node.uid"
                :class="[
                  'graph-node',
                  {
                    active: selectedElement?.element_uid === node.uid,
                    selectedParent: selectedParentUid === node.uid,
                    selectedChild: selectedChildUids.has(node.uid),
                  },
                ]"
                @click="focusElement(node.element)"
              >
                <circle :cx="node.x" :cy="node.y" r="30" />
                <text :x="node.x" :y="node.y - 3" text-anchor="middle">{{ compactName(node.element.name) }}</text>
                <text :x="node.x" :y="node.y + 13" text-anchor="middle" class="node-type">{{ node.element.type }}</text>
              </g>
            </svg>
            <el-empty v-if="!graphNodes.length" description="暂无可展示的模型元素" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8" class="viewer-col">
        <el-card class="viewer-card">
          <template #header>元素详情</template>
          <div v-if="selectedElement" class="detail-panel">
            <h3>{{ selectedElement.name }}</h3>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="类型">{{ selectedElement.type }}</el-descriptions-item>
              <el-descriptions-item label="UID">{{ selectedElement.element_uid }}</el-descriptions-item>
              <el-descriptions-item label="父级">{{ selectedElement.parent_uid || '无' }}</el-descriptions-item>
              <el-descriptions-item label="关联关系">{{ selectedElementRelations.length }}</el-descriptions-item>
            </el-descriptions>
            <div class="detail-doc">
              <div class="detail-doc-title">说明</div>
              <div class="detail-doc-body">{{ selectedElement.documentation || '暂无说明' }}</div>
            </div>
            <el-table :data="selectedElementRelations" height="160" size="small">
              <el-table-column prop="relation_type" label="关系" width="110" />
              <el-table-column label="对象">
                <template #default="{ row }">{{ relationPeerName(row) }}</template>
              </el-table-column>
            </el-table>
            <el-button type="primary" style="margin-top: 12px" @click="editElement(selectedElement)">编辑说明</el-button>
          </div>
          <el-empty v-else description="从表格、树或图中选择元素" />
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="selected" style="margin-top: 18px">
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
      <div v-if="compareResult" class="compare-result compare-grid">
        <div class="stats-grid">
          <div><strong>{{ compareResult.added_elements.length }}</strong><span>新增元素</span></div>
          <div><strong>{{ compareResult.removed_elements.length }}</strong><span>删除元素</span></div>
          <div><strong>{{ compareResult.changed_elements.length }}</strong><span>变更元素</span></div>
          <div><strong>{{ compareResult.added_relations.length + compareResult.removed_relations.length }}</strong><span>关系变化</span></div>
        </div>
        <el-tabs class="compare-tabs">
          <el-tab-pane label="新增">
            <el-table :data="compareResult.added_elements" height="220" size="small">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="type" label="类型" width="160" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="删除">
            <el-table :data="compareResult.removed_elements" height="220" size="small">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="type" label="类型" width="160" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="变更">
            <el-table :data="compareResult.changed_elements" height="220" size="small">
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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import type { TreeInstance } from 'element-plus'
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

interface ElementTreeNode {
  uid: string
  label: string
  element: ModelElement
  children: ElementTreeNode[]
}

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const elements = ref<ModelElement[]>([])
const relations = ref<ModelRelation[]>([])
const selected = ref<SysMLModel | null>(null)
const selectedElement = ref<ModelElement | null>(null)
const loading = ref(false)
const file = ref<File | null>(null)
const upload = reactive({ project_id: undefined as number | undefined, name: '', description: '' })
const editDialog = ref(false)
const editing = ref<ModelElement | null>(null)
const targetModelId = ref<number>()
const compareResult = ref<ModelCompare | null>(null)
const elementKeyword = ref('')
const elementType = ref('')
const modelTreeRef = ref<TreeInstance>()

const elementByUid = computed(() => new Map(elements.value.map((element) => [element.element_uid, element])))
const elementTypes = computed(() => [...new Set(elements.value.map((item) => item.type).filter(Boolean))].sort())
const selectedParentUid = computed(() => selectedElement.value?.parent_uid || '')
const selectedChildUids = computed(
  () =>
    new Set(
      selectedElement.value
        ? elements.value
            .filter((element) => element.parent_uid === selectedElement.value?.element_uid)
            .map((element) => element.element_uid)
        : [],
    ),
)
const filteredElements = computed(() => {
  const keyword = elementKeyword.value.trim().toLowerCase()
  return elements.value.filter((element) => {
    const matchesType = !elementType.value || element.type === elementType.value
    const text = `${element.name} ${element.type} ${element.documentation || ''}`.toLowerCase()
    return matchesType && (!keyword || text.includes(keyword))
  })
})
const visibleElementUids = computed(() => new Set(filteredElements.value.map((element) => element.element_uid)))
const visibleRelations = computed(() =>
  relations.value.filter(
    (relation) => visibleElementUids.value.has(relation.source_uid) || visibleElementUids.value.has(relation.target_uid),
  ),
)

const elementTree = computed(() => {
  const nodes = new Map<string, ElementTreeNode>()
  filteredElements.value.forEach((element) => {
    nodes.set(element.element_uid, {
      uid: element.element_uid,
      label: `${element.name} (${element.type})`,
      element,
      children: [],
    })
  })
  const roots: ElementTreeNode[] = []
  nodes.forEach((node) => {
    const parent = node.element.parent_uid ? nodes.get(node.element.parent_uid) : undefined
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
})

const graphSourceElements = computed(() => {
  if (!selectedElement.value) return filteredElements.value.slice(0, 36)
  const relatedUids = new Set<string>([selectedElement.value.element_uid])
  if (selectedElement.value.parent_uid) relatedUids.add(selectedElement.value.parent_uid)
  selectedChildUids.value.forEach((uid) => relatedUids.add(uid))
  relations.value.forEach((relation) => {
    if (relation.source_uid === selectedElement.value?.element_uid) relatedUids.add(relation.target_uid)
    if (relation.target_uid === selectedElement.value?.element_uid) relatedUids.add(relation.source_uid)
  })
  return Array.from(relatedUids)
    .map((uid) => elementByUid.value.get(uid))
    .filter((element): element is ModelElement => Boolean(element))
    .slice(0, 36)
})

const graphNodes = computed(() => {
  const centerX = 380
  const centerY = 215
  const radius = selectedElement.value ? 145 : 150
  const visible = graphSourceElements.value
  return visible.map((element, index) => {
    if (selectedElement.value?.element_uid === element.element_uid) {
      return { uid: element.element_uid, element, x: centerX, y: centerY }
    }
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

const selectedElementRelations = computed(() => {
  if (!selectedElement.value) return []
  return relations.value.filter(
    (relation) =>
      relation.source_uid === selectedElement.value?.element_uid ||
      relation.target_uid === selectedElement.value?.element_uid,
  )
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
  selectedElement.value = null
  targetModelId.value = undefined
  compareResult.value = null
  elementKeyword.value = ''
  elementType.value = ''
  const graph = await modelApi.graph(row.id)
  elements.value = graph.elements
  relations.value = graph.relations
}
function focusElement(row: ModelElement) {
  selectedElement.value = row
  syncTreeSelection(row.element_uid)
}
function focusTreeNode(node: ElementTreeNode) {
  selectedElement.value = node.element
  syncTreeSelection(node.uid)
}
function focusRelation(row: ModelRelation) {
  const element = elementByUid.value.get(row.source_uid) || elementByUid.value.get(row.target_uid)
  if (element) focusElement(element)
}
function editElement(row: ModelElement) {
  selectedElement.value = row
  syncTreeSelection(row.element_uid)
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
  if (selectedElement.value?.id === updated.id) selectedElement.value = updated
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
function relationPeerName(relation: ModelRelation) {
  if (!selectedElement.value) return ''
  const peerUid =
    relation.source_uid === selectedElement.value.element_uid ? relation.target_uid : relation.source_uid
  return elementByUid.value.get(peerUid)?.name || peerUid
}
async function syncTreeSelection(uid: string) {
  await nextTick()
  const tree = modelTreeRef.value
  if (!tree) return
  tree.setCurrentKey(uid)
  let currentNode: any = tree.getNode(uid)
  while (currentNode) {
    currentNode.expanded = true
    currentNode = currentNode.parent
  }
  await nextTick()
  document.querySelector('.model-tree .is-current')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
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
.compare-toolbar,
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.filter-bar {
  margin-bottom: 12px;
}
.filter-bar .el-input {
  flex: 1;
}
.filter-bar .el-select {
  width: 180px;
}
.viewer-row {
  margin-top: 18px;
  align-items: stretch;
}
.viewer-col {
  display: flex;
}
.viewer-card {
  width: 100%;
}
.viewer-card :deep(.el-card__body) {
  height: 512px;
}
.tree-scroll {
  height: 100%;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.model-tree {
  min-width: 680px;
  padding: 8px 0;
}
.model-tree :deep(.el-tree-node__content) {
  white-space: nowrap;
}
.model-tree :deep(.el-tree-node__label) {
  white-space: nowrap;
}
.graph-legend {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 13px;
}
.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 6px;
  border-radius: 50%;
  vertical-align: -1px;
}
.current-dot {
  background: #f6d7bd;
  border: 1px solid var(--accent);
}
.parent-dot {
  background: #fde68a;
  border: 1px solid #b45309;
}
.child-dot {
  background: #dcfce7;
  border: 1px solid #15803d;
}
.graph-panel {
  height: 434px;
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
.graph-node.selectedParent circle {
  fill: #fde68a;
  stroke: #b45309;
  stroke-width: 2.6;
}
.graph-node.selectedChild circle {
  fill: #dcfce7;
  stroke: #15803d;
  stroke-width: 2.6;
}
.graph-node.active circle {
  fill: #f6d7bd;
  stroke: var(--accent);
  stroke-width: 3;
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
.detail-panel h3 {
  margin: 0 0 12px;
  font-size: 18px;
}
.detail-doc {
  margin: 14px 0;
  border: 1px solid #b7d4d6;
  border-left: 5px solid var(--brand);
  border-radius: 8px;
  background: #eef7f6;
  overflow: hidden;
}
.detail-doc-title {
  padding: 8px 12px;
  font-weight: 700;
  color: var(--brand-dark);
  background: #d8eeee;
  border-bottom: 1px solid #b7d4d6;
}
.detail-doc-body {
  min-height: 72px;
  max-height: 130px;
  overflow: auto;
  padding: 12px;
  color: var(--ink);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.compare-result {
  margin-top: 14px;
}
.compare-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.compare-tabs {
  min-width: 0;
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
