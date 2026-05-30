<template>
  <div>
    <h1 class="page-title">模型管理</h1>
    <el-card class="ingest-card">
      <template #header>
        <div class="card-header">
          <span>模型导入来源</span>
          <el-tag type="info">本地文件 / OpenMBEE MMS / Jupyter</el-tag>
        </div>
      </template>
      <el-tabs v-model="importSource" class="ingest-tabs" @tab-change="handleImportTabChange">
        <el-tab-pane label="本地文件" name="local">
          <el-form label-position="top" class="upload-form">
            <div class="upload-fields">
              <el-form-item label="所属项目">
                <el-select v-model="upload.project_id" placeholder="选择项目">
                  <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="模型名称"><el-input v-model="upload.name" /></el-form-item>
              <el-form-item label="模型说明"><el-input v-model="upload.description" /></el-form-item>
              <el-form-item label="分支"><el-input v-model="upload.branch_name" placeholder="main" /></el-form-item>
              <el-form-item label="标记"><el-input v-model="upload.version_tag" placeholder="例如 v1.0-baseline" /></el-form-item>
              <el-form-item label="模型文件">
                <input class="file-input" type="file" accept=".xmi,.xml,.json,.uml,.sysml,.mms" @change="onFile" />
              </el-form-item>
            </div>
            <div class="upload-actions">
              <el-button type="primary" :loading="loading" @click="submit">上传并解析</el-button>
            </div>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="OpenMBEE MMS" name="mms">
          <div class="integration-panel">
            <div class="integration-summary">
              <div>
                <h3>OpenMBEE MMS 接入</h3>
                <p>用于后续连接 Cameo + MDK 同步到 MMS 的模型数据。当前先展示配置状态和接口目录。</p>
              </div>
              <div class="integration-actions">
                <el-tag :type="openMbeeConfig?.mms_configured ? 'success' : 'warning'">
                  {{ openMbeeConfig?.mms_configured ? '已配置 MMS' : '未配置 MMS' }}
                </el-tag>
                <el-button :disabled="!openMbeeConfig?.mms_configured" :loading="openMbeeTesting" @click="testMmsConnection">
                  测试连接
                </el-button>
                <el-button :loading="openMbeeLoading" @click="loadOpenMbeeInfo">刷新</el-button>
              </div>
            </div>
            <el-alert
              v-if="!openMbeeConfig?.mms_configured"
              type="warning"
              :closable="false"
              title="尚未配置 OpenMBEE MMS。可以先查看接口目录；真实连接需要在后端 .env 中配置 OPENMBEE_MMS_URL。"
            />
            <el-descriptions v-else :column="1" border size="small" class="integration-desc">
              <el-descriptions-item label="MMS 地址">{{ openMbeeConfig.mms_url }}</el-descriptions-item>
              <el-descriptions-item label="Doc Convert">
                {{ openMbeeConfig.doc_convert_configured ? openMbeeConfig.doc_convert_url : '未配置' }}
              </el-descriptions-item>
            </el-descriptions>
            <el-form label-position="top" class="mms-import-form">
              <el-form-item label="导入到本地项目">
                <el-select v-model="mmsImportForm.local_project_id" placeholder="选择本地项目">
                  <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="本地模型名称">
                <el-input v-model="mmsImportForm.name" placeholder="从 MMS 导入的模型名称" />
              </el-form-item>
              <el-form-item label="模型说明">
                <el-input v-model="mmsImportForm.description" placeholder="可选" />
              </el-form-item>
              <el-form-item label="MMS 项目 ID">
                <el-select
                  v-model="mmsImportForm.mms_project_id"
                  allow-create
                  filterable
                  default-first-option
                  placeholder="输入或选择 MMS 项目"
                  @change="loadMmsRefs"
                >
                  <el-option v-for="project in mmsProjects" :key="mmsItemId(project)" :label="mmsItemLabel(project)" :value="mmsItemId(project)" />
                </el-select>
              </el-form-item>
              <el-form-item label="MMS 分支">
                <el-select
                  v-model="mmsImportForm.ref_id"
                  allow-create
                  filterable
                  default-first-option
                  placeholder="master / main / refs"
                >
                  <el-option v-for="refItem in mmsRefs" :key="mmsItemId(refItem)" :label="mmsItemLabel(refItem)" :value="mmsItemId(refItem)" />
                </el-select>
              </el-form-item>
              <el-form-item label="根元素 ID">
                <el-input v-model="mmsImportForm.root_element_id" placeholder="优先按根元素递归导入" />
              </el-form-item>
              <el-form-item label="搜索关键词">
                <el-input v-model="mmsImportForm.search_keyword" placeholder="不填根元素时使用搜索导入" />
              </el-form-item>
              <el-form-item label="提交版本">
                <el-input v-model="mmsImportForm.commit_id" placeholder="latest / commitId，可选" />
              </el-form-item>
              <el-form-item label="数量限制">
                <el-input-number v-model="mmsImportForm.limit" :min="1" :max="2000" />
              </el-form-item>
              <el-form-item label="递归深度">
                <el-input-number v-model="mmsImportForm.depth" :min="1" :max="20" placeholder="可选" />
              </el-form-item>
              <div class="mms-form-actions">
                <el-button :disabled="!openMbeeConfig?.mms_configured" :loading="mmsProjectsLoading" @click="loadMmsProjects">
                  获取 MMS 项目
                </el-button>
                <el-button :disabled="!openMbeeConfig?.mms_configured || !mmsImportForm.mms_project_id" :loading="mmsRefsLoading" @click="loadMmsRefs">
                  获取分支
                </el-button>
                <el-button type="primary" :disabled="!openMbeeConfig?.mms_configured" :loading="mmsImporting" @click="importFromMms">
                  导入为本地模型
                </el-button>
              </div>
            </el-form>
            <el-alert
              v-if="mmsImportResult"
              type="success"
              :closable="false"
              :title="`已导入模型 ${mmsImportResult.model.name} v${mmsImportResult.model.version}，元素 ${mmsImportResult.imported_elements} 个，关系 ${mmsImportResult.imported_relations} 条。`"
            />
            <el-table :data="openMbeeEndpoints" height="260" size="small" stripe class="endpoint-table">
              <el-table-column prop="method" label="方法" width="86" />
              <el-table-column prop="path" label="接口路径" min-width="280" />
              <el-table-column prop="description" label="说明" min-width="180" />
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="Jupyter 实验台" name="jupyter">
          <div class="integration-panel">
            <div class="integration-summary">
              <div>
                <h3>Jupyter Notebook 验证</h3>
                <p>用于演示登录、上传模型、查看元素关系、生成文档，以及验证 OpenMBEE 适配接口目录。</p>
              </div>
              <div class="integration-actions">
                <el-button type="primary" @click="openJupyter">打开 Notebook</el-button>
                <el-button @click="copyToClipboard(jupyterCommand)">复制启动命令</el-button>
              </div>
            </div>
            <div class="jupyter-grid">
              <div class="command-box">
                <span>启动命令</span>
                <pre>{{ jupyterCommand }}</pre>
              </div>
              <div class="command-box">
                <span>Notebook 地址</span>
                <pre>{{ jupyterUrl }}</pre>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card style="margin-top: 18px">
      <template #header>模型列表</template>
      <el-table :data="models" stripe highlight-current-row @row-click="selectModel">
        <el-table-column prop="name" label="模型名称" />
        <el-table-column prop="description" label="说明" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="branch_name" label="分支" width="120" />
        <el-table-column label="标记" width="140">
          <template #default="{ row }">{{ row.version_tag || '-' }}</template>
        </el-table-column>
        <el-table-column prop="source_filename" label="源文件" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ statusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" />
        <el-table-column label="操作" width="150" fixed="right" class-name="table-actions-cell">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button text type="primary" @click.stop="editModel(row)">编辑</el-button>
              <el-button text type="danger" @click.stop="removeModel(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card style="margin-top: 18px">
      <template #header>
        <div class="card-header">
          <span>模型版本分支 / 标签 / 回滚</span>
          <el-select v-model="versionProjectId" placeholder="选择项目" style="width: 240px" @change="loadModelVersioning">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </div>
      </template>
      <div class="version-grid">
        <div class="version-panel">
          <h3>分支</h3>
          <div class="version-form">
            <el-input v-model="branchForm.name" placeholder="分支名称，如 main" />
            <el-select v-model="branchForm.source_model_id" clearable placeholder="来源模型版本">
              <el-option v-for="model in versionModels" :key="model.id" :label="modelVersionLabel(model)" :value="model.id" />
            </el-select>
            <el-button type="primary" @click="createBranch">创建</el-button>
          </div>
          <el-table :data="branches" height="220" size="small" stripe @row-click="selectBranch">
            <el-table-column prop="name" label="分支" />
            <el-table-column label="当前模型">
              <template #default="{ row }">{{ modelLabel(row.head_model) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="210" class-name="table-actions-cell">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button text type="primary" @click.stop="prepareTag(row)">打标签</el-button>
                  <el-button text type="primary" @click.stop="renameBranch(row)">重命名</el-button>
                  <el-button text type="danger" @click.stop="deleteBranch(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="version-panel">
          <h3>标签</h3>
          <div class="version-form">
            <el-input v-model="tagForm.name" placeholder="标签名称，如 baseline-v1" />
            <el-select v-model="tagForm.model_id" clearable placeholder="目标模型">
              <el-option v-for="model in tagTargetModels" :key="model.id" :label="modelVersionLabel(model)" :value="model.id" />
            </el-select>
            <el-button @click="createTag">创建</el-button>
          </div>
          <el-table :data="tags" height="220" size="small" stripe>
            <el-table-column prop="name" label="标签" />
            <el-table-column label="目标模型">
              <template #default="{ row }">{{ modelLabel(row.model) }}</template>
            </el-table-column>
            <el-table-column label="分支">
              <template #default="{ row }">{{ branchName(row.branch_id) }}</template>
            </el-table-column>
          </el-table>
        </div>
        <div class="version-panel">
          <h3>回滚</h3>
          <div class="version-form rollback-form">
            <el-select v-model="rollbackForm.branch_id" clearable placeholder="目标分支" @change="resetInvalidRollbackTargets">
              <el-option v-for="branch in branches" :key="branch.id" :label="branch.name" :value="branch.id" />
            </el-select>
            <el-radio-group v-model="rollbackMode">
              <el-radio-button label="tag">标签</el-radio-button>
              <el-radio-button label="model">模型</el-radio-button>
            </el-radio-group>
            <el-select v-if="rollbackMode === 'tag'" v-model="rollbackForm.tag_id" clearable placeholder="目标标签">
              <el-option v-for="tag in rollbackTargetTags" :key="tag.id" :label="`${tag.name}：${modelLabel(tag.model)}`" :value="tag.id" />
            </el-select>
            <el-select v-else v-model="rollbackForm.target_model_id" clearable placeholder="目标模型">
              <el-option v-for="model in rollbackTargetModels" :key="model.id" :label="modelVersionLabel(model)" :value="model.id" />
            </el-select>
            <el-input v-model="rollbackForm.reason" placeholder="回滚原因" />
            <el-button type="warning" @click="rollbackModel">执行回滚</el-button>
          </div>
          <el-table :data="rollbackRecords" height="150" size="small" stripe>
            <el-table-column label="分支" width="90">
              <template #default="{ row }">{{ branchName(row.branch_id) }}</template>
            </el-table-column>
            <el-table-column label="回滚到">
              <template #default="{ row }">{{ modelLabel(row.target_model) }}</template>
            </el-table-column>
            <el-table-column label="生成版本">
              <template #default="{ row }">{{ modelLabel(row.new_model) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
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
          <el-table :data="pagedElements" height="380" stripe highlight-current-row @row-click="focusElement">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="type" label="类型" width="140" />
            <el-table-column prop="documentation" label="说明" />
            <el-table-column label="操作" width="90" class-name="table-actions-cell">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button text type="primary" @click.stop="editElement(row)">编辑</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="elementPage"
            v-model:page-size="elementPageSize"
            class="table-pagination"
            layout="total, sizes, prev, pager, next"
            :page-sizes="[20, 50, 100]"
            :total="filteredElements.length"
          />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>元素关系</span>
              <div class="table-actions">
                <span class="muted">{{ visibleRelations.length }} / {{ relations.length }}</span>
                <el-button size="small" type="primary" @click="createRelation">新增关系</el-button>
              </div>
            </div>
          </template>
          <div class="filter-bar relation-filter">
            <el-input v-model="relationKeyword" clearable placeholder="按元素、关系类型或标签过滤" />
            <el-select v-model="relationType" clearable placeholder="全部关系">
              <el-option v-for="type in relationTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </div>
          <el-table :data="pagedRelations" height="380" stripe @row-click="focusRelation">
            <el-table-column label="源">
              <template #default="{ row }">{{ elementName(row.source_uid) }}</template>
            </el-table-column>
            <el-table-column prop="relation_type" label="关系" width="120" />
            <el-table-column label="目标">
              <template #default="{ row }">{{ elementName(row.target_uid) }}</template>
            </el-table-column>
            <el-table-column prop="label" label="标签" width="100" />
            <el-table-column label="操作" width="120" class-name="table-actions-cell">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button text type="primary" @click.stop="editRelation(row)">编辑</el-button>
                  <el-button text type="danger" @click.stop="removeRelation(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="relationPage"
            v-model:page-size="relationPageSize"
            class="table-pagination"
            layout="total, sizes, prev, pager, next"
            :page-sizes="[20, 50, 100]"
            :total="visibleRelations.length"
          />
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
              <div class="graph-actions">
                <span class="muted">展示 {{ graphNodes.length }} 个元素、{{ graphEdges.length }} 条关系</span>
                <el-tooltip content="适配视图" placement="top">
                  <el-button class="graph-tool-button" circle :icon="Aim" @click="fitGraph" />
                </el-tooltip>
                <el-tooltip content="放大" placement="top">
                  <el-button class="graph-tool-button" circle :icon="ZoomIn" @click="zoomGraph(1.15)" />
                </el-tooltip>
                <el-tooltip content="缩小" placement="top">
                  <el-button class="graph-tool-button" circle :icon="ZoomOut" @click="zoomGraph(0.87)" />
                </el-tooltip>
                <el-tooltip content="返回概览" placement="top">
                  <el-button class="graph-tool-button" circle :icon="RefreshLeft" :disabled="!selectedElement" @click="clearFocus" />
                </el-tooltip>
              </div>
            </div>
          </template>
          <div class="graph-toolbar">
            <el-radio-group v-model="graphLayout" size="small" @change="resetGraphPositions">
              <el-radio-button label="radial">环形</el-radio-button>
              <el-radio-button label="hierarchy">分层</el-radio-button>
              <el-radio-button label="force">力导向</el-radio-button>
            </el-radio-group>
            <el-select v-model="graphScope" size="small" class="graph-scope" @change="resetGraphPositions">
              <el-option label="智能概览" value="important" />
              <el-option label="筛选结果" value="filtered" />
              <el-option label="当前邻域" value="neighborhood" />
            </el-select>
            <el-input-number v-model="graphNodeLimit" size="small" :min="8" :max="80" :step="4" controls-position="right" />
            <el-input-number v-model="graphEdgeLimit" size="small" :min="20" :max="240" :step="20" controls-position="right" />
          </div>
          <div class="graph-legend">
            <span><i class="legend-dot current-dot"></i>当前节点</span>
            <span><i class="legend-dot parent-dot"></i>当前节点的父节点</span>
            <span><i class="legend-dot child-dot"></i>当前节点的子节点</span>
          </div>
          <div class="graph-panel">
            <svg
              ref="graphSvgRef"
              viewBox="0 0 760 430"
              role="img"
              aria-label="模型关系图"
              @pointerdown="startGraphPan"
              @pointermove="moveGraphPointer"
              @pointerup="endGraphPointer"
              @pointerleave="endGraphPointer"
              @wheel.prevent="handleGraphWheel"
            >
              <defs>
                <marker id="arrow" markerWidth="12" markerHeight="12" refX="11" refY="4" orient="auto">
                  <path d="M0,0 L0,8 L11,4 z" fill="#6b7280" />
                </marker>
              </defs>
              <g :transform="graphTransform">
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
                  @pointerdown.stop="startNodeDrag($event, node)"
                  @pointerup.stop="endNodePointer($event, node.element)"
                >
                  <title>{{ nodeTooltip(node.element) }}</title>
                  <circle :cx="node.x" :cy="node.y" r="42" />
                  <text :x="node.x" :y="node.y - 6" text-anchor="middle">{{ compactName(node.element.name) }}</text>
                  <text :x="node.x" :y="node.y + 13" text-anchor="middle" class="node-type">{{ node.element.type }}</text>
                </g>
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
          <el-option v-for="item in comparableModels" :key="item.id" :label="modelVersionLabel(item)" :value="item.id" />
        </el-select>
        <div class="table-export-actions">
          <el-button type="primary" :disabled="!targetModelId" @click="loadCompare">对比</el-button>
          <el-button :disabled="!compareResult" @click="exportCompareCsv">导出 CSV</el-button>
          <el-button :disabled="!compareResult" @click="exportCompareHtml">导出 HTML</el-button>
        </div>
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

    <el-dialog v-model="modelDialog" title="编辑模型" width="560px" @closed="resetModelForm">
      <el-form label-position="top">
        <el-form-item label="模型名称"><el-input v-model="modelForm.name" /></el-form-item>
        <el-form-item label="模型说明"><el-input v-model="modelForm.description" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modelDialog = false">取消</el-button>
        <el-button type="primary" @click="saveModel">保存</el-button>
      </template>
    </el-dialog>

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

    <el-dialog v-model="relationDialog" :title="editingRelationId ? '编辑模型关系' : '新增模型关系'" width="620px" @closed="resetRelationForm">
      <el-form label-position="top">
        <el-form-item label="源元素">
          <el-select v-model="relationForm.source_uid" filterable placeholder="选择源元素" class="wide">
            <el-option v-for="element in elements" :key="element.element_uid" :label="elementOptionLabel(element)" :value="element.element_uid" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标元素">
          <el-select v-model="relationForm.target_uid" filterable placeholder="选择目标元素" class="wide">
            <el-option v-for="element in elements" :key="element.element_uid" :label="elementOptionLabel(element)" :value="element.element_uid" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型"><el-input v-model="relationForm.relation_type" placeholder="例如 dependency / composition" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="relationForm.label" placeholder="可选" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="relationDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRelation">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import type { TabsPaneContext, TreeInstance } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, RefreshLeft, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import { apiError } from '@/api/http'
import {
  modelApi,
  openMbeeApi,
  projectApi,
  versioningApi,
  type ModelCompare,
  type ModelElement,
  type ModelRelation,
  type OpenMbeeConfig,
  type OpenMbeeEndpoint,
  type OpenMbeeImportResult,
  type Project,
  type SysMLModel,
  type VersionBranch,
  type VersionRollbackRecord,
  type VersionTag,
} from '@/api'

interface ElementTreeNode {
  uid: string
  label: string
  element: ModelElement
  children: ElementTreeNode[]
}

interface GraphNode {
  uid: string
  element: ModelElement
  x: number
  y: number
}

const projects = ref<Project[]>([])
const models = ref<SysMLModel[]>([])
const elements = ref<ModelElement[]>([])
const relations = ref<ModelRelation[]>([])
const selected = ref<SysMLModel | null>(null)
const selectedElement = ref<ModelElement | null>(null)
const loading = ref(false)
const file = ref<File | null>(null)
const importSource = ref<'local' | 'mms' | 'jupyter'>('local')
const openMbeeLoading = ref(false)
const openMbeeTesting = ref(false)
const mmsProjectsLoading = ref(false)
const mmsRefsLoading = ref(false)
const mmsImporting = ref(false)
const openMbeeConfig = ref<OpenMbeeConfig | null>(null)
const openMbeeEndpoints = ref<OpenMbeeEndpoint[]>([])
const mmsProjects = ref<Record<string, unknown>[]>([])
const mmsRefs = ref<Record<string, unknown>[]>([])
const mmsImportResult = ref<OpenMbeeImportResult | null>(null)
const upload = reactive({
  project_id: undefined as number | undefined,
  name: '',
  description: '',
  branch_name: 'main',
  version_tag: '',
})
const mmsImportForm = reactive({
  local_project_id: undefined as number | undefined,
  name: '',
  description: '',
  mms_project_id: '',
  ref_id: 'master',
  root_element_id: '',
  commit_id: '',
  search_keyword: '',
  element_type: '',
  limit: 200,
  depth: undefined as number | undefined,
})
const jupyterUrl = 'http://127.0.0.1:8888/lab/tree/notebooks/sysml_docgen_openmbee_demo.ipynb'
const jupyterCommand = 'powershell -ExecutionPolicy Bypass -File .\\scripts\\start_jupyter.ps1'
const modelDialog = ref(false)
const editingModelId = ref<number>()
const modelForm = reactive({ name: '', description: '' })
const editDialog = ref(false)
const editing = ref<ModelElement | null>(null)
const relationDialog = ref(false)
const editingRelationId = ref<number>()
const relationForm = reactive({ source_uid: '', target_uid: '', relation_type: '', label: '' })
const targetModelId = ref<number>()
const compareResult = ref<ModelCompare | null>(null)
const elementKeyword = ref('')
const elementType = ref('')
const relationKeyword = ref('')
const relationType = ref('')
const elementPage = ref(1)
const elementPageSize = ref(50)
const relationPage = ref(1)
const relationPageSize = ref(50)
const modelTreeRef = ref<TreeInstance>()
const graphSvgRef = ref<SVGSVGElement>()
const graphLayout = ref<'radial' | 'hierarchy' | 'force'>('radial')
const graphScope = ref<'important' | 'filtered' | 'neighborhood'>('important')
const graphNodeLimit = ref(24)
const graphEdgeLimit = ref(80)
const graphView = reactive({ scale: 1, x: 0, y: 0 })
const graphDrag = reactive({
  mode: '' as '' | 'pan' | 'node',
  uid: '',
  startX: 0,
  startY: 0,
  startViewX: 0,
  startViewY: 0,
  originX: 0,
  originY: 0,
  moved: false,
})
const manualGraphPositions = reactive<Record<string, { x: number; y: number }>>({})
const versionProjectId = ref<number>()
const branches = ref<VersionBranch[]>([])
const tags = ref<VersionTag[]>([])
const rollbackRecords = ref<VersionRollbackRecord[]>([])
const rollbackMode = ref<'tag' | 'model'>('tag')
const branchForm = reactive({ name: '', source_model_id: undefined as number | undefined })
const tagForm = reactive({ name: '', branch_id: undefined as number | undefined, model_id: undefined as number | undefined })
const rollbackForm = reactive({
  branch_id: undefined as number | undefined,
  tag_id: undefined as number | undefined,
  target_model_id: undefined as number | undefined,
  reason: '',
})

const elementByUid = computed(() => new Map(elements.value.map((element) => [element.element_uid, element])))
const elementTypes = computed(() => [...new Set(elements.value.map((item) => item.type).filter(Boolean))].sort())
const relationTypes = computed(() => [...new Set(relations.value.map((item) => item.relation_type).filter(Boolean))].sort())
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
const childCountByUid = computed(() => {
  const counts = new Map<string, number>()
  elements.value.forEach((element) => {
    if (!element.parent_uid) return
    counts.set(element.parent_uid, (counts.get(element.parent_uid) || 0) + 1)
  })
  return counts
})
const relationDegreeByUid = computed(() => {
  const degrees = new Map<string, number>()
  relations.value.forEach((relation) => {
    degrees.set(relation.source_uid, (degrees.get(relation.source_uid) || 0) + 1)
    degrees.set(relation.target_uid, (degrees.get(relation.target_uid) || 0) + 1)
  })
  return degrees
})
const filteredElements = computed(() => {
  const keyword = elementKeyword.value.trim().toLowerCase()
  return elements.value.filter((element) => {
    const matchesType = !elementType.value || element.type === elementType.value
    const text = `${element.name} ${element.type} ${element.documentation || ''}`.toLowerCase()
    return matchesType && (!keyword || text.includes(keyword))
  })
})
const pagedElements = computed(() => paginate(filteredElements.value, elementPage.value, elementPageSize.value))
const visibleElementUids = computed(() => new Set(filteredElements.value.map((element) => element.element_uid)))
const visibleRelations = computed(() => {
  const keyword = relationKeyword.value.trim().toLowerCase()
  return relations.value.filter((relation) => {
    const source = elementByUid.value.get(relation.source_uid)
    const target = elementByUid.value.get(relation.target_uid)
    const matchesVisibleElement = visibleElementUids.value.has(relation.source_uid) || visibleElementUids.value.has(relation.target_uid)
    const matchesType = !relationType.value || relation.relation_type === relationType.value
    const text = [
      relation.source_uid,
      relation.target_uid,
      relation.relation_type,
      relation.label || '',
      source?.name || '',
      target?.name || '',
      source?.type || '',
      target?.type || '',
    ]
      .join(' ')
      .toLowerCase()
    return matchesVisibleElement && matchesType && (!keyword || text.includes(keyword))
  })
})
const pagedRelations = computed(() => paginate(visibleRelations.value, relationPage.value, relationPageSize.value))
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
const overviewGraphElements = computed(() => {
  const picked = new Map<string, ModelElement>()
  const add = (items: ModelElement[], limit: number) => {
    items.slice(0, limit).forEach((element) => picked.set(element.element_uid, element))
  }
  const candidates = filteredElements.value
  const roots = candidates.filter((element) => !element.parent_uid)
  const parents = candidates
    .filter((element) => childCountByUid.value.has(element.element_uid))
    .sort((a, b) => (childCountByUid.value.get(b.element_uid) || 0) - (childCountByUid.value.get(a.element_uid) || 0))
  const connected = [...candidates].sort(
    (a, b) => (relationDegreeByUid.value.get(b.element_uid) || 0) - (relationDegreeByUid.value.get(a.element_uid) || 0),
  )
  const baseLimit = graphScope.value === 'filtered' ? graphNodeLimit.value : Math.max(8, Math.min(graphNodeLimit.value, 32))
  add(roots, Math.ceil(baseLimit * 0.3))
  add(parents, Math.ceil(baseLimit * 0.45))
  add(connected, Math.ceil(baseLimit * 0.65))
  add(candidates, baseLimit)
  return Array.from(picked.values()).slice(0, baseLimit)
})
const graphSourceElements = computed(() => {
  if (graphScope.value === 'filtered') return filteredElements.value.slice(0, graphNodeLimit.value)
  if (graphScope.value !== 'neighborhood' && !selectedElement.value) return overviewGraphElements.value
  if (!selectedElement.value) return overviewGraphElements.value
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
    .slice(0, graphNodeLimit.value)
})
const graphNodes = computed(() => {
  const visible = graphSourceElements.value
  const laidOut =
    graphLayout.value === 'hierarchy'
      ? hierarchyLayout(visible)
      : graphLayout.value === 'force'
        ? forceLayout(visible)
        : radialLayout(visible)
  return laidOut.map((node) => {
    const manual = manualGraphPositions[node.uid]
    return manual ? { ...node, x: manual.x, y: manual.y } : node
  })
})
const graphEdges = computed(() => {
  const nodeMap = new Map(graphNodes.value.map((node) => [node.uid, node]))
  return visibleRelations.value
    .filter((relation) => nodeMap.has(relation.source_uid) && nodeMap.has(relation.target_uid))
    .slice(0, graphEdgeLimit.value)
    .map((relation) => ({
      key: relation.id,
      source: nodeMap.get(relation.source_uid)!,
      target: nodeMap.get(relation.target_uid)!,
    }))
})
const graphTransform = computed(() => `matrix(${graphView.scale} 0 0 ${graphView.scale} ${graphView.x} ${graphView.y})`)
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
const versionModels = computed(() => models.value.filter((item) => item.project_id === versionProjectId.value))
const tagTargetModels = computed(() => {
  const branch = branches.value.find((item) => item.id === tagForm.branch_id)
  if (!branch) return versionModels.value
  return versionModels.value.filter((model) => model.branch_name === branch.name)
})
const rollbackBranch = computed(() => branches.value.find((item) => item.id === rollbackForm.branch_id))
const rollbackTargetModels = computed(() => {
  if (!rollbackBranch.value) return []
  return versionModels.value.filter((model) => model.branch_name === rollbackBranch.value?.name)
})
const rollbackTargetTags = computed(() => {
  if (!rollbackBranch.value) return []
  return tags.value.filter((tag) => tag.branch_id === rollbackBranch.value?.id)
})

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
}

function paginate<T>(items: T[], page: number, pageSize: number) {
  const start = (page - 1) * pageSize
  return items.slice(start, start + pageSize)
}

function radialLayout(visible: ModelElement[]): GraphNode[] {
  const centerX = 380
  const centerY = 215
  const radius = selectedElement.value ? 145 : visible.length > 16 ? 165 : 150
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
}

function hierarchyLayout(visible: ModelElement[]): GraphNode[] {
  const visibleUids = new Set(visible.map((element) => element.element_uid))
  const depthCache = new Map<string, number>()
  const depthOf = (element: ModelElement): number => {
    if (depthCache.has(element.element_uid)) return depthCache.get(element.element_uid)!
    if (!element.parent_uid || !visibleUids.has(element.parent_uid)) {
      depthCache.set(element.element_uid, 0)
      return 0
    }
    const parent = elementByUid.value.get(element.parent_uid)
    const depth = parent ? depthOf(parent) + 1 : 0
    depthCache.set(element.element_uid, depth)
    return depth
  }
  const groups = new Map<number, ModelElement[]>()
  visible.forEach((element) => {
    const depth = Math.min(depthOf(element), 5)
    groups.set(depth, [...(groups.get(depth) || []), element])
  })
  const levels = [...groups.keys()].sort((a, b) => a - b)
  const top = 74
  const levelGap = levels.length > 1 ? Math.min(84, 300 / (levels.length - 1)) : 0
  const nodes: GraphNode[] = []
  levels.forEach((depth, levelIndex) => {
    const items = groups.get(depth) || []
    const rowY = top + levelIndex * levelGap
    items.forEach((element, index) => {
      const gap = 680 / Math.max(items.length, 1)
      nodes.push({
        uid: element.element_uid,
        element,
        x: Math.round(40 + gap / 2 + index * gap),
        y: Math.round(rowY),
      })
    })
  })
  return nodes
}

function forceLayout(visible: ModelElement[]): GraphNode[] {
  const nodes = radialLayout(visible).map((node) => ({ ...node }))
  const indexByUid = new Map(nodes.map((node, index) => [node.uid, index]))
  const activeRelations = visibleRelations.value.filter((relation) => indexByUid.has(relation.source_uid) && indexByUid.has(relation.target_uid))
  for (let step = 0; step < 70; step += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i]
        const b = nodes[j]
        const dx = a.x - b.x || 1
        const dy = a.y - b.y || 1
        const distanceSq = Math.max(dx * dx + dy * dy, 900)
        const force = 2200 / distanceSq
        const fx = dx * force
        const fy = dy * force
        a.x += fx
        a.y += fy
        b.x -= fx
        b.y -= fy
      }
    }
    activeRelations.forEach((relation) => {
      const source = nodes[indexByUid.get(relation.source_uid)!]
      const target = nodes[indexByUid.get(relation.target_uid)!]
      const dx = target.x - source.x
      const dy = target.y - source.y
      source.x += dx * 0.012
      source.y += dy * 0.012
      target.x -= dx * 0.012
      target.y -= dy * 0.012
    })
    nodes.forEach((node) => {
      node.x += (380 - node.x) * 0.01
      node.y += (215 - node.y) * 0.01
      node.x = Math.min(710, Math.max(50, node.x))
      node.y = Math.min(380, Math.max(50, node.y))
    })
  }
  return nodes.map((node) => ({ ...node, x: Math.round(node.x), y: Math.round(node.y) }))
}

function graphPoint(event: PointerEvent | WheelEvent) {
  const svg = graphSvgRef.value
  if (!svg) return { x: 0, y: 0 }
  const point = svg.createSVGPoint()
  point.x = event.clientX
  point.y = event.clientY
  const matrix = svg.getScreenCTM()
  if (!matrix) return { x: 0, y: 0 }
  const transformed = point.matrixTransform(matrix.inverse())
  return { x: transformed.x, y: transformed.y }
}

function toGraphContentPoint(event: PointerEvent) {
  const point = graphPoint(event)
  return {
    x: (point.x - graphView.x) / graphView.scale,
    y: (point.y - graphView.y) / graphView.scale,
  }
}

function startGraphPan(event: PointerEvent) {
  if (event.button !== 0) return
  const point = graphPoint(event)
  graphDrag.mode = 'pan'
  graphDrag.startX = event.clientX
  graphDrag.startY = event.clientY
  graphDrag.startViewX = point.x
  graphDrag.startViewY = point.y
  graphDrag.originX = graphView.x
  graphDrag.originY = graphView.y
  graphDrag.moved = false
  graphSvgRef.value?.setPointerCapture(event.pointerId)
}

function startNodeDrag(event: PointerEvent, node: GraphNode) {
  if (event.button !== 0) return
  const point = toGraphContentPoint(event)
  graphDrag.mode = 'node'
  graphDrag.uid = node.uid
  graphDrag.startX = point.x
  graphDrag.startY = point.y
  graphDrag.startViewX = 0
  graphDrag.startViewY = 0
  graphDrag.originX = node.x
  graphDrag.originY = node.y
  graphDrag.moved = false
  ;(event.currentTarget as Element).setPointerCapture?.(event.pointerId)
}

function moveGraphPointer(event: PointerEvent) {
  if (graphDrag.mode === 'pan') {
    const point = graphPoint(event)
    const dx = point.x - graphDrag.startViewX
    const dy = point.y - graphDrag.startViewY
    if (Math.abs(dx) + Math.abs(dy) > 3) graphDrag.moved = true
    graphView.x = graphDrag.originX + dx
    graphView.y = graphDrag.originY + dy
  }
  if (graphDrag.mode === 'node' && graphDrag.uid) {
    const point = toGraphContentPoint(event)
    if (Math.abs(point.x - graphDrag.startX) + Math.abs(point.y - graphDrag.startY) > 3) graphDrag.moved = true
    manualGraphPositions[graphDrag.uid] = {
      x: Math.round(graphDrag.originX + point.x - graphDrag.startX),
      y: Math.round(graphDrag.originY + point.y - graphDrag.startY),
    }
  }
}

function endGraphPointer(event: PointerEvent) {
  try {
    graphSvgRef.value?.releasePointerCapture?.(event.pointerId)
  } catch {
    // Pointer capture may already be released by the browser.
  }
  graphDrag.mode = ''
  graphDrag.uid = ''
}

function endNodePointer(event: PointerEvent, row: ModelElement) {
  try {
    ;(event.currentTarget as Element).releasePointerCapture?.(event.pointerId)
  } catch {
    // Pointer capture may already be released by the browser.
  }
  if (graphDrag.moved) {
    graphDrag.mode = ''
    graphDrag.uid = ''
    graphDrag.moved = false
    return
  }
  graphDrag.mode = ''
  graphDrag.uid = ''
  focusElement(row)
}

function handleGraphWheel(event: WheelEvent) {
  zoomGraph(event.deltaY > 0 ? 0.9 : 1.1, graphPoint(event))
}

function zoomGraph(factor: number, origin = { x: 380, y: 215 }) {
  const nextScale = Math.min(2.6, Math.max(0.45, graphView.scale * factor))
  const contentX = (origin.x - graphView.x) / graphView.scale
  const contentY = (origin.y - graphView.y) / graphView.scale
  graphView.x = origin.x - contentX * nextScale
  graphView.y = origin.y - contentY * nextScale
  graphView.scale = nextScale
}

function fitGraph() {
  if (!graphNodes.value.length) {
    resetGraphView()
    return
  }
  const padding = 70
  const minX = Math.min(...graphNodes.value.map((node) => node.x)) - padding
  const maxX = Math.max(...graphNodes.value.map((node) => node.x)) + padding
  const minY = Math.min(...graphNodes.value.map((node) => node.y)) - padding
  const maxY = Math.max(...graphNodes.value.map((node) => node.y)) + padding
  const scale = Math.min(760 / Math.max(maxX - minX, 1), 430 / Math.max(maxY - minY, 1), 1.8)
  graphView.scale = Math.max(0.45, scale)
  graphView.x = 760 / 2 - ((minX + maxX) / 2) * graphView.scale
  graphView.y = 430 / 2 - ((minY + maxY) / 2) * graphView.scale
}

function resetGraphView() {
  graphView.scale = 1
  graphView.x = 0
  graphView.y = 0
}

function resetGraphPositions() {
  Object.keys(manualGraphPositions).forEach((key) => delete manualGraphPositions[key])
  resetGraphView()
}

function handleImportTabChange(name: string | number | TabsPaneContext) {
  if (name === 'mms' && !openMbeeEndpoints.value.length) {
    loadOpenMbeeInfo()
  }
}

async function loadOpenMbeeInfo() {
  openMbeeLoading.value = true
  try {
    const [config, endpoints] = await Promise.all([openMbeeApi.config(), openMbeeApi.endpoints()])
    openMbeeConfig.value = config
    openMbeeEndpoints.value = endpoints
  } catch (error) {
    ElMessage.error(apiError(error, '加载 OpenMBEE 接口信息失败'))
  } finally {
    openMbeeLoading.value = false
  }
}

async function testMmsConnection() {
  openMbeeTesting.value = true
  try {
    await openMbeeApi.mmsVersion()
    ElMessage.success('MMS 连接成功')
  } catch (error) {
    ElMessage.error(apiError(error, 'MMS 连接失败'))
  } finally {
    openMbeeTesting.value = false
  }
}

async function loadMmsProjects() {
  mmsProjectsLoading.value = true
  try {
    const result = await openMbeeApi.projects()
    mmsProjects.value = extractMmsList(result.data)
    ElMessage.success(`已获取 ${mmsProjects.value.length} 个 MMS 项目`)
  } catch (error) {
    ElMessage.error(apiError(error, '获取 MMS 项目失败'))
  } finally {
    mmsProjectsLoading.value = false
  }
}

async function loadMmsRefs() {
  if (!mmsImportForm.mms_project_id) return
  mmsRefsLoading.value = true
  try {
    const result = await openMbeeApi.refs(mmsImportForm.mms_project_id)
    mmsRefs.value = extractMmsList(result.data)
    ElMessage.success(`已获取 ${mmsRefs.value.length} 个分支`)
  } catch (error) {
    ElMessage.error(apiError(error, '获取 MMS 分支失败'))
  } finally {
    mmsRefsLoading.value = false
  }
}

async function importFromMms() {
  if (!mmsImportForm.local_project_id || !mmsImportForm.name.trim() || !mmsImportForm.mms_project_id || !mmsImportForm.ref_id) {
    ElMessage.warning('请填写本地项目、模型名称、MMS 项目和分支')
    return
  }
  if (!mmsImportForm.root_element_id.trim() && !mmsImportForm.search_keyword.trim()) {
    ElMessage.warning('请填写根元素 ID 或搜索关键词')
    return
  }
  mmsImporting.value = true
  try {
    mmsImportResult.value = await openMbeeApi.importModel({
      local_project_id: mmsImportForm.local_project_id,
      name: mmsImportForm.name,
      description: mmsImportForm.description || undefined,
      mms_project_id: mmsImportForm.mms_project_id,
      ref_id: mmsImportForm.ref_id,
      root_element_id: mmsImportForm.root_element_id || undefined,
      commit_id: mmsImportForm.commit_id || undefined,
      search_keyword: mmsImportForm.search_keyword || undefined,
      element_type: mmsImportForm.element_type || undefined,
      limit: mmsImportForm.limit,
      depth: mmsImportForm.depth,
    })
    ElMessage.success('OpenMBEE 模型已导入')
    models.value = await modelApi.list()
    await loadModelVersioning()
  } catch (error) {
    ElMessage.error(apiError(error, '导入 OpenMBEE 模型失败'))
  } finally {
    mmsImporting.value = false
  }
}

async function load() {
  projects.value = await projectApi.list()
  models.value = await modelApi.list()
  if (!mmsImportForm.local_project_id && projects.value.length) {
    mmsImportForm.local_project_id = projects.value[0].id
  }
  if (!versionProjectId.value && projects.value.length) {
    versionProjectId.value = projects.value[0].id
  }
  await loadModelVersioning()
  await loadOpenMbeeInfo()
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
    form.append('branch_name', upload.branch_name || 'main')
    if (upload.version_tag) form.append('version_tag', upload.version_tag)
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
  if (versionProjectId.value !== row.project_id) {
    versionProjectId.value = row.project_id
    await loadModelVersioning()
  }
  selectedElement.value = null
  targetModelId.value = undefined
  compareResult.value = null
  elementKeyword.value = ''
  elementType.value = ''
  const graph = await modelApi.graph(row.id)
  elements.value = graph.elements
  relations.value = graph.relations
}

async function loadModelVersioning() {
  if (!versionProjectId.value) return
  const params = { item_type: 'model' as const, project_id: versionProjectId.value }
  branches.value = await versioningApi.branches(params)
  tags.value = await versioningApi.tags(params)
  rollbackRecords.value = await versioningApi.rollbackRecords(params)
}

async function createBranch() {
  if (!versionProjectId.value || !branchForm.name.trim()) {
    ElMessage.warning('请选择项目并填写分支名称')
    return
  }
  try {
    await versioningApi.createBranch({
      project_id: versionProjectId.value,
      item_type: 'model',
      name: branchForm.name,
      source_model_id: branchForm.source_model_id,
    })
    ElMessage.success('模型分支已创建')
    Object.assign(branchForm, { name: '', source_model_id: undefined })
    models.value = await modelApi.list()
    await loadModelVersioning()
  } catch (error) {
    ElMessage.error(apiError(error, '创建分支失败'))
  }
}

function selectBranch(row: VersionBranch) {
  rollbackForm.branch_id = row.id
  tagForm.branch_id = row.id
  if (tagForm.model_id && !tagTargetModels.value.some((model) => model.id === tagForm.model_id)) {
    tagForm.model_id = undefined
  }
  resetInvalidRollbackTargets()
}

function prepareTag(row: VersionBranch) {
  tagForm.branch_id = row.id
  tagForm.model_id = row.head_model_id
}

async function renameBranch(row: VersionBranch) {
  try {
    const result = await ElMessageBox.prompt('请输入新的分支名称', '重命名分支', {
      inputValue: row.name,
      inputPattern: /\S+/,
      inputErrorMessage: '分支名称不能为空',
    })
    const name = result.value.trim()
    if (!name || name === row.name) return
    await versioningApi.updateBranch(row.id, { name })
    ElMessage.success('分支已重命名')
    models.value = await modelApi.list()
    await loadModelVersioning()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(apiError(error, '重命名分支失败'))
    }
  }
}

async function deleteBranch(row: VersionBranch) {
  try {
    await ElMessageBox.confirm(`删除分支“${row.name}”？仅没有模型版本、标签和回滚记录的空分支可删除。`, '确认删除', { type: 'warning' })
    await versioningApi.deleteBranch(row.id)
    ElMessage.success('分支已删除')
    if (tagForm.branch_id === row.id) {
      tagForm.branch_id = undefined
      tagForm.model_id = undefined
    }
    if (rollbackForm.branch_id === row.id) {
      rollbackForm.branch_id = undefined
    }
    await loadModelVersioning()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除分支失败'))
    }
  }
}

async function createTag() {
  if (!versionProjectId.value || !tagForm.name.trim() || !tagForm.model_id) {
    ElMessage.warning('请填写标签名称并选择目标模型')
    return
  }
  const targetModel = versionModels.value.find((model) => model.id === tagForm.model_id)
  if (!tagForm.branch_id && targetModel) {
    tagForm.branch_id = branches.value.find((branch) => branch.name === targetModel.branch_name)?.id
  }
  if (!tagForm.branch_id) {
    ElMessage.warning('请先选择分支或点击分支行的打标签')
    return
  }
  try {
    await versioningApi.createTag({
      project_id: versionProjectId.value,
      item_type: 'model',
      branch_id: tagForm.branch_id,
      model_id: tagForm.model_id,
      name: tagForm.name,
    })
    ElMessage.success('模型标签已创建')
    Object.assign(tagForm, { name: '', branch_id: undefined, model_id: undefined })
    await loadModelVersioning()
  } catch (error) {
    ElMessage.error(apiError(error, '创建标签失败'))
  }
}

async function rollbackModel() {
  if (!versionProjectId.value || !rollbackForm.branch_id) {
    ElMessage.warning('请选择目标分支')
    return
  }
  if (rollbackMode.value === 'tag' && !rollbackForm.tag_id) {
    ElMessage.warning('请选择目标标签')
    return
  }
  if (rollbackMode.value === 'model' && !rollbackForm.target_model_id) {
    ElMessage.warning('请选择目标模型')
    return
  }
  try {
    await ElMessageBox.confirm('回滚会复制目标模型并生成新的模型版本，是否继续？', '确认回滚', { type: 'warning' })
    await versioningApi.rollback({
      project_id: versionProjectId.value,
      item_type: 'model',
      branch_id: rollbackForm.branch_id,
      tag_id: rollbackMode.value === 'tag' ? rollbackForm.tag_id : undefined,
      target_model_id: rollbackMode.value === 'model' ? rollbackForm.target_model_id : undefined,
      reason: rollbackForm.reason,
    })
    ElMessage.success('模型回滚完成')
    models.value = await modelApi.list()
    await loadModelVersioning()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '回滚失败'))
    }
  }
}

function resetInvalidRollbackTargets() {
  if (rollbackForm.tag_id && !rollbackTargetTags.value.some((tag) => tag.id === rollbackForm.tag_id)) {
    rollbackForm.tag_id = undefined
  }
  if (
    rollbackForm.target_model_id &&
    !rollbackTargetModels.value.some((model) => model.id === rollbackForm.target_model_id)
  ) {
    rollbackForm.target_model_id = undefined
  }
}

function modelLabel(model?: SysMLModel) {
  return model ? modelVersionLabel(model) : '未设置'
}

function branchName(id?: number) {
  return id ? branches.value.find((branch) => branch.id === id)?.name || `#${id}` : '未关联'
}

function extractMmsList(value: unknown): Record<string, unknown>[] {
  if (Array.isArray(value)) return value.filter(isRecord)
  if (!isRecord(value)) return []
  for (const key of ['projects', 'refs', 'elements', 'items', 'results', 'data']) {
    const nested = value[key]
    if (Array.isArray(nested)) return nested.filter(isRecord)
    if (isRecord(nested)) {
      const result = extractMmsList(nested)
      if (result.length) return result
    }
  }
  return []
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function mmsItemId(item: Record<string, unknown>) {
  return String(item.id || item._id || item.projectId || item.refId || item.name || '')
}

function mmsItemLabel(item: Record<string, unknown>) {
  const id = mmsItemId(item)
  const name = String(item.name || item._name || item.title || id)
  return id && id !== name ? `${name} (${id})` : name
}

async function copyToClipboard(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('已复制')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = value
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
    ElMessage.success('已复制')
  }
}

function openJupyter() {
  window.open(jupyterUrl, '_blank', 'noopener')
}

function editModel(row: SysMLModel) {
  editingModelId.value = row.id
  Object.assign(modelForm, {
    name: row.name,
    description: row.description || '',
  })
  modelDialog.value = true
}

async function saveModel() {
  if (!editingModelId.value) return
  try {
    const updated = await modelApi.update(editingModelId.value, {
      name: modelForm.name,
      description: modelForm.description,
    })
    models.value = await modelApi.list()
    const nextModel = models.value.find((item) => item.id === updated.id) || updated
    await selectModel(nextModel)
    await loadModelVersioning()
    modelDialog.value = false
    ElMessage.success('模型已更新')
  } catch (error) {
    ElMessage.error(apiError(error, '更新模型失败'))
  }
}

async function removeModel(row: SysMLModel) {
  try {
    await ElMessageBox.confirm(`删除模型“${row.name}”？模型元素和关系会一并删除。`, '确认删除', { type: 'warning' })
    await modelApi.remove(row.id)
    ElMessage.success('模型已删除')
    if (selected.value?.id === row.id) {
      selected.value = null
      selectedElement.value = null
      elements.value = []
      relations.value = []
      compareResult.value = null
      targetModelId.value = undefined
    }
    await load()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除模型失败'))
    }
  }
}

function resetModelForm() {
  editingModelId.value = undefined
  Object.assign(modelForm, { name: '', description: '' })
}

function focusElement(row: ModelElement) {
  selectedElement.value = row
  if (elements.value.length > graphNodeLimit.value && graphScope.value === 'important') {
    graphScope.value = 'neighborhood'
  }
  syncTreeSelection(row.element_uid)
}

function focusTreeNode(node: ElementTreeNode) {
  selectedElement.value = node.element
  if (elements.value.length > graphNodeLimit.value && graphScope.value === 'important') {
    graphScope.value = 'neighborhood'
  }
  syncTreeSelection(node.uid)
}

function focusRelation(row: ModelRelation) {
  const element = elementByUid.value.get(row.source_uid) || elementByUid.value.get(row.target_uid)
  if (element) focusElement(element)
}

function createRelation() {
  if (!selected.value) return
  resetRelationForm()
  if (selectedElement.value) {
    relationForm.source_uid = selectedElement.value.element_uid
  }
  relationDialog.value = true
}

function editRelation(row: ModelRelation) {
  editingRelationId.value = row.id
  Object.assign(relationForm, {
    source_uid: row.source_uid,
    target_uid: row.target_uid,
    relation_type: row.relation_type,
    label: row.label || '',
  })
  relationDialog.value = true
}

async function saveRelation() {
  if (!selected.value) return
  if (!relationForm.source_uid || !relationForm.target_uid || !relationForm.relation_type.trim()) {
    ElMessage.warning('请选择源元素、目标元素并填写关系类型')
    return
  }
  try {
    const payload = {
      source_uid: relationForm.source_uid,
      target_uid: relationForm.target_uid,
      relation_type: relationForm.relation_type.trim(),
      label: relationForm.label.trim(),
    }
    const changed = editingRelationId.value
      ? await modelApi.updateRelation(editingRelationId.value, payload)
      : await modelApi.createRelation(selected.value.id, payload)
    await refreshAfterRelationEdit(changed.model_id, changed.source_uid)
    relationDialog.value = false
    ElMessage.success(editingRelationId.value ? '关系已更新' : '关系已新增')
  } catch (error) {
    ElMessage.error(apiError(error, editingRelationId.value ? '修改关系失败' : '新增关系失败'))
  }
}

async function removeRelation(row: ModelRelation) {
  try {
    await ElMessageBox.confirm(`删除关系“${elementName(row.source_uid)} -> ${elementName(row.target_uid)}”？会生成新的模型版本。`, '确认删除', {
      type: 'warning',
    })
    const newModel = await modelApi.removeRelation(row.id)
    await refreshAfterRelationEdit(newModel.id, row.source_uid)
    ElMessage.success('关系已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除关系失败'))
    }
  }
}

async function refreshAfterRelationEdit(modelId: number, focusUid?: string) {
  models.value = await modelApi.list()
  const nextModel = models.value.find((item) => item.id === modelId)
  if (nextModel) {
    await selectModel(nextModel)
    const nextElement = focusUid ? elements.value.find((item) => item.element_uid === focusUid) : undefined
    if (nextElement) {
      selectedElement.value = nextElement
      await syncTreeSelection(nextElement.element_uid)
    }
  }
  await loadModelVersioning()
}

function resetRelationForm() {
  editingRelationId.value = undefined
  Object.assign(relationForm, { source_uid: '', target_uid: '', relation_type: '', label: '' })
}

function editElement(row: ModelElement) {
  selectedElement.value = row
  syncTreeSelection(row.element_uid)
  editing.value = { ...row }
  editDialog.value = true
}

async function saveElement() {
  if (!editing.value) return
  try {
    const updated = await modelApi.updateElement(editing.value.id, {
      name: editing.value.name,
      documentation: editing.value.documentation,
    })
    models.value = await modelApi.list()
    const nextModel = models.value.find((item) => item.id === updated.model_id)
    if (nextModel) {
      await selectModel(nextModel)
      const nextElement =
        elements.value.find((item) => item.id === updated.id) ||
        elements.value.find((item) => item.element_uid === updated.element_uid)
      if (nextElement) {
        selectedElement.value = nextElement
        await syncTreeSelection(nextElement.element_uid)
      }
    }
    await loadModelVersioning()
    editDialog.value = false
    ElMessage.success('元素已更新')
  } catch (error) {
    ElMessage.error(apiError(error, '修改元素失败'))
  }
}

async function loadCompare() {
  if (!selected.value || !targetModelId.value) return
  try {
    compareResult.value = await modelApi.compare(selected.value.id, targetModelId.value)
  } catch (error) {
    ElMessage.error(apiError(error, '版本对比失败'))
  }
}

function exportCompareCsv() {
  if (!compareResult.value) return
  const rows = [
    ['分类', 'UID/源', '名称/目标', '类型/关系', '变更字段/标签'],
    ...compareResult.value.added_elements.map((item) => ['新增元素', item.uid, item.name || '', item.type || '', '']),
    ...compareResult.value.removed_elements.map((item) => ['删除元素', item.uid, item.name || '', item.type || '', '']),
    ...compareResult.value.changed_elements.map((item) => [
      '变更元素',
      item.uid,
      item.name || '',
      item.type || '',
      item.change_fields.join('; '),
    ]),
    ...compareResult.value.added_relations.map((item) => [
      '新增关系',
      item.source_uid,
      item.target_uid,
      item.relation_type,
      item.label || '',
    ]),
    ...compareResult.value.removed_relations.map((item) => [
      '删除关系',
      item.source_uid,
      item.target_uid,
      item.relation_type,
      item.label || '',
    ]),
  ]
  downloadText(compareFileName('csv'), rows.map((row) => row.map(escapeCsv).join(',')).join('\n'), 'text/csv;charset=utf-8')
}

function exportCompareHtml() {
  if (!compareResult.value) return
  const result = compareResult.value
  const section = (title: string, rows: string) => `<h2>${title}</h2><table><tbody>${rows || '<tr><td>无</td></tr>'}</tbody></table>`
  const elementRows = (items: typeof result.added_elements) =>
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.uid)}</td><td>${escapeHtml(item.name || '')}</td><td>${escapeHtml(item.type || '')}</td><td>${escapeHtml(item.change_fields.join(', '))}</td></tr>`,
      )
      .join('')
  const relationRows = (items: typeof result.added_relations) =>
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.source_uid)}</td><td>${escapeHtml(item.relation_type)}</td><td>${escapeHtml(item.target_uid)}</td><td>${escapeHtml(item.label || '')}</td></tr>`,
      )
      .join('')
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>模型版本对比报告</title><style>body{font-family:Microsoft YaHei,sans-serif;line-height:1.7;color:#1f2937;padding:24px}table{border-collapse:collapse;width:100%;margin:12px 0 20px}td,th{border:1px solid #cbd5e1;padding:8px 10px}h1,h2{color:#0f172a}.meta{color:#64748b}</style></head><body><h1>模型版本对比报告</h1><p class="meta">基准：${escapeHtml(result.base_model.name)} V${result.base_model.version}；目标：${escapeHtml(result.target_model.name)} V${result.target_model.version}</p>${section('新增元素', elementRows(result.added_elements))}${section('删除元素', elementRows(result.removed_elements))}${section('变更元素', elementRows(result.changed_elements))}${section('新增关系', relationRows(result.added_relations))}${section('删除关系', relationRows(result.removed_relations))}</body></html>`
  downloadText(compareFileName('html'), html, 'text/html;charset=utf-8')
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

function elementName(uid: string) {
  const element = elementByUid.value.get(uid)
  return element ? `${element.name} (${element.type})` : uid
}

function elementOptionLabel(element: ModelElement) {
  return `${element.name} (${element.type}) - ${element.element_uid}`
}

function statusLabel(status: string) {
  return (
    {
      parsed: '已解析',
      parsing: '解析中',
      failed: '解析失败',
      uploaded: '已上传',
      rollback: '回滚版本',
      edited: '编辑版本',
    }[status] || status
  )
}

function modelVersionLabel(model: SysMLModel) {
  const tag = model.version_tag ? ` @ ${model.version_tag}` : ''
  return `${model.name} ${model.branch_name} v${model.version}${tag}`
}

function clearFocus() {
  selectedElement.value = null
  modelTreeRef.value?.setCurrentKey()
  if (graphScope.value === 'neighborhood') {
    graphScope.value = 'important'
  }
}

function nodeTooltip(element: ModelElement) {
  const childCount = childCountByUid.value.get(element.element_uid) || 0
  const relationCount = relationDegreeByUid.value.get(element.element_uid) || 0
  const documentation = element.documentation ? `\n说明：${element.documentation}` : '\n说明：暂无'
  return `名称：${element.name}\n类型：${element.type}\nUID：${element.element_uid}\n父级：${element.parent_uid || '无'}\n子节点：${childCount}\n关联关系：${relationCount}${documentation}`
}

function compareFileName(ext: 'csv' | 'html') {
  const base = compareResult.value?.base_model.name || 'base'
  const target = compareResult.value?.target_model.name || 'target'
  const safe = `${base}-vs-${target}`.replace(/[^\w\u4e00-\u9fa5-]+/g, '_').slice(0, 80)
  return `model-compare-${safe}.${ext}`
}

function downloadText(filename: string, content: string, type: string) {
  const prefix = type.includes('csv') ? '\uFEFF' : ''
  const blob = new Blob([prefix + content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function escapeCsv(value: unknown) {
  return `"${String(value).replace(/"/g, '""')}"`
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
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

watch([elementKeyword, elementType], () => {
  elementPage.value = 1
  resetGraphPositions()
})

watch([relationKeyword, relationType], () => {
  relationPage.value = 1
})

watch([elementPageSize, relationPageSize], () => {
  elementPage.value = 1
  relationPage.value = 1
})

watch([selected, selectedElement, graphNodeLimit, graphEdgeLimit], () => {
  resetGraphPositions()
})

onMounted(load)
</script>

<style scoped>
.upload-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
}

.upload-fields {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.upload-actions {
  padding-bottom: 18px;
  white-space: nowrap;
}

.upload-form :deep(.el-select),
.upload-form :deep(.el-input) {
  width: 100%;
}

.file-input {
  width: 100%;
  height: 32px;
  padding: 4px 0;
}

.ingest-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.integration-panel {
  display: grid;
  gap: 14px;
}

.integration-summary {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel-soft);
}

.integration-summary > div:first-child {
  flex: 1 1 360px;
  min-width: 0;
}

.integration-summary h3 {
  margin: 0 0 6px;
  color: var(--brand-dark);
  font-size: 17px;
}

.integration-summary p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.integration-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  flex: 0 0 auto;
  max-width: 100%;
}

.integration-actions .el-button,
.mms-form-actions .el-button {
  margin-left: 0;
  white-space: normal;
}

.integration-desc {
  margin-top: 2px;
}

.endpoint-table {
  margin-top: 2px;
}

.mms-import-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.mms-import-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.mms-import-form :deep(.el-select),
.mms-import-form :deep(.el-input),
.mms-import-form :deep(.el-input-number) {
  width: 100%;
}

.mms-form-actions {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  justify-content: flex-end;
  grid-column: 1 / -1;
  flex-wrap: wrap;
  min-width: 0;
}

.jupyter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.command-box {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.command-box span {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.command-box pre {
  margin: 0;
  max-width: 100%;
  overflow: auto;
  color: var(--ink);
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.card-header,
.compare-toolbar,
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}

.card-header {
  flex-wrap: wrap;
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

.relation-filter {
  align-items: stretch;
}

.relation-filter .el-select {
  width: 160px;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
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

.model-tree :deep(.el-tree-node__content),
.model-tree :deep(.el-tree-node__label) {
  white-space: nowrap;
}

.graph-legend {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 13px;
}

.graph-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  min-width: 0;
}

.graph-actions .muted {
  min-width: 0;
  overflow-wrap: anywhere;
}

.graph-actions .el-button + .el-button {
  margin-left: 0;
}

.graph-tool-button {
  width: 30px;
  height: 30px;
  padding: 0;
  border-color: var(--line-strong);
  background: #ffffff;
  color: var(--brand-dark);
  box-shadow: var(--shadow-sm);
}

.graph-tool-button:hover,
.graph-tool-button:focus {
  border-color: var(--brand);
  background: var(--brand-soft);
  color: var(--brand-dark);
}

.graph-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.graph-scope {
  width: 118px;
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
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.graph-panel svg:active {
  cursor: grabbing;
}

.graph-edge {
  stroke: #6b7280;
  stroke-width: 1.8;
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
  font-size: 12px;
  font-weight: 700;
  pointer-events: none;
}

.graph-node .node-type {
  fill: var(--muted);
  font-size: 10px;
  font-weight: 600;
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

.version-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.version-panel {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbfb 100%);
  box-shadow: var(--shadow-sm);
}

.version-panel h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  color: var(--brand-dark);
  font-size: 15px;
  font-weight: 800;
}

.version-panel h3::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--accent);
}

.version-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.rollback-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.version-form :deep(.el-select),
.version-form :deep(.el-input) {
  width: 100%;
}

.version-panel :deep(.el-table) {
  border-radius: 6px;
}

@media (max-width: 1180px) {
  .upload-fields,
  .jupyter-grid,
  .mms-import-form,
  .version-grid,
  .compare-grid {
    grid-template-columns: 1fr;
  }
  .integration-summary {
    flex-direction: column;
  }
  .integration-actions {
    justify-content: flex-start;
  }
}
</style>
